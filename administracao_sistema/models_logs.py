from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class ProntuarioAcessos(models.Model):
    atendimento = models.ForeignKey(
        # Referência por string: o app 'atendimentos' pode ainda não estar
        # carregado quando este módulo é importado.
        'atendimentos.Atendimento',
        on_delete=models.PROTECT, blank=True, null=True)
    us_acesso = models.ForeignKey(
        User, on_delete=models.PROTECT, verbose_name='Us.Acesso', blank=True, null=True)
    dt_acesso = models.DateTimeField(
        default=timezone.now, verbose_name='Dt.Acesso', blank=True, null=True)
    motivo_acesso = models.TextField(
        max_length=255, verbose_name='Motivo de Acesso')
    item_prontuario = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        app_label = 'administracao_sistema'
        db_table = 'admin_logs_prontuarioacessos'
        verbose_name = 'Log Acessos - Prontuários'
        verbose_name_plural = 'Log - Acessos - Prontuários'
        ordering = ['-id']

    def __str__(self):
        return f"{self.atendimento.pessoa.nome}"
