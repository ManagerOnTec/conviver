from datetime import date
from django.db import models
from django.contrib.auth.models import User
from admin_cadastros.models import Pessoa, Estabelecimento
from dominios.choices import regras_emails_choices
from cryptography.fernet import Fernet
from dominios.utils import EncryptedCharField
from django.core.validators import FileExtensionValidator

class Perfil(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, verbose_name='Usuário')
    pessoa = models.OneToOneField(
        Pessoa, on_delete=models.CASCADE, verbose_name='Funcionario')
    estabelecimento = models.ManyToManyField(Estabelecimento)
    estabelecimento_padrao = models.ForeignKey(
        Estabelecimento,
        on_delete=models.PROTECT,
        related_name='perfis_padrao',
        verbose_name='Estabelecimento Padrão'
    )
    dt_admissao = models.DateField(
        default=date.today, verbose_name='Data de Admissão')
    dt_desligamento = models.DateField(
        blank=True, null=True, verbose_name='Data de Desligamento')
    senha_alterada = models.BooleanField(default=False)


    certificado_digital = models.FileField(
        upload_to='certificados/',
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pfx']
            )
        ]
    )

    validade_certificado = models.DateField(
        blank=True, null=True, verbose_name='Validade do Certificado')

    senha_certificado = models.CharField(
        max_length=255, blank=True, null=True, verbose_name='Senha do Certificado')

    def __str__(self):
        return self.pessoa.nome
