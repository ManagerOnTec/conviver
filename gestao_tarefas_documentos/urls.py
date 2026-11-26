"""URLs da Gestão de Tarefas e Documentos."""
from django.urls import path

from . import views

urlpatterns = [
    # Documentos
    path('documento_listar/', views.DocumentoListView.as_view(),
         name='gtd_documento_listar'),
    path('documento_cadastrar/', views.DocumentoCreateView.as_view(),
         name='gtd_documento_cadastrar'),
    path('documento/<int:pk>/editar/', views.DocumentoUpdateView.as_view(),
         name='gtd_documento_editar'),
    path('documento/<int:pk>/detalhe/', views.DocumentoDetailView.as_view(),
         name='gtd_documento_detalhe'),
    path('documento/<int:pk>/validar/', views.DocumentoValidarView.as_view(),
         name='gtd_documento_validar'),
    path('documento/<int:pk>/desvalidar/',
         views.DocumentoDesvalidarView.as_view(),
         name='gtd_documento_desvalidar'),
    path('documento/<int:pk>/renovar/', views.DocumentoRenovarView.as_view(),
         name='gtd_documento_renovar'),
    path('documento/<int:pk>/anotar/', views.DocumentoAnotarView.as_view(),
         name='gtd_documento_anotar'),
    path('documento/<int:pk>/inativar/', views.DocumentoInativarView.as_view(),
         name='gtd_documento_inativar'),
    # Tarefas
    path('tarefa_listar/', views.TarefaListView.as_view(),
         name='gtd_tarefa_listar'),
    path('tarefa_cadastrar/', views.TarefaCreateView.as_view(),
         name='gtd_tarefa_cadastrar'),
    path('tarefa/<int:pk>/editar/', views.TarefaUpdateView.as_view(),
         name='gtd_tarefa_editar'),
    path('tarefa/<int:pk>/acao/<str:acao>/', views.TarefaAcaoView.as_view(),
         name='gtd_tarefa_acao'),
    path('tarefa/<int:pk>/anotar/', views.TarefaAnotarView.as_view(),
         name='gtd_tarefa_anotar'),
    path('tarefa/<int:pk>/inativar/', views.TarefaInativarView.as_view(),
         name='gtd_tarefa_inativar'),
]
