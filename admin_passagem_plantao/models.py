from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import models
from admin_cadastros.models import Estabelecimento
from admin_cadastros_assistenciais.models import CadastroProfissional, Especialidade, Profissao
from dominios.choices import status_choices
from django.contrib.auth.models import User


class TipoPassagemPlantao(models.Model):
    tipo_passagem_plantao = models.CharField(
        max_length=80, verbose_name='Tipo de Passagem de Plantão')

    observacao = models.TextField(
        verbose_name='Observação', blank=True, null=True)

    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='tipopassagem_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, default='', blank=True, null=True, related_name='tipopassagem_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT, verbose_name='Estabelecimento')

    class Meta:
        verbose_name = 'Tipo de Passagem de Plantão'
        verbose_name_plural = '1. Tipos de Passagem de Plantão'

    def __str__(self):
        return self.tipo_passagem_plantao


class ParametrosPassagemPlantao(models.Model):
    profissao = models.ForeignKey(
        Profissao, on_delete=models.PROTECT, verbose_name='Profissao Passagem Plantao', blank=True, null=True)
    profissional = models.ForeignKey(
        User, on_delete=models.PROTECT, verbose_name='Profissional Passagem Plantao', blank=True, null=True, related_name='profissional_passagem')

    tipo_passagem_plantao = models.ManyToManyField(
        TipoPassagemPlantao, verbose_name='Tipos de Passagem de Plantão', help_text='As opções de tipos liberam os tipos que o usuário pode ver e cadastrar!')

    tipo_passagem_plantao_padrao = models.ForeignKey('admin_passagem_plantao.TipoPassagemPlantao', on_delete=models.SET_NULL,
                                                     verbose_name='Tipo de Passagem Plantão Padrão', blank=True, null=True, related_name='tipo_passagem_plantao_padrao')

    observacoes = models.CharField(
        max_length=255, blank=True, null=True, verbose_name='Observações')

    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='parpassagem_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, default='', blank=True, null=True, related_name='parpassagem_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT, verbose_name='Estabelecimento')

    class Meta:
        verbose_name = 'Parâmetros Passagem Plantão'
        verbose_name_plural = '2. Parâmetros Passagens de Plantões'
        ordering = ['-pk']

    def __str__(self):
        return f"Parâmetros liberados para {self.profissao} ou {self.profissional}"
