"""Admins de CONTAS A PAGAR (fluxo de SAÍDA).

Espelha o fluxo de ENTRADA (`admin_faturas`):

    AcordoPagamento → PrePagamento → Pagamento → BaixaPagamento → Movimento

Regras (ver `instrucoes_pagamentos.md` e `admin_financeiro/instrucoes_financeiro.md`):

- cada etapa só muda enquanto NENHUMA etapa à frente estiver travada;
- a COMPETÊNCIA (bancária ou de caixa) FECHADA trava tudo;
- pagamento FINALIZADO não edita nem exclui — só o botão “Reabrir”;
- baixa e movimento saem juntos (concomitantes), devolvendo o saldo.
"""
from datetime import date
from decimal import Decimal

from django.contrib import admin, messages
from django.db import models, transaction
from django.db.models import Sum
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _

from admin_cadastros.utils import EstabelecimentoFilterAdminMixin
from admin_cadastros_financeiros.models import TransacaoFinanceira
from admin_financeiro.models import CompetenciaBancaria
from dominios.utils import (
    AdminEstabelecimentoPadraoMixin, AdminSaveModelAuditMixin,
    BotaoExcluirLinhaMixin, EdicaoComRegrasMixin,
    ExclusaoEmLoteComRegrasMixin, ExportToXLSMixin, StatusFilterAdminMixin,
)

from .dashboard import FornecedorPagadorFilter, PagamentosDashboardMixin, \
    _money, _qtd

from .forms import (
    BaixaPagamentoForm, ClassificacaoFornecedorForm,
    ClassePagamentoForm, FornecedorForm,
)
from .models import (
    AcordoPagamento, BaixaPagamento, ClassificacaoFornecedor,
    ClassePagamento, Fornecedor, Pagamento, PrePagamento,
)


# ----------------------------------------------------------------------
# Cadastros auxiliares
# ----------------------------------------------------------------------
class ClassificacaoFornecedorAdmin(PagamentosDashboardMixin, ExportToXLSMixin,
                                   admin.ModelAdmin):
    """Cadastro simples: herda só o TOPO (barra de busca, atalhos de status e
    indicadores) do `PagamentosDashboardMixin`, para ter o mesmo padrão das
    telas do fluxo.
    """
    form = ClassificacaoFornecedorForm
    actions = ['export_as_xls']
    dashboard_valor_field = 'descricao'
    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']
    list_display = ['descricao', 'observacao',
                    'us_registro', 'dt_registro', 'status']
    list_editable = ['status', 'observacao']
    list_filter = [StatusFilterAdminMixin]
    search_fields = ['descricao', 'observacao']
    list_per_page = 99

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()
        super().save_model(request, obj, form, change)


admin.site.register(ClassificacaoFornecedor, ClassificacaoFornecedorAdmin)


class ClassePagamentoAdmin(PagamentosDashboardMixin, ExportToXLSMixin,
                           admin.ModelAdmin):
    """Cadastro simples: mesmo topo (busca/status/indicadores) das telas do
    fluxo.
    """
    form = ClassePagamentoForm
    actions = ['export_as_xls']
    dashboard_valor_field = 'descricao'
    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']
    list_display = ['descricao', 'observacao',
                    'us_registro', 'dt_registro', 'status']
    list_editable = ['status', 'observacao']
    list_filter = [StatusFilterAdminMixin]
    search_fields = ['descricao', 'observacao']
    list_per_page = 99

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()
        super().save_model(request, obj, form, change)


admin.site.register(ClassePagamento, ClassePagamentoAdmin)


class FornecedorAdmin(PagamentosDashboardMixin, ExportToXLSMixin,
                      admin.ModelAdmin):
    """Cadastro de fornecedores: topo com busca, atalhos de status e os
    seletores de CLASSE DO FORNECEDOR e ESTABELECIMENTO (conforme o modelo
    tiver o campo).
    """
    form = FornecedorForm
    actions = ['export_as_xls']
    dashboard_valor_field = 'descricao'
    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']
    list_display = ['id', 'descricao', 'empresa',
                    'pessoa', 'classificacao', 'observacao', 'dt_registro',
                    'status']
    list_filter = ['empresa', 'pessoa', StatusFilterAdminMixin]
    search_fields = ['descricao', 'observacao']
    list_display_links = ['id', 'descricao']
    list_editable = ['observacao', 'status']
    list_per_page = 99

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()
        super().save_model(request, obj, form, change)


admin.site.register(Fornecedor, FornecedorAdmin)


# ----------------------------------------------------------------------
# 4. ACORDO DE PAGAMENTO (espelho de AcordoFaturamento)
# ----------------------------------------------------------------------
class AcordoPagamentoAdmin(
        PagamentosDashboardMixin, BotaoExcluirLinhaMixin,
        EdicaoComRegrasMixin, ExclusaoEmLoteComRegrasMixin,
        AdminEstabelecimentoPadraoMixin,
        ExportToXLSMixin, admin.ModelAdmin):
    """Acordo de pagamento.

    O modelo TEM o campo `estabelecimento` (FK preenchida com o padrão da
    sessão/perfil) → segue o padrão do resto do fluxo:
    `AdminEstabelecimentoPadraoMixin` fixa o campo no formulário e
    `EstabelecimentoFilterAdminMixin` recorta a listagem.
    """

    # INDICADORES / FILTROS (espelho do fluxo de faturas).
    dashboard_competencia_field = 'data_inicio'
    dashboard_vencimento_field = 'data_fim'
    dashboard_valor_field = 'valor_previsto'

    def get_dashboard_kpis(self, request, queryset):
        hoje = timezone.localdate()
        ativos = queryset.filter(status='A')
        em_vigor = ativos.filter(
            data_inicio__lte=hoje).filter(
            models.Q(data_fim__isnull=True) | models.Q(data_fim__gte=hoje))
        pre_pagos = queryset.filter(pre_pago=True).count()
        total = queryset.aggregate(t=Sum('valor_previsto'))['t'] or 0
        return [
            {'title': 'Acordos', 'value': _qtd(queryset.count()),
             'subtitle': f'{_qtd(ativos.count())} ativos',
             'color_class': 'kpi-blue', 'icon': 'fa-file-invoice'},
            {'title': 'Em Vigor', 'value': _qtd(em_vigor.count()),
             'subtitle': 'Vigência na data de hoje',
             'color_class': 'kpi-green', 'icon': 'fa-calendar-days'},
            {'title': 'Valor Previsto', 'value': _money(total),
             'subtitle': 'Soma do valor previsto',
             'color_class': 'kpi-teal', 'icon': 'fa-money-bill-wave'},
            {'title': 'Pré-Pagos', 'value': _qtd(pre_pagos),
             'subtitle': f'{_qtd(queryset.filter(pre_pago=False).count())} sem previsão',
             'color_class': 'kpi-orange', 'icon': 'fa-receipt'},
        ]

    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']
    actions = ['export_as_xls', 'gerar_previsoes_em_lote',
               'excluir_selecionados']

    list_display = ['id', 'gerar_previsoes_button', 'duplicate_button',
                    'excluir_linha', 'fornecedor', 'fornecedor_classificacao', 'classe_pagamento',
                    'valor_previsto', 'tx_retencao', 'vl_retencao',
                    'recorrencia', 'data_inicio',
                    'data_fim', 'estabelecimento', 'pre_pago', 'status']
    list_display_links = ['id', 'fornecedor']
    # EDIÇÃO EM LINHA (a mesma regra da tela): acordo que JÁ gerou previsão
    # não edita nenhuma coluna.
    list_editable_sempre = ['valor_previsto', 'tx_retencao', 'vl_retencao',
                            'recorrencia', 'status']
    list_editable = list_editable_sempre

    def fornecedor_classificacao(self, obj):
        return obj.fornecedor.classificacao
    fornecedor_classificacao.short_description = "Classe Fornecedor"


    def get_changelist(self, request, **kwargs):
        """Listagem EDITÁVEL com o CADEADO nas linhas travadas.

        Sem este `get_changelist` o Django usa a tabela padrão e as colunas
        de `list_editable` aparecem editáveis mesmo quando a linha está
        travada pelo fluxo. O `ChangeListEditavel` lê
        `get_linhas_nao_editaveis` e renderiza essas colunas como TEXTO
        (com o aviso no `title`) — mesmo comportamento das faturas.
        """
        from admin_faturas.changelist_editavel import ChangeListEditavel
        return ChangeListEditavel

    def list_editable_permitido(self, request):
        """Acordo COM previsão gerada não tem edição em linha.

        Espelho do `AcordoFaturamentoAdmin`: uma vez que gerou previsão, o
        acordo é somente leitura (`motivo_recusa_edicao`).
        """
        if request.GET.get('pre_pago__exact') == '1':
            # Recorte “Pré-Pagos”: nenhuma linha editável.
            return []
        return list(self.list_editable_sempre)

    def get_linhas_nao_editaveis(self, request):
        """Pks dos acordos que JÁ geraram previsão: só texto na listagem."""
        try:
            return {str(pk) for pk in PrePagamento.objects.values_list(
                'acordo_pagamento_id', flat=True).distinct()}
        except Exception:
            return set()
    list_editable_sempre = ['status']
    list_editable = list_editable_sempre
    # O `AcordoPagamento` TEM o campo `estabelecimento` (FK preenchida com o
    # padrão da sessão/perfil), então entra o filtro padrão do projeto.
    list_filter = [FornecedorPagadorFilter, StatusFilterAdminMixin,
                   EstabelecimentoFilterAdminMixin,
                   'fornecedor', 'recorrencia', 'pre_pago']
    list_per_page = 99

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('gerar-previsoes/<int:acordo_id>/',
                 self.admin_site.admin_view(self.gerar_previsoes_view),
                 name='admin_pagamentos_acordopagamento_gerar_previsoes'),
            path('duplicar/<int:acordo_id>/',
                 self.admin_site.admin_view(self.duplicar_view),
                 name='admin_pagamentos_acordopagamento_duplicar'),
        ]
        return custom + urls

    # ------------------------------------------------------------------
    # DUPLICAR (espelho do “Duplicar” do AcordoFaturamento)
    # ------------------------------------------------------------------
    def duplicate_button(self, obj):
        """Cópia do acordo para uma nova DESPESA.

        Só aparece depois que as previsões foram geradas (mesma régua do
        fluxo de entradas): o acordo “fonte” já está completo.
        """
        if obj.pre_pago:
            return format_html(
                '<a class="button" href="{}">Duplicar</a>',
                reverse('admin:admin_pagamentos_acordopagamento_duplicar',
                        args=[obj.pk]))
        return format_html('<span style="color:gray;">Duplicar</span>')
    duplicate_button.short_description = 'Duplicar'
    duplicate_button.allow_tags = True

    def duplicar_view(self, request, acordo_id):
        """Duplica o acordo: cria uma NOVA despesa (cópia do contrato).

        O original fica INATIVO (`status='I'`) e a cópia nasce ATIVA e sem
        previsões geradas (`pre_pago=False`), pronta para receber o botão
        “Gerar previsões”. Mesma regra do duplicar de acordos de faturamento.
        """
        original = get_object_or_404(AcordoPagamento, pk=acordo_id)
        novo = AcordoPagamento.objects.get(pk=original.pk)
        novo.pk = None
        novo.pre_pago = False
        novo.status = 'A'
        novo.us_registro = request.user
        novo.dt_registro = timezone.now()
        novo.us_atualizacao = None
        novo.dt_atualizacao = None
        novo.save()
        original.status = 'I'
        original.us_atualizacao = request.user
        original.dt_atualizacao = timezone.now()
        original.save(update_fields=[
            'status', 'us_atualizacao', 'dt_atualizacao'])

        messages.success(
            request,
            f'Acordo de pagamento duplicado: novo acordo {novo.pk} (o '
            f'original {original.pk} foi inativado).')
        opts = self.model._meta
        return redirect(
            f'admin:{opts.app_label}_{opts.model_name}_change', novo.pk)

    def gerar_previsoes_button(self, obj):
        if obj.pre_pago:
            return format_html(
                '<span title="Previsões já geradas" style="color:#198754;'
                'font-weight:bold;">&#10003; Previsões</span>')
        url = reverse(
            'admin:admin_pagamentos_acordopagamento_gerar_previsoes',
            args=[obj.pk])
        return format_html(
            '<a class="button" href="{}">Gerar previsões</a>', url)
    gerar_previsoes_button.short_description = 'Previsões'

    def gerar_previsoes_view(self, request, acordo_id):
        acordo = get_object_or_404(AcordoPagamento, pk=acordo_id)
        motivo = acordo.motivo_recusa_edicao()
        if acordo.pre_pago:
            messages.warning(
                request,
                f'O acordo {acordo.pk} já gerou as previsões. Exclua a '
                'PREVISÃO, em “5. Pré-Pagamentos”, para gerar de novo.')
        else:
            try:
                with transaction.atomic():
                    criadas = acordo.gerar_previsoes()
                messages.success(
                    request,
                    f'{criadas} previsão(ões) gerada(s) para o acordo '
                    f'{acordo.pk}.')
            except Exception as erro:
                messages.error(
                    request,
                    f'Não foi possível gerar as previsões do acordo '
                    f'{acordo.pk}: {erro}')
        return redirect('admin:admin_pagamentos_acordopagamento_changelist')

    @admin.action(description='Gerar previsões dos acordos selecionados')
    def gerar_previsoes_em_lote(self, request, queryset):
        gerados = 0
        ignorados = 0
        erros = 0
        for acordo in queryset:
            if acordo.pre_pago:
                ignorados += 1
                continue
            try:
                with transaction.atomic():
                    acordo.gerar_previsoes()
                gerados += 1
            except Exception:
                erros += 1
        if gerados:
            self.message_user(
                request, f'Previsões geradas para {gerados} acordo(s).',
                level=messages.SUCCESS)
        if ignorados:
            self.message_user(
                request,
                f'{ignorados} acordo(s) ignorado(s): já tinham previsões.',
                level=messages.WARNING)
        if erros:
            self.message_user(
                request, f'Falha ao gerar previsões para {erros} acordo(s).',
                level=messages.ERROR)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()
        super().save_model(request, obj, form, change)


admin.site.register(AcordoPagamento, AcordoPagamentoAdmin)


# ----------------------------------------------------------------------
# 5. PRÉ-PAGAMENTO (espelho de PreFatura)
# ----------------------------------------------------------------------
class PrePagamentoAdmin(
        PagamentosDashboardMixin, BotaoExcluirLinhaMixin,
        EdicaoComRegrasMixin, ExclusaoEmLoteComRegrasMixin,
        AdminEstabelecimentoPadraoMixin,
        ExportToXLSMixin, admin.ModelAdmin):

    # INDICADORES / FILTROS.
    dashboard_competencia_field = 'competencia'
    dashboard_vencimento_field = 'dt_vencimento'
    dashboard_valor_field = 'valor'

    def get_dashboard_kpis(self, request, queryset):
        hoje = timezone.localdate()
        total = queryset.aggregate(t=Sum('valor'))['t'] or 0
        fechadas = queryset.filter(previsto_fechado=True)
        fechado = fechadas.aggregate(t=Sum('valor'))['t'] or 0
        vencidas = queryset.filter(
            previsto_fechado=False, dt_vencimento__lt=hoje).aggregate(
            t=Sum('valor'))['t'] or 0
        return [
            {'title': 'Pré-Pagamentos', 'value': _qtd(queryset.count()),
             'subtitle': 'Registros no filtro',
             'color_class': 'kpi-blue', 'icon': 'fa-file-invoice'},
            {'title': 'Valor Total', 'value': _money(total),
             'subtitle': 'Soma das previsões',
             'color_class': 'kpi-teal', 'icon': 'fa-money-bill-wave'},
            {'title': 'A Gerar Pagamento', 'value': _money(total - fechado),
             'subtitle': f'{_qtd(queryset.filter(previsto_fechado=False).count())} pendentes',
             'color_class': 'kpi-orange', 'icon': 'fa-hourglass-half'},
            {'title': 'Vencidas sem Pagamento', 'value': _money(vencidas),
             'subtitle': f'Vencimento anterior a {hoje:%d/%m/%Y}',
             'color_class': 'kpi-red', 'icon': 'fa-triangle-exclamation'},
            {'title': 'Já Geraram Pagamento', 'value': _money(fechado),
             'subtitle': f'{_qtd(fechadas.count())} convertidas',
             'color_class': 'kpi-green', 'icon': 'fa-circle-check'},
        ]

    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao', 'previsto_fechado']
    actions = ['export_as_xls', 'gerar_pagamentos_em_lote',
               'excluir_selecionados']

    list_display = ['id', 'gerar_pagamento_button', 'excluir_linha',
                    'fornecedor', 'classe_fornecedor', 'classe_pagamento','valor',
                    'competencia', 'dt_vencimento', 'acordo_pagamento',
                    'previsto_fechado', 'estabelecimento', 'status']
    list_display_links = ['id', 'fornecedor']
    # EDIÇÃO EM LINHA (mesma regra da tela): previsão que JÁ gerou pagamento
    # não edita nenhuma coluna.
    list_editable_sempre = ['valor', 'status']
    list_editable = list_editable_sempre

    def get_changelist(self, request, **kwargs):
        """Listagem editável com CADEADO nas previsões que já geraram
        pagamento (mesmo padrão das faturas)."""
        from admin_faturas.changelist_editavel import ChangeListEditavel
        return ChangeListEditavel
    list_filter = [FornecedorPagadorFilter, StatusFilterAdminMixin,
                   EstabelecimentoFilterAdminMixin,
                   'fornecedor', 'previsto_fechado',
                   ('competencia', admin.DateFieldListFilter)]
    list_per_page = 99

    def list_editable_permitido(self, request):
        """Previsão QUE JÁ GEROU PAGAMENTO não tem edição em linha.

        Espelho do `PreFaturaAdmin`: com pagamento gerado (`previsto_fechado`)
        a linha é somente leitura (`motivo_recusa_edicao`).
        """
        if request.GET.get('previsto_fechado__exact') == 'True':
            return []
        return list(self.list_editable_sempre)

    def get_linhas_nao_editaveis(self, request):
        """Pks das previsões que JÁ geraram pagamento: só texto."""
        try:
            return {str(pk) for pk in Pagamento.objects.values_list(
                'prepagamento_ptr_id', flat=True)}
        except Exception:
            return set()

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<path:object_id>/gerar-pagamento/',
                 self.admin_site.admin_view(self.gerar_pagamento_view),
                 name='admin_pagamentos_prepagamento_gerar'),
        ]
        return custom + urls

    def gerar_pagamento_button(self, obj):
        if Pagamento.objects.filter(prepagamento_ptr_id=obj.pk).exists():
            return format_html(
                '<span title="Pagamento gerado" style="color:#198754;'
                'font-weight:bold;">&#10003;</span>')
        url = reverse('admin:admin_pagamentos_prepagamento_gerar',
                      args=[obj.pk])
        return format_html(
            '<a class="button" href="{}">Gerar pagamento</a>', url)
    gerar_pagamento_button.short_description = 'Pagamento'

    def gerar_pagamento_view(self, request, object_id):
        from urllib.parse import unquote
        prepag = get_object_or_404(
            PrePagamento, pk=unquote(str(object_id)))
        try:
            with transaction.atomic():
                pag = prepag.gerar_pagamento()
            if pag is None:
                messages.info(
                    request,
                    f'A previsão {prepag.pk} já gerou o pagamento.')
            else:
                messages.success(
                    request,
                    f'Pagamento {pag.pk} gerado da previsão {prepag.pk}.')
        except Exception as erro:
            messages.error(
                request,
                f'Não foi possível gerar o pagamento da previsão '
                f'{prepag.pk}: {erro}')
        return redirect('admin:admin_pagamentos_prepagamento_changelist')

    @admin.action(description='Gerar pagamentos das previsões selecionadas')
    def gerar_pagamentos_em_lote(self, request, queryset):
        gerados = 0
        ja = 0
        erros = 0
        for prepag in queryset:
            try:
                with transaction.atomic():
                    if prepag.gerar_pagamento() is None:
                        ja += 1
                    else:
                        gerados += 1
            except Exception:
                erros += 1
        if gerados:
            self.message_user(
                request, f'{gerados} pagamento(s) gerado(s).',
                level=messages.SUCCESS)
        if ja:
            self.message_user(
                request,
                f'{ja} previsão(ões) já tinham pagamento; foram ignoradas.',
                level=messages.WARNING)
        if erros:
            self.message_user(
                request, f'Falha ao gerar {erros} pagamento(s).',
                level=messages.ERROR)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()
        super().save_model(request, obj, form, change)


admin.site.register(PrePagamento, PrePagamentoAdmin)


# ----------------------------------------------------------------------
# 6. PAGAMENTO (espelho de Fatura) — lista + modal de baixas + finalizar
# ----------------------------------------------------------------------
class DtLiquidacaoFilter(admin.SimpleListFilter):
    title = _('Liquidado')
    parameter_name = 'dt_liquidacao'

    def lookups(self, request, model_admin):
        return (('true', _('Liquidado')),
                ('false', _('Não Liquidado')))

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(dt_liquidacao__isnull=False)
        if self.value() == 'false':
            return queryset.filter(dt_liquidacao__isnull=True)
        return queryset


class FinalizadoStatusFilter(admin.SimpleListFilter):
    title = 'Finalização'
    parameter_name = 'finalizado_status'

    def lookups(self, request, model_admin):
        return (('sim', 'Finalizados'), ('nao', 'Abertos'))

    def queryset(self, request, queryset):
        if self.value() == 'sim':
            return queryset.filter(finalizado=True)
        if self.value() == 'nao':
            return queryset.filter(finalizado=False)
        return queryset


class PagamentoAdmin(
        PagamentosDashboardMixin, BotaoExcluirLinhaMixin,
        EdicaoComRegrasMixin,
        ExclusaoEmLoteComRegrasMixin, AdminEstabelecimentoPadraoMixin,
        AdminSaveModelAuditMixin, ExportToXLSMixin, admin.ModelAdmin):

    # INDICADORES / FILTROS (espelho da Fatura: saldo em aberto/vencido).
    dashboard_competencia_field = 'competencia'
    dashboard_vencimento_field = 'dt_vencimento'
    dashboard_valor_field = 'valor_pagamento'
    dashboard_saldo_field = 'valor_saldo'

    def get_dashboard_kpis(self, request, queryset):
        hoje = timezone.localdate()
        total = queryset.aggregate(t=Sum('valor_pagamento'))['t'] or 0
        saldo = queryset.aggregate(t=Sum('valor_saldo'))['t'] or 0
        pago = total - saldo
        em_aberto = queryset.filter(valor_saldo__gt=0).aggregate(
            t=Sum('valor_saldo'))['t'] or 0
        vencidas = queryset.filter(
            valor_saldo__gt=0, dt_vencimento__lt=hoje).aggregate(
            t=Sum('valor_saldo'))['t'] or 0
        return [
            {'title': 'Pagamentos', 'value': _qtd(queryset.count()),
             'subtitle': f"{_qtd(queryset.filter(finalizado=True).count())} finalizados",
             'color_class': 'kpi-blue', 'icon': 'fa-file-invoice'},
            {'title': 'Valor dos Pagamentos', 'value': _money(total),
             'subtitle': 'Soma do valor a pagar',
             'color_class': 'kpi-teal', 'icon': 'fa-money-bill-wave'},
            {'title': 'Pago', 'value': _money(pago),
             'subtitle': 'Valor menos saldo em aberto',
             'color_class': 'kpi-green', 'icon': 'fa-circle-check'},
            {'title': 'Total Saldo em Aberto', 'value': _money(em_aberto),
             'subtitle': f"{_qtd(queryset.filter(valor_saldo__gt=0).count())} com saldo",
             'color_class': 'kpi-orange', 'icon': 'fa-sack-dollar'},
            {'title': 'Saldo Vencido em Aberto', 'value': _money(vencidas),
             'subtitle': f'Vencimento anterior a {hoje:%d/%m/%Y}',
             'color_class': 'kpi-red', 'icon': 'fa-triangle-exclamation'},
        ]

    readonly_fields = ['us_registro', 'dt_registro', 'us_atualizacao',
                       'dt_atualizacao', 'dt_liquidacao', 'finalizado']
    actions = ['export_as_xls', 'finalizar_pagamentos_em_lote',
               'abrir_pagamentos_em_lote', 'excluir_selecionados']

    list_display = ['id', 'finalizar_pagamento_button', 'baixas_button',
                    'excluir_linha', 'fornecedor', 'classe_fornecedor','classe_pagamento',
                    'valor_pagamento', 'valor_saldo', 'dt_vencimento',
                    'dt_liquidacao', 'estabelecimento', 'status']
    list_display_links = ['id', 'fornecedor']
    list_editable_sempre = ['status']
    list_editable = list_editable_sempre
    list_filter = [FornecedorPagadorFilter, 'fornecedor',
                   FinalizadoStatusFilter, DtLiquidacaoFilter,
                   StatusFilterAdminMixin, EstabelecimentoFilterAdminMixin,
                   ('dt_vencimento', admin.DateFieldListFilter)]
    list_per_page = 99

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<path:object_id>/finalizar/',
                 self.admin_site.admin_view(self.finalizar_view),
                 name='admin_pagamentos_pagamento_finalizar'),
            path('<path:object_id>/baixas/',
                 self.admin_site.admin_view(self.baixas_view),
                 name='admin_pagamentos_pagamento_baixas'),
        ]
        return custom + urls

    # ------------------------------------------------------------------
    # FINALIZAR / REABRIR
    # ------------------------------------------------------------------
    def finalizar_pagamento_button(self, obj):
        url = reverse('admin:admin_pagamentos_pagamento_finalizar',
                      args=[obj.pk])
        if obj.finalizado:
            return format_html(
                '<a class="button" href="{}" title="Reabrir para edição">'
                'Reabrir</a>', url)
        return format_html(
            '<a class="button" href="{}">Finalizar</a>', url)
    finalizar_pagamento_button.short_description = 'Finalizar/Reabrir'

    def finalizar_view(self, request, object_id):
        from urllib.parse import unquote
        pag = get_object_or_404(Pagamento, pk=unquote(str(object_id)))
        # REABRIR um pagamento COM BAIXA é recusado: desfaria a saída.
        if pag.finalizado and pag.baixas_registradas().exists():
            messages.error(
                request,
                f'O pagamento {pag.pk} tem baixa registrada e não pode ser '
                'reaberto. Exclua primeiro a BAIXA, em “7. Baixa de '
                'Pagamentos”, e depois reabra.')
        else:
            pag.finalizado = not pag.finalizado
            pag.us_atualizacao = request.user
            pag.dt_atualizacao = timezone.now()
            pag.save(update_fields=[
                'finalizado', 'us_atualizacao', 'dt_atualizacao'])
            estado = 'finalizado' if pag.finalizado else 'reaberto'
            messages.success(
                request, f'Pagamento {pag.pk} marcado como {estado}.')
        return redirect('admin:admin_pagamentos_pagamento_changelist')

    @admin.action(description='Finalizar pagamentos selecionados')
    def finalizar_pagamentos_em_lote(self, request, queryset):
        agora = timezone.now()
        ok = ja = erros = 0
        for pag in queryset:
            if pag.finalizado:
                ja += 1
                continue
            try:
                with transaction.atomic():
                    pag.finalizado = True
                    pag.us_atualizacao = request.user
                    pag.dt_atualizacao = agora
                    pag.save(update_fields=[
                        'finalizado', 'us_atualizacao', 'dt_atualizacao'])
                ok += 1
            except Exception:
                erros += 1
        if ok:
            self.message_user(
                request, f'{ok} pagamento(s) finalizado(s).',
                level=messages.SUCCESS)
        if ja:
            self.message_user(
                request,
                f'{ja} pagamento(s) já estavam finalizados; ignorados.',
                level=messages.WARNING)
        if erros:
            self.message_user(
                request, f'Falha ao finalizar {erros} pagamento(s).',
                level=messages.ERROR)

    @admin.action(description='Abrir pagamentos selecionados (reabrir)')
    def abrir_pagamentos_em_lote(self, request, queryset):
        agora = timezone.now()
        ok = ja = com_baixa = erros = 0
        for pag in queryset:
            if not pag.finalizado:
                ja += 1
                continue
            if pag.baixas_registradas().exists():
                com_baixa += 1
                continue
            try:
                with transaction.atomic():
                    pag.finalizado = False
                    pag.us_atualizacao = request.user
                    pag.dt_atualizacao = agora
                    pag.save(update_fields=[
                        'finalizado', 'us_atualizacao', 'dt_atualizacao'])
                ok += 1
            except Exception:
                erros += 1
        if ok:
            self.message_user(
                request, f'{ok} pagamento(s) reaberto(s).',
                level=messages.SUCCESS)
        if com_baixa:
            self.message_user(
                request,
                f'{com_baixa} pagamento(s) NÃO foram reabertos: têm baixa '
                'registrada. Exclua primeiro a BAIXA, em “7. Baixa de '
                'Pagamentos”.', level=messages.WARNING)
        if ja:
            self.message_user(
                request, f'{ja} pagamento(s) já estavam abertos; ignorados.',
                level=messages.WARNING)
        if erros:
            self.message_user(
                request, f'Falha ao reabrir {erros} pagamento(s).',
                level=messages.ERROR)

    # ------------------------------------------------------------------
    # MODAL DE BAIXAS (só pagamento FINALIZADO)
    # ------------------------------------------------------------------
    def baixas_button(self, obj):
        if not obj.finalizado:
            return format_html(
                '<span title="O pagamento está ABERTO: finalize antes de '
                'lançar baixas." style="color:#9ca3af; cursor:not-allowed;">'
                'Baixas</span>')
        url = reverse('admin:admin_pagamentos_pagamento_baixas',
                      args=[obj.pk])
        qtd = obj.baixas_registradas().count()
        # `js-baixas-modal` abre o MODAL (ver static/js/admin_baixas_modal.js);
        # sem a classe o link navegaria para a página inteira.
        return format_html(
            '<button type="button" class="button js-baixas-modal" '
            'data-url="{}">Baixas ({})</button>', url, qtd)
    baixas_button.short_description = 'Baixas'

    def _resumo_baixas(self, pagamento):
        pagamento = Pagamento.objects.get(pk=pagamento.pk)
        total = pagamento.baixas_registradas().aggregate(
            s=Sum('valor_pagamento'))['s'] or 0
        return {
            'valor_pagamento': pagamento.valor_pagamento or pagamento.valor or 0,
            'soma_baixas': total,
            'saldo': pagamento.valor_saldo,
            'qtd': pagamento.baixas_registradas().count(),
        }

    def baixas_view(self, request, object_id):
        from urllib.parse import unquote
        from django.template.response import TemplateResponse

        pag = get_object_or_404(Pagamento, pk=unquote(str(object_id)))
        if not pag.finalizado:
            messages.warning(
                request,
                f'O pagamento {pag.pk} está ABERTO e ainda não pode receber '
                'baixas. Finalize o pagamento primeiro e depois lance a baixa.')
            return redirect('admin:admin_pagamentos_pagamento_changelist')

        if request.method == 'POST':
            acao = request.POST.get('acao') or 'lancar'
            if acao == 'excluir':
                baixa = BaixaPagamento.objects.filter(
                    pk=request.POST.get('baixa_id')).first()
                if baixa is None:
                    messages.warning(request, 'Baixa não encontrada.')
                else:
                    motivo = baixa.motivo_recusa_exclusao()
                    if motivo:
                        messages.error(request, motivo)
                    else:
                        pk = baixa.pk
                        try:
                            motivo = baixa.excluir_com_movimento()
                        except Exception as erro:
                            motivo = f'falha ao excluir ({erro})'
                        if motivo:
                            messages.error(request, motivo)
                        else:
                            messages.success(
                                request,
                                f'Baixa {pk} excluída e o valor devolvido ao '
                                'saldo do pagamento.')
            else:
                form = self._form_nova_baixa(request, pag)
                if form.is_valid():
                    try:
                        with transaction.atomic():
                            obj = form.save(commit=False)
                            obj.pagamento = pag
                            obj.estabelecimento = pag.estabelecimento
                            # AUDITORIA: quem lançou e quando (o
                            # `dt_registro` tem `default`, mas gravamos
                            # explícito para não depender do default do
                            # campo em `commit=False`).
                            obj.us_registro = request.user
                            obj.dt_registro = timezone.now()
                            obj.us_atualizacao = None
                            obj.dt_atualizacao = None
                            obj.status = 'A'
                            obj.save()
                        messages.success(
                            request,
                            f'Baixa registrada: {obj.valor_pagamento}. Saldo '
                            'atualizado.')
                    except Exception as erro:
                        form.add_error(None, f'Não foi possível salvar: {erro}')

        contexto = dict(self.admin_site.each_context(request))
        contexto.update({
            'title': 'Baixas do pagamento',
            'pagamento': pag,
            'baixas': pag.baixas_registradas().order_by('-dt_pagamento', '-pk'),
            'resumo': self._resumo_baixas(pag),
            'form_baixa': self._form_nova_baixa(request, pag),
            'opts': self.model._meta,
            'model_admin': self,
        })
        return TemplateResponse(
            request, 'admin_pagamentos/baixas_do_pagamento.html', contexto)

    def _form_nova_baixa(self, request, pagamento):
        dados = request.POST if request.method == 'POST' and \
            (request.POST.get('acao') or 'lancar') == 'lancar' else None
        form = BaixaPagamentoForm(dados or None, pagamento=pagamento)
        # DATA de hoje como padrão (o usuário ajusta se precisar).
        if dados is None and 'dt_pagamento' in form.fields:
            form.fields['dt_pagamento'].initial = timezone.localdate()
        # Recortes: pagamento fixo e lados válidos (banco ou caixa).
        if 'pagamento' in form.fields:
            form.fields['pagamento'].queryset = Pagamento.objects.filter(
                pk=pagamento.pk)
            form.fields['pagamento'].initial = pagamento.pk
            # O pagamento é DEFINIDO pela URL do modal: não vem no POST, logo
            # não pode ser exigido (senão a validação recusa a baixa).
            form.fields['pagamento'].required = False
        if 'transacao_financeira' in form.fields:
            form.fields['transacao_financeira'].queryset = (
                TransacaoFinanceira.objects.filter(
                    tipo='saida', movimento__in=['banco', 'caixa'],
                    status='A'))
        if 'competencia_bancaria' in form.fields:
            form.fields['competencia_bancaria'].queryset = (
                CompetenciaBancaria.objects.filter(
                    dt_fechamento_competencia__isnull=True, status='A'))
        return form

    # ------------------------------------------------------------------
    # REGRAS de edição/exclusão (mesma régua do modelo)
    # ------------------------------------------------------------------
    def get_changelist(self, request, **kwargs):
        """Listagem EDITÁVEL com o CADEADO nas linhas travadas.

        Sem este `get_changelist` o Django usa a tabela padrão e as colunas
        de `list_editable` aparecem editáveis mesmo com o pagamento
        FINALIZADO. O `ChangeListEditavel` lê `get_linhas_nao_editaveis` e
        renderiza essas colunas como TEXTO (aviso no `title`) — o mesmo
        comportamento da listagem de faturas.
        """
        from admin_faturas.changelist_editavel import ChangeListEditavel
        return ChangeListEditavel

    def get_linhas_nao_editaveis(self, request):
        pks = set(Pagamento.objects.filter(
            finalizado=True).values_list('pk', flat=True))
        pks.update(BaixaPagamento.objects.filter(
            pagamento_baixado__isnull=False).values_list(
            'pagamento_baixado__pk', flat=True))
        return {str(pk) for pk in pks}

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
            if obj.valor_pagamento is None:
                obj.valor_pagamento = obj.valor
            obj.valor_saldo = obj.valor_pagamento
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields
        return self.readonly_fields + ['status']


admin.site.register(Pagamento, PagamentoAdmin)


# ----------------------------------------------------------------------
# 7. BAIXA DE PAGAMENTO — tela própria retirada (a gestão é no MODAL)
# ----------------------------------------------------------------------
class BaixaPagamentoAdmin(
        PagamentosDashboardMixin,
        BotaoExcluirLinhaMixin, EdicaoComRegrasMixin,
        ExclusaoEmLoteComRegrasMixin, AdminSaveModelAuditMixin,
        AdminEstabelecimentoPadraoMixin, ExportToXLSMixin, admin.ModelAdmin):
    """Mantido apenas para consulta/histórico; o lançamento é pelo modal.

    Herda o `PagamentosDashboardMixin` (indicadores + seletores do topo,
    inclusive ESTABELECIMENTO) e o `AdminEstabelecimentoPadraoMixin` como as
    demais etapas: o campo `estabelecimento` é fixado no estabelecimento da
    sessão/perfil (aqui ele também é derivado do pagamento no `save_model`).
    """

    form = BaixaPagamentoForm
    actions = ['export_as_xls', 'excluir_selecionados']
    list_editable_sempre = ['observacao', 'status']
    list_editable = list_editable_sempre

    # O `estabelecimento` sai como READONLY (derivado do pagamento no
    # `save_model`): não há campo para o mixin fixar no formulário, mas ele
    # segue aplicando o recorte/bloqueio de sessão.
    readonly_fields = ['us_registro', 'dt_registro', 'us_atualizacao',
                       'dt_atualizacao', 'estabelecimento']
    list_display = ['id', 'excluir_linha', 'pagamento', 'competencia_bancaria',
                    'competencia_caixa', 'valor_pagamento', 'dt_pagamento',
                    'estabelecimento', 'observacao', 'status']
    list_filter = [StatusFilterAdminMixin, EstabelecimentoFilterAdminMixin,
                   'transacao_financeira']
    list_per_page = 99

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        def form_init(form_instance, *args, **init_kwargs):
            # Pagamento = SAÍDA (banco ou caixa).
            if 'transacao_financeira' in form_instance.fields:
                form_instance.fields['transacao_financeira'].queryset = (
                    TransacaoFinanceira.objects.filter(
                        tipo='saida', movimento__in=['banco', 'caixa'],
                        status='A'))
            if 'competencia_bancaria' in form_instance.fields:
                form_instance.fields['competencia_bancaria'].queryset = (
                    CompetenciaBancaria.objects.filter(
                        dt_fechamento_competencia__isnull=True, status='A'))
            if 'pagamento' in form_instance.fields:
                form_instance.fields['pagamento'].queryset = Pagamento.objects.filter(
                    valor_saldo__gt=0, status='A')

        from dominios.utils import chain_form_init
        chain_form_init(form, form_init)
        return form

    def delete_model(self, request, obj):
        motivo = obj.motivo_recusa_exclusao()
        if motivo:
            messages.error(request, motivo)
            return
        try:
            motivo = obj.excluir_com_movimento()
        except Exception as erro:
            messages.error(
                request, f'Não foi possível excluir a baixa: {erro}')
            return
        if motivo:
            messages.error(request, motivo)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()
        if obj.pagamento_id:
            obj.estabelecimento = obj.pagamento.estabelecimento
        super().save_model(request, obj, form, change)


# BAIXA de Pagamento NÃO tem tela própria (item “7. Baixa de Pagamentos”).
# A gestão é feita APENAS pelo MODAL “Baixas (n)” da linha do Pagamento —
# ver `PagamentoAdmin.baixas_view`. Mesmo padrão do fluxo de faturas, onde a
# `BaixaFatura` também não é registrada (o menu só existe até o “Pagamento”).
#
# O `BaixaPagamentoAdmin` acima continua DEFINIDO: as URLs de baixa são as do
# `PagamentoAdmin` e a exclusão acontece dentro do próprio modal (não usa a
# `delete_view` do admin da baixa).
# admin.site.register(BaixaPagamento, BaixaPagamentoAdmin)  # removido do menu
