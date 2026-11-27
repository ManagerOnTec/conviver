"""Debug 2: valida form liberando o atendimento primeiro."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'managerontec.settings')
django.setup()

from django.db import transaction
from django.utils import timezone
from gestao_leitos.forms import OcupacaoForm
from admin_cadastros.models import Estabelecimento, Ala, Setor, Local, Leito
from atendimentos.models import Atendimento
from gestao_leitos.models import GestaoLeito

with transaction.atomic():
    at1 = Atendimento.objects.select_related('estabelecimento').first()
    est = at1.estabelecimento
    # libera at1 (dentro do rollback)
    for o in GestaoLeito.objects.filter(atendimento=at1, dt_saida__isnull=True):
        o.situacao = 'L'
        o.dt_saida = timezone.now()
        o.save(update_fields=['situacao', 'dt_saida'])
    ala = Ala(estabelecimento=est, nome='ALA RL4', internacao=True)
    ala.save()
    setor = Setor(estabelecimento=est, ala=ala, nome='SETOR RL4')
    setor.save()
    local = Local(setor=setor, nome='LOCAL RL4')
    local.save()
    l1 = Leito(local=local, leito='RL4')
    l1.save()
    agora = timezone.localtime().strftime('%Y-%m-%dT%H:%M')
    form = OcupacaoForm(
        data={'leito': l1.pk, 'atendimento': at1.pk, 'dt_entrada': agora,
              'situacao': 'O'},
        estabelecimento=est)
    print('VALID:', form.is_valid())
    print('ERRORS:', dict(form.errors))
    print('QS TOTAL:', form.fields['atendimento'].queryset.count())
    print('AT1 NA QS:', form.fields['atendimento'].queryset.filter(
        pk=at1.pk).exists())
    raise RuntimeError('rollback')
