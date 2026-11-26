"""
Dashboards e filtros superiores das telas de ADMIN TESOURARIA (caixa).

Espelha o `admin_faturas/dashboard.py` / `admin_pagamentos/dashboard.py`
(segundo o "Padrão obrigatório dos admins" do AGENTS.md). Reaproveita a
barra/grade de KPIs do projeto (`AdminDashboardAndTopFilterMixin`) e acrescenta
o que é específico do caixa:

- presets de período por Competência de Caixa e Data do Movimento;
- atalhos de Status (Ativos/Inativos) e de Caixa (Aberto/Fechado);
- seletor de Estabelecimento e de Caixa na barra superior;
- KPIs financeiros (saldo atual, entradas, saídas, movimentos).
"""
from datetime import date, timedelta

from django.utils import timezone

from dominios.admin_dashboard_mixins import AdminDashboardAndTopFilterMixin


def _money(valor):
    """Formata em Reais no padrão brasileiro (sem depender do locale)."""
    try:
        valor = float(valor or 0)
    except (TypeError, ValueError):
        valor = 0.0
    inteiro, centavos = f"{valor:,.2f}".split('.')
    return f"R$ {inteiro.replace(',', '.')},{centavos}"


def _qtd(valor):
    return f"{int(valor or 0):,}".replace(',', '.')


class TesourariaDashboardMixin(AdminDashboardAndTopFilterMixin):
    """Base dos admins de tesouraria: competência de caixa, movimento, saldo.

    Mesma estrutura do `FaturasDashboardMixin`/`PagamentosDashboardMixin` —
    o que muda são os campos lidos em cada tela.
    """

    # LOOKUP de tipo de data no filtro do TOPO (como em Faturas/Pagamentos):
    # o usuário escolhe o campo de data antes de informar o intervalo.
    dashboard_date_filter_fields = '__all__'

    # Campo de "competência" (base dos presets de mês/ano) — cada admin
    # sobrescreve (ex.: 'dt_abertura' na competência de caixa).
    dashboard_competencia_field = 'dt_movimento'
    # Campo de "vencimento" (presets de período e KPI de fechamento).
    dashboard_vencimento_field = 'dt_movimento'
    # Campos de valor lidos nos KPIs.
    dashboard_valor_field = 'valor_entrada'

    # ------------------------------------------------------------------
    # Utilitários (iguais aos das telas financeiras)
    # ------------------------------------------------------------------
    @staticmethod
    def _query_params(request):
        params = request.GET.copy()
        params.pop('p', None)  # volta para a 1ª página ao filtrar
        for chave in list(params.keys()):
            if any(valor == '' for valor in params.getlist(chave)):
                params.pop(chave, None)
        return params

    def _url_com(self, request, **mudancas):
        """URL da própria changelist trocando/removendo apenas as chaves dadas
        (``None`` ou ``''`` removem a chave)."""
        params = self._query_params(request)
        for chave, valor in mudancas.items():
            if valor in (None, ''):
                params.pop(chave, None)
            elif isinstance(valor, bool):
                params[chave] = '1' if valor else '0'
            else:
                params[chave] = valor
        qs = params.urlencode()
        return f"{request.path}?{qs}" if qs else request.path

    def _tem_filtro_periodo(self, request):
        return (
            any(request.GET.get(chave) for chave in
                self.get_top_date_filter_range_keys())
            or any(chave.startswith((
                f'{self.dashboard_competencia_field}__',
                f'{self.dashboard_vencimento_field}__',
            )) for chave in request.GET.keys())
        )

    # ------------------------------------------------------------------
    # Presets do período (barra superior)
    # ------------------------------------------------------------------
    def get_top_filter_presets(self, request):
        hoje = timezone.localdate()
        ano, mes = hoje.year, hoje.month
        if mes == 1:
            mes_anterior = date(ano - 1, 12, 1)
        else:
            mes_anterior = date(ano, mes - 1, 1)

        campo_comp = self.dashboard_competencia_field
        campo_venc = self.dashboard_vencimento_field

        def url_periodo(**filtros):
            params = self._query_params(request)
            for chave in self.get_top_date_filter_range_keys():
                params.pop(chave, None)
            for chave in list(params.keys()):
                if chave.startswith((f'{campo_comp}__', f'{campo_venc}__')):
                    params.pop(chave, None)
            params.update(filtros)
            query = params.urlencode()
            return f'{request.path}?{query}' if query else request.path

        def ativo(**filtros):
            return all(request.GET.get(chave) == str(valor)
                       for chave, valor in filtros.items())

        return [
            {'label': 'Todos', 'url': url_periodo(),
             'active': not self._tem_filtro_periodo(request)},
            {'label': f'Competência {mes:02d}/{ano}',
             'url': url_periodo(**{f'{campo_comp}__year': ano,
                                   f'{campo_comp}__month': mes}),
             'active': ativo(**{f'{campo_comp}__year': ano,
                                f'{campo_comp}__month': mes})},
            {'label': 'Competência anterior',
             'url': url_periodo(**{f'{campo_comp}__year': mes_anterior.year,
                                   f'{campo_comp}__month': mes_anterior.month}),
             'active': ativo(**{f'{campo_comp}__year': mes_anterior.year,
                                f'{campo_comp}__month': mes_anterior.month})},
            {'label': f'Movimento {mes:02d}/{ano}',
             'url': url_periodo(**{f'{campo_venc}__year': ano,
                                   f'{campo_venc}__month': mes}),
             'active': ativo(**{f'{campo_venc}__year': ano,
                                f'{campo_venc}__month': mes})},
            {'label': 'Últimos 7 dias',
             'url': url_periodo(
                 **{f'{campo_venc}__gte': str(hoje - timedelta(days=7))}),
             'active': request.GET.get(
                 f'{campo_venc}__gte') == str(hoje - timedelta(days=7))},
        ]

    # ------------------------------------------------------------------
    # Filtros superiores (atalhos)
    # ------------------------------------------------------------------
    def filtro_todos_status(self, request, parametros=None):
        """Botão “Todos”: limpa SÓ os filtros de estado informados."""
        parametros = ('status', *(parametros or ()))
        filtros_ativos = any(
            request.GET.get(chave) not in (None, '') for chave in parametros
        )
        return {
            'label': 'Todos',
            'url': self._url_com(
                request, **{chave: None for chave in parametros}),
            'active': not filtros_ativos,
            'icon': 'fa-list',
        }

    def get_top_extra_filters(self, request):
        status = request.GET.get('status')
        filtros = [
            self.filtro_todos_status(request),
            {'label': 'Ativos', 'url': self._url_com(request, status='A'),
             'active': status == 'A', 'icon': '✅'},
            {'label': 'Inativos', 'url': self._url_com(request, status='I'),
             'active': status == 'I', 'icon': '🚫'},
        ]
        # Caixa Aberto/Fechado: só nas telas que têm a competência de caixa
        # (movimento) ou o fechamento próprio (competência).
        if self._modelo_tem_campo('competencia_caixa'):
            filtros += [
                {'label': 'Caixa Aberto',
                 'url': self._url_com(
                     request, competencia_caixa__dt_fechamento__isnull='True'),
                 'active': request.GET.get(
                     'competencia_caixa__dt_fechamento__isnull') == 'True',
                 'icon': '🔓'},
            ]
        if self._modelo_tem_campo('dt_fechamento'):
            filtros += [
                {'label': 'Abertas',
                 'url': self._url_com(
                     request, dt_fechamento__isnull='True'),
                 'active': request.GET.get('dt_fechamento__isnull') == 'True',
                 'icon': '🔓'},
                {'label': 'Fechadas',
                 'url': self._url_com(
                     request, dt_fechamento__isnull='False'),
                 'active': request.GET.get('dt_fechamento__isnull') == 'False',
                 'icon': '🔒'},
            ]
        return filtros

    def _modelo_tem_campo(self, nome):
        return any(f.name == nome for f in self.model._meta.get_fields())

    # Lookups de FK ANINHADA usados pelo seletor "Caixa" do topo (o Django
    # só aceita traversal de 1 nível por padrão).
    LOOKUPS_LIBERADOS = (
        'competencia_caixa__controle_caixa__id__exact',
    )

    def lookup_allowed(self, lookup, value, request=None):
        if lookup in self.LOOKUPS_LIBERADOS:
            return True
        try:
            return super().lookup_allowed(lookup, value, request)
        except TypeError:
            # Django < 4.1 não recebe o `request`.
            return super().lookup_allowed(lookup, value)

    # ------------------------------------------------------------------
    # Dropdown do topo: Caixa (controle de caixa) e Estabelecimento
    # ------------------------------------------------------------------
    def get_top_dropdown_subfilters(self, request):
        def opcoes(param, objs, rotulo_vazio, fmt, key=None, default=None):
            atuais = set(filter(None, request.GET.getlist(param)))
            lista = [{
                'label': rotulo_vazio,
                'url': self._url_com(request, **{param: None}),
                'selected': not atuais and not default,
            }]
            vistos = set()
            for obj in objs:
                valor = key(obj) if key is not None else obj.pk
                if valor in vistos:
                    continue
                vistos.add(valor)
                lista.append({
                    'label': fmt(obj),
                    'url': self._url_com(request, **{param: valor}),
                    'selected': (str(valor) in atuais
                                 or (not atuais
                                     and str(valor) == str(default))),
                })
            return lista

        seletores = []

        # CAIXA (Controle de Caixa) — entra pelo caminho que existe em cada
        # modelo: próprio campo `controle_caixa` (competência) ou através da
        # competência de caixa (movimento/conferência).
        if self._modelo_tem_campo('competencia_caixa') or \
                self._modelo_tem_campo('controle_caixa'):
            try:
                from admin_tesouraria.models import ControleCaixa
                caixas = ControleCaixa.objects.filter(
                    status='A').order_by('descricao')
                if self._modelo_tem_campo('controle_caixa'):
                    seletores.append({
                        'label': 'Caixa',
                        'options': opcoes(
                            'controle_caixa__id__exact', caixas,
                            'Todos os caixas', lambda c: str(c)),
                    })
                else:
                    seletores.append({
                        'label': 'Caixa',
                        'options': opcoes(
                            'competencia_caixa__controle_caixa__id__exact',
                            caixas, 'Todos os caixas', lambda c: str(c)),
                    })
            except Exception:
                pass  # nunca derruba a listagem (AGENTS.md, item 9)

        # ESTABELECIMENTO — seletor do topo (mesmo padrão do fluxo de faturas).
        if self._modelo_tem_campo('estabelecimento'):
            try:
                from admin_cadastros.models import Estabelecimento
                perfil = getattr(request.user, 'perfil', None)
                if perfil is not None:
                    estabelecimentos = perfil.estabelecimento.filter(status='A')
                    if perfil.estabelecimento_padrao_id:
                        estabelecimentos = (
                            estabelecimentos |
                            Estabelecimento.objects.filter(
                                pk=perfil.estabelecimento_padrao_id,
                                status='A'))
                else:
                    estabelecimentos = Estabelecimento.objects.filter(
                        status='A')
                estabelecimentos = estabelecimentos.distinct().order_by(
                    'estabelecimento')
                if estabelecimentos.exists():
                    atual = (request.GET.get('estabelecimento__id__exact')
                             or request.GET.get('estabelecimento'))
                    seletores.append({
                        'label': 'Estabelecimento',
                        'options': opcoes(
                            'estabelecimento__id__exact', estabelecimentos,
                            'Todos os meus', lambda e: str(e),
                            default=atual),
                    })
            except Exception:
                pass

        return seletores

    # ------------------------------------------------------------------
    # KPIs (cada admin sobrescreve com os seus)
    # ------------------------------------------------------------------
    def get_dashboard_kpis(self, request, queryset):
        return [
            {
                'title': 'Registros',
                'value': _qtd(queryset.count()),
                'subtitle': 'No filtro atual',
                'color_class': 'kpi-blue',
                'icon': '📑',
            },
        ]

    def _somas(self, queryset):
        from django.db.models import Count, Sum
        campos = {
            'total': Sum(self.dashboard_valor_field),
            'registros': Count('pk'),
        }
        if self.dashboard_saldo_field:
            campos['saldo'] = Sum(self.dashboard_saldo_field)
        return queryset.aggregate(**campos)

    # ------------------------------------------------------------------
    # Contexto
    # ------------------------------------------------------------------
    @property
    def dashboard_date_field(self):
        return getattr(self, '_dashboard_date_field',
                       self.dashboard_competencia_field or 'dt_registro')

    @dashboard_date_field.setter
    def dashboard_date_field(self, valor):
        self._dashboard_date_field = valor

    top_filter_search_label = 'Busca'
    top_filter_search_placeholder = 'Buscar por caixa, competência, observação...'
    top_extra_filter_label = 'Status & Caixa'
