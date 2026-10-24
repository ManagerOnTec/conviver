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
from django.contrib.admin.views.main import ChangeList
from django.contrib.admin.utils import (
    display_for_field,
    display_for_value,
    label_for_field,
    lookup_field,
)
from django.core.exceptions import FieldDoesNotExist, ObjectDoesNotExist
from django.db import models
from django.urls import NoReverseMatch
from django.utils.html import format_html
from django.utils.safestring import mark_safe


class _Celula:
    """Uma célula já renderizada (texto/HTML) de uma coluna da listagem."""

    __slots__ = ("contents", "is_link", "field")

    def __init__(self, contents, is_link=False, field=None):
        self.contents = contents
        self.is_link = is_link
        self.field = field


class ChangeListEditavel(ChangeList):
    """ChangeList que entrega à listagem TODAS as colunas do `list_display`.

    Cabeçalho e células percorrem a MESMA lista de colunas efetivas, na mesma
    ordem. Uma única coluna fora de sincronia (a mais, ou a menos) desloca todos
    os títulos seguintes — é o que acontece quando `result_headers` gera um
    header a mais (ver `colunas_efetivas`).
    """

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

    def linha_renderizada(self, obj, form=None):
        """Lista de _Celula, uma por item de `list_display`."""
        admin = self.model_admin
        celulas = []

        colunas = self.colunas_efetivas()
        for indice, field_name in enumerate(colunas):
            eh_link = self._eh_link(indice, field_name)
            conteudo = self._valor_da_coluna(obj, field_name)

            # Coluna editável: usa o widget do formset (mantém o POST).
            if (not eh_link and form is not None
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
                    celulas.append(_Celula(conteudo))
                    continue
                from django.contrib.admin.templatetags.admin_urls import (
                    add_preserved_filters,
                )
                url = add_preserved_filters(
                    {"preserved_filters": self.preserved_filters,
                     "opts": self.opts}, url)
                attr_pk = str(self.to_field) if self.to_field else self.model._meta.pk.attname
                serial = obj.serializable_value(attr_pk)
                conteudo = format_html(
                    '<a href="{}">{}</a>', url, conteudo,
                )
                celulas.append(_Celula(conteudo, True))
            else:
                celulas.append(_Celula(conteudo))

        return celulas

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
