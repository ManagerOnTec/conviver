"""Verificação (rollback): função em tela NO TOPO da lista expandida."""
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
    for url in ('/atendimentos/atendimento_listar/',
                '/prontuarios/evolucao_listar/'):
        html = client.get(url).content.decode()
        resultados = {
            'funcao_acima_do_grupo': (
                "wrapGrupo.parentNode.insertBefore(funcaoEmTela, wrapGrupo)"
                in html),
            'demais_no_grupo': 'demais.forEach(function (a)' in html,
            'sem_firstChild': 'grupo.firstChild' not in html,
        }
        print(url, 'RESULTADOS:', resultados)
        assert all(resultados.values())
    print('v9 ✓')
    raise RuntimeError('rollback')
