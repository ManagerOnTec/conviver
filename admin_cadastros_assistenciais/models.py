from django.urls import reverse
from datetime import datetime
from django.utils import timezone
from django.db import models
from dominios.choices import turnos, obrigatorios_choices, sn_choices, status_choices, pessoa_choices, estabelecimento_choices, periodos_choices, dias_choices
from django.db.models import Q
from django.contrib.auth.models import User
from admin_cadastros.models import Pessoa, Estado


class CBO(models.Model):
    codigo_cbo = models.CharField(max_length=6, verbose_name='Código CBO')
    descricao = models.CharField(max_length=200, verbose_name='Descrição CBO')
    escolaridade_minima = models.CharField(
        max_length=100, null=True, blank=True, verbose_name='Escolaridade Mínima')
    salario_medio = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='Salário Médio')
    area_atuacao = models.CharField(
        max_length=100, null=True, blank=True, verbose_name='Área de Atuação')
    habilidades_requeridas = models.TextField(
        null=True, blank=True, verbose_name='Habilidades Requiridas')
    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='cbo_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True, related_name='cbo_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    class Meta:

        verbose_name = 'CBO - Classificação Brasileira de Ocupações'
        verbose_name_plural = '3. CBO - Classificação Brasileira de Ocupações'
        ordering = ['descricao']
        constraints = [
            models.UniqueConstraint(
                fields=['codigo_cbo', 'status'], name='unique_cbo_status')
        ]

    def __str__(self):
        return self.descricao


class Profissao(models.Model):
    profissao = models.CharField(max_length=255, verbose_name='Profissão')
    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='profissao_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True, related_name='profissao_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    class Meta:

        verbose_name = 'Profissão'
        verbose_name_plural = '1. Profissões'
        ordering = ['profissao']
        constraints = [
            models.UniqueConstraint(
                fields=['profissao', 'status'], name='unique_profissao_status')
        ]

    def __str__(self):
        return self.profissao


class Especialidade(models.Model):
    especialidade = models.CharField(max_length=255)
    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='especialidade_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True, related_name='especialidade_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    class Meta:

        verbose_name = 'Especialidade'
        verbose_name_plural = '2. Especialidades'
        ordering = ['especialidade']
        constraints = [
            models.UniqueConstraint(
                fields=['especialidade', 'status'], name='unique_especialidade_status')
        ]

    def __str__(self):
        return self.especialidade


class ProfissionalEspecialidade(models.Model):
    profissional = models.ForeignKey(
        'CadastroProfissional', on_delete=models.PROTECT, verbose_name='Profissional')
    especialidade = models.ForeignKey(
        Especialidade, on_delete=models.PROTECT, verbose_name='Especialidade')
    numero_especialidade = models.CharField(
        max_length=20, verbose_name='Número Reg.Esp.')

    class Meta:
        unique_together = ('profissional', 'especialidade')
        verbose_name = 'Especialidade do Profissional'
        verbose_name_plural = 'Especialidades dos Profissionais'

    def __str__(self):
        return f"{self.especialidade.especialidade} - RQE: {self.numero_especialidade}"


class OrgaoRegulador(models.Model):
    sigla = models.CharField(
        max_length=100, verbose_name='Sigla Órgão Regulador')
    descricao = models.CharField(
        max_length=100, verbose_name='descricao por Extenso')
    uf = models.ForeignKey(Estado, on_delete=models.PROTECT, verbose_name='UF')
    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='orgao_regulador_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True, related_name='orgao_regulador_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    class Meta:

        verbose_name = 'Orgão Regulador'
        verbose_name_plural = '4. Orgãos Reguladores'
        ordering = ['descricao']
        constraints = [
            models.UniqueConstraint(
                fields=['descricao', 'status'], name='unique_orgao_regulador_status')
        ]

    def __str__(self):
        return self.descricao


class CadastroProfissional(models.Model):
    profissional = models.ForeignKey(
        User, on_delete=models.PROTECT, verbose_name='Usuario Associado ao Profissional')
    profissao = models.ForeignKey(
        Profissao, on_delete=models.PROTECT, verbose_name='Profissão')
    orgao_regulador = models.ForeignKey(
        OrgaoRegulador, on_delete=models.PROTECT, verbose_name='Orgão Regulador')
    numero = models.CharField(
        max_length=20, verbose_name='Número', help_text='CRM/Coren/Etc')

    especialidades = models.ManyToManyField(
        Especialidade, through='ProfissionalEspecialidade', blank=True, verbose_name='Especialidades')

    cbo = models.ForeignKey(
        CBO, on_delete=models.PROTECT, null=True, blank=True, verbose_name='CBO')
    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='cadastro_medico_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True, related_name='cadastro_medico_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    class Meta:

        verbose_name = 'Cadastro Profissional da Assistencia'
        verbose_name_plural = '7. Cadastro de Profissionais da Assistencia'
        ordering = ['profissional']
        constraints = [
            models.UniqueConstraint(
                fields=['profissional', 'status'], name='unique_cadmedicoass_status')
        ]

    def __str__(self):
        return str(self.profissional)


class CID(models.Model):
    codigo = models.CharField(
        max_length=6, verbose_name='Código CID', unique=True)
    descricao = models.CharField(
        max_length=200, verbose_name='descricao Código CID')
    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='cid_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True, related_name='cid_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    class Meta:

        verbose_name = 'CID'
        verbose_name_plural = '5. Classif CID'
        ordering = ['descricao']

    def __str__(self):
        return f"{self.codigo} - {str(self.descricao)}"


class Turnos(models.Model):
    turnos = models.CharField(
        max_length=20, choices=turnos, verbose_name='Turnos')
    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='turnos_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True, related_name='turnos_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    class Meta:

        verbose_name = 'Turnos Assistência'
        verbose_name_plural = '6. Turnos Assistência'
        ordering = ['-pk']

    def __str__(self):
        return str(self.turnos)
