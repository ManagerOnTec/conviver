"""Debug: resposta JSON do POST inline de pessoa."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'managerontec.settings')
django.setup()

from django.db import transaction
from django.test import Client
from django.contrib.auth.models import User

with transaction.atomic():
    from atendimentos.models import Atendimento
    user = User.objects.filter(is_superuser=True).first()
    at = Atendimento.objects.select_related('estabelecimento').first()
    est = at.estabelecimento
    client = Client(SERVER_NAME='localhost')
    client.force_login(user)
    s = client.session
    s['estabelecimento_id'] = est.pk
    s.save()
    r = client.post('/atendimentos/inline/pessoa/', {
        'nome': 'QA MOD PAC I', 'cpf': '', 'classificacao': 'paciente'})
    print('STATUS:', r.status_code)
    print('JSON:', r.json())
    raise RuntimeError('rollback')
