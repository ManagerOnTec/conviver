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
from django.db import models


class ConvenioForm(FilterByStatusMixin, forms.ModelForm):

    class Meta:
        model = Convenio
        fields = '__all__'
        exclude = ['fatura_vig_inicial', 'fatura_vig_final']

        widgets = {
            'inicio_vigencia': AdminDateWidget(),
            'final_vigencia': AdminDateWidget(),
        }

    def __init__(self, *args, **kwargs):
        # Força a reaplicação do queryset DEPOIS dos __init__ da MRO.
        super().__init__(*args, **kwargs)
        self._aplicar_filtro_cliente()

    def _aplicar_filtro_cliente(self):
        """Somente PACIENTES ativos podem ser cliente do convênio.

        Precisa rodar depois do ``FilterByStatusMixin.__init__`` (primeiro da
        MRO): ele percorre todos os ModelChoiceField e reescreve o queryset
        para ``status='A'`` de TODAS as Pessoas, o que incluía funcionários.
        """
        if 'cliente' not in self.fields:
            return
        self.fields['cliente'].queryset = Pessoa.objects.filter(
            classificacao_pessoa='paciente',
            status='A',
        )
        # O select2 de múltipla escolha dispensa o help_text de "Ctrl/Cmd".
        self.fields['cliente'].help_text = None

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

    def clean_cliente(self):
        clientes = self.cleaned_data.get('cliente')
        if clientes:
            invalidos = clientes.exclude(
                classificacao_pessoa='paciente', status='A')
            if invalidos.exists():
                raise ValidationError(
                    'Somente pacientes ativos podem ser vinculados como '
                    'cliente do convênio.')
        return clientes

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

    # A regra antiga ("não é possível excluir um registro que está faturado")
    # bloqueava TODA edição de fatura já finalizada — inclusive registrar uma
    # baixa no inline. A exclusão de fatura já é barrada pelo
    # `FaturaAdmin.has_delete_permission`, então a edição fica livre.




import copy


# TODO: APOS IMPLANTAR O CAIXA, FIELD COMPETENCIA_CAIXA E NO IF TRANSACAOFINANCEIRA MOVIMENTO CAIXA EXIGIR O FIELD
def _meta_com_exclusoes(meta, *campos):
    """`meta` (ModelFormOptions) com `campos` acrescentados ao `exclude`.

    O `_meta` do ModelForm é compartilhado por todas as instâncias; alterá-lo
    no `__init__` vazaria a exclusão para os outros formulários. Este clone leve
    mantém o `fields` já resolvido e só troca o `exclude`.
    """
    novo = copy.copy(meta)
    novo.exclude = tuple(meta.exclude or ()) + tuple(campos)
    return novo


class BaixaFaturaForm(forms.ModelForm):
    # `fatura_baixada` é a fatura sendo baixada. No admin (add/change) ela é
    # SELECIONÁVEL (não disabled): é o único lugar em que o usuário escolhe.
    # Na listagem/inline a tela já define a fatura, e o `__init__` a desabilita
    # e preenche o `initial` (aí o POST não traz o valor — e o
    # `_garantir_fatura_no_cleaned_data` repõe no cleaned_data).
    fatura_baixada = forms.ModelMultipleChoiceField(
        queryset=Fatura.objects.all(), required=False,
        help_text='Fatura que está sendo baixada.', label='Fatura')

    # Data de recebimento com o seletor de datas nativo do navegador
    # (`<input type="date">`): vale para a listagem editável (os widgets das
    # células vêm deste form) e para o admin (add/change/inline).
    dt_recebimento = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        input_formats=['%Y-%m-%d', '%d/%m/%Y'],
        label='Data de Recebimento')

    class Meta:
        model = BaixaFatura
        fields = '__all__'
        exclude = [
            'estabelecimento_baixa',  # preenchido com o estabelecimento da fatura
            # Auditoria e controle são definidos pelo BaixaFaturaAdmin.
            'us_registro_baixa', 'dt_registro', 'us_atualizacao_baixa',
            'dt_atualizacao', 'status',
        ]

    # Campos herdados da fatura: cópia do estado da fatura no recebimento. Ficam
    # desabilitados e são preenchidos a partir dela (inclusive os FKs herdados
    # `estabelecimento`/`us_registro`, cujos valores mora em `*_baixa`).
    CAMPOS_COPIA = BaixaFatura.CAMPOS_COPIADOS_DA_FATURA

    # `fatura_baixada` NÃO entra: é a própria fatura baixada e o form do
    # changelist já a exclui (só o parent link `fatura_ptr` vai oculto).
    CAMPOS_COPIA_SOMENTE_LEITURA = tuple(
        sorted({c for c in CAMPOS_COPIA if c not in ('estabelecimento',
                                                     'convenio')})
        + ['estabelecimento_baixa', 'us_registro_baixa',
           'us_atualizacao_baixa']
    )

    @classmethod
    def marcar_campos_copia_somente_leitura(cls, form_class):
        """Desabilita a cópia da fatura em um form (base) qualquer."""
        for nome in cls.CAMPOS_COPIA_SOMENTE_LEITURA:
            if nome in form_class.base_fields:
                form_class.base_fields[nome].disabled = True

    def __init__(self, *args, **kwargs):
        # A baixa tem TRÊS ligações com a fatura: o parent link da cadeia
        # (`fatura_ptr ↔ prefatura_ptr`), a cópia herdada `fatura` (de
        # PreFatura) e o M2M `fatura_baixada`. Só UM parent link é aceito por
        # ModelForm e o Django só trata como parent link o que é PK do modelo
        # pai (`fatura_ptr`); a cópia herdada `fatura` viraria um campo
        # editável obrigatório e atrapalharia o `_post_clean`. Ela sai do
        # form — o vínculo é gravado pelo `fatura_baixada`.
        # O clone fica na INSTÂNCIA (o `super().__init__` lê o `exclude` dali);
        # o `_meta` da CLASSE volta ao original logo abaixo, senão cada
        # instância somaria as exclusões no `_meta` compartilhado e o inline
        # (que lê `base_fields` da classe) ficaria sem campos.
        self._meta = _meta_com_exclusoes(
            self._meta, 'fatura', 'fatura_ptr', 'prefatura_ptr')
        # A tela que hospeda este form decide a fatura (listagem = a fatura da
        # linha; inline = só as baixas da própria fatura). Precisa ser lido
        # ANTES do super(), que não repassa kwargs desconhecidos.
        self._fatura_origem = kwargs.pop('fatura_origem', None)
        # Lista de campos do form desta instância (ex.: só o `list_editable` na
        # listagem). Sem ela vale o `fields='__all__'` do Meta.
        campos = kwargs.pop('fields', None)
        super().__init__(*args, **kwargs)
        # A classe tem de voltar ao `_meta` original (o `self._meta` da
        # instância continua com o clone, usado na validação).
        type(self)._meta = BaixaFaturaForm._meta
        instancia = self.instance

        # Na listagem, a instância é NOVA (sem pk) e o `fatura_origem` vem do
        # ChangeList; no admin/inline, a fatura sai do próprio vínculo.
        if self._fatura_origem is None and instancia is not None:
            self._fatura_origem = instancia.fatura_baixada_do_bd()

        # Na listagem/inline a fatura é definida pela TELA (fatura da linha /
        # fatura aberta): o campo fica desabilitado (o usuário não escolhe).
        # No admin (add/change) continua habilitado para o usuário escolher.
        if self._fatura_origem is not None:
            field_fatura = self.fields.get('fatura_baixada')
            if field_fatura is not None:
                field_fatura.disabled = True

        # Cópia da fatura: somente leitura.
        for nome in self.CAMPOS_COPIA_SOMENTE_LEITURA:
            if nome in self.fields:
                self.fields[nome].disabled = True
        for nome in ('convenio', 'valor', 'valor_fatura', 'valor_saldo',
                     'competencia', 'dt_vencimento', 'cliente',
                     'estabelecimento', 'us_registro'):
            if nome in self.fields:
                self.fields[nome].disabled = True

        self._aplicar_copia_no_instance()

        # O PK da baixa acompanha o parent link: o formset manda o `id` e o
        # ORM grava a linha herdada com essa pk. Sem o `initial`, o form pa
        # edição (admin) listaria o campo como vazio.
        if 'id' in self.fields and instancia is not None and instancia.pk:
            self.initial.setdefault('id', instancia.pk)

        # Campo `disabled` ignora o POST e usa o `initial`: sem isso o
        # ModelForm valida "obrigatório" em cima de um valor vazio.
        if self._fatura_origem is not None:
            fatura = self._fatura_origem
            for campo in self.CAMPOS_COPIA:
                field = self.fields.get(campo)
                if field is None or not field.disabled:
                    continue
                valor = getattr(fatura, campo, None)
                if valor is not None:
                    self.initial[campo] = valor
            for campo in ('estabelecimento', 'us_registro'):
                field = self.fields.get(campo)
                if field is None or not field.disabled:
                    continue
                self.initial[campo] = getattr(fatura, f'{campo}_id', None)
            # `fatura_baixada` é M2M: o initial é a LISTA de pks que será
            # gravada no vínculo da baixa (uma única fatura por baixa).
            if 'fatura_baixada' in self.fields:
                self.initial['fatura_baixada'] = [fatura.pk]
            # O POST da listagem traz só os campos editáveis da baixa: completa
            # a fatura baixada (chave obrigatória do form) e o usuário.
            dados = self.data.copy()
            if 'fatura_baixada' in self.fields:
                chave = self._chave_post('fatura_baixada')
                if not dados.getlist(chave):
                    dados.setlist(chave, [str(fatura.pk)])
            for campo in ('us_registro',):
                field = self.fields.get(campo)
                if field is None:
                    continue
                chave = self._chave_post(campo)
                if dados.get(chave):
                    continue
                valor = getattr(fatura, f'{campo}_id', None)
                if valor is not None:
                    dados[chave] = str(valor)
            self.data = dados

    def _aplicar_copia_no_instance(self):
        """Preenche a instância com a fatura antes de validar.

        Escreve direto nas colunas herdadas (`_id`/valor no `__dict__`): o
        ORM, ao salvar, grava a linha de `prefatura` a partir desses valores.
        """
        fatura = self._fatura_origem
        if fatura is None or not self.instance._state.adding:
            return
        for campo in self.CAMPOS_COPIA:
            if campo in self.instance.__dict__:
                continue
            valor = getattr(fatura, campo, None)
            if valor is not None:
                # FK é guardada no __dict__ como `<campo>_id`.
                modelo = BaixaFatura._meta.get_field(campo)
                if modelo.is_relation:
                    self.instance.__dict__[f'{campo}_id'] = valor.pk
                else:
                    self.instance.__dict__[campo] = valor
        self.instance.__dict__['estabelecimento_id'] = fatura.estabelecimento_id
        self.instance.__dict__['us_registro_id'] = fatura.us_registro_id
        self.instance.__dict__['status'] = fatura.status
        # M2M: o ORM guarda o vínculo no aliases `<campo>_ids`. Não basta
        # gravar aqui: com o `fatura_baixada` fora do form (listagem/inline),
        # o valor é reaplicado depois da validação (ver
        # `_garantir_fatura_no_cleaned_data`).
        self.instance.__dict__['fatura_baixada_ids'] = [fatura.pk]

    def _fatura_para_validacao(self):
        """Fatura desta baixa, já com o `fatura_baixada` lido (se for campo)."""
        fatura = self._fatura_da_instancia()
        if fatura is not None:
            return fatura
        pk = self._fatura_do_post()
        return self._fatura_do_valor(pk) if pk else None

    def _garantir_fatura_no_cleaned_data(self):
        """Põe a fatura em `cleaned_data['fatura_baixada']` quando o campo
        não está no form (listagem editável e inline).

        O `ModelForm._post_clean` refaz `instance = construct_instance(...)`,
        que descarta o `fatura_baixada_ids` gravado no `__init__`: sem isto o
        `save()` não saberia a fatura (a cópia herdada e o vínculo M2M
        ficariam vazios). Roda DEPOIS do `validate_unique` do modelo.
        """
        if 'fatura_baixada' in self.fields:
            if self.is_bound and hasattr(self.data, 'getlist') and self.data.getlist(
                    self.add_prefix('fatura_baixada')):
                return  # campo no form com valor do POST: o Django já validou
            # Sem valor no POST (campo desabilitado): a fatura vem da
            # tela/instância e vai direto para o cleaned_data abaixo.
        elif not self.is_bound:
            return
        if not hasattr(self, 'cleaned_data'):
            return
        if self._cleaned_data_preenchida():
            return  # já garantida (o clean() chama isto também)
        fatura = self._fatura_para_validacao()
        if fatura is None:
            return
        # O campo está no FORM mas sem o valor no POST (desabilitado e sem
        # initial de GET): é o caso do admin (change/add), em que o
        # `cleaned_data` vem do POST — o initial não é aplicado a campos
        # desabilitados lá. Garante a fatura na instância para o `save()`.
        self.cleaned_data['fatura_baixada'] = [fatura]
        object.__setattr__(self.instance, 'fatura_baixada_ids', [fatura.pk])

    def _cleaned_data_preenchida(self):
        """`cleaned_data['fatura_baixada']` já tem a fatura desta baixa."""
        faturas = (self.cleaned_data or {}).get('fatura_baixada')
        return bool(faturas)

    def _post_clean(self):
        # O POST do admin (change/add) não traz os campos HERDADOS da fatura
        # (não estão no form do admin, ver `BaixaFaturaAdmin.fields`): repõe
        # no data antes do construct, senão a linha herdada (NOT NULL) é
        # gravada em branco — e a validação "obrigatório" nem passa.
        try:
            if self.is_bound:
                self._preencher_copia_da_fatura()
        except Exception:
            # Sem fatura conhecida (nada selecionado no add): o `clean()` já
            # vai reclamar de "Fatura é obrigatória".
            pass
        super()._post_clean()
        self._garantir_fatura_no_cleaned_data()
        # Reforço: a cópia herdada é feita a partir da fatura do cleaned_data
        # (o construct_instance não toca nela — os campos não estão no form).
        faturas = (self.cleaned_data or {}).get('fatura_baixada')
        if faturas and self.instance._state.adding:
            fatura = faturas[0]
            if self.instance.competencia is None:
                for campo in self.CAMPOS_COPIA:
                    valor = getattr(fatura, campo, None)
                    if valor is not None:
                        campo_modelo = BaixaFatura._meta.get_field(campo)
                        if campo_modelo.is_relation:
                            self.instance.__dict__[f'{campo}_id'] = valor.pk
                        else:
                            self.instance.__dict__[campo] = valor
                self.instance.__dict__['estabelecimento_id'] = \
                    fatura.estabelecimento_id
                self.instance.__dict__['us_registro_id'] = fatura.us_registro_id
                self.instance.__dict__['status'] = fatura.status

    def _chave_post(self, campo):
        """Nome do campo no POST, já com o prefixo do form.

        `self.add_prefix('x')` devolve 'form-0-x' (sem hífen final) e é o
        mesmo nome usado pelos widgets — é ele que precisa ser lido/escrito.
        """
        return self.add_prefix(campo)

    def _fatura_do_post(self):
        """PK da fatura baixada informada no POST (ou na instância)."""
        for nome in ('fatura_baixada', 'fatura', 'fatura_ptr'):
            valor = self.data.get(self._chave_post(nome))
            if valor:
                return valor
        instancia = self.instance
        if instancia is not None:  # Constante por compatibilidade.
            return instancia.pk_fatura_baixada()
        return None

    def _fatura_da_instancia(self):
        """Fatura de origem do form (guardada no __init__)."""
        fatura = getattr(self, '_fatura_origem', None)
        if fatura is not None:
            return fatura
        instancia = self.instance
        if instancia is not None:
            return instancia.fatura_baixada_do_bd()
        return None

    @staticmethod
    def _fatura_do_valor(fatura_id):
        """Fatura referenciada pela pk da baixa ou pela pk do parent link."""
        baixa = BaixaFatura.objects.filter(pk=fatura_id).first()
        if baixa is not None:
            fatura = baixa.fatura_baixada_do_bd()
            if fatura is not None:
                return fatura
        return Fatura.objects.filter(pk=fatura_id).first()

    def _preencher_copia_da_fatura(self):
        """Repõe no POST os campos da cópia que o navegador não envia."""
        fatura_id = self._fatura_do_post()
        fatura = self._fatura_do_valor(fatura_id) if fatura_id else None
        if fatura is None:
            fatura = self._fatura_da_instancia()
        if fatura is None:
            return

        dados = self.data.copy()
        prefixo = self.prefix
        prefixo = f'{prefixo}-' if prefixo else ''
        valores = {campo: getattr(fatura, campo) for campo in self.CAMPOS_COPIA}

        # `fatura_baixada` (M2M) e `fatura` (parent link): o navegador não
        # envia o valor quando o campo está desabilitado/oculto.
        for nome_fatura in ('fatura_baixada', 'fatura'):
            field = self.fields.get(nome_fatura)
            if field is not None and field.disabled:
                dados.setlist(f'{prefixo}{nome_fatura}', [str(fatura.pk)])

        for campo, valor in valores.items():
            field = self.fields.get(campo)
            if field is None or not field.disabled:
                continue
            campo_modelo = BaixaFatura._meta.get_field(campo)
            chave = f'{prefixo}{campo}'
            if campo in ('estabelecimento', 'us_registro'):
                # FK herdada: o valor usado pela baixa é a coluna `*_baixa`.
                dados[chave] = str(valor.pk) if valor else ''
                continue
            if campo_modelo.is_relation:
                dados[chave] = '' if valor is None else str(valor.pk)
            elif isinstance(campo_modelo, models.DateField) and valor:
                dados[chave] = valor.isoformat()
            else:
                dados[chave] = '' if valor is None else str(valor)

        # A própria fatura baixada é obrigatória no form da listagem (o formset
        # não traz esse campo; a referência vem do parent link `fatura_ptr`).
        if 'fatura_baixada' in self.fields and not dados.getlist(
                f'{prefixo}fatura_baixada'):
            dados.setlist(f'{prefixo}fatura_baixada', [str(fatura.pk)])
        self.data = dados

    def clean(self):
        # No inline/listagem o `fatura_baixada` não é campo do form: a fatura
        # chega pelo `_fatura_origem` (fatura aberta / fatura da linha).
        if 'fatura_baixada' not in self.fields:
            self._garantir_fatura_no_cleaned_data()
        cleaned_data = super().clean()
        faturas = cleaned_data.get('fatura_baixada')
        transacao_financeira = cleaned_data.get('transacao_financeira')
        competencia_bancaria = cleaned_data.get('competencia_bancaria')
        dt_recebimento = cleaned_data.get('dt_recebimento')

        # Verifica se a fatura está presente
        if not faturas:
            raise forms.ValidationError('Fatura é obrigatória.')
        if len(faturas) != 1:
            # O M2M está no formulário da FATURA (inline: várias baixas), mas
            # cada linha de baixa é o recebimento de UMA fatura.
            raise forms.ValidationError(
                'Cada baixa deve estar vinculada a uma única fatura.')
        fatura = faturas[0]
        # Atribui o estabelecimento da fatura ao campo estabelecimentos
        cleaned_data['estabelecimento'] = fatura.estabelecimento

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

    def save(self, commit=True):
        """Grava a baixa e o vínculo M2M com a fatura baixada.

        O `fatura_baixada` vem do campo do formulário; no inline (campo fora do
        form) usa-se a fatura da instância, que o ModelAdmin definiu.
        """
        fatura = None
        if self.cleaned_data.get('fatura_baixada'):
            fatura = self.cleaned_data['fatura_baixada'][0]
        if fatura is None:
            fatura = self._fatura_origem or self._fatura_da_instancia()

        baixa = super().save(commit=False)
        # A fatura é só informada aqui; quem grava o vínculo é o
        # `BaixaFatura.save()` (que também preenche a cópia herdada a partir
        # dela). O `.set()` só funciona depois que a baixa tem pk.
        if fatura is not None:
            object.__setattr__(baixa, 'fatura_baixada_ids', [fatura.pk])
        if not commit:
            return baixa

        baixa.save()
        return baixa