from django.urls import path
from . import views

app_name = 'appbaixa_fatura'

urlpatterns = [
    # Dashboard
    path('', views.baixa_fatura_index, name='baixa_fatura_index'),
    
    # Baixa de Fatura
    path('baixafatura_listar/', views.BaixaFaturaListView.as_view(), name='baixafatura_listar'),
    path('baixafatura_listar/<int:fatura_id>/', views.BaixaFaturaListView.as_view(), name='baixafatura_listar_fatura'),
    path('baixafatura_criar/', views.BaixaFaturaCreateView.as_view(), name='baixafatura_criar'),
    path('baixafatura_criar/<int:fatura_id>/', views.BaixaFaturaCreateView.as_view(), name='baixafatura_criar_fatura'),
    path('baixafatura_detalhe/<int:pk>/', views.BaixaFaturaDetailView.as_view(), name='baixafatura_detalhe'),
    path('baixafatura_editar/<int:pk>/', views.BaixaFaturaUpdateView.as_view(), name='baixafatura_editar'),
    
    # Baixa de Pagamento
    path('baixapagamento_listar/', views.BaixaPagamentoListView.as_view(), name='baixapagamento_listar'),
    path('baixapagamento_listar/<int:pagamento_id>/', views.BaixaPagamentoListView.as_view(), name='baixapagamento_listar_pagamento'),
    path('baixapagamento_criar/', views.BaixaPagamentoCreateView.as_view(), name='baixapagamento_criar'),
    path('baixapagamento_criar/<int:pagamento_id>/', views.BaixaPagamentoCreateView.as_view(), name='baixapagamento_criar_pagamento'),
    path('baixapagamento_detalhe/<int:pk>/', views.BaixaPagamentoDetailView.as_view(), name='baixapagamento_detalhe'),
    path('baixapagamento_editar/<int:pk>/', views.BaixaPagamentoUpdateView.as_view(), name='baixapagamento_editar'),
    
    # Processo de Baixa
    path('processoBaixa_listar/', views.ProcessoBaixaListView.as_view(), name='processoBaixa_listar'),
    path('processoBaixa_detalhe/<int:pk>/', views.ProcessoBaixaDetailView.as_view(), name='processoBaixa_detalhe'),
    
    # Relatório de Baixa
    path('relatoriobaixa_listar/', views.RelatorioBaixaListView.as_view(), name='relatoriobaixa_listar'),
    path('relatoriobaixa_criar/', views.RelatorioBaixaCreateView.as_view(), name='relatoriobaixa_criar'),
    path('relatoriobaixa_detalhe/<int:pk>/', views.RelatorioBaixaDetailView.as_view(), name='relatoriobaixa_detalhe'),
    path('relatoriobaixa_editar/<int:pk>/', views.RelatorioBaixaUpdateView.as_view(), name='relatoriobaixa_editar'),
]
