"""Verificação (rollback): criar bloqueio/higienização/livre SEM atendimento."""
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
    est = Estabelecimento.objects.first()
    client = Client(SERVER_NAME='localhost')
    client.force_login(user)
    s = client.session
    s['estabelecimento_id'] = est.pk
    s.save()
    ala = Ala(estabelecimento=est, nome='ALA NF', internacao=True,
              us_registro=user)
    ala.save()
    setor = Setor(estabelecimento=est, ala=ala, nome='SETOR NF',
                  us_registro=user)
    setor.save()
    local = Local(setor=setor, nome='LOCAL NF', us_registro=user)
    local.save()
    l1 = Leito(local=local, leito='NF1', us_registro=user)
    l1.save()
    l2 = Leito(local=local, leito='NF2', us_registro=user)
    l2.save()
    l3 = Leito(local=local, leito='NF3', us_registro=user)
    l3.save()
    agora = timezone.localtime().strftime('%Y-%m-%dT%H:%M')

    for situacao, leito in (('B', l1), ('H', l2), ('L', l3)):
        r = client.post('/leitos/ocupacao_cadastrar/', {
            'leito': leito.pk, 'atendimento': '', 'dt_entrada': agora,
            'situacao': situacao, 'observacoes': 'operacional'})
        leito.refresh_from_db()
        occ = GestaoLeito.objects.filter(leito=leito,
                                         dt_saida__isnull=True).first()
        assert occ is not None and occ.atendimento_id is None, \
            f'{situacao}: {occ}'
        assert not leito.ocupado, f'{situacao} não deve marcar ocupado'
        print(f'{situacao} sem atendimento: ok (histórico + sem flag ocupado)')

    # detalhe renderiza sem atendimento
    occ = GestaoLeito.objects.filter(leito=l1, dt_saida__isnull=True).first()
    r = client.get(f'/leitos/ocupacao/{occ.pk}/detalhe/')
    assert r.status_code == 200
    html = r.content.decode()
    assert 'Sem atendimento (leito operacional)' in html
    print('detalhe sem atendimento: ok')

    raise RuntimeError('rollback')
