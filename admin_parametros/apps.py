# em apps.py na pasta admin_parametros
from django.apps import AppConfig


class AdminParametrosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admin_parametros'
    verbose_name = 'Admin Parâmetros'
