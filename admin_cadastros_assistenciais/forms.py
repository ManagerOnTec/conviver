from django.core.exceptions import ValidationError
from datetime import datetime
from django.contrib import messages
from django import forms
from contas import models
from . models import CBO, CID, Profissao, Especialidade, OrgaoRegulador, CadastroProfissional, Turnos
from unidecode import unidecode
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.utils.text import capfirst
# from .widgets import TabelaCampoWidget
from dominios.utils import FilterByStatusMixin, validar_whats, validar_telefone
from django.contrib.auth.models import User


class CBOForm(FilterByStatusMixin, forms.ModelForm):

    class Meta:
        model = CBO
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super(CBOForm, self).__init__(*args, **kwargs)
        # Esconda o campo 'status' se for um novo objeto (ou seja, se este for um form de criação)
        if self.instance._state.adding:
            self.fields['status'].widget = forms.HiddenInput()

    def clean_descricao(self):
        return self.cleaned_data['descricao'].title()


class ProfissaoForm(FilterByStatusMixin, forms.ModelForm):

    class Meta:
        model = Profissao
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super(ProfissaoForm, self).__init__(*args, **kwargs)

        if self.instance._state.adding:
            self.fields['status'].widget = forms.HiddenInput()

    def clean_profissao(self):
        return self.cleaned_data['profissao'].title()


class EspecialidadeForm(FilterByStatusMixin, forms.ModelForm):

    class Meta:
        model = Especialidade
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super(EspecialidadeForm, self).__init__(*args, **kwargs)

        if self.instance._state.adding:
            self.fields['status'].widget = forms.HiddenInput()

    def clean_especialidade(self):
        return self.cleaned_data['especialidade'].title()


class OrgaoReguladorForm(FilterByStatusMixin, forms.ModelForm):

    class Meta:
        model = OrgaoRegulador
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super(OrgaoReguladorForm, self).__init__(*args, **kwargs)

        if self.instance._state.adding:
            self.fields['status'].widget = forms.HiddenInput()

    def clean_sigla(self):
        return self.cleaned_data['sigla'].upper()

    def clean_nome(self):
        return self.cleaned_data['nome'].title()


class CadastroProfissionalForm(FilterByStatusMixin, forms.ModelForm):

    class Meta:
        model = CadastroProfissional
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super(CadastroProfissionalForm, self).__init__(*args, **kwargs)

        if self.instance._state.adding:
            self.fields['status'].widget = forms.HiddenInput()


class CIDForm(FilterByStatusMixin, forms.ModelForm):

    class Meta:
        model = CID
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super(CIDForm, self).__init__(*args, **kwargs)

        if self.instance._state.adding:
            self.fields['status'].widget = forms.HiddenInput()

    def clean_nome(self):
        return self.cleaned_data['nome'].title()

    def clean_codigo(self):
        return self.cleaned_data['codigo'].upper()


class TurnosForm(FilterByStatusMixin, forms.ModelForm):

    class Meta:
        model = Turnos
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super(TurnosForm, self).__init__(*args, **kwargs)

        if self.instance._state.adding:
            self.fields['status'].widget = forms.HiddenInput()
