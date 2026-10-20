from django.db import models
from admin_cadastros.models import Estabelecimento
from admin_cadastros_assistenciais.models import Profissao
from dominios.choices import intervalo_horas_choices, status_choices, duracao_presc_choices
from django.utils import timezone
from django.contrib.auth.models import User


class BaseModelPrescricao(models.Model):
    dt_registro = models.DateTimeField(
        default=timezone.now, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='%(class)s_registro', verbose_name='Us.Registro', null=True, blank=True)
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='%(class)s_atualizacao', null=True, blank=True, verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    class Meta:
        abstract = True
        ordering = ['-pk']


class InicioPlanoTerapeutico(BaseModelPrescricao):
    hora_inicio = models.TimeField(
        verbose_name='Hora inicial do plano terapêutico', default='07:00:00')
    padrao = models.BooleanField(default=False)
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT, verbose_name='Estabelecimento')

    class Meta(BaseModelPrescricao.Meta):
        verbose_name = 'Horário padrão para início do plano terapêutico prescrito'
        verbose_name_plural = '3. Horário padrão para início do plano terapêutico prescrito'

    def save(self, *args, **kwargs):
        if self.padrao and self.status == 'A':
            # Set all other objects with the same estabelecimento to padrao=False
            InicioPlanoTerapeutico.objects.filter(
                estabelecimento=self.estabelecimento, status='A').update(padrao=False)

        super(InicioPlanoTerapeutico, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.hora_inicio}"


class IntervaloHoras(BaseModelPrescricao):
    intervalo_horas = models.PositiveIntegerField(choices=intervalo_horas_choices,
                                                  verbose_name='Intervalo em horas')

    padrao = models.BooleanField(default=False)

    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT, verbose_name='Estabelecimento')

    class Meta(BaseModelPrescricao.Meta):
        verbose_name = 'Intervalo em horas para prescrições'
        verbose_name_plural = '2. Intervalos em horas para prescrições'

    def save(self, *args, **kwargs):
        if self.padrao and self.status == 'A':
            # Set all other objects with the same estabelecimento to padrao=False
            IntervaloHoras.objects.filter(
                estabelecimento=self.estabelecimento, status='A').update(padrao=False)

        super(IntervaloHoras, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_intervalo_horas_display()}"


class HorarioRestritoPrescricao(BaseModelPrescricao):
    hora_inicio = models.TimeField(
        verbose_name='Hora inicial de restrição', default='00:00:00')
    hora_final = models.TimeField(
        verbose_name='Hora final de restrição', default='06:00:00')
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT, verbose_name='Estabelecimento')

    class Meta(BaseModelPrescricao.Meta):
        verbose_name = 'Horário Restrito para prescrição'
        verbose_name_plural = '4. Horários Restritos para prescrições'

    def __str__(self):
        return f"Restrição: {self.hora_inicio}h até {self.hora_final}h"


class ParametrosPrescricao(models.Model):
    profissao = models.ForeignKey(
        Profissao, on_delete=models.PROTECT, verbose_name='Profissão Prescrição', null=True, blank=True)
    profissional = models.ForeignKey(User, on_delete=models.PROTECT,
                                     verbose_name='Profissional Prescrição', null=True, blank=True, related_name='profissional_prescricao')

    dias = models.PositiveIntegerField(choices=duracao_presc_choices,
                                       help_text='Validade de dias posteriores a data inicial, para permitir prescrever',
                                       verbose_name='Intervalo Dias Permitido', default='1')

    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT, verbose_name='Estabelecimento')
    status = models.CharField(choices=status_choices,
                              max_length=1, default='A')

    permite_prescricao_retroativa = models.BooleanField(
        default=False, help_text='NÃO RECOMENDADO! Permissão para prescrever retroativamente, utilizado em implantações/exceções!')

    permite_editar_outras = models.BooleanField(
        default=False, help_text='Permissão para editar prescrições de outros profissionais')

    permite_suspender_outras = models.BooleanField(
        default=False, help_text='Permissão para suspender prescrições de outros profissionais')

    class Meta:
        verbose_name = 'Parametros Prescrição'
        verbose_name_plural = '1. Parametros Prescricao'

    def __str__(self):
        return f'Pode criar e editar Prescrições'
