from django import forms
from .models import ExtratoBancario, LancamentoBancario, Conciliacao, RelatorioConciliacao


class ExtratoBancarioForm(forms.ModelForm):
    class Meta:
        model = ExtratoBancario
        fields = ['numero_banco', 'numero_agencia', 'numero_conta', 'data_inicio', 'data_fim', 
                  'saldo_inicial', 'saldo_final', 'tipo_arquivo', 'arquivo', 'status']
        widgets = {
            'numero_banco': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_agencia': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_conta': forms.TextInput(attrs={'class': 'form-control'}),
            'data_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_fim': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'saldo_inicial': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'saldo_final': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tipo_arquivo': forms.Select(attrs={'class': 'form-control'}),
            'arquivo': forms.FileInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class LancamentoBancarioForm(forms.ModelForm):
    class Meta:
        model = LancamentoBancario
        fields = ['data_lancamento', 'tipo', 'valor', 'descricao', 'numero_documento']
        widgets = {
            'data_lancamento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_documento': forms.TextInput(attrs={'class': 'form-control'}),
        }


class ConciliacaoForm(forms.ModelForm):
    class Meta:
        model = Conciliacao
        fields = ['tipo_transacao', 'fatura', 'pagamento', 'status', 'observacao']
        widgets = {
            'tipo_transacao': forms.Select(attrs={'class': 'form-control'}),
            'fatura': forms.Select(attrs={'class': 'form-control'}),
            'pagamento': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


class RelatorioConciliacaoForm(forms.ModelForm):
    class Meta:
        model = RelatorioConciliacao
        fields = ['data_inicio', 'data_fim', 'status']
        widgets = {
            'data_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_fim': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
