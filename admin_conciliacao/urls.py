from django.urls import path
from . import views

app_name = 'admin_conciliacao'

urlpatterns = [
    # Dashboard principal
    path('', views.index_conciliacao, name='index'),
    
    # Extratos bancários
    path('extratos/', views.listar_extratos, name='listar_extratos'),
    path('extratos/criar/', views.criar_extrato, name='criar_extrato'),
    path('extratos/<int:pk>/', views.detalhar_extrato, name='detalhar_extrato'),
    
    # Conciliação
    path('conciliar/', views.conciliar_transacoes, name='conciliar_transacoes'),
    path('conciliar/criar/', views.criar_conciliacao, name='criar_conciliacao'),
    path('conciliações/', views.listar_conciliações, name='listar_conciliações'),
    path('conciliações/<int:pk>/', views.detalhar_conciliacao, name='detalhar_conciliacao'),
    
    # Divergências
    path('divergências/', views.listar_divergencias, name='listar_divergencias'),
]
