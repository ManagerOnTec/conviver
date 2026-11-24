from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from admin_cadastros.models import Estabelecimento
from admin_cadastros_assistenciais.models import Profissao
from dominios.choices import status_choices
class TipoExame(models.Model):
    descricao = models.CharField(max_length=120, unique=True, verbose_name='Tipo de Exame')
    cor = models.CharField(max_length=7, default='#FFFFFF', verbose_name='Cor')
    iniciais_nome = models.BooleanField(
        default=False, verbose_name='Exibir iniciais do paciente no relatório')
    dt_registro = models.DateTimeField(default=timezone.now, verbose_name='Dt. Registro')
    us_registro = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='tipo_exame_criado_por', null=True, blank=True)
    dt_atualizacao = models.DateTimeField(null=True, blank=True, verbose_name='Dt. Atualização')
    us_atualizacao = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='tipo_exame_atualizado_por', null=True, blank=True)
    status = models.CharField(max_length=1, choices=status_choices, default='A')

    class Meta:
        ordering = ('descricao',)
        verbose_name = 'Tipo de Exame'
        verbose_name_plural = '1. Tipos de Exames'

    def __str__(self):
        return self.descricao
class ParametrosExames(models.Model):
    profissao = models.ForeignKey(
        Profissao, on_delete=models.PROTECT, null=True, blank=True,
        verbose_name='Profissão liberada')
    profissional = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name='parametros_exames_profissional', verbose_name='Profissional liberado')
    tipos_exame = models.ManyToManyField(TipoExame, verbose_name='Tipos de Exames liberados')
    tipo_exame_padrao = models.ForeignKey(
        TipoExame, on_delete=models.PROTECT, null=True, blank=True,
        related_name='parametros_padrao_exames', verbose_name='Tipo de Exame Padrão')
    observacoes = models.CharField(max_length=255, null=True, blank=True, verbose_name='Observações')
    estabelecimento = models.ForeignKey(Estabelecimento, on_delete=models.PROTECT)
    dt_registro = models.DateTimeField(default=timezone.now, verbose_name='Dt. Registro')
    us_registro = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='parametros_exames_criado_por', null=True, blank=True)
    dt_atualizacao = models.DateTimeField(null=True, blank=True, verbose_name='Dt. Atualização')
    us_atualizacao = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='parametros_exames_atualizado_por', null=True, blank=True)
    status = models.CharField(max_length=1, choices=status_choices, default='A')

    class Meta:
        ordering = ('-pk',)
        verbose_name = 'Parâmetro de Exames'
        verbose_name_plural = '2. Parâmetros de Exames'

    def clean(self):
        if bool(self.profissao_id) == bool(self.profissional_id):
            raise ValidationError('Informe exatamente uma opção: profissão ou profissional.')
        if self.pk and self.tipo_exame_padrao_id:
            if not self.tipos_exame.filter(pk=self.tipo_exame_padrao_id).exists():
                raise ValidationError({
                    'tipo_exame_padrao':
                    'O tipo padrão deve estar entre os tipos liberados.'})

    def __str__(self):
        return f'Liberação de exames - {self.profissional or self.profissao}'
