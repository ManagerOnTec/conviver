from django.urls import path
from . import views

app_name = 'admin_pagamentos'

urlpatterns = [
    # Cartão de Pagamento
    path('cartao/', views.cartao_index, name='cartao_index'),
    path('cartao/listar/', views.CartaoListView.as_view(), name='cartao_listar'),
    path('cartao/criar/', views.CartaoCreateView.as_view(), name='cartao_criar'),
    path('cartao/<int:pk>/', views.CartaoDetailView.as_view(), name='cartao_detalhe'),
    path('cartao/<int:pk>/editar/', views.CartaoUpdateView.as_view(), name='cartao_editar'),
    
    # Transações do Cartão
    path('cartao/<int:cartao_id>/transacoes/', views.TransacaoCartaoListView.as_view(), name='transacao_listar'),
    path('cartao/<int:cartao_id>/transacoes/criar/', views.TransacaoCartaoCreateView.as_view(), name='transacao_criar'),
    path('transacao/<int:pk>/editar/', views.TransacaoCartaoUpdateView.as_view(), name='transacao_editar'),
    path('transacao/<int:pk>/deletar/', views.deletar_transacao, name='transacao_deletar'),
    
    # Faturas do Cartão
    path('cartao/<int:cartao_id>/faturas/', views.FaturaCartaoListView.as_view(), name='fatura_listar'),
    path('fatura/<int:pk>/', views.FaturaCartaoDetailView.as_view(), name='fatura_detalhe'),
    
    # Pagamentos de Fatura
    path('fatura/<int:fatura_id>/pagar/', views.pagar_fatura, name='fatura_pagar'),
]
