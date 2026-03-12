from django.contrib import admin
from django.utils.html import format_html
from .models import ExtratoBancario, TransacaoExtrato, Conciliacao, DivergenciaConciliacao


@admin.register(ExtratoBancario)
class ExtratoBancarioAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'conta',
        'competencia_bancaria',
        'data_extrato_inicio',
        'data_extrato_fim',
        'quantidade_transacoes',
        'saldo_inicial',
        'saldo_final',
        'status'
    )
    list_filter = (
        'status',
        'tipo_arquivo',
        'data_extrato_inicio',
        'competencia_bancaria',
    )
    search_fields = (
        'conta__numero_conta',
        'competencia_bancaria__descricao',
    )
    readonly_fields = (
        'dt_registro',
        'dt_atualizacao',
        'total_entradas',
        'total_saidas',
        'quantidade_transacoes',
    )
    fieldsets = (
        ('Informações Básicas', {
            'fields': (
                'competencia_bancaria',
                'conta',
                'tipo_arquivo',
                'arquivo',
            )
        }),
        ('Período do Extrato', {
            'fields': (
                'data_extrato_inicio',
                'data_extrato_fim',
            )
        }),
        ('Saldos', {
            'fields': (
                'saldo_inicial',
                'saldo_final',
                'total_entradas',
                'total_saidas',
            )
        }),
        ('Transações', {
            'fields': (
                'quantidade_transacoes',
            )
        }),
        ('Observações', {
            'fields': (
                'observacao',
            )
        }),
        ('Auditoria', {
            'fields': (
                'status',
                'us_registro',
                'dt_registro',
                'us_atualizacao',
                'dt_atualizacao',
                'estabelecimento',
            ),
            'classes': ('collapse',)
        }),
    )


@admin.register(TransacaoExtrato)
class TransacaoExtratoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'extrato_bancario',
        'data_transacao',
        'tipo_transacao_display',
        'valor_display',
        'descricao_truncada',
        'conciliada_display',
    )
    list_filter = (
        'tipo_transacao',
        'conciliada',
        'data_transacao',
        'extrato_bancario',
    )
    search_fields = (
        'descricao',
        'numero_documento',
        'referencia_banco',
    )
    readonly_fields = (
        'dt_registro',
        'extrato_bancario',
    )
    fieldsets = (
        ('Informações da Transação', {
            'fields': (
                'extrato_bancario',
                'data_transacao',
                'data_lancamento',
                'tipo_transacao',
                'valor',
            )
        }),
        ('Detalhes', {
            'fields': (
                'descricao',
                'numero_documento',
                'referencia_banco',
                'observacao',
            )
        }),
        ('Status', {
            'fields': (
                'conciliada',
            )
        }),
        ('Auditoria', {
            'fields': (
                'dt_registro',
            ),
            'classes': ('collapse',)
        }),
    )

    def tipo_transacao_display(self, obj):
        """Exibe o tipo de transação com cores."""
        if obj.tipo_transacao == 'D':
            color = '#dc3545'  # Vermelho para débito
            texto = 'Débito'
        else:
            color = '#28a745'  # Verde para crédito
            texto = 'Crédito'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            texto
        )
    tipo_transacao_display.short_description = 'Tipo'

    def valor_display(self, obj):
        """Exibe o valor com formatação."""
        return f"R$ {obj.valor:,.2f}".replace(',', '.')
    valor_display.short_description = 'Valor'

    def descricao_truncada(self, obj):
        """Exibe a descrição truncada."""
        return obj.descricao[:50] + '...' if len(obj.descricao) > 50 else obj.descricao
    descricao_truncada.short_description = 'Descrição'

    def conciliada_display(self, obj):
        """Exibe o status de conciliação com ícone."""
        if obj.conciliada:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">✓ Conciliada</span>'
            )
        else:
            return format_html(
                '<span style="color: #ffc107; font-weight: bold;">⊘ Pendente</span>'
            )
    conciliada_display.short_description = 'Status'


@admin.register(Conciliacao)
class ConciliacaoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'transacao_extrato',
        'movimento_bancario',
        'valor_conciliado_display',
        'diferenca_display',
        'status_display',
    )
    list_filter = (
        'status',
        'competencia_bancaria',
        'dt_registro',
    )
    search_fields = (
        'transacao_extrato__descricao',
        'movimento_bancario__transacao_financeira__descricao',
    )
    readonly_fields = (
        'dt_registro',
        'dt_atualizacao',
        'diferenca',
    )
    fieldsets = (
        ('Informações da Conciliação', {
            'fields': (
                'transacao_extrato',
                'movimento_bancario',
                'competencia_bancaria',
            )
        }),
        ('Valores', {
            'fields': (
                'valor_conciliado',
                'diferenca',
            )
        }),
        ('Status', {
            'fields': (
                'status',
                'motivo_divergencia',
            )
        }),
        ('Observações', {
            'fields': (
                'observacao',
            )
        }),
        ('Auditoria', {
            'fields': (
                'us_registro',
                'dt_registro',
                'us_atualizacao',
                'dt_atualizacao',
                'estabelecimento',
            ),
            'classes': ('collapse',)
        }),
    )

    def valor_conciliado_display(self, obj):
        """Exibe o valor conciliado com formatação."""
        return f"R$ {obj.valor_conciliado:,.2f}".replace(',', '.')
    valor_conciliado_display.short_description = 'Valor'

    def diferenca_display(self, obj):
        """Exibe a diferença com cores."""
        if obj.diferenca == 0:
            color = '#28a745'  # Verde
            texto = 'Sem diferença'
        else:
            color = '#dc3545'  # Vermelho
            texto = f"R$ {obj.diferenca:,.2f}".replace(',', '.')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            texto
        )
    diferenca_display.short_description = 'Diferença'

    def status_display(self, obj):
        """Exibe o status com cores."""
        status_colors = {
            'P': '#ffc107',  # Amarelo - Pendente
            'C': '#28a745',  # Verde - Conciliado
            'D': '#dc3545',  # Vermelho - Divergente
            'A': '#6c757d',  # Cinza - Anulado
        }
        status_textos = {
            'P': 'Pendente',
            'C': 'Conciliado',
            'D': 'Divergente',
            'A': 'Anulado',
        }
        color = status_colors.get(obj.status, '#000000')
        texto = status_textos.get(obj.status, obj.status)
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            texto
        )
    status_display.short_description = 'Status'


@admin.register(DivergenciaConciliacao)
class DivergenciaConciliacaoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'conciliacao',
        'tipo_divergencia',
        'prioridade_display',
        'resolvida_display',
    )
    list_filter = (
        'tipo_divergencia',
        'prioridade',
        'resolvida',
        'dt_registro',
    )
    search_fields = (
        'descricao',
        'solucao',
    )
    readonly_fields = (
        'dt_registro',
        'dt_resolucao',
    )
    fieldsets = (
        ('Informações da Divergência', {
            'fields': (
                'conciliacao',
                'tipo_divergencia',
                'descricao',
            )
        }),
        ('Prioridade e Status', {
            'fields': (
                'prioridade',
                'resolvida',
            )
        }),
        ('Resolução', {
            'fields': (
                'solucao',
                'us_resolucao',
                'dt_resolucao',
            )
        }),
        ('Auditoria', {
            'fields': (
                'us_registro',
                'dt_registro',
            ),
            'classes': ('collapse',)
        }),
    )

    def prioridade_display(self, obj):
        """Exibe a prioridade com cores."""
        prioridade_colors = {
            'A': '#dc3545',  # Vermelho - Alta
            'M': '#ffc107',  # Amarelo - Média
            'B': '#28a745',  # Verde - Baixa
        }
        prioridade_textos = {
            'A': 'Alta',
            'M': 'Média',
            'B': 'Baixa',
        }
        color = prioridade_colors.get(obj.prioridade, '#000000')
        texto = prioridade_textos.get(obj.prioridade, obj.prioridade)
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            texto
        )
    prioridade_display.short_description = 'Prioridade'

    def resolvida_display(self, obj):
        """Exibe o status de resolução com ícone."""
        if obj.resolvida:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">✓ Resolvida</span>'
            )
        else:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">✗ Não Resolvida</span>'
            )
    resolvida_display.short_description = 'Status'
