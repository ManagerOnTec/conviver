from django.db import models
from django.core.validators import FileExtensionValidator
from multiupload.fields import MultiFileField
from dominios.utils import validate_anexo_file
from django.utils import timezone
from django.contrib.auth.models import User
from dominios.choices import status_choices, tipo_atas_choices
from django.core.validators import MaxLengthValidator
from admin_cadastros.models import Estabelecimento
# Create your models here.

# Modelo principal para as atas


class Atas(models.Model):
    participantes = models.CharField(
        max_length=500, verbose_name="Participantes")
    assunto = models.CharField(max_length=255, verbose_name="Assunto")

    anexo = models.FileField(upload_to='anexos/atas/%Y/%m/', blank=True, null=True, help_text='Adicione arquivos dos formatos PDF, JPG, JPEG, PNG.',
                             validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png']), validate_anexo_file])

    tipo_ata = models.CharField(
        max_length=100, choices=tipo_atas_choices)

    observacoes = models.CharField(
        max_length=100
    )

    ata = models.TextField(validators=[MaxLengthValidator(5500)])

    assinar = models.BooleanField(default=True)

    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT)

    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='atas_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True, related_name='atas_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    class Meta:
        verbose_name = "Ata"
        verbose_name_plural = "Atas"
        ordering = ["-pk"]

    def __str__(self):
        return f"{self.assunto} ({self.tipo_ata})"
