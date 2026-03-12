from tinymce.widgets import TinyMCE
from django import forms
from django.utils import timezone
from django.forms import TextInput, inlineformset_factory
from admin_evolucoes.models import TipoEvolucao, TextoPadrao
from django.core.validators import MinLengthValidator
from dominios.utils import FilterByStatusMixin
from .models import ParametrosPassagemPlantao, TipoPassagemPlantao
from django.core.exceptions import ValidationError


class TipoPassagemPlantaoForm(FilterByStatusMixin, forms.ModelForm):

    class Meta:
        model = TipoPassagemPlantao
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super(TipoPassagemPlantaoForm, self).__init__(*args, **kwargs)

        if self.instance._state.adding:
            self.fields['status'].widget = forms.HiddenInput()

    def clean_tipo_passagem_plantao(self):
        return self.cleaned_data['tipo_passagem_plantao'].title()


class ParametrosPassagemPlantaoAdminForm(forms.ModelForm):
    class Meta:
        model = ParametrosPassagemPlantao
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super(ParametrosPassagemPlantaoAdminForm,
              self).__init__(*args, **kwargs)

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
