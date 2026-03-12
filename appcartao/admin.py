from django.contrib import admin
from .models import CartaoPagamento, TransacaoCartao, FaturaCartao, PagamentoCartao


@admin.register(CartaoPagamento)
class CartaoPagamentoAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'bandeira', 'tipo', 'limite', 'status', 'data_criacao')
    list_filter = ('status', 'bandeira', 'tipo', 'data_criacao')
    search_fields = ('descricao', 'numero_cartao')
    readonly_fields = ('data_criacao', 'data_atualizacao', 'us_registro', 'us_atualizacao')


@admin.register(TransacaoCartao)
class TransacaoCartaoAdmin(admin.ModelAdmin):
    list_display = ('cartao', 'descricao', 'valor', 'data_transacao', 'fornecedor', 'status')
    list_filter = ('status', 'data_transacao', 'cartao', 'categoria')
    search_fields = ('descricao', 'fornecedor', 'numero_documento')
    readonly_fields = ('data_criacao', 'data_atualizacao', 'us_registro', 'us_atualizacao')


@admin.register(FaturaCartao)
class FaturaCartaoAdmin(admin.ModelAdmin):
    list_display = ('cartao', 'mes_referencia', 'valor_total', 'valor_pago', 'status')
    list_filter = ('status', 'mes_referencia', 'cartao')
    readonly_fields = ('data_criacao', 'data_atualizacao', 'us_registro', 'us_atualizacao')


@admin.register(PagamentoCartao)
class PagamentoCartaoAdmin(admin.ModelAdmin):
    list_display = ('fatura', 'valor_pagamento', 'data_pagamento', 'forma_pagamento', 'status')
    list_filter = ('status', 'forma_pagamento', 'data_pagamento')
    search_fields = ('numero_documento',)
    readonly_fields = ('data_criacao', 'data_atualizacao', 'us_registro', 'us_atualizacao')
