from django.contrib import admin
from .models import Banco, Agencia, Conta, TransacaoFinanceira
from dominios.utils import ExportToXLSMixin


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
class TransacaoFinanceiraAdmin(ExportToXLSMixin, admin.ModelAdmin):
    list_display = ['transacao_financeira', 'tipo', 'movimento', ]
    search_fields = ['tipo',]

    actions = ['export_as_xls']
