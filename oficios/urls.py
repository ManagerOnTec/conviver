from django import urls
from .views import (OficiosDeleteView, OficiosListView, OficiosCreateView,
                    OficiosUpdateView)
from django.urls import path, include
from . import views

urlpatterns = [

    # oficios ##############################################
    path('oficios_listar/', OficiosListView.as_view(),
         name="oficios_listar"),
    path('oficios_cadastrar/', OficiosCreateView.as_view(),
         name="oficios_cadastrar"),
    path('oficios_editar/<int:pk>/',
         OficiosUpdateView.as_view(), name="oficios_editar"),
    path('oficios_excluir/<int:pk>/',
         OficiosDeleteView.as_view(), name="oficios_excluir"),
]
