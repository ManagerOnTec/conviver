"""Admin da TESOURARIA: caixas, competências e movimentos de caixa."""
from decimal import Decimal

from django.contrib import admin, messages
from django.urls import reverse, path
from django.utils import timezone
from django.utils.html import format_html
from django.shortcuts import redirect, render

from admin_cadastros_financeiros.models import TransacaoFinanceira
from admin_financeiro.models import CompetenciaBancaria
from dominios.utils import (AdminEstabelecimentoPadraoMixin,
                            ExportToXLSMixin, StatusFilterAdminMixin,
                            chain_form_init)
from admin_cadastros.utils import EstabelecimentoFilterAdminMixin

from .models import (ControleCaixa, CompetenciaCaixa, MovimentoCaixa,
                     ConferenciaCaixa)
from .forms import MovimentoCaixaForm
from .dashboard import TesourariaDashboardMixin, _money, _qtd


@admin.register(ControleCaixa)
class ControleCaixaAdmin(AdminEstabelecimentoPadraoMixin, ExportToXLSMixin,
                         TesourariaDashboardMixin, admin.ModelAdmin):
    list_display = ['descricao', 'usuario', 'estabelecimento',
                    'competencia_aberta', 'status']
    list_filter = [StatusFilterAdminMixin, EstabelecimentoFilterAdminMixin]
    search_fields = ['descricao', 'usuario__username', 'usuario__first_name']
    readonly_fields = ['dt_registro', 'us_registro', 'dt_atualizacao',
                       'us_atualizacao']
    # KPIs/filtro do topo (padrão das telas financeiras).
    dashboard_competencia_field = 'dt_registro'
    dashboard_vencimento_field = 'dt_registro'

    def get_dashboard_kpis(self, request, queryset):
        from django.db.models import Count, Q
        metricas = queryset.aggregate(
            total=Count('pk', distinct=True),
            ativos=Count('pk', filter=Q(status='A'), distinct=True),
            inativos=Count('pk', filter=Q(status='I'), distinct=True),
            estabelecimentos=Count('estabelecimento_id', distinct=True),
        )
        return [
            {'title': 'Caixas', 'value': _qtd(metricas['total']),
             'subtitle': 'No filtro atual', 'color_class': 'kpi-blue',
             'icon': 'fa-cash-register'},
            {'title': 'Ativos', 'value': _qtd(metricas['ativos']),
             'subtitle': 'Caixas ativos', 'color_class': 'kpi-green',
             'icon': 'fa-circle-check'},
            {'title': 'Inativos', 'value': _qtd(metricas['inativos']),
             'subtitle': 'Caixas inativos', 'color_class': 'kpi-red',
             'icon': 'fa-ban'},
            {'title': 'Estabelecimentos',
             'value': _qtd(metricas['estabelecimentos']),
             'subtitle': 'No filtro atual', 'color_class': 'kpi-purple',
             'icon': 'fa-house'},
        ]

    def competencia_aberta(self, obj):
        comp = obj.competencias.filter(dt_fechamento__isnull=True).first()
        if comp is None:
            return '—'
        return format_html('<strong>{}</strong> (saldo R$ {})',
                           comp.descricao, comp.saldo_atual)
    competencia_aberta.short_description = 'Competência Aberta'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(CompetenciaCaixa)
class CompetenciaCaixaAdmin(AdminEstabelecimentoPadraoMixin,
                            ExportToXLSMixin, TesourariaDashboardMixin,
                            admin.ModelAdmin):
    list_display = ['descricao', 'controle_caixa', 'dt_abertura',
                    'dt_fechamento', 'saldo_inicial', 'saldo_anterior',
                    'saldo_atual', 'total_movimentos', 'fechar_link']
    list_filter = ['controle_caixa', StatusFilterAdminMixin,
                   EstabelecimentoFilterAdminMixin]
    readonly_fields = ['saldo_atual', 'dt_registro', 'us_registro',
                       'dt_atualizacao', 'us_atualizacao']
    actions = ['fechar_competencias']
    # KPIs/filtro do topo: presets por MÊS DE ABERTURA.
    dashboard_competencia_field = 'dt_abertura'
    dashboard_vencimento_field = 'dt_fechamento'

    def get_dashboard_kpis(self, request, queryset):
        from django.db.models import Count, Q, Sum
        metricas = queryset.aggregate(
            total=Count('pk', distinct=True),
            abertas=Count('pk', filter=Q(dt_fechamento__isnull=True),
                          distinct=True),
            fechadas=Count('pk', filter=Q(dt_fechamento__isnull=False),
                           distinct=True),
            saldo_atual=Sum('saldo_atual'),
        )
        return [
            {'title': 'Competências', 'value': _qtd(metricas['total']),
             'subtitle': 'No filtro atual', 'color_class': 'kpi-blue',
             'icon': 'fa-calendar-days'},
            {'title': 'Abertas', 'value': _qtd(metricas['abertas']),
             'subtitle': 'Competências em andamento',
             'color_class': 'kpi-green', 'icon': 'fa-circle-check'},
            {'title': 'Fechadas', 'value': _qtd(metricas['fechadas']),
             'subtitle': 'Competências encerradas', 'color_class': 'kpi-red',
             'icon': 'fa-lock'},
            {'title': 'Saldo atual', 'value': _money(metricas['saldo_atual']),
             'subtitle': 'Soma no filtro atual', 'color_class': 'kpi-purple',
             'icon': 'fa-money-bill-wave'},
        ]

    def total_movimentos(self, obj):
        return obj.movimentocaixa_set.count()
    total_movimentos.short_description = 'Movimentos'

    def fechar_link(self, obj):
        if obj.dt_fechamento:
            return format_html(
                '<span style="color:#15803d;font-weight:600">✓ Fechada em '
                '{}</span>', obj.dt_fechamento.strftime('%d/%m/%Y'))
        url = reverse('admin:admin_tesouraria_competenciacaixa_change',
                      args=[obj.pk])
        return format_html(
            '<a class="button" style="padding:3px 10px;background:#b91c1c" '
            'href="{}?fechar=1">Fechar caixa</a>', url)
    fechar_link.short_description = 'Fechamento'

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        def form_init(form_instance, *a, **kw):
            # Saldo anterior herdado da última competência fechada do caixa.
            if not form_instance.is_bound and obj is None:
                caixa = form_instance.initial.get('controle_caixa') or \
                    getattr(form_instance.instance, 'controle_caixa', None)
                if caixa is not None:
                    anterior = CompetenciaCaixa.objects.filter(
                        controle_caixa=caixa,
                        dt_fechamento__isnull=False,
                    ).order_by('-dt_fechamento').first()
                    if anterior is not None:
                        form_instance.initial['saldo_anterior'] = \
                            anterior.saldo_atual
                        form_instance.initial['saldo_inicial'] = \
                            anterior.saldo_atual
            if obj is not None and request.GET.get('fechar') == '1':
                hoje = timezone.localdate()
                form_instance.initial['dt_fechamento'] = hoje
                messages.info(
                    request,
                    'Data de fechamento preenchida com HOJE '
                    f'({hoje:%d/%m/%Y}). Confira/ajuste a data CORRETA. A '
                    'CONFERÊNCIA de caixa precisa estar finalizada.')

        chain_form_init(form, form_init)
        return form

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()
        # Saldo anterior herdado quando não informado.
        if not obj.saldo_anterior:
            obj.anexar_saldo_anterior()
        super().save_model(request, obj, form, change)
        obj.recalcular_saldos()

    @admin.action(description='Fechar caixa (exige conferência finalizada)')
    def fechar_competencias(self, request, queryset):
        fechadas, problemas = [], []
        for comp in queryset:
            if comp.dt_fechamento:
                problemas.append(f'{comp}: já fechada.')
                continue
            try:
                comp.fechar(request.user)
                fechadas.append(str(comp))
            except ValueError as erro:
                problemas.append(f'{comp}: {erro}')
        if fechadas:
            messages.success(request,
                             'Caixa(s) fechado(s): ' + '; '.join(fechadas))
        for problema in problemas:
            messages.warning(request, problema)


@admin.register(MovimentoCaixa)
class MovimentoCaixaAdmin(AdminEstabelecimentoPadraoMixin, ExportToXLSMixin,
                          TesourariaDashboardMixin, admin.ModelAdmin):
    form = MovimentoCaixaForm
    list_display = ['dt_movimento', 'competencia_caixa', 'tipo', 'origem',
                    'valor_entrada', 'valor_saida', 'transacao_financeira',
                    'competencia_bancaria', 'fatura_recebida', 'observacao']
    list_filter = ['competencia_caixa', 'origem', 'tipo',
                   'competencia_bancaria', 'transacao_financeira',
                   StatusFilterAdminMixin, EstabelecimentoFilterAdminMixin]
    search_fields = ['observacao', 'documento', 'competencia_caixa__descricao',
                     'competencia_caixa__controle_caixa__descricao']
    readonly_fields = ['transferencia_id', 'dt_registro', 'us_registro',
                       'dt_atualizacao', 'us_atualizacao', 'estabelecimento']
    date_hierarchy = 'dt_movimento'
    # KPIs/filtro do topo (padrão do MovimentoBancario do financeiro).
    dashboard_competencia_field = 'dt_movimento'
    dashboard_vencimento_field = 'dt_movimento'
    dashboard_valor_field = 'valor_entrada'
    dashboard_saldo_field = None

    # O recorte dos campos (competências de caixa abertas, transações de caixa/
    # depósito/saque, competências bancárias abertas) é feito no
    # `MovimentoCaixaForm.__init__`. Não repetir aqui: um recorte no
    # `get_form` sobrescrevia o do form e tirava DEPÓSITO/SAQUE da lista.

    def fatura_recebida(self, obj):
        """Fatura baixada por este movimento (recebimento em dinheiro)."""
        if not obj.baixa_fatura_id:
            return '—'
        fatura = obj.baixa_fatura.fatura_baixada_do_bd()
        if fatura is None:
            return '—'
        return format_html(
            '<a href="{}" title="Saldo R$ {}">Fatura {} — R$ {}</a>',
            reverse('admin:admin_faturas_fatura_change', args=[fatura.pk]),
            fatura.valor_saldo or 0, fatura.pk, fatura.valor_fatura or 0)
    fatura_recebida.short_description = 'Fatura recebida'

    def get_dashboard_kpis(self, request, queryset):
        """KPIs do movimento de caixa (espelho do MovimentoBancario):
        ENTRADAS, SAÍDAS, RESULTADO e quantidade — sempre sobre o queryset
        já filtrado (caixa, origem, período, datas)."""
        from django.db.models import Sum, Count
        somas = queryset.aggregate(
            entradas=Sum('valor_entrada'),
            saidas=Sum('valor_saida'),
            qtde=Count('pk'))
        entradas = somas['entradas'] or Decimal('0')
        saidas = somas['saidas'] or Decimal('0')
        qtde = somas['qtde'] or 0
        com_baixa = queryset.exclude(baixa_fatura=None).count()
        return [
            {'title': 'Entradas', 'value': _money(entradas),
             'subtitle': 'Soma dos créditos no filtro',
             'color_class': 'kpi-green', 'icon': 'fa-arrow-down'},
            {'title': 'Saídas', 'value': _money(saidas),
             'subtitle': 'Soma dos débitos no filtro',
             'color_class': 'kpi-red', 'icon': 'fa-arrow-up'},
            {'title': 'Resultado (E − S)',
             'value': _money(entradas - saidas),
             'subtitle': 'Entradas menos saídas',
             'color_class': 'kpi-blue', 'icon': 'fa-scale-balanced'},
            {'title': 'Lançamentos', 'value': _qtd(qtde),
             'subtitle': f'{_qtd(com_baixa)} com baixa de fatura',
             'color_class': 'kpi-purple', 'icon': 'fa-list'},
        ]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()
        try:
            super().save_model(request, obj, form, change)
        except Exception as erro:
            messages.error(request, f'Não foi possível salvar: {erro}')
            raise


@admin.register(ConferenciaCaixa)
class ConferenciaCaixaAdmin(TesourariaDashboardMixin, admin.ModelAdmin):
    list_display = ['competencia_caixa', 'valor_sistema', 'valor_contado',
                    'diferenca', 'finalizada', 'dt_conferencia']
    list_filter = ['finalizada']
    readonly_fields = ['valor_sistema', 'diferenca', 'dt_conferencia',
                       'us_registro']
    # KPIs/filtro do topo.
    dashboard_competencia_field = 'dt_conferencia'
    dashboard_vencimento_field = 'dt_conferencia'

    def get_dashboard_kpis(self, request, queryset):
        from django.db.models import Count, Q, Sum
        metricas = queryset.aggregate(
            total=Count('pk', distinct=True),
            finalizadas=Count('pk', filter=Q(finalizada=True),
                              distinct=True),
            em_andamento=Count('pk', filter=Q(finalizada=False),
                               distinct=True),
            soma_sistema=Sum('valor_sistema'),
            soma_contado=Sum('valor_contado'),
        )
        sistema = metricas['soma_sistema'] or Decimal('0')
        contado = metricas['soma_contado'] or Decimal('0')
        return [
            {'title': 'Conferências', 'value': _qtd(metricas['total']),
             'subtitle': 'No filtro atual', 'color_class': 'kpi-blue',
             'icon': 'fa-clipboard-check'},
            {'title': 'Finalizadas', 'value': _qtd(metricas['finalizadas']),
             'subtitle': 'Prontas para fechar o caixa',
             'color_class': 'kpi-green', 'icon': 'fa-circle-check'},
            {'title': 'Em andamento', 'value': _qtd(metricas['em_andamento']),
             'subtitle': 'Aguardando contagem',
             'color_class': 'kpi-orange', 'icon': 'fa-hourglass-half'},
            {'title': 'Diferença (contado − sistema)',
             'value': _money(contado - sistema),
             'subtitle': 'Sobra (+) / quebra (−) somada',
             'color_class': 'kpi-purple', 'icon': 'fa-scale-balanced'},
        ]
