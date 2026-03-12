from asyncio import format_helpers
from datetime import datetime
from django.utils import timezone
from django.contrib import admin
from django.urls import reverse
from dominios.utils import StatusFilterAdminMixin, ExportToXLSMixin
from .models import CBO, Profissao, Especialidade, OrgaoRegulador, CadastroProfissional, CID, ProfissionalEspecialidade, Turnos
from .forms import CBOForm, CIDForm, ProfissaoForm, EspecialidadeForm, OrgaoReguladorForm, CadastroProfissionalForm, TurnosForm


class CBOAdmin(ExportToXLSMixin, admin.ModelAdmin):
    form = CBOForm

    actions = ['export_as_xls']

    list_display = ('id', 'codigo_cbo', 'descricao', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')
    # Usando ChoicesFieldListFilter para permitir um valor padrão
    list_filter = (StatusFilterAdminMixin, 'dt_registro', 'us_registro')
    search_fields = ['id', 'codigo_cbo', 'descricao', ]
    list_display_links = ['id', 'codigo_cbo', 'descricao', ]
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


class ProfissaoAdmin(ExportToXLSMixin, admin.ModelAdmin):
    form = ProfissaoForm

    actions = ['export_as_xls']

    list_display = ('id', 'profissao', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao',  'us_atualizacao')
    # Usando ChoicesFieldListFilter para permitir um valor padrão
    list_filter = (StatusFilterAdminMixin, 'dt_registro', 'us_registro')
    list_display_links = ('id', 'profissao',)
    search_fields = ['id', 'profissao', ]
    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']
    list_editable = ['status']
    ordering = ('-pk',)

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


class EspecialidadeAdmin(ExportToXLSMixin, admin.ModelAdmin):
    form = EspecialidadeForm

    actions = ['export_as_xls']

    list_display = ('id', 'especialidade', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')
    # Usando ChoicesFieldListFilter para permitir um valor padrão
    list_filter = (StatusFilterAdminMixin, 'us_registro', 'dt_registro')
    list_display_links = ('id', 'especialidade',)
    search_fields = ['id', 'especialidade', ]
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


class OrgaoReguladorAdmin(ExportToXLSMixin, admin.ModelAdmin):
    form = OrgaoReguladorForm

    actions = ['export_as_xls']

    list_display = ('id', 'sigla', 'descricao', 'uf', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')
    autocomplete_fields = ('uf',)
    list_display_links = ('id', 'sigla', 'descricao',)
    # Usando ChoicesFieldListFilter para permitir um valor padrão
    list_filter = (StatusFilterAdminMixin, 'dt_registro', 'us_registro',)
    search_fields = ['id', 'sigla', 'descricao', 'uf__estado']
    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']
    list_editable = ['status']
    ordering = ['-pk', ]
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


class ProfissionalEspecialidadeInline(admin.TabularInline):
    model = ProfissionalEspecialidade
    extra = 1  # Número de linhas extras para novas especialidades


class CadastroProfissionalAdmin(ExportToXLSMixin, admin.ModelAdmin):
    form = CadastroProfissionalForm

    actions = ['export_as_xls']

    # Adiciona o inline ao admin do CadastroProfissional
    inlines = [ProfissionalEspecialidadeInline, ]

    list_display = ('id', 'profissional', 'profissao', 'orgao_regulador', 'numero', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')
    list_display_links = ('id', 'profissao', 'profissional')
    # Usando ChoicesFieldListFilter para permitir um valor padrão
    list_filter = (StatusFilterAdminMixin, 'profissao',
                   'orgao_regulador', 'especialidades', 'dt_registro', 'us_registro',)
    search_fields = ['id', 'profissional__username', 'profissao__profissao',
                     'orgao_regulador__descricao', 'numero']
    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']
    list_editable = ['status']
    ordering = ['-pk', ]
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


class CIDAdmin(ExportToXLSMixin, admin.ModelAdmin):
    form = CIDForm

    actions = ['export_as_xls']

    list_display = ('id', 'codigo', 'descricao',  'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao',  'us_atualizacao')
    list_display_links = ('id', 'codigo', 'descricao',)
    # Usando ChoicesFieldListFilter para permitir um valor padrão
    list_filter = (StatusFilterAdminMixin, 'dt_registro', 'us_registro',)
    search_fields = ['id', 'descricao', 'codigo']
    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']
    list_editable = ['status']
    ordering = ['-pk', ]
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


class TurnosAdmin(admin.ModelAdmin):
    form = TurnosForm

    list_display = ('id', 'turnos',  'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao',  'us_atualizacao')
    list_display_links = ('id', 'turnos',)
    # Usando ChoicesFieldListFilter para permitir um valor padrão
    list_filter = (StatusFilterAdminMixin, 'dt_registro', 'us_registro',)
    search_fields = ['id', 'turnos',]
    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']
    list_editable = ['status']
    ordering = ['-pk', ]
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


admin.site.site_header = 'Administração e Cadastros'
admin.site.site_title = 'Administração e Cadastros'
admin.site.index_title = 'Administração e Cadastros'


admin.site.register(CBO, CBOAdmin)
admin.site.register(CID, CIDAdmin)
admin.site.register(Turnos, TurnosAdmin)
admin.site.register(Profissao, ProfissaoAdmin)
admin.site.register(Especialidade, EspecialidadeAdmin)
admin.site.register(OrgaoRegulador, OrgaoReguladorAdmin)
admin.site.register(CadastroProfissional,
                    CadastroProfissionalAdmin)
