from django import urls
from . views import (AtasDeleteView, AtasListView, AtasCreateView,
                     AtasUpdateView)
from django.urls import path, include
from . import views

urlpatterns = [

    # atas ##############################################
    path('atas_listar/', AtasListView.as_view(),
         name="atas_listar"),
    path('atas_cadastrar/', AtasCreateView.as_view(),
         name="atas_cadastrar"),
    path('atas_editar/<int:pk>/',
         AtasUpdateView.as_view(), name="atas_editar"),
    path('atas_excluir/<int:pk>/',
         AtasDeleteView.as_view(), name="atas_excluir"),
]
