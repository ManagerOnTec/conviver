from django import forms
from django.core.exceptions import ValidationError
from .models import ExtratoBancario, TransacaoExtrato, Conciliacao, DivergenciaConciliacao
from admin_financeiro.models import CompetenciaBancaria
from admin_cadastros_financeiros.models import Conta
import csv
from io import TextIOWrapper
from datetime import datetime
from decimal import Decimal


class ExtratoBancarioForm(forms.ModelForm):
    """
    Formulário para upload e criação de extratos bancários.
    """
    
    class Meta:
        model = ExtratoBancario
        fields = [
            'competencia_bancaria',
            'conta',
            'tipo_arquivo',
            'arquivo',
            'data_extrato_inicio',
            'data_extrato_fim',
            'saldo_inicial',
            'saldo_final',
            'observacao',
        ]
        widgets = {
            'competencia_bancaria': forms.Select(attrs={
                'class': 'form-control',
            }),
            'conta': forms.Select(attrs={
                'class': 'form-control',
            }),
            'tipo_arquivo': forms.Select(attrs={
                'class': 'form-control',
            }),
            'arquivo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.csv,.ofx,.txt',
            }),
            'data_extrato_inicio': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'data_extrato_fim': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'saldo_inicial': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
            }),
            'saldo_final': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
            }),
            'observacao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        data_inicio = cleaned_data.get('data_extrato_inicio')
        data_fim = cleaned_data.get('data_extrato_fim')
        
        if data_inicio and data_fim:
            if data_inicio > data_fim:
                raise ValidationError(
                    'A data de início não pode ser posterior à data de fim.'
                )
        
        return cleaned_data


class TransacaoExtratoForm(forms.ModelForm):
    """
    Formulário para criação manual de transações do extrato.
    """
    
    class Meta:
        model = TransacaoExtrato
        fields = [
            'extrato_bancario',
            'data_transacao',
            'data_lancamento',
            'descricao',
            'tipo_transacao',
            'valor',
            'numero_documento',
            'referencia_banco',
            'observacao',
        ]
        widgets = {
            'extrato_bancario': forms.Select(attrs={
                'class': 'form-control',
            }),
            'data_transacao': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'data_lancamento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'descricao': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descrição da transação',
            }),
            'tipo_transacao': forms.Select(attrs={
                'class': 'form-control',
            }),
            'valor': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
            }),
            'numero_documento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número do documento',
            }),
            'referencia_banco': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Referência do banco',
            }),
            'observacao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
        }


class ConciliacaoForm(forms.ModelForm):
    """
    Formulário para conciliação de transações.
    """
    
    class Meta:
        model = Conciliacao
        fields = [
            'transacao_extrato',
            'movimento_bancario',
            'competencia_bancaria',
            'valor_conciliado',
            'status',
            'motivo_divergencia',
            'observacao',
        ]
        widgets = {
            'transacao_extrato': forms.Select(attrs={
                'class': 'form-control',
            }),
            'movimento_bancario': forms.Select(attrs={
                'class': 'form-control',
            }),
            'competencia_bancaria': forms.Select(attrs={
                'class': 'form-control',
            }),
            'valor_conciliado': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
            }),
            'status': forms.Select(attrs={
                'class': 'form-control',
            }),
            'motivo_divergencia': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
            'observacao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
        }


class DivergenciaConciliacaoForm(forms.ModelForm):
    """
    Formulário para registrar divergências na conciliação.
    """
    
    class Meta:
        model = DivergenciaConciliacao
        fields = [
            'conciliacao',
            'tipo_divergencia',
            'descricao',
            'prioridade',
            'resolvida',
            'solucao',
        ]
        widgets = {
            'conciliacao': forms.Select(attrs={
                'class': 'form-control',
            }),
            'tipo_divergencia': forms.Select(attrs={
                'class': 'form-control',
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
            }),
            'prioridade': forms.Select(attrs={
                'class': 'form-control',
            }),
            'resolvida': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'solucao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
            }),
        }


class ImportarExtratoCSVForm(forms.Form):
    """
    Formulário para importar transações de um arquivo CSV.
    """
    
    arquivo_csv = forms.FileField(
        label='Arquivo CSV',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv',
        })
    )
    
    def clean_arquivo_csv(self):
        arquivo = self.cleaned_data.get('arquivo_csv')
        
        if arquivo:
            if not arquivo.name.endswith('.csv'):
                raise ValidationError('O arquivo deve ser um CSV.')
            
            # Validar o conteúdo do arquivo
            try:
                arquivo.seek(0)
                wrapper = TextIOWrapper(arquivo.file, encoding='utf-8')
                reader = csv.reader(wrapper)
                linhas = list(reader)
                
                if len(linhas) < 2:
                    raise ValidationError('O arquivo CSV deve conter pelo menos uma linha de dados.')
                
                arquivo.seek(0)
            except Exception as e:
                raise ValidationError(f'Erro ao ler o arquivo CSV: {str(e)}')
        
        return arquivo


class FiltrosConciliacaoForm(forms.Form):
    """
    Formulário para filtrar transações na tela de conciliação.
    """
    
    competencia_bancaria = forms.ModelChoiceField(
        queryset=CompetenciaBancaria.objects.all(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Competência Bancária'
    )
    
    conta = forms.ModelChoiceField(
        queryset=Conta.objects.all(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Conta Bancária'
    )
    
    data_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        }),
        label='Data Início'
    )
    
    data_fim = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        }),
        label='Data Fim'
    )
    
    valor_minimo = forms.DecimalField(
        required=False,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
        }),
        label='Valor Mínimo'
    )
    
    valor_maximo = forms.DecimalField(
        required=False,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
        }),
        label='Valor Máximo'
    )
    
    status_conciliacao = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Todos'),
            ('P', 'Pendente'),
            ('C', 'Conciliado'),
            ('D', 'Divergente'),
            ('A', 'Anulado'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Status da Conciliação'
    )
    
    descricao = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por descrição',
        }),
        label='Descrição'
    )
