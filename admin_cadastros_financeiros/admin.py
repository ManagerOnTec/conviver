from django.contrib import admin
from .models import Banco, Agencia, Conta, TransacaoFinanceira
from dominios.utils import ExportToXLSMixin, Select2AdminModelAdminMixin


@admin.register(Banco)
class BancoAdmin(admin.ModelAdmin):
    list_display = ['numero_banco', 'descricao_banco']
    search_fields = ['numero_banco', 'descricao_banco']


@admin.register(Agencia)
class AgenciaAdmin(admin.ModelAdmin):
    list_display = ['banco', 'numero_agencia', 'observacao']
    search_fields = ['banco', 'numero_agencia', 'observacao']


@admin.register(Conta)
class ContaAdmin(admin.ModelAdmin):
    list_display = ['agencia', 'numero_conta', 'observacao',]
    search_fields = ['agencia', 'numero_conta', 'observacao',]


@admin.register(TransacaoFinanceira)
class TransacaoFinanceiraAdmin(Select2AdminModelAdminMixin, ExportToXLSMixin,
                               admin.ModelAdmin):
    # Precisa do mixin: é o admin de DESTINO do select2 de transação usado em
    # faturas/pagamentos, e é aqui que o recorte do campo é aplicado na busca.
    list_display = ['transacao_financeira', 'tipo', 'movimento', ]
    # Necessário para o select2 de digitação (autocomplete) nas Baixas de Fatura.
    search_fields = ['transacao_financeira', 'tipo',]

    actions = ['export_as_xls']
