from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from admin_cadastros_financeiros.models import Conta
from admin_financeiro.models import CompetenciaBancaria, MovimentoBancario
from admin_cadastros.models import Estabelecimento
from dominios.choices import status_choices
from decimal import Decimal

User = get_user_model()


class ExtratoBancario(models.Model):
    """
    Modelo para armazenar os extratos bancários importados.
    Cada extrato é associado a uma competência bancária específica.
    """
    
    TIPO_ARQUIVO_CHOICES = [
        ('CSV', 'CSV'),
        ('OFX', 'OFX'),
        ('MANUAL', 'Manual'),
    ]
    
    competencia_bancaria = models.ForeignKey(
        CompetenciaBancaria,
        on_delete=models.PROTECT,
        verbose_name='Competência Bancária'
    )
    
    conta = models.ForeignKey(
        Conta,
        on_delete=models.PROTECT,
        verbose_name='Conta Bancária'
    )
    
    arquivo = models.FileField(
        upload_to='extratos_bancarios/',
        verbose_name='Arquivo do Extrato',
        blank=True,
        null=True
    )
    
    tipo_arquivo = models.CharField(
        max_length=10,
        choices=TIPO_ARQUIVO_CHOICES,
        default='CSV',
        verbose_name='Tipo de Arquivo'
    )
    
    data_extrato_inicio = models.DateField(
        verbose_name='Data Início do Extrato'
    )
    
    data_extrato_fim = models.DateField(
        verbose_name='Data Fim do Extrato'
    )
    
    saldo_inicial = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Saldo Inicial do Extrato'
    )
    
    saldo_final = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Saldo Final do Extrato'
    )
    
    total_entradas = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Total de Entradas'
    )
    
    total_saidas = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Total de Saídas'
    )
    
    quantidade_transacoes = models.PositiveIntegerField(
        default=0,
        verbose_name='Quantidade de Transações'
    )
    
    observacao = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observações'
    )
    
    us_registro = models.ForeignKey(
        User,
        related_name='us_extrato_registro',
        on_delete=models.PROTECT
    )
    dt_registro = models.DateTimeField(
        default=timezone.now,
        editable=False
    )
    
    us_atualizacao = models.ForeignKey(
        User,
        related_name='us_extrato_atualizacao',
        on_delete=models.PROTECT,
        blank=True,
        null=True
    )
    dt_atualizacao = models.DateTimeField(
        default=None,
        blank=True,
        null=True
    )
    
    estabelecimento = models.ForeignKey(
        Estabelecimento,
        on_delete=models.PROTECT
    )
    
    status = models.CharField(
        max_length=1,
        choices=status_choices,
        default='A',
        verbose_name='Status'
    )
    
    class Meta:
        verbose_name = 'Extrato Bancário'
        verbose_name_plural = '1. Extratos Bancários'
        ordering = ['-dt_registro']
    
    def __str__(self):
        return f"{self.conta} - {self.data_extrato_inicio} a {self.data_extrato_fim}"


class TransacaoExtrato(models.Model):
    """
    Modelo para armazenar cada transação individual do extrato bancário.
    """
    
    TIPO_TRANSACAO_CHOICES = [
        ('D', 'Débito'),
        ('C', 'Crédito'),
    ]
    
    extrato_bancario = models.ForeignKey(
        ExtratoBancario,
        on_delete=models.CASCADE,
        related_name='transacoes',
        verbose_name='Extrato Bancário'
    )
    
    data_transacao = models.DateField(
        verbose_name='Data da Transação'
    )
    
    data_lancamento = models.DateField(
        verbose_name='Data de Lançamento',
        blank=True,
        null=True
    )
    
    descricao = models.CharField(
        max_length=255,
        verbose_name='Descrição'
    )
    
    tipo_transacao = models.CharField(
        max_length=1,
        choices=TIPO_TRANSACAO_CHOICES,
        verbose_name='Tipo de Transação'
    )
    
    valor = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Valor'
    )
    
    numero_documento = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Número do Documento'
    )
    
    referencia_banco = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Referência do Banco'
    )
    
    observacao = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observações'
    )
    
    conciliada = models.BooleanField(
        default=False,
        verbose_name='Conciliada?'
    )
    
    dt_registro = models.DateTimeField(
        default=timezone.now,
        editable=False
    )
    
    class Meta:
        verbose_name = 'Transação do Extrato'
        verbose_name_plural = '2. Transações do Extrato'
        ordering = ['data_transacao', 'id']
        indexes = [
            models.Index(fields=['extrato_bancario', 'conciliada']),
            models.Index(fields=['data_transacao']),
        ]
    
    def __str__(self):
        tipo = 'Débito' if self.tipo_transacao == 'D' else 'Crédito'
        return f"{self.data_transacao} - {tipo} - {self.valor} - {self.descricao[:50]}"


class Conciliacao(models.Model):
    """
    Modelo central que registra a conciliação entre transações do extrato
    e movimentos bancários internos do sistema.
    """
    
    STATUS_CONCILIACAO_CHOICES = [
        ('P', 'Pendente'),
        ('C', 'Conciliado'),
        ('D', 'Divergente'),
        ('A', 'Anulado'),
    ]
    
    transacao_extrato = models.ForeignKey(
        TransacaoExtrato,
        on_delete=models.PROTECT,
        verbose_name='Transação do Extrato'
    )
    
    movimento_bancario = models.ForeignKey(
        MovimentoBancario,
        on_delete=models.PROTECT,
        verbose_name='Movimento Bancário',
        blank=True,
        null=True
    )
    
    competencia_bancaria = models.ForeignKey(
        CompetenciaBancaria,
        on_delete=models.PROTECT,
        verbose_name='Competência Bancária'
    )
    
    valor_conciliado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Valor Conciliado'
    )
    
    diferenca = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Diferença'
    )
    
    status = models.CharField(
        max_length=1,
        choices=STATUS_CONCILIACAO_CHOICES,
        default='P',
        verbose_name='Status da Conciliação'
    )
    
    motivo_divergencia = models.TextField(
        blank=True,
        null=True,
        verbose_name='Motivo da Divergência'
    )
    
    observacao = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observações'
    )
    
    us_registro = models.ForeignKey(
        User,
        related_name='us_conciliacao_registro',
        on_delete=models.PROTECT
    )
    dt_registro = models.DateTimeField(
        default=timezone.now,
        editable=False
    )
    
    us_atualizacao = models.ForeignKey(
        User,
        related_name='us_conciliacao_atualizacao',
        on_delete=models.PROTECT,
        blank=True,
        null=True
    )
    dt_atualizacao = models.DateTimeField(
        default=None,
        blank=True,
        null=True
    )
    
    estabelecimento = models.ForeignKey(
        Estabelecimento,
        on_delete=models.PROTECT
    )
    
    class Meta:
        verbose_name = 'Conciliação'
        verbose_name_plural = '3. Conciliações'
        ordering = ['-dt_registro']
        indexes = [
            models.Index(fields=['status', 'competencia_bancaria']),
            models.Index(fields=['transacao_extrato']),
            models.Index(fields=['movimento_bancario']),
        ]
    
    def __str__(self):
        status_display = dict(self.STATUS_CONCILIACAO_CHOICES).get(self.status, self.status)
        return f"Conciliação {self.id} - {status_display} - {self.valor_conciliado}"
    
    def calcular_diferenca(self):
        """
        Calcula a diferença entre o valor do extrato e o valor conciliado.
        """
        if self.movimento_bancario:
            valor_movimento = self.movimento_bancario.valor_entrada or self.movimento_bancario.valor_saida or Decimal('0.00')
            self.diferenca = self.transacao_extrato.valor - valor_movimento
        else:
            self.diferenca = Decimal('0.00')
    
    def save(self, *args, **kwargs):
        self.calcular_diferenca()
        super().save(*args, **kwargs)


class DivergenciaConciliacao(models.Model):
    """
    Modelo para registrar divergências encontradas durante a conciliação.
    Permite rastrear problemas e criar ações corretivas.
    """
    
    TIPO_DIVERGENCIA_CHOICES = [
        ('VALOR', 'Diferença de Valor'),
        ('DATA', 'Diferença de Data'),
        ('FALTANTE', 'Transação Faltante no Sistema'),
        ('EXCEDENTE', 'Transação Excedente no Sistema'),
        ('DUPLICADA', 'Transação Duplicada'),
        ('OUTRO', 'Outro'),
    ]
    
    PRIORIDADE_CHOICES = [
        ('A', 'Alta'),
        ('M', 'Média'),
        ('B', 'Baixa'),
    ]
    
    conciliacao = models.ForeignKey(
        Conciliacao,
        on_delete=models.CASCADE,
        related_name='divergencias',
        verbose_name='Conciliação'
    )
    
    tipo_divergencia = models.CharField(
        max_length=20,
        choices=TIPO_DIVERGENCIA_CHOICES,
        verbose_name='Tipo de Divergência'
    )
    
    descricao = models.TextField(
        verbose_name='Descrição da Divergência'
    )
    
    prioridade = models.CharField(
        max_length=1,
        choices=PRIORIDADE_CHOICES,
        default='M',
        verbose_name='Prioridade'
    )
    
    resolvida = models.BooleanField(
        default=False,
        verbose_name='Resolvida?'
    )
    
    solucao = models.TextField(
        blank=True,
        null=True,
        verbose_name='Solução Aplicada'
    )
    
    us_registro = models.ForeignKey(
        User,
        related_name='us_divergencia_registro',
        on_delete=models.PROTECT
    )
    dt_registro = models.DateTimeField(
        default=timezone.now,
        editable=False
    )
    
    us_resolucao = models.ForeignKey(
        User,
        related_name='us_divergencia_resolucao',
        on_delete=models.PROTECT,
        blank=True,
        null=True
    )
    dt_resolucao = models.DateTimeField(
        blank=True,
        null=True
    )
    
    class Meta:
        verbose_name = 'Divergência de Conciliação'
        verbose_name_plural = '4. Divergências de Conciliação'
        ordering = ['-prioridade', '-dt_registro']
    
    def __str__(self):
        return f"Divergência {self.id} - {self.get_tipo_divergencia_display()} - {self.conciliacao}"
