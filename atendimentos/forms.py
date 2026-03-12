from django.db import IntegrityError
from admin_cadastros.models import Pessoa, PessoaCampos, TipoAtendimento
from datetime import datetime
from django.contrib import messages
from django import forms
from contas import models
from . models import Atendimento
from unidecode import unidecode
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.utils.text import capfirst
from admin_cadastros.widgets import TabelaCampoWidget
from dominios.utils import FilterByStatusMixin, validar_whats, validar_telefone
from django_select2.forms import Select2Widget
from django_select2.forms import ModelSelect2Widget
from django_select2.views import AutoResponseView
from django.forms.widgets import DateInput, DateTimeInput
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from dominios.widgets import DateTimePickerInput
from django.core.validators import FileExtensionValidator
from django_select2.forms import Select2MultipleWidget
from admin_cadastros_assistenciais.models import CID


class AtendimentoCreateForm(FilterByStatusMixin, forms.ModelForm):

    class Meta:
        model = Atendimento
        exclude = ('dt_registro', 'dt_atualizacao',
                   'us_registro', 'us_atualizacao', 'status', 'dt_alta', 'estabelecimento',)

        widgets = {
            'dt_atendimento': DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
            'dt_alta': DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
            'pessoa': Select2Widget(attrs={'data-width': '100%'}),
            'empresa': Select2Widget(attrs={'data-width': '100%'}),
            'cidade_encaminhamento': Select2Widget(attrs={'data-width': '100%'}),
            'entidade_encaminhamento': Select2Widget(attrs={'data-width': '100%'}),
            'pessoa_docentrega': Select2Widget(attrs={'data-width': '100%'}),
            'convenio': Select2Widget(attrs={'data-width': '100%'}),
        }

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        self.fields['diagnostico_encaminhamento'] = forms.ModelMultipleChoiceField(
            queryset=CID.objects.all(),
            widget=Select2MultipleWidget(attrs={'data-width': '100%'}),
            required=False,
            label='CID - Diagnósticos dos encaminhamentos'
        )
        self.fields['pessoa'].queryset = Pessoa.objects.filter(status__in=['A'], classificacao_pessoa='paciente')

    def clean(self):
        cleaned_data = super().clean()
        pessoa = cleaned_data.get('pessoa')
        estabelecimento = cleaned_data.get('estabelecimento')

        exists = Atendimento.objects.filter(
            pessoa=pessoa,
            estabelecimento=estabelecimento,
            status='A',
            dt_alta__isnull=False
        ).exclude(pk=self.instance.pk).exists()

        if exists:
            raise forms.ValidationError(
                "Já existe um registro ativo para esta pessoa e estabelecimento.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.us_registro = self.usuario
        if commit:
            instance.save()
        return instance


class AtendimentoDetailForm(forms.ModelForm):
    class Meta:
        model = Atendimento
        exclude = ('pessoa',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields:
            self.fields[field].widget.attrs['disabled'] = True

###############################################################################


class AtendimentoUpdateForm(FilterByStatusMixin, forms.ModelForm):
    class Meta:
        model = Atendimento
        exclude = ('dt_registro', 'dt_atualizacao', 'us_registro',
                   'us_atualizacao', 'estabelecimento', 'pessoa')

        widgets = {
            'dt_atendimento': DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
            'dt_alta': DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
            'pessoa': Select2Widget(attrs={'data-width': '100%'}),
            'empresa': Select2Widget(attrs={'data-width': '100%'}),
            'cidade_encaminhamento': Select2Widget(attrs={'data-width': '100%'}),
            'entidade_encaminhamento': Select2Widget(attrs={'data-width': '100%'}),
            'pessoa_docentrega': Select2Widget(attrs={'data-width': '100%'}),
            'convenio': Select2Widget(attrs={'data-width': '100%'}),
        }

    def __init__(self, *args, **kwargs):
        super(AtendimentoUpdateForm, self).__init__(*args, **kwargs)
        self.fields['diagnostico_encaminhamento'] = forms.ModelMultipleChoiceField(
            queryset=CID.objects.all(),
            required=False,
            label='CID - Diagnósticos dos encaminhamentos',
            widget=Select2MultipleWidget(attrs={'data-width': '100%'})
        )
        # Ajustar o queryset dos outros campos, se necessário


class PessoaForm(FilterByStatusMixin, forms.ModelForm):

    telefone = forms.CharField(
        label='Telefone',

        required=False,
        widget=forms.TextInput(attrs={'placeholder': '+55 XX X XXXX-XXXX'})
    )

    whats = forms.CharField(
        label='whats',

        required=False,
        widget=forms.TextInput(attrs={'placeholder': '+55 XX X XXXX-XXXX'})
    )

    class Meta:
        model = Pessoa
        exclude = ('dt_registro', 'dt_atualizacao',
                   'us_registro', 'us_atualizacao', )

        widgets = {
            'dt_nascimento': DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'naturalidade': Select2Widget(attrs={'data-width': '100%'}),
            'responsavel': Select2Widget(attrs={'data-width': '100%'}),
            'estado': Select2Widget(attrs={'data-width': '100%'}),
            'cidade': Select2Widget(attrs={'data-width': '100%'}),
        }

        status = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, *args, usuario=None, nacionalidade=None, **kwargs):
        self.usuario = usuario
        self.nacionalidade = nacionalidade
        super(PessoaForm, self).__init__(*args, **kwargs)

        if self.instance._state.adding:
            self.fields['status'].widget = forms.HiddenInput()

        config_campos = PessoaCampos.objects.all()

        for config_campo in config_campos:
            campo = config_campo.campo
            obrigatorio = config_campo.obrigatorio

            if campo in self.fields:
                self.fields[campo].required = obrigatorio

    def clean_nome(self):
        return self.cleaned_data['nome'].title()

    def clean_whats(self):
        whats = self.cleaned_data['whats']
        if whats and not validar_whats(whats):
            raise forms.ValidationError(
                'Número Inválido, siga o padrao com código do país "+55" e DDD "47", ex: "+5547912341234"')
        return whats

    def clean_telefone(self):
        telefone = self.cleaned_data['telefone']
        if telefone and not validar_telefone(telefone):
            raise forms.ValidationError(
                'Número Inválido, sempre informe o DDD "47"')
        return telefone

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf', '')
        if not cpf:
            return cpf
        cpf_digits = ''.join(filter(str.isdigit, cpf))
        if len(cpf_digits) != 11:
            raise forms.ValidationError(
                'O CPF deve ter 11 dígitos e somente números')

        if Pessoa.objects.filter(cpf=cpf_digits).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Esse CPF já está cadastrado.')

        return cpf_digits

    def clean(self):

        cleaned_data = super().clean()
        nacionalidade = cleaned_data.get('nacionalidade')

        if nacionalidade == 'e':
            if 'cpf' in self._errors:
                del self._errors['cpf']
            if 'rg' in self._errors:
                del self._errors['rg']
            if 'naturalidade' in self._errors:
                del self._errors['naturalidade']
            if 'cidade' in self._errors:
                del self._errors['cidade']
            if 'estado' in self._errors:
                del self._errors['estado']
            if 'cep' in self._errors:
                del self._errors['cep']
            if 'bairro' in self._errors:
                del self._errors['bairro']
            if 'complemento' in self._errors:
                del self._errors['complemento']
            if 'numero' in self._errors:
                del self._errors['numero']
            if 'rua' in self._errors:
                del self._errors['rua']

        return cleaned_data
