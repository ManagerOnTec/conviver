"""Forms da tesouraria."""
from django import forms

from admin_cadastros_financeiros.models import TransacaoFinanceira
from admin_financeiro.models import CompetenciaBancaria

from .models import MovimentoCaixa, CompetenciaCaixa

ORIGENS_COM_BAIXA_FATURA = ('recebimento', 'ajuste')


class MovimentoCaixaForm(forms.ModelForm):
    """Form do movimento de caixa.

    As validações de REGRA (tipo × valor × origem × transação) ficam no
    `clean()` do FORM: ali as FKs já vêm validadas pelo Django, e o erro pode
    ser escrito no campo certo (no `clean()` do modelo a instância ainda está
    parcialmente montada no `_post_clean`).
    """

    # BAIXA DE FATURA (recebimento em dinheiro): o usuário escolhe a FATURA
    # (com saldo); o sistema cria a `BaixaFatura` concomitante ao movimento —
    # espelho da baixa de pagamento em caixa, só que para ENTRADA.
    fatura_receber = forms.ModelChoiceField(
        queryset=None, required=False, label='Fatura a receber (baixa)',
        help_text='Opcional: origem “Recebimento avulso” ou “Ajuste/estorno” '
                  'com ENTRADA de dinheiro. O valor da entrada baixa o saldo '
                  'desta fatura.')

    class Meta:
        model = MovimentoCaixa
        fields = '__all__'
        exclude = ['estabelecimento', 'transferencia_id', 'baixa_fatura']
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
        # BAIXA DE FATURA: só faturas ATIVAS COM SALDO (o valor da entrada
        # abate o saldo; a baixa pode, no máximo, zerá-lo).
        if 'fatura_receber' in self.fields:
            from admin_faturas.models import Fatura
            self.fields['fatura_receber'].queryset = Fatura.objects.filter(
                status='A', valor_saldo__gt=0).order_by('-pk')

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

        # BAIXA DE FATURA: só ENTRADA, nas origens de recebimento/ajuste.
        fatura_receber = dados.get('fatura_receber')
        if fatura_receber is not None:
            if entrada <= 0 or tipo != 'E':
                self.add_error(
                    'fatura_receber',
                    'A baixa de fatura vale para ENTRADA de dinheiro: informe '
                    'o VALOR DE ENTRADA e o tipo “Entrada”.')
            elif origem not in ORIGENS_COM_BAIXA_FATURA:
                self.add_error(
                    'fatura_receber',
                    'A baixa de fatura só vale para a origem “Recebimento '
                    'avulso” ou “Ajuste/estorno”.')
            else:
                saldo = (fatura_receber.valor_saldo or 0)
                if entrada > saldo:
                    self.add_error(
                        'valor_entrada',
                        f'O valor da entrada (R$ {entrada}) é maior que o '
                        f'saldo da fatura {fatura_receber.pk} (R$ {saldo}). '
                        'A baixa pode, no máximo, zerar o saldo.')

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

    def save(self, commit=True):
        """Grava o movimento e a BAIXA DE FATURA concomitante.

        Com `fatura_receber` preenchida, cria a `BaixaFatura` nova (sem
        gravar): ela segue para `MovimentoCaixa.save()` como `baixa_fatura`,
        e o helper `_registrar_baixa_fatura_do_caixa` a grava DEPOIS que o
        movimento tem pk — abatendo o saldo da fatura (concomitância igual à
        da baixa de pagamento em caixa).
        """
        movimento = super().save(commit=False)
        fatura = self.cleaned_data.get('fatura_receber')
        if fatura is not None:
            from admin_faturas.models import BaixaFatura
            nova_baixa = BaixaFatura(
                fatura_baixada=[fatura],
                valor_baixa=movimento.valor_entrada or 0,
                dt_recebimento=movimento.dt_movimento,
                transacao_financeira_id=movimento.transacao_financeira_id,
                competencia_bancaria=None,
            )
            # A baixa fica PENDENTE (sem pk): o save() do modelo a registra
            # DEPOIS que o movimento tem pk (concomitância com o movimento).
            object.__setattr__(movimento, '_baixa_fatura_pendente', nova_baixa)
        if commit:
            movimento.save()
        return movimento
