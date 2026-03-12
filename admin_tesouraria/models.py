from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from admin_cadastros.models import Estabelecimento
from admin_cadastros_financeiros.models import Conta
from dominios.choices import status_choices
from decimal import Decimal

User = get_user_model()


class Caixa(models.Model):
    """
    Modelo para representar um caixa físico da tesouraria.
    Cada caixa pode ter múltiplos saldos abertos/fechados.
    """
    descricao = models.CharField(
        max_length=255,
        verbose_name='Descrição do Caixa'
    )
    
    estabelecimento = models.ForeignKey(
        Estabelecimento,
        on_delete=models.PROTECT,
        verbose_name='Estabelecimento'
    )
    
    numero_caixa = models.CharField(
        max_length=20,
        verbose_name='Número do Caixa',
        unique=True
    )
    
    responsavel = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name='Responsável',
        related_name='caixas_responsavel'
    )
    
    observacao = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Observações'
    )
    
    us_registro = models.ForeignKey(
        User,
        related_name='us_caixa_registro',
        on_delete=models.PROTECT
    )
    dt_registro = models.DateTimeField(
        default=timezone.now,
        editable=False
    )
    us_atualizacao = models.ForeignKey(
        User,
        related_name='us_caixa_atualizacao',
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
        verbose_name = "Caixa"
        verbose_name_plural = "1. Caixas"
        ordering = ['descricao']

    def __str__(self):
        return f"{self.numero_caixa} - {self.descricao}"


class SaldoCaixa(models.Model):
    """
    Modelo para registrar o saldo de um caixa em um período específico.
    Controla abertura e fechamento de caixa.
    """
    caixa = models.ForeignKey(
        Caixa,
        on_delete=models.PROTECT,
        verbose_name='Caixa'
    )
    
    dt_abertura = models.DateTimeField(
        default=timezone.now,
        verbose_name='Data/Hora de Abertura'
    )
    
    dt_fechamento = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Data/Hora de Fechamento'
    )
    
    saldo_inicial = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Saldo Inicial',
        default=Decimal('0.00')
    )
    
    saldo_final = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Saldo Final',
        blank=True,
        null=True
    )
    
    total_entradas = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Total de Entradas',
        default=Decimal('0.00')
    )
    
    total_saidas = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Total de Saídas',
        default=Decimal('0.00')
    )
    
    observacao = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observações'
    )
    
    us_registro = models.ForeignKey(
        User,
        related_name='us_saldo_caixa_registro',
        on_delete=models.PROTECT
    )
    dt_registro = models.DateTimeField(
        default=timezone.now,
        editable=False
    )
    us_atualizacao = models.ForeignKey(
        User,
        related_name='us_saldo_caixa_atualizacao',
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
        verbose_name = "Saldo de Caixa"
        verbose_name_plural = "2. Saldos de Caixa"
        ordering = ['-dt_abertura']

    def __str__(self):
        return f"{self.caixa} - {self.dt_abertura.strftime('%d/%m/%Y %H:%M')}"

    def save(self, *args, **kwargs):
        # Verifica se há algum saldo de caixa aberto antes de abrir um novo
        if not self.dt_fechamento:
            if SaldoCaixa.objects.filter(
                caixa=self.caixa,
                dt_fechamento__isnull=True
            ).exclude(pk=self.pk).exists():
                raise ValidationError(
                    'Não é possível abrir um novo saldo enquanto houver outro saldo aberto.')
        
        super().save(*args, **kwargs)

    def calcular_saldo_final(self):
        """Calcula o saldo final com base nas movimentações"""
        if self.dt_fechamento:
            self.saldo_final = self.saldo_inicial + self.total_entradas - self.total_saidas
            self.save()


class MovimentacaoCaixa(models.Model):
    """
    Modelo para registrar todas as movimentações de caixa.
    Pode ser entrada (do banco ou recebimento) ou saída (pagamento ou para banco).
    """
    TIPO_MOVIMENTACAO_CHOICES = [
        ('ENTRADA_BANCO', 'Entrada do Banco'),
        ('ENTRADA_RECEBIMENTO', 'Entrada de Recebimento'),
        ('SAIDA_PAGAMENTO', 'Saída - Pagamento'),
        ('SAIDA_BANCO', 'Saída para o Banco'),
        ('SAIDA_OUTRA', 'Saída Outra'),
    ]
    
    saldo_caixa = models.ForeignKey(
        SaldoCaixa,
        on_delete=models.PROTECT,
        verbose_name='Saldo de Caixa',
        related_name='movimentacoes'
    )
    
    tipo_movimentacao = models.CharField(
        max_length=20,
        choices=TIPO_MOVIMENTACAO_CHOICES,
        verbose_name='Tipo de Movimentação'
    )
    
    descricao = models.CharField(
        max_length=255,
        verbose_name='Descrição'
    )
    
    valor = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Valor'
    )
    
    data_movimentacao = models.DateField(
        default=timezone.now,
        verbose_name='Data da Movimentação'
    )
    
    hora_movimentacao = models.TimeField(
        auto_now_add=True,
        verbose_name='Hora da Movimentação'
    )
    
    # Referências opcionais para rastreamento
    pagamento = models.ForeignKey(
        'admin_pagamentos.Pagamento',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='Pagamento',
        related_name='movimentacoes_caixa'
    )
    
    conta_bancaria = models.ForeignKey(
        Conta,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='Conta Bancária'
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
        related_name='us_movimentacao_caixa_registro',
        on_delete=models.PROTECT
    )
    dt_registro = models.DateTimeField(
        default=timezone.now,
        editable=False
    )
    us_atualizacao = models.ForeignKey(
        User,
        related_name='us_movimentacao_caixa_atualizacao',
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
        verbose_name = "Movimentação de Caixa"
        verbose_name_plural = "3. Movimentações de Caixa"
        ordering = ['-data_movimentacao', '-hora_movimentacao']

    def __str__(self):
        return f"{self.get_tipo_movimentacao_display()} - {self.valor} - {self.data_movimentacao}"

    def save(self, *args, **kwargs):
        # Atualiza totais no saldo de caixa
        super().save(*args, **kwargs)
        self._atualizar_totais_saldo()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self._atualizar_totais_saldo()

    def _atualizar_totais_saldo(self):
        """Atualiza os totais de entrada e saída no saldo de caixa"""
        saldo = self.saldo_caixa
        
        # Recalcula totais
        entradas = saldo.movimentacoes.filter(
            tipo_movimentacao__in=['ENTRADA_BANCO', 'ENTRADA_RECEBIMENTO'],
            status='A'
        ).aggregate(total=models.Sum('valor'))['total'] or Decimal('0.00')
        
        saidas = saldo.movimentacoes.filter(
            tipo_movimentacao__in=['SAIDA_PAGAMENTO', 'SAIDA_BANCO', 'SAIDA_OUTRA'],
            status='A'
        ).aggregate(total=models.Sum('valor'))['total'] or Decimal('0.00')
        
        saldo.total_entradas = entradas
        saldo.total_saidas = saidas
        saldo.save()
