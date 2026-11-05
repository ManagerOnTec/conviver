from .models import BaixaPagamento, ClassificacaoFornecedor, Fornecedor, ClassePagamento, Pagamento
from admin_cadastros.models import Empresa
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




class ClassePagamentoForm(forms.ModelForm):
    class Meta:
        model = ClassePagamento
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Só empresas do TIPO FORNECEDOR podem virar fornecedor (a mesma
        # tabela Empresa atende convênio e estabelecimento). O registro já
        # salvo é preservado para não invalidar a edição.
        if 'empresa' in self.fields:
            from django.db.models import Q
            atual = self.instance.empresa_id if self.instance.pk else None
            self.fields['empresa'].queryset = Empresa.objects.filter(
                Q(tipo='fornecedor', status='A') | Q(pk=atual)
            )

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
        # DATA como `type="date"` (calendário do navegador) — sem widget o
        # Django renderiza `<input type="text">` e o usuário digita o texto.
        widgets = {
            'dt_pagamento': forms.DateInput(
                format='%Y-%m-%d', attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        # O MODAL passa o pagamento da URL: a instância já nasce ligada a ele.
        self.pagamento_fixo = kwargs.pop('pagamento', None)
        super().__init__(*args, **kwargs)
        if self.pagamento_fixo is not None:
            if 'pagamento' in self.fields:
                self.fields['pagamento'].required = False
            self.instance.pagamento = self.pagamento_fixo
            self.instance.estabelecimento = self.pagamento_fixo.estabelecimento
        # AUDITORIA e controle são preenchidos pelo admin, não pelo usuário:
        # sem tirar do form eles aparecem como OBRIGATÓRIOS na validação
        # (e o POST do modal não os enviava, derrubando o lançamento).
        for nome in ('us_registro', 'us_atualizacao', 'dt_registro',
                     'dt_atualizacao', 'status', 'pagamento_baixado'):
            if nome in self.fields:
                self.fields[nome].required = False
        # O `format='%Y-%m-%d'` do widget só vale para exibição se o campo
        # aceitar a entrada nesse formato (o `type=date` do HTML manda ISO).
        campo_data = self.fields.get('dt_pagamento')
        if campo_data is not None:
            campo_data.input_formats = ['%Y-%m-%d', '%d/%m/%Y']
            campo_data.widget.format = '%Y-%m-%d'
            # Garante o calendário do navegador (`type="date"`): o `Meta`
            # define o widget, mas o input precisa do attr explícito.
            campo_data.widget.input_type = 'date'
        # TRANSAÇÃO: pagamento é sempre SAÍDA (banco ou caixa). A própria
        # transação escolhida define o lado: uma transação de ENTRADA é de
        # fatura (recebimento), não de pagamento.
        campo_transacao = self.fields.get('transacao_financeira')
        if campo_transacao is not None:
            try:
                from admin_cadastros_financeiros.models import \
                    TransacaoFinanceira
                # Pagamento é SAÍDA (banco/caixa). Transferências (Depósito/
                # Saque Bancário) não são forma de pagamento — ficam fora.
                campo_transacao.queryset = \
                    campo_transacao.queryset.filter(
                        tipo='saida', status='A',
                        movimento__in=['banco', 'caixa'])
            except Exception:
                pass  # nunca derruba o form por causa do recorte

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

    def _post_clean(self):
        """Aceita o form SEM o campo `pagamento`.

        O `pagamento` vem da URL do modal (a view injeta `obj.pagamento`).
        O `_post_clean` do ModelForm roda `full_clean` no MODELO e devolve
        "Pagamento é obrigatório." quando o campo não está no POST — por isso
        ele é excluído da validação do modelo apenas quando não veio dado.
        """
        if not self.cleaned_data.get('pagamento'):
            excluir = tuple(self._meta.exclude or ())
            if 'pagamento' not in excluir:
                # `instance._meta` é a do MODELO (compartilhada), então o
                # ajuste fica restrito a esta chamada e é desfeito depois.
                self.instance._meta.exclude = excluir + ('pagamento',)
                try:
                    super()._post_clean()
                finally:
                    self.instance._meta.exclude = excluir
                return
        super()._post_clean()

    def clean(self):
        cleaned_data = super().clean()
        pagamento = cleaned_data.get('pagamento') or self.pagamento_fixo
        transacao_financeira = cleaned_data.get('transacao_financeira')
        competencia_bancaria = cleaned_data.get('competencia_bancaria')
        competencia_caixa = cleaned_data.get('competencia_caixa')
        dt_pagamento = cleaned_data.get('dt_pagamento')


        # Verifica se a fatura está presente
        if pagamento:
            # Atribui o estabelecimento da fatura ao campo estabelecimentos
            cleaned_data['estabelecimento'] = pagamento.estabelecimento
        elif self.instance.pagamento_id:
            # No MODAL o pagamento vem da URL (injetado pela view): o
            # `pagamento_id` já está na instância e não precisa vir no POST.
            cleaned_data['estabelecimento'] = (
                self.instance.pagamento.estabelecimento)
        else:
            raise forms.ValidationError('Pagamento é obrigatório.')

        # Pagamento só aceita transação de SAÍDA que movimente banco OU caixa.
        if transacao_financeira:
            if transacao_financeira.tipo != 'saida':
                self.add_error(
                    'transacao_financeira',
                    'Em PAGAMENTO escolha uma transação de SAÍDA (as de '
                    'entrada são de recebimento/fatura).')
            elif transacao_financeira.movimento not in ('banco', 'caixa'):
                self.add_error(
                    'transacao_financeira',
                    'Escolha uma transação que movimente BANCO ou CAIXA.')

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