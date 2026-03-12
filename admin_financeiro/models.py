from django.db import models
from django.utils import timezone
from admin_pagamentos.models import Pagamento, User
from admin_cadastros_financeiros.models import Conta, TransacaoFinanceira
from django.core.exceptions import ValidationError
from admin_cadastros.models import Estabelecimento
from dominios.choices import status_choices

class ControleBancario(models.Model):

    conta = models.ForeignKey(Conta, on_delete=models.PROTECT)
    us_registro = models.ForeignKey(
        User, related_name='uscontbanc_registro', on_delete=models.PROTECT)
    dt_registro = models.DateTimeField(default=timezone.now, editable=False)
    us_atualizacao = models.ForeignKey(
        User, related_name='uscontbanc_atualizacao', on_delete=models.PROTECT, blank=True, null=True)
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None,  verbose_name='Dt.Atualização')
    estabelecimento = models.ForeignKey(Estabelecimento, on_delete=models.PROTECT)

    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status')

    def __str__(self):
        return f"{self.conta}"

    class Meta:
        verbose_name = 'Controle Bancário'
        verbose_name_plural = '1. Controles Bancários'



class CompetenciaBancaria(models.Model):
    controle_bancario = models.ForeignKey(ControleBancario, on_delete=models.PROTECT)
    descricao = models.CharField(max_length=100, help_text='Utilize uma descrição, como exemplo = JANEIRO/2024')
    dt_abertura_competencia = models.DateField()
    dt_fechamento_competencia = models.DateField(blank=True, null=True)
    saldo_inicial = models.DecimalField(max_digits=12, decimal_places=2)
    saldo_anterior = models.DecimalField(max_digits=12, decimal_places=2)
    saldo_atual = models.DecimalField(max_digits=12, decimal_places=2)
    observacao = models.CharField(max_length=100, blank=True, null=True)

    us_registro = models.ForeignKey(
        User, related_name='ussaldo_registro', on_delete=models.PROTECT)
    dt_registro = models.DateTimeField(default=timezone.now, editable=False)
    us_atualizacao = models.ForeignKey(
        User, related_name='ussaldo_atualizacao', on_delete=models.PROTECT, blank=True, null=True)
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None,  verbose_name='Dt.Atualização')
    estabelecimento = models.ForeignKey(Estabelecimento, on_delete=models.PROTECT)

    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status')
    
    class Meta:
        verbose_name = 'Competência Bancária'
        verbose_name_plural = '2. Competências Bancárias'


    def __str__(self):
        abertura_formatada = self.dt_abertura_competencia.strftime('%d/%m/%Y')
        if self.dt_fechamento_competencia:
            fechamento_formatado = self.dt_fechamento_competencia.strftime('%d/%m/%Y')
            return f"{self.controle_bancario} - Competência Bancária - Abertura: {abertura_formatada} - Fechamento: {fechamento_formatado} - {self.estabelecimento}"
        else:
            return f"{self.controle_bancario} - Competência Bancária - Abertura: {abertura_formatada} - Fechamento: Em aberto - {self.estabelecimento}"


#########################################################################
#########################################################################
class MovimentoBancario(models.Model):

    competencia_bancaria = models.ForeignKey(CompetenciaBancaria, on_delete=models.PROTECT, verbose_name='Competência (Aberta)')


    transacao_financeira = models.ForeignKey(
        TransacaoFinanceira, on_delete=models.PROTECT, verbose_name='Transação Financeira')
    
    valor_entrada = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Valor E', blank=True, null=True)
    
    valor_saida = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Valor S', blank=True, null=True)
    
 
    us_registro = models.ForeignKey(
        User, related_name='movimento_registro', on_delete=models.PROTECT)
    dt_registro = models.DateTimeField(default=timezone.now, editable=False)
    us_atualizacao = models.ForeignKey(
        User, related_name='movimento_atualizacao', on_delete=models.PROTECT, blank=True, null=True)
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None,  verbose_name='Dt.Atualização')
    estabelecimento = models.ForeignKey(Estabelecimento, on_delete=models.PROTECT)

    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status')

    class Meta:
        verbose_name = "Movimento Bancário"
        verbose_name_plural = "3. Movimentos Bancários"

    def save(self, *args, **kwargs):
        # Atribui o estabelecimento com base na competência bancária
        if self.competencia_bancaria:
            self.estabelecimento = self.competencia_bancaria.estabelecimento
        else:
            raise ValueError('Competência bancária é obrigatória.')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transacao_financeira} Entrada: {self.valor_entrada} Saída: {self.valor_saida}"


