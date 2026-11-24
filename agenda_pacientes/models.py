from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from admin_cadastros.models import Estabelecimento, Pessoa, Local
from atendimentos.models import Atendimento
from dominios.choices import sn_choices, status_choices

# Setor, Local e a hierarquia (Estabelecimento → Setor → Local) moraram aqui
# antes; agora fazem parte de `admin_cadastros` (“10. Setores” / “11. Locais”).


def local_choices():
    """Locais ativos — usados nos filtros e selects da agenda."""
    return Local.objects.filter(status='A')


class TipoAgendamento(models.Model):
    """Tipos de agendamento: exame, visita, dentista, perícia..."""
    descricao = models.CharField(max_length=100, verbose_name='Descrição')
    externo = models.BooleanField(
        default=True, verbose_name='Agenda Externa',
        help_text='Locais externos usam Alas que não são de internação.')
    exige_exame_solicitado = models.BooleanField(
        default=False, verbose_name='Exige Exame Solicitado',
        help_text='Vincula o agendamento a um exame solicitado no atendimento.')
    local = models.ForeignKey(
        Local, on_delete=models.PROTECT, blank=True, null=True,
        verbose_name='Local Padrão',
        help_text='Local sugerido ao criar um agendamento deste tipo.')
    cor = models.CharField(
        max_length=7, default='#0d6efd', blank=True, verbose_name='Cor',
        help_text='Cor usada para destacar este tipo na agenda (ex.: #0d6efd).')
    exige_local_online = models.CharField(
        max_length=1, choices=sn_choices, default='N',
        verbose_name='Exige Local Online',
        help_text='Sim = o agendamento deste tipo precisa de link de acesso.')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status')
    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, blank=True,
        related_name='tipoagendamento_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, blank=True,
        related_name='tipoagendamento_atualizado_por', verbose_name='Us.Atualização')

    class Meta:
        verbose_name = 'Tipo de Agendamento'
        verbose_name_plural = '2. Tipos de Agendamento'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao

    def clean(self):
        cor = (self.cor or '').strip()
        if cor and not cor.startswith('#'):
            cor = f'#{cor}'
        if cor and (len(cor) != 7 or any(
                c not in '0123456789abcdefABCDEF' for c in cor[1:])):
            raise ValidationError(
                {'cor': 'Informe a cor no formato hexadecimal, ex.: #0d6efd.'})
        self.cor = cor
        if self.local_id:
            local = self.local
            if local.status != 'A':
                raise ValidationError({
                    'local': 'Selecione um local ativo como padrão do tipo.'
                })
            if local.online == 'S' and not self.externo:
                raise ValidationError({
                    'local': 'Agenda interna deve usar local de uma Ala de '
                             'internação, não um local online.'
                })
            if local.setor_id and \
                    local.setor.ala.internacao == self.externo:
                classificacao = 'interna' if not self.externo else 'externa'
                raise ValidationError({
                    'local': f'Selecione um local de uma Ala {classificacao} '
                             'para este tipo de agendamento.'
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class AgendaPaciente(models.Model):
    """Agendamento sempre ligado a um ATENDIMENTO (e, se exame, ao Exame).

    Não existe campo `pessoa`: o paciente é sempre o do atendimento
    (`agenda.atendimento.pessoa`). Quando o tipo é do tipo exame, o agendamento
    referencia o **exame solicitado** (`exame` → `prontuarios.Exame`).
    """
    atendimento = models.ForeignKey(
        Atendimento, on_delete=models.PROTECT, related_name='agendamentos',
        verbose_name='Atendimento')
    tipo = models.ForeignKey(
        TipoAgendamento, on_delete=models.PROTECT, verbose_name='Tipo de Agendamento')
    exame = models.ForeignKey(
        'prontuarios.Exame', on_delete=models.PROTECT, blank=True, null=True,
        related_name='agendamentos', verbose_name='Exame Solicitado',
        help_text='Obrigatório quando o tipo de agendamento for do tipo exame. '
                  'O exame deve pertencer ao atendimento e não pode ter sido '
                  'executado.')
    local = models.ForeignKey(Local, on_delete=models.PROTECT, blank=False, null=False,
        verbose_name='Local', error_messages={
            'blank': 'Informe o local do agendamento.',
            'null': 'Informe o local do agendamento.',
        },
        help_text='Obrigatório; local do agendamento (modal de agendamento do exame).'
        )
    data_hora = models.DateTimeField(verbose_name='Data/Hora do Agendamento')
    observacao = models.TextField(
        blank=False, null=False, verbose_name='Anotação',
        error_messages={
            'blank': 'Informe a anotação da agenda.',
            'null': 'Informe a anotação da agenda.',
        },
        help_text='Obrigatória; anotação do agendamento (modal de '
                  'agendamento do exame).')
    link_videochamada = models.CharField(
        max_length=300, blank=True, null=True, verbose_name='Link da Videochamada')
    link_whatsapp = models.CharField(
        max_length=300, blank=True, null=True, verbose_name='Link do WhatsApp')
    responsavel = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True,
        related_name='agendamentos_realizados', verbose_name='Responsável')
    efetuado = models.CharField(
        max_length=1, choices=sn_choices, default='N', verbose_name='Efetuado')
    dt_efetuado = models.DateTimeField(
        blank=True, null=True, verbose_name='Data da Realização')
    data_execucao = models.DateTimeField(
        blank=True, null=True, verbose_name='Data da Execução')
    observacao_execucao = models.TextField(
        blank=True, null=False, verbose_name='Anotação da Execução',
        help_text='Obrigatória quando o agendamento estiver efetuado.')
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT, verbose_name='Estabelecimento')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status')
    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, blank=True,
        related_name='agendapaciente_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, blank=True,
        related_name='agendapaciente_atualizado_por', verbose_name='Us.Atualização')

    class Meta:
        verbose_name = 'Agenda de Paciente'
        verbose_name_plural = '3. Agendas de Pacientes'
        ordering = ('data_hora', 'pk')
        constraints = [
            models.UniqueConstraint(
                fields=('exame',),
                condition=Q(exame__isnull=False, status='A'),
                name='unique_agenda_ativa_por_exame',
            ),
        ]

    def __str__(self):
        return (f'{self.atendimento.pessoa} - {self.tipo} - '
                f'{timezone.localtime(self.data_hora):%d/%m/%Y %H:%M}')

    @property
    def tipo_agendamento(self):
        """Apelido de `tipo` (compatível com a API da agenda)."""
        return self.tipo

    @property
    def pessoa(self):
        """Paciente do agendamento: SEMPRE a pessoa do atendimento."""
        return self.atendimento.pessoa if self.atendimento_id else None

    # Apelido mantido para compatibilidade com telas antigas.
    paciente = pessoa

    @property
    def tipo_exame(self):
        """Compatibilidade: indica se o tipo exige exame solicitado."""
        if not self.tipo_id:
            return False
        return self.tipo.exige_exame_solicitado

    @property
    def link_acesso(self):
        if self.link_videochamada:
            return self.link_videochamada
        if self.link_whatsapp:
            return self.link_whatsapp
        if self.local_id and self.local.link_online:
            return self.local.link_online
        return ''

    def clean(self):
        from prontuarios.models import ResultadoExame

        errors = {}
        if self.observacao and not self.observacao.strip():
            errors['observacao'] = 'Informe a anotação da agenda.'
        if self.efetuado == 'S' and not (
                self.observacao_execucao or '').strip():
            errors['observacao_execucao'] = (
                'Informe a anotação da execução.')
        if not self.data_hora:
            errors['data_hora'] = 'Informe a data e hora do agendamento.'
        if not self.tipo_id:
            errors['tipo'] = 'Informe o tipo de agendamento.'
        elif self.tipo.status != 'A':
            errors['tipo'] = ('Este tipo de agendamento está inativo. '
                              'Selecione um tipo ativo.')

        if self.atendimento_id and self.estabelecimento_id and \
                self.atendimento.estabelecimento_id != self.estabelecimento_id:
            errors['atendimento'] = (
                'O atendimento precisa pertencer ao estabelecimento '
                'selecionado na sessão.')

        if self.tipo_id and self.tipo_exame:
            # Tipo configurado para depender de exame exige solicitação ativa
            # do mesmo atendimento, ainda sem resultado.
            if not self.exame_id:
                errors['exame'] = (
                    'Para este tipo de agendamento, selecione o exame solicitado '
                    'do atendimento.')
            else:
                if self.atendimento_id and \
                        self.exame.atendimento_id != self.atendimento_id:
                    errors['exame'] = (
                        'Este exame não pertence ao atendimento informado.')
                if self.exame.status != 'A':
                    errors['exame'] = (
                        'Este exame solicitado está inativo. Selecione um '
                        'exame ativo do atendimento.')
                agenda_original = None
                if self.pk:
                    agenda_original = AgendaPaciente.objects.filter(
                        pk=self.pk).values_list('exame_id', flat=True).first()
                if agenda_original != self.exame_id and \
                        ResultadoExame.objects.filter(
                            exame_id=self.exame_id, status='A').exists():
                    errors['exame'] = (
                        'Este exame já foi executado e não pode ser agendado '
                        'novamente.')
        elif self.exame_id:
            errors['exame'] = (
                'Somente tipos de agendamento que exigem exame podem estar '
                'vinculados a um exame.')

        if self.exame_id and self.status == 'A':
            agenda_existente = AgendaPaciente.objects.filter(
                exame_id=self.exame_id, status='A').exclude(pk=self.pk)
            if agenda_existente.exists():
                errors['exame'] = (
                    'Este exame já possui um agendamento ativo. Consulte a '
                    'data e o local na lista de exames.')

        if not self.local_id:
            errors['local'] = 'Selecione o local do agendamento.'

        if self.local_id:
            local = self.local
            if local.online == 'S' and not self.tipo.externo:
                errors['local'] = (
                    'Agendamento interno deve usar um local de uma Ala de '
                    'internação, não um local online.')
            elif local.setor_id:
                eh_internacao = local.setor.ala.internacao
                if self.tipo_id and eh_internacao == self.tipo.externo:
                    classificacao = 'interna' if not self.tipo.externo else 'externa'
                    errors['local'] = (
                        f'Selecione um local de uma Ala {classificacao} para '
                        'este tipo de agendamento.')
                if self.estabelecimento_id and \
                        local.setor.estabelecimento_id != self.estabelecimento_id:
                    errors['local'] = (
                        'O local precisa pertencer ao estabelecimento '
                        'selecionado na sessão.')

        if self.tipo_id and self.tipo.exige_local_online == 'S' and \
                (not self.local_id or self.local.online != 'S'):
            errors['local'] = (
                'Este tipo de agendamento exige um local online ativo.')
        if self.local_id and self.local.online == 'S' and not self.link_acesso:
            errors['link_videochamada'] = (
                'Informe o link da videochamada ou do WhatsApp '
                'para o atendimento online.')
        if self.efetuado == 'S' and not self.dt_efetuado:
            self.dt_efetuado = timezone.now()
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.efetuado == 'S' and not self.dt_efetuado:
            self.dt_efetuado = timezone.now()
        self.full_clean()
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # Execução espelhada: agenda ↔ exame
    # ------------------------------------------------------------------
    def efetuar(self, usuario=None, desfazer=False, observacao_execucao=None):
        """Marca/desmarca a execução — e espelha no exame (ResultadoExame).

        O que faz em um reflete no outro: efetuar aqui cria/marca o resultado
        do exame; desfazer aqui remove-o.
        """
        from prontuarios.models import ResultadoExame

        self.efetuado = 'N' if desfazer else 'S'
        self.dt_efetuado = None if desfazer else timezone.now()
        self.data_execucao = self.dt_efetuado
        if desfazer:
            self.observacao_execucao = ''
        elif observacao_execucao is not None:
            self.observacao_execucao = observacao_execucao.strip()
        if usuario is not None:
            self.us_atualizacao = usuario
            self.dt_atualizacao = timezone.now()
        self.save(update_fields=[
            'efetuado', 'dt_efetuado', 'data_execucao',
            'observacao_execucao', 'us_atualizacao', 'dt_atualizacao'])

        if self.exame_id:
            if desfazer:
                ResultadoExame.objects.filter(
                    exame_id=self.exame_id, status='A').delete()
            else:
                resultado, criado = ResultadoExame.objects.get_or_create(
                    exame_id=self.exame_id, status='A',
                    defaults={
                        'data_resultado': timezone.localdate(),
                        'us_registro': usuario,
                        'dt_registro': timezone.now(),
                    })
                if criado and not resultado.us_registro_id and usuario:
                    resultado.us_registro = usuario
                    resultado.dt_registro = timezone.now()
                    resultado.save(update_fields=['us_registro', 'dt_registro'])
        return self

    def sincronizar_execucao(self):
        """Espelha a execução vinda do EXAME (ResultadoExame → agenda)."""
        from prontuarios.models import ResultadoExame
        executado = self.exame_id and ResultadoExame.objects.filter(
            exame_id=self.exame_id, status='A').exists()
        if executado and self.efetuado != 'S':
            self.efetuado = 'S'
            self.dt_efetuado = timezone.now()
            self.data_execucao = self.dt_efetuado
            self.save(update_fields=['efetuado', 'dt_efetuado', 'data_execucao'])
        elif not executado and self.efetuado == 'S':
            self.efetuado = 'N'
            self.dt_efetuado = None
            self.data_execucao = None
            self.save(update_fields=['efetuado', 'dt_efetuado', 'data_execucao'])
        return self

    def get_absolute_url(self):
        return reverse('agendapaciente_detalhe', args=[self.pk])


class ParametrosAgenda(models.Model):
    """admin_parametros_agendapaciente — quem vê, edita e exclui a agenda."""
    estabelecimento = models.OneToOneField(
        Estabelecimento, on_delete=models.CASCADE, verbose_name='Estabelecimento')
    usuarios_visualizacao = models.ManyToManyField(
        User, blank=True, related_name='agenda_visualizacao',
        verbose_name='Podem Visualizar')
    usuarios_edicao = models.ManyToManyField(
        User, blank=True, related_name='agenda_edicao',
        verbose_name='Podem Editar')
    usuarios_exclusao = models.ManyToManyField(
        User, blank=True, related_name='agenda_exclusao',
        verbose_name='Podem Excluir')
    grupos_visualizacao = models.ManyToManyField(
        'auth.Group', blank=True, related_name='agenda_grupo_visualizacao',
        verbose_name='Grupos que Podem Visualizar')
    grupos_edicao = models.ManyToManyField(
        'auth.Group', blank=True, related_name='agenda_grupo_edicao',
        verbose_name='Grupos que Podem Editar')
    grupos_exclusao = models.ManyToManyField(
        'auth.Group', blank=True, related_name='agenda_grupo_exclusao',
        verbose_name='Grupos que Podem Excluir')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status')
    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, blank=True,
        related_name='parametrosagenda_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, blank=True,
        related_name='parametrosagenda_atualizado_por', verbose_name='Us.Atualização')

    class Meta:
        verbose_name = 'Parâmetros da Agenda'
        verbose_name_plural = '1. Parâmetros da Agenda'

    def __str__(self):
        return f'Parâmetros da agenda - {self.estabelecimento}'

    @classmethod
    def pode(cls, usuario, estabelecimento, acao):
        """acao: 'ver' | 'editar' | 'excluir'.

        Libera quando o usuário está em **usuários OU em qualquer grupo** da
        ação (superusuário sempre pode).
        """
        if not usuario or not usuario.is_authenticated:
            return False
        if usuario.is_superuser:
            return True
        parametros = cls.objects.filter(
            estabelecimento=estabelecimento, status='A').first()
        if not parametros:
            return False
        campos = {
            'ver': ('usuarios_visualizacao', 'grupos_visualizacao'),
            'editar': ('usuarios_edicao', 'grupos_edicao'),
            'excluir': ('usuarios_exclusao', 'grupos_exclusao'),
        }.get(acao)
        if not campos:
            return False
        campo_usuarios, campo_grupos = campos
        if getattr(parametros, campo_usuarios).filter(pk=usuario.pk).exists():
            return True
        return getattr(parametros, campo_grupos).filter(
            user__pk=usuario.pk).exists()
