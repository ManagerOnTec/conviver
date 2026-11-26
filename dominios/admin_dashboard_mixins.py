"""
Mixins para adicionar:
1. Dashboard com cartões de KPIs dinâmicos no topo das telas do Django Admin.
2. Barra horizontal superior com filtros analíticos rápidos (Hoje, Ontem, 7 Dias, Mês Atual, custom De/Até).
"""
from datetime import date, datetime, timedelta
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.utils.text import capfirst
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
    # Configure como '__all__' para oferecer todos os campos Date/DateTime
    # próprios do modelo no filtro superior.
    dashboard_date_filter_fields = None

    def get_top_date_filter_fields(self):
        configured_fields = getattr(self, 'dashboard_date_filter_fields', None)
        use_date_lookup = configured_fields is not None
        if configured_fields == '__all__':
            fields = [
                field for field in self.model._meta.fields
                if isinstance(field, models.DateField)
            ]
        elif configured_fields:
            names = (configured_fields,) if isinstance(
                configured_fields, str) else configured_fields
            fields = []
            for name in names:
                try:
                    field = self.model._meta.get_field(name)
                except FieldDoesNotExist:
                    continue
                if isinstance(field, models.DateField):
                    fields.append(field)
        else:
            try:
                fields = [self.model._meta.get_field(
                    self.dashboard_date_field)]
            except FieldDoesNotExist:
                fields = []
            fields = [
                field for field in fields
                if isinstance(field, models.DateField)
            ]

        return [
            {
                'name': field.name,
                'label': capfirst(str(field.verbose_name)),
                'gte_key': (
                    f'{field.name}__date__gte'
                    if use_date_lookup and isinstance(
                        field, models.DateTimeField)
                    else f'{field.name}__gte'
                ),
                'lte_key': (
                    f'{field.name}__date__lte'
                    if use_date_lookup and isinstance(
                        field, models.DateTimeField)
                    else f'{field.name}__lte'
                ),
                'legacy_gte_key': f'{field.name}__gte',
                'legacy_lte_key': f'{field.name}__lte',
            }
            for field in fields
        ]

    def get_top_date_filter_range_keys(self, date_fields=None):
        date_fields = (
            self.get_top_date_filter_fields()
            if date_fields is None else date_fields
        )
        return list(dict.fromkeys(
            key
            for field in date_fields
            for key in (
                field['gte_key'], field['lte_key'],
                field['legacy_gte_key'], field['legacy_lte_key'],
            )
        ))

    def get_selected_top_date_filter_field(self, request, date_fields=None):
        date_fields = (
            self.get_top_date_filter_fields()
            if date_fields is None else date_fields
        )
        for field in date_fields:
            if any(request.GET.get(key) for key in (
                    field['gte_key'], field['lte_key'],
                    field['legacy_gte_key'], field['legacy_lte_key'])):
                return field
        for field in date_fields:
            prefix = f"{field['name']}__"
            if any(key.startswith(prefix) for key in request.GET.keys()):
                return field
        default_name = getattr(self, 'dashboard_date_field', '')
        return next(
            (field for field in date_fields
             if field['name'] == default_name),
            date_fields[0] if date_fields else None,
        )

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

    def get_top_filter_presets(self, request):
        """Presets de período da barra superior.

        Sobrescreva para trazer presets próprios do módulo (ex.: Competência no
        financeiro). O mixin detecta a sobrescrita e usa a sua lista em vez de
        Hoje/Ontem/7 dias/Mês. Retorne uma lista de
        ``{'label', 'url', 'active'}``. Se o módulo tiver presets próprios,
        devolva ``None`` para indicar que não quer os presets padrão.
        """
        return None

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

        # Alguns widgets de data geram parâmetros vazios (ex.: campo inicial e
        # final sem valor). Remova-os antes do Django ChangeList converter
        # esses valores para DateField, o que geraria IncorrectLookupParameters.
        if any('' in request.GET.getlist(chave)
               for chave in request.GET.keys()):
            request.GET = request.GET.copy()
            for chave in list(request.GET.keys()):
                if any(valor == '' for valor in request.GET.getlist(chave)):
                    request.GET.pop(chave, None)

        # 1. Configuração dos campos de data
        date_fields = self.get_top_date_filter_fields()
        selected_date_field = self.get_selected_top_date_filter_field(
            request, date_fields)
        date_range_keys = self.get_top_date_filter_range_keys(date_fields)
        selected_date_range_keys = (
            list(dict.fromkeys((
                selected_date_field['gte_key'],
                selected_date_field['lte_key'],
                selected_date_field['legacy_gte_key'],
                selected_date_field['legacy_lte_key'],
            )))
            if selected_date_field else []
        )
        date_gte_key = (
            selected_date_field['gte_key'] if selected_date_field else ''
        )
        date_lte_key = (
            selected_date_field['lte_key'] if selected_date_field else ''
        )

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
            for key in date_range_keys:
                params.pop(key, None)

            for k, v in params_to_set.items():
                if v is not None:
                    params[k] = v

            qs_str = params.urlencode()
            url = f"{request.path}?{qs_str}" if qs_str else request.path
            return url

        current_periodo = request.GET.get('periodo', '')
        current_date_gte = (
            request.GET.get(selected_date_field['gte_key'])
            or request.GET.get(selected_date_field['legacy_gte_key'])
            or ''
        ) if selected_date_field else ''
        current_date_lte = (
            request.GET.get(selected_date_field['lte_key'])
            or request.GET.get(selected_date_field['legacy_lte_key'])
            or ''
        ) if selected_date_field else ''

        # Presets do período: o próprio módulo pode trazer os seus
        # (ex.: Competência do financeiro) no lugar de Hoje/Ontem/7 dias.
        presets_customizados = self.get_top_filter_presets(request)
        if presets_customizados is not None:
            presets = presets_customizados
        else:
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

        has_active_top_filter = bool(
            current_periodo or current_date_gte or current_date_lte
            or any(request.GET.get(key) for key in date_range_keys)
            or presets_customizados is not None and any(
                p.get('active') and p.get('label') not in ('Todos',)
                for p in presets_customizados)
        )

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
            'top_date_filter_fields': date_fields,
            'selected_top_date_filter_field': (
                selected_date_field['name'] if selected_date_field else ''),
            'top_date_filter_range_keys': date_range_keys,
            'selected_top_date_filter_range_keys': selected_date_range_keys,
            'top_extra_filters': self.get_top_extra_filters(request),
            'top_extra_filter_label': getattr(
                self, 'top_extra_filter_label', 'Status & Módulo'),
            'top_dropdown_subfilters': self.get_top_dropdown_subfilters(request),
            'has_active_top_filter': has_active_top_filter,
            'date_field_gte': date_gte_key,
            'date_field_lte': date_lte_key,
            'current_date_gte': current_date_gte[:10] if current_date_gte else '',
            'current_date_lte': current_date_lte[:10] if current_date_lte else '',
            'search_query': request.GET.get('q', ''),
            'current_paciente_id': request.GET.get('paciente_id', ''),
            # Cada módulo pode renomear a busca superior (default: paciente).
            'top_filter_search_label': getattr(
                self, 'top_filter_search_label', 'Paciente'),
            'top_filter_search_placeholder': getattr(
                self, 'top_filter_search_placeholder',
                'Digitar Nome do Paciente, CPF, RG ou Nº do Atendimento...'),
        })

        return super().changelist_view(request, extra_context=extra_context)
