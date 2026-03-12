from tinymce.widgets import TinyMCE
from django import forms
from django.utils import timezone
from django.forms import TextInput, inlineformset_factory
from admin_evolucoes.models import TipoEvolucao, TextoPadrao
from django.core.validators import MinLengthValidator
from dominios.utils import FilterByStatusMixin
from .models import ParametrosEvolucao
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from dominios.utils import validar_tamanho_ata


class ParametrosEvolucaoAdminForm(forms.ModelForm):
    class Meta:
        model = ParametrosEvolucao
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super(ParametrosEvolucaoAdminForm, self).__init__(*args, **kwargs)

        if self.instance._state.adding:
            self.fields['status'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        profissao = cleaned_data.get('profissao')
        profissional = cleaned_data.get('profissional')

        # Verifica se pelo menos um dos campos está preenchido
        if not (profissao or profissional):
            raise ValidationError(
                "Pelo menos um entre 'Profissão' e 'Profissional' deve ser preenchido.")

        return cleaned_data


class TipoEvolucaoForm(FilterByStatusMixin, forms.ModelForm):

    class Meta:
        model = TipoEvolucao
        fields = '__all__'
        widgets = {
            'cor': forms.TextInput(attrs={'type': 'color'}),
        }

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super(TipoEvolucaoForm, self).__init__(*args, **kwargs)

        if self.instance._state.adding:
            self.fields['status'].widget = forms.HiddenInput()

    def clean_tipo_evolucao(self):
        return self.cleaned_data['tipo_evolucao'].title()


class TextoPadraoForm(FilterByStatusMixin, forms.ModelForm):

    texto = forms.CharField(widget=TinyMCE(
        attrs={'cols': 80, 'rows': 25}), validators=[
            validar_tamanho_ata
    ])

    class Meta:
        model = TextoPadrao
        fields = '__all__'

    def clean_descricao(self):
        return self.cleaned_data['descricao'].title()

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super(TextoPadraoForm, self).__init__(*args, **kwargs)

        if self.instance._state.adding:
            self.fields['status'].widget = forms.HiddenInput()
