from smart_selects.form_fields import ChainedModelChoiceField
from django.contrib import admin
from django.db import models
from .models import Categoria, Grupo, Classe, SubClasse, TipoProduto, Produto, UnidadeMedida, ViaAdministracao
from dominios.utils import StatusFilterAdminMixin, ExportToXLSMixin
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
            referer_path = request.META['HTTP_REFERER'].split(
                request.META['HTTP_HOST'])[1]
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


class GrupoAdmin(ExportToXLSMixin, BaseModelAdmin):
    form = GrupoForm

    actions = ['export_as_xls']

    list_display = ('id', 'descricao', 'grupo_de_medicamento', 'pode_ser_prescrito', 'grupo_de_medicamento', 'tipo_produto',
                    'status', 'dt_registro', 'us_registro', 'dt_atualizacao', 'us_atualizacao')

    list_display_links = ['id', 'descricao', ]
    search_fields = ['id', 'descricao', ]


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


class ProdutoAdmin(ExportToXLSMixin, BaseModelAdmin):
    form = ProdutoForm

    actions = ['export_as_xls']

    change_list_template = 'admin_estoques/produto/change_list.html'

    autocomplete_fields = ['classe',]

    list_display = ('id', 'descricao', 'unidade_medida_descricao', 'via', 'principio_ativo', 'produto_referencia',
                    'pode_ser_prescrito', 'grupo', 'get_grupo_prescricao', 'classe', 'subclasse', 'categoria', 'status')

    search_fields = ['id', 'descricao', 'unidade_medida__unidade_medida',
                     'unidade_medida__descricao']
    list_display_links = ['id', 'descricao', ]
    list_editable = ['status']

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
