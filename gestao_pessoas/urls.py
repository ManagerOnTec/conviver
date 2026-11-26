"""URLs da Gestão de Pessoas."""
from django.urls import path

from . import views

urlpatterns = [
    path('funcionario_listar/', views.FuncionarioListView.as_view(),
         name='gp_funcionario_listar'),
    path('funcionario_cadastrar/', views.FuncionarioCreateView.as_view(),
         name='gp_funcionario_cadastrar'),
    path('funcionario/<int:pk>/editar/', views.FuncionarioUpdateView.as_view(),
         name='gp_funcionario_editar'),
    path('funcionario/<int:pk>/detalhe/',
         views.FuncionarioDetailView.as_view(),
         name='gp_funcionario_detalhe'),
    path('funcionario/<int:pk>/documento/',
         views.DocumentoFuncionarioView.as_view(),
         name='gp_funcionario_documento'),
    path('funcionario/<int:pk>/documento/<int:documento_id>/excluir/',
         views.DocumentoExcluirView.as_view(),
         name='gp_documento_excluir'),
    path('funcionario/<int:pk>/aso/<str:acao>/', views.AsoView.as_view(),
         name='gp_aso'),
    path('funcionario/<int:pk>/ficha/', views.FichaRegistroView.as_view(),
         name='gp_ficha'),
    path('funcionario/<int:pk>/cartao/', views.CartaoPontoView.as_view(),
         name='gp_cartao'),
    path('funcionario/<int:pk>/periodico/<str:acao>/',
         views.PeriodicoView.as_view(), name='gp_periodico'),
    path('funcionario/<int:pk>/curso/', views.CursoFuncionarioView.as_view(),
         name='gp_curso'),
    path('funcionario/<int:pk>/curso_pendente/',
         views.CursoFuncionarioPendenteView.as_view(),
         name='gp_curso_pendente'),
    path('funcionario/<int:pk>/ferias/<str:acao>/', views.FeriasView.as_view(),
         name='gp_ferias'),
]
