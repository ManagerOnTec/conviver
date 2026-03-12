from django import urls
from . views import (AtendimentoDeleteView, AtendimentoListView, AtendimentoCreateView,
                     AtendimentoDetailView, AtendimentoUpdateView)
from . views import PessoaCreateView

from django.urls import path, include
from . import views

urlpatterns = [

    # atendimento ##############################################
    path('atendimento_listar/', AtendimentoListView.as_view(),
         name="atendimento_listar"),
    path('atendimento_cadastrar/', AtendimentoCreateView.as_view(),
         name="atendimento_cadastrar"),
    path('atendimento_detalhe/<int:pk>/',
         AtendimentoDetailView.as_view(), name="atendimento_detalhe"),
    path('atendimento_editar/<int:pk>/',
         AtendimentoUpdateView.as_view(), name="atendimento_editar"),
    path('atendimento_excluir/<int:pk>/',
         AtendimentoDeleteView.as_view(), name="atendimento_excluir"),
    path('pessoa_cadastrar/', PessoaCreateView.as_view(), name='pessoa_cadastrar'),
    path('obter_cidades/', views.obter_cidades, name='obter_cidades'),

]
