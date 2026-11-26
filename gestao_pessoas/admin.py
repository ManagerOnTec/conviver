"""Admin da Gestão de Pessoas (padrão dos outros admins: KPIs + topo)."""
from django.contrib import admin
from django.db.models import Q
from django.utils import timezone
from django.utils.html import format_html

from admin_cadastros.utils import EstabelecimentoFilterAdminMixin
from dominios.admin_dashboard_mixins import AdminDashboardAndTopFilterMixin
from dominios.utils import AdminEstabelecimentoPadraoMixin, ExportToXLSMixin

from .models import (
    ASO, CartaoPonto, Curso, CursoFuncionario, DocumentoFuncionario,
    ExamePeriodico, Ferias, FichaRegistro, Funcionario,
    HistoricoFuncionario, ParametrosGestaoPessoas,
)


@admin.register(Funcionario)
class FuncionarioAdmin(AdminEstabelecimentoPadraoMixin, ExportToXLSMixin,
                       AdminDashboardAndTopFilterMixin, admin.ModelAdmin):
    list_display = ['pessoa', 'data_admissao', 'status_funcionario',
                    'estabelecimento', 'status', 'dt_cadastro',
                    'usuario_cadastro']
    list_filter = ['status_funcionario', 'status',
                   EstabelecimentoFilterAdminMixin]
    search_fields = ['pessoa__nome', 'pessoa__cpf']
    date_hierarchy = 'data_admissao'
    dashboard_date_filter_fields = '__all__'
    dashboard_date_field = 'data_admissao'

    class HistoricoInline(admin.TabularInline):
        model = HistoricoFuncionario
        extra = 0
        can_delete = False
        fields = ['operacao', 'usuario', 'dt_operacao', 'descricao']
        readonly_fields = fields

    class DocumentosInline(admin.TabularInline):
        model = DocumentoFuncionario
        extra = 0

    inlines = [HistoricoInline, DocumentosInline]

    def get_dashboard_kpis(self, request, queryset):
        hoje = timezone.localdate()
        return [
            {'title': 'Funcionários', 'value': str(queryset.count()),
             'subtitle': 'No filtro atual', 'color_class': 'kpi-blue',
             'icon': 'fa-users'},
            {'title': 'Ativos', 'value': str(queryset.filter(
                status_funcionario='A').count()),
             'subtitle': 'Situação funcional', 'color_class': 'kpi-green',
             'icon': 'fa-user-check'},
            {'title': 'Afastados', 'value': str(queryset.filter(
                status_funcionario='F').count()),
             'subtitle': 'Situação funcional', 'color_class': 'kpi-orange',
             'icon': 'fa-user-clock'},
            {'title': 'Desligados', 'value': str(queryset.filter(
                status_funcionario='D').count()),
             'subtitle': 'Situação funcional', 'color_class': 'kpi-red',
             'icon': 'fa-user-minus'},
        ]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.usuario_cadastro = request.user
        else:
            obj.usuario_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(DocumentoFuncionario)
class DocumentoFuncionarioAdmin(AdminEstabelecimentoPadraoMixin,
                                ExportToXLSMixin,
                                AdminDashboardAndTopFilterMixin,
                                admin.ModelAdmin):
    list_display = ['funcionario', 'tipo_documento', 'data_documento',
                    'anexo_link', 'dt_cadastro', 'usuario_cadastro']
    list_filter = [EstabelecimentoFilterAdminMixin]
    search_fields = ['tipo_documento', 'descricao', 'funcionario__pessoa__nome']
    dashboard_date_field = 'dt_cadastro'

    def anexo_link(self, obj):
        if obj.anexo:
            return format_html('<a href="{}" target="_blank">📎</a>',
                               obj.anexo.url)
        return '—'
    anexo_link.short_description = 'Anexo'


@admin.register(ASO)
class AsoAdmin(ExportToXLSMixin, AdminDashboardAndTopFilterMixin,
               admin.ModelAdmin):
    list_display = ['funcionario', 'tipo_exame', 'status', 'data_agendamento',
                    'data_realizacao', 'data_validade', 'anexo_link',
                    'dt_cadastro']
    list_filter = ['status', 'tipo_exame']
    search_fields = ['funcionario__pessoa__nome']
    dashboard_date_field = 'data_agendamento'
    dashboard_date_filter_fields = '__all__'

    def anexo_link(self, obj):
        if obj.anexo:
            return format_html('<a href="{}" target="_blank">📎</a>',
                               obj.anexo.url)
        return '—'
    anexo_link.short_description = 'Anexo'


@admin.register(FichaRegistro)
class FichaRegistroAdmin(ExportToXLSMixin, AdminDashboardAndTopFilterMixin,
                         admin.ModelAdmin):
    list_display = ['funcionario', 'data_registro', 'anexo_link',
                    'dt_cadastro']
    search_fields = ['funcionario__pessoa__nome']
    dashboard_date_field = 'dt_cadastro'

    def anexo_link(self, obj):
        if obj.anexo:
            return format_html('<a href="{}" target="_blank">📎</a>',
                               obj.anexo.url)
        return '—'
    anexo_link.short_description = 'Anexo'


@admin.register(CartaoPonto)
class CartaoPontoAdmin(admin.ModelAdmin):
    list_display = ['funcionario', 'numero_cartao', 'data_inicio_vigencia',
                    'status']
    list_filter = ['status']
    search_fields = ['numero_cartao', 'funcionario__pessoa__nome']


@admin.register(ExamePeriodico)
class ExamePeriodicoAdmin(ExportToXLSMixin, AdminDashboardAndTopFilterMixin,
                          admin.ModelAdmin):
    list_display = ['funcionario', 'status', 'data_agendamento',
                    'data_realizacao', 'data_proximo_exame', 'anexo_link',
                    'dt_cadastro']
    list_filter = ['status']
    search_fields = ['funcionario__pessoa__nome']
    dashboard_date_field = 'data_agendamento'
    dashboard_date_filter_fields = '__all__'

    def anexo_link(self, obj):
        if obj.anexo:
            return format_html('<a href="{}" target="_blank">📎</a>',
                               obj.anexo.url)
        return '—'
    anexo_link.short_description = 'Anexo'


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'carga_horaria', 'validade_meses', 'status']
    list_filter = ['status']
    search_fields = ['nome']


@admin.register(CursoFuncionario)
class CursoFuncionarioAdmin(ExportToXLSMixin, AdminDashboardAndTopFilterMixin,
                            admin.ModelAdmin):
    list_display = ['funcionario', 'curso', 'status', 'data_realizacao',
                    'data_validade', 'vencido_badge', 'anexo_link']
    list_filter = ['status', 'curso']
    search_fields = ['funcionario__pessoa__nome', 'curso__nome']
    dashboard_date_field = 'data_realizacao'
    dashboard_date_filter_fields = '__all__'

    def anexo_link(self, obj):
        if obj.anexo_certificado:
            return format_html('<a href="{}" target="_blank">🎓</a>',
                               obj.anexo_certificado.url)
        return '—'
    anexo_link.short_description = 'Certificado'

    def vencido_badge(self, obj):
        if obj.vencido:
            return format_html(
                '<span style="background:#dc3545;color:#fff;padding:2px 7px;'
                'border-radius:4px;font-size:.75rem">VENCIDO</span>')
        return '—'
    vencido_badge.short_description = 'Vencido'


@admin.register(Ferias)
class FeriasAdmin(ExportToXLSMixin, AdminDashboardAndTopFilterMixin,
                  admin.ModelAdmin):
    list_display = ['funcionario', 'status', 'periodo_aquisitivo_inicio',
                    'periodo_aquisitivo_final', 'periodo_concessivo_final',
                    'dias_direito', 'dias_gozados', 'saldo_dias',
                    'data_inicio_ferias', 'data_final_ferias']
    list_filter = ['status']
    search_fields = ['funcionario__pessoa__nome']
    dashboard_date_field = 'periodo_aquisitivo_inicio'
    dashboard_date_filter_fields = '__all__'


@admin.register(HistoricoFuncionario)
class HistoricoFuncionarioAdmin(admin.ModelAdmin):
    list_display = ['funcionario', 'operacao', 'usuario', 'dt_operacao']
    list_filter = ['operacao']
    search_fields = ['descricao', 'funcionario__pessoa__nome']
    date_hierarchy = 'dt_operacao'


@admin.register(ParametrosGestaoPessoas)
class ParametrosGestaoPessoasAdmin(admin.ModelAdmin):
    list_display = ['estabelecimento', 'status']
    filter_horizontal = [
        'usuarios_visualizacao', 'grupos_visualizacao',
        'usuarios_edicao', 'grupos_edicao',
        'usuarios_exclusao', 'grupos_exclusao',
    ]
