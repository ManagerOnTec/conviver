from django.utils.text import camel_case_to_spaces
from django.apps import apps
from datetime import datetime
from django.utils import timezone
from django.contrib.auth.models import User
from django.db import models
from dominios.choices import classificacao_pessoa_choices, religiao_choices, cor_raca_choices, estado_civil_choices, nacionalidade_choices, obrigatorios_choices, sexo_choices, sn_choices, status_choices, pessoa_choices, estabelecimento_choices, pessoa_atributo_choices, empresa_atributo_choices
from django.core.exceptions import ValidationError
from django import forms
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from smart_selects.db_fields import ChainedForeignKey
from django.db.models import Q
from django.core.validators import FileExtensionValidator


class BaseModel(models.Model):

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

    def __str__(self):
        return self.descricao


class Estado(models.Model):
    uf = models.CharField(max_length=2, verbose_name='UF', unique=True)
    estado = models.CharField(max_length=255, unique=True)
    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='estado_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True, related_name='estado_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    class Meta:
        verbose_name = 'Estado'
        verbose_name_plural = '3. Estados'
        ordering = ['estado']
        constraints = [
            models.UniqueConstraint(
                fields=['uf', 'status'], name='unique_estado_status')
        ]

    def __str__(self):
        return self.estado


class Cidade(models.Model):
    cidade = models.CharField(max_length=255, unique=True)
    estado = models.ForeignKey(Estado, on_delete=models.PROTECT)
    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='cidade_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True, related_name='cidade_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    class Meta:

        verbose_name = 'Cidade'
        verbose_name_plural = '4. Cidades'
        ordering = ['cidade']
        constraints = [
            models.UniqueConstraint(
                fields=['cidade', 'status'], name='unique_cidade_status')
        ]

    def __str__(self):
        return self.cidade


class Pais(models.Model):
    pais = models.CharField(max_length=255, verbose_name='País', unique=True)

    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='pais_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True, related_name='pais_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    class Meta:

        verbose_name = 'País'
        verbose_name_plural = '5. Países'
        ordering = ['pais']
        constraints = [
            models.UniqueConstraint(
                fields=['pais', 'status'], name='unique_pais_status')
        ]

    def __str__(self):
        return self.pais


class Genero(models.Model):
    genero = models.CharField(max_length=100)
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    class Meta:

        verbose_name = 'Gênero'
        verbose_name_plural = '6. Gêneros'
        ordering = ['genero']

    def __str__(self):
        return self.genero


class Pessoa(models.Model):
    nome = models.CharField(max_length=255)
    classificacao_pessoa = models.CharField(
        max_length=15, choices=classificacao_pessoa_choices, verbose_name='Classificação')
    nacionalidade = models.CharField(
        max_length=255, choices=nacionalidade_choices, default='b')
    pais = models.ForeignKey(
        Pais, on_delete=models.PROTECT, null=True, blank=True, verbose_name='País')
    dt_nascimento = models.DateField(default='',
                                     null=True, blank=True, verbose_name='Data de Nascimento')
    sexo = models.CharField(max_length=1, choices=sexo_choices)
    genero = models.ForeignKey(
        Genero, on_delete=models.PROTECT, blank=True, null=True)
    alergico = models.CharField(
        max_length=1, choices=sn_choices, default='N', verbose_name='Alérgico?')
    alergias = models.CharField(
        default='', max_length=255, null=True, blank=True, verbose_name='Descrição de Alergias')
    cpf = models.CharField(default='', max_length=11, null=True,
                           blank=True, verbose_name='CPF', unique=True)
    rg = models.CharField(default='',
                          max_length=11, null=True, blank=True, verbose_name='RG', unique=True)
    estado_civil = models.CharField(
        max_length=15, blank=True, null=True, choices=estado_civil_choices, verbose_name='Estado Civil')
    naturalidade = models.ForeignKey(
        Cidade, on_delete=models.PROTECT, blank=True, null=True, related_name='naturalidade_pessoa')

    cor_raca = models.CharField(
        max_length=20, choices=cor_raca_choices, blank=True, null=True, verbose_name='Cor/Raça')

    religiao = models.CharField(
        max_length=20, choices=religiao_choices, blank=True, null=True, verbose_name='Religião')

    whats = models.CharField(default='', max_length=14, null=True, blank=True)
    telefone = models.CharField(
        default='', max_length=14, null=True, blank=True)
    email = models.EmailField(default='',
                              max_length=255, null=True, blank=True, verbose_name='E-mail')
    mae = models.CharField(default='', max_length=255, null=True,
                           blank=True, verbose_name='Nome da Mãe')
    pai = models.CharField(default='', max_length=255, null=True,
                           blank=True, verbose_name='Nome do Pai')
    responsavel = models.ForeignKey(
        'Pessoa', on_delete=models.PROTECT, null=True, blank=True, related_name='responsavel_pessoa', verbose_name='Nome do Responsável')
    cep = models.CharField(default='', max_length=8, null=True,
                           blank=True, verbose_name='CEP')
    rua = models.CharField(default='', max_length=255, null=True,
                           blank=True, verbose_name='Rua/Avenida')
    numero = models.CharField(default='', max_length=5, null=True,
                              blank=True, verbose_name='Número')
    complemento = models.CharField(
        default='', max_length=30, null=True, blank=True)
    bairro = models.CharField(default='', max_length=30, null=True, blank=True)
    estado = models.ForeignKey(
        Estado, on_delete=models.PROTECT, verbose_name='estado', null=True, blank=True, related_name='estado_pessoa')
    cidade = ChainedForeignKey(Cidade, on_delete=models.PROTECT,
                               verbose_name='cidade', null=True, blank=True,
                               chained_field='estado',
                               chained_model_field='estado',
                               show_all=False,
                               auto_choose=True)
    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='pessoa_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True, related_name='pessoa_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    class Meta:

        verbose_name = 'Pessoa'
        verbose_name_plural = '7. Pessoas'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Empresa(models.Model):
    nacionalidade = models.CharField(
        max_length=255, choices=nacionalidade_choices, default='b', verbose_name='Nacionalidade')

    razao_social = models.CharField(
        max_length=255, verbose_name='Razão Social')

    fantasia = models.CharField(default='',
                                max_length=255, verbose_name='Nome de Fantasia')
    empresa = models.CharField(default='', max_length=255,
                               verbose_name='Empresa Apelido')
    cnpj = models.CharField(default='', max_length=14, blank=True,
                            null=True, verbose_name='CNPJ', unique=True)
    nome_responsavel = models.CharField(default='',
                                        max_length=255, blank=True, null=True, verbose_name='Nome do Responável')
    nome_contato = models.CharField(default='',
                                    max_length=255, blank=True, null=True, verbose_name='Nome do Contato')
    whats = models.CharField(default='', max_length=14, null=True, blank=True)
    telefone = models.CharField(
        default='', max_length=14, null=True, blank=True)
    email = models.EmailField(default='',
                              max_length=50, blank=True, null=True, verbose_name='E-mail')
    rua = models.CharField(default='', max_length=255, blank=True,
                           null=True, verbose_name='Rua')
    numero = models.CharField(default='', max_length=5, blank=True,
                              null=True, verbose_name='Número')
    complemento = models.CharField(
        default='', max_length=30, blank=True, null=True)
    bairro = models.CharField(default='', max_length=30, blank=True, null=True)
    cep = models.CharField(default='', max_length=8, blank=True,
                           null=True, verbose_name='CEP')
    estado = models.ForeignKey(
        Estado, on_delete=models.PROTECT, verbose_name='estado', blank=True, null=True)
    cidade = ChainedForeignKey(Cidade, on_delete=models.PROTECT,
                               verbose_name='cidade',
                               blank=True,
                               null=True,
                               chained_field="estado",
                               chained_model_field="estado",
                               show_all=False,
                               auto_choose=True,
                               )

    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='empresa_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None,  verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True, related_name='empresa_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = '8. Empresas'
        ordering = ['-pk']
        constraints = [
            models.UniqueConstraint(
                fields=['cnpj', 'status'], name='unique_empresa_status')
        ]

    def __str__(self):
        if self.cnpj:
            return f'{self.empresa} - CNPJ: {self.cnpj}'
        else:
            return self.empresa


class Estabelecimento(models.Model):
    estabelecimento = models.CharField(max_length=255)
    tipo = models.CharField(max_length=50, choices=estabelecimento_choices)
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT)
    logo = models.ImageField(upload_to='anexos/logos/', verbose_name='Logotipos', blank=True, null=True, help_text='Adicione arquivos dos formatos JPG, JPEG, PNG.',
                             validators=[FileExtensionValidator(['jpg', 'jpeg', 'png']),])
    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='estabelecimento_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None,  verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True, related_name='estabelecimento_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    class Meta:

        verbose_name = 'Estabelecimento'
        verbose_name_plural = '9. Estabelecimentos'
        ordering = ['estabelecimento']
        constraints = [
            models.UniqueConstraint(
                fields=['estabelecimento', 'status'], name='unique_estabelecimento_status')
        ]

    def __str__(self):
        return self.estabelecimento


class PessoaCampos(models.Model):
    campo = models.CharField(max_length=100, choices=pessoa_atributo_choices,
                             help_text='Definição de Campos obrigatórios para Cadastro de Pessoas')
    obrigatorio = models.BooleanField(default=True)
    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='pessoa_campos_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None,  verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True, related_name='pessoa_campos_atualizado_por', verbose_name='Us.Atualização')

    class Meta:
        verbose_name = 'Pessoa - campo obrigatório'
        verbose_name_plural = '2. Pessoas - campos obrigatórios'
        ordering = ['campo']
        unique_together = ('campo',)

    def __str__(self):
        return self.campo


class EmpresaCampos(models.Model):
    campo = models.CharField(max_length=100, choices=empresa_atributo_choices,
                             help_text='Definição de Campos obrigatórios para Cadastro de Empresas')
    obrigatorio = models.BooleanField(default=True)

    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='empresa_campos_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None,  verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True, related_name='empresa_campos_atualizado_por', verbose_name='Us.Atualização')

    class Meta:
        verbose_name = 'Empresa - campo obrigatório'
        verbose_name_plural = '1. Empresas - campos obrigatórios'
        ordering = ['campo']
        unique_together = ('campo',)

    def __str__(self):
        return self.campo


class TipoAtendimento(models.Model):
    tipo_atendimento = models.CharField(
        max_length=30, verbose_name='Tipos de Atendimentos')

    observacoes = models.CharField(default='',
                                   max_length=255, null=True, blank=True, verbose_name='Observações')
    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='tipo_atendimento_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None,  verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True, related_name='tipo_atendimento_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    class Meta:

        verbose_name = 'Tipo de Atendimento'
        verbose_name_plural = '10. Tipos de Atendimentos'
        ordering = ['tipo_atendimento']
        constraints = [
            models.UniqueConstraint(
                fields=['tipo_atendimento', 'status'], name='unique_tipo_atendimento_status')
        ]

    def __str__(self):
        return f"{self.tipo_atendimento}"
