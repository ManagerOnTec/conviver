from django.forms import BaseInlineFormSet
from asyncio import format_helpers
from datetime import datetime
from datetime import date as _dt_date
from django.db import models
from django.utils import timezone
from django.contrib import admin
from dominios.utils import StatusFilterAdminMixin, ExportToXLSMixin, Select2AdminModelAdminMixin
from dominios.admin_dashboard_mixins import AdminDashboardAndTopFilterMixin
from dominios.choices import tipo_empresa_choices
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


class ParametroTopoFilter(admin.SimpleListFilter):
    """Filtro “de passagem” para parâmetros que a BARRA DE TOPO aplica.

    Existe só para o ChangeList reconhecer o parâmetro como filtro conhecido.
    O recorte real é feito no `get_queryset` do ModelAdmin — que é o único
    lugar onde os quatro parâmetros podem ser COMBINADOS sem conflito.

    - `lookups()` devolve vazio (não aparece na barra lateral);
    - `queryset()` devolve tudo (não recorta).

    Sem isso o Django tenta resolver `tipo_pessoa` como campo do modelo e
    derruba a listagem com `FieldDoesNotExist` / `?e=1`.
    """

    # O Django instancia cada filtro com `(request, params, model,
    # model_admin)`. Por isso o parâmetro vem por CLASSE (criada pela
    # fábrica `para()`), e não pelo `__init__`.
    parametro = ''
    # O Django exige `title` e `parameter_name` na CLASSE (lê no `__init__`).
    title = 'Filtro do topo'
    parameter_name = ''

    @classmethod
    def para(cls, parametro):
        """Fábrica: devolve uma SUBCLASSE já amarrada ao parâmetro."""
        nome = f'ParametroTopo_{parametro}'
        return type(nome, (cls,), {
            'parametro': parametro,
            'parameter_name': parametro,
            'title': f'Filtro do topo ({parametro})',
            '__module__': cls.__module__,
        })

    def lookups(self, request, model_admin):
        return ()

    def value(self):
        # O ChangeList lê o valor via `used_parameters`; devolve-o como veio
        # (string ou None) para o Django saber que o parâmetro foi tratado.
        valor = self.used_parameters.get(self.parametro)
        if isinstance(valor, (list, tuple)):
            valor = valor[0] if valor else None
        return valor

    def expected_parameters(self):
        return [self.parametro]

    def queryset(self, request, queryset):
        return queryset


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


class PessoaAdmin(AdminDashboardAndTopFilterMixin, ExportToXLSMixin,
                  Select2AdminModelAdminMixin, admin.ModelAdmin):
    form = PessoaAdminForm

    actions = ['export_as_xls']

    # A barra de período opera sobre a DATA DE NASCIMENTO (é o eixo que
    # interessa ao cadastro de pessoas). Outros módulos usam `dt_registro`.
    dashboard_date_field = 'dt_nascimento'

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

    def get_list_filter(self, request):
        """Declara os parâmetros da barra de TOPO como filtros PRÓPRIOS.

        Não basta a lista vazia: o ChangeList exige um `SimpleListFilter`
        real para “consumir” o parâmetro — sem isso ele tenta resolver
        `tipo_pessoa` como lookup do modelo e levanta
        `FieldDoesNotExist`. Os filtros abaixo NÃO recortam nada (o recorte
        é do `get_queryset`, que consegue COMBINAR os quatro); só declaram
        o parâmetro como conhecido.
        """
        extras = [ParametroTopoFilter.para('tipo_pessoa'),
                  ParametroTopoFilter.para('mes_nascimento'),
                  ParametroTopoFilter.para('sexo_filtro'),
                  ParametroTopoFilter.para('idade_faixa')]
        return list(super().get_list_filter(request)) + extras

    search_fields = ['id', 'nome', 'email', 'cpf', 'rg', 'dt_nascimento']
    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']
    list_editable = ['status', 'classificacao_pessoa']
    ordering = ['-pk',]
    list_per_page = 99

    def get_changelist(self, request, **kwargs):
        """A listagem com `list_editable` usa a tabela montada no SERVIDOR.

        O `templates/admin/change_list.html` renderiza
        `cl.linhas_renderizadas` quando há `list_editable`; o `ChangeList`
        padrão do Django não tem esse atributo (o `{% result_list %}` do
        Django gera `<tr>` soltas, que o navegador descarta). É o mesmo
        `ChangeListEditavel` do fluxo de faturas.
        """
        from admin_faturas.changelist_editavel import ChangeListEditavel
        return ChangeListEditavel

    def get_linhas_nao_editaveis(self, request):
        """Nenhuma linha travada: o cadastro de pessoas não tem regra de
        fluxo (diferente de faturas/pagamentos, que travam por etapa)."""
        return set()

    # ------------------------------------------------------------------
    # BARRA SUPERIOR: presets, atalhos e combinações
    # ------------------------------------------------------------------
    # Parâmetros que a barra superior GERENCIA. O link de cada botão troca (ou
    # limpa) SÓ os seus; os demais filtros da URL são preservados — é isso que
    # permite COMBINAR tipo + mês de nascimento + sexo + faixa de idade.
    _TOP_PARAMS_GRUPO = ('tipo_pessoa', 'mes_nascimento', 'sexo_filtro',
                         'idade_faixa', 'status', 'dt_nascimento__gte',
                         'dt_nascimento__lte', 'periodo')

    def _url_sem(self, request, chaves):
        """URL da própria listagem removendo `chaves` (e a paginação)."""
        params = request.GET.copy()
        params.pop('p', None)
        for chave in chaves:
            params.pop(chave, None)
        query = params.urlencode()
        return f'{request.path}?{query}' if query else request.path

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

    def get_top_filter_presets(self, request):
        """Presets de IDADE em lugar do período: os aniversariantes do mês
        são um atalho próprio e ocupariam o lugar de Hoje/Ontem/mês."""
        hoje = timezone.localdate()

        def ativo(**filtros):
            return all(str(request.GET.get(k)) == str(v)
                       for k, v in filtros.items())

        sem_faixa = not any(
            request.GET.get(k) for k in ('idade_faixa', 'dt_nascimento__gte',
                                         'dt_nascimento__lte', 'periodo'))
        return [
            {'label': 'Todas as idades',
             'url': self._url_sem(
                 request, ('idade_faixa', 'dt_nascimento__gte',
                           'dt_nascimento__lte', 'periodo', 'mes_nascimento')),
             'active': sem_faixa},
            {'label': 'Crianças (0-11)',
             'url': self._url_com(request, idade_faixa='crianca',
                                  mes_nascimento=None),
             'active': ativo(idade_faixa='crianca')},
            {'label': 'Adolescentes (12-17)',
             'url': self._url_com(request, idade_faixa='adolescente',
                                  mes_nascimento=None),
             'active': ativo(idade_faixa='adolescente')},
            {'label': 'Adultos (18-59)',
             'url': self._url_com(request, idade_faixa='adulto',
                                  mes_nascimento=None),
             'active': ativo(idade_faixa='adulto')},
            {'label': 'Idosos (60+)',
             'url': self._url_com(request, idade_faixa='idoso',
                                  mes_nascimento=None),
             'active': ativo(idade_faixa='idoso')},
            {'label': f'Aniversariantes {hoje:%m/%Y}',
             'url': self._url_com(request, mes_nascimento=hoje.month,
                                  idade_faixa=None),
             'active': ativo(mes_nascimento=hoje.month)},
        ]

    def get_top_extra_filters(self, request):
        """Atalhos do TOPO: tipo de pessoa (paciente/funcionário) e sexo.

        Cada grupo tem o seu “Todos”, que limpa SÓ o próprio parâmetro e
        preserva todos os outros filtros da tela.
        """
        tipo = request.GET.get('tipo_pessoa')
        sexo = request.GET.get('sexo_filtro')

        # Os tipos vêm de graça das escolhas do modelo (não há enum fixo aqui).
        from .models import classificacao_pessoa_choices
        filtros = [{
            'label': 'Todos os tipos',
            'url': self._url_com(request, tipo_pessoa=None),
            'active': not tipo,
            'icon': 'fa-list',
        }]
        for valor, rotulo in classificacao_pessoa_choices:
            filtros.append({
                'label': str(rotulo).capitalize(),
                'url': self._url_com(request, tipo_pessoa=valor),
                'active': tipo == valor,
                'icon': 'fa-user-tag',
            })
        filtros += [
            {'label': 'Todos os sexos',
             'url': self._url_com(request, sexo_filtro=None),
             'active': not sexo, 'icon': 'fa-venus-mars'},
            {'label': 'Feminino',
             'url': self._url_com(request, sexo_filtro='f'),
             'active': sexo == 'f', 'icon': 'fa-venus'},
            {'label': 'Masculino',
             'url': self._url_com(request, sexo_filtro='m'),
             'active': sexo == 'm', 'icon': 'fa-mars'},
        ]
        return filtros

    top_extra_filter_label = 'Tipo & Sexo'

    def get_top_dropdown_subfilters(self, request):
        """Combinações: mês de nascimento, idade, tipo e sexo num select cada.

        Diferente dos atalhos (que só ligam/desligam), o select mostra o valor
        ATUAL e permite trocar mantendo os outros filtros — é a forma de
        cruzar mês + faixa + sexo + tipo sem perder o recorte anterior.
        """
        meses = [
            (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
            (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
            (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'),
            (12, 'Dezembro'),
        ]
        mes_atual = request.GET.get('mes_nascimento') or ''
        opcoes_mes = [{'value': self._url_com(request, mes_nascimento=None),
                       'label': 'Todos os meses',
                       'selected': not mes_atual}]
        for numero, rotulo in meses:
            opcoes_mes.append({
                'value': self._url_com(request, mes_nascimento=numero),
                'label': rotulo,
                'selected': str(mes_atual) == str(numero),
            })

        faixa = request.GET.get('idade_faixa') or ''
        opcoes_idade = [
            {'value': self._url_com(request, idade_faixa=None),
             'label': 'Todas as idades', 'selected': not faixa},
            {'value': self._url_com(request, idade_faixa='crianca'),
             'label': '0 a 11 anos', 'selected': faixa == 'crianca'},
            {'value': self._url_com(request, idade_faixa='adolescente'),
             'label': '12 a 17 anos', 'selected': faixa == 'adolescente'},
            {'value': self._url_com(request, idade_faixa='adulto'),
             'label': '18 a 59 anos', 'selected': faixa == 'adulto'},
            {'value': self._url_com(request, idade_faixa='idoso'),
             'label': '60 anos ou mais', 'selected': faixa == 'idoso'},
        ]

        tipo = request.GET.get('tipo_pessoa') or ''
        from .models import classificacao_pessoa_choices
        opcoes_tipo = [{'value': self._url_com(request, tipo_pessoa=None),
                        'label': 'Todos os tipos', 'selected': not tipo}]
        for valor, rotulo in classificacao_pessoa_choices:
            opcoes_tipo.append({
                'value': self._url_com(request, tipo_pessoa=valor),
                'label': str(rotulo).capitalize(),
                'selected': tipo == valor,
            })

        sexo = request.GET.get('sexo_filtro') or ''
        opcoes_sexo = [
            {'value': self._url_com(request, sexo_filtro=None),
             'label': 'Todos os sexos', 'selected': not sexo},
            {'value': self._url_com(request, sexo_filtro='f'),
             'label': 'Feminino', 'selected': sexo == 'f'},
            {'value': self._url_com(request, sexo_filtro='m'),
             'label': 'Masculino', 'selected': sexo == 'm'},
        ]

        return [
            {'label': 'Mês de nascimento', 'options': opcoes_mes},
            {'label': 'Faixa de idade', 'options': opcoes_idade},
            {'label': 'Tipo', 'options': opcoes_tipo},
            {'label': 'Sexo', 'options': opcoes_sexo},
            {'label': 'Limpar filtros do topo', 'is_clear': True,
             'options': [{'value': self._url_sem(
                 request, self._TOP_PARAMS_GRUPO),
                 'label': 'Limpar todos os filtros', 'selected': False}]},
        ]

    # ------------------------------------------------------------------
    # RECORTES do topo (aplicados no queryset da listagem)
    # ------------------------------------------------------------------
    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        tipo = request.GET.get('tipo_pessoa')
        if tipo:
            queryset = queryset.filter(classificacao_pessoa=tipo)

        sexo = request.GET.get('sexo_filtro')
        if sexo:
            queryset = queryset.filter(sexo=sexo)

        mes = request.GET.get('mes_nascimento')
        if mes:
            try:
                queryset = queryset.filter(dt_nascimento__month=int(mes))
            except (TypeError, ValueError):
                pass

        idade = request.GET.get('idade_faixa')
        if idade:
            queryset = self._filtrar_faixa_idade(queryset, idade)
        return queryset

    @staticmethod
    def _filtrar_faixa_idade(queryset, faixa):
        """Faixa de idade por DATA (não por `EXTRACT(age())`, que não existe
        no SQLite): compara `dt_nascimento` com as datas-limite já
        calculadas em Python, então funciona em qualquer backend."""
        from datetime import date as _date
        hoje = _date.today()
        limites = {
            # (mais novo que..., mais velho que...) em anos
            'crianca': (0, 11),
            'adolescente': (12, 17),
            'adulto': (18, 59),
            'idoso': (60, 130),
        }
        faixa = limites.get(faixa)
        if faixa is None:
            return queryset
        minimo, maximo = faixa
        # Aniversário ainda não chegou neste ano → idade = ano - 1.
        mais_novo = _date(hoje.year - minimo, hoje.month, hoje.day)
        mais_velho = _date(hoje.year - maximo - 1, hoje.month, hoje.day)
        return queryset.filter(
            dt_nascimento__isnull=False,
            dt_nascimento__lte=mais_novo,
            dt_nascimento__gt=mais_velho,
        )

    # ------------------------------------------------------------------
    # INDICADORES
    # ------------------------------------------------------------------
    def get_dashboard_kpis(self, request, queryset):
        from django.db.models import Count
        hoje = timezone.localdate()

        def _qtd(valor):
            return f'{int(valor or 0):,}'.replace(',', '.')

        total = queryset.count()
        ativos = queryset.filter(status='A').count()
        fem = queryset.filter(sexo='f').count()
        masc = queryset.filter(sexo='m').count()
        aniversariantes = queryset.filter(
            dt_nascimento__month=hoje.month).count()
        sem_nascimento = queryset.filter(
            dt_nascimento__isnull=True).count()

        # Idade média (só quem tem data de nascimento).
        idades = [
            hoje.year - d.year - ((hoje.month, hoje.day) < (d.month, d.day))
            for d in queryset.exclude(dt_nascimento__isnull=True)
            .values_list('dt_nascimento', flat=True)[:5000]
        ]
        media = round(sum(idades) / len(idades), 1) if idades else 0

        return [
            {'title': 'Pessoas', 'value': _qtd(total),
             'subtitle': f'{_qtd(ativos)} ativas',
             'color_class': 'kpi-blue', 'icon': 'fa-users'},
            {'title': 'Feminino', 'value': _qtd(fem),
             'subtitle': f'{_qtd(masc)} masculino',
             'color_class': 'kpi-purple', 'icon': 'fa-venus'},
            {'title': f'Aniversariantes {hoje:%m/%Y}',
             'value': _qtd(aniversariantes),
             'subtitle': 'Nascidos neste mês',
             'color_class': 'kpi-orange', 'icon': 'fa-cake-candles'},
            {'title': 'Idade média', 'value': f'{media} anos',
             'subtitle': 'Somente com data de nascimento',
             'color_class': 'kpi-teal', 'icon': 'fa-calendar-days'},
            {'title': 'Sem data de nascimento', 'value': _qtd(sem_nascimento),
             'subtitle': 'Revisar cadastro',
             'color_class': 'kpi-red',
             'icon': 'fa-triangle-exclamation'},
        ]

    top_filter_search_label = 'Busca'
    top_filter_search_placeholder = 'Nome, CPF, RG, e-mail ou data de nascimento...'

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


class EmpresaAdmin(AdminDashboardAndTopFilterMixin, ExportToXLSMixin,
                   Select2AdminModelAdminMixin, admin.ModelAdmin):
    form = EmpresaForm

    actions = ['export_as_xls']

    # A barra de período opera sobre o cadastro (data de registro).
    dashboard_date_field = 'dt_registro'

    list_display = ('id', 'empresa', 'razao_social', 'fantasia', 'cnpj',
                    'tipo', 'status', 'dt_registro', 'us_registro',
                    'dt_atualizacao', 'us_atualizacao')
    autocomplete_fields = ('estado',)
    list_display_links = ('id', 'empresa', 'razao_social', 'fantasia',)
    # Usando ChoicesFieldListFilter para permitir um valor padrão
    list_filter = (StatusFilterAdminMixin, 'tipo', 'nacionalidade',
                   'estado', 'cidade', 'dt_registro', 'us_registro',)
    search_fields = ['id', 'empresa', 'razao_social', 'fantasia', 'cnpj']
    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']
    list_editable = ['status', 'tipo']

    list_per_page = 99
    ordering = ['-pk']

    def get_queryset(self, request):
        """Recortes da barra SUPERIOR.

        `tipo` e `estado`/`cidade` também são filtros laterais nativos — o
        Django os aplica sozinho. Aqui só garantimos que os parâmetros
        venham em `__exact` quando o topo os envia e que um valor inválido
        no `tipo` não derrube a listagem.
        """
        queryset = super().get_queryset(request)
        tipo = request.GET.get('tipo')
        if tipo:
            validos = {v for v, _ in tipo_empresa_choices}
            if tipo in validos:
                queryset = queryset.filter(tipo=tipo)
            # tipo inválido → ignora (o topo já está com o preset “Todos”)

        # UF/Cidade dos selects do topo. Lidos da PRÓPRIA URL (os nomes não
        # são lookups válidos para o Django declarar como filtro).
        uf = request.GET.get('estado__id__exact')
        if uf:
            queryset = queryset.filter(estado_id=uf)
        cidade = request.GET.get('cidade__id__exact')
        if cidade:
            queryset = queryset.filter(cidade_id=cidade)
        return queryset

    def get_list_filter(self, request):
        """O topo usa `estado__id__exact`/`cidade__id__exact`, que NÃO são
        caminhos de campo válidos para o Django declarar como filtro (dá
        `NotRelationField`). Aplicamos esses dois direto no `get_queryset` e
        removemos da URL antes do ChangeList — assim o filtro lateral
        (`estado`, `cidade`) continua funcionando normalmente.
        """
        return list(super().get_list_filter(request))

    # ------------------------------------------------------------------
    # BARRA SUPERIOR (tipo, ativos e combinação de UF/cidade)
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
        """Presets de TIPO no lugar do período.

        O recorte mais importante desta tela é por PAPEL (fornecedor,
        convênio, estabelecimento), não por data de cadastro.
        """
        tipo = request.GET.get('tipo')

        presets = [{'label': 'Todos os tipos',
                    'url': self._url_sem(request, ('tipo',)),
                    'active': not tipo}]
        for valor, rotulo in tipo_empresa_choices:
            presets.append({
                'label': str(rotulo),
                'url': self._url_com(request, tipo=valor),
                'active': tipo == valor,
            })
        return presets

    def get_top_extra_filters(self, request):
        """Atalhos de STATUS (as demais combinações vêm nos selects)."""
        status = request.GET.get('status')
        return [
            self._filtro_status(request, 'Todos', None, not status),
            self._filtro_status(request, 'Ativas', 'A', status == 'A'),
            self._filtro_status(request, 'Inativas', 'I', status == 'I'),
        ]

    def _filtro_status(self, request, rotulo, valor, ativo):
        return {'label': rotulo,
                'url': self._url_com(request, status=valor),
                'active': ativo,
                'icon': 'fa-circle-check' if valor == 'A'
                        else ('fa-ban' if valor == 'I' else 'fa-list')}

    top_extra_filter_label = 'Status'

    def get_top_dropdown_subfilters(self, request):
        """Combinações de UF e Cidade (cada select preserva os demais)."""
        from .models import Estado, Cidade

        uf_atual = request.GET.get('estado__id__exact') or ''
        opcoes_uf = [{'value': self._url_com(
                          request, **{'estado__id__exact': None,
                                      'cidade__id__exact': None}),
                      'label': 'Todas as UF', 'selected': not uf_atual}]
        for estado in Estado.objects.filter(status='A').order_by('uf'):
            opcoes_uf.append({
                'value': self._url_com(
                    request, **{'estado__id__exact': estado.pk,
                                'cidade__id__exact': None}),
                'label': f'{estado.uf} — {estado.estado}',
                'selected': str(uf_atual) == str(estado.pk),
            })

        cid_atual = request.GET.get('cidade__id__exact') or ''
        cidades = Cidade.objects.filter(status='A')
        if uf_atual:
            cidades = cidades.filter(estado_id=uf_atual)
        opcoes_cidade = [{'value': self._url_com(
                             request, **{'cidade__id__exact': None}),
                         'label': 'Todas as cidades',
                         'selected': not cid_atual}]
        for cidade in cidades.order_by('cidade')[:500]:
            opcoes_cidade.append({
                'value': self._url_com(
                    request, **{'cidade__id__exact': cidade.pk}),
                'label': cidade.cidade,
                'selected': str(cid_atual) == str(cidade.pk),
            })

        return [
            {'label': 'UF', 'options': opcoes_uf},
            {'label': 'Cidade', 'options': opcoes_cidade},
            {'label': 'Limpar filtros do topo', 'is_clear': True,
             'options': [{'value': self._url_sem(
                 request, ('tipo', 'estado__id__exact',
                           'cidade__id__exact', 'status')),
                 'label': 'Limpar todos os filtros', 'selected': False}]},
        ]

    # ------------------------------------------------------------------
    # INDICADORES
    # ------------------------------------------------------------------
    def get_dashboard_kpis(self, request, queryset):
        def _qtd(valor):
            return f'{int(valor or 0):,}'.replace(',', '.')

        total = queryset.count()
        ativas = queryset.filter(status='A').count()
        forn = queryset.filter(tipo='fornecedor').count()
        conv = queryset.filter(tipo='convenio').count()
        estab = queryset.filter(tipo='estabelecimento').count()
        sem_cnpj = queryset.filter(
            models.Q(cnpj__isnull=True) | models.Q(cnpj='')).count()

        return [
            {'title': 'Empresas', 'value': _qtd(total),
             'subtitle': f'{_qtd(ativas)} ativas',
             'color_class': 'kpi-blue', 'icon': 'fa-building'},
            {'title': 'Fornecedores', 'value': _qtd(forn),
             'subtitle': 'Fluxo de saída (pagamentos)',
             'color_class': 'kpi-orange', 'icon': 'fa-truck'},
            {'title': 'Convênios', 'value': _qtd(conv),
             'subtitle': 'Pagadores do faturamento',
             'color_class': 'kpi-green', 'icon': 'fa-file-invoice'},
            {'title': 'Estabelecimentos', 'value': _qtd(estab),
             'subtitle': 'Unidades próprias',
             'color_class': 'kpi-purple', 'icon': 'fa-hospital'},
            {'title': 'Sem CNPJ', 'value': _qtd(sem_cnpj),
             'subtitle': 'Revisar cadastro',
             'color_class': 'kpi-red',
             'icon': 'fa-triangle-exclamation'},
        ]

    top_filter_search_label = 'Busca'
    top_filter_search_placeholder = (
        'Razão social, fantasia, apelido ou CNPJ...')

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
