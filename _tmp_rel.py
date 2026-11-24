import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'managerontec.settings')
django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS = ['*']

from django.db import transaction
from django.test import Client
from django.contrib.auth.models import User, Group
from django.utils import timezone
from datetime import timedelta

from admin_cadastros.models import Estabelecimento
from atendimentos.models import Atendimento
from agenda_pacientes.models import (
    AgendaPaciente, ParametrosAgenda, TipoAgendamento,
)
from prontuarios.models import Exame, ResultadoExame
from admin_exames.models import TipoExame

est = Estabelecimento.objects.first()
user = User.objects.filter(is_superuser=True).first()
print('est:', est, '| user:', user)


class Rollback(Exception):
    pass


try:
    with transaction.atomic():
        tipo_exame = TipoAgendamento.objects.create(
            descricao='Exame QA Rel', status='A')
        tipo_visita = TipoAgendamento.objects.create(
            descricao='Visita QA Rel', status='A')
        tipo_ex = TipoExame.objects.first()
        from admin_cadastros.models import Pessoa
        from atendimentos.models import TipoAtendimento
        atend = Atendimento.objects.filter(estabelecimento=est).first()
        if not atend:
            pessoa = Pessoa.objects.first()
            tipo_at = TipoAtendimento.objects.first()
            booleanos = {f.name: False for f in Atendimento._meta.fields
                         if f.get_internal_type() == 'BooleanField'
                         and not f.null}
            texto = {f.name: '' for f in Atendimento._meta.fields
                     if f.get_internal_type() in ('CharField', 'TextField')
                     and not f.null and f.name != 'status'}
            choices_ent = Atendimento._meta.get_field(
                'entidade_encaminhamento').choices
            texto['entidade_encaminhamento'] = (choices_ent[0][0]
                                                if choices_ent else 'X')
            texto['carater_atendimento'] = Atendimento._meta.get_field(
                'carater_atendimento').default or 'E'
            atend = Atendimento(pessoa=pessoa, estabelecimento=est,
                                tipo_atendimento=tipo_at,
                                us_registro=user,
                                status='A', **booleanos, **texto)
            atend.full_clean()
            atend.save()
        print('atendimento teste:', atend.pk)

        exame = Exame(atendimento=atend, tipo_exame=tipo_ex,
                      estabelecimento=est, us_registro=user,
                      dt_registro=timezone.now())
        exame.full_clean()
        exame.save()
        print('exame criado:', exame.pk)

        # --- Grupos nos Parâmetros da Agenda -----------------------------
        from django.contrib.auth.models import User as U, Permission
        comum = U.objects.create_user('qa_comum_grupos', password='x')
        comum.is_superuser = False
        comum.is_staff = False
        comum.user_permissions.add(*Permission.objects.filter(
            codename__in=['view_agendapaciente', 'add_agendapaciente',
                          'change_agendapaciente', 'delete_agendapaciente']))
        comum.save()
        grupo = Group.objects.create(name='QA Agenda')
        comum.groups.add(grupo)
        ParametrosAgenda.objects.filter(estabelecimento=est).delete()
        p, _ = ParametrosAgenda.objects.update_or_create(
            estabelecimento=est, defaults={'status': 'A'})
        # sem usuário nem grupo
        print('sem usuario/grupo -> pode editar?',
              ParametrosAgenda.pode(comum, est, 'editar'))
        # só com grupo
        p.grupos_edicao.add(grupo)
        print('por grupo -> pode editar?', ParametrosAgenda.pode(comum, est, 'editar'))
        print('por grupo -> pode excluir? (nao liberado)',
              ParametrosAgenda.pode(comum, est, 'excluir'))

        c = Client()
        c.force_login(user)
        s = c.session
        s['estabelecimento_id'] = est.pk
        s.save()

        # --- Agendamento tipo EXAME sem exame -> recusa ------------------
        r = c.post('/agenda/agenda_cadastrar/', {
            'atendimento': atend.pk, 'tipo': tipo_exame.pk,
            'data_hora': '2026-12-20T10:00', 'status': 'A', 'efetuado': 'N'})
        txt = r.content.decode()
        print('exame sem exame solicitado ->',
              'selecione o exame solicitado' in txt)

        # --- Agendamento tipo EXAME com exame -> OK ----------------------
        r = c.post('/agenda/agenda_cadastrar/', {
            'atendimento': atend.pk, 'tipo': tipo_exame.pk,
            'exame': exame.pk, 'data_hora': '2026-12-20T10:00',
            'status': 'A', 'efetuado': 'N'})
        print('exame com exame solicitado ->', r.status_code,
              r.get('Location'))
        agenda = AgendaPaciente.objects.get(
            tipo=tipo_exame, atendimento=atend)
        print('agenda.exame setado?', agenda.exame_id == exame.pk,
              '| paciente via atendimento:',
              agenda.pessoa == atend.pessoa)

        # --- Tipo NAO-exame com exame -> recusa --------------------------
        r = c.post('/agenda/agenda_cadastrar/', {
            'atendimento': atend.pk, 'tipo': tipo_visita.pk,
            'exame': exame.pk, 'data_hora': '2026-12-21T10:00',
            'status': 'A', 'efetuado': 'N'})
        print('nao-exame com exame ->', 'Somente agendamento do tipo exame'
              in r.content.decode())

        # --- Exame de OUTRO atendimento -> recusa ------------------------
        atend2 = Atendimento.objects.exclude(pk=atend.pk).filter(
            estabelecimento=est).first()
        if atend2:
            exame2 = Exame.objects.create(
                atendimento=atend2, tipo_exame=tipo_ex,
                estabelecimento=est, us_registro=user)
            r = c.post('/agenda/agenda_cadastrar/', {
                'atendimento': atend.pk, 'tipo': tipo_exame.pk,
                'exame': exame2.pk, 'data_hora': '2026-12-22T10:00',
                'status': 'A', 'efetuado': 'N'})
            print('exame de outro atendimento ->',
                  'não pertence ao atendimento' in r.content.decode())

        # --- Efetuar na agenda espelha no exame --------------------------
        agenda.efetuar(usuario=user)
        print('efetuado na agenda ->', agenda.efetuado,
              '| resultado do exame criado?',
              ResultadoExame.objects.filter(exame=exame, status='A').exists())

        # --- Exame executado não pode ser re-agendado --------------------
        r = c.post('/agenda/agenda_cadastrar/', {
            'atendimento': atend.pk, 'tipo': tipo_exame.pk,
            'exame': exame.pk, 'data_hora': '2026-12-23T10:00',
            'status': 'A', 'efetuado': 'N'})
        print('re-agendar exame executado ->',
              'já foi executado' in r.content.decode())

        # --- Desfazer na agenda remove o resultado -----------------------
        agenda.efetuar(usuario=user, desfazer=True)
        print('desfeito ->', agenda.efetuado,
              '| resultado removido?',
              not ResultadoExame.objects.filter(exame=exame, status='A').exists())

        # --- Efetuar direto no EXAME espelha na agenda -------------------
        ResultadoExame.objects.create(exame=exame, data_resultado=timezone.localdate(), us_registro=user, dt_registro=timezone.now())
        agenda.sincronizar_execucao()
        print('execucao no exame -> agenda efetuado?', agenda.efetuado == 'S')

        raise Rollback
except Rollback as _r:
    print('rollback efetuado (nada persistido)')
