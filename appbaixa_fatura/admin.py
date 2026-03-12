from django.contrib import admin
from .models import BaixaFatura, BaixaPagamento, ProcessoBaixa, RelatorioBaixa


@admin.register(BaixaFatura)
class BaixaFaturaAdmin(admin.ModelAdmin):
    list_display = ('fatura', 'tipo_baixa', 'valor_baixa', 'data_baixa', 'status')
    list_filter = ('status', 'tipo_baixa', 'data_baixa')
    search_fields = ('fatura__numero_fatura', 'numero_documento')
    readonly_fields = ('data_criacao', 'data_atualizacao', 'us_registro', 'us_atualizacao')


@admin.register(BaixaPagamento)
class BaixaPagamentoAdmin(admin.ModelAdmin):
    list_display = ('pagamento', 'tipo_baixa', 'valor_baixa', 'data_baixa', 'status')
    list_filter = ('status', 'tipo_baixa', 'data_baixa')
    search_fields = ('pagamento__numero_documento', 'numero_documento')
    readonly_fields = ('data_criacao', 'data_atualizacao', 'us_registro', 'us_atualizacao')


@admin.register(ProcessoBaixa)
class ProcessoBaixaAdmin(admin.ModelAdmin):
    list_display = ('id', 'tipo_processo', 'status', 'itens_processados', 'total_itens', 'data_criacao')
    list_filter = ('status', 'tipo_processo', 'data_criacao')
    readonly_fields = ('data_criacao', 'data_conclusao')


@admin.register(RelatorioBaixa)
class RelatorioBaixaAdmin(admin.ModelAdmin):
    list_display = ('data_fim', 'total_baixas_fatura', 'total_baixas_pagamento', 'valor_total_baixado', 'status')
    list_filter = ('status', 'data_fim')
    readonly_fields = ('data_criacao', 'data_atualizacao', 'us_registro', 'us_atualizacao')
