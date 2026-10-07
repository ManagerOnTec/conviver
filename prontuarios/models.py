import re
import html
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.files.temp import NamedTemporaryFile
from django.core.files import File
import PyPDF2
from django.core.validators import MaxLengthValidator
from admin_passagem_plantao.models import TipoPassagemPlantao
from admin_plano_cuidados.models import Humor
from admin_prescricoes.models import InicioPlanoTerapeutico, IntervaloHoras
from dominios.choices import duracao_dias_choices
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from datetime import date, datetime, timedelta
from django.db import models
from admin_cadastros.models import Pessoa
from admin_estoques.models import Produto
from atendimentos.models import Atendimento
from admin_cadastros_assistenciais.models import CadastroProfissional, Especialidade, Profissao, Turnos
from dominios.choices import status_choices
from django.contrib.auth.models import User
from admin_cadastros.models import Estabelecimento
from admin_evolucoes.models import TipoEvolucao
from dominios.choices import fase_prescricao_choices, fase_adep_choices
from admin_sae.models import Aspecto, AspectoAnalisado, Evidencia, DiagnosticoEnfermagem, FatorRelacionado, Intervencao
from django.utils.timezone import make_aware
from cryptography.fernet import Fernet
from django.conf import settings
from dominios.utils import EncryptedTextField, validate_anexo_file
from django.core.validators import FileExtensionValidator
from admin_cadastros_assistenciais.models import CID
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from admin_relatorios.models import Relatorio
from admin_relatorios.utils import RelatorioMixin
from django.utils.html import strip_tags
from dominios.text_validators import (
    MAX_RICH_TEXT_LENGTH,
    rich_text_to_plain_text,
    validate_evolucao_like_text,
)

MAX_EVOLUCAO_TEXT_LENGTH = MAX_RICH_TEXT_LENGTH


def _texto_puro_evolucao(value):
    return rich_text_to_plain_text(value)


def validate_evolucao_texto(value):
    validate_evolucao_like_text(value)


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


class Prontuario(Atendimento):
    class Meta:
        proxy = True
        verbose_name = 'Prontuário'
        verbose_name_plural = 'Prontuários'
        ordering = ['-id']


class Diagnostico(models.Model, RelatorioMixin):
    atendimento = models.ForeignKey(Atendimento, on_delete=models.PROTECT)
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT)
    diagnostico = models.ManyToManyField(
        CID, verbose_name='CID - Diagnóstico')
    observacoes = models.CharField(
        max_length=255, blank=True, null=True, verbose_name='Observações')
    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='diagnostico_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True, related_name='diagnostico_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    assinar = models.BooleanField(default=True)

    class Meta:

        verbose_name = 'Diagnóstico'
        verbose_name_plural = 'Diagnósticos'
        ordering = ['-pk']

    def __str__(self):
        return f"{self.diagnostico}"


class Evolucao(models.Model, RelatorioMixin):
    atendimento = models.ForeignKey(Atendimento, on_delete=models.PROTECT)

    tipo_evolucao = models.ForeignKey(
        TipoEvolucao, on_delete=models.PROTECT, verbose_name='Tipo de Evolução')
    evolucao = models.TextField(validators=[
        validate_evolucao_texto,
    ])
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT)

    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='evolucao_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, default='', blank=True, null=True, related_name='evolucao_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    anexo_evolucao = models.FileField(upload_to='anexos/evolucao/%Y/%m/', verbose_name='Imagem', blank=True, null=True, help_text='Adicione arquivos dos formatos JPG, JPEG, PNG.',
                                      validators=[FileExtensionValidator(['jpg', 'jpeg', 'png']), validate_anexo_file])

    assinar = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Evolução'
        verbose_name_plural = 'Evoluções'
        ordering = ['-id']

    def __str__(self):
        return f"{self.evolucao}"


class Psicoterapia(models.Model):
    atendimento = models.ForeignKey(Atendimento, on_delete=models.PROTECT)
    psicoterapia = EncryptedTextField(validators=[MaxLengthValidator(20000)])
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT)

    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='psico_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, default='', blank=True, null=True, related_name='psico_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    class Meta:
        verbose_name = 'Psicoterapia'
        verbose_name_plural = 'Psicoterapias'
        ordering = ['-id']

    def __str__(self):
        return f"{self.psicoterapia}"


class SinaisVitais(models.Model, RelatorioMixin):
    atendimento = models.ForeignKey(
        Atendimento, on_delete=models.PROTECT, verbose_name='Atendimento SV')

    temperatura = models.DecimalField(
        max_digits=4, decimal_places=1, verbose_name='Temperatura (°C)', blank=True, null=True)
    pressao_arterial = models.CharField(
        max_length=7, verbose_name='Pressão arterial (mmHg)', blank=True, null=True)
    frequencia_cardiaca = models.IntegerField(
        verbose_name='Frequência cardíaca (bpm)', blank=True, null=True)
    frequencia_respiratoria = models.IntegerField(
        verbose_name='Frequência respiratória (rpm)', blank=True, null=True)
    saturacao_oxigenio = models.IntegerField(
        verbose_name='Saturação de oxigênio (%)', blank=True, null=True)
    controle_glicemia = models.IntegerField(
        blank=True, null=True, verbose_name='Controle de Glicemia (mg/dL)')

    observacoes = models.CharField(max_length=400,
                                   blank=True, null=True, verbose_name='Observações')

    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT)

    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='sinais_vitais_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, default='', blank=True, null=True, related_name='sinais_vitais_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    assinar = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Sinal Vital'
        verbose_name_plural = 'Sinais Vitais'
        ordering = ['-dt_registro']

    def __str__(self):
        return f'{self.atendimento.pessoa.nome} - {self.dt_registro.strftime("%d/%m/%Y %H:%M")}'


class PerdasGanhos(models.Model, RelatorioMixin):
    atendimento = models.ForeignKey(
        Atendimento, on_delete=models.PROTECT, verbose_name='Atendimento CP')

    # Mudado para IntegerField
    peso = models.IntegerField(verbose_name='Peso (kg)')
    # Mudado para IntegerField
    altura = models.IntegerField(verbose_name='Altura (cm)')
    observacoes = models.CharField(max_length=400,
                                   blank=True, null=True, verbose_name='Observações')

    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT)

    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='controle_peso_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, default='', blank=True, null=True, related_name='controle_peso_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    assinar = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Perdas e Ganhos'
        verbose_name_plural = 'Perdas e Ganhos'
        ordering = ['-dt_registro']

    def __str__(self):
        return f'{self.atendimento.pessoa.nome} - {self.dt_registro.strftime("%d/%m/%Y %H:%M")}'

    @property
    def imc(self):
        if self.altura > 0:
            # Convert cm to meters for correct BMI calculation
            altura_metros = self.altura / 100
            return self.peso / (altura_metros ** 2)
        else:
            return None


class PlanoCuidados(models.Model, RelatorioMixin):
    turnos = models.ForeignKey(
        Turnos, on_delete=models.PROTECT, verbose_name='Turnos')
    atendimento = models.ForeignKey(
        Atendimento, on_delete=models.PROTECT, verbose_name='Atendimento PC')
    eliminacoes_vesicais = models.BooleanField(
        verbose_name='Eliminações Vesicais')
    eliminacoes_intestinais = models.BooleanField(
        verbose_name='Eliminações Intestinais')
    alimentacao = models.BooleanField(verbose_name='Alimentação')
    hidratacao = models.BooleanField(verbose_name='Hidratação')
    higiene_conforto = models.BooleanField(verbose_name='Higiene Conforto')
    higiene_bucal = models.BooleanField(verbose_name='Higiene Bucal')
    atividades_lazer = models.BooleanField(
        verbose_name='Atividades de Lazer e Recreação')
    terapia_ocupacional = models.BooleanField(
        verbose_name='Terapia Ocupacional')
    humor = models.ForeignKey(Humor, on_delete=models.PROTECT)
    observacoes = models.CharField(max_length=400,
                                   blank=True, null=True, verbose_name='Observações')
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT)
    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='plano_cuidados_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, default='', blank=True, null=True, related_name='plano_cuidados_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    assinar = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Plano de Cuidados'
        verbose_name_plural = 'Plano de Cuidados'
        ordering = ['-pk']

    def __str__(self):
        return f'{self.atendimento.pessoa.nome} - {self.dt_registro.strftime("%d/%m/%Y %H:%M")}'


class SAE(models.Model, RelatorioMixin):
    atendimento = models.ForeignKey(
        Atendimento, on_delete=models.PROTECT, verbose_name='Atendimento SAE')

    aspecto = models.ForeignKey(
        Aspecto, on_delete=models.PROTECT, verbose_name='Aspecto')
    aspecto_analisado = models.ForeignKey(
        AspectoAnalisado, on_delete=models.PROTECT, verbose_name='Aspecto Analisado')
    evidencia = models.ManyToManyField(
        Evidencia, verbose_name='Evidências/Características Definidoras')
    diagnostico_enfermagem = models.ForeignKey(
        DiagnosticoEnfermagem, on_delete=models.PROTECT, verbose_name='Diagnóstico de Enfermagem')
    fator_relacionado = models.ManyToManyField(
        FatorRelacionado, verbose_name='Fatores Relacionados')
    intervencao = models.ManyToManyField(
        Intervencao, verbose_name='Intervenções')

    anotacao = models.CharField(max_length=400,
                                verbose_name='Anotações de Enfermagem', blank=True, null=True)

    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT)

    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='sae_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, default='', blank=True, null=True, related_name='sae_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    assinar = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'SAE'
        verbose_name_plural = 'SAE'
        ordering = ['-dt_registro']

    def __str__(self):
        return f'{self.atendimento.pessoa.nome} - {self.dt_registro.strftime("%d/%m/%Y %H:%M")}'


class Prescricao(models.Model, RelatorioMixin):
    prescricao_anterior = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True)
    atendimento = models.ForeignKey(
        Atendimento, on_delete=models.PROTECT, verbose_name='Atendimento')
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT, verbose_name='Estabelecimento')
    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')

    us_prescricao_inicial = models.ForeignKey(User, on_delete=models.PROTECT, null=True,
                                              blank=True,       related_name='us_prescricao_inicial', verbose_name='Us.Pres.Inicial')

    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='prescricao_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, default='', blank=True, null=True, related_name='prescricao_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    dt_inicio = models.DateTimeField(
        verbose_name='Data de Início', default=datetime.today)
    fase = models.CharField(choices=fase_prescricao_choices,
                            max_length=1, default='U', verbose_name='Fase da Prescrição')

    dt_final = models.DateTimeField(
        verbose_name='Dt.Final')

    us_suspensao = models.ForeignKey(User, on_delete=models.PROTECT, null=True,
                                     blank=True,       related_name='us_suspensao', verbose_name='Us.Suspensão')
    dt_suspensao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Suspensão')

    assinar = models.BooleanField(default=True)

    class Meta(BaseModelPrescricao.Meta):
        verbose_name = 'Prescrição'
        verbose_name_plural = 'Prescrições'

    def __str__(self):
        return f"{self.id}"


class ProdutoPrescricao(BaseModelPrescricao):
    prescricao = models.ForeignKey(
        Prescricao, related_name='produtos', on_delete=models.CASCADE, verbose_name='Prescrição')
    produto = models.ForeignKey(
        Produto, on_delete=models.PROTECT, verbose_name='Produto')
    intervalo_horas = models.ForeignKey(
        IntervaloHoras, on_delete=models.PROTECT, verbose_name='Intervalos')
    se_necessario = models.BooleanField(
        default=False, verbose_name='Se necessário?')

    dose_unica = models.BooleanField(default=False, verbose_name='Dose Única?',
                                     help_text='Marque se o medicamento for administrado apenas uma vez.')

    observacao = models.CharField(
        blank=True, null=True, max_length=11, verbose_name='Observações gerais')
    dt_inicio = models.DateTimeField()

    hora_inicio_produto = models.ForeignKey(
        InicioPlanoTerapeutico, on_delete=models.PROTECT, verbose_name='Hora de Início', related_name='hora_inicio_produto')

    dt_final = models.DateTimeField(
        verbose_name='Dt.Fim', blank=True, null=True)

    atendimento = models.ForeignKey(
        Atendimento, on_delete=models.PROTECT, verbose_name='Atendimento')
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT, verbose_name='Estabelecimento Itens Prescricao')

    class Meta(BaseModelPrescricao.Meta):
        verbose_name = 'Produto da Prescrição'
        verbose_name_plural = 'Produtos da Prescrição'

        ordering = ['dt_inicio']

    def save(self, *args, **kwargs):
        # Se dt_inicio não estiver definido, pegue de Prescricao (como estava antes)
        if not self.dt_inicio:
            prescricao = self.prescricao
            self.dt_inicio = prescricao.dt_inicio

        if not self.dt_final:
            prescricao = self.prescricao
            self.dt_final = prescricao.dt_final

        if self.prescricao:
            self.atendimento = self.prescricao.atendimento
            self.estabelecimento = self.prescricao.estabelecimento

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Produto {self.produto.descricao} da {self.prescricao}"


class Adep(BaseModelPrescricao):
    prescricao = models.ForeignKey(
        Prescricao, on_delete=models.CASCADE, verbose_name='Prescrição')
    data_hora = models.DateTimeField(verbose_name='Dt.Prescrição')
    produto_prescricao = models.ForeignKey(
        ProdutoPrescricao, on_delete=models.PROTECT, verbose_name='Produto da Prescrição')

    fase_adep = models.CharField(
        choices=fase_adep_choices,
        max_length=20,
        default='P',
        verbose_name='Fase da Administração',
        blank=True,
        null=True,
    )

    fase_prescricao = models.CharField(choices=fase_prescricao_choices,
                                       max_length=1, default='U', verbose_name='Fase da Prescricao', blank=True, null=True)

    se_necessario = models.BooleanField(
        default=False, verbose_name='Se necessário?')
    dose_unica = models.BooleanField(default=False, verbose_name='Dose Única?')
    observacao = models.CharField(max_length=255, blank=True, null=True)

    assinar = models.BooleanField(default=False)

    pdf = models.BooleanField(default=False)

    atendimento = models.ForeignKey(
        Atendimento, on_delete=models.PROTECT, verbose_name='Atendimento')
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT, verbose_name='Estabelecimento')

    us_suspensao = models.ForeignKey(User, on_delete=models.PROTECT, null=True,
                                     blank=True,       related_name='us_suspensao_adep', verbose_name='Us.Suspensão')
    dt_suspensao = models.DateTimeField(
        default=None, blank=True, null=True, verbose_name='Dt.Suspensão')

    us_adep = models.ForeignKey(User, on_delete=models.PROTECT, null=True,
                                blank=True, related_name='us_adep', verbose_name='Us.Administração')
    dt_adep = models.DateTimeField(
        default=None, blank=True, null=True, verbose_name='Dt.Administração')

    class Meta(BaseModelPrescricao.Meta):
        verbose_name = 'Adep'
        verbose_name_plural = 'Adep'

        ordering = ['data_hora']

    def __str__(self):
        return f"Adep #{self.id}"


class PassagemPlantao(models.Model):
    tipo_passagem_plantao = models.ForeignKey(
        TipoPassagemPlantao, on_delete=models.PROTECT, verbose_name='Tipos de Passagem de Plantão')

    passagem_plantao = models.TextField(validators=[MaxLengthValidator(25000)])

    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT)

    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='passpla_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, default='', blank=True, null=True, related_name='passpla_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    class Meta:
        verbose_name = 'Passagem de Plantão'
        verbose_name_plural = 'Passagem de Plantões'
        ordering = ['-id']

    def __str__(self):
        return f"{self.passagem_plantao}"
