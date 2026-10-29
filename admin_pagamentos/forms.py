from .models import BaixaPagamento, ClassificacaoFornecedor, Fornecedor, ClassificacaoPagamento, Pagamento
from admin_financeiro.models import MovimentoBancario, CompetenciaBancaria
from django.core.exceptions import ValidationError
from admin_cadastros_financeiros.models import TransacaoFinanceira
from django import forms


class ClassificacaoFornecedorForm(forms.ModelForm):
    class Meta:
        model = ClassificacaoFornecedor
        fields = '__all__'

    def clean_descricao(self):
        descricao = self.cleaned_data.get('descricao')
        if descricao:
            # Converte a descrição para o formato title case
            return descricao.title()
        return descricao

    def clean_observacao(self):
        observacao = self.cleaned_data.get('observacao')
        if observacao:
            # Converte a descrição para o formato title case
            return observacao.title()
        return observacao




class ClassificacaoPagamentoForm(forms.ModelForm):
    class Meta:
        model = ClassificacaoPagamento
        fields = '__all__'

    def clean_descricao(self):
        descricao = self.cleaned_data.get('descricao')
        if descricao:
            # Converte a descrição para o formato title case
            return descricao.title()
        return descricao

    def clean_observacao(self):
        observacao = self.cleaned_data.get('observacao')
        if observacao:
            # Converte a descrição para o formato title case
            return observacao.title()
        return observacao



class FornecedorForm(forms.ModelForm):
    class Meta:
        model = Fornecedor
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        empresa = cleaned_data.get('empresa')
        pessoa = cleaned_data.get('pessoa')

        # Verifica se ambos os campos estão vazios
        if not empresa and not pessoa:
            raise forms.ValidationError(
                'Preencha: Pessoa Jurídica ou Pessoa Física.'
            )

        # Verifica se ambos os campos estão preenchidos
        if empresa and pessoa:
            raise forms.ValidationError(
                'Preencha apenas um: Pessoa Jurídica ou Pessoa Física.'
            )

        # Retorna os dados limpos
        return cleaned_data

    def clean_descricao(self):
        descricao = self.cleaned_data.get('descricao')
        if descricao:
            # Converte a descrição para o formato title case
            return descricao.title()
        return descricao


class BaixaPagamentoForm(forms.ModelForm):
    class Meta:
        model = BaixaPagamento
        fields = '__all__'
        exclude = ['estabelecimento']  # Remover o campo estabelecimento do formulário

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Competência de CAIXA: só caixas ABERTOS. Competência bancária: só
        # bancos abertos (mesmo recorte do módulo financeiro).
        try:
            from admin_tesouraria.models import CompetenciaCaixa
            if 'competencia_caixa' in self.fields:
                self.fields['competencia_caixa'].queryset = \
                    CompetenciaCaixa.objects.filter(
                        dt_fechamento__isnull=True, status='A')
        except Exception:
            pass
        try:
            from admin_financeiro.models import CompetenciaBancaria
            if 'competencia_bancaria' in self.fields:
                self.fields['competencia_bancaria'].queryset = \
                    CompetenciaBancaria.objects.filter(
                        dt_fechamento_competencia__isnull=True, status='A')
        except Exception:
            pass

    def clean(self):
        cleaned_data = super().clean()
        pagamento = cleaned_data.get('pagamento')
        transacao_financeira = cleaned_data.get('transacao_financeira')
        competencia_bancaria = cleaned_data.get('competencia_bancaria')
        competencia_caixa = cleaned_data.get('competencia_caixa')
        dt_pagamento = cleaned_data.get('dt_pagamento')


        # Verifica se a fatura está presente
        if pagamento:
            # Atribui o estabelecimento da fatura ao campo estabelecimentos
            cleaned_data['estabelecimento'] = pagamento.estabelecimento
        else:
            raise forms.ValidationError('Pagamento é obrigatório.')

        # Transação por BANCO exige competência bancária ABERTA.
        if transacao_financeira and transacao_financeira.movimento == 'banco':
            if not competencia_bancaria:
                self.add_error('competencia_bancaria',
                               'O campo "Competência Bancária" é obrigatório '
                               'para transações do tipo "banco".')
            elif competencia_bancaria.dt_fechamento_competencia:
                self.add_error(
                    'competencia_bancaria',
                    f'A competência bancária "{competencia_bancaria.descricao}" '
                    'está FECHADA: escolha uma aberta.')
            if competencia_caixa:
                self.add_error(
                    'competencia_caixa',
                    'Pagamento por BANCO não usa competência de caixa '
                    '(limpe o campo).')

        # Transação por CAIXA exige competência de CAIXA aberta.
        if transacao_financeira and transacao_financeira.movimento == 'caixa':
            if not competencia_caixa:
                self.add_error(
                    'competencia_caixa',
                    'Pagamento em DINHEIRO: informe a COMPETÊNCIA DE CAIXA '
                    '(caixa aberto).')
            elif competencia_caixa.dt_fechamento:
                self.add_error(
                    'competencia_caixa',
                    f'O caixa "{competencia_caixa}" está FECHADO: abra/use '
                    'outro caixa.')
            elif dt_pagamento and not competencia_caixa.validar_periodo(
                    dt_pagamento):
                self.add_error(
                    'dt_pagamento',
                    'A data do pagamento está fora do período da competência '
                    'de caixa.')
            if competencia_bancaria:
                self.add_error(
                    'competencia_bancaria',
                    'Pagamento em CAIXA não usa competência bancária '
                    '(limpe o campo).')

        # Validação: dt_pagamento deve ser igual ou maior que a abertura.
        if dt_pagamento and competencia_bancaria:
            if dt_pagamento < competencia_bancaria.dt_abertura_competencia:
                self.add_error('dt_pagamento', 'A data de pagamento deve ser igual ou posterior à data de abertura da competência bancária.')

        return cleaned_data