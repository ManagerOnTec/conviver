from .models import BaixaFatura, Fatura
from django.contrib import admin
from django.contrib.admin.widgets import AdminDateWidget
from contas.models import Perfil
from .models import PreFatura, Fatura
from django.forms import BaseInlineFormSet
from django.core.exceptions import ValidationError
from django import forms
from dominios.utils import FilterByStatusMixin
from .models import Convenio
from admin_cadastros.models import Estabelecimento, Pessoa


class ConvenioForm(FilterByStatusMixin, forms.ModelForm):

    class Meta:
        model = Convenio

        fields = '__all__'

        widgets = {
            'inicio_vigencia': AdminDateWidget(),
            'final_vigencia': AdminDateWidget(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 🔹 Filtra somente Pessoas com classificacao 'cliente'
        self.fields['cliente'].queryset = Pessoa.objects.filter(
            classificacao_pessoa='paciente',
            status='A'
        )

    def clean(self):
        cleaned_data = super().clean()
        pagador_pj = cleaned_data.get('pagador_pj')
        pagador_pf = cleaned_data.get('pagador_pf')
        valor_mensal = cleaned_data.get('valor_mensal')
        valor_diaria = cleaned_data.get('valor_diaria')

        if not pagador_pj and not pagador_pf:
            self.add_error('pagador_pj', "Selecione um pagador PF ou PJ!")
            self.add_error('pagador_pf', "Selecione um pagador PF ou PJ!")

        if pagador_pj and pagador_pf:
            self.add_error(
                'pagador_pj', "Selecione apenas um tipo de pagador!")
            self.add_error(
                'pagador_pf', "Selecione apenas um tipo de pagador!")

        if not valor_mensal and not valor_diaria:
            self.add_error(
                'valor_mensal', "Informe um valor mensal ou um valor diário!")
            self.add_error(
                'valor_diaria', "Informe um valor mensal ou um valor diário!")

        if valor_mensal and valor_diaria:
            self.add_error(
                'valor_mensal', "Informe apenas um valor, mensal ou diário!")
            self.add_error(
                'valor_diaria', "Informe apenas um valor, mensal ou diário!")

        return cleaned_data

    def clean_convenio(self):
        return self.cleaned_data['convenio'].title()


class PreFaturaForm(forms.ModelForm):
    class Meta:
        model = PreFatura
        fields = '__all__'

        widgets = {
            'competencia': AdminDateWidget(),
            'dt_vencimento': AdminDateWidget(),
        }

    def clean(self):
        cleaned_data = super().clean()
        pre_faturado = self.instance.pre_faturado  # Verifica se é pré-faturado

        # Se o registro for pré-faturado, não permite a exclusão
        if self.instance.pk and pre_faturado:
            raise ValidationError(
                "Não é possível excluir um registro que está pré-faturado.")

        return cleaned_data


class FaturaForm(forms.ModelForm):
    class Meta:
        model = Fatura
        fields = '__all__'

        widgets = {
            'inicio_vigencia': AdminDateWidget(),
            'final_vigencia': AdminDateWidget(),
            'competencia': AdminDateWidget(),
            'dt_vencimento': AdminDateWidget(),

        }

    def clean(self):
        cleaned_data = super().clean()
        faturado = self.instance.faturado  # Verifica se é faturado

        # Se o registro for faturado, não permite a exclusão
        if self.instance.pk and faturado:
            raise ValidationError(
                "Não é possível excluir um registro que está faturado.")

        return cleaned_data




# TODO: APOS IMPLANTAR O CAIXA, FIELD COMPETENCIA_CAIXA E NO IF TRANSACAOFINANCEIRA MOVIMENTO CAIXA EXIGIR O FIELD
class BaixaFaturaForm(forms.ModelForm):
    class Meta:
        model = BaixaFatura
        fields = '__all__'
        exclude = ['estabelecimento']  # Remover o campo estabelecimento do formulário

    def clean(self):
        cleaned_data = super().clean()
        fatura = cleaned_data.get('fatura')
        transacao_financeira = cleaned_data.get('transacao_financeira')
        competencia_bancaria = cleaned_data.get('competencia_bancaria')
        dt_recebimento = cleaned_data.get('dt_recebimento')


        # Verifica se a fatura está presente
        if fatura:
            # Atribui o estabelecimento da fatura ao campo estabelecimentos
            cleaned_data['estabelecimento'] = fatura.estabelecimento
        else:
            raise forms.ValidationError('Fatura é obrigatória.')

        # Verifica se a transação financeira é do tipo 'entrada' e de movimento 'banco'
        if transacao_financeira and transacao_financeira.movimento == 'banco':
            if not competencia_bancaria:
                # Adiciona um erro ao campo 'competencia_bancaria'
                self.add_error('competencia_bancaria', 'O campo "Competência Bancária" é obrigatório para transações do tipo "banco".')

         # Validação: dt_recebimento deve ser igual ou maior que dt_abertura_competencia
        if dt_recebimento and competencia_bancaria:
            if dt_recebimento < competencia_bancaria.dt_abertura_competencia:
                self.add_error('dt_recebimento', 'A data de recebimento deve ser igual ou posterior à data de abertura da competência bancária.')

        return cleaned_data