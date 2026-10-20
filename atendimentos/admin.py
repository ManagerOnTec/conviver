from datetime import datetime
from django.contrib import admin
from dominios.admin_dashboard_mixins import AdminDashboardAndTopFilterMixin
from .models import Atendimento
from dominios.utils import AdminEstabelecimentoPadraoMixin 
from admin_cadastros.utils import EstabelecimentoFilterAdminMixin



@admin.register(Atendimento)
class AtendimentoAdmin(AdminEstabelecimentoPadraoMixin, AdminDashboardAndTopFilterMixin, admin.ModelAdmin):
    dashboard_date_field = 'dt_atendimento'

    def get_dashboard_kpis(self, request, queryset):
        total = queryset.count()
        internados_hoje = queryset.filter(dt_alta__isnull=True).count()
        altas = queryset.filter(dt_alta__isnull=False).count()
        convenio_count = queryset.exclude(convenio__isnull=True).count()

        return [
            {
                'title': 'Total Atendimentos',
                'value': f"{total:,}".replace(',', '.'),
                'subtitle': 'Registros no filtro',
                'color_class': 'kpi-blue',
                'icon': '🏥',
            },
            {
                'title': 'Internados Atualmente',
                'value': f"{internados_hoje:,}".replace(',', '.'),
                'subtitle': 'Sem data de alta',
                'color_class': 'kpi-green',
                'icon': '🛌',
            },
            {
                'title': 'Altas Concedidas',
                'value': f"{altas:,}".replace(',', '.'),
                'subtitle': 'Pacientes desospitalizados',
                'color_class': 'kpi-purple',
                'icon': '🏁',
            },
            {
                'title': 'Por Convênios',
                'value': f"{convenio_count:,}".replace(',', '.'),
                'subtitle': 'Atendimentos com convênio',
                'color_class': 'kpi-orange',
                'icon': '📑',
            },
        ]

    def get_top_extra_filters(self, request):
        params = request.GET.copy()
        current_alta = params.get('dt_alta__isnull', '')

        def build_alta_url(val):
            p = request.GET.copy()
            p.pop('p', None)
            if val is None or (p.get('dt_alta__isnull') == val):
                p.pop('dt_alta__isnull', None)
            else:
                p['dt_alta__isnull'] = val
            qs_str = p.urlencode()
            return f"{request.path}?{qs_str}" if qs_str else request.path

        return [
            {
                'label': 'Apenas Internados',
                'url': build_alta_url('True'),
                'active': current_alta == 'True',
                'icon': '🛌',
            },
            {
                'label': 'Apenas com Alta',
                'url': build_alta_url('False'),
                'active': current_alta == 'False',
                'icon': '🏁',
            },
        ]

    list_display = (
        'id', 'pessoa', 'tipo_atendimento', 'carater_atendimento',
        'estabelecimento', 'dt_atendimento', 'dt_alta',
    )
    list_display_links = ('id', 'pessoa')
    list_filter = (EstabelecimentoFilterAdminMixin,'tipo_atendimento', 'carater_atendimento', 'estabelecimento')
    search_fields = ('id', 'pessoa__nome', 'pessoa__cpf', 'pessoa__rg')
    autocomplete_fields = ('pessoa',)
    date_hierarchy = 'dt_atendimento'
    ordering = ('-id',)

