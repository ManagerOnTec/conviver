from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from admin_cadastros.models import Estabelecimento
from decimal import Decimal
from datetime import date


class CartaoPagamento(models.Model):
    """Modelo de Cartão de Pagamento"""
    TIPO_CHOICES = [
        ('CREDITO', 'Crédito'),
        ('DEBITO', 'Débito'),
    ]
    
    BANDEIRA_CHOICES = [
        ('VISA', 'Visa'),
        ('MASTERCARD', 'Mastercard'),
        ('ELO', 'Elo'),
        ('AMEX', 'American Express'),
        ('DINERS', 'Diners'),
        ('OUTRA', 'Outra'),
    ]
    
    STATUS_CHOICES = [
        ('A', 'Ativo'),
        ('I', 'Inativo'),
    ]
    
    estabelecimento = models.ForeignKey(
        Estabelecimento,
        on_delete=models.PROTECT,
        related_name='cartoes_pagamento'
    )
    descricao = models.CharField(max_length=255)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    numero_cartao = models.CharField(max_length=20, unique=True)
    bandeira = models.CharField(max_length=20, choices=BANDEIRA_CHOICES)
    limite = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    dia_fechamento = models.IntegerField(default=10)
    dia_vencimento = models.IntegerField(default=20)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='A')
    
    us_registro = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='cartoes_pagamento_criados'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    us_atualizacao = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cartoes_pagamento_atualizados'
    )
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Cartão de Pagamento'
        verbose_name_plural = 'Cartões de Pagamento'
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"{self.descricao} - {self.bandeira}"


class TransacaoCartao(models.Model):
    """Modelo de Transação do Cartão"""
    STATUS_CHOICES = [
        ('A', 'Ativo'),
        ('C', 'Cancelado'),
    ]
    
    cartao = models.ForeignKey(
        CartaoPagamento,
        on_delete=models.CASCADE,
        related_name='transacoes'
    )
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=15, decimal_places=2)
    data_transacao = models.DateField()
    categoria = models.CharField(max_length=100, blank=True, null=True)
    fornecedor = models.CharField(max_length=255, blank=True, null=True)
    numero_documento = models.CharField(max_length=50, blank=True, null=True)
    nota_fiscal = models.FileField(
        upload_to='cartao/notas_fiscais/%Y/%m/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'peg'])]
    )
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='A')
    
    us_registro = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='transacoes_cartao_criadas'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    us_atualizacao = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transacoes_cartao_atualizadas'
    )
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Transação de Cartão'
        verbose_name_plural = 'Transações de Cartão'
        ordering = ['-data_transacao']
    
    def __str__(self):
        return f"{self.cartao.descricao} - R$ {self.valor}"


class FaturaCartao(models.Model):
    """Modelo de Fatura do Cartão"""
    STATUS_CHOICES = [
        ('ABERTA', 'Aberta'),
        ('FECHADA', 'Fechada'),
        ('PAGA', 'Paga'),
        ('PARCIAL', 'Parcialmente Paga'),
    ]
    
    cartao = models.ForeignKey(
        CartaoPagamento,
        on_delete=models.CASCADE,
        related_name='faturas'
    )
    mes_referencia = models.DateField()
    data_fechamento = models.DateField()
    data_vencimento = models.DateField()
    valor_total = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    valor_pago = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ABERTA')
    
    us_registro = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='faturas_cartao_criadas'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    us_atualizacao = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='faturas_cartao_atualizadas'
    )
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Fatura de Cartão'
        verbose_name_plural = 'Faturas de Cartão'
        ordering = ['-mes_referencia']
        unique_together = ('cartao', 'mes_referencia')
    
    def __str__(self):
        return f"Fatura {self.cartao.descricao} - {self.mes_referencia}"
    
    def calcular_saldo_pendente(self):
        """Calcula o saldo pendente da fatura"""
        return self.valor_total - self.valor_pago


class PagamentoCartao(models.Model):
    """Modelo de Pagamento de Fatura do Cartão"""
    FORMA_PAGAMENTO_CHOICES = [
        ('DINHEIRO', 'Dinheiro'),
        ('CHEQUE', 'Cheque'),
        ('TRANSFERENCIA', 'Transferência'),
        ('BOLETO', 'Boleto'),
        ('OUTRO', 'Outro'),
    ]
    
    STATUS_CHOICES = [
        ('A', 'Ativo'),
        ('C', 'Cancelado'),
    ]
    
    fatura = models.ForeignKey(
        FaturaCartao,
        on_delete=models.CASCADE,
        related_name='pagamentos'
    )
    valor_pagamento = models.DecimalField(max_digits=15, decimal_places=2)
    data_pagamento = models.DateField()
    forma_pagamento = models.CharField(max_length=20, choices=FORMA_PAGAMENTO_CHOICES)
    numero_documento = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='A')
    
    us_registro = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='pagamentos_cartao_criados'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    us_atualizacao = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pagamentos_cartao_atualizados'
    )
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Pagamento de Cartão'
        verbose_name_plural = 'Pagamentos de Cartão'
        ordering = ['-data_pagamento']
    
    def __str__(self):
        return f"Pagamento R$ {self.valor_pagamento} - {self.data_pagamento}"
