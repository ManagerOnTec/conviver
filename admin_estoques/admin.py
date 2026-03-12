from smart_selects.form_fields import ChainedModelChoiceField
from django.contrib import admin
from .models import Categoria, Grupo, Classe, SubClasse, TipoProduto, Produto, UnidadeMedida
from dominios.utils import StatusFilterAdminMixin, ExportToXLSMixin
from .forms import CategoriaForm, GrupoForm, ClasseForm, SubClasseForm, TipoProdutoForm, ProdutoForm, UnidadeMedidaForm
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


class ProdutoAdmin(ExportToXLSMixin, BaseModelAdmin):
    form = ProdutoForm

    actions = ['export_as_xls']
    
    autocomplete_fields = ['classe',]

    list_display = ('id', 'descricao', 'unidade_medida', 'principio_ativo', 'produto_referencia',
                    'pode_ser_prescrito', 'grupo', 'get_grupo_prescricao', 'classe', 'subclasse', 'categoria', 'status')

    search_fields = ['id', 'descricao', 'unidade_medida']
    list_display_links = ['id', 'descricao', ]
    list_editable = ['status']

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


admin.site.register(TipoProduto, TipoProdutoAdmin)
admin.site.register(Grupo, GrupoAdmin)
admin.site.register(Classe, ClasseAdmin)
admin.site.register(SubClasse, SubClasseAdmin)
admin.site.register(Categoria, CategoriaAdmin)
admin.site.register(UnidadeMedida, UnidadeMedidaAdmin)
admin.site.register(Produto, ProdutoAdmin)
