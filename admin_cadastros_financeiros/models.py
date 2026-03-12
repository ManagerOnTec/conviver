from django.db import models
from dominios.choices import status_choices
from admin_cadastros.models import Estabelecimento


class Banco(models.Model):
    numero_banco = models.CharField(max_length=10, unique=True)
    descricao_banco = models.CharField(max_length=100)
    observacao = models.CharField(max_length=100, blank=True, null=True)
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT, 
        help_text="Estabelecimento associado a este banco"
    )
    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status'
    )

    def __str__(self):
        return f"{self.numero_banco} - {self.descricao_banco}"

    class Meta:
        verbose_name = "Banco"
        verbose_name_plural = "1. Bancos"


class Agencia(models.Model):
    banco = models.ForeignKey(
        Banco, on_delete=models.PROTECT, related_name='agencias')
    numero_agencia = models.CharField(max_length=10)
    descricao_agencia = models.CharField(max_length=100, blank=True, null=True)
    observacao = models.CharField(max_length=100, blank=True, null=True)
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT, 
        help_text="Estabelecimento associado a esta agência"
    )
    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status'
    )

    def __str__(self):
        return f"Agência {self.numero_agencia} - {self.banco.descricao_banco}"

    class Meta:
        verbose_name = "Agência"
        verbose_name_plural = "2. Agências"


class Conta(models.Model):
    numero_conta = models.CharField(
        max_length=20, help_text='Informe com o digito e sem caracteres especiais')
    observacao = models.CharField(max_length=100, blank=True, null=True)
    agencia = models.ForeignKey(
        Agencia, on_delete=models.PROTECT, related_name='contas')
    padrao = models.BooleanField(
        blank=True, null=True, default=False, help_text='Movimentação financeira padrão do estabelecimento'
    )
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT, 
        help_text="Estabelecimento associado a esta conta"
    )
    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status'
    )

    def __str__(self):
        return f"Conta: {self.numero_conta} - Agência: {self.agencia.numero_agencia} - {self.agencia.banco.descricao_banco}"

    class Meta:
        verbose_name = "Conta"
        verbose_name_plural = "3. Contas"


class TransacaoFinanceira(models.Model):
    TIPO_CHOICES = [
        ('entrada', 'Entrada'),
        ('saida', 'Saída'),
        ('nenhum', 'Não Movimenta'),
    ]

    MOVIMENTO_CHOICES = [
        ('caixa', 'Movimenta Caixa'),
        ('banco', 'Movimenta Banco'),
        ('nenhum', 'Não Movimenta'),
    ]

    transacao_financeira = models.CharField(max_length=80)
    tipo = models.CharField(max_length=7, choices=TIPO_CHOICES)
    movimento = models.CharField(max_length=7, choices=MOVIMENTO_CHOICES)
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT,
        help_text="Estabelecimento associado a esta transação"
    )
    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status'
    )

    def __str__(self):
        return f"{self.transacao_financeira} / {self.tipo} / {self.movimento}"

    class Meta:
        verbose_name = "Transação Financeira"
        verbose_name_plural = "7. Transações Financeiras"
