"""Admin da Gestão de Tarefas e Documentos.

Mesmo padrão dos outros admins: KPIs + filtro do topo
(`AdminDashboardAndTopFilterMixin`), mixins de estabelecimento, histórico em
inline e ordem de menu pelo `verbose_name_plural`.
"""
from django.contrib import admin
from django.db.models import Q
from django.utils import timezone

from admin_cadastros.utils import EstabelecimentoFilterAdminMixin
from dominios.admin_dashboard_mixins import AdminDashboardAndTopFilterMixin
from dominios.utils import (AdminEstabelecimentoPadraoMixin, ExportToXLSMixin,
                            StatusFilterAdminMixin)

from .models import (
    HistoricoDocumento, HistoricoTarefa, ParametrosGestaoDocumentos, Tipo,
    Documento, Tarefa,
)


@admin.register(Tipo)
class TipoAdmin(AdminEstabelecimentoPadraoMixin, ExportToXLSMixin,
                AdminDashboardAndTopFilterMixin, admin.ModelAdmin):
    list_display = ['descricao', 'observacao_resumo', 'total_documentos',
                    'status', 'dt_registro', 'us_registro']
    list_filter = [StatusFilterAdminMixin]
    search_fields = ['descricao', 'observacao']
    readonly_fields = ['dt_registro', 'us_registro']

    dashboard_date_filter_fields = '__all__'
    dashboard_date_field = 'dt_registro'

    def observacao_resumo(self, obj):
        return (obj.observacao or '')[:60] or '—'
    observacao_resumo.short_description = 'Observação'

    def total_documentos(self, obj):
        return obj.documentos.count()
    total_documentos.short_description = 'Documentos'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
        super().save_model(request, obj, form, change)


@admin.register(Documento)
class DocumentoAdmin(AdminEstabelecimentoPadraoMixin, ExportToXLSMixin,
                     AdminDashboardAndTopFilterMixin, admin.ModelAdmin):
    list_display = ['tipo', 'descricao_documento', 'anexo_link',
                    'vigencia_inicial', 'vigencia_final', 'inicio_renovacao',
                    'situacao_badge', 'validado', 'status', 'dt_registro',
                    'us_registro']
    list_filter = ['tipo', StatusFilterAdminMixin,
                   EstabelecimentoFilterAdminMixin]
    search_fields = ['descricao_documento', 'anotacoes', 'tipo__descricao']
    readonly_fields = ['validado', 'dt_validacao', 'us_validacao',
                       'dt_registro', 'us_registro', 'dt_atualizacao',
                       'us_atualizacao', 'estabelecimento']
    date_hierarchy = 'vigencia_final'

    dashboard_date_filter_fields = '__all__'
    dashboard_date_field = 'vigencia_final'

    class HistoricoInline(admin.TabularInline):
        model = HistoricoDocumento
        extra = 0
        can_delete = False
        fields = ['operacao', 'usuario', 'dt_operacao', 'descricao']
        readonly_fields = fields

    inlines = [HistoricoInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tipo')

    def anexo_link(self, obj):
        from django.utils.html import format_html
        if obj.anexo:
            return format_html(
                '<a href="{}" target="_blank">📎 {}</a>',
                obj.anexo.url, obj.anexo.name.rsplit('/', 1)[-1])
        return '—'
    anexo_link.short_description = 'Anexo'

    def situacao_badge(self, obj):
        from django.utils.html import format_html
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 7px;'
            'border-radius:4px;font-size:.75rem;font-weight:600">{}</span>',
            obj.situacao_cor, obj.situacao_rotulo)
    situacao_badge.short_description = 'Situação'

    def get_dashboard_kpis(self, request, queryset):
        hoje = timezone.localdate()
        vivos = queryset.filter(status='A')
        return [
            {'title': 'Documentos', 'value': str(queryset.count()),
             'subtitle': 'No filtro atual', 'color_class': 'kpi-blue',
             'icon': 'fa-file'},
            {'title': 'Vigentes', 'value': str(vivos.filter(
                vigencia_final__gte=hoje).filter(
                Q(inicio_renovacao__isnull=True)
                | Q(inicio_renovacao__gt=hoje)).count()),
             'subtitle': 'Vigência em curso', 'color_class': 'kpi-green',
             'icon': 'fa-circle-check'},
            {'title': 'Vencidos', 'value': str(vivos.filter(
                vigencia_final__lt=hoje).count()),
             'subtitle': 'Renovar', 'color_class': 'kpi-red',
             'icon': 'fa-triangle-exclamation'},
            {'title': 'Validados', 'value': str(queryset.filter(
                validado=True).count()),
             'subtitle': 'Conferidos', 'color_class': 'kpi-purple',
             'icon': 'fa-clipboard-check'},
        ]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(Tarefa)
class TarefaAdmin(AdminEstabelecimentoPadraoMixin, ExportToXLSMixin,
                  AdminDashboardAndTopFilterMixin, admin.ModelAdmin):
    list_display = ['titulo', 'documento', 'usuario_responsavel',
                    'data_criacao', 'data_prazo', 'prioridade', 'status',
                    'atrasada_badge', 'estabelecimento', 'dt_registro',
                    'us_registro']
    list_filter = ['status', 'prioridade', 'usuario_responsavel',
                   StatusFilterAdminMixin, EstabelecimentoFilterAdminMixin]
    search_fields = ['titulo', 'descricao', 'anotacoes',
                     'documento__descricao_documento']
    date_hierarchy = 'data_criacao'
    dashboard_date_filter_fields = '__all__'
    dashboard_date_field = 'data_criacao'

    class HistoricoInline(admin.TabularInline):
        model = HistoricoTarefa
        extra = 0
        can_delete = False
        fields = ['operacao', 'usuario', 'dt_operacao', 'descricao']
        readonly_fields = fields

    inlines = [HistoricoInline]

    def atrasada_badge(self, obj):
        from django.utils.html import format_html
        if obj.atrasada:
            return format_html(
                '<span style="background:#dc3545;color:#fff;padding:2px 7px;'
                'border-radius:4px;font-size:.75rem;font-weight:600">'
                'ATRASADA</span>')
        return '—'
    atrasada_badge.short_description = 'Atrasada'

    def get_dashboard_kpis(self, request, queryset):
        hoje = timezone.localdate()
        return [
            {'title': 'Tarefas', 'value': str(queryset.count()),
             'subtitle': 'No filtro atual', 'color_class': 'kpi-blue',
             'icon': 'fa-list-check'},
            {'title': 'Pendentes', 'value': str(queryset.filter(
                status='P').count()),
             'subtitle': 'A iniciar', 'color_class': 'kpi-orange',
             'icon': 'fa-hourglass-half'},
            {'title': 'Em andamento', 'value': str(queryset.filter(
                status='A').count()),
             'subtitle': 'Em execução', 'color_class': 'kpi-yellow',
             'icon': 'fa-play'},
            {'title': 'Concluídas', 'value': str(queryset.filter(
                status='C').count()),
             'subtitle': 'Encerradas', 'color_class': 'kpi-green',
             'icon': 'fa-circle-check'},
        ]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(ParametrosGestaoDocumentos)
class ParametrosGestaoDocumentosAdmin(admin.ModelAdmin):
    list_display = ['estabelecimento', 'dias_proximo_vencimento', 'status']
    filter_horizontal = [
        'usuarios_visualizacao', 'grupos_visualizacao',
        'usuarios_edicao', 'grupos_edicao',
        'usuarios_exclusao', 'grupos_exclusao',
    ]
    readonly_fields = ['dt_registro', 'us_registro']

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
        super().save_model(request, obj, form, change)
