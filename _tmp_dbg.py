import os, django
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
    for url in ['/atendimentos/atendimento_listar/','/atendimentos/atendimento_cadastrar/']:
        html = c.get(url).content.decode()
        import re
        # extrai bloco menul
        i = html.find('left-menu'); j = html.find('right-content', i)
        trecho = html[i-200:j]
        # ordem dos elementos-chave
        marks = []
        for pat, nome in [('btn-novo','NOVO'),('voltar-link','VOLTAR'),('custom-link','LISTAR/aux'),('bg-primary','FUNCAO'),('usernav','SESSAO'),('form method','FILTRO-FORM'),('Filtros','H5-FILTROS'),('Funções','GRUPO-FUNCOES')]:
            p = trecho.find(pat)
            if p>0: marks.append((p,nome))
        marks.sort()
        print(url)
        print(' -> '.join(n for _,n in marks))
    raise RuntimeError('rollback')
