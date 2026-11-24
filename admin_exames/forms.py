from django import forms
from django.core.exceptions import ValidationError
from .models import ParametrosExames, TipoExame
class TipoExameForm(forms.ModelForm):
    class Meta:
        model = TipoExame
        fields = '__all__'
        widgets = {'cor': forms.TextInput(attrs={'type': 'color'})}

class ParametrosExamesForm(forms.ModelForm):
    class Meta:
        model = ParametrosExames
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        profissao = cleaned_data.get('profissao')
        profissional = cleaned_data.get('profissional')
        if bool(profissao) == bool(profissional):
            raise ValidationError('Selecione exatamente uma opção: profissão ou profissional.')
        padrao = cleaned_data.get('tipo_exame_padrao')
        tipos = cleaned_data.get('tipos_exame')
        if padrao and tipos and not tipos.filter(pk=padrao.pk).exists():
            self.add_error('tipo_exame_padrao', 'O tipo padrão deve estar entre os tipos liberados.')
        return cleaned_data
