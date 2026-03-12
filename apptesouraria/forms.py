from django import forms
from .models import Tesouraria, Caixa, SaldoCaixa, MovimentacaoCaixa


class TesourariaForm(forms.ModelForm):
    class Meta:
        model = Tesouraria
        fields = ['descricao', 'numero_tesouraria', 'status']
        widgets = {
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_tesouraria': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class CaixaForm(forms.ModelForm):
    class Meta:
        model = Caixa
        fields = ['descricao', 'numero_caixa', 'status']
        widgets = {
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_caixa': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class SaldoCaixaForm(forms.ModelForm):
    class Meta:
        model = SaldoCaixa
        fields = ['data_abertura', 'saldo_inicial', 'status']
        widgets = {
            'data_abertura': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'saldo_inicial': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class MovimentacaoCaixaForm(forms.ModelForm):
    class Meta:
        model = MovimentacaoCaixa
        fields = ['tipo', 'origem', 'descricao', 'valor', 'numero_documento', 'status']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'origem': forms.Select(attrs={'class': 'form-control'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'numero_documento': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
