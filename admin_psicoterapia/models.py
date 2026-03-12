from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import models
from admin_cadastros.models import Estabelecimento
from admin_cadastros_assistenciais.models import CadastroProfissional, Especialidade, Profissao
from dominios.choices import status_choices
from django.contrib.auth.models import User


class ParametrosPsicoterapia(models.Model):
    profissao = models.ForeignKey(
        Profissao, on_delete=models.PROTECT, verbose_name='Profissao Psicoterapia', blank=True, null=True)
    profissional = models.ForeignKey(
        User, on_delete=models.PROTECT, verbose_name='Profissional Psicoterapia', blank=True, null=True, related_name='profissional_psicoterapia')

    observacoes = models.CharField(
        max_length=255, blank=True, null=True, verbose_name='Observações')

    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='parpsico_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, default='', blank=True, null=True, related_name='parpsico_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT, verbose_name='Estabelecimento')

    class Meta:
        verbose_name = 'Parâmetros Psicoterapia'
        verbose_name_plural = '1. Parâmetros Psicoterapias'
        ordering = ['-pk']

    def __str__(self):
        return f"Parâmetros liberados para {self.profissao} ou {self.profissional}"
