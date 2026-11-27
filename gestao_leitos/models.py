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
    """Histórico de auditoria do leito — nunca é apagado."""

    gestao = models.ForeignKey(
        'GestaoLeito', on_delete=models.CASCADE, related_name='historico',
        verbose_name='Leito')
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


class MovimentoLeito(models.Model):
    """MOVIMENTAÇÃO do leito (tabela auxiliar, nunca apagada).

    Cada operação vira UMA linha aqui: ocupação, saída/alta, transferência,
    bloqueio, higienização, reocupação... A listagem/mapa mostra o estado
    ATUAL (uma linha por leito em GestaoLeito); os movimentos ficam no
    detalhe/edição do leito.
    """

    leito = models.ForeignKey(
        Leito, on_delete=models.PROTECT, related_name='movimentos',
        verbose_name='Leito')
    atendimento = models.ForeignKey(
        Atendimento, on_delete=models.PROTECT, related_name='movimentos_leito',
        blank=True, null=True, verbose_name='Atendimento',
        help_text='Preenchido nos movimentos com paciente (ocupação).')
    operacao = models.CharField(
        max_length=20, choices=HISTORICO_OPERACOES, verbose_name='Operação')
    situacao = models.CharField(
        max_length=1, choices=GESTAO_STATUS, verbose_name='Situação resultante')
    dt_movimento = models.DateTimeField(
        default=timezone.now, editable=False, verbose_name='Dt. Movimento')
    observacoes = models.CharField(
        max_length=255, blank=True, null=True, verbose_name='Observações')
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT,
        verbose_name='Estabelecimento')
    usuario = models.ForeignKey(
        User, on_delete=models.PROTECT, editable=False,
        related_name='gl_movimentos', verbose_name='Usuário')

    class Meta:
        verbose_name = 'Movimento de Leito'
        verbose_name_plural = '4. Movimentos de Leitos'
        ordering = ('-dt_movimento',)

    def __str__(self):
        paciente = (self.atendimento.pessoa.nome
                    if self.atendimento_id else 'sem paciente')
        return (f'{self.get_operacao_display()} — {self.leito} — {paciente}')


class GestaoLeito(models.Model):
    """ESTADO ATUAL de um leito — UMA linha por leito (unique no leito).

    Nunca há duas linhas na listagem para o mesmo leito: a reocupação, a
    saída, o bloqueio etc. ATUALIZAM esta linha e geram MovimentoLeito (a
    movimentação fica no detalhe/edição).
    """

    leito = models.OneToOneField(
        Leito, on_delete=models.PROTECT, related_name='gestao',
        verbose_name='Leito')
    atendimento = models.ForeignKey(
        Atendimento, on_delete=models.PROTECT, related_name='ocupacoes_leito',
        blank=True, null=True, verbose_name='Atendimento',
        help_text='Somente quando a situação for OCUPADO; livre, bloqueado e '
                  'higienização operam o leito sem paciente.')
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
            # NOTA: as unicidades "um leito ativo por atendimento" e "um
            # atendimento ativo por leito" são garantidas no `clean()`/views
            # (o SQLite não recria partial UNIQUE indexes em ALTER e mantinha
            # a versão antiga sem `atendimento_id IS NOT NULL`, bloqueando
            # ocupações operacionais sem atendimento).
        ]

    def __str__(self):
        paciente = (self.atendimento.pessoa.nome
                    if self.atendimento_id else 'sem atendimento')
        return (f'{self.leito} — {paciente} '
                f'({self.get_situacao_display()})')

    @property
    def paciente(self):
        return self.atendimento.pessoa if self.atendimento_id else None

    @property
    def ativa(self):
        return self.dt_saida is None and self.status == 'A'

    @property
    def ocupada(self):
        """Ocupada por um paciente (situacao O COM atendimento)."""
        return self.situacao == 'O' and self.atendimento_id is not None

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
        # NOTA: “UMA linha por leito” é garantida pela OneToOneField no BANCO
        # e pela tela (o form_valid ATUALIZA a linha existente em vez de
        # criar outra); não pode estar no clean(), senão a reocupação — que
        # é exatamente atualizar a linha do leito — seria sempre recusada.
        # Um atendimento só em UM leito.
        if self.atendimento_id and self.situacao == 'O' and \
                self.dt_saida is None and self.status == 'A':
            if GestaoLeito.objects.filter(
                    atendimento_id=self.atendimento_id,
                    dt_saida__isnull=True, status='A'
            ).exclude(pk=self.pk).exclude(leito_id=self.leito_id).exists():
                erros['atendimento'] = (
                    'Este atendimento já está em outro leito (use Trocar '
                    'leito).')
        if self.atendimento_id:
            atendimento = self.atendimento
            if self.estabelecimento_id and \
                    atendimento.estabelecimento_id != self.estabelecimento_id:
                erros['atendimento'] = (
                    'O atendimento não pertence ao estabelecimento '
                    'selecionado.')
            # NÃO recusar atendimento com ALTA: registrar a saída do leito é
            # exatamente o registro que acompanha a alta (a saída libera o
            # leito e o atendimento).
            # NÃO recusar atendimento em situações L/B/H: essas transições
            # LIBERAM o atendimento (a saída fica registrada no histórico
            # com o atendimento que estava no leito). O atendimento é
            # obrigatório apenas na OCUPAÇÃO sem saída (ver abaixo).
            if self.situacao == 'O' and self.dt_saida is None and \
                    not self.atendimento_id:
                erros['atendimento'] = (
                    'Para ocupar o leito, informe o atendimento do paciente.')
        if self.dt_entrada and self.dt_saida and \
                self.dt_saida.replace(second=0, microsecond=0) < \
                self.dt_entrada.replace(second=0, microsecond=0):
            erros['dt_saida'] = (
                'A data de saída deve ser igual ou posterior à entrada.')
        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        # Ocupação ativa marca a flag do leito; saída desmarca.
        if self.leito_id and self.status == 'A':
            nova_flag = (self.dt_saida is None and self.situacao == 'O'
                         and self.atendimento_id is not None)
            # Lê a flag DO BANCO (o cache do objeto pode estar velho).
            ocupado_atual = Leito.objects.filter(
                pk=self.leito_id).values_list('ocupado', flat=True).first()
            if ocupado_atual != nova_flag:
                Leito.objects.filter(pk=self.leito_id).update(
                    ocupado=nova_flag)
        # Validações de regra SEM `validate_constraints` (o full_clean do
        # Django avalia as UniqueConstraints condicionais mal no SQLite;
        # a proteção real fica no BANCO, no INSERT/UPDATE).
        try:
            self.clean()
        except ValidationError:
            raise
        return super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    def _historico(self, operacao, usuario, descricao):
        HistoricoLeito.objects.create(
            gestao=self, operacao=operacao, usuario=usuario,
            descricao=descricao)

    def _movimento(self, operacao, usuario, observacoes='', situacao=None,
                   atendimento_id=None):
        """Registra o MOVIMENTO do leito (tabela auxiliar, nunca apagada).

        `atendimento_id` é o atendimento ENVOLVIDO no movimento (ex.: o que
        estava no leito na saída) — não é o estado atual da linha.
        """
        MovimentoLeito.objects.create(
            leito=self.leito,
            atendimento_id=atendimento_id or self.atendimento_id,
            operacao=operacao,
            situacao=situacao or self.situacao,
            observacoes=observacoes or '',
            estabelecimento=self.estabelecimento,
            usuario=usuario)

    def registrar_saida(self, usuario, dt_saida=None, observacoes=''):
        if self.dt_saida is not None:
            raise ValidationError(
                {'dt_saida': 'Este leito já teve saída registrada.'})
        # O atendimento SAI da FK da linha (o movimento/histórico guardam
        # quem estava no leito) — é isso que permite realocar outro paciente
        # no leito depois.
        atendimento_id = self.atendimento_id
        self.atendimento = None
        self.dt_saida = dt_saida or timezone.now()
        self.situacao = 'L'
        self.us_atualizacao = usuario
        self.dt_atualizacao = timezone.now()
        if observacoes:
            self.observacoes = ((self.observacoes + ' | ' if self.observacoes
                                 else '') + observacoes)
        self.save(update_fields=[
            'atendimento', 'dt_saida', 'situacao', 'observacoes',
            'us_atualizacao', 'dt_atualizacao'])
        # O movimento guarda o atendimento que estava no leito.
        self._movimento('saida', usuario, observacoes,
                        atendimento_id=atendimento_id)
        self._historico(
            'saida', usuario,
            f'Saída registrada em '
            f'{timezone.localtime(self.dt_saida):%d/%m/%Y %H:%M}; leito '
            f'liberado. {observacoes}'.strip())
        return self

    def reocupar(self, usuario, leito=None, atendimento=None, dt_entrada=None,
                 observacoes=''):
        """REOCUPAÇÃO: atualiza ESTA linha (nunca cria outra para o leito) e
        registra o movimento. `leito` troca o leito (transferência)."""
        if leito is not None and leito != self.leito:
            self.leito = leito
        if atendimento is not None:
            self.atendimento = atendimento
        elif self.dt_saida is not None and self.situacao == 'O':
            pass
        self.dt_entrada = dt_entrada or timezone.now()
        self.dt_saida = None
        self.situacao = 'O'
        self.us_atualizacao = usuario
        self.dt_atualizacao = timezone.now()
        if observacoes:
            self.observacoes = observacoes
        self.save()
        self._movimento('ocupacao', usuario, observacoes)
        paciente = (self.atendimento.pessoa
                    if self.atendimento_id else 'sem paciente')
        self._historico(
            'ocupacao', usuario,
            f'Leito ocupado por {paciente} em '
            f'{timezone.localtime(self.dt_entrada):%d/%m/%Y %H:%M}. '
            f'{observacoes}'.strip())
        return self

    def mudar_status(self, usuario, situacao, observacoes=''):
        """Bloquear/Desbloquear/Higienização.

        Mudar para B/H/L **libera o atendimento** (o leito deixa de estar
        ocupado por um paciente): grava a saída do atendimento com data/hora
        de agora e preserva o histórico. Voltar para O não é permitido aqui
        (ocupar é um registro próprio, com atendimento).
        """
        if situacao == 'O':
            raise ValidationError({
                'situacao': 'Para ocupar o leito use “Registrar Ocupação” '
                            '(com o atendimento do paciente).'})
        liberou = False
        atendimento_id = self.atendimento_id
        if self.situacao == 'O' and self.atendimento_id and \
                self.dt_saida is None:
            # Libera o atendimento: registra a saída dele agora.
            self.dt_saida = timezone.now()
            self.atendimento = None
            liberou = True
        self.situacao = situacao
        self.us_atualizacao = usuario
        self.dt_atualizacao = timezone.now()
        if observacoes:
            self.observacoes = ((self.observacoes + ' | ' if self.observacoes
                                 else '') + observacoes)
        self.save(update_fields=['atendimento', 'situacao', 'dt_saida',
                                 'observacoes', 'us_atualizacao',
                                 'dt_atualizacao'])
        self._movimento('status', usuario, observacoes,
                        atendimento_id=atendimento_id if liberou else None)
        self._historico(
            'status', usuario,
            f'Situação alterada para "{self.get_situacao_display()}".'
            + (' Atendimento liberado do leito.' if liberou else '')
            + f' {observacoes}'.strip())
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
