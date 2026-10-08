from http.client import HTTPResponse
from django.db.models.deletion import ProtectedError
from sqlite3 import IntegrityError
from django.contrib.messages import constants
from pathlib import Path
import os
from decouple import config, Csv

from datetime import timedelta
from google.oauth2 import service_account
import base64
import json
import logging
import logging.config
import ssl
from dotenv import load_dotenv  # Biblioteca para ler o .env
import redis
from django.core.cache import cache


# --- CONFIGURAÇÃO PARA GCP E PROXY ---
CSRF_TRUSTED_ORIGINS = [
    f"https://{host}" for host in config("ALLOWED_HOSTS", default="", cast=Csv())
]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

BASE_DIR = Path(__file__).resolve().parent.parent

# --- SEGURANÇA ---
SECRET_KEY = config('SECRET_KEY')
FERNET_KEY = config('FERNET_KEY').encode('utf-8')

DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="",
    cast=lambda v: [s.strip() for s in v.split(",") if s]
)

# ==========================================================
# LOGGING
# ==========================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': config('DJANGO_LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        'storages': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}


# ==========================================================
# REDIS (PADRÃO GCP)
# ==========================================================

# --- HEROKU (comentado) ---
REDIS_URL = os.getenv('REDIS_URL', None)
if not REDIS_URL and not DEBUG:
    raise ValueError(
        "Variável de ambiente REDIS_URL não definida. Verifique o add-on Heroku Redis.")
elif not REDIS_URL and DEBUG:
    # Para desenvolvimento local, você pode definir um padrão ou usar o .env
    REDIS_URL = os.environ.get(
        'LOCAL_REDIS_URL', 'redis://localhost:6379/0')  # Exemplo para local


"""
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL"),  # rediss://...
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SSL": True,
            "CONNECTION_POOL_KWARGS": {
                "ssl_cert_reqs": ssl.CERT_NONE,  # <- aceita cert. autoassinado
                "ssl_check_hostname": False,     # <- desabilita checagem de host
            },
        },
    }
}

"""

SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = config('SESSION_COOKIE_AGE_SECONDS', default=3600, cast=int)
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = False  # Geralmente False é melhor para performance



def handler_exception(request, exception):
    if isinstance(exception, IntegrityError):
        return (request, "Erro ao criar o registro, o mesmo ja esta sendo utilizado.")
    if isinstance(exception, ProtectedError):
        return (request, "Registro ja utilizado, nao pode ser excluido, voce pode inativa-lo")
    else:
        return HTTPResponse("Erro desconhecido.", status=500)


handler404 = handler_exception
handler500 = handler_exception

# ==========================================================
# INSTALLED APPS
# ==========================================================

INSTALLED_APPS = [
    ## 'jazzmin',
    'django.contrib.admin',
    'admin_cadastros.templatetags',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'storages',
    'multiupload',
    'crispy_forms',
    'django_select2',
    'smart_selects',
    'contas',
    'admin_relatorios',
    'admin_cadastros',
    'admin_evolucoes',
    'admin_cadastros_assistenciais',
    'atendimentos',
    'admin_faturas',
    'widget_tweaks',
    'prontuarios',
    'django_filters',
    'admin_sae',
    'admin_estoques',
    'admin_prescricoes',
    'admin_automacoes',
    'admin_logs',
    'admin_parametros',
    'admin_adep',
    'admin_perdas_ganhos',
    'admin_plano_cuidados',
    'admin_sinais_vitais',
    'admin_psicoterapia',
    'admin_diagnosticos',
    'admin_passagem_plantao',
    'admin_cadastros_financeiros',
    'admin_pagamentos',
    'admin_financeiro',
    'oficios',
    'orcamentos',
    'atas',
    'tinymce',
    'apptesouraria',
    'appconciliacao',
    'appcartao',
    'appbaixa_fatura',
    'documentos_legais',
]



TINYMCE_DEFAULT_CONFIG = {
    'plugins': False,
    'toolbar': False,
    'menubar': False,  # Remove menu superior
    'statusbar': False,  # Remove barra de status
    'height': '300px',
    'contextmenu': False,  # Desativa menu de contexto (botão direito)
    'styleselect': False,
}


CRISPY_TEMPLATE_PACK = 'bootstrap4'


# ==========================================================
# MIDDLEWARE
# ==========================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'managerontec.middlewares.RegistroAcessoMiddleware',
    'managerontec.middlewares.LimitUserLoginsMiddleware',
]


ROOT_URLCONF = 'managerontec.urls'

WSGI_APPLICATION = 'managerontec.wsgi.application'


# ==========================================================
# DATABASE (REMOVIDO DJ_DATABASE_URL DO HEROKU)
# ==========================================================

# --- HEROKU (comentado) ---
# import dj_database_url
# DATABASES = {
#     'default': dj_database_url.config(conn_max_age=600, ssl_require=True)
# }

USE_SQLITE = config("USE_SQLITE", default=True, cast=bool)

if USE_SQLITE:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": config("DB_NAME"),
            "USER": config("DB_USER"),
            "PASSWORD": config("DB_PASSWORD"),
            "HOST": config("DB_HOST"),
            "PORT": config("DB_PORT", default="3306"),
            "OPTIONS": {
                "unix_socket": config("DB_SOCKET", default=""),
                "charset": "utf8mb4",
            },
        }
    }


# ==========================================================
# STATIC E MEDIA (IGUAL AO PROJETO 1)
# ==========================================================
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

STATIC_URL = '/static/'


STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static')
]


STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


if not DEBUG:
    GS_PROJECT_ID = config('GS_PROJECT_ID')
    GS_BUCKET_NAME = config('GS_BUCKET_NAME')
    GS_EXPIRATION = timedelta(minutes=30)

    GS_QUERYSTRING_AUTH = True
    GS_DEFAULT_ACL = None

    DEFAULT_FILE_STORAGE = 'managerontec.storage_backends.PrivateMediaStorage'

    MEDIA_URL = f'https://storage.googleapis.com/{GS_BUCKET_NAME}/media/'

    if config('GCP_SERVICE_ACCOUNT_JSON_BASE64', default=None):
        service_account_info = json.loads(
            base64.b64decode(
                config('GCP_SERVICE_ACCOUNT_JSON_BASE64')
            ).decode('utf-8')
        )
        GS_CREDENTIALS = service_account.Credentials.from_service_account_info(
            service_account_info
        )
else:
    MEDIA_URL = '/media/'


# ==========================================================
# TEMPLATES
# ==========================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ==========================================================
# INTERNACIONALIZAÇÃO
# ==========================================================

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ==========================================================
# LIMITES DE UPLOAD
# ==========================================================
# As fotos de validação (responsável e documento) são enviadas como data URL
# base64 dentro do corpo do POST, o que infla o tamanho em ~33%. O padrão do
# Django (2,5 MB) é baixo demais e provocava RequestDataTooBig. Aumentamos os
# limites para acomodar as duas capturas de webcam sem rejeitar o formulário.
DATA_UPLOAD_MAX_MEMORY_SIZE = int(config('DATA_UPLOAD_MAX_MEMORY_SIZE', default=25 * 1024 * 1024))
FILE_UPLOAD_MAX_MEMORY_SIZE = int(config('FILE_UPLOAD_MAX_MEMORY_SIZE', default=25 * 1024 * 1024))
DATA_UPLOAD_MAX_NUMBER_FIELDS = int(config('DATA_UPLOAD_MAX_NUMBER_FIELDS', default=2000))


LOGIN_REDIRECT_URL = '/login/'
LOGIN_URL = '/login/'
LOGOUT_REDIRECT_URL = '/logout/'

DATE_INPUT_FORMATS = ['%d/%m/%Y']
DATETIME_INPUT_FORMATS = ['%d/%m/%Y %H:%M:%S']
TIME_INPUT_FORMATS = ['%H:%M:%S']

DATE_INPUT_FORMAT = 'd/m/Y'
DATETIME_INPUT_FORMAT = 'd/m/Y H:i:s'
TIME_INPUT_FORMAT = 'H:i:s'

DATE_FORMAT = 'd/m/Y'
DATETIME_FORMAT = 'd/m/Y H:i:s'
TIME_FORMAT = 'H:i:s'


USE_DJANGO_JQUERY = True


JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": True,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": True,
    "brand_colour": "navbar-primary",
    "accent": "accent-navy",
    "navbar": "navbar-dark navbar-light",
    "no_navbar_border": True,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": True,
    "theme": "minty",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-outline-primary",
        "secondary": "btn-outline-secondary",
        "info": "btn-outline-info",
        "warning": "btn-outline-warning",
        "danger": "btn-outline-danger",
        "success": "btn-success"
    },
    "actions_sticky_top": True,

}

JAZZMIN_SETTINGS = {
    "show_footer": False,
    "show_ui_builder": False,  # Customizar admin jazzmin
    "custom_css": "css/jazz.css",
    "user_avatar": None,
    "topmenu_links": [        # Urls de nome
        {"name": "Home", "url": "select_estabelecimento",
            "permissions": ["auth.view_user"]},
        {"name": "Encerrar sessao", "url": "logout",
            "permissions": ["auth.view_user"]},

    ],
}

JAZZMIN_DASHBOARDS = {
    "main": {
        "widgets": [
            {
                "type": "list",
                "position": [0, 0],
                "columns": ["name", "created"],
                "order": "-created",
                "limit": 15,  # Adjust this value to the number of items you want to show
            },],
    },
}


MESSAGE_TAGS = {
    constants.ERROR: 'alert-danger',
    constants.WARNING: 'alert-warning',
    constants.DEBUG: 'alert-info',
    constants.SUCCESS: 'alert-success',
    constants.INFO: 'alert-info',
}

MSG_ADD = 'Adicionado com sucesso!'
MSG_EDIT = 'Atualizado com sucesso!'
MSG_DELETE = 'Excluido com sucesso!'
MSG_ERROR = 'Erro ao realizar a operacao!'
MSG_SUSP = 'Suspensa com sucesso!'


DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='webmaster@localhost')

