from dominios.utils import FilterByStatusMixin
from .models import ParametrosSinaisVitais
from django import forms
from django.core.exceptions import ValidationError


# Custom form for ParametrosPrescricao in admin
class ParametrosSinaisVitaisAdminForm(FilterByStatusMixin, forms.ModelForm):
    class Meta:
        model = ParametrosSinaisVitais
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        profissional = cleaned_data.get("profissional")
        profissao = cleaned_data.get("profissao")

        if profissional is None and profissao is None:
            raise ValidationError(
                "Ao menos um entre 'Usuário' e 'Grupo' deve ser fornecido.")
        elif profissional is not None and profissao is not None:
            raise ValidationError(
                "Selecione apenas um entre 'Usuário' e 'Grupo'.")

        return cleaned_data
