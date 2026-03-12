from dominios.utils import StatusFilterAdminMixin
from django.contrib import admin
from django.utils import timezone
from dominios.utils import StatusFilterAdminMixin
from .models import ParametrosDiagnostico
from django.core.exceptions import ValidationError
from .forms import ParametrosDiagnosticoAdminForm


class ParametrosDiagnosticoAdmin(admin.ModelAdmin):
    form = ParametrosDiagnosticoAdminForm

    list_editable = ['status']

    list_display = ('id', 'profissional', 'profissao', 'estabelecimento',
                    'status', 'dt_registro', 'us_registro', 'dt_atualizacao', 'us_atualizacao')
    # Usando ChoicesFieldListFilter para permitir um valor padrão
    list_filter = (StatusFilterAdminMixin,
                   'dt_registro', 'us_registro')
    search_fields = ['id', 'profissional', 'profissao', 'estabelecimento']
    list_display_links = ['id', 'profissional', 'profissao']
    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']
    list_editable = ['status']
    ordering = ['-pk',]

    list_per_page = 11

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


admin.site.register(ParametrosDiagnostico, ParametrosDiagnosticoAdmin)
