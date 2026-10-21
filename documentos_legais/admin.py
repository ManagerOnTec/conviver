from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse

from dominios.admin_dashboard_mixins import AdminDashboardAndTopFilterMixin
from dominios.utils import (
    AdminEstabelecimentoPadraoMixin, AdminSaveModelAuditMixin,
    StatusFilterAdminMixin, SomenteLeituraEstatisticoAdminMixin,
)
from admin_cadastros.utils import EstabelecimentoFilterAdminMixin
from .forms import ModeloDocumentoLegalAdminForm, TipoDocumentoLegalAdminForm
from .models import DocumentoLegalInternacao, ModeloDocumentoLegal, TipoDocumentoLegal


@admin.register(TipoDocumentoLegal)
class TipoDocumentoLegalAdmin(AdminSaveModelAuditMixin, admin.ModelAdmin):
    form = TipoDocumentoLegalAdminForm
    list_display = ('nome', 'slug', 'ordem', 'padrao_sistema', 'status')
    list_editable = ('ordem', 'status')
    search_fields = ('nome', 'slug')
    list_filter = (StatusFilterAdminMixin, 'padrao_sistema')
    ordering = ('ordem', 'nome')


@admin.register(ModeloDocumentoLegal)
class ModeloDocumentoLegalAdmin(AdminEstabelecimentoPadraoMixin, AdminSaveModelAuditMixin, admin.ModelAdmin):
    form = ModeloDocumentoLegalAdminForm
    list_display = ('nome_modelo', 'tipo_documento', 'estabelecimento', 'exige_assinatura_responsavel', 'exige_assinatura_atendente', 'status')
    list_filter = (StatusFilterAdminMixin, 'tipo_documento', 'estabelecimento', 'exige_assinatura_responsavel', 'exige_assinatura_atendente')
    search_fields = ('nome_modelo', 'titulo_documento', 'conteudo_html')
    autocomplete_fields = ('tipo_documento', 'estabelecimento')


@admin.register(DocumentoLegalInternacao)
class DocumentoLegalInternacaoAdmin(
        SomenteLeituraEstatisticoAdminMixin,
        AdminDashboardAndTopFilterMixin,
        admin.ModelAdmin):
    """
    Módulo estatístico: termos/documentos legais GERADOS.

    O documento é criado/assinado pelo fluxo do atendimento (selfie, foto do
    documento, hash do PDF e IP). No admin é somente consulta.

    Permanece no app 'documentos_legais' (agrupado no admin como
    "B. DOCUMENTOS LEGAIS"), sem alteração de tabela ou de ContentType.
    """
    dashboard_date_field = 'dt_registro'
    date_hierarchy = 'dt_registro'
    ordering = ('-dt_registro', '-id')

    list_display = (
        'id', 'codigo_documento', 'titulo_documento', 'paciente_nome',
        'atendimento_link', 'tipo_documento', 'estabelecimento',
        'dt_registro', 'us_registro', 'pdf_link', 'status_badge',
    )
    list_display_links = ('id', 'codigo_documento')
    list_filter = (
        EstabelecimentoFilterAdminMixin,
        StatusFilterAdminMixin,
        'tipo_documento', 'modelo_documento', 'dt_registro', 'us_registro',
    )
    search_fields = (
        'id', 'codigo_documento', 'titulo_documento', 'hash_pdf',
        'responsavel_nome', 'responsavel_cpf',
        'pessoa__nome', 'pessoa__cpf',
        'atendimento__id', 'atendimento__pessoa__nome', 'atendimento__pessoa__cpf',
    )
    autocomplete_fields = ('atendimento', 'pessoa')
    list_select_related = (
        'pessoa', 'atendimento__pessoa', 'tipo_documento',
        'modelo_documento', 'estabelecimento', 'us_registro',
    )

    def get_dashboard_kpis(self, request, queryset):
        hoje = timezone.now().date()
        total = queryset.count()
        total_hoje = queryset.filter(dt_registro__date=hoje).count()
        com_pdf = queryset.exclude(pdf_gerado='').exclude(pdf_gerado__isnull=True).count()
        pacientes = queryset.exclude(pessoa__isnull=True) \
            .values('pessoa_id').distinct().count()
        return [
            {'title': 'Total de Termos', 'value': f'{total:,}'.replace(',', '.'),
             'subtitle': 'Documentos no filtro', 'color_class': 'kpi-blue', 'icon': '⚖️'},
            {'title': 'Gerados Hoje', 'value': f'{total_hoje:,}'.replace(',', '.'),
             'subtitle': f'Em {hoje:%d/%m/%Y}', 'color_class': 'kpi-green', 'icon': '📅'},
            {'title': 'Com PDF', 'value': f'{com_pdf:,}'.replace(',', '.'),
             'subtitle': 'Arquivos disponíveis', 'color_class': 'kpi-purple', 'icon': '📄'},
            {'title': 'Pacientes', 'value': f'{pacientes:,}'.replace(',', '.'),
             'subtitle': 'Pessoas identificadas', 'color_class': 'kpi-orange', 'icon': '👥'},
        ]

    def paciente_nome(self, obj):
        p = obj.pessoa or (obj.atendimento.pessoa if obj.atendimento else None)
        return p.nome if p else '-'
    paciente_nome.short_description = 'Paciente'
    paciente_nome.admin_order_field = 'pessoa__nome'

    def atendimento_link(self, obj):
        if not obj.atendimento_id:
            return format_html('<span style="color:#999">-</span>')
        return format_html(
            '<a href="{}">#{}</a>',
            reverse('admin:atendimentos_atendimento_change', args=[obj.atendimento_id]),
            obj.atendimento_id)
    atendimento_link.short_description = 'Atendimento'
    atendimento_link.admin_order_field = 'atendimento__id'

    def pdf_link(self, obj):
        if obj.pdf_gerado and obj.pdf_gerado.name:
            return format_html(
                '<a href="{}" target="_blank">📄 {}</a>',
                obj.pdf_gerado.url, obj.pdf_gerado.name.rsplit('/', 1)[-1])
        return format_html('<span style="color:#dc3545">Sem PDF</span>')
    pdf_link.short_description = 'PDF'

    def status_badge(self, obj):
        if obj.status == 'A':
            return format_html(
                '<span style="background-color:#28a745;color:#fff;padding:2px 6px;'
                'border-radius:3px;font-size:0.7rem;font-weight:bold;">Ativo</span>')
        return format_html(
            '<span style="background-color:#dc3545;color:#fff;padding:2px 6px;'
            'border-radius:3px;font-size:0.7rem;font-weight:bold;">Inativo</span>')
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

