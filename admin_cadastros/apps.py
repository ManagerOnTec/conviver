from django.apps import AppConfig


class AdminCadastrosAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admin_cadastros'
    verbose_name = 'Admin Cadastros'

   # def ready(self):
   #     from cadastros import signals


# default_app_config = 'cadastros.apps.CadastrosAppConfig'
