from django_select2.forms import Select2Widget
from django_select2.forms import ModelSelect2Widget  # Atualize esta linha
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.models import User
from datetime import datetime
from django.contrib import messages
from django import forms
from contas import models
from dominios.widgets import DateTimePickerInput
from . models import Estado, Cidade, Genero, Pessoa, Empresa, Estabelecimento, PessoaCampos, EmpresaCampos, TipoAtendimento, Pais
from unidecode import unidecode
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.utils.text import capfirst
from .widgets import TabelaCampoWidget
from dominios.utils import FilterByStatusMixin, NoneToEmptyMixin, validar_whats, validar_telefone
from django.forms.widgets import DateInput, DateTimeInput


# BASE ###############################################################
class BaseModelForm(forms.ModelForm):
    class Meta:
        fields = ['dt_registro', 'us_registro',
                  'dt_atualizacao', 'us_atualizacao', 'status']
        abstract = True

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super(BaseModelForm, self).__init__(*args, **kwargs)
        if self.instance._state.adding:
            self.fields['status'].widget = forms.HiddenInput()


# ESTADO ##############################################################

class EstadoForm(FilterByStatusMixin, forms.ModelForm):
    class Meta:
        model = Estado
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(EstadoForm, self).__init__(*args, **kwargs)

        # Esconda o campo 'status' se for um novo objeto (ou seja, se este for um form de criação)
        if self.instance._state.adding:
            self.fields['status'].widget = forms.HiddenInput()

    def clean_uf(self):
        return self.cleaned_data['uf'].upper()

    def clean_estado(self):
        return self.cleaned_data['estado'].title()


# CIDADE ######################################################


class CidadeForm(FilterByStatusMixin, forms.ModelForm):

    class Meta:
        model = Cidade
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(CidadeForm, self).__init__(*args, **kwargs)

        # Esconda o campo 'status' se for um novo objeto (ou seja, se este for um form de criação)
        if self.instance._state.adding:
            self.fields['status'].widget = forms.HiddenInput()

    def clean_cidade(self):
        return self.cleaned_data['cidade'].title()


# pais

class PaisForm(FilterByStatusMixin, forms.ModelForm):

    class Meta:
        model = Pais
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super(PaisForm, self).__init__(*args, **kwargs)

        # Esconda o campo 'status' se for um novo objeto (ou seja, se este for um form de criação)
        if self.instance._state.adding:
            self.fields['status'].widget = forms.HiddenInput()

    def clean_pais(self):
        return self.cleaned_data['pais'].title()


class GeneroForm(FilterByStatusMixin, forms.ModelForm):
    class Meta:
        model = Genero
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(GeneroForm, self).__init__(*args, **kwargs)

    def clean_genero(self):
        return self.cleaned_data['genero'].title()

# PESSOA ###############################################################


class PessoaAdminForm(FilterByStatusMixin, forms.ModelForm):

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
        }

        status = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, *args, usuario=None, nacionalidade=None, **kwargs):
        self.usuario = usuario
        self.nacionalidade = nacionalidade
        super(PessoaAdminForm, self).__init__(*args, **kwargs)

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


class PessoaDetailForm(NoneToEmptyMixin, FilterByStatusMixin, forms.ModelForm):

    class Meta:
        model = Pessoa
        # Adicione aqui os campos que deseja incluir no formulário.
        fields = '__all__'

    def __init__(self, *args, usuario=None, nacionalidade=None, **kwargs):
        super(PessoaDetailForm, self).__init__(*args, **kwargs)

        for field in self.fields:
            self.fields[field].widget.attrs['disabled'] = True
            if self.fields[field].initial is None:
                self.fields[field].initial = ''
# EMPRESA ######################################################


class EmpresaForm(FilterByStatusMixin, forms.ModelForm):

    telefone = forms.CharField(
        label='Telefone',
        max_length=14,

        required=False,
        widget=forms.TextInput(attrs={'placeholder': '+55 XX X XXXX-XXXX'})
    )

    whats = forms.CharField(
        label='whats',
        max_length=14,

        required=False,
        widget=forms.TextInput(attrs={'placeholder': '+55 XX X XXXX-XXXX'})
    )

    class Meta:
        model = Empresa
        fields = '__all__'

    def __init__(self, *args, usuario=None, nacionalidade=None, **kwargs):
        self.usuario = usuario
        self.nacionalidade = nacionalidade
        super(EmpresaForm, self).__init__(*args, **kwargs)

        # Esconda o campo 'status' se for um novo objeto (ou seja, se este for um form de criação)
        if self.instance._state.adding:
            self.fields['status'].widget = forms.HiddenInput()

        config_campos = EmpresaCampos.objects.all()

        for config_campo in config_campos:
            campo = config_campo.campo
            obrigatorio = config_campo.obrigatorio

            if campo in self.fields:
                self.fields[campo].required = obrigatorio

    def clean_empresa(self):
        empresa = self.cleaned_data['empresa']
        if empresa:
            return self.cleaned_data['empresa'].title()

    def clean_fantasia(self):
        fantasia = self.cleaned_data['fantasia']
        if fantasia:
            return self.cleaned_data['fantasia'].title()

    def clean_razao_social(self):
        razao_social = self.cleaned_data['razao_social']
        if razao_social:
            return self.cleaned_data['razao_social'].title()

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

    def clean_cnpj(self):
        cnpj = self.cleaned_data.get('cnpj', '')
        if not cnpj:
            return cnpj
        cnpj_digits = ''.join(filter(str.isdigit, cnpj))
        if len(cnpj_digits) != 14:
            raise forms.ValidationError(
                'O CNPJ deve ter 14 dígitos e somente números')
        return cnpj_digits

    def clean(self):
        cleaned_data = super().clean()

        nacionalidade = cleaned_data.get('nacionalidade')

        if nacionalidade == 'e':
            if 'cnpj' in self._errors:
                del self._errors['cnpj']
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


# ESTABELECIMENTO ######################################################


class EstabelecimentoForm(FilterByStatusMixin, forms.ModelForm):

    class Meta:
        model = Estabelecimento
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super(EstabelecimentoForm, self).__init__(*args, **kwargs)

        # Esconda o campo 'status' se for um novo objeto (ou seja, se este for um form de criação)
        if self.instance._state.adding:
            self.fields['status'].widget = forms.HiddenInput()

    def clean_estabelecimento(self):
        return self.cleaned_data['estabelecimento'].title()


class PessoaCamposForm(FilterByStatusMixin, forms.ModelForm):

    class Meta:
        model = PessoaCampos
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)


class EmpresaCamposForm(FilterByStatusMixin, forms.ModelForm):

    class Meta:
        model = EmpresaCampos
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)


class TipoAtendimentoForm(FilterByStatusMixin, forms.ModelForm):

    class Meta:
        model = TipoAtendimento
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super(TipoAtendimentoForm, self).__init__(*args, **kwargs)

        # Esconda o campo 'status' se for um novo objeto (ou seja, se este for um form de criação)
        if self.instance._state.adding:
            self.fields['status'].widget = forms.HiddenInput()

    def clean_tipo_atendimento(self):
        tipo_atendimento = self.cleaned_data['tipo_atendimento']
        if tipo_atendimento:
            return self.cleaned_data['tipo_atendimento'].title()


class TipoAtendimentoOpForm(FilterByStatusMixin, forms.Form):
    tipo_atendimento = TipoAtendimento.objects.all()
