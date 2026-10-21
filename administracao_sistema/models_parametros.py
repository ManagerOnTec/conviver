from django.db import models


class ConfiguracaoSessao(models.Model):
    duracao_sessao = models.IntegerField(
        default=3600, help_text='Defina em segundos o tempo de duração de sessão, após este tempo o usuário perde a autenticação no sistema, ex: 3600 = 1 hora')
    # Tempo em micro segundos (padrão: 60 minutos)

    class Meta:
        app_label = 'administracao_sistema'
        db_table = 'admin_parametros_configuracaosessao'
        verbose_name = 'Configuração de Sessão'
        verbose_name_plural = '1. Configurações de Sessões'

    def __str__(self):
        return f"Duração da Sessão: {self.duracao_sessao} segundos"
