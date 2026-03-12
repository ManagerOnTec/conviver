from django.db import models
from dominios.choices import regras_emails_choices
from django.utils.crypto import get_random_string
from dominios.utils import EncryptedCharField
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.contrib.auth.models import User

class EmailConfiguration(models.Model):
    email_backend = models.CharField(
        max_length=255, default='django.core.mail.backends.smtp.EmailBackend')
    email_host = models.CharField(max_length=255, default='smtp.zoho.com')
    email_port = models.PositiveIntegerField(default=587)
    email_use_tls = models.BooleanField(default=True)
    email_host_user = models.EmailField(
        default='nao-responda@managerontecsolutions.com.br')
    email_host_password = EncryptedCharField(
        max_length=255, help_text='Senha do e-mail remetente, sempre que editar esta tabela, precisara repassar novamente a senha do e-mail')

    # campo para armazenar o assunto
    subject = models.CharField(max_length=255)

    # Campo para armazenar a mensagem
    message = models.TextField()

    # Campo para armazenar o número de dias em que o link de recuperação de senha será válido
    valid_days = models.PositiveIntegerField()
    # Campo para descrever a regra de email
    regra = models.CharField(max_length=255, choices=regras_emails_choices)

    class Meta:
        verbose_name = 'E-mail e configuração'
        verbose_name_plural = '1. E-mails e configurações'

    def __str__(self):
        return f'Configurações de E-mail Remetente {self.regra}'


class QtdUsuariosSimultaneos(models.Model):
    max_usuarios_simultaneos = models.PositiveIntegerField()

    class Meta:
        verbose_name = 'Quantidade de Usuários Simultâneos'
        verbose_name_plural = '2. Quantidade de Usuários Simultâneos'

    def __str__(self):
        return f'Quantidade de Usuários Simultâneos: {self.max_usuarios_simultaneos}'




class ActiveSession(Session):
    class Meta:
        proxy = True
        verbose_name = "Usuário Logado"
        verbose_name_plural = "Usuários Logados"

    def get_user(self):
        data = self.get_decoded()
        user_id = data.get('_auth_user_id')
        if user_id:
            try:
                return User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return None
        return None

    def is_authenticated(self):
        return self.get_user() is not None

    def get_username(self):
        user = self.get_user()
        return user.username if user else None

    def get_email(self):
        user = self.get_user()
        return user.email if user else None

    def get_expire_date(self):
        return self.expire_date       
