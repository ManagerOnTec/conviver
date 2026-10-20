from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from dominios.admin_dashboard_mixins import AdminDashboardAndTopFilterMixin
from .models import (
    Evolucao, Prescricao, ProdutoPrescricao, Adep, SinaisVitais,
    SAE, Diagnostico, PlanoCuidados, PerdasGanhos
)


@admin.register(Evolucao)
class EvolucaoAdmin(AdminDashboardAndTopFilterMixin, admin.ModelAdmin):
    dashboard_date_field = 'dt_registro'
    list_display = ('id', 'paciente_nome', 'tipo_evolucao', 'estabelecimento', 'dt_registro', 'us_registro', 'status_badge')
    list_filter = ('tipo_evolucao', 'status', 'estabelecimento', 'dt_registro', 'us_registro')
    search_fields = ('id', 'evolucao', 'atendimento__pessoa__nome', 'atendimento__pessoa__cpf')
    autocomplete_fields = ('atendimento',)
    date_hierarchy = 'dt_registro'
    ordering = ('-id',)

    def paciente_nome(self, obj):
        p = obj.atendimento.pessoa if obj.atendimento else None
        return p.nome if p else '-'
    paciente_nome.short_description = 'Paciente'
    paciente_nome.admin_order_field = 'atendimento__pessoa__nome'

    def status_badge(self, obj):
        if obj.status == 'A':
            return format_html('<span style="background-color: #28a745; color: #fff; padding: 2px 6px; border-radius: 3px; font-size: 0.7rem; font-weight: bold;">Ativo</span>')
        return format_html('<span style="background-color: #dc3545; color: #fff; padding: 2px 6px; border-radius: 3px; font-size: 0.7rem; font-weight: bold;">Inativo</span>')
    status_badge.short_description = 'Status'

    def get_dashboard_kpis(self, request, queryset):
        hoje = timezone.now().date()
        total = queryset.count()
        total_hoje = queryset.filter(dt_registro__date=hoje).count()
        assinadas = queryset.filter(assinar=True).count()
        com_anexo = queryset.exclude(anexo_evolucao='').count()

        return [
            {
                'title': 'Total Evoluções',
                'value': f"{total:,}".replace(',', '.'),
                'subtitle': 'Registros correspondentes',
                'color_class': 'kpi-blue',
                'icon': '📝',
            },
            {
                'title': 'Registradas Hoje',
                'value': f"{total_hoje:,}".replace(',', '.'),
                'subtitle': f"Em {hoje.strftime('%d/%m/%Y')}",
                'color_class': 'kpi-green',
                'icon': '📅',
            },
            {
                'title': 'Assinadas / Prontas',
                'value': f"{assinadas:,}".replace(',', '.'),
                'subtitle': 'Com validação ativa',
                'color_class': 'kpi-purple',
                'icon': '✍️',
            },
            {
                'title': 'Com Anexos / Imagens',
                'value': f"{com_anexo:,}".replace(',', '.'),
                'subtitle': 'Fotos e laudos clínicos',
                'color_class': 'kpi-orange',
                'icon': '📷',
            },
        ]


@admin.register(Prescricao)
class PrescricaoAdmin(AdminDashboardAndTopFilterMixin, admin.ModelAdmin):
    dashboard_date_field = 'dt_registro'
    list_display = ('id', 'paciente_nome', 'fase', 'dt_inicio', 'dt_final', 'estabelecimento', 'status')
    list_filter = ('fase', 'status', 'estabelecimento', 'dt_inicio')
    search_fields = ('id', 'atendimento__pessoa__nome', 'atendimento__pessoa__cpf')
    autocomplete_fields = ('atendimento',)
    date_hierarchy = 'dt_registro'
    ordering = ('-id',)
    inlines = ()  # definido após ProdutoPrescricaoInline (ver abaixo)

    def paciente_nome(self, obj):
        p = obj.atendimento.pessoa if obj.atendimento else None
        return p.nome if p else '-'
    paciente_nome.short_description = 'Paciente'
    paciente_nome.admin_order_field = 'atendimento__pessoa__nome'

    def get_dashboard_kpis(self, request, queryset):
        total = queryset.count()
        em_uso = queryset.filter(fase='U').count()
        suspensas = queryset.exclude(us_suspensao__isnull=True).count()
        ativas = queryset.filter(status='A').count()

        return [
            {
                'title': 'Total Prescrições',
                'value': f"{total:,}".replace(',', '.'),
                'subtitle': 'No filtro atual',
                'color_class': 'kpi-blue',
                'icon': '💊',
            },
            {
                'title': 'Em Uso (Vigentes)',
                'value': f"{em_uso:,}".replace(',', '.'),
                'subtitle': 'Fase ativa de aplicação',
                'color_class': 'kpi-green',
                'icon': '⚡',
            },
            {
                'title': 'Suspensas',
                'value': f"{suspensas:,}".replace(',', '.'),
                'subtitle': 'Canceladas / Interrompidas',
                'color_class': 'kpi-red',
                'icon': '⏹',
            },
            {
                'title': 'Prescrições Ativas',
                'value': f"{ativas:,}".replace(',', '.'),
                'subtitle': 'Status operacional A',
                'color_class': 'kpi-purple',
                'icon': '✅',
            },
        ]


class ProdutoPrescricaoInline(admin.TabularInline):
    """Itens da prescrição real — apenas leitura de contexto.

    O lançamento de itens é feito na tela *Produto da Prescrição* (com select2)
    ou pelo fluxo do prontuário, que calcula datas, gera ADEP e assina o PDF.
    """

    model = ProdutoPrescricao
    fk_name = 'prescricao'
    extra = 0
    can_delete = False
    fields = ('produto', 'intervalo_horas', 'hora_inicio_produto',
              'se_necessario', 'dose_unica', 'observacao', 'dt_inicio', 'status')
    readonly_fields = fields
    ordering = ('dt_inicio',)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


PrescricaoAdmin.inlines = (ProdutoPrescricaoInline,)


@admin.register(ProdutoPrescricao)
class ProdutoPrescricaoAdmin(admin.ModelAdmin):
    """Produto da Prescrição (item de uma prescrição real).

    Antes não havia tela no admin. Aqui os campos relacionados usam select2 de
    digitação (autocomplete do Django) para localizar produto, intervalo, horário
    de início e a prescrição sem rolar listas enormes.

    `atendimento`/`estabelecimento` são derivados da prescrição
    (`ProdutoPrescricao.save`), por isso ficam ocultos no formulário.
    """

    autocomplete_fields = ('prescricao', 'produto', 'intervalo_horas',
                           'hora_inicio_produto')

    class Media:
        js = ('js/admin_select2_largura.js',)

    exclude = ('atendimento', 'estabelecimento')
    list_display = ('id', 'prescricao', 'produto', 'intervalo_horas',
                    'hora_inicio_produto', 'se_necessario', 'dose_unica',
                    'dt_inicio', 'dt_final', 'status')
    list_display_links = ('id', 'produto')
    list_filter = ('status', 'se_necessario', 'dose_unica', 'dt_inicio')
    search_fields = ('id', 'produto__descricao', 'prescricao__id',
                     'atendimento__pessoa__nome')
    date_hierarchy = 'dt_inicio'
    ordering = ('-id',)
    list_per_page = 20

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(SinaisVitais)
class SinaisVitaisAdmin(AdminDashboardAndTopFilterMixin, admin.ModelAdmin):
    dashboard_date_field = 'dt_registro'
    list_display = (
        'id', 'paciente_nome', 'temperatura', 'pressao_arterial',
        'frequencia_cardiaca', 'saturacao_oxigenio', 'controle_glicemia', 'dt_registro'
    )
    list_filter = ('status', 'dt_registro', 'estabelecimento')
    search_fields = ('id', 'atendimento__pessoa__nome', 'observacoes')
    autocomplete_fields = ('atendimento',)
    date_hierarchy = 'dt_registro'
    ordering = ('-dt_registro',)

    def paciente_nome(self, obj):
        p = obj.atendimento.pessoa if obj.atendimento else None
        return p.nome if p else '-'
    paciente_nome.short_description = 'Paciente'
    paciente_nome.admin_order_field = 'atendimento__pessoa__nome'

    def get_dashboard_kpis(self, request, queryset):
        total = queryset.count()
        hoje = timezone.now().date()
        afericoes_hoje = queryset.filter(dt_registro__date=hoje).count()

        # Alertas de desvios vitais (temperatura > 37.5 ou saturação < 92%)
        alerta_febril = queryset.filter(temperatura__gte=37.8).count()
        alerta_spo2 = queryset.filter(saturacao_oxigenio__lt=92, saturacao_oxigenio__gt=0).count()

        return [
            {
                'title': 'Total Aferições',
                'value': f"{total:,}".replace(',', '.'),
                'subtitle': 'Registros correspondentes',
                'color_class': 'kpi-blue',
                'icon': '🩺',
            },
            {
                'title': 'Aferições Hoje',
                'value': f"{afericoes_hoje:,}".replace(',', '.'),
                'subtitle': f"Em {hoje.strftime('%d/%m/%Y')}",
                'color_class': 'kpi-green',
                'icon': '⏱',
            },
            {
                'title': 'Alerta Febril (≥ 37.8°C)',
                'value': f"{alerta_febril:,}".replace(',', '.'),
                'subtitle': 'Sinais de hipertermia',
                'color_class': 'kpi-orange' if alerta_febril == 0 else 'kpi-red',
                'icon': '🌡',
            },
            {
                'title': 'Alerta SpO2 (< 92%)',
                'value': f"{alerta_spo2:,}".replace(',', '.'),
                'subtitle': 'Dessaturação detectada',
                'color_class': 'kpi-purple' if alerta_spo2 == 0 else 'kpi-red',
                'icon': '🫁',
            },
        ]

