"""TESOURARIA — Caixas (espelho do módulo bancário do financeiro).

Fluxo:
 1. Controle de Caixa   — o caixa físico (por estabelecimento/usuario).
 2. Competência Caixa   — período do caixa (aberta → fechada).
 3. Movimentos Caixa    — entradas/saídas do caixa (vendas, baixa de
                          pagamento, sangria/depósito e transferências
                          BANCO ↔ CAIXA).

Regra de ouro: toda transferência gera DOIS lançamentos — a saída de um lado
e a entrada do outro (caixa→banco = depósito; banco→caixa = saque).
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from django.contrib.auth.models import User
from admin_cadastros.models import Estabelecimento
from admin_cadastros_financeiros.models import TransacaoFinanceira
from dominios.choices import status_choices


class ControleCaixa(models.Model):
    """O CAIXA físico do estabelecimento (ex.: Caixa Recepção, Caixa Loja).

    Um caixa pertence a um estabelecimento e pode ter um USUÁRIO responsável
    (o operador). Cada operador abre a SUA competência de caixa.
    """

    descricao = models.CharField(
        max_length=100, verbose_name='Caixa',
        help_text='Ex.: Caixa Recepção, Caixa Loja')
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT,
        verbose_name='Estabelecimento')
    usuario = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True,
        related_name='caixas_operados', verbose_name='Operador',
        help_text='Operador responsável por este caixa (opcional).')
    us_registro = models.ForeignKey(
        User, related_name='caixa_registro', on_delete=models.PROTECT,
        verbose_name='Us.Registro')
    dt_registro = models.DateTimeField(
        default=timezone.now, editable=False, verbose_name='Dt.Registro')
    us_atualizacao = models.ForeignKey(
        User, related_name='caixa_atualizacao', on_delete=models.PROTECT,
        blank=True, null=True, verbose_name='Us.Atualização')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A',
        verbose_name='Status')

    class Meta:
        verbose_name = 'Controle de Caixa'
        verbose_name_plural = '1. Controles de Caixa'
        ordering = ['descricao']
        constraints = [
            models.UniqueConstraint(
                fields=['descricao', 'estabelecimento'],
                name='caixa_unico_por_estabelecimento'),
        ]

    def __str__(self):
        nome = self.descricao
        if self.usuario_id:
            nome += f' — {self.usuario.get_full_name() or self.usuario}'
        return f'{nome} ({self.estabelecimento})'


class CompetenciaCaixa(models.Model):
    """Período ABERTO do caixa (um aberto por caixa)."""

    controle_caixa = models.ForeignKey(
        ControleCaixa, on_delete=models.PROTECT,
        related_name='competencias', verbose_name='Caixa')
    descricao = models.CharField(
        max_length=100, verbose_name='Descrição',
        help_text='Ex.: JANEIRO/2024 - Turno manhã')
    dt_abertura = models.DateField(verbose_name='Dt. Abertura')
    dt_fechamento = models.DateField(
        blank=True, null=True, verbose_name='Dt. Fechamento')
    saldo_inicial = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Saldo Inicial',
        help_text='Dinheiro em caixa no momento da abertura (fundo de '
                  'troco).')
    saldo_anterior = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Saldo Anterior',
        help_text='Saldo final herdado da competência anterior do caixa.')
    saldo_atual = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, editable=False,
        verbose_name='Saldo Atual')
    observacao = models.CharField(
        max_length=255, blank=True, null=True, verbose_name='Observação')
    us_registro = models.ForeignKey(
        User, related_name='comp_caixa_registro', on_delete=models.PROTECT,
        verbose_name='Us.Registro')
    dt_registro = models.DateTimeField(
        default=timezone.now, editable=False)
    us_atualizacao = models.ForeignKey(
        User, related_name='comp_caixa_atualizacao', on_delete=models.PROTECT,
        blank=True, null=True, verbose_name='Us.Atualização')
    dt_atualizacao = models.DateTimeField(blank=True, null=True, default=None)
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT)
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    class Meta:
        verbose_name = 'Competência de Caixa'
        verbose_name_plural = '2. Competências de Caixa'
        ordering = ['-dt_abertura']

    def __str__(self):
        situacao = ('Fechada' if self.dt_fechamento else 'Aberta')
        return (f'{self.controle_caixa.descricao} — {self.descricao} '
                f'({situacao})')

    # ------------------------------------------------------------------
    @property
    def fechada(self):
        return self.dt_fechamento is not None

    def recalcular_saldos(self):
        """saldo_atual = saldo_inicial + Σ entradas − Σ saídas."""
        agg = self.movimentocaixa_set.aggregate(
            entradas=Sum('valor_entrada'), saidas=Sum('valor_saida'))
        self.saldo_atual = ((self.saldo_inicial or 0)
                            + (agg['entradas'] or 0) - (agg['saidas'] or 0))
        self.save(update_fields=['saldo_atual'])

    @property
    def total_entradas(self):
        return self.movimentocaixa_set.aggregate(
            s=Sum('valor_entrada'))['s'] or 0

    @property
    def total_saidas(self):
        return self.movimentocaixa_set.aggregate(
            s=Sum('valor_saida'))['s'] or 0

    @property
    def conciliada(self):
        """Conciliação de caixa finalizada (conferência do dinheiro)."""
        return getattr(self, 'conciliacao', None) is not None \
            and self.conciliacao.finalizada

    def validar_periodo(self, dt):
        if dt is None:
            return True
        if self.dt_abertura and dt < self.dt_abertura:
            return False
        return dt <= (self.dt_fechamento or timezone.localdate())

    def anexar_saldo_anterior(self):
        """Herda o saldo final da última competência FECHADA do caixa."""
        anterior = CompetenciaCaixa.objects.filter(
            controle_caixa_id=self.controle_caixa_id,
            dt_fechamento__isnull=False,
        ).exclude(pk=self.pk).order_by('-dt_fechamento').first()
        if anterior is not None and self.saldo_anterior in (None, 0):
            self.saldo_anterior = anterior.saldo_atual
        return anterior

    def fechar(self, user, dt_fechamento=None):
        """Fecha o caixa: exige a conferência de caixa finalizada."""
        if self.fechada:
            raise ValueError('Esta competência de caixa já está fechada.')
        if not self.conciliada:
            raise ValueError(
                'A CONFERÊNCIA DE CAIXA precisa ser finalizada (informar o '
                'dinheiro contado) antes de fechar. Use “Conferir caixa”.')
        if (self.saldo_atual or 0) < 0:
            raise ValueError(
                'O saldo do caixa está NEGATIVO (R$ {0}). Corrija os '
                'lançamentos antes de fechar.'.format(self.saldo_atual))
        self.dt_fechamento = dt_fechamento or timezone.localdate()
        self.us_atualizacao = user
        self.dt_atualizacao = timezone.now()
        self.save(update_fields=['dt_fechamento', 'us_atualizacao',
                                 'dt_atualizacao'])

    def clean(self):
        # Um caixa aberto por vez.
        if not self.dt_fechamento and self.controle_caixa_id:
            abertas = CompetenciaCaixa.objects.filter(
                controle_caixa_id=self.controle_caixa_id,
                dt_fechamento__isnull=True,
            ).exclude(pk=self.pk)
            if abertas.exists():
                raise ValidationError(
                    'Já existe a competência de caixa "%s" ABERTA para este '
                    'caixa. Feche-a antes de abrir outra.'
                    % abertas.first().descricao)


class ConferenciaCaixa(models.Model):
    """Conferência (fechamento de caixa): dinheiro CONTADO × esperado.

    É o equivalente da conciliação bancária no caixa: a diferença entre o
    valor contado e o saldo do sistema é a quebra/sobra de caixa.
    """

    competencia_caixa = models.OneToOneField(
        CompetenciaCaixa, on_delete=models.PROTECT,
        related_name='conciliacao', verbose_name='Competência Caixa')
    valor_sistema = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name='Valor no sistema')
    valor_contado = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name='Valor contado')
    diferenca = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Diferença (sobra/quebra)')
    observacao = models.CharField(
        max_length=255, blank=True, null=True, verbose_name='Observação',
        help_text='Explique a diferença, se houver (ex.: falta de troco).')
    finalizada = models.BooleanField(default=False)
    dt_conferencia = models.DateTimeField(
        default=timezone.now, editable=False)
    us_registro = models.ForeignKey(
        User, related_name='conferencias_caixa', on_delete=models.PROTECT,
        verbose_name='Us.Registro')

    class Meta:
        verbose_name = 'Conferência de Caixa'
        verbose_name_plural = '4. Conferências de Caixa'

    def __str__(self):
        return (f'Conferência {self.competencia_caixa} — '
                f'{"Finalizada" if self.finalizada else "Em andamento"}')

    def save(self, *args, **kwargs):
        self.diferenca = (self.valor_contado or 0) - (self.valor_sistema or 0)
        super().save(*args, **kwargs)


class MovimentoCaixa(models.Model):
    """Lançamento do caixa (entrada ou saída)."""

    TIPOS = [
        ('E', 'Entrada'),
        ('S', 'Saída'),
        # TRANSFERÊNCIA para o banco: o dinheiro SAI do caixa (é uma saída) e
        # o sistema lança a ENTRADA no banco. Fica como tipo próprio para o
        # operador identificar a transferência na listagem.
        ('D', 'Depósito em Banco'),
    ]
    # Tipos que SAEM do caixa (S normal e D transferência).
    TIPOS_SAIDA = ('S', 'D')
    # Origem x tipo: depósito só com o tipo próprio; saque só entra (par do
    # saque lançado no banco); os demais aceitam E/S.
    ORIGENS = [
        ('pagamento', 'Baixa de pagamento'),
        ('recebimento', 'Recebimento avulso'),
        ('deposito_banco', 'Depósito em banco (caixa → banco)'),
        ('saque_banco', 'Saque do banco (banco → caixa)'),
        ('troco', 'Fundo de troco'),
        ('ajuste', 'Ajuste/estorno'),
    ]

    competencia_caixa = models.ForeignKey(
        CompetenciaCaixa, on_delete=models.PROTECT,
        related_name='movimentocaixa_set', verbose_name='Competência Caixa')
    dt_movimento = models.DateField(
        default=timezone.localdate, verbose_name='Dt. Movimento')
    tipo = models.CharField(max_length=1, choices=TIPOS, verbose_name='Tipo',
                            help_text='Entrada = dinheiro que entra; Saída = '
                                      'dinheiro que sai; Depósito em Banco = '
                                      'sai do caixa e entra no banco.')
    origem = models.CharField(
        max_length=20, choices=ORIGENS, default='recebimento',
        verbose_name='Origem')
    valor_entrada = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True,
        verbose_name='Valor Entrada')
    valor_saida = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True,
        verbose_name='Valor Saída')
    transacao_financeira = models.ForeignKey(
        TransacaoFinanceira, on_delete=models.PROTECT,
        verbose_name='Transação Financeira',
        help_text='Somente transações que movimentam CAIXA.')
    observacao = models.CharField(
        max_length=255, blank=True, null=True, verbose_name='Observação')
    documento = models.CharField(
        max_length=60, blank=True, null=True,
        verbose_name='Documento/Comprovante')

    # Vínculo com o BANCO na transferência (caixa ⇄ banco).
    competencia_bancaria = models.ForeignKey(
        'admin_financeiro.CompetenciaBancaria', on_delete=models.PROTECT,
        blank=True, null=True, verbose_name='Competência Bancária')
    # Movimento do outro lado da transferência (para exibição/rastreio).
    transferencia_id = models.CharField(
        max_length=36, blank=True, null=True, editable=False,
        verbose_name='ID da transferência')

    # Vínculo com a baixa de PAGAMENTO que gerou o lançamento.
    pagamento = models.ForeignKey(
        'admin_pagamentos.Pagamento', on_delete=models.PROTECT,
        blank=True, null=True, related_name='movimentos_caixa',
        verbose_name='Pagamento')

    us_registro = models.ForeignKey(
        User, related_name='mov_caixa_registro', on_delete=models.PROTECT,
        verbose_name='Us.Registro')
    dt_registro = models.DateTimeField(default=timezone.now, editable=False)
    us_atualizacao = models.ForeignKey(
        User, related_name='mov_caixa_atualizacao', on_delete=models.PROTECT,
        blank=True, null=True, verbose_name='Us.Atualização')
    dt_atualizacao = models.DateTimeField(blank=True, null=True, default=None)
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT)
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    class Meta:
        verbose_name = 'Movimento de Caixa'
        verbose_name_plural = '3. Movimentos de Caixa'
        ordering = ['-dt_movimento', '-pk']

    def __str__(self):
        sinal = 'E' if (self.valor_entrada or 0) else 'S'
        valor = self.valor_entrada or self.valor_saida or 0
        return (f'{self.dt_movimento} {sinal} R$ {valor} '
                f'- {self.get_origem_display()}')

    # ------------------------------------------------------------------
    def valor(self):
        return (self.valor_entrada or 0) - (self.valor_saida or 0)
    valor.short_description = 'Valor'

    # Lançamento que o SISTEMA cria (par de uma transferência do outro app):
    # não passa pelas regras de "onde deve ser digitado".
    _estado_automatico = False

    def _fk_segura(self, nome):
        """Objeto da FK ou None.

        No `full_clean` do ModelForm (`_post_clean`) a instância é montada
        parcialmente: uma FK não preenchida faz `self.<campo>` levantar
        `RelatedObjectDoesNotExist` em vez de devolver None. Lê pelo id.
        """
        from django.core.exceptions import ObjectDoesNotExist
        try:
            return getattr(self, nome)
        except ObjectDoesNotExist:
            return None

    def clean(self):
        """Validação do lançamento (tipo, valores, período e banco)."""
        from django.core.exceptions import ValidationError as VE
        erros = {}
        # 1) exatamente UM dos valores positivo
        ent = self.valor_entrada or 0
        sai = self.valor_saida or 0
        if ent < 0 or sai < 0:
            erros['valor_entrada'] = 'Valores não podem ser negativos.'
        if (ent > 0) == (sai > 0):
            erros['valor_entrada'] = (
                'Informe APENAS um valor: entrada OU saída.')
        # 2) o TIPO tem de casar com o valor. `D` (Depósito em Banco) é uma
        #    SAÍDA do caixa; `E` exige valor de entrada.
        if ent > 0:
            if self.tipo not in ('E', 'D'):
                erros['tipo'] = 'Valor de ENTRADA exige o tipo “Entrada”.'
            elif self.tipo == 'D':
                erros['tipo'] = ('Depósito em banco é SAÍDA do caixa: informe o '
                                 'VALOR DE SAÍDA.')
        else:
            if self.tipo not in ('S', 'D'):
                erros['tipo'] = 'Valor de SAÍDA exige o tipo “Saída”.'
        # O tipo D só vale para a origem de transferência.
        if self.tipo == 'D' and self.origem != 'deposito_banco':
            erros['origem'] = ('O tipo “Depósito em Banco” exige a origem '
                               '“Depósito em banco (caixa → banco)”.')
        # 3) competência aberta e data no período
        comp = self._fk_segura('competencia_caixa')
        if comp is None:
            erros['competencia_caixa'] = 'Competência de caixa obrigatória.'
        else:
            if comp.dt_fechamento:
                erros['competencia_caixa'] = (
                    f'O caixa "{comp}" está FECHADO: não aceita lançamentos.')
            if not comp.validar_periodo(self.dt_movimento):
                erros['dt_movimento'] = (
                    f'A data está fora do período da competência de caixa '
                    f'(aberta em {comp.dt_abertura:%d/%m/%Y}).')
        # 4) transação financeira precisa MOVIMENTAR CAIXA
        transacao = self._fk_segura('transacao_financeira')
        if transacao is None and self.transacao_financeira_id:
            transacao = self._fk_segura('transacao_financeira')
        if transacao is None:
            erros['transacao_financeira'] = 'Transação financeira é obrigatória.'
        if transacao is not None and not _transacao_movimenta_caixa(transacao):
            erros['transacao_financeira'] = (
                'Escolha uma transação que MOVIMENTE CAIXA (ou de '
                'DEPÓSITO BANCÁRIO, que movimenta caixa e banco).')
        # 4b) a ORIGEM do movimento tem de casar com o MOVIMENTO da transação.
        #
        # REGRA DO SENTIDO: a transferência é lançada no lado de ORIGEM do
        # dinheiro e o sistema cria o lado de destino.
        #   • depósito (caixa → banco): lança no CAIXA (saída) e entra no banco;
        #   • saque (banco → caixa):    lança no BANCO (saída) e entra no caixa.
        # Por isso o CAIXA só aceita `deposito` como transferência digitada; o
        # `saque_banco` que aparece aqui é o par criado automaticamente.
        if transacao is not None:
            mov = (getattr(transacao, 'movimento', '') or '').lower()
            if mov == 'saque' and self.origem == 'saque_banco' and not \
                    self._estado_automatico:
                erros['origem'] = (
                    'SAQUE BANCÁRIO deve ser lançado no BANCO (é lá que o '
                    'dinheiro sai). O sistema cria a entrada neste caixa auto'
                    'maticamente.')
            elif mov == 'deposito' and self.origem != 'deposito_banco':
                erros['origem'] = (
                    'A transação é de DEPÓSITO BANCÁRIO (caixa → banco): '
                    'selecione a origem “Depósito em banco”.')
            elif self.origem in ('deposito_banco', 'saque_banco') and \
                    mov not in ('deposito', 'saque'):
                erros['transacao_financeira'] = (
                    'Para transferência escolha uma transação cadastrada como '
                    '“Depósito Bancário (Caixa → Banco)” ou '
                    '“Saque Bancário (Banco → Caixa)”.')
        # 5) transferência com banco exige competência bancária ABERTA
        if self.origem in ('deposito_banco', 'saque_banco'):
            banco = self._fk_segura('competencia_bancaria')
            if banco is None:
                erros['competencia_bancaria'] = (
                    'Informe a COMPETÊNCIA BANCÁRIA de destino/origem.')
            elif banco.dt_fechamento_competencia:
                erros['competencia_bancaria'] = (
                    f'A competência bancária "{banco.descricao}" está FECHADA; '
                    'escolha uma ABERTA.')
            # Depósito: tipo 'S' ou o próprio 'D' (Depósito em Banco).
            # Saque: o caixa só recebe a entrada (par automático) → tipo 'E'.
            if self.origem == 'deposito_banco':
                permitidos = ('S', 'D')
            else:
                permitidos = ('E',)
            if self.tipo and self.tipo not in permitidos:
                rotulo = ' ou '.join(dict(self.TIPOS)[t] for t in permitidos)
                erros['tipo'] = (
                    'Depósito em banco sai do CAIXA; saque do banco entra no '
                    f'CAIXA. Para esta origem use o tipo “{rotulo}”.')
        if erros:
            raise VE(erros)

    def save(self, *args, **kwargs):
        if self.competencia_caixa_id:
            self.estabelecimento = (self.competencia_caixa.controle_caixa
                                    .estabelecimento)
            if self.dt_movimento is None:
                self.dt_movimento = timezone.localdate()
        # O par criado AUTOMATICAMENTE pelo banco (entrada do saque) é aceito
        # mesmo vindo de uma transação de 'saque'.
        object.__setattr__(self, '_estado_automatico',
                           bool(kwargs.pop('_automatico', False)))
        self.clean()
        super().save(*args, **kwargs)
        self.competencia_caixa.recalcular_saldos()
        # Transferência caixa ⇄ banco: lança o OUTRO lado.
        if self.origem in ('deposito_banco', 'saque_banco'):
            _sincronizar_banco(self)

    def delete(self, *args, **kwargs):
        competencia = self.competencia_caixa
        # Apaga também o OUTRO lado da transferência (caixa ⇄ banco).
        if self.transferencia_id:
            from admin_financeiro.models import MovimentoBancario
            MovimentoBancario.objects.filter(
                transferencia_id=self.transferencia_id).delete()
        super().delete(*args, **kwargs)
        competencia.recalcular_saldos()


def _transacao_movimenta_caixa(transacao):
    """A transação pode ser usada em um movimento de CAIXA?

    Vale para `movimento='caixa'` (caixa puro) e também para as
    TRANSFERÊNCIAS `deposito` (caixa → banco, saída do caixa) e `saque`
    (banco → caixa, entrada no caixa) — nesses casos o lado BANCO é gerado
    automaticamente e usa a mesma transação.
    """
    movimento = (getattr(transacao, 'movimento', '') or '').lower()
    return movimento in ('caixa', 'deposito', 'saque')


def _transacao_movimenta_banco(transacao):
    movimento = (getattr(transacao, 'movimento', '') or '').lower()
    return movimento in ('banco', 'deposito', 'saque')


def _sincronizar_banco(movimento_caixa):
    """Cria/atualiza o lançamento do lado BANCO da transferência.

    O sentido vem do `origem` do movimento:

    - `deposito_banco` (caixa → banco): a SAÍDA é no caixa; no banco entra
      dinheiro → gera **ENTRADA** no banco.
    - `saque_banco` (banco → caixa): a SAÍDA é no banco; o caixa recebe a
      ENTRADA automaticamente → gera **SAÍDA** no banco.

    O par compartilha `transferencia_id` (excluir um apaga o outro).
    """
    from admin_financeiro.models import MovimentoBancario
    from uuid import uuid4

    banco = movimento_caixa.competencia_bancaria
    if banco is None:
        return
    if not movimento_caixa.transferencia_id:
        movimento_caixa.transferencia_id = str(uuid4())
        MovimentoCaixa.objects.filter(pk=movimento_caixa.pk).update(
            transferencia_id=movimento_caixa.transferencia_id)
    deposito = movimento_caixa.origem == 'deposito_banco'
    valor = movimento_caixa.valor_entrada or movimento_caixa.valor_saida
    descricao = (
        f'{"Depósito Bancário" if deposito else "Saque Bancário"} '
        f'({movimento_caixa.competencia_caixa.controle_caixa.descricao})')
    # Já existe o par desta transferência?
    existente = MovimentoBancario.objects.filter(
        transferencia_id=movimento_caixa.transferencia_id).first()
    dados = dict(
        competencia_bancaria=banco,
        transacao_financeira=movimento_caixa.transacao_financeira,
        dt_movimento=movimento_caixa.dt_movimento,
        # Depósito: entra no banco. Saque: sai do banco.
        valor_entrada=valor if deposito else None,
        valor_saida=None if deposito else valor,
        observacao=descricao[:250],
        origem=descricao[:250],
        us_registro_id=movimento_caixa.us_registro_id,
        estabelecimento=banco.estabelecimento,
        status='A',
        transferencia_id=movimento_caixa.transferencia_id,
    )
    # `_automatico=True`: este é o PAR da transferência — não pode gerar de
    # volta o lançamento do caixa (loop infinito).
    if existente is not None:
        for campo, val in dados.items():
            setattr(existente, campo, val)
        existente.save(_automatico=True)
    else:
        MovimentoBancario(**dados).save(_automatico=True)
