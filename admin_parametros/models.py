from django.db import models


class ConfiguracaoSessao(models.Model):
    duracao_sessao = models.IntegerField(
        default=36000, help_text='Defina em micro segundos o tempo de duração de sessão, após este tempo o usuário perde a autenticação no sistema, ex: 36000 = 1 hora')
    # Tempo em micro segundos (padrão: 60 minutos)

    class Meta:
        verbose_name = 'Configuração de Sessão'
        verbose_name_plural = '1. Configurações de Sessão'

    def __str__(self):
        return f"Duração da Sessão: {self.duracao_sessao} segundos"
