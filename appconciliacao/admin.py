from django.contrib import admin
from .models import ExtratoBancario, LancamentoBancario, Conciliacao, RelatorioConciliacao


@admin.register(ExtratoBancario)
class ExtratoBancarioAdmin(admin.ModelAdmin):
    list_display = ('numero_banco', 'numero_agencia', 'data_fim', 'status', 'data_criacao')
    list_filter = ('status', 'data_fim', 'estabelecimento')
    search_fields = ('numero_banco', 'numero_agencia', 'numero_conta')
    readonly_fields = ('data_criacao', 'data_atualizacao', 'us_registro', 'us_atualizacao')


@admin.register(LancamentoBancario)
class LancamentoBancarioAdmin(admin.ModelAdmin):
    list_display = ('extrato', 'data_lancamento', 'tipo', 'valor', 'descricao')
    list_filter = ('tipo', 'data_lancamento', 'extrato')
    search_fields = ('descricao', 'numero_documento')
    readonly_fields = ('data_criacao',)


@admin.register(Conciliacao)
class ConciliacaoAdmin(admin.ModelAdmin):
    list_display = ('lancamento_bancario', 'tipo_transacao', 'status', 'data_criacao')
    list_filter = ('status', 'tipo_transacao', 'data_criacao')
    search_fields = ('observacao',)
    readonly_fields = ('data_criacao', 'data_atualizacao', 'us_registro', 'us_atualizacao')


@admin.register(RelatorioConciliacao)
class RelatorioConciliacaoAdmin(admin.ModelAdmin):
    list_display = ('estabelecimento', 'data_fim', 'total_lancamentos', 'status', 'data_criacao')
    list_filter = ('status', 'data_fim', 'estabelecimento')
    readonly_fields = ('data_criacao', 'data_atualizacao', 'us_registro', 'us_atualizacao')
