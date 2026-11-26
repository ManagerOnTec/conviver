"""Cria sessão REAL via test client e imprime o cookie."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'managerontec.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from admin_cadastros.models import Estabelecimento
from atendimentos.models import Atendimento
from django.contrib.sessions.backends.db import SessionStore

user = User.objects.filter(is_superuser=True).first()
client = Client(SERVER_NAME='localhost')
client.force_login(user)
sessionid = client.cookies['sessionid'].value

at = Atendimento.objects.select_related('estabelecimento').first()
store = SessionStore(session_key=sessionid)
store['estabelecimento_id'] = at.estabelecimento.pk
store.save()
print(sessionid)
