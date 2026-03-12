from django import forms
from .models_cartao import CartaoPagamento, TransacaoCartao, FaturaCartao, PagamentoCartao


class CartaoPagamentoForm(forms.ModelForm):
    class Meta:
        model = CartaoPagamento
        fields = [
            'descricao',
            'tipo',
            'numero_cartao',
            'bandeira',
            'conta_bancaria',
            'limite',
            'dia_fechamento',
            'dia_vencimento',
            'observacao',
        ]
        widgets = {
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'numero_cartao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Últimos 4 dígitos'}),
            'bandeira': forms.TextInput(attrs={'class': 'form-control'}),
            'conta_bancaria': forms.Select(attrs={'class': 'form-control'}),
            'limite': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'dia_fechamento': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '31'}),
            'dia_vencimento': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '31'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class TransacaoCartaoForm(forms.ModelForm):
    class Meta:
        model = TransacaoCartao
        fields = [
            'descricao',
            'valor',
            'data_transacao',
            'categoria',
            'fornecedor',
            'numero_documento',
            'nota_fiscal',
            'observacao',
        ]
        widgets = {
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'data_transacao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'categoria': forms.TextInput(attrs={'class': 'form-control'}),
            'fornecedor': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_documento': forms.TextInput(attrs={'class': 'form-control'}),
            'nota_fiscal': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png,.peg'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class FaturaCartaoForm(forms.ModelForm):
    class Meta:
        model = FaturaCartao
        fields = [
            'mes_referencia',
            'data_fechamento',
            'data_vencimento',
            'valor_total',
            'observacao',
        ]
        widgets = {
            'mes_referencia': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_fechamento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_vencimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'valor_total': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class PagamentoCartaoForm(forms.ModelForm):
    class Meta:
        model = PagamentoCartao
        fields = [
            'valor_pagamento',
            'data_pagamento',
            'forma_pagamento',
            'numero_documento',
            'observacao',
        ]
        widgets = {
            'valor_pagamento': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'data_pagamento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'forma_pagamento': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_documento': forms.TextInput(attrs={'class': 'form-control'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
