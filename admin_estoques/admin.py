from smart_selects.form_fields import ChainedModelChoiceField
from django.contrib import admin
from django.db import models
from .models import Categoria, Grupo, Classe, SubClasse, TipoProduto, Produto, UnidadeMedida, ViaAdministracao
from dominios.utils import StatusFilterAdminMixin, ExportToXLSMixin
from dominios.admin_dashboard_mixins import AdminDashboardAndTopFilterMixin
from .forms import CategoriaForm, GrupoForm, ClasseForm, SubClasseForm, TipoProdutoForm, ProdutoForm, UnidadeMedidaForm, ViaAdministracaoForm
from django.utils import timezone


class BaseModelAdmin(admin.ModelAdmin):
    # Incluindo alguns dos métodos comuns aqui para evitar duplicação

    list_display = ('id', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')
    list_filter = (StatusFilterAdminMixin, 'dt_registro', 'us_registro')
    search_fields = ['id', ]
    list_display_links = ['id', ]
    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']
    list_editable = ['status']
    ordering = ['-pk',]
    list_per_page = 11

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)

        if 'HTTP_REFERER' in request.META:
            # HTTP_HOST pode estar ausente (ex.: alguns clientes ajax) — não
            # pode derrubar a busca; deriva o path direto do referer.
            from urllib.parse import urlparse
            referer_path = urlparse(request.META['HTTP_REFERER']).path
            if '/add/' in referer_path or '/change/' in referer_path:
                queryset = queryset.filter(status='A')

        return queryset, use_distinct

    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:  # Editing existing object
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()

        super().save_model(request, obj, form, change)


class TipoProdutoAdmin(ExportToXLSMixin, BaseModelAdmin):
    form = TipoProdutoForm

    actions = ['export_as_xls']

    list_display = ('id', 'descricao', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')
    list_display_links = ['id', 'descricao', ]
    search_fields = ['id', 'descricao', ]


class GrupoAdmin(AdminDashboardAndTopFilterMixin, ExportToXLSMixin,
                 BaseModelAdmin):
    form = GrupoForm

    actions = ['export_as_xls']

    dashboard_date_field = 'dt_registro'

    list_display = ('id', 'descricao', 'tipo_produto', 'grupo_de_medicamento',
                    'pode_ser_prescrito', 'qtd_produtos',
                    'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')

    list_display_links = ['id', 'descricao', ]
    search_fields = ['id', 'descricao', ]

    # A listagem padrão do Grupo já tem `list_editable` (herdado): precisa
    # do ChangeListEditavel, senão o template quebra em
    # `linhas_renderizadas`.
    def get_changelist(self, request, **kwargs):
        from admin_faturas.changelist_editavel import ChangeListEditavel
        return ChangeListEditavel

    def get_linhas_nao_editaveis(self, request):
        return set()

    def get_queryset(self, request):
        # `qtd_produtos` no list_display: anota em vez de contar por linha
        # (1 consulta para a página inteira, não N).
        queryset = super().get_queryset(request).select_related(
            'tipo_produto').annotate(
            _qtd_produtos=models.Count('produto'))

        # Recortes do topo (combináveis).
        tipo = request.GET.get('tipo_produto')
        if tipo:
            queryset = queryset.filter(tipo_produto_id=tipo)
        if request.GET.get('medicamento') == 'sim':
            queryset = queryset.filter(grupo_de_medicamento=True)
        if request.GET.get('prescritivel') == 'sim':
            queryset = queryset.filter(pode_ser_prescrito=True)
        return queryset

    @admin.display(description='Produtos', ordering='_qtd_produtos')
    def qtd_produtos(self, obj):
        return obj._qtd_produtos

    def _url_com(self, request, **mudancas):
        params = request.GET.copy()
        params.pop('p', None)
        for chave, valor in mudancas.items():
            if valor in (None, ''):
                params.pop(chave, None)
            else:
                params[chave] = valor
        return f'{request.path}?{params.urlencode()}' if params else request.path

    def get_top_filter_presets(self, request):
        """Presets por TIPO DE PRODUTO (a hierarquia do grupo)."""
        tipo = request.GET.get('tipo_produto')
        params = request.GET.copy()
        params.pop('p', None)
        params.pop('tipo_produto', None)
        presets = [{'label': 'Todos os tipos',
                    'url': f'{request.path}?{params.urlencode()}'
                           if params else request.path,
                    'active': not tipo}]
        for tp in TipoProduto.objects.filter(status='A').order_by('descricao'):
            presets.append({
                'label': tp.descricao,
                'url': self._url_com(request, tipo_produto=tp.pk),
                'active': str(tipo) == str(tp.pk),
            })
        return presets

    def get_top_extra_filters(self, request):
        med = request.GET.get('medicamento')
        presc = request.GET.get('prescritivel')
        return [
            {'label': 'Todos', 'url': self._url_com(
                request, medicamento=None, prescritivel=None),
             'active': not med and not presc, 'icon': 'fa-list'},
            {'label': 'Medicamentos', 'url': self._url_com(
                request, medicamento='sim'),
             'active': med == 'sim', 'icon': 'fa-pills'},
            {'label': 'Prescritíveis', 'url': self._url_com(
                request, prescritivel='sim'),
             'active': presc == 'sim', 'icon': 'fa-prescription'},
        ]

    top_extra_filter_label = 'Tipo & Prescrição'

    def get_top_dropdown_subfilters(self, request):
        """Select de TIPO DE PRODUTO + botão de limpar (preserva o resto)."""
        tipo_atual = request.GET.get('tipo_produto')
        opcoes = [{'value': self._url_com(request, tipo_produto=None),
                   'label': 'Todos os tipos', 'selected': not tipo_atual}]
        for tp in TipoProduto.objects.filter(status='A').order_by('descricao'):
            opcoes.append({
                'value': self._url_com(request, tipo_produto=tp.pk),
                'label': tp.descricao,
                'selected': str(tipo_atual) == str(tp.pk),
            })
        params = request.GET.copy()
        params.pop('p', None)
        for chave in ('tipo_produto', 'medicamento', 'prescritivel'):
            params.pop(chave, None)
        return [
            {'label': 'Tipo de produto', 'options': opcoes},
            {'label': 'Limpar filtros do topo', 'is_clear': True,
             'options': [{'value': f'{request.path}?{params.urlencode()}'
                                   if params else request.path,
                          'label': 'Limpar todos os filtros',
                          'selected': False}]},
        ]

    def get_list_filter(self, request):
        from admin_cadastros.admin import ParametroTopoFilter
        extras = [ParametroTopoFilter.para('tipo_produto'),
                  ParametroTopoFilter.para('medicamento'),
                  ParametroTopoFilter.para('prescritivel')]
        return list(super().get_list_filter(request)) + extras

    def get_dashboard_kpis(self, request, queryset):
        def _qtd(valor):
            return f'{int(valor or 0):,}'.replace(',', '.')

        total = queryset.count()
        ativos = queryset.filter(status='A').count()
        med = queryset.filter(grupo_de_medicamento=True).count()
        presc = queryset.filter(pode_ser_prescrito=True).count()
        vazios = queryset.annotate(n=models.Count('produto')).filter(n=0).count()

        return [
            {'title': 'Grupos', 'value': _qtd(total),
             'subtitle': f'{_qtd(ativos)} ativos',
             'color_class': 'kpi-blue', 'icon': 'fa-layer-group'},
            {'title': 'Medicamentos', 'value': _qtd(med),
             'subtitle': f'{_qtd(total - med)} materiais/outros',
             'color_class': 'kpi-green', 'icon': 'fa-pills'},
            {'title': 'Prescritíveis', 'value': _qtd(presc),
             'subtitle': 'Grupos liberados para prescrição',
             'color_class': 'kpi-purple', 'icon': 'fa-prescription'},
            {'title': 'Sem produtos', 'value': _qtd(vazios),
             'subtitle': 'Grupos sem nenhum produto vinculado',
             'color_class': 'kpi-orange', 'icon': 'fa-inbox'},
        ]

    top_filter_search_label = 'Busca'
    top_filter_search_placeholder = 'Descrição do grupo...'


class ClasseAdmin(ExportToXLSMixin, BaseModelAdmin):
    form = ClasseForm

    actions = ['export_as_xls']

    list_display = ('id', 'descricao', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')

    list_display_links = ['id', 'descricao', ]
    search_fields = ['id', 'descricao', ]


class SubClasseAdmin(ExportToXLSMixin, BaseModelAdmin):
    form = SubClasseForm

    actions = ['export_as_xls']

    list_display = ('id', 'descricao', 'classe', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')

    list_display_links = ['id', 'descricao', ]
    search_fields = ['id', 'descricao', ]


class CategoriaAdmin(ExportToXLSMixin, BaseModelAdmin):
    form = CategoriaForm

    actions = ['export_as_xls']

    list_display = ('id', 'descricao', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')

    list_display_links = ['id', 'descricao', ]
    search_fields = ['id', 'descricao', ]


class UnidadeMedidaAdmin(ExportToXLSMixin, BaseModelAdmin):
    form = UnidadeMedidaForm

    actions = ['export_as_xls']

    list_display = ('id', 'unidade_medida', 'descricao', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')

    list_display_links = ['id', 'unidade_medida', ]
    search_fields = ['id', 'unidade_medida', 'descricao']


class ViaAdministracaoAdmin(ExportToXLSMixin, BaseModelAdmin):
    form = ViaAdministracaoForm

    actions = ['export_as_xls']

    list_display = ('id', 'codigo', 'descricao', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')

    list_display_links = ['id', 'descricao', ]
    search_fields = ['id', 'codigo', 'descricao']


class ProdutoAdmin(AdminDashboardAndTopFilterMixin, ExportToXLSMixin,
                   BaseModelAdmin):
    form = ProdutoForm

    actions = ['export_as_xls']

    change_list_template = 'admin_estoques/produto/change_list.html'

    autocomplete_fields = ['classe',]

    # A barra de período opera sobre a data de cadastro do produto.
    dashboard_date_field = 'dt_registro'

    # ------------------------------------------------------------------
    # BARRA SUPERIOR: KPIs e filtros por GRUPO/TIPO/CLASSE
    # ------------------------------------------------------------------
    def _url_com(self, request, **mudancas):
        """URL trocando `mudancas` (None remove) e PRESERVANDO o resto."""
        params = request.GET.copy()
        params.pop('p', None)
        for chave, valor in mudancas.items():
            if valor in (None, ''):
                params.pop(chave, None)
            else:
                params[chave] = valor
        query = params.urlencode()
        return f'{request.path}?{query}' if query else request.path

    def _url_sem(self, request, chaves):
        params = request.GET.copy()
        params.pop('p', None)
        for chave in chaves:
            params.pop(chave, None)
        query = params.urlencode()
        return f'{request.path}?{query}' if query else request.path

    def get_top_filter_presets(self, request):
        """Presets por TIPO DE PRODUTO (o eixo mais alto da hierarquia)."""
        tipo = request.GET.get('tipo_produto')
        presets = [{'label': 'Todos os tipos',
                    'url': self._url_sem(request, ('tipo_produto',)),
                    'active': not tipo}]
        for tp in TipoProduto.objects.filter(status='A').order_by('descricao'):
            presets.append({
                'label': tp.descricao,
                'url': self._url_com(request, tipo_produto=tp.pk),
                'active': str(tipo) == str(tp.pk),
            })
        return presets

    def get_top_extra_filters(self, request):
        """Atalhos rápidos: prescritível, medicamento e princípio ativo."""
        def _btn(rotulo, param, valor, ativo, icone):
            # `param=None` = botão “Todos”: limpa os DOIS filtros de uma vez
            # (montar `**{None: ...}` estoura com “keywords must be strings”).
            mudancas = ({'medicamento': None, 'prescritivel': None,
                         'principio_ativo': None}
                        if param is None else {param: valor})
            return {'label': rotulo,
                    'url': self._url_com(request, **mudancas),
                    'active': ativo, 'icon': icone}

        medicamento = request.GET.get('medicamento')
        prescrito = request.GET.get('prescritivel')
        principio = request.GET.get('principio_ativo')
        return [
            _btn('Todos', None, None, True, 'fa-list'),
            _btn('Medicamentos', 'medicamento', 'sim',
                 medicamento == 'sim', 'fa-pills'),
            _btn('Materiais', 'medicamento', 'nao',
                 medicamento == 'nao', 'fa-box'),
            _btn('Prescritíveis', 'prescritivel', 'sim',
                 prescrito == 'sim', 'fa-prescription'),
            _btn('Princípio ativo', 'principio_ativo', 'sim',
                 principio == 'sim', 'fa-flask'),
        ]

    top_extra_filter_label = 'Tipo & Prescrição'

    def get_top_dropdown_subfilters(self, request):
        """Combinações: GRUPO, CLASSE e VIA (cada um preserva os demais)."""
        grupo_atual = request.GET.get('grupo')
        opcoes_grupo = [{'value': self._url_com(request, grupo=None),
                         'label': 'Todos os grupos',
                         'selected': not grupo_atual}]
        for g in (Grupo.objects.filter(status='A')
                  .select_related('tipo_produto').order_by('descricao')):
            opcoes_grupo.append({
                'value': self._url_com(request, grupo=g.pk),
                'label': f'{g.descricao} ({g.tipo_produto.descricao})',
                'selected': str(grupo_atual) == str(g.pk),
            })

        classe_atual = request.GET.get('classe')
        opcoes_classe = [{'value': self._url_com(request, classe=None),
                          'label': 'Todas as classes',
                          'selected': not classe_atual}]
        for c in Classe.objects.filter(status='A').order_by('descricao'):
            opcoes_classe.append({
                'value': self._url_com(request, classe=c.pk),
                'label': c.descricao,
                'selected': str(classe_atual) == str(c.pk),
            })

        via_atual = request.GET.get('via')
        opcoes_via = [{'value': self._url_com(request, via=None),
                       'label': 'Todas as vias',
                       'selected': not via_atual}]
        for v in ViaAdministracao.objects.filter(status='A').order_by('descricao'):
            opcoes_via.append({
                'value': self._url_com(request, via=v.pk),
                'label': v.descricao,
                'selected': str(via_atual) == str(v.pk),
            })

        return [
            {'label': 'Grupo', 'options': opcoes_grupo},
            {'label': 'Classe', 'options': opcoes_classe},
            {'label': 'Via', 'options': opcoes_via},
            {'label': 'Limpar filtros do topo', 'is_clear': True,
             'options': [{'value': self._url_sem(
                 request, ('tipo_produto', 'grupo', 'classe', 'via',
                           'medicamento', 'prescritivel', 'principio_ativo')),
                 'label': 'Limpar todos os filtros', 'selected': False}]},
        ]

    def get_queryset(self, request):
        """Aplica os recortes do topo (combináveis entre si)."""
        queryset = super().get_queryset(request).select_related(
            'grupo', 'grupo__tipo_produto', 'classe', 'via',
            'unidade_medida', 'categoria')

        tipo = request.GET.get('tipo_produto')
        if tipo:
            queryset = queryset.filter(grupo__tipo_produto_id=tipo)

        grupo = request.GET.get('grupo')
        if grupo:
            queryset = queryset.filter(grupo_id=grupo)

        classe = request.GET.get('classe')
        if classe:
            queryset = queryset.filter(classe_id=classe)

        via = request.GET.get('via')
        if via:
            queryset = queryset.filter(via_id=via)

        # “Medicamento” não é campo: vem do GRUPO.
        medicamento = request.GET.get('medicamento')
        if medicamento == 'sim':
            queryset = queryset.filter(grupo__grupo_de_medicamento=True)
        elif medicamento == 'nao':
            queryset = queryset.filter(grupo__grupo_de_medicamento=False)

        # Prescritível = o GRUPO permite OU o produto é exceção marcada.
        prescritivel = request.GET.get('prescritivel')
        if prescritivel == 'sim':
            queryset = queryset.filter(
                models.Q(grupo__pode_ser_prescrito=True)
                | models.Q(pode_ser_prescrito=True))

        if request.GET.get('principio_ativo') == 'sim':
            queryset = queryset.filter(principio_ativo=True)

        return queryset.distinct()

    def get_list_filter(self, request):
        """Declara os parâmetros do topo como filtros próprios.

        Lista vazia não basta (o Django tenta resolver o nome como campo).
        Os filtros abaixo só DECLARAM o parâmetro; o recorte é do
        `get_queryset`, que consegue combinar todos.
        """
        from admin_cadastros.admin import ParametroTopoFilter
        extras = [ParametroTopoFilter.para('tipo_produto'),
                  ParametroTopoFilter.para('medicamento'),
                  ParametroTopoFilter.para('prescritivel'),
                  ParametroTopoFilter.para('principio_ativo')]
        return list(super().get_list_filter(request)) + extras

    def get_dashboard_kpis(self, request, queryset):
        def _qtd(valor):
            return f'{int(valor or 0):,}'.replace(',', '.')

        total = queryset.count()
        ativos = queryset.filter(status='A').count()
        med = queryset.filter(grupo__grupo_de_medicamento=True).count()
        presc = queryset.filter(
            models.Q(grupo__pode_ser_prescrito=True)
            | models.Q(pode_ser_prescrito=True)).count()
        principios = queryset.filter(principio_ativo=True).count()
        grupos = queryset.values('grupo_id').distinct().count()

        return [
            {'title': 'Produtos', 'value': _qtd(total),
             'subtitle': f'{_qtd(ativos)} ativos',
             'color_class': 'kpi-blue', 'icon': 'fa-boxes-stacked'},
            {'title': 'Medicamentos', 'value': _qtd(med),
             'subtitle': f'{_qtd(total - med)} materiais/outros',
             'color_class': 'kpi-green', 'icon': 'fa-pills'},
            {'title': 'Prescritíveis', 'value': _qtd(presc),
             'subtitle': 'Grupo ou produto liberado',
             'color_class': 'kpi-purple', 'icon': 'fa-prescription'},
            {'title': 'Princípios ativos', 'value': _qtd(principios),
             'subtitle': 'Controladores de estoque',
             'color_class': 'kpi-orange', 'icon': 'fa-flask'},
            {'title': 'Grupos no filtro', 'value': _qtd(grupos),
             'subtitle': 'Grupos distintos',
             'color_class': 'kpi-teal', 'icon': 'fa-layer-group'},
        ]

    top_filter_search_label = 'Busca'
    top_filter_search_placeholder = (
        'Descrição do produto, unidade de medida ou princípio ativo...')

    list_display = ('id', 'descricao', 'unidade_medida_descricao', 'via', 'principio_ativo', 'produto_referencia',
                    'pode_ser_prescrito', 'grupo', 'get_grupo_prescricao', 'classe', 'subclasse', 'categoria', 'status')

    search_fields = ['id', 'descricao', 'unidade_medida__unidade_medida',
                     'unidade_medida__descricao']
    list_display_links = ['id', 'descricao', ]
    list_editable = ['status']

    def get_changelist(self, request, **kwargs):
        """Listagem com `list_editable` usa a tabela montada no SERVIDOR.

        O `change_list.html` renderiza `cl.linhas_renderizadas` quando há
        `list_editable`; o `ChangeList` padrão não tem esse atributo. É o
        mesmo `ChangeListEditavel` do fluxo de faturas.
        """
        from admin_faturas.changelist_editavel import ChangeListEditavel
        return ChangeListEditavel

    def get_linhas_nao_editaveis(self, request):
        """Sem regra de fluxo no cadastro → nenhuma linha travada."""
        return set()

    @admin.display(description='Unidade de Medida')
    def unidade_medida_descricao(self, obj):
        return obj.unidade_medida.descricao

    def get_grupo_prescricao(self, obj):
        return obj.grupo.pode_ser_prescrito
    get_grupo_prescricao.boolean = True
    get_grupo_prescricao.short_description = 'Grupo pode ser prescrito?'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'produto_referencia':
            kwargs["queryset"] = Produto.objects.filter(
                produto_referencia__isnull=True, grupo__grupo_de_medicamento=True, status='A')
        elif db_field.name == 'subclasse':
            kwargs["queryset"] = SubClasse.objects.filter(
                status='A')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_search_results(self, request, queryset, search_term):
        """Autocomplete de Produto (usado pela Prescrição Padrão).

        O widget `autocomplete_fields` consulta este ModelAdmin, ignorando o
        queryset do form. Aqui aplicamos dois ajustes, **somente** quando a
        consulta vem da Prescrição Padrão:

        1. **Filtro de prescritibilidade**: só produtos com
           `pode_ser_prescrito=True` ou cujo grupo seja prescritível (mesmo
           critério de `produtos_prescritiveis_queryset`).
        2. **Busca pelo nome do comercial vinculado**: o `__str__` do genérico
           mostra ``Midazolam→ Dormonid / ...``, mas o `search_fields` apenas
           cobre `descricao` ("Midazolam"). Pesquisar por "Dormonid" encontrava
           o **comercial** (não prescritível) e não o genérico. Agora a busca
           também considera `produto_referencia__descricao` e o comercial é
           descartado, permanecendo o genérico prescritível que o referencia.
        """
        if not self._autocomplete_origem_prescricao_padrao(request):
            return super().get_search_results(request, queryset, search_term)

        prescritivel = models.Q(pode_ser_prescrito=True) | models.Q(
            grupo__pode_ser_prescrito=True)

        termo = (search_term or '').strip()
        if not termo:
            return queryset.filter(prescritivel).distinct(), False

        # Recalcula a partir do queryset original (o `super()` filtra por
        # `search_fields`, que não conhece o comercial vinculado).
        # Mantém também os campos originais de busca (unidade de medida) e o id.
        casam = Produto.objects.filter(
            models.Q(descricao__icontains=termo)
            | models.Q(produto_referencia__descricao__icontains=termo)
            | models.Q(unidade_medida__unidade_medida__icontains=termo)
            | models.Q(unidade_medida__descricao__icontains=termo)
        )
        if termo.isdigit():
            casam = casam | Produto.objects.filter(pk=int(termo))

        ids_prescritiveis = set(casam.filter(prescritivel).values_list('pk', flat=True))
        # Comerciais (não prescritíveis) vinculados a um genérico prescritível
        # encontrado são omitidos: o usuário escolhe o genérico.
        ids_comerciais_vinculados = set(casam.filter(
            pk__in=Produto.objects.filter(
                produto_referencia__in=ids_prescritiveis,
            ).values_list('pk', flat=True),
        ).values_list('pk', flat=True))

        ids = ids_prescritiveis - ids_comerciais_vinculados
        resultado = Produto.objects.filter(pk__in=ids)

        # Mantém eventuais filtros do queryset recebido (ex.: status).
        resultado = resultado.filter(pk__in=queryset.values('pk'))
        return resultado.distinct(), False

    @staticmethod
    def _autocomplete_origem_prescricao_padrao(request):
        """True quando o autocomplete foi aberto a partir da Prescrição Padrão.

        O Django envia o parâmetro ``field_name`` (ex.: ``produtos-0-produto``)
        e o ``Referer`` da página de origem.
        """
        referer = request.META.get('HTTP_REFERER', '')
        if 'prescricaopadrao' in referer:
            return True
        # Fallback: o formulário-pai informa o prefixo do formset
        field_name = request.GET.get('field_name', '')
        return field_name.startswith('produtos-')



admin.site.register(TipoProduto, TipoProdutoAdmin)
admin.site.register(Grupo, GrupoAdmin)
admin.site.register(Classe, ClasseAdmin)
admin.site.register(SubClasse, SubClasseAdmin)
admin.site.register(Categoria, CategoriaAdmin)
admin.site.register(UnidadeMedida, UnidadeMedidaAdmin)
admin.site.register(ViaAdministracao, ViaAdministracaoAdmin)
admin.site.register(Produto, ProdutoAdmin)
