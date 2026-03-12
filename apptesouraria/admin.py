from django.contrib import admin
from .models import Tesouraria, Caixa, SaldoCaixa, MovimentacaoCaixa


@admin.register(Tesouraria)
class TesourariaAdmin(admin.ModelAdmin):
    list_display = ('numero_tesouraria', 'descricao', 'estabelecimento', 'status', 'data_criacao')
    list_filter = ('status', 'data_criacao', 'estabelecimento')
    search_fields = ('numero_tesouraria', 'descricao')
    readonly_fields = ('data_criacao', 'data_atualizacao', 'us_registro', 'us_atualizacao')


@admin.register(Caixa)
class CaixaAdmin(admin.ModelAdmin):
    list_display = ('numero_caixa', 'descricao', 'tesouraria', 'status', 'data_criacao')
    list_filter = ('status', 'data_criacao', 'tesouraria')
    search_fields = ('numero_caixa', 'descricao')
    readonly_fields = ('data_criacao', 'data_atualizacao', 'us_registro', 'us_atualizacao')


@admin.register(SaldoCaixa)
class SaldoCaixaAdmin(admin.ModelAdmin):
    list_display = ('caixa', 'data_abertura', 'saldo_inicial', 'saldo_final', 'status')
    list_filter = ('status', 'data_abertura', 'caixa')
    search_fields = ('caixa__numero_caixa',)
    readonly_fields = ('data_criacao', 'data_atualizacao', 'us_registro', 'us_atualizacao')


@admin.register(MovimentacaoCaixa)
class MovimentacaoCaixaAdmin(admin.ModelAdmin):
    list_display = ('saldo_caixa', 'tipo', 'origem', 'valor', 'descricao', 'status', 'data_criacao')
    list_filter = ('tipo', 'origem', 'status', 'data_criacao')
    search_fields = ('descricao', 'numero_documento')
    readonly_fields = ('data_criacao', 'data_atualizacao', 'us_registro', 'us_atualizacao')
