import os, django, re
os.environ.setdefault('DJANGO_SETTINGS_MODULE','managerontec.settings')
django.setup()
from django.db import transaction
from django.test import Client
from django.contrib.auth.models import User
from admin_cadastros.models import Estabelecimento
with transaction.atomic():
    user = User.objects.filter(is_superuser=True).first()
    est = Estabelecimento.objects.first()
    c = Client(SERVER_NAME='localhost'); c.force_login(user)
    s = c.session; s['estabelecimento_id']=est.pk; s.save()
    html = c.get('/atendimentos/atendimento_listar/').content.decode()
    i = html.find('left-menu')
    j = html.find('</form>', i)
    trecho = re.sub(r'\n\s*\n','\n',html[i-150:j+10])
    print(trecho[:4000])
    raise RuntimeError('rollback')
