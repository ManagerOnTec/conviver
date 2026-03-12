from django.urls import reverse
from django.utils import timezone
from datetime import datetime
from django.db import models
from admin_cadastros_assistenciais.models import CID
from dominios.choices import tipo_alta_choices, entidade_encaminha_choices, carater_atendimento_choices, obrigatorios_choices, sn_choices, status_choices, pessoa_choices, estabelecimento_choices, periodos_choices, dias_choices
from django.db.models import Q
from django.contrib.auth.models import User
from admin_cadastros.models import Pessoa, Estado, Estabelecimento, Cidade
from django.core.validators import FileExtensionValidator
from multiupload.fields import MultiFileField
from dominios.utils import validate_anexo_file
from admin_cadastros.models import TipoAtendimento, Empresa
from admin_faturas.models import Convenio


class Atendimento(models.Model):
    pessoa = models.ForeignKey(
        Pessoa, on_delete=models.PROTECT, verbose_name='Pessoa')
    tipo_atendimento = models.ForeignKey(
        TipoAtendimento, on_delete=models.PROTECT, verbose_name='Tpo de Atendimento')
    carater_atendimento = models.CharField(
        max_length=1, choices=carater_atendimento_choices, default='E', verbose_name='Caráter do Atendimento')
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT)
    dt_atendimento = models.DateTimeField(default=timezone.now,
                                          verbose_name='Data de Atendimento')
    dt_alta = models.DateTimeField(
        verbose_name='Data de Alta', blank=True, null=True)

    tipo_alta = models.CharField(
        max_length=50, blank=True, null=True, choices=tipo_alta_choices, verbose_name='Tipo de Alta')

    telefone_responsavel = models.CharField(default='',
                                            max_length=14, null=True, blank=True, verbose_name='Telefone do Responsável')
    telefone_familiar = models.CharField(default='',
                                         max_length=14, null=True, blank=True, verbose_name='Telefone do Famíliar')
    telefone_extra = models.CharField(
        default='', max_length=14, null=True, blank=True)
    cidade_encaminhamento = models.ForeignKey(
        Cidade, on_delete=models.PROTECT, blank=True, null=True, verbose_name='Cidade do Encaminhamento', related_name='encaminhamento_cidade')
    entidade_encaminhamento = models.CharField(
        max_length=50, choices=entidade_encaminha_choices, verbose_name='Entidade do Encaminhamento')
    convenio = models.ForeignKey(Convenio, on_delete=models.PROTECT, blank=True, null=True,
                                 verbose_name='Convênio')
    diagnostico_encaminhamento = models.ManyToManyField(
        CID, blank=True, verbose_name='CID - Diagnósticos dos encaminhamentos')
    medicacao = models.CharField(max_length=400, default='',
                                 null=True, blank=True, verbose_name='Uso de Medicação')
    observacoes = models.CharField(max_length=400, default='',
                                   null=True, blank=True, verbose_name='Observações')
    autos_internacao = models.CharField(default='', null=True,
                                        blank=True, max_length=40, verbose_name='Autos da Internação')

    autos_curatela = models.CharField(default='', null=True,
                                      blank=True, max_length=40, verbose_name='Autos da Curatela')

    autos_cobranca = models.CharField(default='', null=True,
                                      blank=True, max_length=40, verbose_name='Autos Cobrança')

    anexo_um = models.FileField(upload_to='anexos/atendimento/%Y/%m/', blank=True, null=True, help_text='Adicione arquivos dos formatos PDF, JPG, JPEG, PNG.',
                                validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png']), validate_anexo_file])

    anexo_dois = models.FileField(upload_to='anexos/atendimento/%Y/%m/', blank=True, null=True, help_text='Adicione arquivos dos formatos PDF, JPG, JPEG, PNG.',
                                  validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png']), validate_anexo_file])

    anexo_tres = models.FileField(upload_to='anexos/atendimento/%Y/%m/', blank=True, null=True, help_text='Adicione arquivos dos formatos PDF, JPG, JPEG, PNG.',
                                  validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png']), validate_anexo_file])

    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='atendimento_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True, related_name='atendimento_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    pessoa_docentrega = models.ForeignKey(Pessoa, on_delete=models.PROTECT, blank=True, null=True,
                                          related_name='pessoa_documento_entrega', verbose_name='Pessoa da Entrega de Documentos')
    cert_nascimento = models.BooleanField(
        verbose_name='Certidão de Nascimento')
    rg = models.BooleanField(verbose_name='RG')
    cpf = models.BooleanField(verbose_name='CPF')
    titulo_eleitor = models.BooleanField(verbose_name='Título de Eleitor')
    carteira_vacina = models.BooleanField(verbose_name='Carteira de Vacina')
    cartao_sus = models.BooleanField(verbose_name='Cartão SUS')
    cartao_banco = models.BooleanField(verbose_name='Cartão Banco')
    carteira_trabalho = models.BooleanField(
        verbose_name='CTPS Carteira de Trabalho')
    foto = models.BooleanField()
    outros = models.BooleanField()

    class Meta:

        verbose_name = 'Atendimento'
        verbose_name_plural = '3.1 Atendimentos'
        ordering = ['-id']

    def __str__(self):
        return f"{self.pessoa.nome}"
