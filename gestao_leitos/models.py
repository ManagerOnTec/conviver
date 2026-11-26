"""GESTÃO DE LEITOS — modelos.

Ocupação de leitos por atendimento, sobre a hierarquia já existente em
`admin_cadastros` (Estabelecimento → Ala → Setor → Local → Leito). O paciente
é sempre o do atendimento (`atendimento.pessoa`). Segue os padrões do ERP.
"""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from admin_cadastros.models import Estabelecimento, Leito
from atendimentos.models import Atendimento
from dominios.choices import status_choices

GESTAO_STATUS = (
    ('O', 'Ocupado'),
    ('L', 'Livre'),
    ('B', 'Bloqueado'),
    ('H', 'Higienização'),
)

HISTORICO_OPERACOES = (
    ('ocupacao', 'Ocupação'),
    ('saida', 'Saída/alta'),
    ('transferencia', 'Transferência de leito'),
    ('status', 'Mudança de status'),
    ('alteracao', 'Alteração'),
)


class HistoricoLeito(models.Model):
    """Histórico da ocupação — nunca é apagado."""

    gestao = models.ForeignKey(
        'GestaoLeito', on_delete=models.CASCADE, related_name='historico',
        verbose_name='Ocupação')
    operacao = models.CharField(
        max_length=20, choices=HISTORICO_OPERACOES, verbose_name='Operação')
    usuario = models.ForeignKey(
        User, on_delete=models.PROTECT, editable=False,
        related_name='gl_historico', verbose_name='Usuário')
    dt_operacao = models.DateTimeField(
        default=timezone.now, editable=False, verbose_name='Dt. Operação')
    descricao = models.TextField(verbose_name='Descrição')

    class Meta:
        verbose_name = 'Histórico de Leito'
        verbose_name_plural = '2. Histórico de Leitos'
        ordering = ('-dt_operacao',)

    def __str__(self):
        return (f'{self.get_operacao_display()} — '
                f'{timezone.localtime(self.dt_operacao):%d/%m/%Y %H:%M} — '
                f'{self.usuario}')


class GestaoLeito(models.Model):
    """Ocupação de um LEITO por um ATENDIMENTO (paciente do atendimento)."""

    leito = models.ForeignKey(
        Leito, on_delete=models.PROTECT, related_name='ocupacoes',
        verbose_name='Leito')
    atendimento = models.ForeignKey(
        Atendimento, on_delete=models.PROTECT, related_name='ocupacoes_leito',
        verbose_name='Atendimento')
    dt_entrada = models.DateTimeField(
        default=timezone.now, verbose_name='Dt. Entrada')
    dt_saida = models.DateTimeField(
        blank=True, null=True, verbose_name='Dt. Saída',
        help_text='Vazio = leito ainda ocupado pelo atendimento.')
    situacao = models.CharField(
        max_length=1, choices=GESTAO_STATUS, default='O',
        verbose_name='Situação')
    observacoes = models.CharField(
        max_length=255, blank=True, null=True, verbose_name='Observações')
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT,
        verbose_name='Estabelecimento')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status')
    dt_registro = models.DateTimeField(
        default=timezone.now, editable=False, verbose_name='Dt.Cadastro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, editable=False,
        related_name='gl_ocupacoes_criadas', verbose_name='Us.Cadastro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, editable=False, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True,
        editable=False, related_name='gl_ocupacoes_atualizadas',
        verbose_name='Us.Atualização')

    class Meta:
        verbose_name = 'Ocupação de Leito'
        verbose_name_plural = '1. Ocupações de Leitos'
        ordering = ('-dt_entrada', '-pk')
        constraints = [
            # Uma ocupação ATIVA por atendimento.
            models.UniqueConstraint(
                fields=('atendimento',),
                condition=Q(dt_saida__isnull=True, status='A'),
                name='gl_atendimento_um_leito_ativo'),
            # Um atendimento ativo por leito.
            models.UniqueConstraint(
                fields=('leito',),
                condition=Q(dt_saida__isnull=True, status='A',
                            situacao='O'),
                name='gl_leito_um_atendimento_ativo'),
        ]

    def __str__(self):
        paciente = (self.atendimento.pessoa.nome
                    if self.atendimento_id else '?')
        return (f'{self.leito} — {paciente} '
                f'({self.get_situacao_display()})')

    @property
    def paciente(self):
        return self.atendimento.pessoa if self.atendimento_id else None

    @property
    def ativa(self):
        return self.dt_saida is None and self.status == 'A'

    @property
    def dias_internado(self):
        base = (self.dt_saida or timezone.now())
        return (base - self.dt_entrada).days if self.dt_entrada else 0

    # ------------------------------------------------------------------
    def clean(self):
        erros = {}
        leito = self.leito if self.leito_id else None
        if leito is None:
            erros['leito'] = 'Informe o leito.'
        else:
            local = leito.local if leito.local_id else None
            if local is None or not local.setor_id or \
                    not local.setor.ala.internacao:
                erros['leito'] = (
                    'O leito deve pertencer a um local de ala de '
                    'internação.')
        if self.atendimento_id:
            atendimento = self.atendimento
            if self.estabelecimento_id and \
                    atendimento.estabelecimento_id != self.estabelecimento_id:
                erros['atendimento'] = (
                    'O atendimento não pertence ao estabelecimento '
                    'selecionado.')
            if atendimento.dt_alta and self.dt_saida is None:
                erros['atendimento'] = (
                    'O atendimento já teve ALTA: registre a data de saída '
                    'do leito.')
        if self.dt_entrada and self.dt_saida and \
                self.dt_saida < self.dt_entrada:
            erros['dt_saida'] = (
                'A data de saída deve ser posterior à entrada.')
        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        # Ocupação ativa marca a flag do leito; saída desmarca.
        if self.leito_id and self.status == 'A':
            nova_flag = self.dt_saida is None and self.situacao == 'O'
            if self.leito.ocupado != nova_flag:
                Leito.objects.filter(pk=self.leito_id).update(
                    ocupado=nova_flag)
        self.full_clean()
        return super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    def _historico(self, operacao, usuario, descricao):
        HistoricoLeito.objects.create(
            gestao=self, operacao=operacao, usuario=usuario,
            descricao=descricao)

    def registrar_saida(self, usuario, dt_saida=None, observacoes=''):
        if self.dt_saida is not None:
            raise ValidationError(
                {'dt_saida': 'Este leito já teve saída registrada.'})
        self.dt_saida = dt_saida or timezone.now()
        self.situacao = 'L'
        self.us_atualizacao = usuario
        self.dt_atualizacao = timezone.now()
        if observacoes:
            self.observacoes = ((self.observacoes + ' | ' if self.observacoes
                                 else '') + observacoes)
        self.save(update_fields=[
            'dt_saida', 'situacao', 'observacoes', 'us_atualizacao',
            'dt_atualizacao'])
        self._historico(
            'saida', usuario,
            f'Saída registrada em '
            f'{timezone.localtime(self.dt_saida):%d/%m/%Y %H:%M}; leito '
            f'liberado. {observacoes}'.strip())
        return self

    def mudar_status(self, usuario, situacao, observacoes=''):
        self.situacao = situacao
        self.us_atualizacao = usuario
        self.dt_atualizacao = timezone.now()
        if observacoes:
            self.observacoes = ((self.observacoes + ' | ' if self.observacoes
                                 else '') + observacoes)
        self.save(update_fields=['situacao', 'observacoes',
                                 'us_atualizacao', 'dt_atualizacao'])
        self._historico(
            'status', usuario,
            f'Situação alterada para "{self.get_situacao_display()}". '
            f'{observacoes}'.strip())
        return self


class ParametrosGestaoLeitos(models.Model):
    """Liberação por usuário OU grupo (padrão de ParametrosAgenda)."""

    estabelecimento = models.OneToOneField(
        Estabelecimento, on_delete=models.CASCADE,
        verbose_name='Estabelecimento')
    usuarios_visualizacao = models.ManyToManyField(
        User, blank=True, related_name='gl_visualizacao',
        verbose_name='Podem Visualizar')
    usuarios_edicao = models.ManyToManyField(
        User, blank=True, related_name='gl_edicao',
        verbose_name='Podem Editar')
    usuarios_exclusao = models.ManyToManyField(
        User, blank=True, related_name='gl_exclusao',
        verbose_name='Podem Excluir')
    grupos_visualizacao = models.ManyToManyField(
        'auth.Group', blank=True, related_name='gl_grupo_visualizacao',
        verbose_name='Grupos que Podem Visualizar')
    grupos_edicao = models.ManyToManyField(
        'auth.Group', blank=True, related_name='gl_grupo_edicao',
        verbose_name='Grupos que Podem Editar')
    grupos_exclusao = models.ManyToManyField(
        'auth.Group', blank=True, related_name='gl_grupo_exclusao',
        verbose_name='Grupos que Podem Excluir')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status')
    dt_cadastro = models.DateTimeField(
        default=timezone.now, editable=False, verbose_name='Dt.Cadastro')
    usuario_cadastro = models.ForeignKey(
        User, on_delete=models.PROTECT, editable=False,
        related_name='gl_parametros_criados', verbose_name='Us.Cadastro')

    class Meta:
        verbose_name = 'Parâmetros da Gestão de Leitos'
        verbose_name_plural = '3. Parâmetros da Gestão de Leitos'

    def __str__(self):
        return f'Parâmetros da Gestão de Leitos - {self.estabelecimento}'

    @classmethod
    def pode(cls, usuario, estabelecimento, acao):
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
        return usuario.groups.filter(
            pk__in=getattr(parametros, campo_grupos)
            .values_list('pk', flat=True)).exists()
