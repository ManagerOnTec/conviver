from django.db import models
from django.core.validators import FileExtensionValidator
from multiupload.fields import MultiFileField
from dominios.utils import validate_anexo_file
from django.utils import timezone
from django.contrib.auth.models import User
from dominios.choices import status_choices
from admin_cadastros.models import Estabelecimento
from dominios.text_validators import validate_evolucao_like_text
# Create your models here.


# Modelo principal para as orcamentoss
class Orcamentos(models.Model):

    observacao = models.CharField(max_length=255, verbose_name="Observações")

    orcamento = models.TextField(validators=[validate_evolucao_like_text])

    anexo = models.FileField(upload_to='anexos/orcamentos/%Y/%m/', blank=True, null=True, help_text='Adicione arquivos dos formatos PDF, JPG, JPEG, PNG.',
                             validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png']), validate_anexo_file])

    assinar = models.BooleanField(default=True)

    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT)

    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='orcamentos_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True, related_name='orcamentos_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    class Meta:
        verbose_name = "orcamentos"
        verbose_name_plural = "orcamentoss"
        ordering = ["-pk"]

    def __str__(self):
        return f"{self.pk}"
