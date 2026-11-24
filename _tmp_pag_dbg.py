import re
from django.db import transaction
from django.test import Client
from django.contrib.auth import get_user_model
from atendimentos.models import Atendimento
from admin_exames.models import TipoExame
from prontuarios.models import Exame

User = get_user_model()


def run():
    with transaction.atomic():
        atend = Atendimento.objects.first()
        est = atend.estabelecimento if atend else None
        if not (est and atend):
            print('SKIP: sem estabelecimento/atendimento')
            transaction.set_rollback(True)
            return

        user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        if not user:
            print('SKIP: sem usuario')
            transaction.set_rollback(True)
            return
        User.objects.filter(pk=user.pk).update(is_superuser=True, is_staff=True)

        print('atendimento:', atend.pk, '| estabelecimento:', est.pk, '| usuario:', user.pk)

        tipo, _ = TipoExame.objects.get_or_create(
            descricao='TESTE PAG DBG',
            defaults={'us_registro': user, 'status': 'A'})
        for i in range(18):
            Exame.objects.create(
                atendimento=atend, tipo_exame=tipo, solicitacao=f'teste {i}',
                estabelecimento=est, us_registro=user, status='A')

        print('exames TESTE no atendimento:', Exame.objects.filter(
            atendimento=atend, tipo_exame=tipo, estabelecimento=est, status='A').count())

        c = Client(SERVER_NAME='localhost')
        c.force_login(user)
        s = c.session
        s['estabelecimento_id'] = est.pk
        s.save()

        for page in (1, 2):
            r = c.get(f'/prontuarios/exame_listar/{atend.pk}/', {'page': page})
            html = r.content.decode() if r.status_code == 200 else ''
            print(f'--- pagina {page}: status {r.status_code}')
            if r.status_code == 200:
                print('painel listing-pagination-panel:', 'listing-pagination-panel' in html)
                m = re.search(r'<strong>([^<]*registros[^<]*)</strong>', html)
                print('strong:', m.group(1) if m else 'AUSENTE')
                print('qtd page-link:', len(re.findall(r'class="page-link"', html)))
                print('tem page=2:', 'page=2' in html)
                for href in re.findall(r'href="(\?[^"]*page=\d+[^"]*)"', html)[:6]:
                    print('   href:', href)
                print('session exame_filters:', dict(c.session.get('exame_filters') or {}))
                print('linhas exame_detalhe:', len(re.findall(r'exame_detalhe/\d+/', html)))
                print('linhas teste:', len(re.findall(r'teste \d+', html)))
            else:
                print('erro (trecho):', html[:800])
        transaction.set_rollback(True)


run()
