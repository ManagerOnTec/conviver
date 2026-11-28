"""Verificação (rollback): mapa de leitos — Novo, Voltar e grupo Funções."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'managerontec.settings')
django.setup()

from django.db import transaction
from django.test import Client
from django.contrib.auth.models import User

with transaction.atomic():
    from admin_cadastros.models import Estabelecimento
    user = User.objects.filter(is_superuser=True).first()
    est = Estabelecimento.objects.first()
    client = Client(SERVER_NAME='localhost')
    client.force_login(user)
    s = client.session
    s['estabelecimento_id'] = est.pk
    s.save()
    html = client.get('/leitos/leito_mapa/').content.decode()
    resultados = {
        'botao_novo': '>Novo<' in html,
        'sem_registrar_ocupacao': 'Registrar Ocupação' not in html,
        'voltar_link': 'voltar-link' in html,
        'grupo_1_item': "demais.length > 0" in html,
        'wrapper_funcoes': 'Funções' in html,
    }
    print('RESULTADOS:', resultados)
    assert all(resultados.values())
    print('v11 ✓')
    raise RuntimeError('rollback')
