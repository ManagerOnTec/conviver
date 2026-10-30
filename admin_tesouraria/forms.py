"""Forms da tesouraria."""
from django import forms

from admin_cadastros_financeiros.models import TransacaoFinanceira
from admin_financeiro.models import CompetenciaBancaria

from .models import MovimentoCaixa, CompetenciaCaixa


class MovimentoCaixaForm(forms.ModelForm):
    """Form do movimento de caixa.

    As validações de REGRA (tipo × valor × origem × transação) ficam no
    `clean()` do FORM: ali as FKs já vêm validadas pelo Django, e o erro pode
    ser escrito no campo certo (no `clean()` do modelo a instância ainda está
    parcialmente montada no `_post_clean`).
    """

    class Meta:
        model = MovimentoCaixa
        fields = '__all__'
        exclude = ['estabelecimento', 'transferencia_id']
        widgets = {
            'dt_movimento': forms.DateInput(attrs={'type': 'date'},
                                            format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Só competências de caixa ABERTAS.
        if 'competencia_caixa' in self.fields:
            self.fields['competencia_caixa'].queryset = \
                CompetenciaCaixa.objects.filter(
                    dt_fechamento__isnull=True, status='A')
        # Só transações que movimentam caixa (ou transferência).
        if 'transacao_financeira' in self.fields:
            self.fields['transacao_financeira'].queryset = \
                TransacaoFinanceira.objects.filter(
                    status='A', movimento__in=['caixa', 'deposito', 'saque'])
        # Transferência exige o banco de destino/origem.
        if 'competencia_bancaria' in self.fields:
            self.fields['competencia_bancaria'].queryset = \
                CompetenciaBancaria.objects.filter(
                    dt_fechamento_competencia__isnull=True, status='A')

    def clean(self):
        dados = super().clean()
        entrada = dados.get('valor_entrada') or 0
        saida = dados.get('valor_saida') or 0
        tipo = dados.get('tipo')
        origem = dados.get('origem')
        transacao = dados.get('transacao_financeira')
        competencia = dados.get('competencia_caixa')

        # Um valor só, positivo, e coerente com o tipo.
        #   E = Entrada, S = Saída, D = Depósito em Banco (também SAÍDA do
        #   caixa, com a ENTRADA lançada no banco).
        if (entrada > 0) == (saida > 0):
            self.add_error('valor_entrada',
                           'Informe APENAS um valor: entrada OU saída.')
        elif entrada > 0 and tipo not in ('E',):
            self.add_error('tipo',
                           'Valor de ENTRADA exige o tipo “Entrada”.')
        elif saida > 0 and tipo not in ('S', 'D'):
            self.add_error('tipo',
                           'Valor de SAÍDA exige o tipo “Saída” ou '
                           '“Depósito em Banco”.')
        if tipo == 'D' and origem != 'deposito_banco':
            self.add_error('origem',
                           'O tipo “Depósito em Banco” exige a origem '
                           '“Depósito em banco (caixa → banco)”.')

        # Competência aberta.
        if competencia is not None and competencia.dt_fechamento:
            self.add_error('competencia_caixa',
                           f'O caixa "{competencia}" está FECHADO: não aceita '
                           'lançamentos.')

        # Regras da TRANSFERÊNCIA (Depósito Bancário / Saque Bancário).
        movimento = getattr(transacao, 'movimento', '') if transacao else ''
        tipo_transacao = getattr(transacao, 'tipo', '') if transacao else ''
        if tipo_transacao in ('deposito_bancario', 'saque_bancario'):
            sentido = ('deposito' if tipo_transacao == 'deposito_bancario'
                       else 'saque')
            if movimento != sentido:
                self.add_error(
                    'transacao_financeira',
                    'A transação é de '
                    f'“{transacao.get_tipo_display()}” e o movimento dela é '
                    f'“{transacao.get_movimento_display()}” — os dois precisam '
                    'ser de transferência. Corrija o cadastro ou escolha outra '
                    'transação.')
            if tipo_transacao == 'saque_bancario':
                self.add_error(
                    'transacao_financeira',
                    'SAQUE BANCÁRIO é lançado no MOVIMENTO BANCÁRIO (o dinheiro '
                    'sai do banco): o sistema cria a entrada neste caixa '
                    'automaticamente.')
        if origem in ('deposito_banco', 'saque_banco'):
            banco = dados.get('competencia_bancaria')
            if banco is None:
                self.add_error('competencia_bancaria',
                               'Informe a COMPETÊNCIA BANCÁRIA '
                               'de destino/origem.')
            elif banco.dt_fechamento_competencia:
                self.add_error('competencia_bancaria',
                               f'A competência bancária "{banco.descricao}" '
                               'está FECHADA; escolha uma ABERTA.')
            permitidos = ('S', 'D') if origem == 'deposito_banco' else ('E',)
            if tipo and tipo not in permitidos:
                self.add_error(
                    'tipo',
                    'Depósito em banco é SAÍDA do caixa; saque do banco é '
                    'ENTRADA no caixa.')
            if movimento not in ('deposito', 'saque'):
                self.add_error(
                    'transacao_financeira',
                    'Para transferência escolha uma transação cadastrada como '
                    '“Depósito Bancário (Caixa → Banco)” ou '
                    '“Saque Bancário (Banco → Caixa)”.')
            elif movimento == 'deposito' and origem != 'deposito_banco':
                self.add_error('origem',
                               'A transação é de DEPÓSITO BANCÁRIO: selecione a '
                               'origem “Depósito em banco”.')
        return dados
