from django.apps import AppConfig


class AdminAutomacoesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admin_automacoes'
    verbose_name = 'Admin Automações'

    def ready(self):
        import admin_automacoes.signals