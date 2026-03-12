from django.db import models
from django.contrib.auth.models import User
from admin_cadastros.models import Estabelecimento
from decimal import Decimal
from datetime import date


class Tesouraria(models.Model):
    """Modelo principal de Tesouraria"""
    STATUS_CHOICES = [
        ('A', 'Ativo'),
        ('I', 'Inativo'),
    ]
    
    estabelecimento = models.ForeignKey(
        Estabelecimento,
        on_delete=models.PROTECT,
        related_name='tesourarias'
    )
    descricao = models.CharField(max_length=255)
    numero_tesouraria = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='A')
    
    us_registro = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='tesourarias_criadas'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    us_atualizacao = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tesourarias_atualizadas'
    )
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Tesouraria'
        verbose_name_plural = 'Tesourarias'
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"{self.numero_tesouraria} - {self.descricao}"


class Caixa(models.Model):
    """Modelo de Caixa da Tesouraria"""
    STATUS_CHOICES = [
        ('A', 'Ativo'),
        ('I', 'Inativo'),
    ]
    
    tesouraria = models.ForeignKey(
        Tesouraria,
        on_delete=models.CASCADE,
        related_name='caixas'
    )
    descricao = models.CharField(max_length=255)
    numero_caixa = models.CharField(max_length=50)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='A')
    
    us_registro = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='caixas_criados'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    us_atualizacao = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='caixas_atualizados'
    )
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Caixa'
        verbose_name_plural = 'Caixas'
        ordering = ['-data_criacao']
        unique_together = ('tesouraria', 'numero_caixa')
    
    def __str__(self):
        return f"Caixa {self.numero_caixa} - {self.descricao}"


class SaldoCaixa(models.Model):
    """Modelo de Saldo de Caixa por dia"""
    STATUS_CHOICES = [
        ('A', 'Aberto'),
        ('F', 'Fechado'),
    ]
    
    caixa = models.ForeignKey(
        Caixa,
        on_delete=models.CASCADE,
        related_name='saldos'
    )
    data_abertura = models.DateField(default=date.today)
    saldo_inicial = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    saldo_final = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='A')
    
    us_registro = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='saldos_caixa_criados'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    us_atualizacao = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='saldos_caixa_atualizados'
    )
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Saldo de Caixa'
        verbose_name_plural = 'Saldos de Caixa'
        ordering = ['-data_abertura']
        unique_together = ('caixa', 'data_abertura')
    
    def __str__(self):
        return f"{self.caixa.numero_caixa} - {self.data_abertura}"
    
    def calcular_saldo_final(self):
        """Calcula o saldo final baseado nas movimentações"""
        entradas = self.movimentacoes.filter(tipo='ENTRADA').aggregate(
            total=models.Sum('valor')
        )['total'] or Decimal('0.00')
        
        saidas = self.movimentacoes.filter(tipo='SAIDA').aggregate(
            total=models.Sum('valor')
        )['total'] or Decimal('0.00')
        
        return self.saldo_inicial + entradas - saidas


class MovimentacaoCaixa(models.Model):
    """Modelo de Movimentação de Caixa"""
    TIPO_CHOICES = [
        ('ENTRADA', 'Entrada'),
        ('SAIDA', 'Saída'),
    ]
    
    ORIGEM_CHOICES = [
        ('BANCO', 'Banco'),
        ('RECEBIMENTO', 'Recebimento'),
        ('PAGAMENTO', 'Pagamento'),
        ('SAQUE', 'Saque'),
        ('OUTRA', 'Outra'),
    ]
    
    STATUS_CHOICES = [
        ('A', 'Ativo'),
        ('C', 'Cancelado'),
    ]
    
    saldo_caixa = models.ForeignKey(
        SaldoCaixa,
        on_delete=models.CASCADE,
        related_name='movimentacoes'
    )
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    origem = models.CharField(max_length=20, choices=ORIGEM_CHOICES)
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=15, decimal_places=2)
    numero_documento = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='A')
    
    us_registro = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='movimentacoes_caixa_criadas'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    us_atualizacao = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimentacoes_caixa_atualizadas'
    )
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Movimentação de Caixa'
        verbose_name_plural = 'Movimentações de Caixa'
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"{self.tipo} - R$ {self.valor} - {self.descricao}"
