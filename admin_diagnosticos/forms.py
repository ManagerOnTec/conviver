from tinymce.widgets import TinyMCE
from django import forms
from django.utils import timezone
from django.forms import TextInput, inlineformset_factory
from admin_evolucoes.models import TipoEvolucao, TextoPadrao
from django.core.validators import MinLengthValidator
from dominios.utils import FilterByStatusMixin
from .models import ParametrosDiagnostico
from django.core.exceptions import ValidationError


class ParametrosDiagnosticoAdminForm(forms.ModelForm):
    class Meta:
        model = ParametrosDiagnostico
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super(ParametrosDiagnosticoAdminForm, self).__init__(*args, **kwargs)

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
