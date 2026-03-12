from django.urls import path
from . import views

app_name = 'apptesouraria'

urlpatterns = [
    # Dashboard
    path('', views.tesouraria_index, name='tesouraria_index'),
    
    # Tesouraria
    path('tesouraria_listar/', views.TesourariaListView.as_view(), name='tesouraria_listar'),
    path('tesouraria_criar/', views.TesourariaCreateView.as_view(), name='tesouraria_criar'),
    path('tesouraria_detalhe/<int:pk>/', views.TesourariaDetailView.as_view(), name='tesouraria_detalhe'),
    path('tesouraria_editar/<int:pk>/', views.TesourariaUpdateView.as_view(), name='tesouraria_editar'),
    
    # Caixa
    path('caixa_listar/<int:tesouraria_id>/', views.CaixaListView.as_view(), name='caixa_listar'),
    path('caixa_criar/<int:tesouraria_id>/', views.CaixaCreateView.as_view(), name='caixa_criar'),
    path('caixa_detalhe/<int:pk>/', views.CaixaDetailView.as_view(), name='caixa_detalhe'),
    path('caixa_editar/<int:pk>/', views.CaixaUpdateView.as_view(), name='caixa_editar'),
    
    # Saldo Caixa
    path('saldocaixa_listar/<int:caixa_id>/', views.SaldoCaixaListView.as_view(), name='saldocaixa_listar'),
    path('saldocaixa_criar/<int:caixa_id>/', views.SaldoCaixaCreateView.as_view(), name='saldocaixa_criar'),
    path('saldocaixa_detalhe/<int:pk>/', views.SaldoCaixaDetailView.as_view(), name='saldocaixa_detalhe'),
    path('saldocaixa_editar/<int:pk>/', views.SaldoCaixaUpdateView.as_view(), name='saldocaixa_editar'),
    
    # Movimentação Caixa
    path('movimentacaocaixa_listar/<int:saldo_id>/', views.MovimentacaoCaixaListView.as_view(), name='movimentacaocaixa_listar'),
    path('movimentacaocaixa_criar/<int:saldo_id>/', views.MovimentacaoCaixaCreateView.as_view(), name='movimentacaocaixa_criar'),
    path('movimentacaocaixa_detalhe/<int:pk>/', views.MovimentacaoCaixaDetailView.as_view(), name='movimentacaocaixa_detalhe'),
    path('movimentacaocaixa_editar/<int:pk>/', views.MovimentacaoCaixaUpdateView.as_view(), name='movimentacaocaixa_editar'),
]
