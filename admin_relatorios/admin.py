from django.db import models
from django.db.models import Q
from .forms import TextoDocumentoPadraoForm
from .models import TextoDocumentoPadrao
from django.contrib import admin
from .models import GerenciadorRelatorioGeral, GerenciadorRelatorioPersonalizado, Relatorio
from .forms import GerenciadorRelatorioGeralForm, GerenciadorRelatorioPersonalizadoForm
from django.utils import timezone
from django.http import HttpResponse
from django.utils.html import format_html
from django.contrib import messages
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from dominios.admin_dashboard_mixins import AdminDashboardAndTopFilterMixin
from admin_evolucoes.models import TipoEvolucao
from documentos_legais.models import TipoDocumentoLegal, ModeloDocumentoLegal, DocumentoLegalInternacao
from prontuarios.models import Evolucao
from .export_services import (
    gerar_zip_dossie_pacientes,
    gerar_zip_relatorios_selecionados,
    exportar_relatorios_xlsx,
    TIPO_LABELS,
)


@admin.register(GerenciadorRelatorioGeral)
class GerenciadorRelatorioGeralAdmin(admin.ModelAdmin):
    form = GerenciadorRelatorioGeralForm
    list_display = ('dados_header', 'dados_right_header',
                    'dados_footer', 'estabelecimento', 'status')
    list_filter = ('estabelecimento', 'status')
    search_fields = ('dados_header', 'dados_footer')
    # Adicione mais configurações conforme necessário

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)

        # Verifica se a solicitação veio de um campo de autocomplete
        if 'HTTP_REFERER' in request.META:
            referer_path = request.META['HTTP_REFERER'].split(
                request.META['HTTP_HOST'])[1]
            if '/add/' in referer_path or '/change/' in referer_path:
                # Se a solicitação veio de um campo de autocomplete, filtra os objetos inativos
                print('DEBUG: The request came from an autocomplete field')
                queryset = queryset.filter(status='A')

        return queryset, use_distinct

    def save_model(self, request, obj, form, change):
        if not change:  # se estiver criando um novo objeto
            print('DEBUG: Creating a new object')
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:  # se estiver editando um objeto existente
            print('DEBUG: Editing an existing object')
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()

        super().save_model(request, obj, form, change)


@admin.register(GerenciadorRelatorioPersonalizado)
class GerenciadorRelatorioPersonalizadoAdmin(admin.ModelAdmin):
    form = GerenciadorRelatorioPersonalizadoForm
    list_display = ('relatorio', 'tipo_evolucao', 'tipo_documento_legal', 'dados_header',
                    'dados_right_header', 'dados_footer', 'estabelecimento', 'status')
    list_filter = ('relatorio', 'tipo_evolucao', 'tipo_documento_legal', 'estabelecimento', 'status')
    search_fields = ('dados_header', 'dados_footer')
    # Adicione mais configurações conforme necessário

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)

        # Verifica se a solicitação veio de um campo de autocomplete
        if 'HTTP_REFERER' in request.META:
            referer_path = request.META['HTTP_REFERER'].split(
                request.META['HTTP_HOST'])[1]
            if '/add/' in referer_path or '/change/' in referer_path:
                # Se a solicitação veio de um campo de autocomplete, filtra os objetos inativos
                print('DEBUG: The request came from an autocomplete field')
                queryset = queryset.filter(status='A')

        return queryset, use_distinct

    def save_model(self, request, obj, form, change):
        if not change:  # se estiver criando um novo objeto
            print('DEBUG: Creating a new object')
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:  # se estiver editando um objeto existente
            print('DEBUG: Editing an existing object')
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()

        super().save_model(request, obj, form, change)


class TextoDocumentoPadraoAdmin(admin.ModelAdmin):
    form = TextoDocumentoPadraoForm
    list_display = ('descricao', 'tipo', 'status',
                    'dt_registro', 'us_registro')
    list_filter = ('tipo', 'status')
    search_fields = ('descricao', 'texto')
    readonly_fields = ('dt_registro', 'us_registro',
                       'dt_atualizacao', 'us_atualizacao')
    fieldsets = (
        ('Texto Padrão', {
            'classes': ('wide',),
            'fields': ('tipo', 'descricao', 'texto', 'status'),
        }),
        ('Auditoria', {
            'classes': ('collapse',),
            'fields': ('dt_registro', 'us_registro',
                       'dt_atualizacao', 'us_atualizacao'),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.us_registro_id:
            obj.us_registro = request.user
        obj.us_atualizacao = request.user
        super().save_model(request, obj, form, change)


class PDFAtivoFilter(admin.SimpleListFilter):
    title = 'PDF Ativo / Vigente'
    parameter_name = 'pdf_ativo'

    def lookups(self, request, model_admin):
        return (
            ('A', 'Somente Ativos (Vigentes)'),
            ('I', 'Somente Inativos / Obsoletos'),
            ('ALL', 'Todos os Registros'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'I':
            return queryset.filter(status='I')
        elif self.value() == 'ALL':
            return queryset
        elif self.value() == 'A':
            return queryset.filter(status='A')
        # Padrão: exibe relatórios ativos
        return queryset.filter(status='A')


class PacienteRelatorioFilter(admin.SimpleListFilter):
    title = 'Paciente (Seletor Rápido)'
    parameter_name = 'paciente_id'

    def lookups(self, request, model_admin):
        from admin_cadastros.models import Pessoa
        pacientes = (
            Pessoa.objects.filter(
                Q(relatorio__isnull=False) | Q(atendimento__relatorio__isnull=False)
            )
            .distinct()
            .order_by('nome')[:60]
        )
        return [(str(p.id), f"{p.nome} (CPF: {p.cpf})" if p.cpf else p.nome) for p in pacientes]

    def queryset(self, request, queryset):
        val = self.value()
        if not val:
            return queryset
        return queryset.filter(Q(pessoa_id=val) | Q(atendimento__pessoa_id=val))


class SituacaoAtendimentoFilter(admin.SimpleListFilter):
    title = 'Situação do Atendimento'
    parameter_name = 'situacao_atend'

    def lookups(self, request, model_admin):
        return (
            ('internado', 'Internados Atualmente (Sem Alta)'),
            ('alta', 'Com Alta Concedida'),
        )

    def queryset(self, request, queryset):
        val = self.value()
        if val == 'internado':
            return queryset.filter(atendimento__dt_alta__isnull=True)
        elif val == 'alta':
            return queryset.filter(atendimento__dt_alta__isnull=False)
        return queryset


class TipoEvolucaoRelatorioFilter(admin.SimpleListFilter):
    title = 'Subfiltro: Tipo de Evolução'
    parameter_name = 'sub_tipo_evolucao'

    def lookups(self, request, model_admin):
        # Lista os tipos de evolução existentes
        tipos = TipoEvolucao.objects.filter(status='A').values_list('id', 'tipo_evolucao').order_by('tipo_evolucao')
        return [(str(t_id), t_nome) for t_id, t_nome in tipos]

    def queryset(self, request, queryset):
        val = self.value()
        if not val:
            return queryset
        # Busca os IDs de Evolucao que possuem este tipo_evolucao
        evolucao_ct = ContentType.objects.get_for_model(Evolucao)
        evolucao_ids = Evolucao.objects.filter(tipo_evolucao_id=val).values_list('id', flat=True)
        return queryset.filter(content_type=evolucao_ct, object_id__in=evolucao_ids)


class TipoDocumentoLegalRelatorioFilter(admin.SimpleListFilter):
    title = 'Subfiltro: Termo/Doc. Legal por Tipo'
    parameter_name = 'sub_tipo_doc_legal'

    def lookups(self, request, model_admin):
        # Lista tipos de documentos legais e modelos
        tipos = TipoDocumentoLegal.objects.filter(status='A').values_list('id', 'nome').order_by('nome')
        return [(str(t_id), t_nome) for t_id, t_nome in tipos]

    def queryset(self, request, queryset):
        val = self.value()
        if not val:
            return queryset
        # Filtra relatórios cujo tipo seja documentos_legais/termo e correspondam aos documentos gerados deste tipo
        doc_ct = ContentType.objects.get_for_model(DocumentoLegalInternacao)
        doc_ids = DocumentoLegalInternacao.objects.filter(
            tipo_documento_id=val).values_list('id', flat=True)
        # O tipo gravado pelo gerador de documentos legais é 'documentos_legais'.
        return queryset.filter(content_type=doc_ct, object_id__in=doc_ids)


class ModuloProntuarioFilter(admin.SimpleListFilter):
    title = 'Módulo / Grupo Clínico'
    parameter_name = 'modulo_clinico'

    def lookups(self, request, model_admin):
        return (
            ('prontuario', 'Todos de Prontuário Clínico'),
            ('evolucao', 'Evoluções Clínicas'),
            ('documentos_legais', 'Termos e Documentos Legais'),
            ('prescricao', 'Prescrições Médicas'),
            ('adep', 'ADEP (Administrações)'),
            ('sinais_vitais', 'Sinais Vitais & Perdas/Ganhos'),
            ('sae', 'SAE (Enfermagem)'),
            ('diagnostico', 'Diagnósticos (CID)'),
            ('plano_cuidados', 'Plano de Cuidados'),
            ('documentos_legais', 'Termos e Documentos Legais'),
            ('administrativo', 'Atas, Ofícios e Orçamentos'),
        )

    def queryset(self, request, queryset):
        val = self.value()
        if not val:
            return queryset
        if val == 'prontuario':
            # Os tipos são gravados no modelo sem separador (ver os registros
            # existentes: 'sinaisvitais', 'perdasganhos', 'planocuidados').
            return queryset.filter(
                tipo__in=['evolucao', 'psicoterapia', 'prescricao', 'adep',
                          'sinaisvitais', 'sinais_vitais', 'perdasganhos',
                          'perdas_ganhos', 'sae', 'diagnostico', 'planocuidados',
                          'plano_cuidados']
            )
        elif val == 'evolucao':
            return queryset.filter(tipo__in=['evolucao', 'psicoterapia'])
        elif val == 'prescricao':
            return queryset.filter(tipo='prescricao')
        elif val == 'adep':
            return queryset.filter(tipo='adep')
        elif val == 'sinais_vitais':
            return queryset.filter(
                tipo__in=['sinaisvitais', 'sinais_vitais', 'perdasganhos',
                          'perdas_ganhos', 'sv'])
        elif val == 'sae':
            return queryset.filter(tipo='sae')
        elif val == 'diagnostico':
            return queryset.filter(tipo='diagnostico')
        elif val == 'plano_cuidados':
            return queryset.filter(tipo__in=['planocuidados', 'plano_cuidados'])
        elif val == 'documentos_legais':
            return queryset.filter(
                tipo__in=['documentos_legais', 'documentolegal', 'termo', 'termos'])
        elif val == 'administrativo':
            # Atas/Ofícios/Orçamentos são gravados no plural pelos respectivos apps.
            return queryset.filter(
                tipo__in=['ata', 'atas', 'oficio', 'oficios', 'orcamento', 'orcamentos'])
        return queryset


@admin.register(Relatorio)
class RelatorioAdmin(AdminDashboardAndTopFilterMixin, admin.ModelAdmin):
    dashboard_date_field = 'dt_registro'

    def get_dashboard_kpis(self, request, queryset):
        total_listagem = queryset.count()
        total_ativos = queryset.filter(status='A').count()
        total_inativos = queryset.filter(status='I').count()

        # PDFs de hoje
        hoje = timezone.now().date()
        total_hoje = queryset.filter(dt_registro__date=hoje).count()

        # Pacientes únicos na listagem
        pacientes_count = queryset.exclude(pessoa__isnull=True).values('pessoa_id').distinct().count()

        return [
            {
                'title': 'Total na Listagem',
                'value': f"{total_listagem:,}".replace(',', '.'),
                'subtitle': 'Registros correspondentes',
                'color_class': 'kpi-blue',
                'icon': '📑',
            },
            {
                'title': 'PDFs Ativos',
                'value': f"{total_ativos:,}".replace(',', '.'),
                'subtitle': 'Documentos vigentes',
                'color_class': 'kpi-green',
                'icon': '✅',
            },
            {
                'title': 'Gerados Hoje',
                'value': f"{total_hoje:,}".replace(',', '.'),
                'subtitle': f"Em {hoje.strftime('%d/%m/%Y')}",
                'color_class': 'kpi-orange',
                'icon': '📅',
            },
            {
                'title': 'Pacientes',
                'value': f"{pacientes_count:,}".replace(',', '.'),
                'subtitle': 'Pessoas identificadas',
                'color_class': 'kpi-purple',
                'icon': '👥',
            },
        ]

    def get_top_extra_filters(self, request):
        params = request.GET.copy()
        current_modulo = params.get('modulo_clinico', '')
        current_pdf_ativo = params.get('pdf_ativo', 'A')

        def build_extra_url(key, val):
            p = request.GET.copy()
            p.pop('p', None)
            if val is None or (key in p and p[key] == val):
                p.pop(key, None)
            else:
                p[key] = val
            qs_str = p.urlencode()
            return f"{request.path}?{qs_str}" if qs_str else request.path

        return [
            {
                'label': 'Apenas Ativos',
                'url': build_extra_url('pdf_ativo', 'A'),
                'active': current_pdf_ativo == 'A',
                'icon': '✅',
            },
            {
                'label': 'Todos de Prontuário',
                'url': build_extra_url('modulo_clinico', 'prontuario'),
                'active': current_modulo == 'prontuario',
                'icon': '📋',
            },
            {
                'label': 'Evoluções',
                'url': build_extra_url('modulo_clinico', 'evolucao'),
                'active': current_modulo == 'evolucao',
                'icon': '📝',
            },
            {
                'label': 'Prescrições & ADEP',
                'url': build_extra_url('modulo_clinico', 'prescricao'),
                'active': current_modulo == 'prescricao',
                'icon': '💊',
            },
            {
                'label': 'Termos Legais',
                'url': build_extra_url('modulo_clinico', 'documentos_legais'),
                'active': current_modulo == 'documentos_legais',
                'icon': '⚖️',
            },
            {
                'label': 'Internados',
                'url': build_extra_url('situacao_atend', 'internado'),
                'active': params.get('situacao_atend') == 'internado',
                'icon': '🛌',
            },
            {
                'label': 'Com Alta',
                'url': build_extra_url('situacao_atend', 'alta'),
                'active': params.get('situacao_atend') == 'alta',
                'icon': '🏁',
            },
        ]

    def get_top_dropdown_subfilters(self, request):
        params = request.GET.copy()
        current_paciente = params.get('paciente_id', '')
        current_ev = params.get('sub_tipo_evolucao', '')
        current_doc = params.get('sub_tipo_doc_legal', '')

        def build_sub_url(param_name, val):
            p = request.GET.copy()
            p.pop('p', None)
            if not val:
                p.pop(param_name, None)
            else:
                p[param_name] = str(val)
            qs_str = p.urlencode()
            return f"{request.path}?{qs_str}" if qs_str else request.path

        # Opções de pacientes com relatórios
        from admin_cadastros.models import Pessoa
        pacientes = (
            Pessoa.objects.filter(
                Q(relatorio__isnull=False) | Q(atendimento__relatorio__isnull=False)
            )
            .distinct()
            .order_by('nome')[:60]
        )
        pac_options = [{'label': 'Todos os Pacientes', 'url': build_sub_url('paciente_id', ''), 'selected': not current_paciente}]
        for p in pacientes:
            cpf_txt = f" - CPF: {p.cpf}" if p.cpf else ""
            pac_options.append({
                'label': f"👤 {p.nome}{cpf_txt}",
                'url': build_sub_url('paciente_id', p.id),
                'selected': current_paciente == str(p.id),
            })

        # Opções de tipo de evolução
        tipos_ev = TipoEvolucao.objects.filter(status='A').values_list('id', 'tipo_evolucao').order_by('tipo_evolucao')
        ev_options = [{'label': 'Todas as Evoluções', 'url': build_sub_url('sub_tipo_evolucao', ''), 'selected': not current_ev}]
        for t_id, t_nome in tipos_ev:
            ev_options.append({
                'label': f"Evolução: {t_nome}",
                'url': build_sub_url('sub_tipo_evolucao', t_id),
                'selected': current_ev == str(t_id),
            })

        # Opções de tipo de termo / documento legal
        tipos_doc = TipoDocumentoLegal.objects.filter(status='A').values_list('id', 'nome').order_by('nome')
        doc_options = [{'label': 'Todos os Termos / Docs Legais', 'url': build_sub_url('sub_tipo_doc_legal', ''), 'selected': not current_doc}]
        for d_id, d_nome in tipos_doc:
            doc_options.append({
                'label': f"Termo: {d_nome}",
                'url': build_sub_url('sub_tipo_doc_legal', d_id),
                'selected': current_doc == str(d_id),
            })

        return [
            {
                'label': 'Filtrar por Paciente',
                'options': pac_options,
            },
            {
                'label': 'Subfiltro Evolução',
                'options': ev_options,
            },
            {
                'label': 'Subfiltro Termos Legais',
                'options': doc_options,
            },
        ]

    list_display = (
        'id', 'tipo_badge', 'paciente_info', 'atendimento_link',
        'link_pdf', 'dt_registro', 'us_registro', 'status_badge'
    )
    list_display_links = ('id', 'tipo_badge')
    list_filter = (
        PDFAtivoFilter,
        ModuloProntuarioFilter,
        PacienteRelatorioFilter,
        SituacaoAtendimentoFilter,
        TipoEvolucaoRelatorioFilter,
        TipoDocumentoLegalRelatorioFilter,
        'tipo',
        'dt_registro',
        'us_registro',
    )
    search_fields = (
        'id', 'tipo', 'relatorio', 'atendimento__id',
        'pessoa__nome', 'pessoa__cpf',
        'atendimento__pessoa__nome', 'atendimento__pessoa__cpf',
    )
    autocomplete_fields = ('pessoa', 'atendimento')
    readonly_fields = ('dt_registro', 'us_registro')
    date_hierarchy = 'dt_registro'
    list_select_related = ('pessoa', 'atendimento', 'atendimento__pessoa', 'us_registro')
    ordering = ('-dt_registro', '-id')

    actions = [
        'action_baixar_dossie_paciente_zip',
        'action_baixar_selecionados_zip',
        'action_exportar_xlsx',
        'action_ativar',
        'action_inativar',
    ]

    def get_actions(self, request):
        actions = super().get_actions(request)
        # Opções de ativar e inativar relatórios somente para usuários administradores (superuser)
        if not request.user.is_superuser:
            actions.pop('action_ativar', None)
            actions.pop('action_inativar', None)
        return actions

    def tipo_badge(self, obj):
        tipo_str = (obj.tipo or '').lower()
        nome = TIPO_LABELS.get(tipo_str, obj.tipo or 'Outro')
        cores = {
            'evolucao': '#17a2b8',
            'prescricao': '#6f42c1',
            'adep': '#5a32a3',
            'sinais_vitais': '#e83e8c',
            'perdas_ganhos': '#d63384',
            'sae': '#20c997',
            'diagnostico': '#0d6efd',
            'plano_cuidados': '#0dcaf0',
            'documentos_legais': '#fd7e14',
            'ata': '#6c757d',
            'oficio': '#495057',
            'orcamento': '#198754',
        }
        bg = cores.get(tipo_str, '#0d6efd')
        return format_html(
            '<span style="background-color: {}; color: #fff; padding: 2px 7px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; white-space: nowrap;">{}</span>',
            bg, nome
        )
    tipo_badge.short_description = 'Módulo / Tipo'
    tipo_badge.admin_order_field = 'tipo'

    def paciente_info(self, obj):
        p = obj.pessoa or (obj.atendimento.pessoa if obj.atendimento else None)
        if not p:
            return format_html('<span style="color: #999;">-</span>')
        cpf_str = f" <small style='color: #666;'>({p.cpf})</small>" if getattr(p, 'cpf', None) else ""
        url = reverse('admin:admin_cadastros_pessoa_change', args=[p.id])
        return format_html('<a href="{}" style="font-weight: 600; text-decoration: none;">{}</a>{}', url, p.nome, format_html(cpf_str))
    paciente_info.short_description = 'Paciente'
    paciente_info.admin_order_field = 'pessoa__nome'

    def atendimento_link(self, obj):
        if not obj.atendimento_id:
            return format_html('<span style="color: #999;">-</span>')
        url = reverse('admin:atendimentos_atendimento_change', args=[obj.atendimento_id])
        dt_str = obj.atendimento.dt_atendimento.strftime('%d/%m/%Y') if obj.atendimento.dt_atendimento else ''
        return format_html('<a href="{}" style="text-decoration: none;">#{} <small style="color: #666;">({})</small></a>', url, obj.atendimento_id, dt_str)
    atendimento_link.short_description = 'Atendimento'
    atendimento_link.admin_order_field = 'atendimento__id'

    def link_pdf(self, obj):
        if obj.relatorio and obj.relatorio.name:
            nome_arquivo = obj.relatorio.name.rsplit('/', 1)[-1]
            return format_html(
                '<a href="{}" target="_blank" title="Abrir PDF em nova aba" style="display: inline-flex; align-items: center; gap: 4px; text-decoration: none; font-weight: 500; color: #0d6efd;">'
                '<span style="font-size: 1.05rem;">📄</span> '
                '<span style="text-decoration: underline;">{}</span>'
                '</a>',
                obj.relatorio.url, nome_arquivo
            )
        return format_html('<span style="color: #dc3545;">Sem arquivo</span>')
    link_pdf.short_description = 'Arquivo PDF'

    def status_badge(self, obj):
        if obj.status == 'A':
            return format_html('<span style="background-color: #28a745; color: #fff; padding: 2px 6px; border-radius: 3px; font-size: 0.7rem; font-weight: bold;">Ativo</span>')
        return format_html('<span style="background-color: #dc3545; color: #fff; padding: 2px 6px; border-radius: 3px; font-size: 0.7rem; font-weight: bold;">Inativo</span>')
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    @admin.action(description="📦 Baixar Dossiê Completo do Paciente em ZIP (Prontuário + Termos Legais)")
    def action_baixar_dossie_paciente_zip(self, request, queryset):
        zip_bytes, nome_zip, total = gerar_zip_dossie_pacientes(queryset, user=request.user)
        if not zip_bytes or total == 0:
            self.message_user(
                request,
                "Nenhum arquivo PDF ativo foi encontrado para o(s) paciente(s) dos registros selecionados.",
                level=messages.WARNING
            )
            return None

        response = HttpResponse(zip_bytes, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{nome_zip}"'
        return response

    @admin.action(description="🗂 Baixar Selecionados em ZIP (Filtros Aplicados)")
    def action_baixar_selecionados_zip(self, request, queryset):
        zip_bytes, nome_zip, total = gerar_zip_relatorios_selecionados(queryset, user=request.user)
        if not zip_bytes or total == 0:
            self.message_user(
                request,
                "Nenhum arquivo PDF válido encontrado entre os relatórios selecionados.",
                level=messages.WARNING
            )
            return None

        response = HttpResponse(zip_bytes, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{nome_zip}"'
        return response

    @admin.action(description="📊 Exportar Selecionados para Excel (XLSX Formatado)")
    def action_exportar_xlsx(self, request, queryset):
        xlsx_bytes, nome_xlsx = exportar_relatorios_xlsx(queryset, user=request.user)
        response = HttpResponse(
            xlsx_bytes,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{nome_xlsx}"'
        return response

    @admin.action(description="⛔ Inativar PDFs Selecionados (Apenas Admin)")
    def action_inativar(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "Apenas administradores do sistema podem inativar relatórios.", level=messages.ERROR)
            return None
        atualizados = queryset.update(status='I')
        self.message_user(request, f"{atualizados} relatório(s) marcado(s) como inativo(s).", level=messages.SUCCESS)

    @admin.action(description="✅ Ativar PDFs Selecionados (Apenas Admin)")
    def action_ativar(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "Apenas administradores do sistema podem ativar relatórios.", level=messages.ERROR)
            return None
        atualizados = queryset.update(status='A')
        self.message_user(request, f"{atualizados} relatório(s) marcado(s) como ativo(s).", level=messages.SUCCESS)

    def save_model(self, request, obj, form, change):
        if not obj.us_registro_id:
            obj.us_registro = request.user
        if not obj.dt_registro:
            obj.dt_registro = timezone.now()
        super().save_model(request, obj, form, change)


admin.site.register(TextoDocumentoPadrao, TextoDocumentoPadraoAdmin)
