"""Verificação (rollback): ambos os selects digitáveis no modal."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'managerontec.settings')
django.setup()

from django.db import transaction
from django.test import Client
from django.contrib.auth.models import User

with transaction.atomic():
    from admin_cadastros.models import Estabelecimento
    from atendimentos.models import Atendimento
    user = User.objects.filter(is_superuser=True).first()
    at = Atendimento.objects.select_related('estabelecimento').first()
    est = at.estabelecimento
    client = Client(SERVER_NAME='localhost')
    client.force_login(user)
    s = client.session
    s['estabelecimento_id'] = est.pk
    s.save()
    html = client.get('/leitos/leito_mapa/').content.decode()
    i = html.find('id="modal-ocupar"')
    trecho = html[i:i+4000] if i > 0 else ''
    print('modal ocupar presente:', i > 0)
    print('select2 leito:', 'id_leito' in trecho or 'name="leito"' in trecho)
    print('select2 atendimento:', 'id_atendimento' in trecho)
    print('data-ajax--url no modal:',
          'data-ajax--url' in trecho, '|',
          'django-select2' in html)
    # select2 inicializa via form.media (js)
    print('media js select2:', 'select2.full.min.js' in html
          or 'select2.min.js' in html)
    assert i > 0 and ('name="leito"' in trecho) and ('id_atendimento' in trecho)
    print('ok: leito e atendimento digitáveis no modal')
    raise RuntimeError('rollback')
