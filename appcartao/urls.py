from django.urls import path
from . import views

app_name = 'appcartao'

urlpatterns = [
    # Dashboard
    path('', views.cartao_index, name='cartao_index'),
    
    # Cartão de Pagamento
    path('cartaopagamento_listar/', views.CartaoPagamentoListView.as_view(), name='cartaopagamento_listar'),
    path('cartaopagamento_criar/', views.CartaoPagamentoCreateView.as_view(), name='cartaopagamento_criar'),
    path('cartaopagamento_detalhe/<int:pk>/', views.CartaoPagamentoDetailView.as_view(), name='cartaopagamento_detalhe'),
    path('cartaopagamento_editar/<int:pk>/', views.CartaoPagamentoUpdateView.as_view(), name='cartaopagamento_editar'),
    
    # Transação de Cartão
    path('transacaocartao_listar/<int:cartao_id>/', views.TransacaoCartaoListView.as_view(), name='transacaocartao_listar'),
    path('transacaocartao_criar/<int:cartao_id>/', views.TransacaoCartaoCreateView.as_view(), name='transacaocartao_criar'),
    path('transacaocartao_detalhe/<int:pk>/', views.TransacaoCartaoDetailView.as_view(), name='transacaocartao_detalhe'),
    path('transacaocartao_editar/<int:pk>/', views.TransacaoCartaoUpdateView.as_view(), name='transacaocartao_editar'),
    
    # Fatura de Cartão
    path('faturacartao_listar/<int:cartao_id>/', views.FaturaCartaoListView.as_view(), name='faturacartao_listar'),
    path('faturacartao_criar/<int:cartao_id>/', views.FaturaCartaoCreateView.as_view(), name='faturacartao_criar'),
    path('faturacartao_detalhe/<int:pk>/', views.FaturaCartaoDetailView.as_view(), name='faturacartao_detalhe'),
    path('faturacartao_editar/<int:pk>/', views.FaturaCartaoUpdateView.as_view(), name='faturacartao_editar'),
    
    # Pagamento de Cartão
    path('pagamentocartao_listar/<int:fatura_id>/', views.PagamentoCartaoListView.as_view(), name='pagamentocartao_listar'),
    path('pagamentocartao_criar/<int:fatura_id>/', views.PagamentoCartaoCreateView.as_view(), name='pagamentocartao_criar'),
    path('pagamentocartao_detalhe/<int:pk>/', views.PagamentoCartaoDetailView.as_view(), name='pagamentocartao_detalhe'),
    path('pagamentocartao_editar/<int:pk>/', views.PagamentoCartaoUpdateView.as_view(), name='pagamentocartao_editar'),
]
