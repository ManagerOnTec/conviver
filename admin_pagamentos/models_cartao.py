from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from admin_cadastros.models import Estabelecimento
from admin_cadastros_financeiros.models import Conta
from dominios.choices import status_choices
from decimal import Decimal
from django.core.validators import FileExtensionValidator

User = get_user_model()


class CartaoPagamento(models.Model):
    """
    Modelo para representar um cartão de crédito/débito da empresa.
    """
    TIPO_CARTAO_CHOICES = [
        ('CREDITO', 'Crédito'),
        ('DEBITO', 'Débito'),
    ]
    
    descricao = models.CharField(
        max_length=255,
        verbose_name='Descrição do Cartão'
    )
    
    tipo = models.CharField(
        max_length=10,
        choices=TIPO_CARTAO_CHOICES,
        default='CREDITO',
        verbose_name='Tipo de Cartão'
    )
    
    numero_cartao = models.CharField(
        max_length=20,
        verbose_name='Número do Cartão (últimos 4 dígitos)',
        unique=True
    )
    
    bandeira = models.CharField(
        max_length=50,
        verbose_name='Bandeira',
        help_text='Ex: Visa, Mastercard, Elo, etc.'
    )
    
    estabelecimento = models.ForeignKey(
        Estabelecimento,
        on_delete=models.PROTECT,
        verbose_name='Estabelecimento'
    )
    
    conta_bancaria = models.ForeignKey(
        Conta,
        on_delete=models.PROTECT,
        verbose_name='Conta Bancária',
        help_text='Conta onde será feito o pagamento do cartão'
    )
    
    limite = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Limite do Cartão',
        blank=True,
        null=True
    )
    
    dia_fechamento = models.PositiveIntegerField(
        verbose_name='Dia de Fechamento',
        help_text='Dia do mês em que a fatura é fechada',
        default=10
    )
    
    dia_vencimento = models.PositiveIntegerField(
        verbose_name='Dia de Vencimento',
        help_text='Dia do mês em que a fatura vence',
        default=20
    )
    
    observacao = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observações'
    )
    
    us_registro = models.ForeignKey(
        User,
        related_name='us_cartao_registro',
        on_delete=models.PROTECT
    )
    dt_registro = models.DateTimeField(
        default=timezone.now,
        editable=False
    )
    us_atualizacao = models.ForeignKey(
        User,
        related_name='us_cartao_atualizacao',
        on_delete=models.PROTECT,
        blank=True,
        null=True
    )
    dt_atualizacao = models.DateTimeField(
        default=None,
        blank=True,
        null=True
    )
    
    status = models.CharField(
        max_length=1,
        choices=status_choices,
        default='A',
        verbose_name='Status'
    )

    class Meta:
        verbose_name = "Cartão de Pagamento"
        verbose_name_plural = "1. Cartões de Pagamento"
        ordering = ['descricao']

    def __str__(self):
        return f"{self.descricao} ({self.bandeira})"


class TransacaoCartao(models.Model):
    """
    Modelo para registrar cada transação individual do cartão.
    """
    cartao = models.ForeignKey(
        CartaoPagamento,
        on_delete=models.PROTECT,
        verbose_name='Cartão',
        related_name='transacoes'
    )
    
    descricao = models.CharField(
        max_length=255,
        verbose_name='Descrição da Transação'
    )
    
    valor = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Valor'
    )
    
    data_transacao = models.DateField(
        default=timezone.now,
        verbose_name='Data da Transação'
    )
    
    categoria = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Categoria'
    )
    
    fornecedor = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Fornecedor/Estabelecimento'
    )
    
    numero_documento = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Número do Documento'
    )
    
    nota_fiscal = models.FileField(
        upload_to='cartao/notas_fiscais/',
        blank=True,
        null=True,
        verbose_name='Nota Fiscal',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'peg'])]
    )
    
    observacao = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observações'
    )
    
    us_registro = models.ForeignKey(
        User,
        related_name='us_transacao_cartao_registro',
        on_delete=models.PROTECT
    )
    dt_registro = models.DateTimeField(
        default=timezone.now,
        editable=False
    )
    us_atualizacao = models.ForeignKey(
        User,
        related_name='us_transacao_cartao_atualizacao',
        on_delete=models.PROTECT,
        blank=True,
        null=True
    )
    dt_atualizacao = models.DateTimeField(
        default=None,
        blank=True,
        null=True
    )
    
    status = models.CharField(
        max_length=1,
        choices=status_choices,
        default='A',
        verbose_name='Status'
    )

    class Meta:
        verbose_name = "Transação de Cartão"
        verbose_name_plural = "2. Transações de Cartão"
        ordering = ['-data_transacao']

    def __str__(self):
        return f"{self.cartao.descricao} - {self.valor} - {self.data_transacao}"


class FaturaCartao(models.Model):
    """
    Modelo para representar uma fatura de cartão.
    Agrupa transações de um período específico.
    """
    STATUS_FATURA_CHOICES = [
        ('ABERTA', 'Aberta'),
        ('FECHADA', 'Fechada'),
        ('PAGA', 'Paga'),
        ('PARCIAL', 'Paga Parcialmente'),
    ]
    
    cartao = models.ForeignKey(
        CartaoPagamento,
        on_delete=models.PROTECT,
        verbose_name='Cartão',
        related_name='faturas'
    )
    
    mes_referencia = models.DateField(
        verbose_name='Mês de Referência',
        help_text='Primeiro dia do mês da fatura'
    )
    
    data_fechamento = models.DateField(
        verbose_name='Data de Fechamento'
    )
    
    data_vencimento = models.DateField(
        verbose_name='Data de Vencimento'
    )
    
    valor_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Valor Total',
        default=Decimal('0.00')
    )
    
    valor_pago = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Valor Pago',
        default=Decimal('0.00')
    )
    
    status = models.CharField(
        max_length=10,
        choices=STATUS_FATURA_CHOICES,
        default='ABERTA',
        verbose_name='Status da Fatura'
    )
    
    observacao = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observações'
    )
    
    us_registro = models.ForeignKey(
        User,
        related_name='us_fatura_cartao_registro',
        on_delete=models.PROTECT
    )
    dt_registro = models.DateTimeField(
        default=timezone.now,
        editable=False
    )
    us_atualizacao = models.ForeignKey(
        User,
        related_name='us_fatura_cartao_atualizacao',
        on_delete=models.PROTECT,
        blank=True,
        null=True
    )
    dt_atualizacao = models.DateTimeField(
        default=None,
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = "Fatura de Cartão"
        verbose_name_plural = "3. Faturas de Cartão"
        ordering = ['-mes_referencia']
        unique_together = [['cartao', 'mes_referencia']]

    def __str__(self):
        return f"{self.cartao.descricao} - {self.mes_referencia.strftime('%m/%Y')}"

    def calcular_total(self):
        """Calcula o total da fatura a partir das transações"""
        total = self.transacoes.filter(status='A').aggregate(
            total=models.Sum('valor')
        )['total'] or Decimal('0.00')
        self.valor_total = total
        self.save()

    @property
    def saldo_devedor(self):
        """Retorna o saldo devedor (valor total - valor pago)"""
        return self.valor_total - self.valor_pago


class PagamentoCartao(models.Model):
    """
    Modelo para registrar pagamentos de faturas de cartão.
    Cada pagamento pode ser total ou parcial.
    """
    fatura = models.ForeignKey(
        FaturaCartao,
        on_delete=models.PROTECT,
        verbose_name='Fatura',
        related_name='pagamentos'
    )
    
    valor_pagamento = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Valor do Pagamento'
    )
    
    data_pagamento = models.DateField(
        default=timezone.now,
        verbose_name='Data do Pagamento'
    )
    
    forma_pagamento = models.CharField(
        max_length=50,
        verbose_name='Forma de Pagamento',
        help_text='Ex: Transferência, Débito, etc.'
    )
    
    numero_documento = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Número do Documento'
    )
    
    observacao = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observações'
    )
    
    us_registro = models.ForeignKey(
        User,
        related_name='us_pagamento_cartao_registro',
        on_delete=models.PROTECT
    )
    dt_registro = models.DateTimeField(
        default=timezone.now,
        editable=False
    )
    us_atualizacao = models.ForeignKey(
        User,
        related_name='us_pagamento_cartao_atualizacao',
        on_delete=models.PROTECT,
        blank=True,
        null=True
    )
    dt_atualizacao = models.DateTimeField(
        default=None,
        blank=True,
        null=True
    )
    
    status = models.CharField(
        max_length=1,
        choices=status_choices,
        default='A',
        verbose_name='Status'
    )

    class Meta:
        verbose_name = "Pagamento de Cartão"
        verbose_name_plural = "4. Pagamentos de Cartão"
        ordering = ['-data_pagamento']

    def __str__(self):
        return f"{self.fatura.cartao.descricao} - R$ {self.valor_pagamento} - {self.data_pagamento}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Atualiza status da fatura
        self._atualizar_status_fatura()

    def _atualizar_status_fatura(self):
        """Atualiza o status da fatura baseado nos pagamentos"""
        fatura = self.fatura
        total_pago = fatura.pagamentos.filter(status='A').aggregate(
            total=models.Sum('valor_pagamento')
        )['total'] or Decimal('0.00')
        
        fatura.valor_pago = total_pago
        
        if total_pago >= fatura.valor_total:
            fatura.status = 'PAGA'
        elif total_pago > 0:
            fatura.status = 'PARCIAL'
        
        fatura.save()
