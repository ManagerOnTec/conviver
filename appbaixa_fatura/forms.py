from django import forms
from .models import BaixaFatura, BaixaPagamento, ProcessoBaixa, RelatorioBaixa


class BaixaFaturaForm(forms.ModelForm):
    class Meta:
        model = BaixaFatura
        fields = ['tipo_baixa', 'valor_baixa', 'data_baixa', 'numero_documento', 'descricao', 'status']
        widgets = {
            'tipo_baixa': forms.Select(attrs={'class': 'form-control'}),
            'valor_baixa': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'data_baixa': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'numero_documento': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class BaixaPagamentoForm(forms.ModelForm):
    class Meta:
        model = BaixaPagamento
        fields = ['tipo_baixa', 'valor_baixa', 'data_baixa', 'numero_documento', 'descricao', 'status']
        widgets = {
            'tipo_baixa': forms.Select(attrs={'class': 'form-control'}),
            'valor_baixa': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'data_baixa': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'numero_documento': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class ProcessoBaixaForm(forms.ModelForm):
    class Meta:
        model = ProcessoBaixa
        fields = ['tipo_processo', 'status', 'mensagem_erro']
        widgets = {
            'tipo_processo': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'mensagem_erro': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


class RelatorioBaixaForm(forms.ModelForm):
    class Meta:
        model = RelatorioBaixa
        fields = ['data_inicio', 'data_fim', 'status', 'observacao']
        widgets = {
            'data_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_fim': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
