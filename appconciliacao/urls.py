from django.urls import path
from . import views

app_name = 'appconciliacao'

urlpatterns = [
    # Dashboard
    path('', views.conciliacao_index, name='conciliacao_index'),
    
    # Extrato Bancário
    path('extratobancario_listar/', views.ExtratoBancarioListView.as_view(), name='extratobancario_listar'),
    path('extratobancario_criar/', views.ExtratoBancarioCreateView.as_view(), name='extratobancario_criar'),
    path('extratobancario_detalhe/<int:pk>/', views.ExtratoBancarioDetailView.as_view(), name='extratobancario_detalhe'),
    path('extratobancario_editar/<int:pk>/', views.ExtratoBancarioUpdateView.as_view(), name='extratobancario_editar'),
    
    # Lançamento Bancário
    path('lancamentobancario_listar/<int:extrato_id>/', views.LancamentoBancarioListView.as_view(), name='lancamentobancario_listar'),
    path('lancamentobancario_criar/<int:extrato_id>/', views.LancamentoBancarioCreateView.as_view(), name='lancamentobancario_criar'),
    path('lancamentobancario_detalhe/<int:pk>/', views.LancamentoBancarioDetailView.as_view(), name='lancamentobancario_detalhe'),
    path('lancamentobancario_editar/<int:pk>/', views.LancamentoBancarioUpdateView.as_view(), name='lancamentobancario_editar'),
    
    # Conciliação
    path('conciliacao_listar/<int:lancamento_id>/', views.ConciliacaoListView.as_view(), name='conciliacao_listar'),
    path('conciliacao_criar/<int:lancamento_id>/', views.ConciliacaoCreateView.as_view(), name='conciliacao_criar'),
    path('conciliacao_detalhe/<int:pk>/', views.ConciliacaoDetailView.as_view(), name='conciliacao_detalhe'),
    path('conciliacao_editar/<int:pk>/', views.ConciliacaoUpdateView.as_view(), name='conciliacao_editar'),
    
    # Relatório de Conciliação
    path('relatorioconciliacao_listar/', views.RelatorioConciliacaoListView.as_view(), name='relatorioconciliacao_listar'),
    path('relatorioconciliacao_criar/', views.RelatorioConciliacaoCreateView.as_view(), name='relatorioconciliacao_criar'),
    path('relatorioconciliacao_detalhe/<int:pk>/', views.RelatorioConciliacaoDetailView.as_view(), name='relatorioconciliacao_detalhe'),
]
