"""Verificação (rollback): função em tela NO TOPO da lista expandida."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'managerontec.settings')
django.setup()

from django.db import transaction
from django.test import Client
from django.contrib.auth.models import User

with transaction.atomic():
    from atendimentos.models import Atendimento
    from admin_cadastros.models import Estabelecimento
    user = User.objects.filter(is_superuser=True).first()
    est = Estabelecimento.objects.first()
    client = Client(SERVER_NAME='localhost')
    client.force_login(user)
    s = client.session
    s['estabelecimento_id'] = est.pk
    s.save()
    html = client.get('/atendimentos/atendimento_listar/').content.decode()
    resultados = {
        'topo_da_lista': 'grupo.insertBefore(funcaoEmTela, '
                         'grupo.firstChild)' in html,
        'sem_nextSibling': 'grupo.nextSibling' not in html,
    }
    print('RESULTADOS:', resultados)
    assert all(resultados.values())
    print('v8 ✓')
    raise RuntimeError('rollback')
