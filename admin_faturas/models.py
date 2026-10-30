from datetime import timedelta
from decimal import Decimal
from datetime import timedelta, date
from django.urls import reverse
from django.utils import timezone
from django.db import models
from admin_cadastros_financeiros.models import Conta, TransacaoFinanceira
from dominios.choices import (
    periodos_faturas_choices, modo_fatura_choices, tipo_contrato_choices,
    modalidade_contrato_choices, obrigatorios_choices, sn_choices,
    status_choices, pessoa_choices, estabelecimento_choices,
    periodos_choices, dias_choices, descricao_internacao_choices
)
from django.contrib.auth.models import User
from admin_cadastros.models import Estabelecimento, Pessoa, Empresa
import calendar
from admin_financeiro.models import CompetenciaBancaria, MovimentoBancario
from dominios.utils import EncryptedTextField, validate_anexo_file
from django.core.validators import FileExtensionValidator

def periodo_cobranca(competencia, dia_envio):
    # Intervalo inclusivo coberto por uma competência e seu dia de envio.
    if competencia.month == 1:
        ano_anterior, mes_anterior = competencia.year - 1, 12
    else:
        ano_anterior, mes_anterior = competencia.year, competencia.month - 1
    ultimo_dia_mes_anterior = calendar.monthrange(
        ano_anterior, mes_anterior)[1]

    if dia_envio == 1:
        inicio = date(ano_anterior, mes_anterior, 1)
        fim = date(ano_anterior, mes_anterior, ultimo_dia_mes_anterior)
    else:
        dia_inicio = min(dia_envio + 1, ultimo_dia_mes_anterior)
        inicio = date(ano_anterior, mes_anterior, dia_inicio)
        # O período termina no próprio dia de envio, não na véspera.
        fim = competencia
    return inicio, fim
class Convenio(models.Model):
    convenio = models.CharField(max_length=255, verbose_name='Convênio',
                                help_text='Informe o nome do convênio do contrato')
    modalidade_contrato = models.CharField(
        max_length=20, choices=modalidade_contrato_choices)
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT, verbose_name='Estabelecimento')
    pagador_pj = models.ForeignKey(Empresa, on_delete=models.PROTECT,
                                   verbose_name='Pagador PJ', blank=True, null=True)
    pagador_pf = models.ForeignKey(Pessoa, on_delete=models.PROTECT, related_name='pagador_pf_contrato',
                                   verbose_name='Pagador PF', blank=True, null=True)
    modo_fatura = models.CharField(max_length=2, choices=modo_fatura_choices, default='CO', verbose_name='Modalidade',
                                   help_text='Escolha se gera uma fatura para todos os clientes ou uma fatura para cada cliente!')
    pre_faturado = models.BooleanField(
        default=False, verbose_name='Pré-Faturado')
    cliente = models.ManyToManyField(
        Pessoa, related_name='clientes_contrato', verbose_name='Cliente(s)')
    nr_contrato = models.CharField(max_length=30)
    nr_aditivo = models.CharField(max_length=30, blank=True, null=True)
    inicio_vigencia = models.DateField(
        verbose_name='Início Vigência', help_text='Início vigência do contrato')
    final_vigencia = models.DateField(
        verbose_name='Final Vigência', help_text='Final vigência do contrato')
    fatura_vig_inicial = models.BooleanField(
        default=True, help_text='Marque para gerar pré-fatura no primeiro mês de vigência')
    fatura_vig_final = models.BooleanField(
        default=True, help_text='Marque para gerar pré-fatura no último mês de vigência')
    dia_envio = models.PositiveSmallIntegerField(
        default=1, verbose_name='Dia Envio', help_text='Dia de envio da fatura')
    dias_pagamento = models.PositiveSmallIntegerField(
        default=10, verbose_name='Dias Pagamento', help_text='Dias corridos para pagamento após o envio da fatura/NF')
    valor_mensal = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Valor Mensal', blank=True, null=True, help_text='Valor por cliente')
    valor_diaria = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Valor Diária', blank=True, null=True, help_text='Valor por cliente')
    empenho_global = models.CharField(max_length=80, blank=True, null=True,
                                      help_text='Só marque se o empenho for global e não tiver empenho por cliente. Para empenhos individuais o ajuste deve ser na pré-fatura')
    tx_retencao_nf = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Tx.Retenção(%)',
                                         blank=True, null=True, help_text='Informe a taxa de retenção da nota fiscal em percentual')
    vl_retencao_nf = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Vl.Retenção(R$)',
                                         blank=True, null=True, help_text='Informe o valor de taxa de retenção')

    descricao_internacao = models.CharField(
        max_length=100, choices=descricao_internacao_choices, default='tratamento', help_text='Escolha a descrição do tratamento para exibir na descrição da Nota Fiscal')
    descricao_nf = models.CharField(max_length=256, blank=True, null=True,
                                    help_text='Digite uma descrição padrão para o campo descrição da nota em faturas, ex: Dados Bancários')

    iniciais_cliente = models.BooleanField(
        default=True, help_text='Marque para aparecer somente as iniciais do nome do cliente nas descrições de notas')

    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(User, on_delete=models.PROTECT, null=True,
                                    related_name='contrato_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(User, on_delete=models.PROTECT, blank=True,
                                       null=True, related_name='contrato_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status')



    class Meta:
        verbose_name = 'Convênio'
        verbose_name_plural = '1. Convênios/Contratos'
        ordering = ['-pk']

    def __str__(self):
        return self.convenio

    def motivo_recusa_edicao(self):
        """Por que este CONVÊNIO não pode ser ALTERADO (ou None = pode).

        REGRA: só se altera o convênio quando ele NÃO tem pré-fatura ligada a
        ele. As etapas seguintes (fatura, baixa, movimento) são tratadas nas
        próprias telas — aqui o convênio olha só um passo à frente.
        """
        if self.pk is None:
            return None
        if self.prefaturas.exists():
            return (f'O convênio “{self}” já tem pré-fatura gerada e não pode '
                    'ser alterado. Exclua primeiro a PRÉ-FATURA '
                    '(“2. Pré-Faturas”) para liberar a edição.')
        return None


class PreFatura(models.Model):
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT, verbose_name='Estabelecimento')
    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(User, on_delete=models.PROTECT, null=True,
                                    related_name='pre_fatura_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(User, on_delete=models.PROTECT, blank=True,
                                       null=True, related_name='pre_fatura_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status')

    convenio = models.ForeignKey(
        Convenio, on_delete=models.PROTECT, related_name='prefaturas', verbose_name='Convênio')
    cliente = models.CharField(
        max_length=1024, blank=True, null=True, verbose_name='Cliente')
    nr_contrato = models.CharField(max_length=100, blank=True, null=True)
    nr_aditivo = models.CharField(max_length=100, blank=True, null=True)
    empenho = models.CharField(max_length=100, blank=True, null=True)
    dia_envio = models.PositiveSmallIntegerField(
        default=1, verbose_name='Dia Envio', help_text='Dia para enviar o faturamento')
    dias_pagamento = models.PositiveSmallIntegerField(
        default=10, verbose_name='Dias corridos para pagamento', help_text='Dias corridos para pagamento após o envio da fatura/NF')
    competencia = models.DateField(verbose_name='Competência')
    pagador_pj = models.ForeignKey(Empresa, on_delete=models.PROTECT,
                                   null=True, blank=True, verbose_name='Pagador Pessoa Jurídica')
    pagador_pf = models.ForeignKey(Pessoa, on_delete=models.PROTECT, null=True,
                                   blank=True, verbose_name='Pagador Pessoa Física', related_name='pagador_pf')
    valor = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Valor Bruto', help_text='Valor da pré-fatura bruto, sem taxas e retenções')
    pre_faturado = models.BooleanField(default=False)
    dt_vencimento = models.DateField(
        verbose_name='Vencimento', help_text='Vencimento da Fatura')

    class Meta:
        verbose_name = 'Pré-Fatura'
        verbose_name_plural = '2. Pré-Faturas'
        ordering = ['-id']

    def __str__(self):
        return f"{self.convenio}"

    def fatura_gerada(self):
        """A FATURA gerada por esta pré-fatura (ou None)."""
        if self.pk is None:
            return None
        return Fatura.objects.filter(prefatura_ptr_id=self.pk).first()

    def motivo_recusa_edicao(self):
        """Por que esta PRÉ-FATURA não pode ser ALTERADA (ou None = pode).

        REGRA: só se altera a pré-fatura quando ela NÃO tem FATURA ligada a
        ela. Como `Fatura` herda de `PreFatura`, a versão de baixo (fatura)
        sobrescreve a desta classe.
        """
        if self.pk is None:
            return None
        fatura = Fatura.objects.filter(prefatura_ptr_id=self.pk).first()
        if fatura is not None:
            return (f'A pré-fatura {self.pk} já gerou a fatura {fatura.pk} e '
                    'não pode ser alterada. Exclua primeiro a FATURA, em '
                    '“3. Faturas”, para liberar a edição.')
        return None

    def motivo_recusa_exclusao(self):
        """Por que esta pré-fatura NÃO pode ser excluída (ou None = pode).

        REGRA: só se exclui a pré-fatura quando ela NÃO tem FATURA ligada a
        ela. (A versão de baixo, da fatura, sobrescreve esta.)
        """
        if self.pk is None:
            return None
        fatura = Fatura.objects.filter(prefatura_ptr_id=self.pk).first()
        if fatura is not None:
            return (f'A pré-fatura {self.pk} já gerou a fatura {fatura.pk} e '
                    'não pode ser excluída. Exclua primeiro a FATURA, em '
                    '“3. Faturas”.')
        return None

    def save(self, *args, **kwargs):
        # Sem vencimento informado, o padrão é a COMPETÊNCIA + dia de envio +
        # dias de pagamento (antes somava o dia de envio a um `timedelta`, o
        # que levantava `TypeError` e derrubava a edição em linha).
        if not self.dt_vencimento:
            base_venc = self.competencia or timezone.localdate()
            self.dt_vencimento = base_venc + timedelta(
                days=(self.dia_envio or 0) + (self.dias_pagamento or 0))
        super().save(*args, **kwargs)

    def create_fatura(self):
        # Sem taxa cadastrada (None) = sem retenção: 0.
        # `Decimal(x or 0)` com x=None já vira 0; o divisor também precisa ser
        # Decimal — `Decimal / int` levanta TypeError.
        retencao_percentual = Decimal(
            self.convenio.tx_retencao_nf or 0) / Decimal('100')
        retencao = retencao_percentual * self.valor
        retencao_fixa = Decimal(self.convenio.vl_retencao_nf or 0)
        valor_fatura = self.valor - retencao - retencao_fixa
        competencia = self.competencia
        dia_envio = self.dia_envio
        periodo_inicio, periodo_fim = periodo_cobranca(competencia, dia_envio)

        # Os valores da pré-fatura são sempre brutos. Preserva-se o valor bruto
        # também na fatura; somente valor_fatura desconta retenções.
        periodo_inicio = max(periodo_inicio, self.convenio.inicio_vigencia)
        periodo_fim = min(periodo_fim, self.convenio.final_vigencia)
        periodo_tratamento = (
            f"Período de {periodo_inicio:%d/%m/%y} a "
            f"{periodo_fim:%d/%m/%y}"
        )

        # Criação da descrição
        descricao_internacao = self.convenio.get_descricao_internacao_display()
        descricao_nf = self.convenio.descricao_nf or ''
        clientes = self.cliente or ''
        contrato = self.convenio.nr_contrato or ''

        if self.convenio.iniciais_cliente:
            # Separa os clientes pelo delimitador ";"
            lista_clientes = clientes.split(';')
            # Extrai as iniciais de cada cliente
            cliente_descricao = "; ".join(
                ["".join([nome.strip().split()[0][0] + (nome.strip().split()[1][0] if len(nome.strip().split())
                                                        > 1 else '') for nome in cliente.split()]) for cliente in lista_clientes]
            )
        else:
            cliente_descricao = clientes

        descricao = f"Contrato: {contrato} - {descricao_internacao} : {cliente_descricao} - {periodo_tratamento} - Empenho: {self.empenho or 'N/A'} - {descricao_nf}"

        Fatura.objects.create(
            prefatura_ptr=self,
            estabelecimento=self.estabelecimento,
            dt_registro=self.dt_registro,
            us_registro=self.us_registro,
            dt_atualizacao=self.dt_atualizacao,
            us_atualizacao=self.us_atualizacao,
            status=self.status,
            convenio=self.convenio,
            cliente=self.cliente,
            nr_contrato=self.nr_contrato,
            nr_aditivo=self.nr_aditivo,
            empenho=self.empenho,
            dia_envio=self.dia_envio,
            dias_pagamento=self.dias_pagamento,
            competencia=self.competencia,
            pagador_pj=self.pagador_pj,
            pagador_pf=self.pagador_pf,
            valor=self.valor,
            pre_faturado=self.pre_faturado,
            faturado=False,
            descricao=descricao,  # Adiciona a descrição criada
            nr_nota_fiscal='N/A',  # criar lógica
            dt_vencimento=self.dt_vencimento,
            tx_retencao_nf=self.convenio.tx_retencao_nf,
            valor_fatura=valor_fatura,
            periodo_tratamento=periodo_tratamento
        )


class Fatura(PreFatura):

    tx_retencao_nf = models.DecimalField(
        max_digits=5, decimal_places=2, verbose_name='Taxa Retenção(%)', blank=True, null=True)
    valor_fatura = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Valor Fatura')
    valor_saldo = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Valor Saldo', blank=True, null=True)

    dt_liquidacao = models.DateField(
        verbose_name='Data Liquidação', blank=True, null=True)
    descricao = models.TextField(
        verbose_name='Descrição', blank=True, null=True)
    nr_nota_fiscal = models.CharField(
        max_length=50, verbose_name='NF', help_text='Nota Fiscal', blank=True, null=True)
    periodo_tratamento = models.CharField(
        max_length=255, verbose_name='Período', help_text='Período de Tratamento', blank=True, null=True)
    faturado = models.BooleanField(default=False, verbose_name='Faturado')
    anexo_nf = models.FileField(upload_to='anexos/nf/%Y/%m/', verbose_name='Anexo NF', blank=True, null=True, help_text='Adicione arquivos dos formatos PDF, JPG, JPEG, PNG.',
                                      validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png']), validate_anexo_file])



    class Meta:
        verbose_name = 'Fatura'
        verbose_name_plural = '3. Faturas'
        ordering = ['-id']

    def save(self, *args, **kwargs):
        if not self.valor_fatura:
            # Sem taxa cadastrada (None) = sem retenção: 0. Divisor em Decimal
            # porque `Decimal / int` levanta TypeError.
            tx_retencao = Decimal(
                self.convenio.tx_retencao_nf or 0) / Decimal('100') * self.valor
            vl_retencao = Decimal(self.convenio.vl_retencao_nf or 0)
            self.valor_fatura = self.valor - tx_retencao - vl_retencao

        # Inicializa o valor_saldo com valor_fatura se for None
        if self.valor_saldo is None:
            self.valor_saldo = self.valor_fatura

        super().save(*args, **kwargs)

    def atualizar_saldo(self, valor_baixa, salvar=True):
        # Verifica se valor_saldo é None e inicializa com valor_fatura
        if self.valor_saldo is None:
            self.valor_saldo = self.valor_fatura or 0

        # Atualiza o valor do saldo, descontando o valor baixado
        self.valor_saldo -= valor_baixa

        if self.valor_saldo <= 0:
            # atualiza a data de liquidacao com data atual
            self.dt_liquidacao = timezone.now().date()

        # Salva a fatura com o saldo atualizado (a BaixaFatura adia o save até
        # depois de gravar a própria linha: salvar=False).
        if salvar:
            self.save()

    def __str__(self):
        dt_vencimento_formatado = self.dt_vencimento.strftime(
            '%d/%m/%Y') if self.dt_vencimento else 'N/A'
        competencia_formatada = self.competencia.strftime(
            '%d/%m/%Y') if self.competencia else 'N/A'

        return (f"{self.id} - {self.convenio} / Vencimento: {dt_vencimento_formatado} / "
                f"Competência: {competencia_formatada} / "
                f"Valor: {self.valor_fatura} / Saldo: {self.valor_saldo} / "
                f"Local: {self.estabelecimento}")

    def baixas_registradas(self):
        """Baixas registradas para esta fatura (tabela da BAIXA)."""
        if self.pk is None:
            return BaixaFatura.objects.none()
        return BaixaFatura.objects.filter(fatura_baixada__in=[self.pk])

    def movimento_vinculado(self):
        """Movimento bancário de uma baixa desta fatura (o primeiro)."""
        if self.pk is None:
            return None
        try:
            return MovimentoBancario.objects.filter(
                baixa_fatura__in=self.baixas_registradas()).first()
        except Exception:
            return None

    def motivo_recusa_edicao(self):
        """Por que esta FATURA não pode ser ALTERADA (ou None = pode).

        REGRA: só se altera a fatura quando ela NÃO tem BAIXA ligada a ela.
        (A baixa, por sua vez, depende da competência bancária aberta.)
        """
        if self.pk is None:
            return None
        if self.baixas_registradas().exists():
            return (f'A fatura {self.pk} tem baixa registrada e não pode ser '
                    'alterada. Exclua primeiro a BAIXA, em “4. Baixa de '
                    'Faturas”, para liberar a edição.')
        return None

    def motivo_recusa_exclusao(self):
        """Por que esta FATURA não pode ser excluída (ou None = pode).

        REGRA: só se exclui a fatura quando ela NÃO tem BAIXA ligada a ela.
        """
        if self.pk is None:
            return None
        if self.baixas_registradas().exists():
            return ('A fatura %s já tem baixa (recebimento) registrada e não '
                    'pode ser excluída. Exclua primeiro a BAIXA, em “4. Baixa '
                    'de Faturas”.' % self.pk)
        if BaixaFatura.objects.filter(fatura_ptr_id=self.pk).exists():
            return ('O registro %s é uma baixa de fatura e não pode ser '
                    'excluído por aqui.' % self.pk)
        return None

    def pk_fatura_baixada(self):
        """Na FATURA, a própria pk (o `__str__` da baixa usa este nome)."""
        return self.pk

    def valor_total_empacotado(self):
        """Na listagem de baixas a LINHA é uma fatura: sem pacote próprio."""
        return '-'

    def fatura_baixada_do_bd(self):
        return self

    def baixas_do_pk(self):
        """Baixas ligadas a esta fatura.

        Como a baixa HERDA de Fatura, o M2M ``baixas`` (em Fatura) aponta para
        a tabela pai e traria também as próprias faturas. Por isso o recorte é
        feito pela tabela da baixa (``BaixaFatura``), que é uma SUBQUERY — pode
        ser usada em filtros do admin sobre ``Fatura`` (change lists, filtros
        laterais, busca).
        """
        return BaixaFatura.objects.filter(
            fatura_baixada__in=[self.pk]).values('pk')



# TODO: APOS IMPLANTAR O CAIXA, FIELD COMPETENCIA_CAIXA 

class BaixaFatura(Fatura):
    """Baixa (recebimento) de uma fatura.

    Herda de `Fatura` — e, portanto, também de `PreFatura` — todos os campos
    (estabelecimento, cliente, competência, valores, vencimento, NF, auditoria
    etc.), que aqui funcionam como CÓPIA do estado da fatura no momento do
    recebimento. Declara abaixo apenas os campos que não existem em `Fatura`.

    A ligação com a(s) fatura(s) baixada(s) é o M2M `fatura_baixada`. Uma
    fatura pode ter VÁRIAS baixas (recebimentos parciais), mas cada linha de
    baixa aponta para uma única fatura.

    O M2M não tem tabela intermediária: a tabela dele é a PRÓPRIA tabela da
    baixa e o parent link (`fatura_ptr_id`) faz o papel da coluna de origem,
    como num relacionamento pai/filho. No admin cada baixa é listada/editada
    como antes (o `fatura_baixada` é derivado do `fatura_ptr`).

    NOTA: o Django não aceita campo de modelo filho com o mesmo nome de um
    campo ancestral (models.E006) e, na cadeia herdada, `fatura` já é o parent
    link de `PreFatura` (`pre_fatura` → fatura). Por isso os campos que colidem
    são redefinidos na tabela da baixa com o sufixo `_baixa` e expostos aqui
    pelo nome público (`fatura`, `estabelecimento`, `us_registro`,
    `us_atualizacao`) via __init__/__getattr__/__setattr__.
    """

    # --- Campos próprios da baixa (inexistentes em Fatura) -----------------
    # M2M porque uma baixa é um RECEBIMENTO da fatura: a mesma fatura recebe
    # várias baixas. Cada linha é um recebimento, então a baixa aponta para
    # UMA fatura (lista de um item: ver `pk_fatura_baixada`) — quem acumula
    # vários lançamentos é a FATURA (`Fatura.baixas`).
    fatura_baixada = models.ManyToManyField(
        Fatura, related_name='baixas', verbose_name='Fatura',
        help_text='Fatura que está sendo baixada.')
    valor_baixa = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Valor da Baixa')
    transacao_financeira = models.ForeignKey(
        TransacaoFinanceira, on_delete=models.PROTECT,
        verbose_name='Transação Financeira')
    competencia_bancaria = models.ForeignKey(
        'admin_financeiro.CompetenciaBancaria', on_delete=models.PROTECT,
        verbose_name='Competência Bancária', blank=True, null=True)
    dt_recebimento = models.DateField(verbose_name='Data de Recebimento')
    observacao = models.CharField(
        max_length=255, blank=True, null=True, verbose_name='Observação')

    # Valor ADICIONAL recebido junto com a baixa (não desconta da fatura):
    # vai para o MovimentoBancario como parte da entrada.
    valor_adicional = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, blank=True,
        verbose_name='Valor Adicional',
        help_text='Valor recebido além da baixa (não abate o saldo da '
                  'fatura); entra no movimento bancário.')

    # BAIXA EMPACOTADA: esta baixa RECEBE também as baixas informadas aqui —
    # o valor delas é SOMADO no movimento bancário e o vínculo delas com a
    # fatura é exibido junto. Cada baixa listada permanece vinculada à sua
    # própria fatura.
    baixas_empacotadas = models.ManyToManyField(
        'self', symmetrical=False, blank=True,
        related_name='pacotes_que_me_contem', verbose_name='Baixas Empacotadas',
        help_text='Outras baixas recebidas juntas nesta: os valores são '
                  'somados no movimento bancário.')

    # ------------------------------------------------------------------
    # VALIDADOR: a baixa NUNCA é negativa — o valor deve ser positivo e, no
    # máximo, ZERAR o saldo da fatura (nunca deixá-lo negativo).
    # ------------------------------------------------------------------
    def _validar_valor_baixa(self):
        """Valor da baixa: > 0 e <= saldo da fatura (zera, nunca negativa)."""
        from django.core.exceptions import ValidationError
        if self.valor_baixa is None or self.valor_baixa <= 0:
            raise ValidationError(
                {'valor_baixa': 'O valor da baixa deve ser positivo.'})
        fatura = self.fatura_baixada_do_bd()
        if fatura is not None:
            saldo = fatura.valor_saldo
            # Na criação o saldo ainda não foi descontado; na edição, o saldo
            # atual JÁ contém esta baixa — soma de volta para comparar.
            if not self._state.adding:
                saldo = (saldo or 0) + (self.valor_baixa_original or 0)
            if saldo is not None and self.valor_baixa > saldo:
                raise ValidationError({
                    'valor_baixa':
                        f'O valor da baixa ({self.valor_baixa}) é maior que '
                        f'o saldo da fatura ({saldo}). A baixa pode, no '
                        'máximo, zerar o saldo.'})

    @property
    def valor_baixa_original(self):
        """Valor_baixa ANTES desta edição (lido do banco, 1 consulta)."""
        if self.pk and not self._state.adding:
            original = BaixaFatura.objects.filter(pk=self.pk).first()
            if original is not None:
                return original.valor_baixa or 0
        return 0

    # ------------------------------------------------------------------
    # BAIXA EMPACOTADA: total e descrição do pacote (para o movimento).
    # ------------------------------------------------------------------
    def valor_total_empacotado(self):
        """valor_baixa + adicional + SOMA das baixas empacotadas."""
        from django.db.models import Sum
        extra = self.baixas_empacotadas.aggregate(
            s=Sum('valor_baixa'))['s'] or 0
        return (self.valor_baixa or 0) + (self.valor_adicional or 0) + extra
    valor_total_empacotado.short_description = 'Valor Empacotado'
    valor_total_empacotado.admin_order_field = 'valor_baixa'

    def descricao_empacotado(self):
        """'Baixa #1 (fatura 10), Baixa #2 (fatura 11) + adicional' — para o
        movimento bancário mostrar de onde vem cada valor. A fatura da
        PRÓPRIA baixa sai do alias em memória (no save o vínculo M2M ainda
        não foi gravado no banco)."""
        def fatura_de(baixa):
            pk = baixa.pk_fatura_baixada()
            if pk:
                return pk
            return baixa.fatura_baixada_do_bd() \
                and baixa.fatura_baixada_do_bd().pk
        partes = [f'Baixa #{self.pk} (fatura '
                  f'{fatura_de(self) or "?"})']
        for outra in self.baixas_empacotadas.all():
            partes.append(
                f'Baixa #{outra.pk} (fatura '
                f'{fatura_de(outra) or "?"})')
        texto = ' + '.join(partes)
        if self.valor_adicional:
            texto += f' + adicional {self.valor_adicional}'
        return texto

    class Meta:
        verbose_name = 'Baixa de Fatura'
        verbose_name_plural = '4. Baixa de Faturas'
        ordering = ['-dt_recebimento']  # Ordena por data de recebimento

    # Os campos abaixo existem para REDECLARAR na tabela da baixa os
    # relacionamentos herdados que não podem repetir nome nem `related_name`:
    # as FKs ancestrais guardam os mesmos valores, mas aqui precisam dos
    # `related_name` próprios (`estab_baixa_fatura`, `baixa_fat_criado_por`,
    # ...), senão o Django acusa conflito de reverse accessor.

    estabelecimento_baixa = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT,
        related_name='estab_baixa_fatura', verbose_name='Estabelecimento')
    us_registro_baixa = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True,
        related_name='baixa_fat_criado_por', verbose_name='Us.Registro')
    us_atualizacao_baixa = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True,
        related_name='baixa_fat_atualizado_por',
        verbose_name='Us.Atualização')

    # Campos com nome renomeado internamente -> nome público na baixa.
    _ALIASES = {
        'fatura': 'fatura_baixada',
        'estabelecimento': 'estabelecimento_baixa',
        'us_registro': 'us_registro_baixa',
        'us_atualizacao': 'us_atualizacao_baixa',
    }
    # Nomes aceitos na construção (BaixaFatura(fatura=...)). Os nomes de campo
    # são rejeitados: o __init__ do ORM da linha filha chama isto também e
    # reencodaria os valores de volta para o campo herdado.
    _NOMES_PUBLICOS = frozenset(_ALIASES)
    # Nomes gravados pelo ORM no `__dict__` da instância (o M2M sem tabela
    # intermediária é guardado como `<nome>_ids`).
    _NOMES_INTERNOS = frozenset(_ALIASES.values())

    # Campos de Fatura copiados para a baixa no registro (exceto auditoria /
    # status, que são da baixa, e os `*_baixa` que espelham as FKs).
    CAMPOS_COPIADOS_DA_FATURA = (
        'convenio', 'cliente', 'nr_contrato', 'nr_aditivo', 'empenho',
        'dia_envio', 'dias_pagamento', 'competencia', 'pagador_pj',
        'pagador_pf', 'valor', 'pre_faturado', 'dt_vencimento',
        'tx_retencao_nf', 'valor_fatura', 'valor_saldo', 'dt_liquidacao',
        'descricao', 'nr_nota_fiscal', 'periodo_tratamento', 'faturado',
        'anexo_nf',
        # `estabelecimento` NÃO entra: precisa passar pelo __setattr__ (alias),
        # e um setattr comum cairia no campo herdado, deixando a FK NOT NULL
        # `estabelecimento_baixa` vazia.
    )

    def __str__(self):
        # O M2M só pode ser lido depois que a baixa existe (ou foi ligada):
        # o `__str__` roda até em instância nova, em mensagem de erro.
        id_fatura = self.__dict__.get('fatura_baixada_ids') or None
        id_fatura = id_fatura[0] if id_fatura else self.__dict__.get('fatura')
        if id_fatura is None and self.pk is not None:
            # Carregada do banco: o vínculo está no M2M (sem tabela
            # intermediária) — consulta em UMA query, sem quebrar o `__str__`.
            try:
                id_fatura = self.fatura_baixada.values_list(
                    'pk', flat=True).first()
            except Exception:
                id_fatura = None
        fatura = id_fatura if id_fatura is not None else '?'
        return (f"Baixa {self.pk} (fatura {fatura}) / Valor: "
                f"{self.valor_baixa} / Recebimento: {self.dt_recebimento}")

    def __init__(self, *args, **kwargs):
        # Aceita tanto o nome público (`fatura=`, `estabelecimento=`, ...)
        # quanto o nome interno dos FKs (`estabelecimento_baixa=` etc.), antes
        # de o ORM receber os kwargs.
        if self._NOMES_INTERNOS.intersection(kwargs):
            kwargs = dict(kwargs)
            for interno, publico in self._ALIASES.items():
                if interno in kwargs:
                    valor = kwargs.pop(interno)
                    kwargs.setdefault(publico, valor)

        # `fatura_baixada` é M2M: o ORM não aceita atribuição na construção
        # (`TypeError: ... use fatura_baixada.set()`) e o próprio `.set()`
        # exige a pk da baixa. O valor (fatura solta ou lista) fica no aliases
        # `<campo>_ids` e o `save()` grava o vínculo depois que a baixa existe.
        fatura_baixada = kwargs.pop('fatura_baixada', None)
        if fatura_baixada is not None and not isinstance(
                fatura_baixada, (list, tuple, set)):
            fatura_baixada = [fatura_baixada]

        if self._NOMES_PUBLICOS.intersection(kwargs):
            kwargs = dict(kwargs)
            for publico in self._NOMES_PUBLICOS.intersection(kwargs):
                kwargs[self._ALIASES[publico]] = kwargs.pop(publico)
        super().__init__(*args, **kwargs)

        if fatura_baixada:
            # O gerenciador do M2M exige a pk da baixa, que só existe depois do
            # save(): o valor fica no aliases do ORM e o `save()` grava o
            # vínculo logo após a baixa.
            object.__setattr__(self, 'fatura_baixada_ids',
                               [f.pk for f in fatura_baixada])

    @classmethod
    def fatura_baixada_ids_dos_dados(cls, dados):
        """PKs informadas em ``dados['fatura_baixada']`` (lista ou escalar).

        O campo é um M2M sem tabela intermediária (o parent link da baixa É o
        vínculo), então o valor chega como ``<campo>_ids`` no aliases do ORM.
        """
        valores = dados.get(f'{cls.fatura_baixada.field.name}_ids') or []
        if not isinstance(valores, (list, tuple, set)):
            valores = [valores]
        return [v for v in valores if v is not None]

    @staticmethod
    def queryset_faturas_baixadas(queryset):
        """`queryset` de Fatura + a fatura baixada de cada baixa EXISTENTE.

        O admin recorta as opções do campo M2M para as faturas com saldo; ao
        EDITAR uma baixa, a fatura dela pode já estar liquidada (saldo zero) e
        sairia do recorte — a validação do campo desabilitado então falharia
        com "não é uma das escolhas disponíveis".
        """
        baixadas = BaixaFatura.objects.values('pk')
        return Fatura.objects.filter(
            models.Q(pk__in=queryset.values('pk'))
            | models.Q(baixas__in=baixadas)).distinct()

    def movimentos_gerados(self):
        """Movimentos bancários gerados por esta baixa (saem junto com ela)."""
        if self.pk is None:
            return []
        try:
            return list(self.movimentos_bancarios.all())
        except Exception:
            return []

    def competencia_bancaria_fechada(self):
        """A competência que trava esta baixa (fechada) — ou None.

        Olha a competência do próprio cadastro e as dos movimentos gerados.
        A FATURA (faturada ou não) NÃO entra nesta regra: baixa e movimento
        são do lado BANCÁRIO e só a competência bancária os trava.
        """
        comps = list(self.movimentos_gerados())
        candidatas = [m.competencia_bancaria for m in comps
                      if m.competencia_bancaria_id]
        if self.competencia_bancaria_id:
            candidatas.append(self.competencia_bancaria)
        return next((c for c in candidatas if c.dt_fechamento_competencia),
                    None)

    def motivo_recusa_exclusao(self):
        """Por que esta BAIXA não pode ser excluída (ou None = pode).

        Movimento e baixa são CONCOMITANTES (um exclui o outro) e só a
        COMPETÊNCIA BANCÁRIA decide: aberta → pode; fechada → não. A fatura
        estar finalizada NÃO impede (senão não haveria como desfazer a
        baixa).
        """
        if self.pk is None:
            return None
        comp = self.competencia_bancaria_fechada()
        if comp is not None:
            return (f'A competência bancária “{comp.descricao}” está FECHADA '
                    f'em {comp.dt_fechamento_competencia:%d/%m/%Y}: não é '
                    'possível excluir a baixa (nem o movimento dela). Reabra '
                    'a competência para corrigir.')
        return None

    def motivo_recusa_edicao(self):
        """Por que esta BAIXA não pode ser ALTERADA (ou None = pode).

        REGRA: baixa só se altera (ou exclui) com a COMPETÊNCIA BANCÁRIA
        ABERTA — mesma regra do movimento. A fatura não entra aqui.
        """
        if self.pk is None:
            return None
        comp = self.competencia_bancaria_fechada()
        if comp is not None:
            return (f'A competência bancária “{comp.descricao}” está FECHADA '
                    f'em {comp.dt_fechamento_competencia:%d/%m/%Y}: não é '
                    'possível alterar a baixa. Reabra a competência para '
                    'corrigir.')
        return None

    def excluir_devolvendo_saldo(self):
        """Exclui a baixa e DEVOLVE o valor ao saldo da fatura.

        Uma baixa abate `valor_saldo` da fatura quando é registrada; apagar a
        linha sem devolver deixaria a fatura “paga” sem recebimento. A data de
        liquidação é desfeita quando a fatura volta a ter saldo.
        """
        # A fatura é identificada ANTES: depois do delete o vínculo M2M sai.
        fatura = self.fatura_baixada_do_bd()
        fatura_pk = fatura.pk if fatura else self.pk_fatura_baixada()
        valor = self.valor_baixa or 0
        pk = self.pk
        models.Model.delete(self)
        if not fatura_pk:
            return pk
        fatura = Fatura.objects.filter(pk=fatura_pk).first()
        if fatura is None:
            return pk
        fatura.refresh_from_db(fields=['valor_saldo', 'valor_fatura'])
        saldo = (fatura.valor_saldo or 0) + valor
        if fatura.valor_fatura is not None and saldo > fatura.valor_fatura:
            saldo = fatura.valor_fatura
        fatura.valor_saldo = saldo
        if saldo > 0 and fatura.dt_liquidacao:
            fatura.dt_liquidacao = None
        fatura.save(update_fields=['valor_saldo', 'dt_liquidacao'])
        return pk

    def excluir_com_movimento(self):
        """Exclui a baixa E os movimentos dela (concomitantes).

        É a forma usada pela tela: excluir a baixa e o movimento andam juntos.
        Se algum movimento estiver barrado (competência fechada ou
        conciliado), NADA é excluído e o motivo volta ao chamador.
        """
        movimentos = self.movimentos_gerados()
        for movimento in movimentos:
            motivo = (movimento.motivo_recusa_exclusao()
                      or movimento.motivo_recusa_conciliacao())
            if motivo:
                return motivo
        motivo = self.competencia_bancaria_fechada()
        if motivo is not None and not movimentos:
            return (f'A competência bancária “{motivo.descricao}” está FECHADA '
                    f'em {motivo.dt_fechamento_competencia:%d/%m/%Y}: não é '
                    'possível excluir a baixa.')
        for movimento in movimentos:
            # Sem `excluir_baixa`: o movimento sai e a baixa é apagada logo
            # abaixo, devolvendo o valor ao saldo da fatura.
            movimento.delete()
        self.excluir_devolvendo_saldo()
        return None

    def pk_fatura_baixada(self):
        """PK da SUA fatura, lendo o aliases do ORM (sem SQL extra).

        Uma baixa pertence a UMA fatura; o form manda a lista (campo M2M) e o
        formset de uma fatura chega aqui com um único valor.
        """
        ids = self.fatura_baixada_ids_dos_dados(self.__dict__)
        if ids:
            return ids[0]
        return self.__dict__.get('fatura_baixada_id')

    def fatura_baixada_do_bd(self):
        """Fatura ligada a esta baixa (consulta ao banco)."""
        fatura_id = self.pk_fatura_baixada()
        if fatura_id:
            return Fatura.objects.filter(pk=fatura_id).first()
        # Recém-carregada do banco (o M2M não vem no aliases): lê o vínculo.
        if self._state.adding or self.pk is None:
            return None
        return self.fatura_baixada.first()

    def __getattr__(self, nome):
        # `self.fatura`, `self.estabelecimento`, ... devolvem o campo da baixa.
        # Só é chamado quando o atributo NÃO existe normalmente (ex.: FK não
        # carregada, ainda sem id) — aí o nome renomeado é resolvido aqui e
        # relançado como AttributeError com o nome correto.
        campo = self._ALIASES.get(nome)
        if campo is None:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{nome}'")
        try:
            return object.__getattribute__(self, campo)
        except AttributeError:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{nome}'") from None

    def __setattr__(self, nome, valor):
        # `fatura` é o reverse do parent link `prefatura_ptr` de Fatura
        # (PreFatura.fatura): repassá-lo ao `super().__setattr__` dispararia o
        # `ReverseOneToOneDescriptor.__set__`, que trocaria o parent link da
        # própria FATURA (`f.prefatura_ptr = baixa`) — destrutivo. Aqui
        # `fatura` é o ALIAS do vínculo: grava só o aliases do M2M.
        if nome == 'fatura':
            # Grava DIRETO no `__dict__`: o `object.__setattr__` consultaria a
            # MRO, acharia o `ReverseOneToOneDescriptor` de `prefatura_ptr`
            # (nome 'fatura', herdado de PreFatura) e dispararia o `__set__`
            # dele — trocando o parent link da própria FATURA.
            self.__dict__['fatura'] = valor
            # M2M: o valor é guardado no aliases do ORM como uma lista de pks.
            self.__dict__['fatura_baixada_ids'] = (
                [valor.pk] if valor is not None else [])
            return
        super().__setattr__(nome, valor)

    def _copiar_dados_da_fatura(self):
        """Preenche a cópia herdada com o estado atual da fatura baixada.

        Escreve direto nas colunas herdadas (`_id`/valor): o ORM grava a linha
        de `prefatura` ANTES da linha da baixa, então nada pode depender do
        estado da linha filha.
        """
        positivados = self.fatura_baixada_ids_dos_dados(self.__dict__)
        if self.competencia is not None or not positivados:
            return  # já preenchida (ou baixa sem fatura a copiar)

        fatura = Fatura.objects.get(pk=positivados[0])
        for campo in BaixaFatura.CAMPOS_COPIADOS_DA_FATURA:
            valor = getattr(fatura, campo)
            if valor is not None:
                setattr(self, campo, valor)

        self.estabelecimento_id = fatura.estabelecimento_id
        self.us_registro_id = fatura.us_registro_id
        self.status = self.status or fatura.status

    def save(self, *args, **kwargs):
        nova = self._state.adding

        # 0) VALIDADOR: baixa positiva e no máximo zerando o saldo.
        self._validar_valor_baixa()

        # 0) RETRATO (linha pai): na herança multitable a PK da baixa é o
        #    parent link `fatura_ptr` — cada baixa precisa de sua própria
        #    linha em `prefatura`/`fatura` (a cópia do estado da fatura no
        #    recebimento). Se o vínculo apontar para a FATURA ORIGINAL
        #    (ex.: o inline usa `fk_name='fatura_ptr'` com a fatura aberta),
        #    a nova baixa SOBRESCREVERIA o retrato de outra baixa (mesma pk)
        #    — por isso um novo pai é criado aqui.
        if nova and self.fatura_baixada_do_bd() is not None:
            fatura_vinculo_pk = self.pk_fatura_baixada()
            if self.fatura_ptr_id == fatura_vinculo_pk:
                retrato = Fatura.objects.get(pk=fatura_vinculo_pk)
                copia = Fatura(
                    estabelecimento_id=retrato.estabelecimento_id,
                    dt_registro=retrato.dt_registro,
                    us_registro_id=retrato.us_registro_id,
                    dt_atualizacao=retrato.dt_atualizacao,
                    us_atualizacao_id=retrato.us_atualizacao_id,
                    status=retrato.status,
                    convenio_id=retrato.convenio_id,
                    cliente=retrato.cliente,
                    nr_contrato=retrato.nr_contrato,
                    nr_aditivo=retrato.nr_aditivo,
                    empenho=retrato.empenho,
                    dia_envio=retrato.dia_envio,
                    dias_pagamento=retrato.dias_pagamento,
                    competencia=retrato.competencia,
                    pagador_pj_id=retrato.pagador_pj_id,
                    pagador_pf_id=retrato.pagador_pf_id,
                    valor=retrato.valor,
                    pre_faturado=retrato.pre_faturado,
                    dt_vencimento=retrato.dt_vencimento,
                    tx_retencao_nf=retrato.tx_retencao_nf,
                    valor_fatura=retrato.valor_fatura,
                    valor_saldo=retrato.valor_saldo,
                    dt_liquidacao=retrato.dt_liquidacao,
                    descricao=retrato.descricao,
                    nr_nota_fiscal=retrato.nr_nota_fiscal,
                    periodo_tratamento=retrato.periodo_tratamento,
                    faturado=retrato.faturado,
                    anexo_nf=retrato.anexo_nf,
                )
                # O `save()` de Fatura recalcula valor_fatura/saldo: os dados
                # do retrato já são definitivos, então grava direto. O status
                # 'I' marca o retrato como INTERNO (não é conta a receber —
                # as listagens de faturas filtram status='A'), e o `faturado`
                # segue o original para o retrato refletir o estado dela.
                copia.status = 'I'
                models.Model.save(copia)
                # Grava o PAI inteiro (não só o `fatura_ptr_id`): o
                # `models.Model.save(self)` salva a cadeia herdada a partir da
                # instância pai em cache (`self.fatura_ptr`), e ela
                # SOBRESCREVERIA o `fatura_ptr_id` de volta para a fatura
                # original (mesma pk) — o retrato novo seria ignorado.
                self.fatura_ptr = copia

        # 1) Cópia herdada: os campos da fatura na baixa são um retrato do
        #    momento do recebimento. O form da listagem editável manda o POST
        #    só com os campos de `list_editable`; sem esta cópia a linha filha
        #    (herdada, NOT NULL) seria gravada em branco. Só ocorre quando a
        #    cópia ainda não foi preenchida.
        if getattr(self, '_herdados_congelados', False):
            # Cópia herdada congelada (edição via inline): não mexe nos campos
            # herdados — o formset não os trazia e eles seriam apagados.
            object.__setattr__(self, '_herdados_congelados', False)
        else:
            self._copiar_dados_da_fatura()

        # 2) As FKs espelho da baixa acompanham os campos herdados.
        fatura = self.fatura_baixada_do_bd()
        if self.estabelecimento_baixa_id is None:
            self.estabelecimento_baixa_id = self.estabelecimento_id
        if self.us_registro_baixa_id is None:
            self.us_registro_baixa_id = self.us_registro_id
        if self.us_atualizacao_baixa_id is None:
            self.us_atualizacao_baixa_id = self.us_atualizacao_id

        # 3) Saldo: a fatura baixada só é alterada quando a baixa é REGISTRADA
        #    (editar uma baixa existente não mexe no saldo).
        if nova and fatura is not None:
            fatura.atualizar_saldo(self.valor_baixa, salvar=False)

        # 3b) Vínculo M2M pendente (informado na construção / pelo form):
        #     capturado ANTES do save() — o ORM reescreve o `__dict__` com os
        #     valores do banco e o alias `<campo>_ids` é PERDIDO nele.
        ids_vinculo = self.fatura_baixada_ids_dos_dados(self.__dict__)

        # 4) Grava SEM passar pelo save() de Fatura: a baixa não deve criar/
        #    recalcular fatura nem mexer no saldo de novo, e os campos herdados
        #    são somente leitura (não há o que normalizar).
        models.Model.save(self, *args, **kwargs)

        # 4b) Grava o vínculo agora, que a baixa tem pk.
        if ids_vinculo:
            self.fatura_baixada.set(ids_vinculo)
            object.__setattr__(self, 'fatura_baixada_ids', [])

        # 5) Só depois de gravar a baixa, grava o novo saldo da fatura.
        if nova and fatura is not None:
            fatura.save(update_fields=['valor_saldo', 'dt_liquidacao'])

        # Geração de Movimento Bancário se for uma transação do tipo 'banco'.
        # O valor de entrada EMPACOTA: valor_baixa + valor_adicional + as
        # baixas empacotadas — e o movimento guarda a baixa de origem.
        if self.transacao_financeira.movimento == 'banco':
            # Verifica se o campo competencia_bancaria foi preenchido
            if self.competencia_bancaria:
                MovimentoBancario.objects.create(
                    competencia_bancaria=self.competencia_bancaria,
                    transacao_financeira=self.transacao_financeira,
                    valor_entrada=self.valor_total_empacotado(),
                    valor_saida=0,  # Nenhuma saída para esta transação
                    baixa_fatura=self,
                    origem=self.descricao_empacotado(),
                    us_registro=self.us_registro_baixa,
                    estabelecimento=self.estabelecimento_baixa,
                    status='A'  # Define o status como ativo por padrão
                )

