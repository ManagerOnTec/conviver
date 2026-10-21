from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from dominios.admin_dashboard_mixins import AdminDashboardAndTopFilterMixin
from dominios.utils import SomenteLeituraEstatisticoAdminMixin
from .models import (
    Evolucao, Prescricao, ProdutoPrescricao, Adep, SinaisVitais,
    SAE, Diagnostico, PlanoCuidados, PerdasGanhos, Psicoterapia
)


@admin.register(Evolucao)
class EvolucaoAdmin(SomenteLeituraEstatisticoAdminMixin, AdminDashboardAndTopFilterMixin, admin.ModelAdmin):
    # Módulo estatístico: evolução é criada/assinada pelo fluxo do prontuário.
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
class PrescricaoAdmin(SomenteLeituraEstatisticoAdminMixin, AdminDashboardAndTopFilterMixin, admin.ModelAdmin):
    # Módulo estatístico: prescrição é criada/assinada pelo fluxo do prontuário.
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
class ProdutoPrescricaoAdmin(SomenteLeituraEstatisticoAdminMixin, admin.ModelAdmin):
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
class SinaisVitaisAdmin(SomenteLeituraEstatisticoAdminMixin, AdminDashboardAndTopFilterMixin, admin.ModelAdmin):
    # Módulo estatístico: sinais vitais são registrados pelo fluxo do prontuário.
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



# ==========================================================================
# MÓDULOS ESTATÍSTICOS DO PRONTUÁRIO
# Somente consulta: registros são criados/editados/assinados no fluxo do
# prontuário (com auditoria, parametrização e geração de PDF).
# ==========================================================================


class _ProntuarioEstatisticoAdminMixin(SomenteLeituraEstatisticoAdminMixin):
    """Base comum dos módulos estatísticos de prontuário."""

    dashboard_date_field = 'dt_registro'
    date_hierarchy = 'dt_registro'
    ordering = ('-dt_registro', '-id')

    def paciente_nome(self, obj):
        atendimento = getattr(obj, 'atendimento', None)
        pessoa = getattr(atendimento, 'pessoa', None) if atendimento else None
        return pessoa.nome if pessoa else '-'
    paciente_nome.short_description = 'Paciente'
    paciente_nome.admin_order_field = 'atendimento__pessoa__nome'

    def status_badge(self, obj):
        if getattr(obj, 'status', None) == 'A':
            return format_html(
                '<span style="background-color: #28a745; color: #fff; padding: 2px 6px; '
                'border-radius: 3px; font-size: 0.7rem; font-weight: bold;">Ativo</span>')
        return format_html(
            '<span style="background-color: #dc3545; color: #fff; padding: 2px 6px; '
            'border-radius: 3px; font-size: 0.7rem; font-weight: bold;">Inativo</span>')
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def assinado_badge(self, obj):
        if getattr(obj, 'assinar', False):
            return format_html(
                '<span style="background-color: #0d6efd; color: #fff; padding: 2px 6px; '
                'border-radius: 3px; font-size: 0.7rem; font-weight: bold;">Assinado</span>')
        return format_html('<span style="color: #999;">-</span>')
    assinado_badge.short_description = 'Assinatura'

    def total_hoje_e_assinados(self, queryset):
        """(total, registrados hoje, assinados) — tolerante a modelos sem 'assinar'."""
        hoje = timezone.now().date()
        tem_assinar = any(
            f.name == 'assinar' for f in queryset.model._meta.fields)
        assinados = queryset.filter(assinar=True).count() if tem_assinar else 0
        return (
            queryset.count(),
            queryset.filter(dt_registro__date=hoje).count(),
            assinados,
        )


@admin.register(Diagnostico)
class DiagnosticoAdmin(_ProntuarioEstatisticoAdminMixin, AdminDashboardAndTopFilterMixin, admin.ModelAdmin):
    list_display = ('id', 'paciente_nome', 'cids', 'estabelecimento',
                    'dt_registro', 'us_registro', 'assinado_badge', 'status_badge')
    list_filter = ('status', 'estabelecimento', 'dt_registro', 'us_registro')
    search_fields = ('id', 'atendimento__pessoa__nome', 'atendimento__pessoa__cpf',
                     'diagnostico__codigo', 'diagnostico__descricao')
    autocomplete_fields = ('atendimento',)
    list_select_related = ('atendimento__pessoa', 'estabelecimento')
    list_prefetch_related = ('diagnostico',)

    def cids(self, obj):
        # 'diagnostico' é ManyToMany: list_display exige um método.
        return ', '.join(str(d) for d in obj.diagnostico.all()) or '-'
    cids.short_description = 'Diagnóstico (CID)'

    def get_dashboard_kpis(self, request, queryset):
        total, hoje, assinados = self.total_hoje_e_assinados(queryset)
        pacientes = queryset.exclude(atendimento__pessoa__isnull=True) \
            .values('atendimento__pessoa_id').distinct().count()
        return [
            {'title': 'Total de Diagnósticos', 'value': f'{total:,}'.replace(',', '.'),
             'subtitle': 'Registros no filtro', 'color_class': 'kpi-blue', 'icon': '🧾'},
            {'title': 'Registrados Hoje', 'value': f'{hoje:,}'.replace(',', '.'),
             'subtitle': f"Em {timezone.now():%d/%m/%Y}", 'color_class': 'kpi-green', 'icon': '📅'},
            {'title': 'Assinados', 'value': f'{assinados:,}'.replace(',', '.'),
             'subtitle': 'Com PDF assinado', 'color_class': 'kpi-purple', 'icon': '✍️'},
            {'title': 'Pacientes', 'value': f'{pacientes:,}'.replace(',', '.'),
             'subtitle': 'Atendimentos distintos', 'color_class': 'kpi-orange', 'icon': '👥'},
        ]


@admin.register(Psicoterapia)
class PsicoterapiaAdmin(_ProntuarioEstatisticoAdminMixin, AdminDashboardAndTopFilterMixin, admin.ModelAdmin):
    list_display = ('id', 'paciente_nome', 'estabelecimento',
                    'dt_registro', 'us_registro', 'status_badge')
    list_filter = ('status', 'estabelecimento', 'dt_registro', 'us_registro')
    search_fields = ('id', 'atendimento__pessoa__nome', 'atendimento__pessoa__cpf')
    autocomplete_fields = ('atendimento',)
    list_select_related = ('atendimento__pessoa', 'estabelecimento')

    def get_dashboard_kpis(self, request, queryset):
        total, hoje, _ = self.total_hoje_e_assinados(queryset)
        pacientes = queryset.exclude(atendimento__pessoa__isnull=True) \
            .values('atendimento__pessoa_id').distinct().count()
        return [
            {'title': 'Total de Sessões', 'value': f'{total:,}'.replace(',', '.'),
             'subtitle': 'Registros no filtro', 'color_class': 'kpi-blue', 'icon': '🛋'},
            {'title': 'Registradas Hoje', 'value': f'{hoje:,}'.replace(',', '.'),
             'subtitle': f"Em {timezone.now():%d/%m/%Y}", 'color_class': 'kpi-green', 'icon': '📅'},
            {'title': 'Pacientes', 'value': f'{pacientes:,}'.replace(',', '.'),
             'subtitle': 'Em acompanhamento', 'color_class': 'kpi-purple', 'icon': '👥'},
        ]


@admin.register(Adep)
class AdepAdmin(_ProntuarioEstatisticoAdminMixin, AdminDashboardAndTopFilterMixin, admin.ModelAdmin):
    dashboard_date_field = 'data_hora'
    date_hierarchy = 'data_hora'
    list_display = ('id', 'paciente_nome', 'prescricao', 'fase_adep',
                    'data_hora', 'dt_adep', 'us_adep', 'status_badge')
    list_filter = ('fase_adep', 'status', 'estabelecimento', 'data_hora')
    search_fields = ('id', 'atendimento__pessoa__nome', 'atendimento__pessoa__cpf',
                     'prescricao__id')
    autocomplete_fields = ('atendimento',)
    list_select_related = ('atendimento__pessoa', 'prescricao')

    def get_dashboard_kpis(self, request, queryset):
        total = queryset.count()
        pendentes = queryset.filter(fase_adep='P').count()
        administrados = queryset.filter(fase_adep='A').count()
        nao_adm = queryset.filter(fase_adep='N').count()
        return [
            {'title': 'Total de ADEPs', 'value': f'{total:,}'.replace(',', '.'),
             'subtitle': 'Registros no filtro', 'color_class': 'kpi-blue', 'icon': '💊'},
            {'title': 'Pendentes', 'value': f'{pendentes:,}'.replace(',', '.'),
             'subtitle': 'Aguardando administração', 'color_class': 'kpi-orange', 'icon': '⏳'},
            {'title': 'Administrados', 'value': f'{administrados:,}'.replace(',', '.'),
             'subtitle': 'Doses aplicadas', 'color_class': 'kpi-green', 'icon': '✅'},
            {'title': 'Não Administrados', 'value': f'{nao_adm:,}'.replace(',', '.'),
             'subtitle': 'Registrados como não adm.', 'color_class': 'kpi-red', 'icon': '🚫'},
        ]


@admin.register(SAE)
class SAEAdmin(_ProntuarioEstatisticoAdminMixin, AdminDashboardAndTopFilterMixin, admin.ModelAdmin):
    list_display = ('id', 'paciente_nome', 'estabelecimento',
                    'dt_registro', 'us_registro', 'assinado_badge', 'status_badge')
    list_filter = ('status', 'estabelecimento', 'dt_registro', 'us_registro')
    search_fields = ('id', 'atendimento__pessoa__nome', 'atendimento__pessoa__cpf')
    autocomplete_fields = ('atendimento',)
    list_select_related = ('atendimento__pessoa', 'estabelecimento')

    def get_dashboard_kpis(self, request, queryset):
        total, hoje, assinados = self.total_hoje_e_assinados(queryset)
        pacientes = queryset.exclude(atendimento__pessoa__isnull=True) \
            .values('atendimento__pessoa_id').distinct().count()
        return [
            {'title': 'Total SAE', 'value': f'{total:,}'.replace(',', '.'),
             'subtitle': 'Registros no filtro', 'color_class': 'kpi-blue', 'icon': '🩹'},
            {'title': 'Registrados Hoje', 'value': f'{hoje:,}'.replace(',', '.'),
             'subtitle': f"Em {timezone.now():%d/%m/%Y}", 'color_class': 'kpi-green', 'icon': '📅'},
            {'title': 'Assinados', 'value': f'{assinados:,}'.replace(',', '.'),
             'subtitle': 'Com PDF assinado', 'color_class': 'kpi-purple', 'icon': '✍️'},
            {'title': 'Pacientes', 'value': f'{pacientes:,}'.replace(',', '.'),
             'subtitle': 'Atendimentos distintos', 'color_class': 'kpi-orange', 'icon': '👥'},
        ]


@admin.register(PlanoCuidados)
class PlanoCuidadosAdmin(_ProntuarioEstatisticoAdminMixin, AdminDashboardAndTopFilterMixin, admin.ModelAdmin):
    list_display = ('id', 'paciente_nome', 'estabelecimento',
                    'dt_registro', 'us_registro', 'assinado_badge', 'status_badge')
    list_filter = ('status', 'estabelecimento', 'dt_registro', 'us_registro')
    search_fields = ('id', 'atendimento__pessoa__nome', 'atendimento__pessoa__cpf')
    autocomplete_fields = ('atendimento',)
    list_select_related = ('atendimento__pessoa', 'estabelecimento')

    def get_dashboard_kpis(self, request, queryset):
        total, hoje, assinados = self.total_hoje_e_assinados(queryset)
        pacientes = queryset.exclude(atendimento__pessoa__isnull=True) \
            .values('atendimento__pessoa_id').distinct().count()
        return [
            {'title': 'Total de Planos', 'value': f'{total:,}'.replace(',', '.'),
             'subtitle': 'Registros no filtro', 'color_class': 'kpi-blue', 'icon': '📋'},
            {'title': 'Registrados Hoje', 'value': f'{hoje:,}'.replace(',', '.'),
             'subtitle': f"Em {timezone.now():%d/%m/%Y}", 'color_class': 'kpi-green', 'icon': '📅'},
            {'title': 'Assinados', 'value': f'{assinados:,}'.replace(',', '.'),
             'subtitle': 'Com PDF assinado', 'color_class': 'kpi-purple', 'icon': '✍️'},
            {'title': 'Pacientes', 'value': f'{pacientes:,}'.replace(',', '.'),
             'subtitle': 'Atendimentos distintos', 'color_class': 'kpi-orange', 'icon': '👥'},
        ]


@admin.register(PerdasGanhos)
class PerdasGanhosAdmin(_ProntuarioEstatisticoAdminMixin, AdminDashboardAndTopFilterMixin, admin.ModelAdmin):
    list_display = ('id', 'paciente_nome', 'peso', 'altura', 'estabelecimento',
                    'dt_registro', 'us_registro', 'assinado_badge', 'status_badge')
    list_filter = ('status', 'estabelecimento', 'dt_registro', 'us_registro')
    search_fields = ('id', 'atendimento__pessoa__nome', 'atendimento__pessoa__cpf')
    autocomplete_fields = ('atendimento',)
    list_select_related = ('atendimento__pessoa', 'estabelecimento')

    def get_dashboard_kpis(self, request, queryset):
        total, hoje, assinados = self.total_hoje_e_assinados(queryset)
        pacientes = queryset.exclude(atendimento__pessoa__isnull=True) \
            .values('atendimento__pessoa_id').distinct().count()
        return [
            {'title': 'Total de Aferições', 'value': f'{total:,}'.replace(',', '.'),
             'subtitle': 'Registros no filtro', 'color_class': 'kpi-blue', 'icon': '⚖️'},
            {'title': 'Aferições Hoje', 'value': f'{hoje:,}'.replace(',', '.'),
             'subtitle': f"Em {timezone.now():%d/%m/%Y}", 'color_class': 'kpi-green', 'icon': '📅'},
            {'title': 'Assinadas', 'value': f'{assinados:,}'.replace(',', '.'),
             'subtitle': 'Com PDF assinado', 'color_class': 'kpi-purple', 'icon': '✍️'},
            {'title': 'Pacientes', 'value': f'{pacientes:,}'.replace(',', '.'),
             'subtitle': 'Atendimentos distintos', 'color_class': 'kpi-orange', 'icon': '👥'},
        ]
