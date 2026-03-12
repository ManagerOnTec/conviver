from django import forms
from .models import Caixa, SaldoCaixa, MovimentacaoCaixa
from django.forms import ModelForm


class CaixaForm(ModelForm):
    class Meta:
        model = Caixa
        fields = ['descricao', 'numero_caixa', 'responsavel', 'observacao', 'status']
        widgets = {
            'descricao': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descrição do caixa'
            }),
            'numero_caixa': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número do caixa'
            }),
            'responsavel': forms.Select(attrs={
                'class': 'form-control select2'
            }),
            'observacao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observações'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
        }


class SaldoCaixaForm(ModelForm):
    class Meta:
        model = SaldoCaixa
        fields = ['saldo_inicial', 'observacao']
        widgets = {
            'saldo_inicial': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Saldo inicial',
                'step': '0.01'
            }),
            'observacao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observações'
            }),
        }


class MovimentacaoCaixaForm(ModelForm):
    class Meta:
        model = MovimentacaoCaixa
        fields = [
            'tipo_movimentacao',
            'descricao',
            'valor',
            'data_movimentacao',
            'pagamento',
            'conta_bancaria',
            'numero_documento',
            'observacao'
        ]
        widgets = {
            'tipo_movimentacao': forms.Select(attrs={
                'class': 'form-control'
            }),
            'descricao': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descrição da movimentação'
            }),
            'valor': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Valor',
                'step': '0.01'
            }),
            'data_movimentacao': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'pagamento': forms.Select(attrs={
                'class': 'form-control select2'
            }),
            'conta_bancaria': forms.Select(attrs={
                'class': 'form-control select2'
            }),
            'numero_documento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número do documento'
            }),
            'observacao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observações'
            }),
        }
