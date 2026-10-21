from django.apps import AppConfig


class AdministracaoSistemaConfig(AppConfig):
    """
    Módulo único de Administração do Sistema.

    Consolida os antigos apps ``admin_automacoes``, ``admin_logs`` e
    ``admin_parametros``. As tabelas do banco são preservadas
    (``db_table`` explícito em cada modelo), portanto não há migração de dados.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'administracao_sistema'
    verbose_name = 'Administração do Sistema'

    def ready(self):
        # Sem este import os receivers nunca são registrados e o login do
        # mesmo usuário deixava várias sessões ativas.
        from administracao_sistema import signals_automacoes  # noqa: F401
