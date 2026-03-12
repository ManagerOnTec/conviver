
from django import forms
from django.utils import timezone
from django.forms import TextInput, inlineformset_factory
from .models import ProntuarioAcessos
from django.core.validators import MinLengthValidator


class ProntuarioAcessosCreateForm(forms.ModelForm):
    class Meta:
        model = ProntuarioAcessos
        fields = ['motivo_acesso', 'item_prontuario', 'dt_acesso', 'us_acesso']
        widgets = {
            'us_acesso': forms.TextInput(attrs={'readonly': True}),
            'dt_acesso': forms.TextInput(attrs={'readonly': True}),
            'item_prontuario': TextInput(attrs={'readonly': True}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['item_prontuario'].initial = 'lista de prontuários'
        self.fields['us_acesso'].initial = self.request.user
        self.fields['motivo_acesso'].validators.append(
            MinLengthValidator(8))  # Aqui está a mudança

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.us_acesso = self.request.user
        instance.dt_acesso = timezone.now()

        if commit:
            instance.save()
        return instance
