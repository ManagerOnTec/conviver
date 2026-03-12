from django import forms
from django.core.exceptions import ValidationError
from .models import TransacaoFinanceira


class TransacaoFinanceiraForm(forms.ModelForm):
    class Meta:
        model = TransacaoFinanceira
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        movimento = cleaned_data.get('movimento')
        conta = cleaned_data.get('conta')
        caixa = cleaned_data.get('caixa')

        # Verificação para movimentos de banco
        if movimento == 'banco' and not conta:
            raise ValidationError(
                'Conta bancária é obrigatória para transações que movimentam banco.')

        # Verificação para movimentos de caixa
        if movimento == 'caixa' and not caixa:
            raise ValidationError(
                'Caixa é obrigatório para transações que movimentam caixa.')

        return cleaned_data
