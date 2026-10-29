from django.forms import DateInput
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.middleware.csrf import get_token
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path
from django.shortcuts import redirect, get_object_or_404
from django.utils.html import format_html
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
from contas.models import Perfil
from .models import Convenio, PreFatura, Fatura, BaixaFatura, periodo_cobranca
from .forms import BaixaFaturaForm, ConvenioForm, FaturaForm, PreFaturaForm
from django.contrib import messages
from django.utils import timezone
from dominios.utils import ExportToXLSMixin, AdminEstabelecimentoPadraoMixin, StatusFilterAdminMixin, chain_form_init, Select2AdminModelAdminMixin
from .dashboard import (
    ConvenioPagadorFilter, FaturasDashboardMixin, _money, _qtd,
)
from datetime import timedelta, date
import calendar
from decimal import Decimal
from django.db import models
from admin_cadastros.utils import EstabelecimentoFilterAdminMixin
from admin_cadastros.models import Pessoa
from admin_cadastros_financeiros.models import TransacaoFinanceira
from admin_financeiro.models import CompetenciaBancaria, MovimentoBancario
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django import forms
from django.db import transaction
from django.utils.html import format_html
from django.urls import reverse
from datetime import datetime
from django.contrib import admin
from .models import Convenio, PreFatura, Fatura, BaixaFatura
from .changelist_editavel import ChangeListEditavel  # noqa: F401
from .changelist_editavel import ChangeListEditavel  # noqa: F401


class DateInput(forms.DateInput):
    input_type = 'date'
    format = '%d/%m/%Y'  # Define o formato de entrada de data


class CustomDateFilter(admin.SimpleListFilter):
    title = _('Competência')
    parameter_name = 'competencia'

    def lookups(self, request, model_admin):
        # Obtém todas as competências únicas do modelo PreFatura com status 'A'
        competencias = PreFatura.objects.filter(
            status='A'  # Adiciona o filtro para status 'A'
        ).values_list(
            'competencia', flat=True
        ).distinct().order_by('competencia')
        # Para fins de depuração, imprima as competências obtidas
        # print("Competências obtidas do banco de dados:", competencias)

        # Formata as datas no formato desejado para o filtro
        formatted_dates = [
            (competencia.strftime('%Y-%m-%d'), competencia.strftime('%d/%m/%Y'))
            for competencia in competencias
        ]

        # Para fins de depuração, imprima as datas formatadas
        # print("Datas formatadas para o filtro:", formatted_dates)

        return formatted_dates

    def queryset(self, request, queryset):
        valor = self.value()
        # O valor pode chegar como lista (a listagem editável monta os
        # `used_parameters` do próprio request); usa o primeiro.
        if isinstance(valor, (list, tuple)):
            valor = valor[0] if valor else None
        if valor:
            try:
                # Tenta converter o valor da URL para uma data no formato 'yyyy-mm-dd'
                date_obj = datetime.strptime(valor, '%Y-%m-%d')
                return queryset.filter(competencia=date_obj)
            except (ValueError, TypeError):
                return queryset
        return queryset

    # Removendo o método 'choices' que foi sobrescrito anteriormente
    # def choices(self, changelist):
    #     # Remove a escolha padrão 'All'
    #     return []

    # Mantém os métodos padrão abaixo, se necessário
    def expected_parameters(self):
        return [self.parameter_name]

    def field_name(self):
        return format_html(
            '<input type="date" name="competencia" value="{}" style="width: 110px; display: inline-block; margin-left: 5px;" />',
            self.value() if self.value() else ''
        )

    def value(self):
        if self.used_parameters.get(self.parameter_name):
            return self.used_parameters[self.parameter_name]
        return None


class PreFaturadoQueryFilter(admin.SimpleListFilter):
    title = 'Pré-Faturado'
    parameter_name = 'pre_faturado_status'

    def lookups(self, request, model_admin):
        return (('sim', 'Pré-Faturados'), ('nao', 'Sem Pré-Fatura'))

    def queryset(self, request, queryset):
        if self.value() == 'sim':
            return queryset.filter(pre_faturado=True)
        if self.value() == 'nao':
            return queryset.filter(pre_faturado=False)
        return queryset
class EmpenhoPreFaturaFilter(admin.SimpleListFilter):
    title = 'Empenho'
    parameter_name = 'empenho_status'

    def lookups(self, request, model_admin):
        return (('com', 'Com empenho'), ('sem', 'Sem empenho'))

    def queryset(self, request, queryset):
        from django.db.models import Q
        if self.value() == 'com':
            return queryset.exclude(empenho__isnull=True).exclude(empenho='')
        if self.value() == 'sem':
            return queryset.filter(Q(empenho__isnull=True) | Q(empenho=''))
        return queryset
class EmpenhoConvenioFilter(admin.SimpleListFilter):
    title = 'Empenho Global'
    parameter_name = 'empenho_global_status'

    def lookups(self, request, model_admin):
        return (('com', 'Com empenho'), ('sem', 'Sem empenho'))

    def queryset(self, request, queryset):
        from django.db.models import Q
        if self.value() == 'com':
            return queryset.exclude(empenho_global__isnull=True).exclude(empenho_global='')
        if self.value() == 'sem':
            return queryset.filter(
                Q(empenho_global__isnull=True) | Q(empenho_global=''))
        return queryset
class PreFaturaAdmin(AdminEstabelecimentoPadraoMixin, FaturasDashboardMixin, Select2AdminModelAdminMixin, ExportToXLSMixin, admin.ModelAdmin):

    form = PreFaturaForm
    actions = ['export_as_xls', 'faturar_pre_faturas_em_lote']
    # Seleção para as ações em lote (ex.: "Faturar pré-faturas selecionadas").
    # O POST de uma ação é tratado ANTES de o Django olhar o formset
    # (`_save` ausente), então os campos ocultos do `changelist-form` não
    # interferem na ação.
    selecao_desabilitada = False

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/faturar/',
                self.admin_site.admin_view(self.faturar_pre_fatura_view),
                name='admin_faturas_prefatura_faturar',
            ),
        ]
        return custom_urls + urls
    def render_change_form(self, request, context, *args, **kwargs):
        if context.get('original') and context['original']._meta.model is PreFatura:
            context['faturar_form_template'] = (
                'admin_faturas/includes/faturar_form_inline.html')
        return super().render_change_form(
            request, context, *args, **kwargs)
    @admin.action(description='Faturar pré-faturas selecionadas')
    def faturar_pre_faturas_em_lote(self, request, queryset):
        geradas = 0
        ja_faturadas = 0
        erros = 0
        for prefatura in queryset:
            try:
                with transaction.atomic():
                    if self._faturar_pre_fatura(prefatura, request.user):
                        geradas += 1
                    else:
                        ja_faturadas += 1
            except Exception:
                erros += 1
        if geradas:
            self.message_user(
                request, f'{geradas} fatura(s) gerada(s) com sucesso.',
                level=messages.SUCCESS)
        if ja_faturadas:
            self.message_user(
                request, f'{ja_faturadas} pré-fatura(s) já estavam faturadas; '
                'foram ignoradas.', level=messages.WARNING)
        if erros:
            self.message_user(
                request, f'Falha ao gerar {erros} fatura(s). '
                'As outras selecionadas foram processadas normalmente.',
                level=messages.ERROR)

    def _faturar_pre_fatura(self, prefatura, user=None):
        if Fatura.objects.filter(prefatura_ptr_id=prefatura.pk).exists():
            return False
        prefatura.pre_faturado = True
        if user:
            prefatura.us_atualizacao = user
            prefatura.dt_atualizacao = timezone.now()
            prefatura.save(update_fields=[
                'pre_faturado', 'us_atualizacao', 'dt_atualizacao',
            ])
        else:
            prefatura.save(update_fields=['pre_faturado'])
        prefatura.create_fatura()
        return True
    def changelist_view(self, request, extra_context=None):
        # ModelAdmin.get_list_display() não recebe request; guarde-o para o
        # renderizador do botão, que precisa incluir o token CSRF do POST.
        self._current_request = request
        return super().changelist_view(request, extra_context=extra_context)
    def get_list_display(self, request):
        self._current_request = request
        return super().get_list_display(request)
    def faturar_pre_fatura_view(self, request, object_id):
        if request.method != 'POST':
            return HttpResponseRedirect(
                reverse('admin:admin_faturas_prefatura_changelist'))

        # A própria URL identifica a pré-fatura; não confie em object_id de
        # POST, que pode vir como "undefined" quando o botão está na tabela.
        prefatura = get_object_or_404(PreFatura, pk=object_id)
        try:
            with transaction.atomic():
                gerada = self._faturar_pre_fatura(prefatura, request.user)
            if gerada:
                messages.success(
                    request, f'Fatura gerada para a pré-fatura {prefatura.pk}.')
            else:
                messages.info(
                    request, f'A pré-fatura {prefatura.pk} já foi faturada.')
        except Exception as erro:
            messages.error(
                request,
                f'Não foi possível gerar a fatura da pré-fatura '
                f'{prefatura.pk}: {erro}')

        # O browser envia a URL completa da changelist junto ao POST para
        # preservar integralmente os filtros da listagem.
        return_to = request.POST.get('return_to', '')
        if not url_has_allowed_host_and_scheme(
                return_to, allowed_hosts={request.get_host()},
                require_https=request.is_secure()):
            return_to = reverse('admin:admin_faturas_prefatura_changelist')
        return redirect(return_to)

    def gerar_fatura_button(self, obj):
        if Fatura.objects.filter(prefatura_ptr_id=obj.pk).exists():
            return format_html(
                '<span title="Faturada" style="color:#198754;font-size:18px;'
                'font-weight:bold;">&#10003;</span>')
        if obj.pre_faturado:
            return format_html(
                '<span title="Marcada para faturar" '
                'style="color:#198754;font-size:18px;font-weight:bold;">'
                '&#10003;</span>')
        url = reverse('admin:admin_faturas_prefatura_faturar', args=[obj.pk])
        csrf_token = get_token(self._current_request)
        # Os filtros da listagem seguem na query string do POST (ver o script
        # de change_list_results_editavel.html).
        return format_html(
            '<button type="button" class="button js-faturar-prefatura" '
            'data-url="{}" data-csrf="{}">Faturar</button>',
            url, csrf_token)
    gerar_fatura_button.short_description = 'Faturamento'
    gerar_fatura_button.allow_tags = True

    def get_top_filter_presets(self, request):
        # Presets de competência e vencimento das pré-faturas.
        hoje = timezone.localdate()
        if hoje.month == 1:
            inicio_anterior = date(hoje.year - 1, 12, 1)
        else:
            inicio_anterior = date(hoje.year, hoje.month - 1, 1)
        if hoje.month == 12:
            inicio_proximo = date(hoje.year + 1, 1, 1)
        else:
            inicio_proximo = date(hoje.year, hoje.month + 1, 1)

        def url_competencia(**filtros):
            params = self._query_params(request)
            for chave in list(params.keys()):
                if chave.startswith((
                    'competencia__', 'dt_vencimento__',
                    'pre_faturado_status', 'pre_faturado__exact',
                )):
                    params.pop(chave, None)
            params.update(filtros)
            query = params.urlencode()
            return f'{request.path}?{query}' if query else request.path
        def competencia_ativa(ano, mes):
            return (request.GET.get('competencia__year') == str(ano)
                    and request.GET.get('competencia__month') == str(mes))

        return [
            {'label': 'Todos', 'url': url_competencia(),
             'active': not any(k.startswith(('competencia__', 'dt_vencimento__'))
                               for k in request.GET)},
            {'label': f'Competência atual ({hoje:%m/%Y})',
             'url': url_competencia(competencia__year=hoje.year,
                                    competencia__month=hoje.month),
             'active': competencia_ativa(hoje.year, hoje.month)},
            {'label': 'Competência anterior',
             'url': url_competencia(competencia__year=inicio_anterior.year,
                                    competencia__month=inicio_anterior.month),
             'active': competencia_ativa(inicio_anterior.year,
                                         inicio_anterior.month)},
            {'label': 'Próxima competência',
             'url': url_competencia(competencia__year=inicio_proximo.year,
                                    competencia__month=inicio_proximo.month),
             'active': competencia_ativa(inicio_proximo.year,
                                         inicio_proximo.month)},
            {'label': 'Vencidas',
             'url': url_competencia(dt_vencimento__lt=hoje.isoformat()),
             'active': request.GET.get('dt_vencimento__lt') == hoje.isoformat()},
            {'label': 'A vencer',
             'url': url_competencia(dt_vencimento__gte=hoje.isoformat()),
             'active': request.GET.get('dt_vencimento__gte') == hoje.isoformat()},
        ]

    dashboard_competencia_field = 'competencia'
    dashboard_vencimento_field = 'dt_vencimento'
    dashboard_valor_field = 'valor'

    # Listagem editável com TODAS as colunas do list_display (ver
    # admin_faturas/changelist_editavel.py).
    def get_changelist(self, request, **kwargs):
        from .changelist_editavel import ChangeListEditavel
        return ChangeListEditavel

    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']

    list_display = ['id', 'convenio', 'cliente',
                    'gerar_fatura_button', 'competencia', 'dia_envio',
                    'dt_vencimento', 'valor',
                    'empenho', 'nr_contrato', 'nr_aditivo','estabelecimento', 'status',]
    list_editable = ['valor', 'empenho', 'status']

    list_display_links = ['id', 'convenio']

    search_fields = ['convenio__convenio', 'empenho',
                     'dia_envio', 'cliente', 'nr_contrato', 'nr_aditivo']
    list_filter = [ConvenioPagadorFilter, StatusFilterAdminMixin,
                   PreFaturadoQueryFilter, EmpenhoPreFaturaFilter,
                   EstabelecimentoFilterAdminMixin,
                   'pagador_pj', 'pagador_pf',
                   'cliente', 'dia_envio', CustomDateFilter]
    ordering = ['competencia', 'convenio', 'cliente', 'nr_contrato',
                'nr_aditivo', 'valor', 'dia_envio', 'pre_faturado', 'id']
    list_per_page = 99

    # ------------------------------------------------------------------
    # DASHBOARD DE PRÉ-FATURAS
    # ------------------------------------------------------------------
    def get_dashboard_kpis(self, request, queryset):
        from django.db.models import Sum
        hoje = timezone.localdate()
        total = queryset.aggregate(t=Sum('valor'))['t'] or 0
        pre_faturado = queryset.filter(pre_faturado=True).aggregate(
            t=Sum('valor'))['t'] or 0
        vencidas = queryset.filter(
            pre_faturado=False, dt_vencimento__lt=hoje).aggregate(
            t=Sum('valor'))['t'] or 0

        return [
            {
                'title': 'Pré-Faturas',
                'value': _qtd(queryset.count()),
                'subtitle': 'Registros no filtro',
                'color_class': 'kpi-blue',
                'icon': 'fa-file-invoice',
            },
            {
                'title': 'Valor Total',
                'value': _money(total),
                'subtitle': 'Soma do valor das pré-faturas',
                'color_class': 'kpi-teal',
                'icon': 'fa-money-bill-wave',
            },
            {
                'title': 'A Faturar',
                'value': _money(total - pre_faturado),
                'subtitle': f'{_qtd(queryset.filter(pre_faturado=False).count())} pendentes',
                'color_class': 'kpi-orange',
                'icon': 'fa-hourglass-half',
            },
            {
                'title': 'Vencidas sem Faturar',
                'value': _money(vencidas),
                'subtitle': f'Vencimento anterior a {hoje:%d/%m/%Y}',
                'color_class': 'kpi-red',
                'icon': 'fa-triangle-exclamation',
            },
            {
                'title': 'Já Faturado',
                'value': _money(pre_faturado),
                'subtitle': f'{_qtd(queryset.filter(pre_faturado=True).count())} convertidas',
                'color_class': 'kpi-green',
                'icon': 'fa-circle-check',
            },
        ]

    def get_top_extra_filters(self, request):
        status = request.GET.get('status')
        pre_faturado = request.GET.get('pre_faturado_status')
        empenho = request.GET.get('empenho_status')
        return [
            self.filtro_todos_status(request, (
                'status', 'pre_faturado_status', 'empenho_status')),
            {
                'label': 'Ativos',
                'url': self._url_com(request, status='A'),
                'active': status == 'A',
                'icon': '✅',
            },
            {
                'label': 'Inativos',
                'url': self._url_com(request, status='I'),
                'active': status == 'I',
                'icon': '🚫',
            },
            {
                'label': 'Faturadas',
                'url': self._url_com(request, pre_faturado_status='sim'),
                'active': pre_faturado == 'sim',
                'icon': '🧾',
            },
            {
                'label': 'Não Faturadas',
                'url': self._url_com(request, pre_faturado_status='nao'),
                'active': pre_faturado == 'nao',
                'icon': '➕',
            },
            {
                'label': 'Com Empenho',
                'url': self._url_com(request, empenho_status='com'),
                'active': empenho == 'com',
                'icon': '📌',
            },
            {
                'label': 'Sem Empenho',
                'url': self._url_com(request, empenho_status='sem'),
                'active': empenho == 'sem',
                'icon': '📌',
            },
        ]
    top_extra_filter_label = 'Status, Pré-Fatura & Empenho'

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Se o objeto já existir (change)
            return self.readonly_fields  # Não altera o comportamento padrão
        else:  # Se for uma nova instância (add)
            # Converter para lista para permitir a concatenação
            return self.readonly_fields + ['pre_faturado', 'status']

    # TODO: AJUSTAR PARA FILTRAR PADRAO OU QQ UM OUTRO

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()
        super().save_model(request, obj, form, change)
        if obj.pre_faturado and not Fatura.objects.filter(
                prefatura_ptr_id=obj.pk).exists():
            obj.create_fatura()

    def has_delete_permission(self, request, obj=None):
        """
        Permitir a exclusão apenas para o usuário 'admin'.
        """
        if request.user.username == 'admin':
            return True
        return False

    def delete_queryset(self, request, queryset):
        """
        Impede a exclusão de qualquer queryset de Fatura e exibe uma mensagem.
        """
        if not self.has_delete_permission(request):
            messages.error(
                request, "Não é possível excluir registros deste tipo.")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/admin/'))
        super().delete_queryset(request, queryset)

    def delete_model(self, request, obj):
        """
        Customização da exclusão do modelo para exibir uma mensagem
        se o usuário não tiver permissão.
        """
        if not self.has_delete_permission(request, obj):
            messages.error(
                request, "Não é possível excluir este objeto.")
            return
        super().delete_model(request, obj)


class ConvenioAdmin(AdminEstabelecimentoPadraoMixin, FaturasDashboardMixin, Select2AdminModelAdminMixin, ExportToXLSMixin, admin.ModelAdmin):
    form = ConvenioForm
    dashboard_competencia_field = 'inicio_vigencia'
    dashboard_vencimento_field = 'final_vigencia'
    dashboard_valor_field = 'valor_mensal'

    def get_top_filter_presets(self, request):
        # A tela de convênios filtra os períodos pela competência e vencimento
        # de suas pré-faturas relacionadas.
        hoje = timezone.localdate()
        if hoje.month == 1:
            competencia_anterior = date(hoje.year - 1, 12, 1)
        else:
            competencia_anterior = date(hoje.year, hoje.month - 1, 1)
        if hoje.month == 12:
            competencia_proxima = date(hoje.year + 1, 1, 1)
        else:
            competencia_proxima = date(hoje.year, hoje.month + 1, 1)

        prefixos_periodo = (
            'prefaturas__competencia__', 'prefaturas__dt_vencimento__',
            'inicio_vigencia__', 'final_vigencia__',
        )
        prefixos_vazios = ('inicio_vigencia__', 'final_vigencia__')

        def url_periodo(**filtros):
            params = self._query_params(request)
            for chave in list(params.keys()):
                if chave.startswith(prefixos_periodo):
                    params.pop(chave, None)
            params.update(filtros)
            query = params.urlencode()
            return f'{request.path}?{query}' if query else request.path
        def competencia_url(ref):
            return url_periodo(**{
                'prefaturas__competencia__year': ref.year,
                'prefaturas__competencia__month': ref.month,
            })

        def competencia_ativa(ref):
            return (
                request.GET.get('prefaturas__competencia__year') == str(ref.year)
                and request.GET.get('prefaturas__competencia__month') == str(ref.month)
            )

        tem_periodo = any(
            chave.startswith(prefixos_periodo)
            and bool(request.GET.get(chave))
            for chave in request.GET
        )
        return [
            {'label': 'Todos', 'url': url_periodo(), 'active': not tem_periodo},
            {
                'label': f'Competência atual ({hoje:%m/%Y})',
                'url': competencia_url(hoje),
                'active': competencia_ativa(hoje),
            },
            {
                'label': 'Competência anterior',
                'url': competencia_url(competencia_anterior),
                'active': competencia_ativa(competencia_anterior),
            },
            {
                'label': 'Próxima competência',
                'url': competencia_url(competencia_proxima),
                'active': competencia_ativa(competencia_proxima),
            },
            {
                'label': 'Vencidas',
                'url': url_periodo(**{
                    'prefaturas__dt_vencimento__lt': hoje.isoformat(),
                }),
                'active': request.GET.get(
                    'prefaturas__dt_vencimento__lt') == hoje.isoformat(),
            },
            {
                'label': 'A vencer',
                'url': url_periodo(**{
                    'prefaturas__dt_vencimento__gte': hoje.isoformat(),
                }),
                'active': request.GET.get(
                    'prefaturas__dt_vencimento__gte') == hoje.isoformat(),
            },
        ]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if any(chave.startswith((
            'prefaturas__competencia__', 'prefaturas__dt_vencimento__',
        )) for chave in request.GET):
            queryset = queryset.distinct()
        return queryset
    def get_top_extra_filters(self, request):
        status = request.GET.get('status')
        pre_faturado = request.GET.get('pre_faturado__exact')
        empenho = request.GET.get('empenho_global_status')
        return [
            self.filtro_todos_status(request, (
                'status', 'pre_faturado__exact', 'empenho_global_status')),
            {'label': 'Ativos', 'url': self._url_com(request, status='A'),
             'active': status == 'A', 'icon': '✅'},
            {'label': 'Inativos', 'url': self._url_com(request, status='I'),
             'active': status == 'I', 'icon': '🚫'},
            {'label': 'Pré-Faturados',
             'url': self._url_com(request, **{'pre_faturado__exact': '1'}),
             'active': pre_faturado == '1', 'icon': '🧾'},
            {'label': 'Sem Pré-Fatura',
             'url': self._url_com(request, **{'pre_faturado__exact': '0'}),
             'active': pre_faturado == '0', 'icon': '➕'},
            {'label': 'Com Empenho',
             'url': self._url_com(request, empenho_global_status='com'),
             'active': empenho == 'com', 'icon': '📌'},
            {'label': 'Sem Empenho',
             'url': self._url_com(request, empenho_global_status='sem'),
             'active': empenho == 'sem', 'icon': '📌'},
        ]

    top_extra_filter_label = 'Status & Pré-Fatura'

    # Listagem editável com TODAS as colunas do list_display (ver
    # admin_faturas/changelist_editavel.py).
    def get_changelist(self, request, **kwargs):
        from .changelist_editavel import ChangeListEditavel
        return ChangeListEditavel

    actions = ['export_as_xls', 'gerar_prefaturas_em_lote']

    @admin.action(description='Gerar pré-faturas dos convênios selecionados')
    def gerar_prefaturas_em_lote(self, request, queryset):
        selecionados = list(queryset)
        gerados = 0
        ignorados = 0
        erros = 0
        for convenio in selecionados:
            if convenio.pre_faturado:
                ignorados += 1
                continue
            try:
                with transaction.atomic():
                    foi_gerado = self._gerar_prefaturas_para_convenio(
                        request, convenio)
                if foi_gerado:
                    gerados += 1
                else:
                    ignorados += 1
            except Exception:
                erros += 1
        if gerados:
            self.message_user(
                request, f'Pré-faturas geradas para {gerados} convênio(s).',
                level=messages.SUCCESS)
        if ignorados:
            self.message_user(
                request,
                f'{ignorados} convênio(s) ignorado(s): já tinham pré-faturas.',
                level=messages.WARNING)
        if erros:
            self.message_user(
                request,
                f'Não foi possível gerar pré-faturas para {erros} convênio(s). '
                'Nenhum dado parcial desses convênios foi salvo.',
                level=messages.ERROR)

    list_display = ['id', 'convenio', 'display_clientes',  'client_count', 'nr_contrato', 'nr_aditivo', 'gerar_prefaturas_button', 'duplicate_button', 'inicio_vigencia', 'final_vigencia', 'dia_envio', 'dias_pagamento', 'valor_mensal', 'valor_diaria',  'empenho_global','total_value',
                    'tx_retencao_nf', 'vl_retencao_nf', 'modo_fatura', 'pagador_pj', 'pagador_pf', 'estabelecimento', 'status']
    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']
    list_filter = (
        ConvenioPagadorFilter, StatusFilterAdminMixin,
        EstabelecimentoFilterAdminMixin,
        EmpenhoConvenioFilter, 'cliente', 'pre_faturado',
        ('prefaturas__competencia', admin.DateFieldListFilter),
        ('prefaturas__dt_vencimento', admin.DateFieldListFilter),
        'dia_envio', 'dias_pagamento', 'modo_fatura', 'dt_registro',
        'us_registro',
    )
    search_fields = ['convenio',]
    list_display_links = ['id', 'convenio']
    list_editable = ['status', 'valor_mensal',
                     'valor_diaria', 'dia_envio', 'dias_pagamento', 'empenho_global']
    list_per_page = 99

    # Recorte da busca do select2: 'cliente' só lista pacientes ativos —
    # o mesmo queryset usado pelo ConvenioForm na validação/salvamento.
    select2_querysets = {
        'cliente': Pessoa.objects.filter(
            classificacao_pessoa='paciente', status='A'),
    }

    # Select2 de digitação em todos os FKs/M2M (cliente, pagador PJ/PF, etc.).
    # 'estabelecimento' é filtrado pelo AutocompleteJsonView (search_fields).
    autocomplete_fields = ('estabelecimento',)

    # ------------------------------------------------------------------
    # DASHBOARD DE CONVÊNIOS
    # ------------------------------------------------------------------
    def get_dashboard_kpis(self, request, queryset):
        hoje = timezone.localdate()
        ativos = queryset.filter(status='A')
        em_vigor = ativos.filter(
            inicio_vigencia__lte=hoje, final_vigencia__gte=hoje).count()
        pre_faturados = queryset.filter(pre_faturado=True).count()
        clientes = queryset.values('cliente__id').distinct().count()
        contratos_vencidos = queryset.filter(final_vigencia__lt=hoje).count()

        return [
            {
                'title': 'Convênios',
                'value': _qtd(queryset.count()),
                'subtitle': f'{_qtd(ativos.count())} ativos',
                'color_class': 'kpi-blue',
                'icon': 'fa-file-invoice',
            },
            {
                'title': 'Em Vigor',
                'value': _qtd(em_vigor),
                'subtitle': 'Vigência na data de hoje',
                'color_class': 'kpi-green',
                'icon': 'fa-calendar-days',
            },
            {
                'title': 'Pré-Faturados',
                'value': _qtd(pre_faturados),
                'subtitle': 'Já geraram pré-faturas',
                'color_class': 'kpi-orange',
                'icon': 'fa-receipt',
            },
            {
                'title': 'Clientes Vinculados',
                'value': _qtd(clientes),
                'subtitle': 'Pacientes nos convênios do filtro',
                'color_class': 'kpi-purple',
                'icon': 'fa-users',
            },
            {
                'title': 'Contratos vencidos',
                'value': _qtd(contratos_vencidos),
                'subtitle': 'Convênios com vigência final anterior a hoje',
                'color_class': 'kpi-teal',
                'icon': 'fa-file-circle-xmark',
            },
        ]

    # Método para controlar campos read-only
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Se o objeto já existir (change)
            return self.readonly_fields  # Não altera o comportamento padrão
        else:  # Se for uma nova instância (add)
            # Converter para lista para permitir a concatenação
            return self.readonly_fields + ['pre_faturado', 'status']

    def save_model(self, request, obj, form, change):
        if not change:  # se estiver criando um novo objeto
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:  # se estiver editando um objeto existente
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()

        super().save_model(request, obj, form, change)

    def display_clientes(self, obj):
        return "; ".join([cliente.nome for cliente in obj.cliente.all()])
    display_clientes.short_description = 'Cliente'

    def client_count(self, obj):
        return obj.cliente.count()
    client_count.short_description = 'Qtd.Cliente(s)'

    def total_value(self, obj):
        valor_mensal = obj.valor_mensal if obj.valor_mensal else 0
        valor_diaria = obj.valor_diaria if obj.valor_diaria else 0
        total = (valor_mensal + (valor_diaria * 30)) * self.client_count(obj)
        return f"{total:.2f}"
    total_value.short_description = 'Vl.Mensal(30 dias)'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('duplicate/<int:convenio_id>/',
                 self.admin_site.admin_view(self.duplicate_view), name='duplicate_convenio'),
            path('gerar_prefaturas/<int:convenio_id>/', self.admin_site.admin_view(
                self.gerar_prefaturas_view), name='gerar_prefaturas'),
        ]
        return custom_urls + urls

    def duplicate_button(self, obj):
        if obj.pre_faturado:
            return format_html('<a class="button" href="{}">Duplicar</a>', reverse('admin:duplicate_convenio', args=[obj.pk]))
        return format_html('<span style="color:gray;">Duplicar</span>')
    duplicate_button.short_description = 'Duplicar'
    duplicate_button.allow_tags = True

    def gerar_prefaturas_button(self, obj):
        if obj.pre_faturado:
            return format_html(
                '<span title="Pré-faturado" style="color:#198754;font-size:18px;'
                'font-weight:bold;">&#10003;</span>')
        return format_html(
            '<a class="button" href="{}">Pré-faturar</a>',
            reverse('admin:gerar_prefaturas', args=[obj.pk]))
    gerar_prefaturas_button.short_description = 'Pré-Fatura'
    gerar_prefaturas_button.allow_tags = True

    def duplicate_view(self, request, convenio_id):
        original_convenio = get_object_or_404(Convenio, pk=convenio_id)
        new_convenio = Convenio.objects.get(pk=original_convenio.pk)
        new_convenio.pk = None
        new_convenio.nr_contrato = f"{original_convenio.nr_contrato}"
        new_convenio.pre_faturado = False
        new_convenio.status = 'A'
        new_convenio.save()
        original_convenio.status = 'I'
        original_convenio.save()
        # Duplicate ManyToMany relationships
        new_convenio.cliente.set(original_convenio.cliente.all())

        messages.success(request, 'Convênio duplicado com sucesso.')
        return redirect('admin:admin_faturas_convenio_change', new_convenio.pk)

    def gerar_prefaturas_view(self, request, convenio_id):
        convenio = get_object_or_404(Convenio, pk=convenio_id)

        if convenio.pre_faturado:
            messages.error(
                request, 'Pré-faturas já foram geradas para este convênio.')
            return redirect('admin:admin_faturas_convenio_changelist')

        try:
            with transaction.atomic():
                self._gerar_prefaturas_para_convenio(request, convenio)
        except ValueError as erro:
            messages.error(request, str(erro))
            return redirect('admin:admin_faturas_convenio_changelist')
        messages.success(request, 'Pré-faturas geradas com sucesso.')
        return redirect('admin:admin_faturas_convenio_changelist')

    def _gerar_prefaturas_para_convenio(self, request, convenio):
        if convenio.pre_faturado:
            return False
        start_date = convenio.inicio_vigencia
        end_date = convenio.final_vigencia
        dia_envio = convenio.dia_envio
        clientes = convenio.cliente.all()

        valor_mensal = Decimal(convenio.valor_mensal or 0)
        valor_diaria = Decimal(convenio.valor_diaria or 0)

        if start_date > end_date:
            raise ValueError('A vigência não contém período faturável.')

        # O número de faturas segue os meses de contrato, não a quantidade
        # de competências que caem estritamente dentro das datas de vigência.
        meses_contrato = (
            (end_date.year - start_date.year) * 12
            + end_date.month - start_date.month
            + (1 if end_date.day >= start_date.day else 0)
        )
        quantidade_faturas = max(1, meses_contrato)

        # Primeira data mensal de envio na vigência (ou logo após seu início),
        # seguida de exatamente uma competência por mês do contrato.
        primeiro_mes = start_date.replace(day=1)
        primeiro_ultimo_dia = calendar.monthrange(
            primeiro_mes.year, primeiro_mes.month)[1]
        primeira_competencia = date(
            primeiro_mes.year, primeiro_mes.month,
            min(dia_envio, primeiro_ultimo_dia))
        if primeira_competencia < start_date:
            if primeiro_mes.month == 12:
                primeiro_mes = date(primeiro_mes.year + 1, 1, 1)
            else:
                primeiro_mes = date(primeiro_mes.year, primeiro_mes.month + 1, 1)

        competencias = []
        mes = primeiro_mes
        for _ in range(quantidade_faturas):
            ultimo_dia = calendar.monthrange(mes.year, mes.month)[1]
            competencias.append(
                date(mes.year, mes.month, min(dia_envio, ultimo_dia)))
            if mes.month == 12:
                mes = date(mes.year + 1, 1, 1)
            else:
                mes = date(mes.year, mes.month + 1, 1)

        periodos_faturamento = []
        for competencia in competencias:
            periodo_inicio, periodo_fim = periodo_cobranca(
                competencia, dia_envio)
            periodo_inicio = max(periodo_inicio, start_date)
            periodo_fim = min(periodo_fim, end_date)
            if periodo_inicio <= periodo_fim:
                periodos_faturamento.append(
                    (competencia, periodo_inicio, periodo_fim))

        # Se sobrar vigência depois do último ciclo mensal, cria uma fatura
        # adicional proporcional no próximo dia de envio (ex.: 01/05 para
        # cobrir 01/04 a 25/04).
        if periodos_faturamento:
            ultima_competencia, _, ultimo_dia_faturado = periodos_faturamento[-1]
            periodo_residual_inicio = ultimo_dia_faturado + timedelta(days=1)
            if periodo_residual_inicio <= end_date:
                if ultima_competencia.month == 12:
                    competencia_residual_mes = date(
                        ultima_competencia.year + 1, 1, 1)
                else:
                    competencia_residual_mes = date(
                        ultima_competencia.year,
                        ultima_competencia.month + 1, 1)
                ultimo_dia_mes = calendar.monthrange(
                    competencia_residual_mes.year,
                    competencia_residual_mes.month)[1]
                competencia_residual = date(
                    competencia_residual_mes.year,
                    competencia_residual_mes.month,
                    min(dia_envio, ultimo_dia_mes),
                )
                periodos_faturamento.append((
                    competencia_residual, periodo_residual_inicio, end_date))

        for competencia, periodo_inicio, periodo_fim in periodos_faturamento:
            dias_cobrados = max(0, (periodo_fim - periodo_inicio).days + 1)
            periodo_padrao_inicio, periodo_padrao_fim = periodo_cobranca(
                competencia, dia_envio)
            periodo_parcial = (
                periodo_inicio > periodo_padrao_inicio
                or periodo_fim < periodo_padrao_fim
            )

            if valor_diaria:
                valor_bruto_por_cliente = valor_diaria * dias_cobrados
            elif periodo_parcial:
                valor_bruto_por_cliente = (
                    valor_mensal / Decimal('30')
                    * Decimal(dias_cobrados)
                ).quantize(Decimal('0.01'))
            else:
                valor_bruto_por_cliente = valor_mensal
            # A pré-fatura guarda sempre o bruto proporcional/integral.
            if convenio.modo_fatura == 'CO':
                total_bruto = valor_bruto_por_cliente * clientes.count()
                cliente_names = "; ".join(
                    [cliente.nome for cliente in clientes])

                pre_fatura = PreFatura(
                    estabelecimento=convenio.estabelecimento,
                    dt_registro=timezone.now(),
                    us_registro=request.user,
                    status='A',
                    convenio=convenio,
                    cliente=cliente_names,
                    nr_contrato=convenio.nr_contrato,
                    nr_aditivo=convenio.nr_aditivo,
                    empenho=convenio.empenho_global,
                    dia_envio=convenio.dia_envio,
                    dias_pagamento=convenio.dias_pagamento,
                    competencia=competencia,
                    pagador_pj=convenio.pagador_pj,
                    pagador_pf=convenio.pagador_pf,
                    valor=total_bruto,
                    dt_vencimento=competencia +
                    timedelta(days=convenio.dias_pagamento)
                )
                pre_fatura.save()
            else:
                for cliente in clientes:
                    pre_fatura = PreFatura(
                        estabelecimento=convenio.estabelecimento,
                        dt_registro=timezone.now(),
                        us_registro=request.user,
                        status='A',
                        convenio=convenio,
                        cliente=cliente.nome,
                        nr_contrato=convenio.nr_contrato,
                        nr_aditivo=convenio.nr_aditivo,
                        empenho=convenio.empenho_global,
                        dia_envio=convenio.dia_envio,
                        dias_pagamento=convenio.dias_pagamento,
                        competencia=competencia,
                        pagador_pj=convenio.pagador_pj,
                        pagador_pf=convenio.pagador_pf,
                        valor=valor_bruto_por_cliente,
                        dt_vencimento=competencia +
                        timedelta(days=convenio.dias_pagamento)
                    )
                    pre_fatura.save()


        convenio.pre_faturado = True
        convenio.save()
        return True
class SaldoFilter(admin.SimpleListFilter):
    title = _('Saldo (Valor positivo)')
    parameter_name = 'saldo'

    def lookups(self, request, model_admin):
        return (
            ('positive', _('Saldo positivo')),
            ('negative', _('Saldo negativo')),
            ('zero', _('Saldo zero')),
            ('all', _('Todos')),  # Adiciona opção para exibir todos
        )

    def queryset(self, request, queryset):
        value = self.value()
        if 'saldo' not in request.GET:
            # Se o filtro de saldo não está na URL, aplica o filtro de saldo positivo por padrão
            return queryset.filter(valor_saldo__gt=0)
        elif value == 'positive':
            return queryset.filter(valor_saldo__gt=0)
        elif value == 'negative':
            return queryset.filter(valor_saldo__lt=0)
        elif value == 'zero':
            return queryset.filter(valor_saldo=0)
        elif value == 'all':
            # Retorna todos os objetos quando 'all' é selecionado ou nenhum filtro é aplicado
            return queryset
        return queryset


class FaturadoStatusFilter(admin.SimpleListFilter):
    title = 'Faturamento'
    parameter_name = 'faturado_status'

    def lookups(self, request, model_admin):
        return (('sim', 'Faturadas'), ('nao', 'Não faturadas'))

    def queryset(self, request, queryset):
        if self.value() == 'sim':
            return queryset.filter(faturado=True)
        if self.value() == 'nao':
            return queryset.filter(faturado=False)
        return queryset
class ArquivoNotaFiscalFilter(admin.SimpleListFilter):
    title = 'Anexo NF'
    parameter_name = 'anexo_nf_status'

    def lookups(self, request, model_admin):
        return (('com', 'Com anexo'), ('sem', 'Sem anexo'))

    def queryset(self, request, queryset):
        if self.value() == 'com':
            return queryset.exclude(anexo_nf__isnull=True).exclude(anexo_nf='')
        if self.value() == 'sem':
            from django.db.models import Q
            return queryset.filter(Q(anexo_nf__isnull=True) | Q(anexo_nf=''))
        return queryset
class NotaFiscalFilter(admin.SimpleListFilter):
    title = 'Nota Fiscal'
    parameter_name = 'nota_fiscal_status'

    def lookups(self, request, model_admin):
        return (('com', 'Com NF'), ('sem', 'Sem NF'))

    def queryset(self, request, queryset):
        from django.db.models import Q
        if self.value() == 'com':
            return queryset.exclude(nr_nota_fiscal__isnull=True).exclude(
                nr_nota_fiscal__in=('', 'N/A'))
        if self.value() == 'sem':
            return queryset.filter(
                Q(nr_nota_fiscal__isnull=True)
                | Q(nr_nota_fiscal__in=('', 'N/A'))
            )
        return queryset


class BaixaFaturaInline(admin.TabularInline):
    """Baixas (recebimentos) da fatura, dentro do formulário da FATURA.

    Uma fatura tem VÁRIAS baixas: aqui o usuário registra/edita os
    recebimentos parciais sem sair da tela da fatura. O `fatura_baixada`
    (M2M) não aparece no inline: é justamente o vínculo com a fatura aberta,
    fixado pelo `save_formset` de quem hospeda o inline.
    """

    model = BaixaFatura
    form = BaixaFaturaForm
    # A baixa tem MAIS DE UM vínculo com Fatura (parent link `fatura_ptr` +
    # o M2M `fatura_baixada`): sem dizer qual, o formset não sabe a FK.
    fk_name = 'fatura_ptr'
    extra = 0
    can_delete = True
    show_change_link = True
    fields = ('valor_baixa', 'dt_recebimento', 'transacao_financeira',
              'competencia_bancaria', 'observacao')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'transacao_financeira', 'competencia_bancaria')

    def get_formset(self, request, obj=None, **kwargs):
        """O form do inline conhece a fatura (cópia herdada/telas)."""
        base = super().get_formset(request, obj, **kwargs)
        FormOriginal = base.form

        # O queryset do formset filtra pelo parent link (`fatura_ptr`) — mas
        # cada baixa tem o PRÓPRIO retrato (linha pai criada no save), então
        # as baixas da fatura aberta NÃO estão lá. O vínculo real é o M2M
        # `fatura_baixada`: filtra por ele (e o `fk_name` continua o
        # `fatura_ptr`, que é o que o formset usa para ligar novas linhas).
        class FormSetComM2M(base):
            def get_queryset(self):
                if self.instance is not None and self.instance.pk:
                    # SUBSTITUI o queryset (não acrescenta filtro): o base
                    # já vem com `fatura_ptr = fatura aberta` — mas cada baixa
                    # tem o PRÓPRIO retrato (linha pai criada no save), então
                    # nenhuma baixa tem esse parent link e o filtro do base
                    # devolveria sempre vazio. O vínculo real é o M2M.
                    return BaixaFatura.objects.filter(
                        fatura_baixada__in=[self.instance.pk]
                    ).order_by('-dt_recebimento')
                return super().get_queryset()

            def add_fields(self, form, index):
                # O fk (`fatura_ptr`) É a pk da baixa: o Django já trata este
                # caso (`self._pk_field == self.fk` → InlineForeignKeyField
                # pk_field=True). Só que o `initial` dele é a pk da INSTÂNCIA
                # DO FORMSET (a fatura aberta) — e aqui cada baixa tem o
                # PRÓPRIO retrato (pk diferente). Corrige por linha: o valor
                # hidden tem de ser a pk DA BAIXA (que é o fatura_ptr dela).
                super().add_fields(form, index)
                campo = form.fields.get('fatura_ptr')
                if campo is not None:
                    # O fk (`fatura_ptr`) É a pk da baixa — e cada baixa tem o
                    # PRÓPRIO retrato. O campo precisa EXISTIR (o
                    # `_construct_form` do base o exige), mas como
                    # IntegerField opcional: o `construct_instance` IGNORA
                    # (o campo do modelo é auto_created, editable=False) e o
                    # `InlineForeignKeyField` (que validaria contra a fatura
                    # aberta) sai. O valor real vai no hidden `pk_linha`,
                    # usado pelo `_construct_form` abaixo.
                    from django import forms as _forms
                    form.fields['fatura_ptr'] = _forms.IntegerField(
                        required=False, widget=_forms.HiddenInput)
                    form.fields['pk_linha'] = _forms.IntegerField(
                        required=False, widget=_forms.HiddenInput)
                    if form.instance is not None and form.instance.pk:
                        form.fields['pk_linha'].initial = form.instance.pk

            def _construct_form(self, i, **kwargs):
                form = super()._construct_form(i, **kwargs)
                # Reaponta a instância do form para a baixa REAL da linha (a
                # pk vem do hidden `pk_linha` no POST; no GET, do queryset).
                pk_linha = None
                if form.is_bound:
                    try:
                        pk_linha = int(form.data.get(
                            form.add_prefix('pk_linha')) or 0)
                    except (TypeError, ValueError):
                        pk_linha = None
                else:
                    pk_linha = form.instance.pk
                if pk_linha and pk_linha != form.instance.pk:
                    obj = BaixaFatura.objects.filter(pk=pk_linha).first()
                    if obj is not None:
                        form.instance = obj
                return form

        FormSetComM2M.__name__ = base.__name__
        FormSetComM2M.__qualname__ = base.__qualname__
        base = FormSetComM2M

        class FormComFatura(FormOriginal):
            def __init__(self, *args, **form_kwargs):
                if obj is not None:
                    form_kwargs.setdefault('fatura_origem', obj)
                super().__init__(*args, **form_kwargs)

        FormComFatura.__name__ = FormOriginal.__name__
        FormComFatura.__qualname__ = FormOriginal.__qualname__
        base.form = FormComFatura
        return base


class FaturaAdmin(AdminEstabelecimentoPadraoMixin, FaturasDashboardMixin, Select2AdminModelAdminMixin, ExportToXLSMixin, admin.ModelAdmin):
    dashboard_competencia_field = 'competencia'
    dashboard_vencimento_field = 'dt_vencimento'
    dashboard_valor_field = 'valor_fatura'
    dashboard_saldo_field = 'valor_saldo'
    dashboard_enable_faturado_shortcuts = False
    # `faturado` deixa de ser editado pelo checkbox da linha: é o botão
    # "Finalizar fatura", que faz POST na própria fatura (ver
    # `finalizar_fatura_view`). O checkbox continua disponível para a ação
    # em lote "Finalizar faturas selecionadas".
    selecao_desabilitada = False
    # Filtros da changelist em que o botão "Finalizar fatura" aparece: pares
    # (parâmetro, valor). Fora deles (ex.: "Fatura Finalizada") a linha só
    # exibe o check — finalizar não faz sentido e o botão faria a linha
    # desaparecer do recorte. Vazio = botão em todas as linhas abertas.
    finalizar_fatura_apenas_com_filtro = (('faturado_status', 'nao'),)

    def get_top_filter_presets(self, request):
        # Presets de competência e vencimento iguais aos da pré-fatura.
        return PreFaturaAdmin.get_top_filter_presets(self, request)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/finalizar/',
                self.admin_site.admin_view(self.finalizar_fatura_view),
                name='admin_faturas_fatura_finalizar',
            ),
        ]
        return custom_urls + urls
    def finalizar_fatura_view(self, request, object_id):
        """Alterna SOMENTE o campo `faturado` da fatura clicada.

        Os demais campos não são tocados (nada de serialize de formset, logo
        as outras linhas e seus ids ficam como estão) e os filtros da
        listagem voltam pela `return_to`.
        """
        if request.method != 'POST':
            return HttpResponseRedirect(
                reverse('admin:admin_faturas_fatura_changelist'))

        fatura = get_object_or_404(Fatura, pk=object_id)
        fatura.faturado = not fatura.faturado
        fatura.us_atualizacao = request.user
        fatura.dt_atualizacao = timezone.now()
        fatura.save(update_fields=['faturado', 'us_atualizacao',
                                   'dt_atualizacao'])
        estado = 'faturada' if fatura.faturado else 'reaberta'
        messages.success(
            request, f'Fatura {fatura.pk} marcada como {estado}.')

        return_to = request.POST.get('return_to', '')
        if not url_has_allowed_host_and_scheme(
                return_to, allowed_hosts={request.get_host()},
                require_https=request.is_secure()):
            return_to = reverse('admin:admin_faturas_fatura_changelist')
        return redirect(return_to)

    def filtro_fatura_aberta_ativo(self, request):
        """A listagem está recortada em "Fatura Aberta" (faturado="nao")?"""
        return (request.GET.get('faturado_status') == 'nao'
                or request.GET.get('faturado__exact') == 'False')

    def botao_finalizar_visivel(self, request):
        """Aplica `finalizar_fatura_apenas_com_filtro` à listagem atual."""
        exigidos = self.finalizar_fatura_apenas_com_filtro
        if not exigidos:
            return True
        if self.filtro_fatura_aberta_ativo(request):
            return True
        return any(request.GET.get(chave) == valor for chave, valor in exigidos)

    def finalizar_fatura_button(self, obj):
        request = self._current_request
        if obj.faturado or not self.botao_finalizar_visivel(request):
            return format_html(
                '<span title="Faturada" style="color:#198754;font-size:18px;'
                'font-weight:bold;">&#10003;</span>')
        url = reverse('admin:admin_faturas_fatura_finalizar', args=[obj.pk])
        csrf_token = get_token(request)
        # Os filtros da listagem seguem na query string do POST (ver o script
        # de change_list_results_editavel.html), então a linha volta no mesmo
        # recorte e o Django preserva todos os filtros aplicados.
        return format_html(
            '<button type="button" class="button js-faturar-prefatura" '
            'data-url="{}" data-csrf="{}">Finalizar fatura</button>',
            url, csrf_token)
    finalizar_fatura_button.short_description = 'Finalizar Fatura'
    finalizar_fatura_button.allow_tags = True
    def changelist_view(self, request, extra_context=None):
        self._current_request = request
        return super().changelist_view(request, extra_context=extra_context)

    def get_list_display(self, request):
        self._current_request = request
        return super().get_list_display(request)

    # Listagem editável com TODAS as colunas do list_display (ver
    # admin_faturas/changelist_editavel.py).
    def get_changelist(self, request, **kwargs):
        from .changelist_editavel import ChangeListEditavel
        return ChangeListEditavel

    actions = ['export_as_xls', 'finalizar_faturas_em_lote']

    @admin.action(description='Finalizar faturas selecionadas')
    def finalizar_faturas_em_lote(self, request, queryset):
        """Marca `faturado=True` apenas nas faturas selecionadas.

        As já faturadas são ignoradas e cada linha é atualizada em sua própria
        transação, então uma falha não desfaz as demais. Só o campo `faturado`
        (e a auditoria) é gravado.
        """
        agora = timezone.now()
        finalizadas = 0
        ja_faturadas = 0
        erros = 0
        for fatura in queryset:
            if fatura.faturado:
                ja_faturadas += 1
                continue
            try:
                with transaction.atomic():
                    fatura.faturado = True
                    fatura.us_atualizacao = request.user
                    fatura.dt_atualizacao = agora
                    fatura.save(update_fields=[
                        'faturado', 'us_atualizacao', 'dt_atualizacao',
                    ])
                finalizadas += 1
            except Exception:
                erros += 1
        if finalizadas:
            self.message_user(
                request, f'{finalizadas} fatura(s) finalizada(s) com sucesso.',
                level=messages.SUCCESS)
        if ja_faturadas:
            self.message_user(
                request, f'{ja_faturadas} fatura(s) já estavam finalizadas; '
                'foram ignoradas.', level=messages.WARNING)
        if erros:
            self.message_user(
                request, f'Falha ao finalizar {erros} fatura(s). '
                'As outras selecionadas foram processadas normalmente.',
                level=messages.ERROR)

    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao', 'pre_faturado']

    # Cada fatura recebe VÁRIAS baixas (recebimentos parciais) direto no seu
    # formulário.
    inlines = [BaixaFaturaInline]

    def save_formset(self, request, form, formset, change):
        """Amarra cada baixa do inline à fatura que está sendo editada."""
        instancias = formset.save(commit=False)
        for instancia in instancias:
            if isinstance(instancia, BaixaFatura):
                if instancia._state.adding:
                    instancia.us_registro_baixa = request.user
                    instancia.status = 'A'
                    # O `save_new` do formset apontou o parent link para a
                    # fatura aberta (`fatura_ptr_id = 102`): como a pk da
                    # baixa É o parent link, gravar faria UPDATE da baixa
                    # herdada de mesma pk. Zera: o `save()` do modelo cria o
                    # retrato próprio.
                    instancia.fatura_ptr_id = None
                    instancia.pk = None
                else:
                    instancia.us_atualizacao_baixa = request.user
                instancia.fatura = form.instance
                # Baixa NOVA: a cópia herdada (NOT NULL) é preenchida a partir
                # da fatura aberta, no save() do modelo.
                instancia._herdados_congelados = not instancia._state.adding
                instancia.save()
                # Garante o vínculo M2M com a fatura aberta.
                if instancia.pk_fatura_baixada() != form.instance.pk:
                    instancia.fatura_baixada.set([form.instance])
        for obj in formset.deleted_objects:
            obj.delete()
        formset.save_m2m()

    list_display_links = ('id', 'convenio')

    search_fields = ('cliente__nome', 'id')

    form = FaturaForm

    list_display = ['id', 'convenio', 'cliente', 'get_documento_pagador', 'finalizar_fatura_button', 'periodo_tratamento', 'competencia', 'dia_envio', 'dt_vencimento', 'valor', 'valor_fatura', 'valor_saldo',
                    'dt_liquidacao', 'descricao', 'nr_nota_fiscal', 'anexo_nf', 'estabelecimento', 'status', ]
    list_editable = ['valor_fatura', 'descricao', 'nr_nota_fiscal', 'anexo_nf', 'status']
    search_fields = ['convenio__convenio',
                     'nr_contrato', 'nr_aditivo', 'descricao', 'nr_nota_fiscal']
    list_filter = [FaturadoStatusFilter, NotaFiscalFilter, ArquivoNotaFiscalFilter,
                   SaldoFilter, ConvenioPagadorFilter, StatusFilterAdminMixin,
                   EstabelecimentoFilterAdminMixin,
                   'pagador_pj', 'pagador_pf', 'cliente', 'dia_envio', CustomDateFilter]
    ordering = ['competencia', 'convenio', 'cliente',
                'nr_contrato', 'nr_aditivo', 'valor', 'dia_envio', 'faturado', 'id']
    list_per_page = 99

    # ------------------------------------------------------------------
    # DASHBOARD DE FATURAS
    # ------------------------------------------------------------------
    def get_dashboard_kpis(self, request, queryset):
        from django.db.models import Sum
        hoje = timezone.localdate()
        total = queryset.aggregate(t=Sum('valor_fatura'))['t'] or 0
        saldo = queryset.aggregate(t=Sum('valor_saldo'))['t'] or 0
        recebido = total - saldo
        em_aberto = queryset.filter(valor_saldo__gt=0).aggregate(
            t=Sum('valor_saldo'))['t'] or 0
        vencidas = queryset.filter(
            valor_saldo__gt=0, dt_vencimento__lt=hoje).aggregate(
            t=Sum('valor_saldo'))['t'] or 0

        return [
            {
                'title': 'Faturas',
                'value': _qtd(queryset.count()),
                'subtitle': f"{_qtd(queryset.filter(faturado=True).count())} faturadas",
                'color_class': 'kpi-blue',
                'icon': 'fa-file-invoice',
            },
            {
                'title': 'Valor das Faturas',
                'value': _money(total),
                'subtitle': 'Soma do valor das faturas',
                'color_class': 'kpi-teal',
                'icon': 'fa-money-bill-wave',
            },
            {
                'title': 'Recebido',
                'value': _money(recebido),
                'subtitle': 'Faturado menos saldo em aberto',
                'color_class': 'kpi-green',
                'icon': 'fa-circle-check',
            },
            {
                'title': 'Total Saldo em Aberto',
                'value': _money(em_aberto),
                'subtitle': f"{_qtd(queryset.filter(valor_saldo__gt=0).count())} com saldo",
                'color_class': 'kpi-orange',
                'icon': 'fa-sack-dollar',
            },
            {
                'title': 'Saldo Vencido em Aberto',
                'value': _money(vencidas),
                'subtitle': f'Vencimento anterior a {hoje:%d/%m/%Y}',
                'color_class': 'kpi-red',
                'icon': 'fa-triangle-exclamation',
            },
        ]

    def get_top_extra_filters(self, request):
        faturado = request.GET.get('faturado_status')
        nf_status = request.GET.get('nota_fiscal_status')
        anexo_status = request.GET.get('anexo_nf_status')
        filtros = [
            self.filtro_todos_status(request, (
                'status', 'faturado_status', 'faturado',
                'nota_fiscal_status', 'anexo_nf_status', 'saldo',
                'valor_saldo__gt', 'valor_saldo__lte')),
            {
                'label': 'Fatura Finalizada',
                'url': self._url_com(request, faturado_status='sim'),
                'active': faturado == 'sim',
                'icon': '🧾',
            },
            {
                'label': 'Fatura Aberta',
                'url': self._url_com(request, faturado_status='nao'),
                'active': faturado == 'nao',
                'icon': '➕',
            },
        ]
        filtros += [
            {
                'label': 'Com NF',
                'url': self._url_com(request, nota_fiscal_status='com'),
                'active': nf_status == 'com',
                'icon': '📄',
            },
            {
                'label': 'Sem NF',
                'url': self._url_com(request, nota_fiscal_status='sem'),
                'active': nf_status == 'sem',
                'icon': '📄',
            },
            {
                'label': 'Com anexo',
                'url': self._url_com(request, anexo_nf_status='com'),
                'active': anexo_status == 'com',
                'icon': '📎',
            },
            {
                'label': 'Sem anexo',
                'url': self._url_com(request, anexo_nf_status='sem'),
                'active': anexo_status == 'sem',
                'icon': '📎',
            },
        ]
        return filtros
    top_extra_filter_label = 'Faturamento, NF & Anexo'

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Se o objeto já existir (change)
            return self.readonly_fields  # Não altera o comportamento padrão
        else:  # Se for uma nova instância (add)
            # Converter para lista para permitir a concatenação
            return self.readonly_fields + ['faturado', 'status']

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
            obj.valor_saldo = obj.valor_fatura
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()
        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        """
        Permitir a exclusão apenas para o usuário 'admin'.
        """
        if request.user.username == 'admin':
            return True
        return False

    def delete_queryset(self, request, queryset):
        """
        Impede a exclusão de qualquer queryset de Fatura e exibe uma mensagem.
        """
        if not self.has_delete_permission(request):
            messages.error(
                request, "Não é possível excluir registros deste tipo.")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/admin/'))
        super().delete_queryset(request, queryset)

    def delete_model(self, request, obj):
        """
        Customização da exclusão do modelo para exibir uma mensagem
        se o usuário não tiver permissão.
        """
        if not self.has_delete_permission(request, obj):
            messages.error(
                request, "Não é possível excluir este objeto.")
            return
        super().delete_model(request, obj)


    def get_documento_pagador(self, obj):
        """
        Retorna CNPJ se Pagador PJ
        Retorna CPF se Pagador PF
        """
        if obj.pagador_pj and hasattr(obj.pagador_pj, 'cnpj'):
            return obj.pagador_pj.cnpj

        if obj.pagador_pf and hasattr(obj.pagador_pf, 'cpf'):
            return obj.pagador_pf.cpf

        return "-"

        get_documento_pagador.short_description = "CNPJ / CPF"

    # Este nao pode utilizar AdminEstabelecimentoMixin porque tem outros filtros associados ao get_form

# TODO: APOS IMPLANTAR O CAIXA, FIELD COMPETENCIA_CAIXA NA TRANSACAO_FINANCEIRA DE MOVIMENTO IGUAL CAIXA


class SaldoFaturaFilter(SaldoFilter):
    """Saldo da fatura listada: em aberto, baixada (liquidada) ou ambas.

    A listagem é de FATURAS: o mesmo filtro de saldo da listagem de baixas,
    reaproveitado — o título fica o da listagem de baixas."""
    title = 'Saldo'
    parameter_name = 'saldo'

    def lookups(self, request, model_admin):
        return (
            ('aberto', 'Com saldo (em aberto)'),
            ('zero', 'Sem saldo (baixada)'),
        )

    def queryset(self, request, queryset):
        valor = self.value()
        # A listagem editável monta os `used_parameters` como lista.
        if isinstance(valor, (list, tuple)):
            valor = valor[0] if valor else None
        if valor == 'aberto':
            return queryset.filter(valor_saldo__gt=0)
        if valor == 'zero':
            return queryset.filter(valor_saldo__lte=0)
        return queryset


class DataRecebimentoFilter(admin.SimpleListFilter):
    """Data de recebimento das baixas já registradas da fatura.

    A listagem é de FATURAS: o filtro entra pelas baixas ligadas a ela
    (M2M `fatura_baixada`)."""
    title = 'Data de Recebimento'
    parameter_name = 'dt_recebimento'

    def lookups(self, request, model_admin):
        return (
            ('hoje', 'Hoje'),
            ('mes', 'Neste mês'),
            ('nao', 'Sem recebimento'),
        )

    def queryset(self, request, queryset):
        valor = self.value()
        if isinstance(valor, (list, tuple)):
            valor = valor[0] if valor else None
        hoje = timezone.localdate()
        if valor == 'hoje':
            return queryset.filter(
                baixas__dt_recebimento=hoje).distinct()
        if valor == 'mes':
            return queryset.filter(
                baixas__dt_recebimento__year=hoje.year,
                baixas__dt_recebimento__month=hoje.month).distinct()
        if valor == 'nao':
            return queryset.exclude(baixas__isnull=False).distinct()
        return queryset


class CompetenciaBancariaFilter(admin.SimpleListFilter):
    """Competência bancária das baixas ligadas à fatura listada."""
    title = 'Competência Bancária'
    parameter_name = 'competencia_bancaria'

    def lookups(self, request, model_admin):
        return (
            ('aberta', 'Competência aberta'),
            ('fechada', 'Competência fechada'),
            ('sem', 'Sem competência'),
        )

    def queryset(self, request, queryset):
        valor = self.value()
        if isinstance(valor, (list, tuple)):
            valor = valor[0] if valor else None
        if valor == 'aberta':
            return queryset.filter(
                baixas__competencia_bancaria__dt_fechamento_competencia=None,
                baixas__competencia_bancaria__isnull=False,
            ).distinct()
        if valor == 'fechada':
            return queryset.filter(
                baixas__competencia_bancaria__dt_fechamento_competencia=None,
            ).exclude(
                baixas__competencia_bancaria=None,
            ).distinct()
        if valor == 'sem':
            return queryset.exclude(baixas__competencia_bancaria=None) \
                .exclude(baixas__isnull=False).distinct()
        return queryset


class ClienteFaturaFilter(admin.SimpleListFilter):
    """Cliente (campo texto livre da fatura) — busca por início do nome."""
    title = 'Cliente'
    parameter_name = 'cliente_filtro'

    def lookups(self, request, model_admin):
        clientes = (Fatura.objects.filter(faturado=True, status='A')
                    .exclude(cliente__isnull=True).exclude(cliente='')
                    .values_list('cliente', flat=True).distinct())
        # O campo `cliente` acumula VÁRIOS nomes separados por ';': a opção
        # lista os PRIMEIROS nomes distintos (até 30) para não virar lista
        # infinita.
        nomes = {}
        for valor in clientes:
            for parte in str(valor).split(';'):
                parte = parte.strip()
                if parte and parte not in nomes:
                    nomes[parte] = len(nomes) + 1
                if len(nomes) >= 30:
                    break
            if len(nomes) >= 30:
                break
        return [(f'c{chave}', nome) for nome, chave in sorted(
            nomes.items(), key=lambda item: item[1])]

    def queryset(self, request, queryset):
        valor = self.value()
        if isinstance(valor, (list, tuple)):
            valor = valor[0] if valor else None
        if not valor or not valor.startswith('c'):
            return queryset
        indice = int(valor[1:]) - 1
        clientes = (Fatura.objects.filter(faturado=True, status='A')
                    .exclude(cliente__isnull=True).exclude(cliente='')
                    .values_list('cliente', flat=True).distinct())
        nomes = []
        for valor_cliente in clientes:
            for parte in str(valor_cliente).split(';'):
                parte = parte.strip()
                if parte and parte not in nomes:
                    nomes.append(parte)
        if indice < len(nomes):
            return queryset.filter(cliente__icontains=nomes[indice]) \
                .distinct()
        return queryset


class VencimentoDateFilter(CustomDateFilter):
    """Filtro de data da barra lateral para o VENCIMENTO da fatura listada.

    O `CustomDateFilter` (competência) serve de base: só troca o campo e o
    parâmetro — o `<input type="date">` e a leitura da URL são os mesmos."""
    title = _('Vencimento')
    parameter_name = 'dt_vencimento'

    def queryset(self, request, queryset):
        valor = self.value()
        if isinstance(valor, (list, tuple)):
            valor = valor[0] if valor else None
        if valor:
            try:
                date_obj = datetime.strptime(valor, '%Y-%m-%d')
                return queryset.filter(dt_vencimento=date_obj)
            except (ValueError, TypeError):
                return queryset
        return queryset


class BaixaFaturaAdmin(AdminEstabelecimentoPadraoMixin, FaturasDashboardMixin, Select2AdminModelAdminMixin, ExportToXLSMixin, admin.ModelAdmin):
    form = BaixaFaturaForm

    # Baixa não tem competência/vencimento próprios: o período é o recebimento.
    dashboard_competencia_field = 'dt_recebimento'
    dashboard_vencimento_field = 'dt_recebimento'
    dashboard_valor_field = 'valor_baixa'

    # Listagem com o cabeçalho padrão de cada ModelAdmin (ver
    # admin_faturas/changelist_editavel.py): sem este `get_changelist` o template
    # de listagem editável não é usado e o <thead> fica sem o checkbox
    # "selecionar todos". A edição em linha continua desligada.
    def get_changelist(self, request, **kwargs):
        from .changelist_editavel import ChangeListBaixaFatura
        return ChangeListBaixaFatura

    actions = ['export_as_xls']

    # O template da listagem editável lê este atributo.
    selecao_desabilitada = False

    # A listagem é das FATURAS finalizadas em aberto (contas a receber).
    # Colunas de identificação vêm da fatura; só os campos exclusivos da
    # baixa são editáveis.
    list_display = (
        'id', 'convenio', 'cliente', 'competencia', 'dt_vencimento',
        'valor_fatura', 'valor_saldo', 'estabelecimento',
        'valor_baixa', 'valor_adicional', 'valor_total_empacotado',
        'dt_recebimento', 'transacao_financeira',
        'competencia_bancaria', 'observacao',
    )

    list_editable = [
        'valor_baixa', 'valor_adicional', 'dt_recebimento',
        'transacao_financeira', 'competencia_bancaria', 'observacao',
    ]

    list_display_links = ['id']

    search_fields = ('id', 'convenio__convenio', 'cliente',
                     'nr_nota_fiscal', 'convenio__pagador_pj__empresa',
                     'convenio__pagador_pf__nome')

    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']

    # O form do admin edita SÓ os campos próprios da baixa: os HERDADOS são
    # cópia do estado da fatura no recebimento (preenchidos pelo
    # `save()`/`_post_clean` do form) — exibi-los editáveis gravaria valores
    # dessincronizados com a fatura.
    fields = ('fatura_baixada', 'valor_baixa', 'valor_adicional',
              'baixas_empacotadas', 'dt_recebimento',
              'transacao_financeira', 'competencia_bancaria', 'observacao')

    list_filter = [VencimentoDateFilter, CustomDateFilter,
                   ConvenioPagadorFilter, SaldoFaturaFilter,
                   StatusFilterAdminMixin, EstabelecimentoFilterAdminMixin,
                   ClienteFaturaFilter, DataRecebimentoFilter,
                   CompetenciaBancariaFilter]

    # A ordenação padrão do modelo (`-dt_recebimento`) não existe na fatura
    # listada: as contas a receber saem por vencimento.
    ordering = ['dt_vencimento', 'id']

    list_per_page = 99

    # ------------------------------------------------------------------
    # CONJUNTO DE TRABALHO: faturas finalizadas com saldo
    # ------------------------------------------------------------------
    def faturas_pendentes(self, request):
        """Faturas finalizadas, ativas, do estabelecimento da sessão.

        É a base da listagem: cada linha é uma fatura em que o usuário pode
        lançar a baixa. O padrão recorta pelo VENCIMENTO DO MÊS ATUAL (a
        conta a receber do mês); os filtros laterais/da barra superior podem
        ampliar (vencidas, a vencer, outros meses) — e o filtro "Saldo"
        decide entre com/sem saldo (o padrão traz AMBAS: uma fatura já
        parcialmente baixada ainda pode receber outra baixa).
        """
        hoje = timezone.localdate()
        base = {'faturado': True}
        # O status 'A' é o PADRÃO: vale enquanto o filtro lateral de status
        # não pedir outro ('I' = inativas; aí a base não força e o filtro
        # aplica a escolha do usuário).
        if not any(chave.startswith('status') for chave in request.GET):
            base['status'] = 'A'
        # O recorte "vencimento do mês atual" é o PADRÃO: vale enquanto o
        # usuário não pedir outro vencimento/competência (aí os filtros da
        # URL mandam — inclusive "Todos", que limpa o recorte do mês).
        filtro_periodo = any(chave.startswith(('dt_vencimento', 'competencia'))
                             for chave in request.GET)
        if not filtro_periodo:
            base['dt_vencimento__year'] = hoje.year
            base['dt_vencimento__month'] = hoje.month
        faturas = Fatura.objects.filter(
            **base).select_related('convenio', 'estabelecimento')

        perfil = getattr(request.user, 'perfil', None)
        if perfil is not None:
            estabelecimento, liberado = self._estabelecimento_da_sessao(
                request, perfil)
            # O estabelecimento da sessão é o PADRÃO: quando o usuário filtra
            # por outro (dropdown do topo / filtro lateral), a base NÃO
            # restringe — o filtro escolhido prevalece. O recorte de segurança
            # (só estabelecimentos liberados no perfil) fica no filtro.
            filtro_estab = any(
                chave.startswith('estabelecimento') for chave in request.GET)
            if not filtro_estab:
                if estabelecimento is not None and liberado:
                    faturas = faturas.filter(estabelecimento=estabelecimento)
                else:
                    faturas = faturas.filter(
                        estabelecimento__in=perfil.estabelecimento.all())
        return faturas

    def get_list_select_related(self, request):
        return []

    # ------------------------------------------------------------------
    # DASHBOARD DE BAIXAS DE FATURA
    # ------------------------------------------------------------------
    def get_dashboard_kpis(self, request, queryset):
        from django.db.models import Sum
        hoje = timezone.localdate()
        total = queryset.aggregate(t=Sum('valor_baixa'))['t'] or 0
        mes = queryset.filter(
            dt_recebimento__year=hoje.year, dt_recebimento__month=hoje.month
        ).aggregate(t=Sum('valor_baixa'))['t'] or 0
        # M2M: a fatura baixada está no vínculo, não numa coluna da baixa.
        faturas = queryset.values('fatura_baixada').distinct().count()

        return [
            {
                'title': 'Baixas',
                'value': _qtd(queryset.count()),
                'subtitle': 'Recebimentos no filtro',
                'color_class': 'kpi-blue',
                'icon': 'fa-file-invoice',
            },
            {
                'title': 'Valor Recebido',
                'value': _money(total),
                'subtitle': 'Soma das baixas',
                'color_class': 'kpi-green',
                'icon': 'fa-money-bill-wave',
            },
            {
                'title': f'Recebido em {hoje:%m/%Y}',
                'value': _money(mes),
                'subtitle': 'Baixas do mês atual',
                'color_class': 'kpi-teal',
                'icon': 'fa-calendar-days',
            },
            {
                'title': 'Faturas Baixadas',
                'value': _qtd(faturas),
                'subtitle': 'Faturas distintas',
                'color_class': 'kpi-purple',
                'icon': 'fa-receipt',
            },
        ]
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)

        if 'HTTP_REFERER' in request.META:
            referer_path = request.META['HTTP_REFERER'].split(
                request.META['HTTP_HOST'])[1]
            if '/add/' in referer_path or '/change/' in referer_path:
                queryset = queryset.filter(status='A')

        return queryset, use_distinct

    def get_top_dropdown_subfilters(self, request):
        """Select de ESTABELECIMENTO no topo: o padrão é o estabelecimento da
        sessão (ou os do perfil); aqui o usuário pode trocar/recortar mais."""
        from admin_cadastros.models import Estabelecimento
        perfil = getattr(request.user, 'perfil', None)
        if perfil is None:
            estabelecimentos = Estabelecimento.objects.filter(status='A')
        else:
            estabelecimentos = perfil.estabelecimento.filter(status='A')
        opcoes = [(str(e.pk), str(e)) for e in estabelecimentos]
        if not opcoes:
            return []
        atual = request.GET.get('estabelecimento__id__exact') or \
            request.GET.get('estabelecimento')
        return [{
            'label': 'Estabelecimento',
            'name': 'estabelecimento',
            'value': atual or '',
            'options': [{'value': '', 'label': 'Todos os meus'}] + [
                {'value': valor, 'label': rotulo} for valor, rotulo in opcoes],
        }]

    def get_top_filter_presets(self, request):
        """Presets da barra superior: VENCIMENTO (padrão = mês atual) e
        competência. O "Venc. mês atual" é o padrão da listagem — quando nada
        é filtrado, a base (`faturas_pendentes`) já recorta o mês."""
        hoje = timezone.localdate()
        ano, mes = hoje.year, hoje.month
        if mes == 1:
            mes_anterior = date(ano - 1, 12, 1)
        else:
            mes_anterior = date(ano, mes - 1, 1)
        if mes == 12:
            mes_proximo = date(ano + 1, 1, 1)
        else:
            mes_proximo = date(ano, mes + 1, 1)

        def url_venc(**filtros):
            params = self._query_params(request)
            for chave in list(params.keys()):
                if chave.startswith(('dt_vencimento__', 'competencia__')):
                    params.pop(chave, None)
            params.update(filtros)
            query = params.urlencode()
            return f'{request.path}?{query}' if query else request.path

        def ativo(**filtros):
            return all(request.GET.get(chave) == str(valor)
                       for chave, valor in filtros.items())

        sem_periodo = not any(
            chave.startswith(('dt_vencimento', 'competencia'))
            for chave in request.GET)
        return [
            {'label': f'Venc. {mes:02d}/{ano} (mês atual)',
             'url': url_venc(),
             'active': sem_periodo},
            {'label': f'Venc. {mes_anterior:%m/%Y}',
             'url': url_venc(dt_vencimento__year=mes_anterior.year,
                             dt_vencimento__month=mes_anterior.month),
             'active': ativo(dt_vencimento__year=mes_anterior.year,
                             dt_vencimento__month=mes_anterior.month)},
            {'label': f'Venc. {mes_proximo:%m/%Y}',
             'url': url_venc(dt_vencimento__year=mes_proximo.year,
                             dt_vencimento__month=mes_proximo.month),
             'active': ativo(dt_vencimento__year=mes_proximo.year,
                             dt_vencimento__month=mes_proximo.month)},
            {'label': 'Vencidas',
             'url': url_venc(dt_vencimento__lt=hoje.isoformat()),
             'active': request.GET.get('dt_vencimento__lt') == hoje.isoformat()},
            {'label': 'A vencer',
             'url': url_venc(dt_vencimento__gte=hoje.isoformat()),
             'active': request.GET.get('dt_vencimento__gte') == hoje.isoformat()},
            {'label': f'Competência {mes:02d}/{ano}',
             'url': url_venc(competencia__year=ano, competencia__month=mes),
             'active': ativo(competencia__year=ano, competencia__month=mes)},
            {'label': 'Competência anterior',
             'url': url_venc(competencia__year=mes_anterior.year,
                             competencia__month=mes_anterior.month),
             'active': ativo(competencia__year=mes_anterior.year,
                             competencia__month=mes_anterior.month)},
        ]

    def get_top_extra_filters(self, request):
        """Atalhos de SALDO: o padrão traz com e sem saldo; os atalhos
        restringem a contas em aberto (a receber) ou já baixadas."""
        return [
            {
                'label': 'Em aberto',
                'url': self._url_com(request, saldo='aberto'),
                'active': request.GET.get('saldo') == 'aberto',
                'icon': 'fa-hourglass-half',
            },
            {
                'label': 'Baixadas',
                'url': self._url_com(request, saldo='zero'),
                'active': request.GET.get('saldo') == 'zero',
                'icon': 'fa-circle-check',
            },
        ]

    top_extra_filter_label = 'Saldo'

    def get_form(self, request, obj=None, **kwargs):
        # O super() já inclui a filtragem/inicialização de 'estabelecimento'
        # feita pelo AdminEstabelecimentoPadraoMixin.
        form = super().get_form(request, obj, **kwargs)

        def form_init(form_instance, *args, **kwargs):
            perfil_usuario = getattr(request.user, 'perfil', None)
            if not perfil_usuario:
                return

            estabelecimentos_permitidos = perfil_usuario.estabelecimento.all()

            # `fatura_baixada` é M2M: o queryset recorta as opções do campo.
            # A fatura da própria baixa (ao editar) sai do recorte de saldo,
            # senão o valor atual desapareceria da listagem. O campo do form
            # é CLONE por instância (ver `BaixaFaturaForm.__init__`), então
            # este recorte vale só para este form.
            from django.db.models import Q
            campo_fatura = form_instance.fields.get('fatura_baixada')
            if campo_fatura is not None:
                fatura_ids = [obj.pk_fatura_baixada()] if obj is not None else []
                campo_fatura.queryset = Fatura.objects.filter(
                    Q(valor_saldo__gt=0, status='A', faturado=True,
                      estabelecimento__in=estabelecimentos_permitidos)
                    | Q(pk__in=fatura_ids)
                ).distinct()
                # A fatura da própria baixa pode estar fora do recorte de
                # saldo (já liquidada): mantê-la válida, senão o campo
                # desabilitado falha com "não é uma das escolhas".
                from admin_faturas.models import BaixaFatura as _BF
                campo_fatura.queryset = _BF.queryset_faturas_baixadas(
                    campo_fatura.queryset)

            form_instance.fields['transacao_financeira'].queryset = TransacaoFinanceira.objects.filter(
                tipo='entrada', status='A'
            )

            form_instance.fields['competencia_bancaria'].queryset = CompetenciaBancaria.objects.filter(
                dt_fechamento_competencia__isnull=True, status='A'
            )

        # Encadeia em vez de substituir o __init__ aplicado pelo mixin.
        chain_form_init(form, form_init)

        return form

    # ------------------------------------------------------------------
    # LISTAGEM EDITÁVEL: um form de baixa (nova) por fatura listada
    # ------------------------------------------------------------------
    def get_changelist_form(self, request, **kwargs):
        """Form de cada linha da listagem.

        A listagem mostra faturas ainda não baixadas: cada linha CRIA uma
        baixa, então o form é sempre um `BaixaFatura` novo apontando para a
        fatura da linha (montado em `ChangeListBaixaFatura`).

        Usa o próprio `BaixaFaturaForm`: o form genérico do changelist
        (`modelform_factory` sobre `get_fields()`) desabilita a cópia da
        fatura mas ela ainda apareceria como obrigatória no formset.
        """
        return BaixaFaturaForm

    def _changelist_baixas(self, request):
        """ChangeList da listagem atual (para reaproveitar os forms)."""
        from .changelist_editavel import ChangeListBaixaFatura

        list_display = self.get_list_display(request)
        return ChangeListBaixaFatura(
            request, self.model, list_display,
            self.get_list_display_links(request, list_display),
            self.get_list_filter(request), self.date_hierarchy,
            self.get_search_fields(request), self.get_list_select_related(request),
            self.list_per_page, self.list_max_show_all,
            tuple(self.list_editable), self, self.get_sortable_by(request),
            self.search_help_text)

    def salvar_baixas_da_listagem(self, request):
        """Cria a baixa de cada linha preenchida. Retorna os forms inválidos."""
        if request.method != 'POST' or '_save' not in request.POST:
            return []

        changelist = self._changelist_baixas(request)
        forms = changelist.forms_das_faturas()

        # Só a linha efetivamente ALTERADA pelo usuário é validada/salva — o
        # restante do POST (todas as demais linhas da listagem) é ignorado:
        # `has_changed()` do Django compara o POST com o `initial` de cada
        # form, então só a linha digitada entra no loop.
        preenchidos = [(form, fatura)
                       for form, fatura in zip(forms,
                                               changelist.faturas_pendentes())
                       if form.has_changed()]

        invalidos = []
        criadas = 0
        for form, fatura in preenchidos:
            if not form.is_valid():
                invalidos.append(form)
                continue

            # A fatura vem do form (`_post_clean`); as demais colunas da
            # baixa que não estão na listagem são completadas aqui.
            obj = form.save(commit=False)
            object.__setattr__(obj, 'fatura_baixada_ids', [fatura.pk])
            obj.estabelecimento_baixa = fatura.estabelecimento
            obj.us_registro_baixa = request.user
            obj.status = 'A'
            try:
                obj.save()
            except ValidationError as erro:
                # Validação do MODELO (ex.: valor da baixa acima do saldo):
                # vira erro da linha (o form fica destacado), não um 500.
                if hasattr(erro, 'message_dict'):
                    for campo, msgs in erro.message_dict.items():
                        if campo in form.fields:
                            form.add_error(campo, msgs)
                        else:
                            form.add_error(None, msgs)
                else:
                    form.add_error(None, erro.messages)
                invalidos.append(form)
                continue
            criadas += 1

        if criadas:
            messages.success(
                request, f'{criadas} baixa(s) registrada(s) com sucesso.')
        if invalidos:
            messages.error(
                request, f'{len(invalidos)} linha(s) com erro. Corrija os '
                         'campos destacados e salve novamente.')
        return invalidos

    def changelist_view(self, request, extra_context=None):
        extra_context = dict(extra_context or {})
        # Só é POST de EDIÇÃO EM LINHA quando '_save' está no POST (o botão
        # "Salvar" da listagem). POST de AÇÃO em lote (`action`) e de busca
        # avançada seguem o fluxo normal do Django (aqui um redirect cedo
        # desviava as ações em lote — elas nunca eram executadas).
        if request.method == 'POST' and '_save' in request.POST:
            extra_context['baixa_forms_com_erro'] = \
                self.salvar_baixas_da_listagem(request)
            # Depois de salvar, recarrega a lista (as baixas feitas saem dela).
            if not extra_context['baixa_forms_com_erro']:
                return redirect(request.get_full_path())
        return super().changelist_view(request, extra_context)

    def save_model(self, request, obj, form, change):
        """
        Define os campos de auditoria e salva o objeto com as informações
        de registro e atualização de usuários e datas.
        """
        if not change:
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()

        fatura = form.cleaned_data.get('fatura_baixada') \
            if hasattr(form, 'cleaned_data') else None
        if fatura:
            # O vínculo (`fatura_baixada_ids`) é gravado pelo
            # `BaixaFatura.save()` — a FK herdada `fatura` SÓ é usada pelo
            # `__setattr__` para espelhar o vínculo.
            obj.fatura = fatura[0]
            obj.estabelecimento_baixa = fatura[0].estabelecimento

        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        """Grava o vínculo M2M (`fatura_baixada`) junto com a baixa.

        O `save_m2m()` do ModelForm tentaria gravar o vínculo com a instância
        SEM pk (`save_model` grava via `save(commit=False)`) — e levantaria
        "Cannot add ... the value for field 'fatura' is None". O vínculo já
        foi gravado no `BaixaFatura.save()` (via `fatura_baixada_ids`),
        então aqui só REAFIRMA (agora com a baixa já no banco).
        """
        # O `save_m2m()` gerado pelo ModelForm chama
        # `fatura_baixada.set(None)` para instâncias novas — com a baixa sem
        # pk, isso explode. Neutraliza (o vínculo já está no banco, gravado
        # pelo `BaixaFatura.save()`).
        def _save_m2m_seguro():
            if form.instance.pk:
                faturas = (form.cleaned_data or {}).get('fatura_baixada')
                if faturas:
                    # Através de PKs: a PK da Fatura é o parent link
                    # `prefatura_ptr` (OneToOneField) e o `get_foreign_
                    # related_value` do through devolve None para instâncias
                    # em memória (o `fatura` FK herdado não existe na fatura).
                    form.instance.fatura_baixada.set(
                        [f.pk for f in faturas])
        form.save_m2m = _save_m2m_seguro
        super().save_related(request, form, formsets, change)
        _save_m2m_seguro()


# Registro dos admins no Django
admin.site.register(PreFatura, PreFaturaAdmin)
admin.site.register(Convenio, ConvenioAdmin)
admin.site.register(Fatura, FaturaAdmin)
admin.site.register(BaixaFatura, BaixaFaturaAdmin)
