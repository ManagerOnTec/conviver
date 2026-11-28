"""Verificação (rollback): sessão como toggle único com usuário no rótulo."""
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
        'js_novo_sessao': 'nomeUsuario' in html,
        'hide_div_usuario': "divUsuario.style.display = 'none'" in html,
        'estab_centralizado': "divEstab.style.textAlign = 'center'" in html,
        'sem_segundo_toggle': html.count('envolver(sessao') == 1,
    }
    print('RESULTADOS:', resultados)
    assert all(resultados.values())
    print('v5 ✓')
    raise RuntimeError('rollback')
