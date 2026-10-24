from django import forms
from .models import TransacaoFinanceira
class TransacaoFinanceiraForm(forms.ModelForm):
    class Meta:
        model = TransacaoFinanceira
        fields = '__all__'
