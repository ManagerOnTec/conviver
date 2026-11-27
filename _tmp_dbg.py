"""Debug: POST de ocupação direto com mensagens."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'managerontec.settings')
django.setup()

from django.db import transaction
from django.test import Client
from django.contrib.auth.models import User
from django.utils import timezone

with transaction.atomic():
    from admin_cadastros.models import Estabelecimento, Ala, Setor, Local, Leito
    from atendimentos.models import Atendimento
    from gestao_leitos.models import GestaoLeito
    user = User.objects.filter(is_superuser=True).first()
    at1 = Atendimento.objects.select_related('estabelecimento').first()
    est = at1.estabelecimento
    client = Client(SERVER_NAME='localhost')
    client.force_login(user)
    s = client.session
    s['estabelecimento_id'] = est.pk
    s.save()
    ala = Ala(estabelecimento=est, nome='ALA RL2', internacao=True,
              us_registro=user)
    ala.save()
    setor = Setor(estabelecimento=est, ala=ala, nome='SETOR RL2',
                  us_registro=user)
    setor.save()
    local = Local(setor=setor, nome='LOCAL RL2', us_registro=user)
    local.save()
    l1 = Leito(local=local, leito='RL2', us_registro=user)
    l1.save()
    agora = timezone.localtime().strftime('%Y-%m-%dT%H:%M')
    r = client.post('/leitos/ocupacao_cadastrar/', {
        'leito': l1.pk, 'atendimento': at1.pk, 'dt_entrada': agora,
        'situacao': 'O'})
    from django.contrib.messages import get_messages
    print('MSGS:', [str(m) for m in get_messages(r.wsgi_request)])
    print('LEITO OCUPADO:', Leito.objects.get(pk=l1.pk).ocupado)
    raise RuntimeError('rollback')
