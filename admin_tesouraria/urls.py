from django.urls import path
from . import views

app_name = 'admin_tesouraria'

urlpatterns = [
    # Dashboard
    path('', views.tesouraria_index, name='index'),
    
    # Caixas
    path('caixas/', views.CaixaListView.as_view(), name='caixa_listar'),
    path('caixas/criar/', views.CaixaCreateView.as_view(), name='caixa_criar'),
    path('caixas/<int:pk>/', views.CaixaDetailView.as_view(), name='caixa_detalhe'),
    path('caixas/<int:pk>/editar/', views.CaixaUpdateView.as_view(), name='caixa_editar'),
    
    # Saldos de Caixa
    path('caixas/<int:pk>/abrir/', views.abrir_caixa, name='abrir_caixa'),
    path('saldos/<int:pk>/fechar/', views.fechar_caixa, name='fechar_caixa'),
    
    # Movimentações
    path('saldos/<int:saldo_id>/movimentacoes/', views.MovimentacaoCaixaListView.as_view(), name='movimentacao_listar'),
    path('saldos/<int:saldo_id>/movimentacoes/criar/', views.MovimentacaoCaixaCreateView.as_view(), name='movimentacao_criar'),
    path('movimentacoes/<int:pk>/editar/', views.MovimentacaoCaixaUpdateView.as_view(), name='movimentacao_editar'),
    path('movimentacoes/<int:pk>/deletar/', views.deletar_movimentacao, name='movimentacao_deletar'),
    
    # Relatórios
    path('relatorio/', views.relatorio_tesouraria, name='relatorio'),
]
