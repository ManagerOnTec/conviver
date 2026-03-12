from django import urls
from . views import (OrcamentosDeleteView, OrcamentosListView, OrcamentosCreateView,
                     OrcamentosUpdateView)
from django.urls import path, include
from . import views

urlpatterns = [

    # orcamentos ##############################################
    path('orcamentos_listar/', OrcamentosListView.as_view(),
         name="orcamentos_listar"),
    path('orcamentos_cadastrar/', OrcamentosCreateView.as_view(),
         name="orcamentos_cadastrar"),
    path('orcamentos_editar/<int:pk>/',
         OrcamentosUpdateView.as_view(), name="orcamentos_editar"),
    path('orcamentos_excluir/<int:pk>/',
         OrcamentosDeleteView.as_view(), name="orcamentos_excluir"),
]
