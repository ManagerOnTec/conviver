from django.db import models
from django.contrib.auth.models import User
from admin_faturas.models import Fatura
from admin_pagamentos.models import Pagamento
from appconciliacao.models import Conciliacao
from decimal import Decimal
from datetime import date


class BaixaFatura(models.Model):
    """Modelo de Baixa de Fatura"""
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('PARCIAL', 'Parcialmente Baixada'),
        ('TOTAL', 'Totalmente Baixada'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    TIPO_BAIXA_CHOICES = [
        ('PAGAMENTO', 'Pagamento'),
        ('DEVOLUCAO', 'Devolução'),
        ('CANCELAMENTO', 'Cancelamento'),
        ('DESCONTO', 'Desconto'),
        ('OUTRO', 'Outro'),
    ]
    
    fatura = models.ForeignKey(
        Fatura,
        on_delete=models.CASCADE,
        related_name='baixas'
    )
    tipo_baixa = models.CharField(max_length=20, choices=TIPO_BAIXA_CHOICES)
    valor_baixa = models.DecimalField(max_digits=15, decimal_places=2)
    data_baixa = models.DateField(default=date.today)
    numero_documento = models.CharField(max_length=50, blank=True, null=True)
    descricao = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    
    # Integração com Conciliação
    conciliacao = models.ForeignKey(
        Conciliacao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='baixas_fatura'
    )
    
    us_registro = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='baixas_fatura_criadas'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    us_atualizacao = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='baixas_fatura_atualizadas'
    )
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Baixa de Fatura'
        verbose_name_plural = 'Baixas de Fatura'
        ordering = ['-data_baixa']
    
    def __str__(self):
        return f"Baixa {self.fatura.numero_fatura} - R$ {self.valor_baixa}"


class BaixaPagamento(models.Model):
    """Modelo de Baixa de Pagamento"""
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('CONCILIADO', 'Conciliado'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    TIPO_BAIXA_CHOICES = [
        ('RECEBIMENTO', 'Recebimento'),
        ('DEVOLUCAO', 'Devolução'),
        ('CANCELAMENTO', 'Cancelamento'),
        ('DESCONTO', 'Desconto'),
        ('OUTRO', 'Outro'),
    ]
    
    pagamento = models.ForeignKey(
        Pagamento,
        on_delete=models.CASCADE,
        related_name='baixas'
    )
    tipo_baixa = models.CharField(max_length=20, choices=TIPO_BAIXA_CHOICES)
    valor_baixa = models.DecimalField(max_digits=15, decimal_places=2)
    data_baixa = models.DateField(default=date.today)
    numero_documento = models.CharField(max_length=50, blank=True, null=True)
    descricao = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    
    # Integração com Conciliação
    conciliacao = models.ForeignKey(
        Conciliacao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='baixas_pagamento'
    )
    
    us_registro = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='baixas_pagamento_criadas'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    us_atualizacao = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='baixas_pagamento_atualizadas'
    )
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Baixa de Pagamento'
        verbose_name_plural = 'Baixas de Pagamento'
        ordering = ['-data_baixa']
    
    def __str__(self):
        return f"Baixa {self.pagamento.numero_documento} - R$ {self.valor_baixa}"


class ProcessoBaixa(models.Model):
    """Modelo de Processo de Baixa para rastreamento"""
    STATUS_CHOICES = [
        ('INICIADO', 'Iniciado'),
        ('PROCESSANDO', 'Processando'),
        ('CONCLUIDO', 'Concluído'),
        ('ERRO', 'Erro'),
    ]
    
    TIPO_PROCESSO_CHOICES = [
        ('FATURA', 'Fatura'),
        ('PAGAMENTO', 'Pagamento'),
    ]
    
    tipo_processo = models.CharField(max_length=20, choices=TIPO_PROCESSO_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='INICIADO')
    
    # Referências para diferentes tipos
    baixa_fatura = models.ForeignKey(
        BaixaFatura,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processos'
    )
    baixa_pagamento = models.ForeignKey(
        BaixaPagamento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processos'
    )
    
    mensagem_erro = models.TextField(blank=True, null=True)
    total_itens = models.IntegerField(default=0)
    itens_processados = models.IntegerField(default=0)
    
    us_registro = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='processos_baixa_criados'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_conclusao = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Processo de Baixa'
        verbose_name_plural = 'Processos de Baixa'
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"Processo {self.id} - {self.status}"


class RelatorioBaixa(models.Model):
    """Modelo de Relatório de Baixa"""
    STATUS_CHOICES = [
        ('RASCUNHO', 'Rascunho'),
        ('FINALIZADO', 'Finalizado'),
        ('APROVADO', 'Aprovado'),
    ]
    
    data_inicio = models.DateField()
    data_fim = models.DateField()
    total_baixas_fatura = models.IntegerField(default=0)
    total_baixas_pagamento = models.IntegerField(default=0)
    valor_total_baixado = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='RASCUNHO')
    observacao = models.TextField(blank=True, null=True)
    
    us_registro = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='relatorios_baixa_criados'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    us_atualizacao = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='relatorios_baixa_atualizados'
    )
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Relatório de Baixa'
        verbose_name_plural = 'Relatórios de Baixa'
        ordering = ['-data_fim']
    
    def __str__(self):
        return f"Relatório {self.data_inicio} a {self.data_fim}"
