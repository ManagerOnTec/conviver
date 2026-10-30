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
        dt_fechamento = cleaned_data.get('dt_fechamento_competencia')

        # Uma competência ABERTA por BANCO (controle bancário = conta): para
        # abrir uma nova é obrigatório FECHAR a anterior DESTE banco. Bancos
        # diferentes têm competências abertas independentes.
        if not dt_fechamento and controle_bancario is not None:
            abertas = CompetenciaBancaria.objects.filter(
                controle_bancario=controle_bancario,
                dt_fechamento_competencia__isnull=True,
            ).exclude(pk=self.instance.pk)
            if abertas.exists():
                aberta = abertas.first()
                raise ValidationError(
                    'Já existe a competência "%s" ABERTA para o banco %s. '
                    'Feche-a (com a conciliação finalizada) antes de abrir '
                    'uma nova competência para este mesmo banco.'
                    % (aberta.descricao, controle_bancario.conta))

        # Fechar pela tela exige a conciliação finalizada e sem divergência.
        if dt_fechamento and self.instance.pk:
            conc = getattr(self.instance, 'conciliacao', None)
            pendente = conc is None or not conc.finalizada \
                or abs(conc.divergencia or 0) >= 0.01
            if pendente:
                raise ValidationError(
                    'Para fechar a competência é necessário finalizar a '
                    'CONCILIAÇÃO BANCÁRIA (importar o extrato e conciliar) '
                    'sem divergência de saldo. Use o menu '
                    '“4. Conciliação Bancária”.')

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

        # Competência FECHADA não aceita lançamento nem alteração.
        if competencia_bancaria.dt_fechamento_competencia:
            raise forms.ValidationError(
                f'A competência “{competencia_bancaria.descricao}” está '
                f'FECHADA em '
                f'{competencia_bancaria.dt_fechamento_competencia:%d/%m/%Y}: '
                'não é possível lançar nem alterar movimentos dela. Abra uma '
                'nova competência para o banco.')

        # Verifica o tipo da transação financeira.
        #
        # `tipo_lancamento` traduz os TIPOS DE TRANSFERÊNCIA para o lado que se
        # digita no banco:
        #   • Saque Bancário  → SAÍDA no banco (o caixa recebe a entrada);
        #   • Depósito Bancário lançado no banco → ENTRADA no banco.
        # Sem isso, as transferências caíam em “tipo inválido”.
        if not transacao_financeira:
            raise forms.ValidationError('Transação financeira é obrigatória.')

        # O DEPÓSITO BANCÁRIO lançado no BANCO é ENTRADA (o dinheiro sai do
        # caixa). O SAQUE BANCÁRIO é SAÍDA. Os tipos simples seguem o próprio
        # `tipo`.
        tipo_lancamento = transacao_financeira.tipo
        if (tipo_lancamento == 'deposito_bancario'
                and getattr(transacao_financeira, 'movimento', '') == 'deposito'):
            tipo_lancamento = 'entrada'
        elif tipo_lancamento == 'saque_bancario':
            tipo_lancamento = 'saida'
        if tipo_lancamento == 'entrada':
            if not valor_entrada or valor_entrada <= 0:
                raise forms.ValidationError(
                    'Para esta transação (entrada), o valor de entrada deve ser '
                    'maior que 0.')
            if valor_saida and valor_saida > 0:
                raise forms.ValidationError(
                    'Para esta transação (entrada), o valor de saída deve '
                    'ficar vazio.')
        elif tipo_lancamento == 'saida':
            if not valor_saida or valor_saida <= 0:
                raise forms.ValidationError(
                    'Para esta transação (saída), o valor de saída deve ser '
                    'maior que 0.')
            if valor_entrada and valor_entrada > 0:
                raise forms.ValidationError(
                    'Para esta transação (saída), o valor de entrada deve '
                    'ficar vazio.')
        else:
            raise forms.ValidationError(
                f'A transação “{transacao_financeira}” não movimenta valor '
                '(tipo “Não Movimenta”): escolha uma transação de entrada, '
                'saída, depósito ou saque.')

        return cleaned_data
