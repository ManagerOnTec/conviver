import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','managerontec.settings')
django.setup()
from gestao_leitos.forms import OcuparLeitoForm
from admin_cadastros.models import Estabelecimento
f = OcuparLeitoForm(estabelecimento=Estabelecimento.objects.first())
html = str(f['atendimento'])
print('LEN:', len(html))
print(html[:400])
print('---')
print('select?', '<select' in html)
