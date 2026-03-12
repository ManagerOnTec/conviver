from django.forms import BaseInlineFormSet
from asyncio import format_helpers
from datetime import datetime
from django.utils import timezone
from django.contrib import admin
from dominios.utils import StatusFilterAdminMixin, ExportToXLSMixin
from .models import Estado, Cidade, Genero, Pessoa, Empresa, Estabelecimento, PessoaCampos, EmpresaCampos, TipoAtendimento, Pais
from .forms import EstadoForm, CidadeForm, PessoaAdminForm, EmpresaForm, EstabelecimentoForm, PessoaCamposForm, EmpresaCamposForm, TipoAtendimentoForm, PaisForm, GeneroForm
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.models import User
from datetime import date


class EstadoAdmin(ExportToXLSMixin, admin.ModelAdmin):
    form = EstadoForm

    actions = ['export_as_xls']

    list_display = ('id', 'uf', 'estado', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')
    list_display_links = ('id', 'uf', 'estado')

    # Usando ChoicesFieldListFilter para permitir um valor padrão
    list_filter = (StatusFilterAdminMixin,)

    search_fields = ['id', 'estado', 'uf']
    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']
    list_editable = ['status']
    list_per_page = 11
    ordering = ['-pk',]

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


class CidadeAdmin(ExportToXLSMixin, admin.ModelAdmin):
    form = CidadeForm

    actions = ['export_as_xls']

    autocomplete_fields = ('estado',)

    list_display = ('id', 'cidade', 'estado', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')
    list_display_links = ('id', 'cidade',)
    # Usando ChoicesFieldListFilter para permitir um valor padrão
    list_filter = (StatusFilterAdminMixin,)
    search_fields = ['id', 'cidade', 'estado__estado']
    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']
    list_editable = ['status']
    list_per_page = 11
    ordering = ['-pk',]

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


class PaisAdmin(ExportToXLSMixin, admin.ModelAdmin):
    form = PaisForm

    actions = ['export_as_xls']

    list_display = ('id', 'pais', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')
    # Usando ChoicesFieldListFilter para permitir um valor padrão
    list_filter = (StatusFilterAdminMixin,)
    list_display_links = ('id', 'pais',)
    search_fields = ['id', 'pais', ]
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


class GeneroAdmin(admin.ModelAdmin):
    form = GeneroForm
    list_display = ('id', 'genero', 'status')
    # Usando ChoicesFieldListFilter para permitir um valor padrão
    list_filter = (StatusFilterAdminMixin,)
    list_display_links = ('id', 'genero',)
    search_fields = ['id', 'genero', ]
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


class PessoaCamposAdmin(ExportToXLSMixin, admin.ModelAdmin):
    model = PessoaCampos

    actions = ['export_as_xls']

    list_display = ('id', 'campo', 'obrigatorio', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')

    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']

    list_display_links = ('id', 'campo',)

    list_editable = ('obrigatorio',)

    list_filter = ('campo', 'obrigatorio', 'dt_registro', 'us_registro',)

    ordering = ['-pk',]

    list_per_page = 11

    def configurar_pessoa(self, obj):
        return 'Clique para editar'
    configurar_pessoa.short_description = 'Configuração do Cadastro de Pessoas'

    def has_delete_permission(self, request, obj=None):
        if request.user.username == 'admin':
            return True
        # Somente admin pode excluir este objeto
        # (recomendado apenas para excluir em desenvolvimento,
        # pois em produção não tem necessidade de excluir), demais não podem.
        return False

    def delete_model(self, request, obj):
        if request.user.username != 'admin':
            self.message_user(
                request, "Não é possível excluir este objeto.")
            return
        obj.delete()

    def save_model(self, request, obj, form, change):
        if not change:  # se estiver criando um novo objeto
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:  # se estiver editando um objeto existente
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()

        super().save_model(request, obj, form, change)


class EmpresaCamposAdmin(ExportToXLSMixin, admin.ModelAdmin):
    model = EmpresaCampos

    actions = ['export_as_xls']

    list_display = ('id', 'campo', 'obrigatorio', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')
    list_display_links = ('id', 'campo',)
    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']
    list_editable = ('obrigatorio',)

    list_filter = ('campo', 'obrigatorio', 'dt_registro', 'us_registro',)

    list_per_page = 11

    ordering = ['-pk',]

    def configurar_empresa(self, obj):
        return 'Clique para editar'
    configurar_empresa.short_description = 'Configuração do Cadastro de Empresas'

    def has_delete_permission(self, request, obj=None):
        if request.user.username == 'admin':
            return True
        # Somente admin pode excluir este objeto
        # (recomendado apenas para excluir em desenvolvimento,
        # pois em produção não tem necessidade de excluir), demais não podem.
        return False

    def delete_model(self, request, obj):
        if request.user.username != 'admin':
            self.message_user(
                request, "Não é possível excluir este objeto.")
            return
        obj.delete()

    def save_model(self, request, obj, form, change):
        if not change:  # se estiver criando um novo objeto
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:  # se estiver editando um objeto existente
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()

        super().save_model(request, obj, form, change)


# Filtro personalizado para idade no admin
class IdadeFilter(admin.SimpleListFilter):
    title = 'idade'
    parameter_name = 'idade'

    def lookups(self, request, model_admin):
        return [
            ('0-17', '0 a 17 anos'),
            ('18-59', '18 a 59 anos'),
            ('60+', '60 anos ou mais'),
        ]

    def queryset(self, request, queryset):
        hoje = date.today()

        def calcular_idade(nascimento):
            if nascimento:
                return hoje.year - nascimento.year - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))
            return None

        if self.value() == '0-17':
            return queryset.filter(
                dt_nascimento__isnull=False
            ).extra(
                where=[
                    "EXTRACT(YEAR FROM age(current_date, dt_nascimento)) BETWEEN 0 AND 17"]
            )
        elif self.value() == '18-59':
            return queryset.filter(
                dt_nascimento__isnull=False
            ).extra(
                where=[
                    "EXTRACT(YEAR FROM age(current_date, dt_nascimento)) BETWEEN 18 AND 59"]
            )
        elif self.value() == '60+':
            return queryset.filter(
                dt_nascimento__isnull=False
            ).extra(
                where=[
                    "EXTRACT(YEAR FROM age(current_date, dt_nascimento)) >= 60"]
            )
        return queryset


class PessoaAdmin(ExportToXLSMixin, admin.ModelAdmin):
    form = PessoaAdminForm

    actions = ['export_as_xls']

    # Adiciona o campo idade à listagem
    list_display = (
        'id', 'nome', 'classificacao_pessoa', 'cpf', 'rg', 'dt_nascimento', 'idade_calculada',
        'sexo', 'status', 'nacionalidade', 'dt_registro', 'us_registro',
        'dt_atualizacao', 'us_atualizacao',
    )

    autocomplete_fields = ('estado', 'naturalidade', 'responsavel',)
    list_display_links = ('id', 'nome', 'cpf', 'rg', 'dt_nascimento',)

    # Adiciona filtro por idade
    list_filter = (
        StatusFilterAdminMixin, 'classificacao_pessoa', 'nacionalidade',
        'estado', 'cidade', 'dt_nascimento', 'sexo',
        'dt_registro', 'us_registro', IdadeFilter,
    )

    search_fields = ['id', 'nome', 'email', 'cpf', 'rg', 'dt_nascimento']
    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']
    list_editable = ['status', 'classificacao_pessoa']
    ordering = ['-pk',]
    list_per_page = 11

    # Calcula a idade de forma segura verificando se dt_nascimento está preenchido
    def idade_calculada(self, obj):
        if obj.dt_nascimento:
            hoje = date.today()
            return hoje.year - obj.dt_nascimento.year - (
                (hoje.month, hoje.day) < (
                    obj.dt_nascimento.month, obj.dt_nascimento.day)
            )
        return 'Não informado'
    idade_calculada.short_description = 'Idade'

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)

        if 'HTTP_REFERER' in request.META:
            referer_path = request.META['HTTP_REFERER'].split(
                request.META['HTTP_HOST'])[1]
            if '/add/' in referer_path or '/change/' in referer_path:
                queryset = queryset.filter(status='A')

        return queryset, use_distinct

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()

        super().save_model(request, obj, form, change)


class EmpresaAdmin(ExportToXLSMixin, admin.ModelAdmin):
    form = EmpresaForm

    actions = ['export_as_xls']

    list_display = ('id', 'empresa', 'razao_social', 'fantasia', 'cnpj', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')
    autocomplete_fields = ('estado',)
    list_display_links = ('id', 'empresa', 'razao_social', 'fantasia',)
    # Usando ChoicesFieldListFilter para permitir um valor padrão
    list_filter = (StatusFilterAdminMixin, 'nacionalidade',
                   'estado', 'cidade', 'dt_registro', 'us_registro',)
    search_fields = ['id', 'empresa', 'razao_social', 'fantasia', 'cnpj']
    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']
    list_editable = ['status']

    list_per_page = 11
    ordering = ['-pk']

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


class EstabelecimentoAdmin(admin.ModelAdmin):
    form = EstabelecimentoForm

    autocomplete_fields = ('empresa',)
    list_display = ('id', 'estabelecimento', 'empresa', 'status',
                    'dt_registro', 'us_registro', 'dt_atualizacao', 'us_atualizacao',)
    readonly_fields = ['dt_registro', 'us_registro',
                       'dt_atualizacao', 'us_atualizacao', ]
    # Usando ChoicesFieldListFilter para permitir um valor padrão
    list_filter = (StatusFilterAdminMixin, 'dt_registro', 'us_registro')
    search_fields = ('id', 'estabelecimento',
                     'empresa__razao_social',)
    list_display_links = ('id', 'estabelecimento', 'empresa',)
    list_editable = ['status']
    ordering = ['-pk']

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


class TipoAtendimentoAdmin(admin.ModelAdmin):
    form = TipoAtendimentoForm

    list_display = ('id', 'tipo_atendimento', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')
    # Usando ChoicesFieldListFilter para permitir um valor padrão
    list_filter = (StatusFilterAdminMixin,)
    list_display_links = ('id', 'tipo_atendimento',)
    search_fields = ['id', 'tipo_atendimento', ]
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


admin.site.register(PessoaCampos, PessoaCamposAdmin)
admin.site.register(Estado, EstadoAdmin)
admin.site.register(Cidade, CidadeAdmin)
admin.site.register(Pais, PaisAdmin)
admin.site.register(Genero, GeneroAdmin)
admin.site.register(Pessoa, PessoaAdmin)
admin.site.register(EmpresaCampos, EmpresaCamposAdmin)
admin.site.register(Empresa, EmpresaAdmin)
admin.site.register(Estabelecimento, EstabelecimentoAdmin)
admin.site.register(TipoAtendimento, TipoAtendimentoAdmin)
