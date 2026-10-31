"""
Listagem EDITÁVEL com TODAS as colunas do `list_display` — ADMIN FATURAS
========================================================================

Problema
--------
No Django 4.2, quando o ModelAdmin tem `list_editable`, o `ChangeList` só
conhece os campos editáveis. O template `admin/change_list_results.html`
escreve a `<table>` UMA vez e resume o conteúdo de cada célula a:

    {% if link_in_col %} ... <td><a>...</a></td>
    {% else %}<td>{{ field.contents }}</td>

Ao remover as variáveis `link_in_col`/`field.contents` dos itens (4.2), o
`items_for_result` passou a gerar <th>/<td> avulsos — sem `<table>` em volta,
fora dos loops do template. O navegador descarta essas linhas, a listagem
vira um monte de `<label>`/`<input>` soltos e as colunas que não são editáveis
desaparecem.

Solução
-------
Este módulo substitui apenas a renderização da listagem quando há
`list_editable`:

- o Cabeçalho sai de `admin_list.result_headers` (todas as colunas);
- cada linha é montada aqui com UMA CÉLULA POR COLUNA do `list_display`;
- nas colunas de `list_editable` entra o widget do formset (o mesmo `<input>`
  já ligado ao POST — valores digitados e envio continuam intactos);
- nas demais entra o texto/HTML que o Django já produz para aquela coluna.

Uso: no ModelAdmin, defina

    from admin_faturas.changelist_editavel import ChangeListEditavel
    get_changelist = lambda self, request: ChangeListEditavel

O template `admin/change_list.html` deste projeto chama o hook
`{% changelist_result_list cl %}` (fallback: `{% result_list cl %}`).
"""
from django.contrib.admin.templatetags.admin_list import result_headers
from django.contrib.admin.views.main import ChangeList, IncorrectLookupParameters
from django.contrib.admin.utils import (
    display_for_field,
    display_for_value,
    label_for_field,
    lookup_field,
)
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.core.exceptions import (
    FieldDoesNotExist, ObjectDoesNotExist,
)
from django.db import models
from django.urls import NoReverseMatch
from django import forms
from django.forms import Textarea
from django.utils.html import format_html
from django.utils.safestring import mark_safe


class _Celula:
    """Uma célula já renderizada (texto/HTML) de uma coluna da listagem."""

    # `title`: dica de tela livre. `exclusao`: motivo pelo qual o registro NÃO
    # pode ser excluído — o template mostra a célula do pk em cinza com o motivo
    # na dica de tela (antes mesmo da seleção para a ação em lote).
    # `texto_completo`: conteúdo ORIGINAL do campo de texto. Quando presente, a
    # célula mostra um resumo em uma linha e o template põe um botão “ver” que
    # abre o MODAL de leitura/cópia (ver `admin_changelist_actions.js`).
    __slots__ = ("contents", "is_link", "field", "title", "exclusao",
                 "texto_completo")

    def __init__(self, contents, is_link=False, field=None, title="",
                 exclusao="", texto_completo=""):
        self.contents = contents
        self.is_link = is_link
        self.field = field
        self.title = title
        self.exclusao = exclusao
        self.texto_completo = texto_completo


class ChangeListEditavel(ChangeList):
    """ChangeList que entrega à listagem TODAS as colunas do `list_display`.

    Cabeçalho e células percorrem a MESMA lista de colunas efetivas, na mesma
    ordem. Uma única coluna fora de sincronia (a mais, ou a menos) desloca todos
    os títulos seguintes — é o que acontece quando `result_headers` gera um
    header a mais (ver `colunas_efetivas`).
    """

    #: Campos de TEXTO LONGO: na listagem entram RESUMIDOS em uma linha e, com
    #: clique, abrem o modal de leitura/cópia (senão estouram a altura da linha).
    campos_texto_longo = ('descricao', 'observacao', 'cliente', 'empenho',
                          'empenho_global', 'periodo_tratamento',
                          'display_clientes')

    #: Caracteres mostrados na célula antes do botão “ver”.
    limite_texto_celula = 60

    def ids_da_listagem(self):
        """PKs da PÁGINA atual — o que os checkboxes da tabela enviam."""
        return [obj.pk for obj in self.result_list]

    def motivo_exclusao(self, obj):
        """Motivo pelo qual `obj` NÃO pode ser excluído (None = pode).

        É a MESMA regra da ação em lote e do botão Excluir do registro:
        `motivo_recusa_exclusao()` do modelo. Nunca derruba a listagem.
        """
        metodo = getattr(obj, 'motivo_recusa_exclusao', None)
        if metodo is None:
            return None
        try:
            return metodo()
        except Exception:
            return None

    def _linhas_nao_editaveis(self):
        """Pks (string) que não podem ser editadas em linha nesta tela.

        Vem do ModelAdmin (`get_linhas_nao_editaveis`) — um recorte EM LOTE,
        calculado UMA vez por requisição (sem consulta por linha).
        """
        if not hasattr(self, '_cache_linhas_travadas'):
            metodo = getattr(self.model_admin, 'get_linhas_nao_editaveis', None)
            try:
                self._cache_linhas_travadas = (
                    {str(pk) for pk in metodo(self.request)}
                    if metodo is not None else set())
            except Exception:
                self._cache_linhas_travadas = set()
        return self._cache_linhas_travadas

    def motivo_edicao(self, obj):
        """Motivo pelo qual `obj` NÃO pode ser alterado (None = pode).

        MESMA regra da tela de alteração (`motivo_recusa_edicao()`). Com
        motivo, as colunas de `list_editable` viram TEXTO (somente leitura) e
        a linha não entra no POST — listagem editável é edição, e a regra vale
        igual.
        """
        if str(getattr(obj, 'pk', '')) in self._linhas_nao_editaveis():
            return ('já está em andamento no fluxo — altere/responda pela etapa '
                    'de origem. As colunas editáveis aparecem somente leitura.')
        metodo = getattr(obj, 'motivo_recusa_edicao', None)
        if metodo is None:
            return None
        try:
            return metodo()
        except Exception:
            return None

    def colunas_efetivas(self):
        """Colunas do `list_display` que o Django consegue renderizar.

        Com `list_editable`, o Django restringe `list_display` aos campos do
        formset MAIS um, e `result_headers` só aceita colunas resolvíveis pelo
        `label_for_field` (campo do modelo, atributo/método do ModelAdmin ou
        campo do form). Coluna marcada com `short_description` e `admin_order_field`
        (ex.: métodos como `gerar_prefaturas_button`) é resolvida normalmente.

        A lista é sempre uma SUBLISTA de `list_display`, na mesma ordem — é o
        que mantém o cabeçalho e as células alinhados — e SEMPRE SEM
        `action_checkbox`: essa célula já é escrita pelo template
        (`change_list_results_editavel.html`), com o seu `<input>`. O
        cabeçalho dessa coluna (checkbox "selecionar todos") continua vindo do
        `result_headers` em `cabecalhos`.
        """
        # `formset` só existe em ModelAdmin com `list_editable`.
        formset = getattr(self, 'formset', None)
        if not formset or not formset.forms:
            return [f for f in self.list_display if f != 'action_checkbox']
        form = formset.forms[0]
        colunas = []
        for field_name in self.list_display:
            if field_name == 'action_checkbox':
                continue
            try:
                label_for_field(field_name, self.model, self.model_admin,
                                form=form)
            except (AttributeError, FieldDoesNotExist):
                continue
            colunas.append(field_name)
        return colunas

    def _eh_coluna_pk(self, field_name):
        """Coluna da chave (pk/id): onde a dica da linha é fixada."""
        return field_name in (self.model._meta.pk.name, 'pk', 'id')

    def _eh_link(self, indice, field_name):
        """Mesma regra de `link_in_col` do Django (que é função aninhada)."""
        if self.list_display_links is None:
            return False
        if indice == 0 and not self.list_display_links:
            return True
        return field_name in self.list_display_links

    def _valor_da_coluna(self, obj, field_name):
        """Texto/HTML da coluna (mesma regra do Django), sem o link."""
        admin = self.model_admin
        empty = admin.get_empty_value_display()
        try:
            f, attr, value = lookup_field(field_name, obj, admin)
        except ObjectDoesNotExist:
            return empty

        empty = getattr(attr, "empty_value_display", empty)

        if f is None or f.auto_created:
            boolean = getattr(attr, "boolean", False)
            return display_for_value(value, empty, boolean)

        if isinstance(f.remote_field, models.ManyToOneRel):
            valor = getattr(obj, f.name)
            return empty if valor is None else valor

        return display_for_field(value, f, empty)

    def _celula_hidden_travada(self, form, field_name):
        """`<input type=hidden>` com o valor ORIGINAL de um campo editável
        numa linha travada (ver comentário em `linha_renderizada`)."""
        bf = form[field_name]
        if bf.value() is None or bf.value() == '':
            html = '<input type="hidden" name="%s" value="">' % bf.html_name
        else:
            html = bf.as_hidden()
        return _Celula(mark_safe(str(bf.errors) + html), False, bf)

    def linha_renderizada(self, obj, form=None):
        """Lista de _Celula, uma por item de `list_display`."""
        admin = self.model_admin
        editaveis = set(getattr(admin, 'list_editable', []) or [])
        celulas = []

        colunas = self.colunas_efetivas()
        aviso = self.motivo_exclusao(obj) or ''
        # Linha TRAVADA pelo fluxo: as colunas editáveis ficam somente leitura
        # (mesma regra da tela de alteração).
        travada = self.motivo_edicao(obj) or ''
        for indice, field_name in enumerate(colunas):
            eh_link = self._eh_link(indice, field_name)
            conteudo = self._valor_da_coluna(obj, field_name)
            dica = aviso if self._eh_coluna_pk(field_name) else ''
            if travada and self._eh_coluna_pk(field_name):
                dica = travada

            # Texto de campo em list_editable (ex.: `descricao`): fica RESUMIDO
            # em uma linha, com o texto completo no MODAL (leitura + cópia).
            # Sem isto, o valor longo estourava a altura da linha.
            if self._eh_texto_longo(field_name, form):
                celulas.append(self._celula_texto_longo(
                    obj, field_name, conteudo, form, travada))
                continue

            # Coluna editável: usa o widget do formset (mantém o POST) —
            # exceto na linha travada, que sai como texto somente leitura.
            # Na travada entra um HIDDEN com o valor original: o POST do
            # navegador sempre manda TODOS os campos do formset; sem o hidden
            # o campo obrigatório chegaria vazio e invalidaria o formset TODO
            # (blocking inclusive as linhas liberadas). Como o valor hidden
            # é igual ao do banco, `has_changed()` é falso e nada é gravado
            # na linha travada.
            if (travada and form is not None and field_name in editaveis
                    and field_name in getattr(form, "fields", {})):
                celulas.append(self._celula_hidden_travada(form, field_name))
                continue
            if (not eh_link and form is not None and not travada
                    and field_name in getattr(form, "fields", {})
                    and not (field_name == self.model._meta.pk.name
                             and form[self.model._meta.pk.name].is_hidden)):
                bf = form[field_name]
                return_widget = mark_safe(str(bf.errors) + str(bf))
                celulas.append(_Celula(return_widget, False, bf))
                continue

            if eh_link:
                try:
                    url = self.url_for_result(obj)
                except NoReverseMatch:
                    celulas.append(_Celula(conteudo, exclusao=dica))
                    continue
                url = add_preserved_filters(
                    {"preserved_filters": self.preserved_filters,
                     "opts": self.opts}, url)
                attr_pk = str(self.to_field) if self.to_field else self.model._meta.pk.attname
                serial = obj.serializable_value(attr_pk)
                conteudo = format_html(
                    '<a href="{}">{}</a>', url, conteudo,
                )
                celulas.append(_Celula(conteudo, True, exclusao=dica))
            else:
                celulas.append(_Celula(conteudo, exclusao=dica))

        return celulas

    def _eh_texto_longo(self, field_name, form):
        """A coluna é um campo de TEXTO (de `list_editable` ou do modelo)?"""
        if field_name not in self.campos_texto_longo:
            return False
        if form is not None and field_name in getattr(form, 'fields', {}):
            return isinstance(form.fields[field_name].widget, Textarea)
        try:
            campo = self.model._meta.get_field(field_name)
        except Exception:
            return field_name in self.campos_texto_longo
        return isinstance(campo, (models.TextField, models.CharField))

    def _celula_texto_longo(self, obj, field_name, conteudo, form, travada):
        """Célula de texto longo: resumo em UMA linha + botão “ver”.

        O texto integral vai para o botão (`data-texto`); o template o coloca
        no MODAL com botão de copiar. Quando o campo é editável (list_editable)
        e a linha não está travada, o `<textarea>` continua na célula — só que
        LIMITADO à altura da linha; o modal é o jeito confortável de ler e
        copiar.
        """
        valor = ''
        try:
            valor = getattr(obj, field_name, '') or ''
        except Exception:
            valor = ''
        texto = str(valor).strip()
        resumo = texto if len(texto) <= self.limite_texto_celula else \
            texto[:self.limite_texto_celula].rstrip() + '…'
        editavel = (form is not None and not travada
                    and field_name in getattr(form, 'fields', {}))

        partes = []
        if editavel:
            bf = form[field_name]
            partes.append(str(bf.errors))
            partes.append(str(bf))
        else:
            partes.append(format_html('<span class="texto-resumo">{}</span>',
                                      resumo))
        if texto:
            partes.append(format_html(
                '<button type="button" class="btn-ver-texto"'
                ' data-texto="{}" data-titulo="{}"'
                ' title="Ver o texto completo (e copiar)">↗</button>',
                texto, field_name.replace('_', ' ').title()))
        return _Celula(mark_safe(''.join(str(p) for p in partes)),
                       texto_completo=texto)

    def linhas_renderizadas(self):
        """(form, [celulas], pk) por registro — usado pelo template.

        `form` é None quando o ModelAdmin não tem `list_editable`; por isso a pk
        vem à parte (o template usa no checkbox de seleção).
        """
        formset = getattr(self, 'formset', None)
        if formset:
            for obj, form in zip(self.result_list, formset.forms):
                yield form, self.linha_renderizada(obj, form), obj.pk
        else:
            for obj in self.result_list:
                yield None, self.linha_renderizada(obj, None), obj.pk

    @property
    def cabecalhos(self):
        """Cabeçalho com as mesmas colunas de `linha_renderizada`.

        O template padrão recebe os headers via `{% result_list cl %}`; como
        este ChangeList monta a tabela sozinho, o cabeçalho é calculado aqui,
        com exatamente as colunas efetivas (mesma lista usada nas linhas).
        """
        colunas = self.colunas_efetivas()
        # `result_headers` numera as colunas pelo índice em `list_display`
        # (ordenação `?o=índice`). Mantém o índice ORIGINAL, senão o clique no
        # cabeçalho ordena por outra coluna.
        indices = [self.list_display.index(c) for c in colunas]
        original = self.list_display
        headers = []
        # `result_headers` SEMPRE emite a coluna `action_checkbox` (com o
        # "selecionar todos"). O `__init__` do ChangeList a insere em
        # `list_display` quando há `list_editable`; quando já está lá, usar a
        # lista como está e não adicionar de novo. Ela fica APENAS no cabeçalho:
        # a célula correspondente é escrita pelo template.
        self.list_display = ['action_checkbox'] + colunas
        try:
            for header in result_headers(self):
                if header['class_attrib'] == ' class="action-checkbox-column"':
                    headers.append(header)  # "selecionar todos"
                    continue
                headers.append(header)
        finally:
            self.list_display = original
        # Recoloca o índice original em cada header de coluna (o helper acima
        # só expanded o cabeçalho; o índice é recalculado aqui pela ordem).
        coluna_headers = [h for h in headers
                          if h['class_attrib'] != ' class="action-checkbox-column"']
        for header, indice in zip(coluna_headers, indices):
            header['indice'] = indice
        return headers


class ChangeListBaixaFatura(ChangeListEditavel):
    """Listagem de BAIXA DE FATURAS = faturas finalizadas ainda com saldo.

    A tela não lista baixas já registradas: lista as CONTAS A RECEBER. Cada
    linha é uma `Fatura` (finalizada, ativa, com saldo em aberto, do
    estabelecimento filtrado) e nela o usuário lança o recebimento. Só os
    campos exclusivos da baixa são editáveis; as demais colunas vêm da fatura.

    O formulário de cada linha é um `BaixaFaturaForm` NOVO (sem pk) apontando
    para a fatura da linha — ao salvar, a baixa é criada com
    `fatura_baixada` = fatura (o parent link `fatura_ptr` é preenchido no
    `save()` do modelo).

    O queryset do ChangeList continua sendo o de BAIXAS (é o que os filtros e
    a busca do ModelAdmin conhecem); as linhas exibidas vêm de
    `model_admin.faturas_pendentes()`.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # `ChangeList` recebe o request como 1º posicional mas não o guarda.
        self.request = args[0] if args else kwargs.get('request')
        self._faturas = None
        self._forms = None
        self._forms_por_pk = {}
        # O rótulo é genérico ("Salvar"), alinhado à direita (ver template).

    def _filtro_tolera_baixa(self, filtro):
        """Filtros de campo (tupla nome/lookup) do modelo da BAIXA que não
        existem na FATURA são descartados (a grade é de faturas)."""
        if not isinstance(filtro, (list, tuple)):
            return filtro
        campo = str(filtro[0]).split('__')[0]
        return filtro if campo in self._campos_da_fatura() else None

    def get_filters(self, request):
        # Aceita as duas formas: `(filtros, has_active)` (4.2/5.0) e
        # `(filtros, lookups, has_active)` (5.1+). Em todas, os itens que são
        # pares (campo, valor) só da BAIXA são descartados (a grade é de
        # faturas) — senão o queryset quebraria com campo inexistente.
        resultados = list(super().get_filters(request))
        for indice, valor in enumerate(resultados):
            if isinstance(valor, (list, tuple)) and valor and isinstance(
                    valor[0], (list, tuple)):
                resultados[indice] = [
                    item for item in valor
                    if self._filtro_tolera_baixa(item) is not None]
        return tuple(resultados)

    # ------------------------------------------------------------------
    # Origem das linhas
    # ------------------------------------------------------------------
    def faturas_pendentes(self):
        """Faturas finalizadas com saldo, já filtradas, buscadas e ordenadas."""
        if self._faturas is not None:
            return self._faturas

        admin = self.model_admin
        base = admin.faturas_pendentes(self.request)
        faturas = base

        # Filtros da barra lateral/busca: aplicados INTEIRAMENTE sobre a
        # fatura (não sobre a baixa). O `SimpleListFilter.queryset` do admin
        # (Competência, status, convênio/pagador, estabelecimento) filtra a
        # FATURA, que é o que a listagem mostra. Reaproveitar
        # `self.get_queryset` aqui aplicaria filtros de BAIXA na fatura e
        # ainda DESCARTAVA silenciosamente qualquer filtro inválido.
        from django.core.exceptions import FieldError

        # Filtro incompatível com a fatura: não derruba a tela (bypass).
        try:
            faturas = self._filtrar_por_parametros(self.request, faturas)
        except FieldError:
            faturas = base
        if faturas is None:
            faturas = base

        # Pesquisa do topo/busca do admin: campos da FATURA.
        parametro_busca = getattr(self, 'search_var', 'q') or 'q'
        termo = self.request.GET.get(parametro_busca, '')
        if termo:
            try:
                faturas, _ = admin.get_search_results(
                    self.request, faturas, termo)
            except FieldError:
                pass

        # Ordenação RELATIVA à lista original (as linhas são faturas): o
        # `get_ordering` devolve '?o=índice' — resolvido na `list_display`
        # abaixo — ou um campo da FATURA. O padrão do modelo
        # (`-dt_recebimento`) não existe na fatura e quebraria a tela.
        try:
            ordenacao = self.get_ordering(self.request, faturas)
        except (FieldError, ValueError, TypeError):
            ordenacao = None
        ordenacao = [campo for campo in (ordenacao or admin.ordering)
                     if campo in self._campos_da_fatura()]
        faturas = faturas.order_by(*(ordenacao or ['dt_vencimento', 'pk']))

        self._faturas = list(faturas)
        self.result_count = len(self._faturas)
        self.full_result_count = len(self._faturas)
        return self._faturas

    def get_filters_params(self, params=None):
        """Parâmetros de filtro: os FILTROS SEMÂNTICOS da fatura.

        A listagem é de CONTAS A RECEBER (faturas), então os lookups de campo
        que o Django extrairia da URL (`?dt_vencimento__lt=...`,
        `?competencia=...`, `?status=...`) são tratados pelos filtros da
        fatura em `_filtrar_por_parametros`. Sem isto o Django os descarta
        como "filtro de campo desconhecido" e a tela mostraria tudo.
        """
        keep = {'status', 'competencia', 'convenio_pagador', 'estabelecimento',
                'pre_faturado', 'faturado',
                # Filtros laterais da listagem de baixas (SimpleListFilter):
                # o valor vem do GET e os `filter_specs` precisam recebê-lo
                # (os `used_parameters` são populados com o `pop()` da chave).
                'saldo', 'dt_recebimento', 'competencia_bancaria',
                'cliente_filtro', 'dt_vencimento'}
        if params is None:
            # `self.request` só existe depois do `__init__` desta classe, e o
            # `ChangeList.__init__` (super) já chama este método.
            params = getattr(self, 'request', None)
            if params is None:
                return {}
            params = params.GET
        params = params or self.request.GET
        # DICT (o `get_filters` do Django itera `.items()` e dá `pop()` nas
        # chaves processadas por cada spec — formato de QueryDict). O filtro
        # `competencia` vale SEMPRE (o valor é uma data 'AAAA-MM-DD', lida
        # pelo `CustomDateFilter`, não como lookup de campo).
        return {chave: valor for chave, valor in params.items()
                if chave in keep or '__' in chave}

    def _campos_da_fatura(self):
        """Nomes de campo do modelo FATURA (a grade é de faturas)."""
        from admin_faturas.models import Fatura
        return ({f.name for f in Fatura._meta.get_fields()}
                | {'pk', 'id'})

    def _filtrar_por_parametros(self, request, faturas):
        """Aplica os `list_filter` do ModelAdmin diretamente na FATURA.

        Os filtros (`StatusFilterAdminMixin`, `ConvenioPagadorFilter`,
        `CustomDateFilter`...) são `SimpleListFilter`; a listagem de baixas
        mostra faturas, então cada um recebe o queryset de FATURAS como base.
        O valor usado é o do próprio `request` (mesma leitura que o Django
        faz na barra lateral). A instância do filtro é a que o ChangeList já
        criou (para reaproveitar `value()`/`used_parameters`).
        """
        # 1) Lookups de campo escritos na URL e aplicados na FATURA
        #    (ex.: `?dt_vencimento__lt=...`, `?competencia=...`).
        #    Os parâmetros que já são de um `SimpleListFilter`
        #    (`status`, `competencia`, `convenio_pagador`, `estabelecimento`)
        #    são lidos pelos próprios filtros no passo 2.
        from datetime import datetime

        admin = self.model_admin
        filtros_laterais = set()
        for espec in admin.get_list_filter(request):
            if not isinstance(espec, (list, tuple)):
                filtros_laterais.add(espec.parameter_name)

        def valor_para(campo, valor):
            if campo in ('competencia', 'dt_vencimento', 'dt_registro',
                         'dt_liquidacao', 'dt_recebimento'):
                # `__year`/`__month` chegam como inteiro puro: não é data, e o
                # filtro vai no dicionário `periodo` como lookup (year/month).
                if valor.isdigit():
                    return valor
                try:
                    return datetime.strptime(valor, '%Y-%m-%d').date()
                except ValueError:
                    return None
            return valor

        campos_fatura = self._campos_da_fatura()
        filtros = {}
        periodo = {}
        # A URL chega montada pelo Django com o nome do campo da BAIXA
        # (`dt_recebimento__year`); na grade de faturas ele vira
        # `dt_vencimento__year` (as colunas da linha são da fatura).
        equivalencias = {'dt_recebimento': 'dt_vencimento',
                         'valor_baixa': 'valor_fatura',
                         'fatura_baixada': 'id'}
        for chave, valores in request.GET.lists():
            campo = chave.split('__')[0]
            if chave in filtros_laterais:
                continue
            sufixo_chave = ''
            if campo not in campos_fatura:
                equivalente = equivalencias.get(campo)
                if equivalente is None or equivalente not in campos_fatura:
                    continue
                chave = chave.replace(campo, equivalente, 1)
                campo = equivalente
                sufixo_chave = chave.split('__', 1)[1] if '__' in chave else ''
            for valor in valores:
                if not valor:
                    continue
                valor = valor_para(campo, valor)
                if valor is None:
                    continue
                if sufixo_chave in ('year', 'month'):
                    # Ano/mês convivem num MESMO `filter()` (AND).
                    periodo[chave] = valor
                else:
                    filtros[chave] = valor
        if periodo:
            # Mesma família (competencia/dt_vencimento/...): o `filter()`
            # com ano e mês juntos (evita "pelo menos um dos dois").
            faturas = faturas.filter(**periodo)
        if filtros:
            faturas = faturas.filter(**filtros)
        faturas = faturas.distinct()

        # 2) Filtros da barra lateral (`list_filter`), com o valor da URL.
        # As instâncias do `filter_specs` foram criadas com `lookup_params`
        # VAZIO (o `get_filters_params` deste ChangeList devolve {} antes de
        # `self.request` existir) — então os valores dos `used_parameters`
        # são reidratados aqui, a partir do GET.
        instancias = {type(f): f for f in getattr(self, 'filter_specs', [])
                      if not isinstance(f, (list, tuple))}
        for espec in admin.get_list_filter(request):
            if isinstance(espec, (list, tuple)):
                continue  # filtro de campo do modelo da BAIXA
            filtro = instancias.get(espec)
            if filtro is None:
                filtro = espec(request, request.GET.copy(), admin,
                               self.model, admin)
            else:
                filtro.used_parameters = {
                    espec.parameter_name: request.GET.get(espec.parameter_name)
                } if espec.parameter_name in request.GET else {}
            atual = faturas
            faturas = filtro.queryset(request, atual)
            if faturas is None:
                # Filtro sem recorte (ex.: `status` sem valor válido): a
                # listagem é uma TELA, não pode ficar vazia "do nada".
                faturas = atual
        return faturas.distinct()

    # ------------------------------------------------------------------
    # Forms: um BaixaFatura novo por fatura
    # ------------------------------------------------------------------
    def forms_das_faturas(self):
        if self._forms is not None:
            return self._forms

        from admin_faturas.forms import BaixaFaturaForm

        form_class = BaixaFaturaForm
        enviado = self.request.method == 'POST'
        forms = []
        for indice, fatura in enumerate(self.faturas_pendentes()):
            # Só as colunas editáveis da baixa: a cópia herdada da fatura não
            # entra no form (a linha já exibe os dados da fatura e a cópia é
            # preenchida no save). Sem isto o `fields='__all__'` do
            # `BaixaFaturaForm` exigiria no POST os campos herdados, que não
            # são enviados pela listagem.
            kwargs = {
                'prefix': f'form-{indice}',
                'instance': self._baixa_nova(fatura),
                'fatura_origem': fatura,
                'fields': list(self.model_admin.list_editable),
            }
            if enviado:
                kwargs['data'] = self.request.POST
                kwargs['files'] = self.request.FILES
            form = form_class(**kwargs)
            forms.append(form)
            self._forms_por_pk[fatura.pk] = form

        self._forms = forms
        return forms

    def _baixa_nova(self, fatura):
        baixa = self.model(
            # Sem fatura: o M2M (`fatura_baixada`) só pode ser gravado depois
            # que a baixa existe. No POST o formset traz o hidden
            # `fatura_baixada`; no GET, o `initial` do form (ver
            # `BaixaFaturaForm.__init__`) mostra a fatura da linha.
            estabelecimento_baixa=fatura.estabelecimento,
            estabelecimento=fatura.estabelecimento,
            us_registro=fatura.us_registro,
            us_registro_baixa=fatura.us_registro,
        )
        return baixa

    # ------------------------------------------------------------------
    # Renderização
    # ------------------------------------------------------------------
    def linhas_renderizadas(self):
        forms = self.forms_das_faturas()
        for fatura, form in zip(self.faturas_pendentes(), forms):
            yield form, self.linha_fatura(fatura, form), fatura.pk

    def linha_fatura(self, fatura, form=None):
        """Células da linha: widget da baixa ou dado da própria fatura."""
        celulas = []
        admin = self.model_admin
        editaveis = set(admin.list_editable)
        aviso = fatura.motivo_recusa_exclusao() or ''
        # Linha travada pelo FLUXO (fatura finalizada / com baixa): nenhum
        # widget — a linha inteira é somente leitura.
        travada = self.motivo_edicao(fatura) or ''
        for indice, field_name in enumerate(self.colunas_efetivas()):
            eh_link = self._eh_link(indice, field_name)
            dica = aviso if self._eh_coluna_pk(field_name) else ''
            if travada and self._eh_coluna_pk(field_name):
                dica = travada

            # Só os campos exclusivos da baixa entram como widget.
            if (not eh_link and form is not None and not travada
                    and field_name in editaveis
                    and field_name in getattr(form, 'fields', {})):
                bf = form[field_name]
                celulas.append(_Celula(
                    mark_safe(str(bf.errors) + str(bf)), False, bf))
                continue

            # Coluna de AÇÃO (ex.: `excluir_button`): o método do ModelAdmin
            # devolve HTML e NÃO recebe a fatura do lugar do modelo listado.
            if callable(getattr(admin, field_name, None)):
                try:
                    conteudo_acao = getattr(admin, field_name)(fatura)
                except Exception:
                    conteudo_acao = '-'
                celulas.append(_Celula(conteudo_acao))
                continue

            celulas.append(_Celula(
                self._valor_da_fatura(fatura, field_name,
                                      link=eh_link and fatura.pk is not None),
                exclusao=dica))
        return celulas

    def _valor_da_fatura(self, fatura, field_name, link=False):
        admin = self.model_admin
        empty = admin.get_empty_value_display()
        # Coluna EXCLUSIVA da baixa (ex.: `valor_baixa`) numa linha de FATURA
        # travada: não há o que mostrar — sai o vazio (antes levantava
        # AttributeError e derrubava a listagem).
        if not hasattr(fatura, field_name) and not hasattr(admin, field_name):
            return empty
        try:
            f, attr, value = lookup_field(field_name, fatura, admin)
        except (ObjectDoesNotExist, FieldDoesNotExist, AttributeError):
            return empty

        if f is None or f.auto_created:
            conteudo = display_for_value(
                value, empty, getattr(attr, 'boolean', False))
        elif isinstance(f.remote_field, models.ManyToOneRel):
            valor = getattr(fatura, f.name)
            conteudo = empty if valor is None else valor
        else:
            conteudo = display_for_field(value, f, empty)

        if link:
            try:
                url = add_preserved_filters(
                    {'preserved_filters': self.preserved_filters,
                     'opts': self.opts},
                    self._url_da_fatura(fatura))
            except NoReverseMatch:
                return conteudo
            return format_html('<a href="{}">{}</a>', url, conteudo)
        return conteudo

    def ids_da_listagem(self):
        """PKs da PÁGINA atual — o que os checkboxes da tabela enviam.

        A tabela é montada no servidor (`linhas_renderizadas`) e o Django só
        gera o checkbox quando o `result_list` do ChangeList tem os objetos.
        Aqui as linhas são FATURAS (no admin de Baixa de Faturas), então os
        checkboxes levam o pk da FATURA e este método precisa devolver os
        mesmos pks.
        """
        return [fatura.pk for fatura in self.faturas_pendentes()]



    def _url_da_fatura(self, fatura):
        """URL do admin da FATURA (a linha listada é uma fatura)."""
        from django.urls import reverse

        opts = fatura._meta
        return reverse(
            f'admin:{opts.app_label}_{opts.model_name}_change',
            args=[fatura.pk])
