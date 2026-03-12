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
        verbose_name_plural = '1. Convênios'
        ordering = ['-pk']

    def __str__(self):
        return self.convenio


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

    def save(self, *args, **kwargs):
        if not self.dt_vencimento:
            self.dt_vencimento = self.dia_envio + \
                timedelta(days=self.dias_pagamento)
        super().save(*args, **kwargs)

    def create_fatura(self):
        retencao_percentual = Decimal(
            self.convenio.tx_retencao_nf or 0) / Decimal(100)
        retencao = retencao_percentual * self.valor
        valor_fatura = self.valor - retencao - \
            Decimal(self.convenio.vl_retencao_nf or 0)
        competencia = self.competencia
        dia_envio = self.dia_envio

        # Ajuste do período de tratamento para um mês anterior
        if dia_envio == 1:
            if competencia.month == 1:
                mes_anterior = 12
                ano_anterior = competencia.year - 1
            else:
                mes_anterior = competencia.month - 1
                ano_anterior = competencia.year

            dia_final_mes_anterior = calendar.monthrange(
                ano_anterior, mes_anterior)[1]
            periodo_tratamento = f"Período de 01/{mes_anterior:02d}/{ano_anterior % 100:02d} a {dia_final_mes_anterior}/{mes_anterior:02d}/{ano_anterior % 100:02d}"
        else:
            if competencia.month == 1:
                mes_anterior = 12
                ano_anterior = competencia.year - 1
            else:
                mes_anterior = competencia.month - 1
                ano_anterior = competencia.year

            dia_final_mes_anterior = calendar.monthrange(
                ano_anterior, mes_anterior)[1]
            dia_final = dia_envio - 1
            if dia_final == 0:
                dia_final = dia_final_mes_anterior

            periodo_tratamento = f"Período de {dia_envio}/{mes_anterior:02d}/{ano_anterior % 100:02d} a {dia_final}/{competencia.month:02d}/{competencia.year % 100:02d}"

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
            tx_retencao = (self.convenio.tx_retencao_nf or 0) / \
                100 * self.valor
            vl_retencao = Decimal(self.convenio.vl_retencao_nf or 0)
            self.valor_fatura = self.valor - tx_retencao - vl_retencao

        # Inicializa o valor_saldo com valor_fatura se for None
        if self.valor_saldo is None:
            self.valor_saldo = self.valor_fatura

        super().save(*args, **kwargs)

    def atualizar_saldo(self, valor_baixa):
        # Verifica se valor_saldo é None e inicializa com valor_fatura
        if self.valor_saldo is None:
            self.valor_saldo = self.valor_fatura or 0

        # Atualiza o valor do saldo, descontando o valor baixado
        self.valor_saldo -= valor_baixa

        if self.valor_saldo <= 0:
            # atualiza a data de liquidacao com data atual
            self.dt_liquidacao = timezone.now().date()

        # Salva a fatura com o saldo atualizado
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



# TODO: APOS IMPLANTAR O CAIXA, FIELD COMPETENCIA_CAIXA 

class BaixaFatura(models.Model):
    fatura = models.ForeignKey(Fatura, on_delete=models.PROTECT)
    valor_baixa = models.DecimalField(max_digits=10, decimal_places=2)

    transacao_financeira = models.ForeignKey(
        TransacaoFinanceira, on_delete=models.PROTECT)    

    competencia_bancaria = models.ForeignKey(
        'admin_financeiro.CompetenciaBancaria', on_delete=models.PROTECT, blank=True, null=True)
    dt_recebimento = models.DateField()

    observacao = models.CharField(max_length=255, blank=True, null=True)

    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT, related_name='estab_baixa_fatura')
    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(User, on_delete=models.PROTECT, null=True,
                                    related_name='baixa_fat_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(User, on_delete=models.PROTECT, blank=True,
                                       null=True, related_name='baixa_fat_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status')

    class Meta:
        verbose_name = 'Baixa de Fatura'
        verbose_name_plural = '4. Baixa de Faturas'
        ordering = ['-dt_recebimento']  # Ordena por data de recebimento

    def save(self, *args, **kwargs):
        # Atualiza o saldo da fatura quando uma baixa é registrada
        if not self.pk:  # Se for uma nova baixa
            self.fatura.atualizar_saldo(self.valor_baixa)
        super(BaixaFatura, self).save(*args, **kwargs)

        # Geração de Movimento Bancário se for uma transação do tipo 'banco'
        if self.transacao_financeira.movimento == 'banco':
            # Verifica se o campo competencia_bancaria foi preenchido
            if self.competencia_bancaria:
                MovimentoBancario.objects.create(
                    competencia_bancaria=self.competencia_bancaria,
                    transacao_financeira=self.transacao_financeira,
                    valor_entrada=self.valor_baixa,  # Define o valor de entrada como o valor da baixa
                    valor_saida=0,  # Nenhuma saída para esta transação
                    us_registro=self.us_registro,
                    estabelecimento=self.estabelecimento,
                    status='A'  # Define o status como ativo por padrão
                )

    def __str__(self):
        return f"{self.fatura.id} / Valor: {self.valor_baixa} / Recebimento: {self.dt_recebimento}"

