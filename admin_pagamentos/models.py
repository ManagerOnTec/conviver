from datetime import datetime
from django.db import models
from django.contrib.auth import get_user_model
from django.forms import ValidationError
from admin_cadastros.models import Empresa, Estabelecimento, Pessoa
from admin_cadastros_financeiros.models import Conta, TransacaoFinanceira
from dominios.choices import status_choices, forma_pagamento_choices
from django.utils import timezone
from datetime import timedelta
from django.utils.timezone import now
from django.apps import apps
from django.core.validators import FileExtensionValidator


User = get_user_model()


def _padrao():
    """Estabelecimento de FALLBACK (último recurso).

    Usado só quando o acordo antigo ainda não tem `estabelecimento` e não há
    como derivá-lo do fornecedor: a previsão precisa de UM estabelecimento
    (campo obrigatório) e nunca deve nascer sem vínculo. Em operação normal
    o acordo já vem com o padrão da sessão/perfil.
    """
    return Estabelecimento.objects.filter(status='A').first() \
        or Estabelecimento.objects.first()


class ClassificacaoFornecedor(models.Model):
    descricao = models.CharField(
        max_length=255, verbose_name='Classificacao do Fornecedor')

    observacao = models.CharField(
        max_length=80, verbose_name='Observações', blank=True, null=True
    )

    us_registro = models.ForeignKey(
        User, related_name='us_classefornecedor_registro', on_delete=models.PROTECT)
    dt_registro = models.DateTimeField(default=timezone.now, editable=False)
    us_atualizacao = models.ForeignKey(
        User, related_name='us_classefornecedor_atualizacao', on_delete=models.PROTECT, blank=True, null=True)
    dt_atualizacao = models.DateTimeField(default=None, blank=True, null=True)

    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status')

    class Meta:
        verbose_name = "Classificacao Fornecedor"
        verbose_name_plural = "1. Classificação Fornecedores"

    def __str__(self):
        return self.descricao
    


class ClassePagamento(models.Model):
    """CLASSE de pagamento (antes `ClassificacaoPagamento`).

    Nome curto por decisão de projeto: o rótulo das telas e a FK nos modelos
    do fluxo (`classe_pagamento`) seguem o mesmo nome — sem alias.
    """
    descricao = models.CharField(
        max_length=255, verbose_name='Classe do Pagamento')

    observacao = models.CharField(
        max_length=80, verbose_name='Observações', blank=True, null=True
    )

    us_registro = models.ForeignKey(
        User, related_name='us_classepagto_registro', on_delete=models.PROTECT)
    dt_registro = models.DateTimeField(default=timezone.now, editable=False)
    us_atualizacao = models.ForeignKey(
        User, related_name='us_classepagto_atualizacao', on_delete=models.PROTECT, blank=True, null=True)
    dt_atualizacao = models.DateTimeField(default=None, blank=True, null=True)

    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status')

    class Meta:
        verbose_name = "Classe Pagamento"
        verbose_name_plural = "2. Classes Pagamentos"
        db_table = 'admin_pagamentos_classificacaopagamento'

    def __str__(self):
        return self.descricao





class Fornecedor(models.Model):
    descricao = models.CharField(
        max_length=255, verbose_name='Descrição do Fornecedor')

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE,
                                null=True, blank=True, verbose_name='Pessoa Jurídica')
    pessoa = models.ForeignKey(Pessoa, on_delete=models.CASCADE,
                               null=True, blank=True, verbose_name='Pessoa Física')

    classificacao = models.ForeignKey(
        ClassificacaoFornecedor, on_delete=models.CASCADE, verbose_name='Classificação Fornecedor'
    )

    observacao = models.CharField(max_length=100, blank=True, null=True)

    us_registro = models.ForeignKey(
        User, related_name='us_fornecedor_registro', on_delete=models.PROTECT)
    dt_registro = models.DateTimeField(default=timezone.now, editable=False)
    us_atualizacao = models.ForeignKey(
        User, related_name='us_fornecedor_atualizacao', on_delete=models.PROTECT, blank=True, null=True)
    dt_atualizacao = models.DateTimeField(default=None, blank=True, null=True)

    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status')

    class Meta:
        verbose_name = "Fornecedor"
        verbose_name_plural = "3. Fornecedores"

    def clean(self):
        """A empresa do fornecedor tem de ser do TIPO fornecedor."""
        if self.empresa_id and self.empresa.tipo != 'fornecedor':
            raise ValidationError({
                'empresa': 'A empresa “%s” é do tipo “%s”. Para fornecedor, '
                           'escolha uma empresa do tipo FORNECEDOR '
                           '(cadastre-a em “8. Empresas”).'
                           % (self.empresa, self.empresa.get_tipo_display())
            })
        return super().clean()

    def __str__(self):
        return self.descricao





class AcordoPagamento(models.Model):
    """ACORDO de pagamento (antes `ParametrosPagamentos`).

    Espelha o `AcordoFaturamento` do fluxo de ENTRADA: é o contrato/recorrência
    que GERA as previsões (`PrePagamento`) por competência. O botão
    “Gerar previsões” mora na tela deste acordo.
    """
    RECORRENCIA_CHOICES = [
        ('semanal', 'Semanal'),
        ('quinzenal', 'Quinzenal'),
        ('mensal', 'Mensal'),
        ('anual', 'Anual'),
    ]

    fornecedor = models.ForeignKey(
        Fornecedor, on_delete=models.PROTECT, verbose_name='Fornecedor'
    )
    classe_pagamento = models.ForeignKey(
        ClassePagamento, on_delete=models.PROTECT,
        verbose_name='Classe Pagamento', blank=True, null=True)
    valor_previsto = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Valor Previsto'
    )
    dia_pagamento = models.PositiveIntegerField(
        verbose_name='Dia do Pagamento',
        help_text='Informe o dia do mês (1 a 31) para o pagamento. Para periodicidade semanal/quinzenal, será ignorado.',
        blank=True,
        null=True,
    )
    recorrencia = models.CharField(
        max_length=10,
        choices=RECORRENCIA_CHOICES,
        verbose_name='Recorrência',
        default='mensal'
    )
    data_inicio = models.DateField(
        verbose_name='Início da Recorrência',
        help_text='Data inicial para geração das previsões.'
    )
    data_fim = models.DateField(
        verbose_name='Fim da Recorrência',
        help_text='Data final para geração das previsões. Deixe em branco para recorrência indefinida.',
        blank=True,
        null=True,
    )
    forma_pagamento = models.CharField(
        max_length=1, choices=forma_pagamento_choices, default='A',
        verbose_name='Forma Pagamento')
    # RETENÇÕES (espelho do AcordoFaturamento): percentual aplicado sobre o
    # valor e, depois dele, um valor FIXO abatido. Em branco = não calcula.
    tx_retencao = models.DecimalField(
        max_digits=5, decimal_places=2, verbose_name='Tx. Retenção (%)',
        blank=True, null=True,
        help_text='Percentual descontado do valor a pagar. '
                  'Em branco = sem retenção percentual.')
    vl_retencao = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Vl. Retenção (R$)', blank=True, null=True,
        help_text='Valor FIXO descontado DEPOIS do percentual. '
                  'Em branco = sem retenção fixa.')
    # Marca que as previsões foram geradas (evita gerar duas vezes).
    pre_pago = models.BooleanField(default=False, verbose_name='Pré-Pago')

    # ESTABELECIMENTO do acordo. Era uma `property` derivada do fornecedor;
    # agora é campo PRÓPRIO (FK), preenchido com o estabelecimento padrão da
    # sessão/perfil — a mesma régua do resto do fluxo. O recorte e a grade
    # passam a usar o campo direto (`AdminEstabelecimentoPadraoMixin`).
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT,
        verbose_name='Estabelecimento', blank=True, null=True)

    us_registro = models.ForeignKey(
        User, related_name='parametro_registro', on_delete=models.PROTECT
    )
    dt_registro = models.DateTimeField(default=now, editable=False)
    us_atualizacao = models.ForeignKey(
        User, related_name='parametro_atualizacao', on_delete=models.PROTECT, blank=True, null=True
    )
    dt_atualizacao = models.DateTimeField(default=None, blank=True, null=True)

    observacao = models.CharField(max_length=100, blank=True, null=True)

    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status'
    )

    class Meta:
        verbose_name = 'Acordo de Pagamento'
        verbose_name_plural = '4. Acordos de Pagamento'

    def __str__(self):
        fornecedor = self.fornecedor.descricao if self.fornecedor \
            else 'Fornecedor não definido'
        return f'{fornecedor} - {self.valor_previsto} ({self.recorrencia})'

    # ------------------------------------------------------------------
    # REGRAS (espelho do AcordoFaturamento)
    # ------------------------------------------------------------------
    def save(self, *args, **kwargs):
        """ESTABELECIMENTO: nenhum acordo nasce sem vínculo.

        O form do admin já carrega o padrão da sessão/perfil
        (`AdminEstabelecimentoPadraoMixin`); esta é a rede de segurança para
        o acordo criado FORA do admin (script, shell, fixtures) — que sem
        isso deixaria a previsão sem estabelecimento (campo obrigatório).
        """
        if self.estabelecimento_id is None:
            self.estabelecimento = _padrao()
        return super().save(*args, **kwargs)

    def motivo_recusa_edicao(self):
        if self.pk is None:
            return None
        if self.prepagamentos.exists():
            return (f'O acordo de pagamento “{self}” já gerou PREVISÃO e não '
                    'pode ser alterado. Exclua primeiro a PREVISÃO, em '
                    '“5. Pré-Pagamentos”.')
        return None

    def motivo_recusa_exclusao(self):
        if self.pk is None:
            return None
        if self.prepagamentos.exists():
            return (f'O acordo de pagamento “{self}” já gerou PREVISÃO e não '
                    'pode ser excluído. Exclua primeiro a PREVISÃO, em '
                    '“5. Pré-Pagamentos”.')
        return None

    # ------------------------------------------------------------------
    # RETENÇÕES
    # ------------------------------------------------------------------
    def calcular_retencao(self, valor):
        """Retenção TOTAL sobre `valor` (percentual + fixo).

        Ordem: aplica o PERCENTUAL sobre o valor e, sobre o resultado,
        abate o valor FIXO. Campo em branco não entra no cálculo; sem
        nenhum dos dois a retenção é 0.
        """
        from decimal import Decimal
        valor = Decimal(valor or 0)
        percentual = Decimal(self.tx_retencao or 0) / Decimal('100')
        retencao = (valor * percentual).quantize(Decimal('0.01'))
        fixo = Decimal(self.vl_retencao or 0)
        total = (retencao + fixo).quantize(Decimal('0.01'))
        # Nunca desconta mais do que o valor.
        return min(total, valor)

    def valor_liquido(self, valor):
        """Valor a PAGAR depois das retenções."""
        from decimal import Decimal
        valor = Decimal(valor or 0)
        return (valor - self.calcular_retencao(valor)).quantize(
            Decimal('0.01'))

    def gerar_previsoes(self):
        """Gera as PREVISÕES (`PrePagamento`) da recorrência.

        Devolve o número de previsões CRIADAS. Não gera duas vezes: se já
        houver previsão para a competência, pula.
        """
        from datetime import date as _date  # noqa: F401
        criadas = 0
        data_atual = self.data_inicio
        dia = self.dia_pagamento
        while True:
            if self.data_fim and data_atual > self.data_fim:
                break
            venc = data_atual
            if self.recorrencia == 'mensal' and dia:
                import calendar
                ultimo = calendar.monthrange(venc.year, venc.month)[1]
                venc = venc.replace(day=min(dia, ultimo))
            existe = PrePagamento.objects.filter(
                acordo_pagamento=self, competencia=venc).exists()
            if not existe:
                PrePagamento.objects.create(
                    acordo_pagamento=self,
                    fornecedor=self.fornecedor,
                    classe_pagamento=self.classe_pagamento,
                    valor=self.valor_previsto,
                    competencia=venc,
                    dt_vencimento=venc,
                    forma_pagamento=self.forma_pagamento,
                    # Retenção do ACORDO congelada na previsão (percentual
                    # + valor fixo), como na pré-fatura.
                    tx_retencao=self.tx_retencao,
                    vl_retencao=self.vl_retencao,
                    # ESTABELECIMENTO: o da sessão/perfil quando o acordo
                    # estiver sem vínculo (acordo antigo) — o campo é
                    # obrigatório na previsão.
                    estabelecimento=self.estabelecimento or _padrao(),
                    us_registro=self.us_registro,
                    observacao=f'Previsão gerada do acordo #{self.pk}',
                )
                criadas += 1

            if self.recorrencia == 'semanal':
                data_atual += timedelta(weeks=1)
            elif self.recorrencia == 'quinzenal':
                data_atual += timedelta(weeks=2)
            elif self.recorrencia == 'mensal':
                data_atual += timedelta(days=30)
            elif self.recorrencia == 'anual':
                data_atual = data_atual.replace(year=data_atual.year + 1)
        self.pre_pago = criadas > 0 or self.prepagamentos.exists()
        self.save(update_fields=['pre_pago'])
        return criadas


class PrePagamento(models.Model):
    """PREVISÃO de pagamento (espelho da `PreFatura`).

    Lançamento do acordo para UMA competência. O botão “Gerar pagamento”
    transforma a previsão em `Pagamento` (a obrigação confirmada).
    """
    acordo_pagamento = models.ForeignKey(
        AcordoPagamento, on_delete=models.PROTECT,
        related_name='prepagamentos', blank=True, null=True, verbose_name='Acordo de Pagamento')
    fornecedor = models.ForeignKey(
        Fornecedor, on_delete=models.PROTECT, verbose_name='Fornecedor')
    classe_pagamento = models.ForeignKey(
        ClassePagamento, on_delete=models.PROTECT,
        verbose_name='Classe Pagamento', blank=True, null=True)

    valor = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Valor Previsto')
    competencia = models.DateField(verbose_name='Competência')
    dt_vencimento = models.DateField(verbose_name='Vencimento')
    forma_pagamento = models.CharField(
        max_length=1, choices=forma_pagamento_choices, default='A',
        verbose_name='Forma Pagamento')
    # RETENÇÕES herdadas do acordo no momento da geração (percentual e
    # valor fixo). Em branco = não calcula.
    tx_retencao = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True,
        verbose_name='Tx. Retenção (%)')
    vl_retencao = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True,
        verbose_name='Vl. Retenção (R$)')

    # “PREVISTO/FECHADO”: fechado = já virou Pagamento (quem o controla agora
    # é o Pagamento). Aberto = ainda é a previsão que pode ser editada/
    # excluída.
    previsto_fechado = models.BooleanField(
        default=False, verbose_name='Fechado',
        help_text='Marcado quando a previsão já gerou o PAGAMENTO.')

    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT)
    observacao = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(
        max_length=1, choices=status_choices, default='A',
        verbose_name='Status')

    us_registro = models.ForeignKey(
        User, related_name='prepagamento_registro',
        on_delete=models.PROTECT, null=True)
    dt_registro = models.DateTimeField(default=timezone.now, editable=False)
    us_atualizacao = models.ForeignKey(
        User, related_name='prepagamento_atualizacao',
        on_delete=models.PROTECT, blank=True, null=True)
    dt_atualizacao = models.DateTimeField(
        default=None, blank=True, null=True)

    class Meta:
        verbose_name = 'Pré-Pagamento'
        verbose_name_plural = '5. Pré-Pagamentos'
        ordering = ['-competencia', '-pk']

    def __str__(self):
        return (f'{self.fornecedor} / Competência: '
                f'{self.competencia:%m/%Y} / Valor: {self.valor}')

    def pagamento_gerado(self):
        """O PAGAMENTO gerado por esta previsão (ou None)."""
        if self.pk is None:
            return None
        return Pagamento.objects.filter(prepagamento_ptr_id=self.pk).first()

    # ------------------------------------------------------------------
    # REGRAS (espelho da PreFatura)
    # ------------------------------------------------------------------
    def motivo_recusa_edicao(self):
        """Só edita a previsão enquanto NÃO gerou pagamento."""
        if self.pk is None:
            return None
        pag = self.pagamento_gerado()
        if pag is not None:
            return (f'A previsão {self.pk} já gerou o PAGAMENTO {pag.pk} e '
                    'não pode ser alterada. Exclua primeiro o PAGAMENTO, em '
                    '“6. Pagamentos”.')
        return None

    def motivo_recusa_exclusao(self):
        if self.pk is None:
            return None
        pag = self.pagamento_gerado()
        if pag is not None:
            return (f'A previsão {self.pk} já gerou o PAGAMENTO {pag.pk} e '
                    'não pode ser excluída. Exclua primeiro o PAGAMENTO, em '
                    '“6. Pagamentos”.')
        return None

    def gerar_pagamento(self):
        """Cria o `Pagamento` desta previsão (uma única vez).

        HERANÇA MULTITABLE: a linha pai (`prepagamento`) já existe — só a
        tabela FILHA (`pagamento`) precisa da linha. Criar pelo ORM faria
        INSERT também no pai (e falharia em `valor` NOT NULL). Por isso a
        linha filha é gravada direto pela instância PAI e depois recuperada
        como `Pagamento`.
        """
        if Pagamento.objects.filter(prepagamento_ptr_id=self.pk).exists():
            return None
        # RETENÇÃO: o valor a PAGAR é o bruto já abatido (percentual + fixo).
        valor_liquido = self.valor_liquido()
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                'INSERT INTO admin_pagamentos_pagamento '
                '(prepagamento_ptr_id, valor_pagamento, valor_saldo, '
                ' nota_fiscal, anexo_boleto, dt_liquidacao, finalizado) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s)',
                [self.pk, valor_liquido, valor_liquido, None, None, None,
                 False])
        pagamento = Pagamento.objects.get(pk=self.pk)
        self.previsto_fechado = True
        self.save(update_fields=['previsto_fechado'])
        return pagamento

    # ------------------------------------------------------------------
    # RETENÇÕES (as mesmas do acordo, congeladas na previsão)
    # ------------------------------------------------------------------
    def calcular_retencao(self, valor=None):
        """Retenção TOTAL: percentual sobre `valor`, depois o valor FIXO."""
        from decimal import Decimal
        valor = Decimal(self.valor if valor is None else valor or 0)
        percentual = Decimal(self.tx_retencao or 0) / Decimal('100')
        retencao = (valor * percentual).quantize(Decimal('0.01'))
        fixo = Decimal(self.vl_retencao or 0)
        total = (retencao + fixo).quantize(Decimal('0.01'))
        return min(total, valor)

    def valor_liquido(self, valor=None):
        """Valor a PAGAR depois das retenções (sem retenção = bruto)."""
        from decimal import Decimal
        valor = Decimal(self.valor if valor is None else valor or 0)
        return (valor - self.calcular_retencao(valor)).quantize(
            Decimal('0.01'))
        self.previsto_fechado = True
        self.save(update_fields=['previsto_fechado'])
        return pagamento




class Pagamento(PrePagamento):
    """PAGAMENTO (espelho da `Fatura`): a obrigação CONFIRMADA.

    Herda da `PrePagamento` (multitable: a pk do pagamento é o
    `prepagamento_ptr`). `finalizado=False` → aberto (pode editar/excluir);
    `finalizado=True` → travado, só o botão “Reabrir” destrava.
    """
    valor_pagamento = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Valor Pagamento',
        blank=True, null=True)

    valor_saldo = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Saldo',
        blank=True, null=True, default=0)

    nota_fiscal = models.CharField(
        max_length=10, blank=True, null=True
    )

    # Novos campos para anexos
    anexo_boleto = models.FileField(
        upload_to='pagamentos/boletos/',
        blank=True,
        null=True,
        verbose_name='Anexo Boleto',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'peg'])]
    )

    anexo_nota_fiscal = models.FileField(
        upload_to='pagamentos/notas_fiscais/',
        blank=True,
        null=True,
        verbose_name='Anexo Nota Fiscal',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'peg'])]
    )

    dt_liquidacao = models.DateField(
        null=True, blank=True, verbose_name='Data de Liquidação')

    # FINALIZADO (a trava do fluxo de saída — espelho do `faturado`).
    finalizado = models.BooleanField(
        default=False, verbose_name='Finalizado',
        help_text='Finalizado trava a edição/exclusão do pagamento.')

    class Meta:
        verbose_name = 'Pagamento'
        verbose_name_plural = '6. Pagamentos'

    def save(self, *args, **kwargs):
        # Saldo inicial = valor do pagamento (só na criação).
        # A LINHA PAI já existe (a previsão): só a tabela do pagamento é
        # gravada. Não mexer nos campos herdados aqui — eles vêm do pai.
        super().save(*args, **kwargs)

    def atualizar_saldo(self, valor_pagamento):
        if self.valor_saldo is None:
            self.valor_saldo = self.valor_pagamento or 0
        self.valor_saldo -= valor_pagamento
        if self.valor_saldo <= 0:
            self.dt_liquidacao = timezone.now().date()
        self.save()

    def __str__(self):
        return (f'{self.fornecedor} / Dt.Vencimento: {self.dt_vencimento} / '
                f'Valor: {self.valor_pagamento or self.valor} / '
                f'Saldo: {self.valor_saldo} / Estabelecimento: '
                f'{self.estabelecimento}')

    # ------------------------------------------------------------------
    # BAIXAS (espelho de `Fatura.baixas_registradas`)
    # ------------------------------------------------------------------
    def baixas_registradas(self):
        if self.pk is None:
            return BaixaPagamento.objects.none()
        return BaixaPagamento.objects.filter(pagamento_baixado__in=[self.pk])

    def movimento_vinculado(self):
        """Primeiro movimento (bancário) de uma baixa deste pagamento."""
        if self.pk is None:
            return None
        try:
            from admin_financeiro.models import MovimentoBancario
            return MovimentoBancario.objects.filter(
                baixa_pagamento__in=self.baixas_registradas()).first()
        except Exception:
            return None

    # ------------------------------------------------------------------
    # REGRAS (espelho de `Fatura.motivo_recusa_*`)
    # ------------------------------------------------------------------
    def motivo_recusa_edicao(self):
        if self.pk is None:
            return None
        if self.finalizado:
            return (f'O pagamento {self.pk} está FINALIZADO e não pode ser '
                    'alterado. Primeiro REABRA o pagamento (botão '
                    '“Finalizar/Reabrir”) e depois edite.')
        if self.baixas_registradas().exists():
            return (f'O pagamento {self.pk} tem baixa registrada e não pode '
                    'ser alterado. Exclua primeiro a BAIXA, em '
                    '“7. Baixa de Pagamentos”.')
        return None

    def motivo_recusa_exclusao(self):
        if self.pk is None:
            return None
        if self.finalizado:
            return (f'O pagamento {self.pk} está FINALIZADO e não pode ser '
                    'excluído. Primeiro REABRA o pagamento e depois exclua.')
        if self.baixas_registradas().exists():
            return (f'O pagamento {self.pk} já tem baixa registrada e não '
                    'pode ser excluído. Exclua primeiro a BAIXA, em '
                    '“7. Baixa de Pagamentos”.')
        return None

    def delete(self, *args, **kwargs):
        """Exclusão do PAGAMENTO — leva a PRÉ-PAGAMENTO de origem junto.

        A previsão existe só para gerar este pagamento: uma vez que ele sai,
        ela volta a ser livre (e volta a poder ser editada/excluída).

        A pk é guardada ANTES do `super().delete()` — na herança multitable o
        Django anula a pk da instância e da linha pai em cache.
        """
        prepag_pk = self.prepagamento_ptr_id
        resultado = super().delete(*args, **kwargs)
        if prepag_pk:
            PrePagamento.objects.filter(pk=prepag_pk).delete()
        return resultado




class BaixaPagamento(models.Model):
    """BAIXA de pagamento (espelho da `BaixaFatura`): a SAÍDA efetiva.

    Herda os dados do pagamento baixado (a `pagamento` abaixo é o vínculo).
    Cada baixa aponta para **um** destino: BANCO (`competencia_bancaria` →
    `MovimentoBancario` com `valor_saida`) ou CAIXA (`competencia_caixa` →
    `MovimentoCaixa` tipo 'S').
    """
    pagamento = models.ForeignKey(
        'Pagamento', on_delete=models.PROTECT, verbose_name='Pagamento',
        related_name='baixas_registros')
    # Alias usado pelas regras (espelho de `Fatura.baixas_registradas`).
    pagamento_baixado = models.ManyToManyField(
        'Pagamento', related_name='baixas', blank=True,
        verbose_name='Pagamento baixado')

    competencia_bancaria = models.ForeignKey(
        'admin_financeiro.CompetenciaBancaria', on_delete=models.PROTECT,
        verbose_name='Competência Bancária', blank=True, null=True)
    # Pagamento em DINHEIRO: informa a competência de CAIXA (tesouraria).
    competencia_caixa = models.ForeignKey(
        'admin_tesouraria.CompetenciaCaixa', on_delete=models.PROTECT,
        verbose_name='Competência de Caixa', blank=True, null=True,
        help_text='Obrigatória quando a transação movimenta CAIXA.')
    transacao_financeira = models.ForeignKey(
        TransacaoFinanceira, on_delete=models.PROTECT,
        verbose_name='Transação Financeira')

     
    valor_pagamento = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Valor do Pagamento'
    )
    dt_pagamento = models.DateField(
        verbose_name='Data do Pagamento'
    )
    us_registro = models.ForeignKey(
        User, related_name='us_baixa_pagamento_registro', on_delete=models.PROTECT
    )
    dt_registro = models.DateTimeField(default=timezone.now, editable=False)
    us_atualizacao = models.ForeignKey(
        User, related_name='us_baixa_pagamento_atualizacao', on_delete=models.PROTECT, null=True, blank=True
    )
    dt_atualizacao = models.DateTimeField(default=None, blank=True, null=True)
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT
    )
    observacao = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status'
    )


    class Meta:
        verbose_name = 'Baixa de Pagamento'
        verbose_name_plural = '7. Baixa de Pagamentos'

    def __str__(self):
        return (f'Baixa do pagamento {self.pagamento_id} / Valor: '
                f'{self.valor_pagamento} / Pago em: {self.dt_pagamento}')

    # ------------------------------------------------------------------
    # COMPETÊNCIA FECHADA (bancária ou de caixa) TRAVA TUDO
    # ------------------------------------------------------------------
    def competencia_fechada(self):
        """A competência (banco ou caixa) que trava esta baixa — ou None."""
        if self.competencia_bancaria_id and \
                self.competencia_bancaria.dt_fechamento_competencia:
            return ('bancária', self.competencia_bancaria)
        if self.competencia_caixa_id and \
                getattr(self.competencia_caixa, 'dt_fechamento', None):
            return ('caixa', self.competencia_caixa)
        return None

    def motivo_recusa_exclusao(self):
        """Só a COMPETÊNCIA FECHADA bloqueia a exclusão da baixa."""
        if self.pk is None:
            return None
        travada = self.competencia_fechada()
        if travada:
            tipo, comp = travada
            data = (comp.dt_fechamento_competencia
                    if tipo == 'bancária' else comp.dt_fechamento)
            return (f'A competência {tipo} “{comp}” está FECHADA em '
                    f'{data:%d/%m/%Y}: não é possível excluir a baixa (nem o '
                    'movimento dela). Reabra a competência para corrigir.')
        return None

    def motivo_recusa_edicao(self):
        if self.pk is None:
            return None
        travada = self.competencia_fechada()
        if travada:
            tipo, comp = travada
            return (f'A competência {tipo} “{comp}” está FECHADA: não é '
                    'possível alterar a baixa.')
        return None

    def movimentos_gerados(self):
        """Movimentos (banco **e** caixa) gerados por esta baixa."""
        if self.pk is None:
            return []
        movimentos = []
        try:
            movimentos.extend(self.movimentos_bancarios.all())
        except Exception:
            pass
        try:
            from admin_tesouraria.models import MovimentoCaixa
            movimentos.extend(MovimentoCaixa.objects.filter(
                baixa_pagamento_id=self.pk))
        except Exception:
            pass
        return movimentos

    def excluir_devolvendo_saldo(self):
        """Exclui a baixa e DEVOLVE o valor ao saldo do pagamento."""
        pagamento = self.pagamento
        valor = self.valor_pagamento or 0
        pk = self.pk
        models.Model.delete(self)
        if pagamento is not None:
            pagamento.refresh_from_db(fields=['valor_saldo', 'valor_pagamento'])
            saldo = (pagamento.valor_saldo or 0) + valor
            total = pagamento.valor_pagamento or pagamento.valor or 0
            if total and saldo > total:
                saldo = total
            pagamento.valor_saldo = saldo
            if saldo > 0 and pagamento.dt_liquidacao:
                pagamento.dt_liquidacao = None
            pagamento.save(update_fields=['valor_saldo', 'dt_liquidacao'])
        return pk

    def excluir_com_movimento(self):
        """Exclui a baixa e os movimentos dela (se algum estiver barrado,
        nada sai e o motivo volta)."""
        for mov in self.movimentos_gerados():
            # Banco e caixa têm APIs próprias: `motivo_recusa_exclusao()` no
            # movimento bancário; `pode_excluir()` no de caixa.
            metodo = (getattr(mov, 'motivo_recusa_exclusao', None)
                      or getattr(mov, 'pode_excluir', None))
            motivo = metodo() if metodo is not None else None
            if motivo:
                return motivo
        travada = self.competencia_fechada()
        if travada:
            return self.motivo_recusa_exclusao()
        for mov in self.movimentos_gerados():
            mov.delete()
        self.excluir_devolvendo_saldo()
        return None

    def clean(self):
        from django.core.exceptions import ValidationError
        movimento = (self.transacao_financeira.movimento
                     if self.transacao_financeira_id else None)
        if movimento == 'caixa':
            comp = self.competencia_caixa
            if comp is None:
                raise ValidationError({
                    'competencia_caixa':
                        'Pagamento em DINHEIRO: informe a COMPETÊNCIA DE CAIXA '
                        'aberta.'})
            if comp.dt_fechamento:
                raise ValidationError({
                    'competencia_caixa':
                        f'O caixa "{comp}" está FECHADO: escolha outro caixa '
                        'aberto.'})
            if not comp.validar_periodo(self.dt_pagamento):
                raise ValidationError({
                    'dt_pagamento':
                        'A data do pagamento está fora do período da '
                        'competência de caixa.'})
            if self.competencia_bancaria_id:
                raise ValidationError({
                    'competencia_bancaria':
                        'Transação de CAIXA não usa competência bancária '
                        '(limpe o campo).'})
        elif movimento == 'banco' and self.competencia_bancaria is None:
            raise ValidationError({
                'competencia_bancaria':
                    'Pagamento por BANCO: informe a competência bancária.'})
        return super().clean()

    def save(self, *args, **kwargs):
        # Baixa de pagamento: saldo do pagamento + movimento do lado correto.
        nova = self._state.adding
        if nova and self.pagamento_id:
            self.pagamento.atualizar_saldo(self.valor_pagamento)
        super().save(*args, **kwargs)
        if nova:
            # Amarra o M2M de controle (espelho de `fatura_baixada`).
            try:
                self.pagamento_baixado.set([self.pagamento_id])
            except Exception:
                pass
        movimento = (self.transacao_financeira.movimento
                     if self.transacao_financeira_id else None)
        if movimento == 'banco' and self.competencia_bancaria_id and not \
                self.__dict__.get('_mov_banco_gerado'):
            from admin_financeiro.models import MovimentoBancario
            existe = MovimentoBancario.objects.filter(
                baixa_pagamento=self).exists()
            if not existe:
                MovimentoBancario.objects.create(
                    competencia_bancaria=self.competencia_bancaria,
                    transacao_financeira=self.transacao_financeira,
                    valor_entrada=0,
                    valor_saida=self.valor_pagamento,
                    dt_movimento=self.dt_pagamento,
                    baixa_pagamento=self,
                    observacao=f'Pagamento #{self.pagamento_id}',
                    us_registro=self.us_registro,
                    estabelecimento=self.estabelecimento,
                    status='A')
        elif movimento == 'caixa' and self.competencia_caixa_id:
            from admin_tesouraria.models import MovimentoCaixa
            existe = MovimentoCaixa.objects.filter(
                baixa_pagamento_id=self.pk).exists()
            if not existe:
                MovimentoCaixa.objects.create(
                    competencia_caixa=self.competencia_caixa,
                    dt_movimento=self.dt_pagamento,
                    tipo='S',
                    origem='pagamento',
                    valor_saida=self.valor_pagamento,
                    transacao_financeira=self.transacao_financeira,
                    pagamento=self.pagamento,
                    baixa_pagamento=self,
                    observacao=f'Pagamento #{self.pagamento_id}',
                    us_registro=self.us_registro,
                    estabelecimento=self.estabelecimento)
