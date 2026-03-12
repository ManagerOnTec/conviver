from django.db import models
from django.contrib.auth.models import User
from admin_cadastros.models import Estabelecimento
from admin_faturas.models import Fatura
from admin_pagamentos.models import Pagamento
from decimal import Decimal
from datetime import date


class ExtratoBancario(models.Model):
    """Modelo de Extrato Bancário para Conciliação"""
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('CONCILIADO', 'Conciliado'),
        ('PARCIAL', 'Parcialmente Conciliado'),
    ]
    
    TIPO_ARQUIVO_CHOICES = [
        ('CSV', 'CSV'),
        ('XLS', 'XLS'),
        ('PDF', 'PDF'),
    ]
    
    estabelecimento = models.ForeignKey(
        Estabelecimento,
        on_delete=models.PROTECT,
        related_name='extratos_bancarios'
    )
    numero_banco = models.CharField(max_length=10)
    numero_agencia = models.CharField(max_length=10)
    numero_conta = models.CharField(max_length=20)
    data_inicio = models.DateField()
    data_fim = models.DateField()
    saldo_inicial = models.DecimalField(max_digits=15, decimal_places=2)
    saldo_final = models.DecimalField(max_digits=15, decimal_places=2)
    tipo_arquivo = models.CharField(max_length=10, choices=TIPO_ARQUIVO_CHOICES)
    arquivo = models.FileField(upload_to='extratos_bancarios/%Y/%m/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    
    us_registro = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='extratos_bancarios_criados'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    us_atualizacao = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='extratos_bancarios_atualizados'
    )
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Extrato Bancário'
        verbose_name_plural = 'Extratos Bancários'
        ordering = ['-data_fim']
        unique_together = ('numero_banco', 'numero_agencia', 'numero_conta', 'data_inicio', 'data_fim')
    
    def __str__(self):
        return f"Extrato {self.numero_banco}/{self.numero_agencia}/{self.numero_conta} - {self.data_fim}"


class LancamentoBancario(models.Model):
    """Modelo de Lançamento Bancário do Extrato"""
    TIPO_CHOICES = [
        ('CREDITO', 'Crédito'),
        ('DEBITO', 'Débito'),
    ]
    
    extrato = models.ForeignKey(
        ExtratoBancario,
        on_delete=models.CASCADE,
        related_name='lancamentos'
    )
    data_lancamento = models.DateField()
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    valor = models.DecimalField(max_digits=15, decimal_places=2)
    descricao = models.CharField(max_length=255)
    numero_documento = models.CharField(max_length=50, blank=True, null=True)
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Lançamento Bancário'
        verbose_name_plural = 'Lançamentos Bancários'
        ordering = ['-data_lancamento']
    
    def __str__(self):
        return f"{self.tipo} - R$ {self.valor} - {self.descricao}"


class Conciliacao(models.Model):
    """Modelo de Conciliação entre Lançamentos e Transações"""
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('CONCILIADO', 'Conciliado'),
        ('REJEITADO', 'Rejeitado'),
    ]
    
    TIPO_TRANSACAO_CHOICES = [
        ('FATURA', 'Fatura'),
        ('PAGAMENTO', 'Pagamento'),
        ('MOVIMENTACAO_CAIXA', 'Movimentação de Caixa'),
    ]
    
    lancamento_bancario = models.ForeignKey(
        LancamentoBancario,
        on_delete=models.CASCADE,
        related_name='conciliacoes'
    )
    tipo_transacao = models.CharField(max_length=20, choices=TIPO_TRANSACAO_CHOICES)
    
    # ForeignKeys para diferentes tipos de transação
    fatura = models.ForeignKey(
        Fatura,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conciliacoes'
    )
    pagamento = models.ForeignKey(
        Pagamento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conciliacoes'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    observacao = models.TextField(blank=True, null=True)
    
    us_registro = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='conciliacoes_criadas'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    us_atualizacao = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conciliacoes_atualizadas'
    )
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Conciliação'
        verbose_name_plural = 'Conciliações'
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"Conciliação {self.id} - {self.status}"


class RelatorioConciliacao(models.Model):
    """Modelo de Relatório de Conciliação"""
    STATUS_CHOICES = [
        ('RASCUNHO', 'Rascunho'),
        ('FINALIZADO', 'Finalizado'),
        ('APROVADO', 'Aprovado'),
    ]
    
    estabelecimento = models.ForeignKey(
        Estabelecimento,
        on_delete=models.PROTECT,
        related_name='relatorios_conciliacao'
    )
    extrato = models.ForeignKey(
        ExtratoBancario,
        on_delete=models.CASCADE,
        related_name='relatorios'
    )
    data_inicio = models.DateField()
    data_fim = models.DateField()
    total_lancamentos = models.IntegerField(default=0)
    total_conciliado = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    total_pendente = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='RASCUNHO')
    
    us_registro = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='relatorios_conciliacao_criados'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    us_atualizacao = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='relatorios_conciliacao_atualizados'
    )
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Relatório de Conciliação'
        verbose_name_plural = 'Relatórios de Conciliação'
        ordering = ['-data_fim']
    
    def __str__(self):
        return f"Relatório {self.data_inicio} a {self.data_fim}"
