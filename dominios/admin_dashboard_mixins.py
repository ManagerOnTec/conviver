"""
Mixins para adicionar:
1. Dashboard com cartões de KPIs dinâmicos no topo das telas do Django Admin.
2. Barra horizontal superior com filtros analíticos rápidos (Hoje, Ontem, 7 Dias, Mês Atual, custom De/Até).
"""
from datetime import date, datetime, timedelta
from django.utils import timezone
from urllib.parse import urlencode


class AdminDashboardAndTopFilterMixin:
    """
    Mixin para enriquecer o changelist_view com:
    - KPIs contextuais calculados para o modelo
    - Barra horizontal de períodos analíticos (presets rápidos)
    """
    # Campo de data do modelo usado para o filtro analítico de período (ex: 'dt_registro', 'dt_atendimento')
    dashboard_date_field = 'dt_registro'

    def get_dashboard_kpis(self, request, queryset):
        """
        Sobrescreva para retornar lista de dicionários com os cards de KPI:
        [
            {'title': 'Total', 'value': 120, 'subtitle': 'Registros', 'color_class': 'kpi-blue', 'icon': '📊'},
            ...
        ]
        """
        total = queryset.count()
        return [
            {
                'title': 'Total na Listagem',
                'value': f"{total:,}".replace(',', '.'),
                'subtitle': 'Registros correspondentes',
                'color_class': 'kpi-blue',
                'icon': '📑',
            }
        ]

    def get_top_extra_filters(self, request):
        """
        Sobrescreva para retornar botões rápidos adicionais (ex: Ativos, Inativos, Por tipo).
        """
        return []

    def get_top_dropdown_subfilters(self, request):
        """
        Sobrescreva para retornar selects dropdown com subfiltros específicos (ex: tipo de evolução, tipo de documento legal).
        """
        return []

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        # 1. Configuração do campo de data
        date_field = getattr(self, 'dashboard_date_field', 'dt_registro')
        date_gte_key = f"{date_field}__gte"
        date_lte_key = f"{date_field}__lte"

        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        last_7_days = today - timedelta(days=7)
        first_day_month = today.replace(day=1)

        # 2. Construtor de URLs para os presets de período
        def build_preset_url(params_to_set, is_active=False):
            params = request.GET.copy()
            # Remove paginação ao mudar filtro
            params.pop('p', None)
            params.pop('periodo', None)
            params.pop(date_gte_key, None)
            params.pop(date_lte_key, None)

            for k, v in params_to_set.items():
                if v is not None:
                    params[k] = v

            qs_str = params.urlencode()
            url = f"{request.path}?{qs_str}" if qs_str else request.path
            return url

        current_periodo = request.GET.get('periodo', '')
        current_date_gte = request.GET.get(date_gte_key, '')
        current_date_lte = request.GET.get(date_lte_key, '')

        # Determina preset ativo
        presets = [
            {
                'label': 'Todos',
                'url': build_preset_url({}),
                'active': not current_periodo and not current_date_gte and not current_date_lte,
            },
            {
                'label': 'Hoje',
                'url': build_preset_url({'periodo': 'hoje', date_gte_key: f"{today} 00:00:00", date_lte_key: f"{today} 23:59:59"}),
                'active': current_periodo == 'hoje' or (current_date_gte.startswith(str(today)) and current_date_lte.startswith(str(today))),
            },
            {
                'label': 'Ontem',
                'url': build_preset_url({'periodo': 'ontem', date_gte_key: f"{yesterday} 00:00:00", date_lte_key: f"{yesterday} 23:59:59"}),
                'active': current_periodo == 'ontem',
            },
            {
                'label': 'Últimos 7 dias',
                'url': build_preset_url({'periodo': '7dias', date_gte_key: f"{last_7_days} 00:00:00"}),
                'active': current_periodo == '7dias',
            },
            {
                'label': 'Mês Atual',
                'url': build_preset_url({'periodo': 'mes_atual', date_gte_key: f"{first_day_month} 00:00:00"}),
                'active': current_periodo == 'mes_atual',
            },
        ]

        has_active_top_filter = bool(current_periodo or current_date_gte or current_date_lte)

        # 3. Calcula KPIs baseados no queryset filtrado atual
        try:
            cl = self.get_changelist_instance(request)
            qs = cl.get_queryset(request)
        except Exception:
            qs = self.get_queryset(request)

        kpis = self.get_dashboard_kpis(request, qs)

        extra_context.update({
            'kpi_cards': kpis,
            'top_filter_config': True,
            'top_filter_presets': presets,
            'top_extra_filters': self.get_top_extra_filters(request),
            'top_dropdown_subfilters': self.get_top_dropdown_subfilters(request),
            'has_active_top_filter': has_active_top_filter,
            'date_field_gte': date_gte_key,
            'date_field_lte': date_lte_key,
            'current_date_gte': current_date_gte.split(' ')[0] if current_date_gte else '',
            'current_date_lte': current_date_lte.split(' ')[0] if current_date_lte else '',
            'search_query': request.GET.get('q', ''),
            'current_paciente_id': request.GET.get('paciente_id', ''),
        })

        return super().changelist_view(request, extra_context=extra_context)
