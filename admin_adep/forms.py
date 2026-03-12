from dominios.utils import FilterByStatusMixin
from .models import ParametrosAdep
from django import forms
from django.core.exceptions import ValidationError


# Custom form for ParametrosPrescricao in admin
class ParametrosAdepAdminForm(FilterByStatusMixin, forms.ModelForm):
    class Meta:
        model = ParametrosAdep
        fields = '__all__'

    # Validando que 'usuario' ou 'grupo' sejam selecionados, mas não ambos.
    # Também valida que pelo menos um campo 'permite' deve ser verdadeiro
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
