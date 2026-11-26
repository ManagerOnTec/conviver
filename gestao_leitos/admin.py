"""Admin da Gestão de Leitos (padrão dos admins do AGENTS.md)."""
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from admin_cadastros.utils import EstabelecimentoFilterAdminMixin
from dominios.admin_dashboard_mixins import AdminDashboardAndTopFilterMixin
from dominios.utils import AdminEstabelecimentoPadraoMixin, ExportToXLSMixin

from .models import GestaoLeito, HistoricoLeito, ParametrosGestaoLeitos


@admin.register(GestaoLeito)
class GestaoLeitoAdmin(AdminEstabelecimentoPadraoMixin, ExportToXLSMixin,
                       AdminDashboardAndTopFilterMixin, admin.ModelAdmin):
    list_display = ['leito', 'local_info', 'ala_info', 'atendimento',
                    'paciente_info', 'dt_entrada', 'dt_saida',
                    'dias_internado', 'situacao_badge', 'status']
    list_filter = ['situacao', 'status', EstabelecimentoFilterAdminMixin]
    search_fields = ['leito__leito', 'leito__local__nome',
                     'atendimento__pessoa__nome', 'atendimento__pessoa__cpf']
    date_hierarchy = 'dt_entrada'
    readonly_fields = ['estabelecimento', 'dt_registro', 'us_registro',
                       'dt_atualizacao', 'us_atualizacao']
    dashboard_date_filter_fields = '__all__'
    dashboard_date_field = 'dt_entrada'

    class HistoricoInline(admin.TabularInline):
        model = HistoricoLeito
        extra = 0
        can_delete = False
        fields = ['operacao', 'usuario', 'dt_operacao', 'descricao']
        readonly_fields = fields

    inlines = [HistoricoInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'leito', 'leito__local', 'leito__local__setor',
            'leito__local__setor__ala', 'atendimento', 'atendimento__pessoa')

    def local_info(self, obj):
        return obj.leito.local.nome if obj.leito.local_id else '—'
    local_info.short_description = 'Local'

    def ala_info(self, obj):
        return obj.leito.local.setor.ala.nome \
            if obj.leito.local.setor_id else '—'
    ala_info.short_description = 'Ala'

    def paciente_info(self, obj):
        pessoa = obj.atendimento.pessoa if obj.atendimento_id else None
        return pessoa.nome if pessoa else '—'
    paciente_info.short_description = 'Paciente'

    def situacao_badge(self, obj):
        cores = {'O': '#198754', 'L': '#0dcaf0',
                 'B': '#dc3545', 'H': '#e0a800'}
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 7px;'
            'border-radius:4px;font-size:.75rem;font-weight:600">{}</span>',
            cores.get(obj.situacao, '#6c757d'),
            obj.get_situacao_display())
    situacao_badge.short_description = 'Situação'

    def get_dashboard_kpis(self, request, queryset):
        vivos = queryset.filter(status='A', dt_saida__isnull=True)
        return [
            {'title': 'Ocupações', 'value': str(queryset.count()),
             'subtitle': 'No filtro atual', 'color_class': 'kpi-blue',
             'icon': 'fa-bed'},
            {'title': 'Ocupados agora', 'value': str(vivos.filter(
                situacao='O').count()),
             'subtitle': 'Leitos com atendimento', 'color_class': 'kpi-green',
             'icon': 'fa-user-check'},
            {'title': 'Bloqueados', 'value': str(vivos.filter(
                situacao='B').count()),
             'subtitle': 'Manutenção etc', 'color_class': 'kpi-red',
             'icon': 'fa-ban'},
            {'title': 'Higienização', 'value': str(vivos.filter(
                situacao='H').count()),
             'subtitle': 'Aguardando limpeza', 'color_class': 'kpi-orange',
             'icon': 'fa-broom'},
        ]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(ParametrosGestaoLeitos)
class ParametrosGestaoLeitosAdmin(admin.ModelAdmin):
    list_display = ['estabelecimento', 'status']
    filter_horizontal = [
        'usuarios_visualizacao', 'grupos_visualizacao',
        'usuarios_edicao', 'grupos_edicao',
        'usuarios_exclusao', 'grupos_exclusao',
    ]
    readonly_fields = ['dt_cadastro', 'usuario_cadastro']

    def save_model(self, request, obj, form, change):
        if not change:
            obj.usuario_cadastro = request.user
        super().save_model(request, obj, form, change)
