from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import models
from admin_cadastros.models import Estabelecimento
from admin_cadastros_assistenciais.models import CadastroProfissional, Especialidade, Profissao
from dominios.choices import status_choices
from django.contrib.auth.models import User
from django.core.validators import MaxLengthValidator
from dominios.text_validators import validate_evolucao_like_text


class TipoEvolucao(models.Model):
    tipo_evolucao = models.CharField(
        max_length=100, verbose_name='Tipos de Evoluções')

    iniciais_nome = models.BooleanField(
        default=False, help_text='Marque este se neste tipo desejar exibir apenas as iniciais do nome do paciente e ocultr o CPF!')

    # Exemplo de campo para cor
    cor = models.CharField(max_length=7, default='#FFFFFF')

    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='tipo_ev_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True, related_name='tipo_ev_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    class Meta:

        verbose_name = 'Tipo de Evolução'
        verbose_name_plural = '1. Tipos de Evoluções'
        ordering = ['tipo_evolucao']

    def __str__(self):
        return f"{self.tipo_evolucao}"


class TextoPadrao(models.Model):
    tipo_evolucao = models.ForeignKey(
        TipoEvolucao, on_delete=models.PROTECT,
        blank=True, null=True,
        verbose_name='Tipo de Evolução')
    profissao = models.ForeignKey(
        Profissao, null=True, blank=True, on_delete=models.PROTECT, verbose_name='Profissao liberada')
    profissional = models.ForeignKey(CadastroProfissional, null=True,
                                     blank=True, on_delete=models.PROTECT, verbose_name='Profissional liberado')
    descricao = models.CharField(
        max_length=255, unique=True, verbose_name='Descrição Identificadora')  # Adicionado unique=True
    texto = models.TextField(validators=[
        validate_evolucao_like_text
    ], verbose_name='Evolução Padronizada')

    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='textopadrao_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, default='', blank=True, null=True, related_name='textopadrao_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    class Meta:
        verbose_name = 'Texto Padrão Evolução'
        verbose_name_plural = '3. Texto Padrão Evoluções'
        ordering = ['descricao']

    def __str__(self):
        return f"{self.descricao}"

    def clean(self):
        # Verificar se exatamente um dos campos está preenchido
        fields = [
            self.tipo_evolucao,
            self.profissao,
            self.profissional]
        filled_fields = [field for field in fields if field is not None]

        if len(filled_fields) != 1:
            raise ValidationError(
                "Selecione um dos campos (tipo evolução, profissao, profissional)."
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class ParametrosEvolucao(models.Model):
    profissao = models.ForeignKey(
        Profissao, on_delete=models.PROTECT, verbose_name='Profissao Evolução', blank=True, null=True)
    profissional = models.ForeignKey(
        User, on_delete=models.PROTECT, verbose_name='Profissional Evolução', blank=True, null=True, related_name='profissional_evolucao')

    tipo_evolucao = models.ManyToManyField(
        'admin_evolucoes.TipoEvolucao', verbose_name='Tipos de Evoluções')
    tipo_evolucao_padrao = models.ForeignKey('admin_evolucoes.TipoEvolucao', on_delete=models.SET_NULL,
                                             verbose_name='Tipo de Evolução Padrão', blank=True, null=True, related_name='tipo_evolucao_padrao')

    observacoes = models.CharField(
        max_length=255, blank=True, null=True, verbose_name='Observações')

    dt_registro = models.DateTimeField(
        default=timezone.now, null=True, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name='parevo_criado_por', verbose_name='Us.Registro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, default='', blank=True, null=True, related_name='parevo_atualizado_por', verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT, verbose_name='Estabelecimento')

    class Meta:
        verbose_name = 'Parâmetros Evoluções'
        verbose_name_plural = '2. Parâmetros Evoluções'
        ordering = ['-pk']

    def __str__(self):
        return f"Parâmetros liberados para {self.profissao} ou {self.profissional}"
