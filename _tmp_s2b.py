"""Verificação (rollback): modal de ocupação completo."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'managerontec.settings')
django.setup()

from django.db import transaction
from django.test import Client
from django.contrib.auth.models import User

with transaction.atomic():
    from admin_cadastros.models import Estabelecimento, Ala, Setor, Local, Leito
    from atendimentos.models import Atendimento
    user = User.objects.filter(is_superuser=True).first()
    at = Atendimento.objects.select_related('estabelecimento').first()
    est = at.estabelecimento
    client = Client(SERVER_NAME='localhost')
    client.force_login(user)
    s = client.session
    s['estabelecimento_id'] = est.pk
    s.save()
    r = client.get('/leitos/leito_mapa/')
    html = r.content.decode()
    print('status:', r.status_code)
    print('modal-ocupar:', 'id="modal-ocupar"' in html)
    i = html.find('id="modal-ocupar"')
    trecho = html[i:i+2500] if i > 0 else ''
    print('tem select leito:', 'name="leito"' in trecho)
    print('tem select2:', 'django-select2' in trecho)
    print('tem media css:', 'select2.min.css' in html)
    print('tem media js:', 'select2.full.min.js' in html)
    print('tem data-ajax--url:', 'data-ajax--url' in html)
    if i > 0:
        j = html.find('id="id_atendimento"')
    print('posicao do select atendimento:', j, '| modal em:', i)
    if j > 0:
        print('CONTEXTO:', html[j-150:j+200])
    raise RuntimeError('rollback')
