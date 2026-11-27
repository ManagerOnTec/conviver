"""URLs da Gestão de Leitos."""
from django.urls import path

from . import views

urlpatterns = [
    path('leito_mapa/', views.LeitoMapView.as_view(), name='gl_leito_mapa'),
    path('leito/<int:leito_id>/ocupar/', views.OcuparLeitoView.as_view(),
         name='gl_leito_ocupar'),
    path('ocupacao/<int:pk>/saida/', views.SaidaLeitoView.as_view(),
         name='gl_ocupacao_saida'),
    path('ocupacao/<int:pk>/excluir/',
         views.ExcluirOcupacaoView.as_view(), name='gl_ocupacao_excluir'),
    path('ocupacao/<int:pk>/transferir/',
         views.TransferirLeitoView.as_view(), name='gl_ocupacao_transferir'),
    path('ocupacao/<int:pk>/status/', views.StatusLeitoView.as_view(),
         name='gl_ocupacao_status'),
    path('ocupacao_cadastrar/', views.RegistrarOcupacaoCreateView.as_view(),
         name='gl_ocupacao_cadastrar'),
    path('ocupacao/<int:pk>/editar/',
         views.RegistrarOcupacaoUpdateView.as_view(),
         name='gl_ocupacao_editar'),
    path('ocupacao/<int:pk>/detalhe/', views.OcupacaoDetailView.as_view(),
         name='gl_ocupacao_detalhe'),
]
