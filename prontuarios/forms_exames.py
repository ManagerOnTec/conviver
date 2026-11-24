from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from dominios.utils import validate_anexo_file
from .models import Exame, ResultadoExame
class ExameForm(forms.ModelForm):
    class Meta:
        model = Exame
        exclude = ('atendimento', 'estabelecimento', 'anexo_exame', 'us_registro', 'dt_registro', 'us_atualizacao', 'dt_atualizacao')
        widgets = {'status': forms.HiddenInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assinar'].help_text = 'Será aplicada a assinatura digital se a sua conta estiver configurada com certificado válido.'

    def clean_tipo_exame(self):
        tipo = self.cleaned_data['tipo_exame']
        if tipo.status != 'A':
            raise ValidationError('Selecione um tipo de exame ativo.')
        return tipo

class ExameCreateForm(ExameForm):
    pass


class ExameUpdateForm(ExameForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].widget = forms.Select(
            choices=self.fields['status'].choices,
            attrs={'class': 'form-control'},
        )


class ResultadoExameForm(forms.ModelForm):
    class Meta:
        model = ResultadoExame
        fields = ('data_resultado', 'anotacoes', 'anexo_1', 'anexo_2', 'anexo_3')
        widgets = {
            'data_resultado': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'anotacoes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'anexo_1': forms.FileInput(),
            'anexo_2': forms.FileInput(),
            'anexo_3': forms.FileInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data_resultado'].required = True
        self.fields['anotacoes'].required = True
        validators = (FileExtensionValidator(['pdf', 'png', 'jpg', 'jpeg']), validate_anexo_file)
        for field_name in ('anexo_1', 'anexo_2', 'anexo_3'):
            self.fields[field_name].validators.extend(validators)
            self.fields[field_name].widget.attrs['accept'] = '.pdf,.png,.jpg,.jpeg'

    def clean(self):
        cleaned_data = super().clean()
        files = [cleaned_data.get('anexo_1'), cleaned_data.get('anexo_2'), cleaned_data.get('anexo_3')]
        names = [file.name for file in files if file]
        if len(names) != len(set(names)):
            raise ValidationError('Não anexe o mesmo arquivo mais de uma vez ao resultado.')
        return cleaned_data


class ResultadoExameEdicaoForm(ResultadoExameForm):
    class Meta(ResultadoExameForm.Meta):
        fields = ResultadoExameForm.Meta.fields + ('status',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data_resultado'].required = False
        self.fields['anotacoes'].required = False
        self.fields['status'].required = False
