from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import datetime
from django.contrib import admin
from admin_financeiro.models import MovimentoBancario, CompetenciaBancaria
from admin_cadastros.utils import EstabelecimentoFilterAdminMixin
from contas.models import Perfil
from dominios.utils import AdminEstabelecimentoPadraoMixin, AdminSaveModelAuditMixin, StatusFilterAdminMixin 
from .forms import BaixaPagamentoForm, ClassificacaoFornecedorForm, ClassificacaoPagamentoForm,FornecedorForm
from admin_pagamentos.models import BaixaPagamento, ClassificacaoFornecedor, ClassificacaoPagamento, Fornecedor, ParametrosPagamentos, Pagamento
from admin_cadastros_financeiros.models import TransacaoFinanceira
from dominios.utils import ExportToXLSMixin

class ClassificacaoFornecedorAdmin(ExportToXLSMixin, admin.ModelAdmin):

    form = ClassificacaoFornecedorForm

    actions = ['export_as_xls'] # Registrar a ação no admin

    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']
    list_display = ['descricao', 'observacao',
                    'us_registro', 'dt_registro', 'status']

    list_editable = ['status', 'observacao']

    list_filter = [StatusFilterAdminMixin]

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



class ClassificacaoPagamentoAdmin(ExportToXLSMixin, admin.ModelAdmin):

    form = ClassificacaoPagamentoForm

    actions = ['export_as_xls'] # Registrar a ação no admin

    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']
    list_display = ['descricao', 'observacao',
                    'us_registro', 'dt_registro', 'status']

    list_editable = ['status', 'observacao']

    list_filter = [StatusFilterAdminMixin]

    list_per_page = 99

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()
        super().save_model(request, obj, form, change)


admin.site.register(ClassificacaoPagamento, ClassificacaoPagamentoAdmin)



class FornecedorAdmin(ExportToXLSMixin, admin.ModelAdmin):

    form = FornecedorForm

    actions = ['export_as_xls'] # Registrar a ação no admin

    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']
    list_display = ['id', 'descricao', 'empresa',
                    'pessoa', 'classificacao', 'observacao', 'dt_registro', 'status']

    list_filter = ['empresa', 'pessoa', StatusFilterAdminMixin]

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




@admin.register(ParametrosPagamentos)
class ParametrosPagamentosAdmin(admin.ModelAdmin):
    list_display = ['fornecedor', 'valor_previsto', 'recorrencia', 'data_inicio', 'data_fim', 'status']
    readonly_fields = ['us_registro', 'dt_registro', 'us_atualizacao', 'dt_atualizacao']
    actions = ['gerar_cobrancas_recentes']

    def gerar_cobrancas_recentes(self, request, queryset):
        """
        Ação do admin para gerar cobranças manualmente.
        """
        for parametro in queryset:
            parametro.gerar_cobrancas()
        self.message_user(request, "Cobranças geradas com sucesso.")

    gerar_cobrancas_recentes.short_description = "Gerar cobranças para os parâmetros selecionados"


    def save_model(self, request, obj, form, change):
        if not change:  # se estiver criando um novo objeto
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:  # se estiver editando um objeto existente
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()

        super().save_model(request, obj, form, change)



class DtLiquidacaoFilter(admin.SimpleListFilter):
    title = _('Liquidado (Não)')  # Título do filtro no admin
    parameter_name = 'dt_liquidacao'  # Parâmetro utilizado na URL

    def lookups(self, request, model_admin):
        return (
            ('true', _('Liquidado')),
            ('false', _('Não Liquidado')),
        )

    def queryset(self, request, queryset):
        # Se o valor for 'true', filtra pelos que possuem data de liquidação (liquidados)
        if self.value() == 'true':
            return queryset.filter(dt_liquidacao__isnull=False)
        # Se o valor for 'false', filtra pelos que não possuem data de liquidação (não liquidados)
        if self.value() == 'false':
            return queryset.filter(dt_liquidacao__isnull=True)

        # Se nenhum filtro for aplicado, retorna apenas os "não liquidados" (falso)
        return queryset.filter(dt_liquidacao__isnull=True)


class PagamentoAdmin(ExportToXLSMixin, AdminEstabelecimentoPadraoMixin, AdminSaveModelAuditMixin, admin.ModelAdmin):
    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao', 'dt_liquidacao']
    list_display = ['id', 'fornecedor', 'classificacao_pagamento', 'valor_pagamento',
                    'valor_saldo', 'dt_vencimento', 'observacao', 'dt_liquidacao', 'dt_registro', 'us_registro',
                    'estabelecimento', 'status']
    
    actions = ['export_as_xls'] # Registrar a ação no admin

    list_display_links = ['id', 'fornecedor']

    list_editable = ['observacao', 'status']

    list_filter = ['fornecedor', DtLiquidacaoFilter,
                   StatusFilterAdminMixin, EstabelecimentoFilterAdminMixin]

    list_per_page = 99

    # Método para controlar campos read-only

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Se o objeto já existir (change)
            return self.readonly_fields  # Não altera o comportamento padrão
        else:  # Se for uma nova instância (add)
            # Converter para lista para permitir a concatenação
            return self.readonly_fields + ['valor_saldo', 'status']


admin.site.register(Pagamento, PagamentoAdmin)

class BaixaPagamentoAdmin(ExportToXLSMixin, AdminSaveModelAuditMixin, AdminEstabelecimentoPadraoMixin, admin.ModelAdmin):
    form = BaixaPagamentoForm

    actions = ['export_as_xls'] # Registrar a ação no admin

    readonly_fields = ['us_registro', 'dt_registro', 'us_atualizacao', 'dt_atualizacao', 'estabelecimento']
    list_display = ['id', 'pagamento', 'competencia_bancaria', 'valor_pagamento', 'dt_pagamento',
                    'estabelecimento', 'observacao', 'dt_registro', 'status']
    list_filter = [StatusFilterAdminMixin, EstabelecimentoFilterAdminMixin]
    list_per_page = 99

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)

        if 'HTTP_REFERER' in request.META:
            referer_path = request.META['HTTP_REFERER'].split(
                request.META['HTTP_HOST'])[1]
            if '/add/' in referer_path or '/change/' in referer_path:
                queryset = queryset.filter(status='A')

        return queryset, use_distinct

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        def form_init(form_instance, *args, **kwargs):
            super(form_instance.__class__, form_instance).__init__(
                *args, **kwargs)

            perfil_usuario = request.user.perfil
            estabelecimentos_permitidos = perfil_usuario.estabelecimento.all()

            form_instance.fields['pagamento'].queryset = Pagamento.objects.filter(
                valor_saldo__gt=0, status='A', estabelecimento__in=estabelecimentos_permitidos
            )

            form_instance.fields['transacao_financeira'].queryset = TransacaoFinanceira.objects.filter(
                tipo='entrada', status='A'
            )

            form_instance.fields['competencia_bancaria'].queryset = CompetenciaBancaria.objects.filter(
                dt_fechamento_competencia__isnull = True, status='A'
            )

        form.__init__ = form_init

        return form


    def save_model(self, request, obj, form, change):
        """
        Define os campos de auditoria e salva o objeto com as informações
        de registro e atualização de usuários e datas.
        """
        if not change:
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()

        if obj.pagamento:
            obj.estabelecimento = obj.pagamento.estabelecimento

        super().save_model(request, obj, form, change)



admin.site.register(BaixaPagamento, BaixaPagamentoAdmin)
