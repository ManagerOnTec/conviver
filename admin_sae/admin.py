from django.contrib import admin
from .models import (Aspecto, AspectoAnalisado, Evidencia,
                     DiagnosticoEnfermagem, FatorRelacionado, Intervencao, ParametrosSAE)
from dominios.utils import StatusFilterAdminMixin, ExportToXLSMixin
from .forms import (AspectoForm, AspectoAnalisadoForm, EvidenciaForm,
                    DiagnosticoEnfermagemForm, FatorRelacionadoForm, IntervencaoForm, ParametrosSAEForm)
from django.utils import timezone
from admin_cadastros_assistenciais.models import Profissao


class AspectoAdmin(ExportToXLSMixin, admin.ModelAdmin):
    form = AspectoForm

    actions = ['export_as_xls']

    list_display = ('id', 'descricao', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')
    # Usando ChoicesFieldListFilter para permitir um valor padrão
    list_filter = (StatusFilterAdminMixin, 'dt_registro', 'us_registro')
    search_fields = ['id', 'descricao', ]
    list_display_links = ['id', 'descricao', ]
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


class AspectoAnalisadoAdmin(ExportToXLSMixin, admin.ModelAdmin):
    form = AspectoAnalisadoForm

    actions = ['export_as_xls']

    list_display = ('id', 'descricao', 'aspecto', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')
    # Usando ChoicesFieldListFilter para permitir um valor padrão
    list_filter = (StatusFilterAdminMixin, 'aspecto',
                   'dt_registro', 'us_registro')
    search_fields = ['id', 'descricao', ]
    list_display_links = ['id', 'descricao', ]
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


class EvidenciaAdmin(ExportToXLSMixin, admin.ModelAdmin):
    form = EvidenciaForm

    actions = ['export_as_xls']

    list_display = ('id', 'descricao', 'aspecto_analisado', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')
    # Usando ChoicesFieldListFilter para permitir um valor padrão
    list_filter = (StatusFilterAdminMixin, 'aspecto_analisado',
                   'dt_registro', 'us_registro')
    search_fields = ['id', 'descricao', ]
    list_display_links = ['id', 'descricao', ]
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


class DiagnosticoEnfermagemAdmin(ExportToXLSMixin, admin.ModelAdmin):
    form = DiagnosticoEnfermagemForm

    actions = ['export_as_xls']

    list_display = ('id', 'descricao', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')
    # Usando ChoicesFieldListFilter para permitir um valor padrão
    list_filter = (StatusFilterAdminMixin, 'evidencia',
                   'dt_registro', 'us_registro')
    search_fields = ['id', 'descricao', ]
    list_display_links = ['id', 'descricao', ]
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


class FatorRelacionadoAdmin(ExportToXLSMixin, admin.ModelAdmin):
    form = FatorRelacionadoForm

    actions = ['export_as_xls']

    list_display = ('id', 'descricao', 'diagnostico_enfermagem', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')
    # Usando ChoicesFieldListFilter para permitir um valor padrão
    list_filter = (StatusFilterAdminMixin,
                   'diagnostico_enfermagem', 'dt_registro', 'us_registro')
    search_fields = ['id', 'descricao', ]
    list_display_links = ['id', 'descricao', ]
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


class IntervencaoAdmin(ExportToXLSMixin, admin.ModelAdmin):
    form = IntervencaoForm

    actions = ['export_as_xls']

    list_display = ('id', 'descricao', 'fator_relacionado', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')
    # Usando ChoicesFieldListFilter para permitir um valor padrão
    list_filter = (StatusFilterAdminMixin, 'fator_relacionado',
                   'dt_registro', 'us_registro')
    search_fields = ['id', 'descricao', ]
    list_display_links = ['id', 'descricao', ]
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


class ParametrosSAEAdmin(ExportToXLSMixin, admin.ModelAdmin):
    form = ParametrosSAEForm

    actions = ['export_as_xls']

    list_display = ('id', 'profissao', 'profissional', 'estabelecimento',
                    'status', 'dt_registro', 'us_registro', 'dt_atualizacao', 'us_atualizacao')
    # Usando ChoicesFieldListFilter para permitir um valor padrão
    list_filter = (StatusFilterAdminMixin,
                   'dt_registro', 'us_registro')
    search_fields = ['id', 'profissao', 'profissional', 'estabelecimento']
    list_display_links = ['id', 'profissao', 'profissional']
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


admin.site.register(Aspecto, AspectoAdmin)
admin.site.register(AspectoAnalisado, AspectoAnalisadoAdmin)
admin.site.register(Evidencia, EvidenciaAdmin)
admin.site.register(DiagnosticoEnfermagem, DiagnosticoEnfermagemAdmin)
admin.site.register(FatorRelacionado, FatorRelacionadoAdmin)
admin.site.register(Intervencao, IntervencaoAdmin)
admin.site.register(ParametrosSAE, ParametrosSAEAdmin)
