"""Verificação (rollback): Novo/Listar/Voltar/função em tela acima dos filtros."""
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
    urls = ('/atendimentos/atendimento_listar/',
            '/atendimentos/atendimento_cadastrar/')
    for url in urls:
        html = client.get(url).content.decode()
        resultados = {
            'funcao_acima_do_grupo': (
                "wrapGrupo.parentNode.insertBefore(funcaoEmTela, wrapGrupo)"
                in html),
            'demais_no_grupo': 'demais.forEach(function (a)' in html,
            'sem_firstChild': 'grupo.firstChild' not in html,
            'primarios_antes_do_filtro': (
                "menu.insertBefore(bloco, filtroWrap)" in html),
            'seletor_primarios': ('a.voltar-link, #btn-novo, a.bg-primary'
                                  in html),
        }
        print(url, 'RESULTADOS:', resultados)
        assert all(resultados.values())
    print('v10 ✓')
    raise RuntimeError('rollback')
