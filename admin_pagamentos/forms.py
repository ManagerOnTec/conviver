from .models import BaixaPagamento, ClassificacaoFornecedor, Fornecedor, ClassificacaoPagamento, Pagamento
from admin_financeiro.models import MovimentoBancario, CompetenciaBancaria
from apptesouraria.models import SaldoCaixa
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

    def clean(self):
        cleaned_data = super().clean()
        pagamento = cleaned_data.get('pagamento')
        transacao_financeira = cleaned_data.get('transacao_financeira')
        competencia_bancaria = cleaned_data.get('competencia_bancaria')
        dt_pagamento = cleaned_data.get('dt_pagamento')


        # Verifica se a fatura está presente
        if pagamento:
            # Atribui o estabelecimento da fatura ao campo estabelecimentos
            cleaned_data['estabelecimento'] = pagamento.estabelecimento
        else:
            raise forms.ValidationError('Pagamento é obrigatório.')

        # Verifica se a transação financeira é do tipo 'entrada' e de movimento 'banco'
        if transacao_financeira and transacao_financeira.movimento == 'banco':
            if not competencia_bancaria:
                # Adiciona um erro ao campo 'competencia_bancaria'
                self.add_error('competencia_bancaria', 'O campo "Competência Bancária" é obrigatório para transações do tipo "banco".')

         # Validação: dt_recebimento deve ser igual ou maior que dt_abertura_competencia
        if dt_pagamento and competencia_bancaria:
            if dt_pagamento < competencia_bancaria.dt_abertura_competencia:
                self.add_error('dt_pagamento', 'A data de pagamento deve ser igual ou posterior à data de abertura da competência bancária.')

        return cleaned_data