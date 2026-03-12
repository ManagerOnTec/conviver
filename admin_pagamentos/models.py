from datetime import datetime
from django.db import models
from django.contrib.auth import get_user_model
from django.forms import ValidationError
from admin_cadastros.models import Empresa, Estabelecimento, Pessoa
from admin_cadastros_financeiros.models import Conta, TransacaoFinanceira
from admin_tesouraria.models import Caixa
from dominios.choices import status_choices, forma_pagamento_choices
from django.utils import timezone
from datetime import timedelta
from django.utils.timezone import now
from django.apps import apps
from django.core.validators import FileExtensionValidator


User = get_user_model()


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
    


class ClassificacaoPagamento(models.Model):
    descricao = models.CharField(
        max_length=255, verbose_name='Classificacao do Pagamento')

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
        verbose_name = "Classificacao Pagamento"
        verbose_name_plural = "2. Classificação Pagamentos"

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

    def __str__(self):
        return self.descricao





class ParametrosPagamentos(models.Model):
    RECORRENCIA_CHOICES = [
        ('semanal', 'Semanal'),
        ('quinzenal', 'Quinzenal'),
        ('mensal', 'Mensal'),
        ('anual', 'Anual'),
    ]

    fornecedor = models.ForeignKey(
        Fornecedor, on_delete=models.CASCADE, verbose_name='Fornecedor'
    )
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
        help_text='Data inicial para geração das cobranças.'
    )
    data_fim = models.DateField(
        verbose_name='Fim da Recorrência',
        help_text='Data final para geração das cobranças. Deixe em branco para recorrência indefinida.',
        blank=True,
        null=True,
    )
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
        verbose_name = "Parâmetro de Pagamento"
        verbose_name_plural = "4. Parâmetros de Pagamento"


    def __str__(self):
        fornecedor_nome = self.fornecedor.descricao if self.fornecedor else "Fornecedor não definido"
        recorrencia = self.recorrencia if self.recorrencia else "Recorrência não definida"
        valor_previsto = self.valor_previsto if self.valor_previsto else "0.00"
        return f"{fornecedor_nome} - {valor_previsto} ({recorrencia})"



    def gerar_cobrancas(self):
        """
        Gera cobranças recorrentes com base nos parâmetros configurados.
        """
        data_atual = self.data_inicio
        dia_especifico = self.dia_pagamento
        while True:
            # Verifica o limite da recorrência
            if self.data_fim and data_atual > self.data_fim:
                break

            # Cria a cobrança
            Pagamento.objects.create(
                fornecedor=self.fornecedor,
                valor_pagamento=self.valor_previsto,
                dt_vencimento=data_atual,
                estabelecimento=self.fornecedor.estabelecimento_set.first(),
                observacao=f"Cobrança gerada automaticamente ({self.recorrencia})",
                us_registro=self.us_registro,
            )

            # Calcula a próxima data com base na recorrência
            if self.recorrencia == 'semanal':
                data_atual += timedelta(weeks=1)
            elif self.recorrencia == 'quinzenal':
                data_atual += timedelta(weeks=2)
            elif self.recorrencia == 'mensal':
                # Ajusta para o dia específico do mês, se configurado
                if dia_especifico:
                    data_atual = data_atual.replace(day=dia_especifico)
                data_atual += timedelta(days=30)
            elif self.recorrencia == 'anual':
                data_atual = data_atual.replace(year=data_atual.year + 1)

            # Verifica se passou da data final
            if self.data_fim and data_atual > self.data_fim:
                break




class Pagamento(models.Model):
    fornecedor = models.ForeignKey(
        Fornecedor, on_delete=models.CASCADE, verbose_name='Fornecedor')
    
    classificacao_pagamento = models.ForeignKey(
        ClassificacaoFornecedor, on_delete=models.PROTECT, verbose_name='Classificação Pagamento'
    )

    valor_pagamento= models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Valor Pagamento')
   
    valor_saldo = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Saldo', default=0)

    dt_vencimento = models.DateField(
        verbose_name='Data Vencimento', help_text='Informe o Vencimento')
    
    forma_pagamento = models.CharField(
        max_length=1, choices=forma_pagamento_choices, default='A', verbose_name='Forma Pagamento')


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

    previsto_fechado = models.BooleanField(
        blank=True, null=True, verbose_name='Previsto ou Fechado?', help_text='Marque para fechado, desmarque para previsto!'
    )

    dt_liquidacao = models.DateField(
        null=True, blank=True, verbose_name='Data de Liquidação')
    us_registro = models.ForeignKey(
        User, related_name='us_pagamento_registro', on_delete=models.PROTECT)
    dt_registro = models.DateTimeField(default=timezone.now, editable=False)
    us_atualizacao = models.ForeignKey(
        User, related_name='us_pagamento_atualizacao', on_delete=models.PROTECT, blank=True, null=True)
    dt_atualizacao = models.DateTimeField(default=None, blank=True, null=True)

    observacao = models.CharField(max_length=100, blank=True, null=True)

    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT)

    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status')

    class Meta:
        verbose_name = "Pagamento"
        verbose_name_plural = "5. Pagamentos"


    def save(self, *args, **kwargs):
        # Define o saldo inicial como o valor pagamento se for um novo pagamento
        if not self.pk:
            self.valor_saldo = self.valor_pagamento 
        super().save(*args, **kwargs)


    def atualizar_saldo(self, valor_pagamento):
        # Verifica se valor_saldo é None e inicializa com valor_fatura
        if self.valor_saldo is None:
            self.valor_saldo = self.valor_pagamento or 0

        # Atualiza o valor do saldo, descontando o valor baixado
        self.valor_saldo -= valor_pagamento

        if self.valor_saldo <= 0:
            # atualiza a data de liquidacao com data atual
            self.dt_liquidacao = timezone.now().date()

        # Salva o pagamento com o saldo atualizado
        self.save()



    def __str__(self):
        return (f"{self.fornecedor} / Dt.Vencimento: {self.dt_vencimento} / "
                f"Valor: {self.valor_pagamento} / Saldo: {self.valor_saldo} / "
                f"Estabelecimento: {self.estabelecimento}")




class BaixaPagamento(models.Model):
    pagamento = models.ForeignKey(
        'Pagamento', on_delete=models.CASCADE, verbose_name='Pagamento'
    )
    competencia_bancaria = models.ForeignKey(
        'admin_financeiro.CompetenciaBancaria', on_delete=models.PROTECT, verbose_name='Competência', blank=True, null=True
    )
    transacao_financeira = models.ForeignKey(
        TransacaoFinanceira, on_delete=models.PROTECT, verbose_name='Transação Financeira'
    )

     
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
        verbose_name = "Baixa de Pagamento"
        verbose_name_plural = "6. Baixa de Pagamentos"

    def save(self, *args, **kwargs):
        # Atualiza o saldo da fatura quando uma baixa é registrada
        if not self.pk:  # Se for uma nova baixa
            self.pagamento.atualizar_saldo(self.valor_pagamento)
        super(BaixaPagamento, self).save(*args, **kwargs)

        # Geração de Movimento Bancário se for uma transação do tipo 'banco'
        if self.transacao_financeira.movimento == 'banco':
        # Verifica se o campo competencia_bancaria foi preenchido
            if self.competencia_bancaria:
            # Importação dinâmica para evitar importação circular
                from django.apps import apps
                
                MovimentoBancario = apps.get_model('admin_financeiro', 'MovimentoBancario')

                MovimentoBancario.objects.create(
                    competencia_bancaria=self.competencia_bancaria,
                    transacao_financeira=self.transacao_financeira,
                    valor_entrada=0,  # Define o valor de entrada como 0 (confirme se está correto)
                    valor_saida=self.valor_pagamento,  # Define o valor de saída como o valor do pagamento
                    us_registro=self.us_registro,
                    estabelecimento=self.estabelecimento,
                    status='A'  # Define o status como ativo por padrão
                )

    def __str__(self):
        return f"Baixa do pagamento {self.pagamento.id} / Valor: {self.valor_pagamento} / Pago em: {self.dt_pagamento}"
