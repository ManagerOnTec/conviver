from django.core.exceptions import ValidationError
from .models import ParametrosPrescricao
from django.forms import inlineformset_factory
from django import forms
from dominios.utils import FilterByStatusMixin
from .models import HorarioRestritoPrescricao, InicioPlanoTerapeutico, IntervaloHoras, ParametrosPrescricao
from admin_estoques.models import Produto
from dominios.choices import intervalo_horas_choices, horas_choices, status_choices
from django.utils import timezone
from django.contrib.auth.models import User
from django.forms import HiddenInput, formset_factory
from django.forms import modelformset_factory


# BASE ###############################################################


class BaseModelPrescricaoForm(forms.ModelForm):
    class Meta:
        fields = ['dt_registro', 'us_registro',
                  'dt_atualizacao', 'us_atualizacao', 'status']
        abstract = True

        widgets = {
            'us_registro': forms.TextInput(attrs={'readonly': 'readonly'}),
            'us_atualizacao': forms.TextInput(attrs={'readonly': 'readonly'}),
            'dt_registro': forms.TextInput(attrs={'readonly': 'readonly'}),
            'dt_atualizacao': forms.TextInput(attrs={'readonly': 'readonly'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        user = kwargs.pop('user', None)
        super(BaseModelPrescricaoForm, self).__init__(*args, **kwargs)
        self.instance.created_by = user

        if not self.instance.pk:
            self.fields['status'].widget.attrs['style'] = 'display:none;'


class InicioPlanoTerapeuticoForm(FilterByStatusMixin, forms.ModelForm):

    class Meta(BaseModelPrescricaoForm.Meta):
        model = InicioPlanoTerapeutico
        fields = '__all__'


class IntervaloHorasForm(FilterByStatusMixin, forms.ModelForm):

    class Meta(BaseModelPrescricaoForm.Meta):
        model = IntervaloHoras
        fields = '__all__'


class HorasRestritoPrescricaoForm(FilterByStatusMixin, forms.ModelForm):

    class Meta(BaseModelPrescricaoForm.Meta):
        model = HorarioRestritoPrescricao
        fields = '__all__'


class ParametrosPrescricaoForm(FilterByStatusMixin, forms.ModelForm):
    class Meta:
        model = ParametrosPrescricao
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            self.fields['status'].widget.attrs['style'] = 'display:none;'

    def clean(self):
        cleaned_data = super().clean()

        profissao = cleaned_data.get('profissao')
        profissional = cleaned_data.get('profissional')

        if not profissao and not profissional:
            raise forms.ValidationError(
                "Deve ser definida uma profissão ou usuário.",
                code='invalid',
            )
