from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import models
from admin_cadastros.models import Estabelecimento
from admin_cadastros_assistenciais.models import CadastroProfissional, Profissao
from dominios.choices import status_choices
from django.contrib.auth.models import User


class ParametrosPerdasGanhos(models.Model):
    profissao = models.ForeignKey(
        Profissao, null=True, blank=True, on_delete=models.PROTECT, verbose_name='Profissao liberada')

    profissional = models.ForeignKey(User, null=True,
                                     blank=True, on_delete=models.PROTECT, verbose_name='Profissional liberado', related_name='perga_profissional')

    observacoes = models.CharField(
        max_length=255, blank=True, null=True, verbose_name='Observações')

    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='perga_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, default='', blank=True, null=True, related_name='perga_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT, verbose_name='Estabelecimento')

    class Meta:
        verbose_name = 'Parâmetros Perdas e Ganhos'
        verbose_name_plural = '1. Parâmetros Perdas e Ganhos'
        ordering = ['-pk']

    def __str__(self):
        return f"Parâmetros liberados para {self.profissional} - {self.profissao}"

    def clean(self):
        # Verificar se exatamente um dos campos está preenchido
        fields = [self.profissao,
                  self.profissional]
        filled_fields = [field for field in fields if field is not None]

        if len(filled_fields) != 1:
            raise ValidationError(
                "Apenas um dos campos profissao, profissional deve ser preenchido.")
