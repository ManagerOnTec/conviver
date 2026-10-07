from .forms import TextoDocumentoPadraoForm
from .models import TextoDocumentoPadrao
from django.contrib import admin
from .models import GerenciadorRelatorioGeral, GerenciadorRelatorioPersonalizado
from .forms import GerenciadorRelatorioGeralForm, GerenciadorRelatorioPersonalizadoForm
from django.utils import timezone


@admin.register(GerenciadorRelatorioGeral)
class GerenciadorRelatorioGeralAdmin(admin.ModelAdmin):
    form = GerenciadorRelatorioGeralForm
    list_display = ('dados_header', 'dados_right_header',
                    'dados_footer', 'estabelecimento', 'status')
    list_filter = ('estabelecimento', 'status')
    search_fields = ('dados_header', 'dados_footer')
    # Adicione mais configurações conforme necessário

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)

        # Verifica se a solicitação veio de um campo de autocomplete
        if 'HTTP_REFERER' in request.META:
            referer_path = request.META['HTTP_REFERER'].split(
                request.META['HTTP_HOST'])[1]
            if '/add/' in referer_path or '/change/' in referer_path:
                # Se a solicitação veio de um campo de autocomplete, filtra os objetos inativos
                print('DEBUG: The request came from an autocomplete field')
                queryset = queryset.filter(status='A')

        return queryset, use_distinct

    def save_model(self, request, obj, form, change):
        if not change:  # se estiver criando um novo objeto
            print('DEBUG: Creating a new object')
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:  # se estiver editando um objeto existente
            print('DEBUG: Editing an existing object')
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()

        super().save_model(request, obj, form, change)


@admin.register(GerenciadorRelatorioPersonalizado)
class GerenciadorRelatorioPersonalizadoAdmin(admin.ModelAdmin):
    form = GerenciadorRelatorioPersonalizadoForm
    list_display = ('relatorio', 'tipo_evolucao', 'tipo_documento_legal', 'dados_header',
                    'dados_right_header', 'dados_footer', 'estabelecimento', 'status')
    list_filter = ('relatorio', 'tipo_evolucao', 'tipo_documento_legal', 'estabelecimento', 'status')
    search_fields = ('dados_header', 'dados_footer')
    # Adicione mais configurações conforme necessário

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)

        # Verifica se a solicitação veio de um campo de autocomplete
        if 'HTTP_REFERER' in request.META:
            referer_path = request.META['HTTP_REFERER'].split(
                request.META['HTTP_HOST'])[1]
            if '/add/' in referer_path or '/change/' in referer_path:
                # Se a solicitação veio de um campo de autocomplete, filtra os objetos inativos
                print('DEBUG: The request came from an autocomplete field')
                queryset = queryset.filter(status='A')

        return queryset, use_distinct

    def save_model(self, request, obj, form, change):
        if not change:  # se estiver criando um novo objeto
            print('DEBUG: Creating a new object')
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:  # se estiver editando um objeto existente
            print('DEBUG: Editing an existing object')
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()

        super().save_model(request, obj, form, change)


class TextoDocumentoPadraoAdmin(admin.ModelAdmin):
    form = TextoDocumentoPadraoForm
    list_display = ('descricao', 'tipo', 'status',
                    'dt_registro', 'us_registro')
    list_filter = ('tipo', 'status')
    search_fields = ('descricao', 'texto')
    readonly_fields = ('dt_registro', 'us_registro',
                       'dt_atualizacao', 'us_atualizacao')

    def save_model(self, request, obj, form, change):
        if not obj.us_registro_id:
            obj.us_registro = request.user
        obj.us_atualizacao = request.user
        super().save_model(request, obj, form, change)


admin.site.register(TextoDocumentoPadrao, TextoDocumentoPadraoAdmin)
