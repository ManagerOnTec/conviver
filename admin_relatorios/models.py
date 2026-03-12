from django.core.validators import MaxLengthValidator
from dominios.choices import status_choices
from admin_cadastros_assistenciais.models import CadastroProfissional, Especialidade, Profissao
from admin_cadastros.models import Estabelecimento
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from atendimentos.models import Atendimento
from dominios.choices import relatorios_choices, status_choices
from admin_cadastros.models import Estabelecimento, Pessoa
from django.contrib.auth.models import User
from admin_evolucoes.models import TipoEvolucao

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class GerenciadorRelatorioGeral(models.Model):
    logo_header = models.ImageField(upload_to='anexos/logos/', verbose_name='Logotipo', blank=True, null=True, help_text='Adicione arquivos dos formatos JPG, JPEG, PNG.',
                                    validators=[FileExtensionValidator(['jpg', 'jpeg', 'png']),])

    dados_header = models.CharField(
        max_length=255, verbose_name='Título do Relatório')
    dados_right_header = models.CharField(
        max_length=255, verbose_name='Anotações a direita do cabeçalho', blank=True, null=True)
    dados_footer = models.CharField(
        max_length=255, verbose_name='Dados para rodapé', blank=True, null=True)

    cidade = models.CharField(
        max_length=100, verbose_name='Cidade')

    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='relger_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, default='', blank=True, null=True, related_name='relger_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT, verbose_name='Estabelecimento')

    # Campos adicionais conforme necessário...

    class Meta:
        verbose_name = 'Gerenciador de Relatório Geral'
        verbose_name_plural = '2. Gerenciadores de Relatórios Gerais'

    def __str__(self):
        return self.dados_header


class GerenciadorRelatorioPersonalizado(models.Model):

    relatorio = models.CharField(max_length=50, choices=relatorios_choices)

    tipo_evolucao = models.ForeignKey(
        TipoEvolucao, on_delete=models.PROTECT, blank=True, null=True)

    cidade = models.CharField(
        max_length=100, verbose_name='Cidade')

    # Repetir os campos do modelo geral
    logo_header = models.ImageField(upload_to='anexos/logos/', verbose_name='Logotipo', blank=True, null=True, help_text='Adicione arquivos dos formatos JPG, JPEG, PNG.',
                                    validators=[FileExtensionValidator(['jpg', 'jpeg', 'png']),])

    dados_header = models.CharField(
        max_length=255, verbose_name='Título do Relatório')
    dados_right_header = models.CharField(
        max_length=255, verbose_name='Anotações a direita do cabeçalho', blank=True, null=True)

    dados_footer = models.CharField(
        max_length=255, verbose_name='Dados para rodapé',  blank=True, null=True)

    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='relper_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, default='', blank=True, null=True, related_name='relper_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT, verbose_name='Estabelecimento')

    # Campos adicionais específicos do relatório personalizado...

    class Meta:
        verbose_name = 'Gerenciador de Relatório Personalizado'
        verbose_name_plural = '1. Gerenciadores de Relatórios Personalizados'

    def __str__(self):
        return self.dados_header


class Relatorio(models.Model):
    relatorio = models.FileField(upload_to='relatorios/')
    # Por exemplo, 'prescricao', 'adep', 'evolucao', 'ata', 'oficio', 'orcamento', etc.
    tipo = models.CharField(max_length=10)

    # Campos para implementação da chave genérica
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    atendimento = models.ForeignKey(
        Atendimento, on_delete=models.PROTECT, blank=True, null=True)
    pessoa = models.ForeignKey(
        Pessoa, on_delete=models.PROTECT, blank=True, null=True)

    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    def __str__(self):
        return f"{self.tipo} - {self.content_object}"


# Definindo as escolhas para o campo 'tipo'
TIPO_CHOICES = [
    ('atas', 'Atas'),
    ('oficios', 'Ofícios'),
    ('orcamentos', 'Orçamentos'),
]


class TextoDocumentoPadrao(models.Model):
    tipo = models.CharField(
        max_length=20,  # Tamanho máximo para o campo
        choices=TIPO_CHOICES,  # Usando as escolhas definidas
        blank=True, null=True,
        verbose_name='Tipo de Documento'
    )

    descricao = models.CharField(
        max_length=255, unique=True, verbose_name='Descrição Identificadora'
    )

    texto = models.TextField(
        validators=[MaxLengthValidator(4000)], verbose_name='Textos Padronizados'
    )

    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro'
    )

    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True,
        related_name='textodocpadrao_criado_por', verbose_name='Us.Registro'
    )

    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização'
    )

    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, default='', blank=True, null=True,
        related_name='textodocpadrao_atualizado_por', verbose_name='Us.Atualização'
    )

    status = models.CharField(
        max_length=1, choices=status_choices, default='A'
    )

    class Meta:
        verbose_name = 'Texto Padrão Documentos'
        verbose_name_plural = '3. Texto Padrão Documentos'
        ordering = ['descricao']

    def __str__(self):
        return f"{self.descricao}"

    def clean(self):
        # Verificar se exatamente um dos campos está preenchido
        if not self.tipo:
            raise ValidationError(
                "Selecione um tipo de documento (atas, ofícios, orçamentos)."
            )

    def save(self, *args, **kwargs):
        self.clean()  # Executa a validação antes de salvar
        super().save(*args, **kwargs)
