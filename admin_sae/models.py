from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from pydantic import ValidationError
from dominios.choices import status_choices
from admin_cadastros_assistenciais.models import Profissao
from admin_cadastros.models import BaseModel, Estabelecimento


class Aspecto(BaseModel):
    descricao = models.CharField(max_length=255, verbose_name='Descrição')

    class Meta:
        verbose_name = 'Aspecto'
        verbose_name_plural = '2. Aspectos'

    def __str__(self):
        return f'{self.descricao}'


class AspectoAnalisado(BaseModel):

    descricao = models.CharField(max_length=255, verbose_name='Descrição')
    aspecto = models.ForeignKey(
        Aspecto, on_delete=models.PROTECT)

    class Meta:
        verbose_name = 'Aspecto Analisado'
        verbose_name_plural = '3. Aspectos Analisados'

    def __str__(self):
        return f'{self.descricao}'


class Evidencia(BaseModel):

    descricao = models.CharField(max_length=255, verbose_name='Descrição')
    aspecto_analisado = models.ForeignKey(
        AspectoAnalisado, on_delete=models.PROTECT)

    class Meta:
        verbose_name = 'Evidência/Característica Definidora'
        verbose_name_plural = '4. Evidências/Características Definidoras'

    def __str__(self):
        return f'{self.descricao}'


class DiagnosticoEnfermagem(BaseModel):

    descricao = models.CharField(max_length=255, verbose_name='Descrição')
    evidencia = models.ManyToManyField(Evidencia)

    class Meta:
        verbose_name = 'Diagnóstico de Enfermagem'
        verbose_name_plural = '5. Diagnósticos de Enfermagem'

    def __str__(self):
        return f'{self.descricao}'


class FatorRelacionado(BaseModel):

    descricao = models.CharField(max_length=255, verbose_name='Descrição')
    diagnostico_enfermagem = models.ForeignKey(
        DiagnosticoEnfermagem, on_delete=models.PROTECT, verbose_name='Diagnóstico de Enfermagem')

    class Meta:
        verbose_name = 'Fator Relacionado'
        verbose_name_plural = '6. Fatores Relacionados'

    def __str__(self):
        return f'{self.descricao}'


class Intervencao(BaseModel):

    descricao = models.CharField(max_length=255, verbose_name='Descrição')
    fator_relacionado = models.ForeignKey(
        FatorRelacionado, on_delete=models.PROTECT, verbose_name='Fator Relacionado')

    class Meta:
        verbose_name = 'Intervenção'
        verbose_name_plural = '7. Intervenções'

    def __str__(self):
        return f'{self.descricao}'


class ParametrosSAE(BaseModel):
    profissao = models.ForeignKey(
        Profissao, on_delete=models.PROTECT, verbose_name='Profissao SAE', blank=True, null=True)
    profissional = models.ForeignKey(
        User, on_delete=models.PROTECT, verbose_name='Profissional SAE', blank=True, null=True, related_name='profissional_sae')
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT, verbose_name='Estabelecimento',)

    class Meta:
        verbose_name = 'Parametros SAE'
        verbose_name_plural = '1. Parametros SAE'

    def __str__(self):
        return f'Pode criar e editar SAE'
