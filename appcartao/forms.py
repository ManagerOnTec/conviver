from django import forms
from .models import CartaoPagamento, TransacaoCartao, FaturaCartao, PagamentoCartao


class CartaoPagamentoForm(forms.ModelForm):
    class Meta:
        model = CartaoPagamento
        fields = ['descricao', 'tipo', 'numero_cartao', 'bandeira', 'limite', 'dia_fechamento', 'dia_vencimento', 'status']
        widgets = {
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'numero_cartao': forms.TextInput(attrs={'class': 'form-control'}),
            'bandeira': forms.Select(attrs={'class': 'form-control'}),
            'limite': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'dia_fechamento': forms.NumberInput(attrs={'class': 'form-control'}),
            'dia_vencimento': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class TransacaoCartaoForm(forms.ModelForm):
    class Meta:
        model = TransacaoCartao
        fields = ['descricao', 'valor', 'data_transacao', 'categoria', 'fornecedor', 'numero_documento', 'nota_fiscal', 'status']
        widgets = {
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'data_transacao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'categoria': forms.TextInput(attrs={'class': 'form-control'}),
            'fornecedor': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_documento': forms.TextInput(attrs={'class': 'form-control'}),
            'nota_fiscal': forms.FileInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class FaturaCartaoForm(forms.ModelForm):
    class Meta:
        model = FaturaCartao
        fields = ['mes_referencia', 'data_fechamento', 'data_vencimento', 'valor_total', 'valor_pago', 'status']
        widgets = {
            'mes_referencia': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_fechamento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_vencimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'valor_total': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_pago': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class PagamentoCartaoForm(forms.ModelForm):
    class Meta:
        model = PagamentoCartao
        fields = ['valor_pagamento', 'data_pagamento', 'forma_pagamento', 'numero_documento', 'status']
        widgets = {
            'valor_pagamento': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'data_pagamento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'forma_pagamento': forms.Select(attrs={'class': 'form-control'}),
            'numero_documento': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
