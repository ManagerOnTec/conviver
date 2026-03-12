from django import forms
from django.core.exceptions import ValidationError
from .models import CompetenciaBancaria, MovimentoBancario

class CompetenciaBancariaForm(forms.ModelForm):
    class Meta:
        model = CompetenciaBancaria        
        fields = '__all__'
 
    def clean(self):
        cleaned_data = super().clean()
        controle_bancario = cleaned_data.get('controle_bancario')
        dt_fechamento_competencia = cleaned_data.get('dt_fechamento_competencia')

        # Verifica se está tentando abrir um novo saldo sem uma data de fechamento
        if not dt_fechamento_competencia:
            competencia_bancaria = CompetenciaBancaria.objects.filter(
                controle_bancario=controle_bancario,
                dt_fechamento_competencia__isnull=True
            ).exclude(pk=self.instance.pk)  # Excluir o saldo atual no caso de edição

            if competencia_bancaria.exists():
                raise ValidationError(
                    'Já existe uma competência aberta para este controle bancário. Feche a competência antes de abrir uma nova.'
                )

        return cleaned_data



class MovimentoBancarioForm(forms.ModelForm):
    class Meta:
        model = MovimentoBancario
        fields = '__all__'
        exclude = ['estabelecimento',]


class MovimentoBancarioForm(forms.ModelForm):
    class Meta:
        model = MovimentoBancario
        fields = '__all__'
        exclude = ['estabelecimento',]

    def clean(self):
        cleaned_data = super().clean()       
        transacao_financeira = cleaned_data.get('transacao_financeira')
        valor_entrada = cleaned_data.get('valor_entrada')
        valor_saida = cleaned_data.get('valor_saida')
        competencia_bancaria = cleaned_data.get('competencia_bancaria')


        if not competencia_bancaria:          
            raise forms.ValidationError('Competência bancária é obrigatória.')

        # Verifica o tipo da transação financeira
        if transacao_financeira:
            if transacao_financeira.tipo == 'entrada':
                # Obriga o valor de entrada e valida valor de saída como 0
                if not valor_entrada or valor_entrada <= 0:
                    raise forms.ValidationError('Para transações de entrada, o valor de entrada deve ser maior que 0.')
                if valor_saida and valor_saida > 0:
                    raise forms.ValidationError('Para transações de entrada, o valor de saída deve ser 0.')
            elif transacao_financeira.tipo == 'saida':
                # Obriga o valor de saída e valida valor de entrada como 0
                if not valor_saida or valor_saida <= 0:
                    raise forms.ValidationError('Para transações de saída, o valor de saída deve ser maior que 0.')
                if valor_entrada and valor_entrada > 0:
                    raise forms.ValidationError('Para transações de saída, o valor de entrada deve ser 0.')
            else:
                raise forms.ValidationError('Tipo de transação financeira inválido.')
        else:
            raise forms.ValidationError('Transação financeira é obrigatória.')

        return cleaned_data
