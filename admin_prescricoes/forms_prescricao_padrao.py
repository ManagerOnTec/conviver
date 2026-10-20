"""
Forms/formsets de PRESCRIÇÃO PADRÃO (app admin_prescricoes).

Usados exclusivamente pelo admin (`admin_prescricao_padrao.py`) e pelo modal de
inserção no cadastro de prescrição (`views_prescricao_padrao.py`).
"""
from django import forms
from django.forms import inlineformset_factory

from admin_estoques.models import Produto
from dominios.utils import FilterByStatusMixin

from .models import InicioPlanoTerapeutico, IntervaloHoras
from .models_prescricao_padrao import PrescricaoPadrao, ProdutoPrescricaoPadrao


def produtos_prescritiveis_queryset():
    """Mesmo critério de ProdutoPrescricaoForm: produto OU grupo pode ser prescrito."""
    return Produto.objects.filter(
        pode_ser_prescrito=True, status='A'
    ) | Produto.objects.filter(
        grupo__pode_ser_prescrito=True, status='A')


class PrescricaoPadraoForm(FilterByStatusMixin, forms.ModelForm):
    class Meta:
        model = PrescricaoPadrao
        fields = '__all__'
        widgets = {
            'observacao': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['status'].widget.attrs['style'] = 'display:none;'

    def clean(self):
        cleaned_data = super().clean()
        profissional = cleaned_data.get('profissional')
        profissao = cleaned_data.get('profissao')
        if not profissional and not profissao:
            # Liberado para todos os profissionais com parâmetro de prescrição
            # (informado apenas como aviso na UI do admin).
            pass
        return cleaned_data


class ProdutoPrescricaoPadraoForm(FilterByStatusMixin, forms.ModelForm):
    """Item do modelo de prescrição.

    `prescricao_padrao` é obrigatório no cadastro avulso (admin → Produto da
    Prescrição Padrão). No inline de `PrescricaoPadrao` o vínculo vem do objeto
    pai, por isso a subclasse do inline define `inline_parent = True` e o campo
    é ocultado.
    """

    inline_parent = False

    class Meta:
        model = ProdutoPrescricaoPadrao
        fields = [
            'prescricao_padrao',
            'produto',
            'intervalo_horas',
            'hora_inicio_produto',
            'se_necessario',
            'dose_unica',
            'observacao',
            'ordem',
            'status',
        ]
        widgets = {
            'status': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.inline_parent:
            self.fields.pop('prescricao_padrao', None)
        else:
            self.fields['prescricao_padrao'].required = True
            self.fields['prescricao_padrao'].queryset = PrescricaoPadrao.objects.filter(
                status='A').order_by('descricao')
        self.fields['produto'].queryset = produtos_prescritiveis_queryset()
        # Valores padrão iguais aos do cadastro de prescrição, para facilitar a montagem.
        if not self.instance.pk:
            default_intervalo = IntervaloHoras.objects.filter(
                padrao=True, status='A').first()
            if default_intervalo:
                self.fields['intervalo_horas'].initial = default_intervalo
            default_inicio = InicioPlanoTerapeutico.objects.filter(
                padrao=True, status='A').first()
            if default_inicio:
                self.fields['hora_inicio_produto'].initial = default_inicio


ProdutoPrescricaoPadraoFormSet = inlineformset_factory(
    PrescricaoPadrao,
    ProdutoPrescricaoPadrao,
    form=ProdutoPrescricaoPadraoForm,
    fields=('produto', 'intervalo_horas', 'hora_inicio_produto',
            'se_necessario', 'dose_unica', 'observacao', 'ordem'),
    extra=1,
    can_delete=True,
)
