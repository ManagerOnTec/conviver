"""Debug: chamar InlinePessoaCreateView.post diretamente (traceback real)."""
import os
import django
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'managerontec.settings')
django.setup()

from django.test import RequestFactory
from django.db import transaction
from django.contrib.auth.models import User

with transaction.atomic():
    from atendimentos.views import InlinePessoaCreateView
    rf = RequestFactory()
    user = User.objects.filter(is_superuser=True).first()
    req = rf.post('/atendimentos/inline/pessoa/', {
        'nome': 'QA MOD PAC5', 'cpf': '', 'classificacao': 'paciente'})
    req.user = user
    req.session = {'estabelecimento_id': None}
    view = InlinePessoaCreateView()
    try:
        resp = view.post(req)
        print('RESP:', resp.status_code, resp.content.decode()[:200])
    except Exception:
        traceback.print_exc()
    raise RuntimeError('rollback')
