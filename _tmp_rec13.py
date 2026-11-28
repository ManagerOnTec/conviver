"""Verificação (rollback): Voltar (custom-link) fora do grupo Funções."""
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
    urls = ('/gp/funcionario_listar/',
            '/gp/funcionario_cadastrar/',
            '/gp/pessoa_listar/',
            '/agenda/agenda_listar/',
            '/atendimentos/atendimento_listar/')
    for url in urls:
        html = client.get(url).content.decode()
        resultados = {
            'voltar_existe': 'voltar-link' in html,
            'voltar_fora_do_grupo': (
                "custom-link:not(.voltar-link)" in html),
        }
        print(url, 'RESULTADOS:', resultados)
        assert all(resultados.values())
    print('v13 ✓')
    raise RuntimeError('rollback')
