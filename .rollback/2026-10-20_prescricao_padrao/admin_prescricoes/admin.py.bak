
# Importe o modelo de onde ele estiver
from django.core.exceptions import ValidationError
from .models import ParametrosPrescricao
from django.utils import timezone
from django.contrib import admin
from dominios.utils import StatusFilterAdminMixin
from admin_prescricoes.forms import HorasRestritoPrescricaoForm, InicioPlanoTerapeuticoForm, IntervaloHorasForm, ParametrosPrescricaoForm
from prontuarios.models import Prescricao, ProdutoPrescricao, Adep
from .models import HorarioRestritoPrescricao, InicioPlanoTerapeutico, IntervaloHoras, ParametrosPrescricao
from django.apps import apps


class InicioPlanoTerapeuticoAdmin(admin.ModelAdmin):
    form = InicioPlanoTerapeuticoForm

    list_display = ('id', 'hora_inicio', 'padrao', 'estabelecimento', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')
    # Usando ChoicesFieldListFilter para permitir um valor padrão
    list_filter = (StatusFilterAdminMixin, 'estabelecimento',
                   'dt_registro', 'us_registro')
    search_fields = ['id', ]
    list_display_links = ['id', 'hora_inicio']
    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']
    list_editable = ['status', 'padrao']
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
                queryset = queryset.filter(status='A')

        return queryset, use_distinct

    def save_model(self, request, obj, form, change):
        if not change:  # se estiver criando um novo objeto
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:  # se estiver editando um objeto existente
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()

        super().save_model(request, obj, form, change)


class IntervaloHorasAdmin(admin.ModelAdmin):
    form = IntervaloHorasForm

    list_display = ('id', 'intervalo_horas', 'padrao', 'estabelecimento', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')
    # Usando ChoicesFieldListFilter para permitir um valor padrão
    list_filter = (StatusFilterAdminMixin, 'estabelecimento',
                   'dt_registro', 'us_registro')
    search_fields = ['id', ]
    list_display_links = ['id', 'intervalo_horas']
    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']
    list_editable = ['status', 'padrao']
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
                queryset = queryset.filter(status='A')

        return queryset, use_distinct

    def save_model(self, request, obj, form, change):
        if not change:  # se estiver criando um novo objeto
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:  # se estiver editando um objeto existente
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()

        super().save_model(request, obj, form, change)


class HorarioRestritoPrescricaoAdmin(admin.ModelAdmin):
    form = HorasRestritoPrescricaoForm

    list_display = ('id', 'hora_inicio', 'hora_final', 'estabelecimento', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')
    # Usando ChoicesFieldListFilter para permitir um valor padrão
    list_filter = (StatusFilterAdminMixin, 'estabelecimento',
                   'dt_registro', 'us_registro')
    search_fields = ['id', ]
    list_display_links = ['id', 'hora_inicio', 'hora_final']
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
                queryset = queryset.filter(status='A')

        return queryset, use_distinct

    def save_model(self, request, obj, form, change):
        if not change:  # se estiver criando um novo objeto
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:  # se estiver editando um objeto existente
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()

        super().save_model(request, obj, form, change)


class ParametrosPrescricaoAdmin(admin.ModelAdmin):
    form = ParametrosPrescricaoForm

    list_display = ('id', 'profissao', 'profissional',
                    'dias', 'permite_prescricao_retroativa', 'permite_editar_outras', 'permite_suspender_outras', 'estabelecimento', 'status',)

    list_display_links = ('id', 'profissao', 'profissional',)

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


admin.site.register(InicioPlanoTerapeutico, InicioPlanoTerapeuticoAdmin)
admin.site.register(IntervaloHoras, IntervaloHorasAdmin)
admin.site.register(HorarioRestritoPrescricao, HorarioRestritoPrescricaoAdmin)
admin.site.register(ParametrosPrescricao, ParametrosPrescricaoAdmin)
