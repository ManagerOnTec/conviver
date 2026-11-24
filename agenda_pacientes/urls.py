from django.urls import path

from . import views

urlpatterns = [
    path('agenda_listar/', views.AgendaPacienteListView.as_view(),
         name='agendapaciente_listar'),
    path('agenda_cadastrar/', views.AgendaPacienteCreateView.as_view(),
         name='agendapaciente_cadastrar'),
    path('agenda_opcoes/', views.AgendaOpcoesView.as_view(),
         name='agendapaciente_opcoes'),
    path('agenda_detalhe/<int:pk>/',
         views.AgendaPacienteDetailView.as_view(),
         name='agendapaciente_detalhe'),
    path('agenda_editar/<int:pk>/', views.AgendaPacienteUpdateView.as_view(),
         name='agendapaciente_editar'),
    path('agenda_excluir/<int:pk>/',
         views.AgendaPacienteDeleteView.as_view(),
         name='agendapaciente_excluir'),
    path('agenda_efetuar/<int:pk>/',
         views.AgendaPacienteEfetuarView.as_view(),
         name='agendapaciente_efetuar'),
    path('agenda_relatorio/', views.AgendaPacienteRelatorioView.as_view(),
         name='agendapaciente_relatorio'),
    path('agenda_exame/<int:atendimento_id>/',
         views.AgendaExameListaView.as_view(),
         name='agendaexame_lista'),
]
