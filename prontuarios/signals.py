
from datetime import datetime, timedelta
from django.utils.timezone import make_aware, is_naive, get_current_timezone
from django.utils.timezone import get_current_timezone
from datetime import timezone as dt_timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta, datetime
from admin_prescricoes.models import HorarioRestritoPrescricao
from .models import ProdutoPrescricao, Adep, Prescricao
from django.utils.timezone import is_naive, make_aware, now, get_current_timezone


def horario_permitido(time, estabelecimento):
    """
    Verifica se o horário está dentro dos horários restritos.
    Retorna False se estiver em um intervalo restrito, caso contrário, True.
    """
    intervalos_restritos = HorarioRestritoPrescricao.objects.filter(
        estabelecimento=estabelecimento, status='A')

    for intervalo in intervalos_restritos:
        if intervalo.hora_inicio <= time.time() <= intervalo.hora_final:
            return False
    return True


@receiver(post_save, sender=ProdutoPrescricao)
def criar_adep_condicional(sender, instance, created, **kwargs):
    """
    Cria Adeps ao salvar um ProdutoPrescricao.
    Se for dose única, cria apenas um Adep. Caso contrário, cria múltiplos conforme o intervalo de horas.
    """
    if created:
        if instance.dose_unica:
            criar_adep_unico(instance)
        else:
            criar_adep(instance)


def criar_adep_unico(instance):
    """
    Cria um único Adep para ProdutoPrescricao com dose única.
    Garante que a `data_hora` seja maior ou igual a `dt_inicio` da prescrição.
    """
    inicio = instance.dt_inicio

    if inicio and is_naive(inicio):
        inicio = make_aware(inicio, timezone=get_current_timezone())

    adep = Adep(
        prescricao=instance.prescricao,
        data_hora=inicio,
        produto_prescricao=instance,
        us_registro=instance.us_registro,
        dt_registro=instance.dt_registro,
        se_necessario=instance.se_necessario,
        dose_unica=instance.dose_unica,
        observacao=instance.observacao,
        atendimento=instance.atendimento,
        estabelecimento=instance.estabelecimento,
    )
    adep.save()

# signals.py

# signals.py


def criar_adep(instance):
    dt_inicio_prescricao = instance.prescricao.dt_inicio
    dt_final_prescricao = instance.dt_final
    intervalo_horas = int(instance.intervalo_horas.intervalo_horas)
    hora_inicio = instance.hora_inicio_produto.hora_inicio
    tz = get_current_timezone()

    if is_naive(dt_inicio_prescricao):
        dt_inicio_prescricao = make_aware(dt_inicio_prescricao, timezone=tz)
    if is_naive(dt_final_prescricao):
        dt_final_prescricao = make_aware(dt_final_prescricao, timezone=tz)

    data_atual = dt_inicio_prescricao.date()
    data_fim = dt_final_prescricao.date()

    while data_atual <= data_fim:
        if data_atual == dt_inicio_prescricao.date():
            horario_base = datetime.combine(data_atual, hora_inicio)
            horario_base = make_aware(horario_base, timezone=tz)

            if horario_base < dt_inicio_prescricao:
                delta = dt_inicio_prescricao - horario_base
                horas_ajuste = ((delta.total_seconds() // 3600) //
                                intervalo_horas + 1) * intervalo_horas
                horario_base += timedelta(hours=horas_ajuste)
        else:
            horario_base = datetime.combine(data_atual, hora_inicio)
            horario_base = make_aware(horario_base, timezone=tz)

        while horario_base.date() == data_atual and horario_base <= dt_final_prescricao:
            restrito = False
            for intervalo in HorarioRestritoPrescricao.objects.filter(estabelecimento=instance.estabelecimento, status='A'):
                if intervalo.hora_inicio <= horario_base.time() < intervalo.hora_final:
                    restrito = True
                    horario_base = datetime.combine(
                        data_atual, intervalo.hora_final)
                    horario_base = make_aware(horario_base, timezone=tz)
                    break

            if restrito:
                continue

            if horario_permitido(horario_base, instance.estabelecimento):
                Adep.objects.create(
                    prescricao=instance.prescricao,
                    data_hora=horario_base,
                    produto_prescricao=instance,
                    us_registro=instance.us_registro,
                    dt_registro=instance.dt_registro,
                    se_necessario=instance.se_necessario,
                    dose_unica=instance.dose_unica,
                    observacao=instance.observacao,
                    atendimento=instance.atendimento,
                    estabelecimento=instance.estabelecimento,
                )

            horario_base += timedelta(hours=intervalo_horas)

        data_atual += timedelta(days=1)


# Fim def criar adeps

@receiver(post_save, sender=Prescricao)
def update_adep_status(sender, instance, **kwargs):
    """
    Atualiza o status dos Adeps quando uma nova prescrição é criada com base em uma anterior.
    Suspende os Adeps anteriores caso necessário.
    """
    if instance.prescricao_anterior_id:
        combined_datetime = instance.dt_inicio

        if is_naive(combined_datetime):
            dt_inicio_anterior = make_aware(combined_datetime)
        else:
            dt_inicio_anterior = combined_datetime

        dt_inicio_anterior_utc = dt_inicio_anterior.astimezone(utc)

        adeps_to_update = Adep.objects.filter(
            prescricao_id=instance.prescricao_anterior.id,
            fase_adep='P',
            fase_prescricao='U',
            data_hora__gte=dt_inicio_anterior_utc,
        )

        if adeps_to_update.exists():
            adeps_to_update.update(
                fase_adep='S',
                fase_prescricao='S',
                dt_atualizacao=now(),
                us_atualizacao=instance.us_atualizacao,
                dt_suspensao=now(),
                us_suspensao=instance.us_atualizacao
            )


@receiver(post_save, sender=Prescricao)
def update_pres_adep_status(sender, instance, **kwargs):
    """
    Atualiza os Adeps quando o status da prescrição muda para 'S'.
    """
    if kwargs.get('update_fields') is None or 'fase' in kwargs['update_fields']:
        if instance.fase == 'S':
            combined_datetime = instance.dt_inicio

            if is_naive(combined_datetime):
                dt_inicio_anterior = make_aware(combined_datetime)
            else:
                dt_inicio_anterior = combined_datetime

            dt_inicio_anterior_utc = dt_inicio_anterior.astimezone(utc)

            adeps_to_update = Adep.objects.filter(
                prescricao=instance,
                fase_adep='P',
                fase_prescricao='U',
                data_hora__gte=dt_inicio_anterior_utc,
            )

            if adeps_to_update.exists():
                adeps_to_update.update(
                    fase_adep='S',
                    fase_prescricao='S',
                    dt_atualizacao=now(),
                    us_atualizacao=instance.us_atualizacao,
                    dt_suspensao=now(),
                    us_suspensao=instance.us_atualizacao
                )
