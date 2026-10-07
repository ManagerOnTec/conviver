import uuid

from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from admin_cadastros.models import Estabelecimento, Pessoa
from atendimentos.models import Atendimento
from dominios.choices import status_choices
from dominios.text_validators import validate_evolucao_like_text


def _build_upload_path(instance, prefix, filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'bin'
    codigo = instance.codigo_documento or 'pendente'
    atendimento_id = instance.atendimento_id or 'sem_atendimento'
    return f'documentos_legais/{atendimento_id}/{codigo}/{prefix}.{ext}'


def assinatura_upload_path(instance, filename):
    return _build_upload_path(instance, 'assinatura', filename)


def documento_frente_upload_path(instance, filename):
    return _build_upload_path(instance, 'documento_frente', filename)


def documento_verso_upload_path(instance, filename):
    return _build_upload_path(instance, 'documento_verso', filename)


def selfie_upload_path(instance, filename):
    return _build_upload_path(instance, 'selfie', filename)


def pdf_upload_path(instance, filename):
    return _build_upload_path(instance, 'termo_assinado', filename)


class TipoDocumentoLegal(models.Model):
    nome = models.CharField(max_length=150, unique=True, verbose_name='Tipo de Termo')
    slug = models.SlugField(max_length=160, unique=True, verbose_name='Identificador')
    descricao = models.CharField(max_length=255, blank=True, null=True, verbose_name='Descrição')
    ordem = models.PositiveIntegerField(default=0, verbose_name='Ordem')
    padrao_sistema = models.BooleanField(default=False, verbose_name='Padrão do Sistema')
    status = models.CharField(max_length=1, choices=status_choices, default='A')
    dt_registro = models.DateTimeField(default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='tipo_documento_legal_criado_por',
        verbose_name='Us.Registro',
    )
    dt_atualizacao = models.DateTimeField(blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='tipo_documento_legal_atualizado_por',
        verbose_name='Us.Atualização',
    )

    class Meta:
        verbose_name = 'Tipo de Documento Legal'
        verbose_name_plural = '1. Tipos de Documentos Legais'
        ordering = ['ordem', 'nome']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome


class ModeloDocumentoLegal(models.Model):
    tipo_documento = models.ForeignKey(
        TipoDocumentoLegal,
        on_delete=models.PROTECT,
        related_name='modelos',
        verbose_name='Tipo de Termo',
    )
    estabelecimento = models.ForeignKey(
        Estabelecimento,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        verbose_name='Estabelecimento',
        help_text='Deixe em branco para um modelo global do sistema.',
    )
    nome_modelo = models.CharField(max_length=150, verbose_name='Nome do Modelo')
    titulo_documento = models.CharField(max_length=255, verbose_name='Título do Documento')
    conteudo_html = models.TextField(
        validators=[validate_evolucao_like_text],
        verbose_name='Conteúdo do Termo',
        help_text=(
            'Placeholders disponíveis: {{ paciente_nome }}, {{ paciente_cpf }}, {{ paciente_dt_nascimento }}, '
            '{{ atendimento_id }}, {{ responsavel_nome }}, {{ responsavel_cpf }}, {{ responsavel_documento }}, '
            '{{ responsavel_data_nascimento }}, {{ responsavel_telefone }}, {{ responsavel_email }}, '
            '{{ data_documento }}, {{ estabelecimento_nome }}.'
        ),
    )
    status = models.CharField(max_length=1, choices=status_choices, default='A')
    dt_registro = models.DateTimeField(default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='modelo_documento_legal_criado_por',
        verbose_name='Us.Registro',
    )
    dt_atualizacao = models.DateTimeField(blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='modelo_documento_legal_atualizado_por',
        verbose_name='Us.Atualização',
    )

    class Meta:
        verbose_name = 'Modelo de Documento Legal'
        verbose_name_plural = '2. Modelos de Documentos Legais'
        ordering = ['tipo_documento__ordem', 'nome_modelo']

    def __str__(self):
        if self.estabelecimento:
            return f'{self.nome_modelo} - {self.estabelecimento}'
        return f'{self.nome_modelo} - Global'


class DocumentoLegalInternacao(models.Model):
    atendimento = models.ForeignKey(
        Atendimento,
        on_delete=models.PROTECT,
        related_name='documentos_legais',
        verbose_name='Atendimento',
    )
    pessoa = models.ForeignKey(
        Pessoa,
        on_delete=models.PROTECT,
        related_name='documentos_legais',
        verbose_name='Paciente',
    )
    estabelecimento = models.ForeignKey(
        Estabelecimento,
        on_delete=models.PROTECT,
        related_name='documentos_legais',
        verbose_name='Estabelecimento',
    )
    tipo_documento = models.ForeignKey(
        TipoDocumentoLegal,
        on_delete=models.PROTECT,
        related_name='documentos_gerados',
        verbose_name='Tipo de Termo',
    )
    modelo_documento = models.ForeignKey(
        ModeloDocumentoLegal,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='documentos_gerados',
        verbose_name='Modelo Aplicado',
    )
    codigo_documento = models.CharField(max_length=32, unique=True, editable=False, verbose_name='Código')
    titulo_documento = models.CharField(max_length=255, verbose_name='Título do Documento')
    conteudo_html = models.TextField(validators=[validate_evolucao_like_text], verbose_name='Conteúdo Congelado')
    responsavel_nome = models.CharField(max_length=255, verbose_name='Responsável')
    responsavel_cpf = models.CharField(max_length=18, verbose_name='CPF do Responsável')
    responsavel_documento = models.CharField(max_length=50, verbose_name='Documento de Identificação')
    responsavel_data_nascimento = models.DateField(verbose_name='Data de Nascimento do Responsável')
    responsavel_telefone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Telefone')
    responsavel_email = models.EmailField(blank=True, null=True, verbose_name='E-mail')
    declaracao_aceite = models.BooleanField(default=False, verbose_name='Li e concordo com o termo')
    assinatura_imagem = models.ImageField(upload_to=assinatura_upload_path, blank=True, null=True, verbose_name='Assinatura Desenhada')
    documento_frente = models.ImageField(
        upload_to=documento_frente_upload_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
        verbose_name='Documento Frente',
    )
    documento_verso = models.ImageField(
        upload_to=documento_verso_upload_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
        verbose_name='Documento Verso',
    )
    selfie = models.ImageField(
        upload_to=selfie_upload_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
        verbose_name='Selfie',
    )
    pdf_gerado = models.FileField(upload_to=pdf_upload_path, blank=True, null=True, verbose_name='PDF Gerado')
    hash_pdf = models.CharField(max_length=64, blank=True, null=True, verbose_name='Hash SHA-256')
    dt_assinatura = models.DateTimeField(blank=True, null=True, verbose_name='Dt.Assinatura')
    ip_assinatura = models.CharField(max_length=45, blank=True, null=True, verbose_name='IP')
    user_agent = models.CharField(max_length=500, blank=True, null=True, verbose_name='User Agent')
    observacoes = models.CharField(max_length=255, blank=True, null=True, verbose_name='Observações')
    status = models.CharField(max_length=1, choices=status_choices, default='A')
    dt_registro = models.DateTimeField(default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='documento_legal_criado_por',
        verbose_name='Us.Registro',
    )
    dt_atualizacao = models.DateTimeField(blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='documento_legal_atualizado_por',
        verbose_name='Us.Atualização',
    )

    class Meta:
        verbose_name = 'Documento Legal de Internação'
        verbose_name_plural = '3. Documentos Legais de Internação'
        ordering = ['-dt_registro', '-id']

    def save(self, *args, **kwargs):
        if not self.codigo_documento:
            self.codigo_documento = uuid.uuid4().hex[:16].upper()
        if not self.pessoa_id and self.atendimento_id:
            self.pessoa = self.atendimento.pessoa
        if not self.estabelecimento_id and self.atendimento_id:
            self.estabelecimento = self.atendimento.estabelecimento
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.codigo_documento} - {self.titulo_documento}'
