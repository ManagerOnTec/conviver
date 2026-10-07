from django import forms
from django.core.exceptions import ValidationError
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

    def clean(self):
        cleaned_data = super().clean()
        data_inicio = cleaned_data.get('data_inicio')
        data_fim = cleaned_data.get('data_fim')
        if data_inicio and data_fim and data_inicio > data_fim:
            raise ValidationError('A data inicial nao pode ser maior que a data final.')
        return cleaned_data


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

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo_transacao')
        fatura = cleaned_data.get('fatura')
        pagamento = cleaned_data.get('pagamento')

        if tipo == 'FATURA' and not fatura:
            self.add_error('fatura', 'Informe a fatura para conciliar este lancamento.')

        if tipo == 'PAGAMENTO' and not pagamento:
            self.add_error('pagamento', 'Informe o pagamento para conciliar este lancamento.')

        if tipo == 'MOVIMENTACAO_CAIXA' and (fatura or pagamento):
            raise ValidationError('Para MOVIMENTACAO_CAIXA nao informe fatura ou pagamento.')

        return cleaned_data


class RelatorioConciliacaoForm(forms.ModelForm):
    class Meta:
        model = RelatorioConciliacao
        fields = ['data_inicio', 'data_fim', 'status']
        widgets = {
            'data_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_fim': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        data_inicio = cleaned_data.get('data_inicio')
        data_fim = cleaned_data.get('data_fim')
        if data_inicio and data_fim and data_inicio > data_fim:
            raise ValidationError('A data inicial nao pode ser maior que a data final.')
        return cleaned_data
