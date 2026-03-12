from . import views
from django.urls import path
from . views import (AdepListarAdministrarView, AdepListarAssinarView, DiagnosticoCreateView, DiagnosticoDetailView, DiagnosticoListView, DiagnosticoUpdateView, GestaoPacientesListView, ItensPrescricaoListView, PassagemPlantaoCreateView, PassagemPlantaoDetailView, PassagemPlantaoListView, PrescricaoCreateView, PrescricaoListView, PrescricaoUpdateView, ProntuarioAcessosCreateView, PsicoterapiaCreateView, PsicoterapiaDetailView, PsicoterapiaListView, PsicoterapiaUpdateView, combine_pdfs_specific, download_filtered_pdfs, get_aspecto_analisado, get_evidencia, PerdasGanhosCreateView, PerdasGanhosDetailView, PerdasGanhosListView, PerdasGanhosUpdateView, PlanoCuidadosCreateView, PlanoCuidadosDetailView,
                     PlanoCuidadosListView, PlanoCuidadosUpdateView, ProntuarioDetailView, EvolucaoListView, EvolucaoCreateView, EvolucaoDetailView, EvolucaoUpdateView, ProntuarioListView, SAECreateView, SAEDetailView, SAEListView, SAEUpdateView, SinaisVitaisCreateView, SinaisVitaisDetailView, SinaisVitaisListView, SinaisVitaisUpdateView, TextoPadraoFiltradoView, AdepListView,
                     SuspendPrescriptionView, PrescricaoGeralListView, check_adeps)
from . utils import buscar_diagnosticos


urlpatterns = [
    path('prontuario_listar/', ProntuarioListView.as_view(),
         name="prontuario_listar"),
    path('prontuario_detalhe/<int:pk>/',
         ProntuarioDetailView.as_view(), name="prontuario_detalhe"),

    path('evolucao_listar/', EvolucaoListView.as_view(),
         {'atendimento_id': 0}, name='evolucao_listar_sem_id'),

    path('evolucao_listar/<int:atendimento_id>/',
         EvolucaoListView.as_view(), name='evolucao_listar'),
    path('evolucao_cadastrar/<int:atendimento_id>/',
         EvolucaoCreateView.as_view(), name='evolucao_cadastrar'),
    path('evolucao_detalhe/<int:pk>/',
         EvolucaoDetailView.as_view(), name='evolucao_detalhe'),
    path('evolucao_editar/<int:pk>/',
         EvolucaoUpdateView.as_view(), name='evolucao_editar'),

    path('psicoterapia_listar/<int:atendimento_id>/',
         PsicoterapiaListView.as_view(), name='psicoterapia_listar'),
    path('psicoterapia_cadastrar/<int:atendimento_id>/',
         PsicoterapiaCreateView.as_view(), name='psicoterapia_cadastrar'),
    path('psicoterapia_detalhe/<int:pk>/',
         PsicoterapiaDetailView.as_view(), name='psicoterapia_detalhe'),
    path('psicoterapia_editar/<int:pk>/',
         PsicoterapiaUpdateView.as_view(), name='psicoterapia_editar'),

    path('textopadrao_filtrado/',
         TextoPadraoFiltradoView.as_view(), name='textopadrao_filtrado'),

    path('sinais_vitais_listar/<int:atendimento_id>/',
         SinaisVitaisListView.as_view(), name='sinais_vitais_listar'),
    path('sinais_vitais_cadastrar/<int:atendimento_id>/',
         SinaisVitaisCreateView.as_view(), name='sinais_vitais_cadastrar'),
    path('sinais_vitais_detalhe/<int:pk>/',
         SinaisVitaisDetailView.as_view(), name='sinais_vitais_detalhe'),
    path('sinais_vitais_editar/<int:pk>/',
         SinaisVitaisUpdateView.as_view(), name='sinais_vitais_editar'),

    path('perdas_ganhos_listar/<int:atendimento_id>/',
         PerdasGanhosListView.as_view(), name='perdas_ganhos_listar'),
    path('perdas_ganhos_cadastrar/<int:atendimento_id>/',
         PerdasGanhosCreateView.as_view(), name='perdas_ganhos_cadastrar'),
    path('perdas_ganhos_detalhe/<int:pk>/',
         PerdasGanhosDetailView.as_view(), name='perdas_ganhos_detalhe'),
    path('perdas_ganhos_editar/<int:pk>/',
         PerdasGanhosUpdateView.as_view(), name='perdas_ganhos_editar'),

    path('plano_cuidados_listar/<int:atendimento_id>/',
         PlanoCuidadosListView.as_view(), name='plano_cuidados_listar'),
    path('plano_cuidados_cadastrar/<int:atendimento_id>/',
         PlanoCuidadosCreateView.as_view(), name='plano_cuidados_cadastrar'),
    path('plano_cuidados_detalhe/<int:pk>/',
         PlanoCuidadosDetailView.as_view(), name='plano_cuidados_detalhe'),
    path('plano_cuidados_editar/<int:pk>/',
         PlanoCuidadosUpdateView.as_view(), name='plano_cuidados_editar'),

    path('sae_listar/<int:atendimento_id>/',
         SAEListView.as_view(), name='sae_listar'),
    path('sae_cadastrar/<int:atendimento_id>/',
         SAECreateView.as_view(), name='sae_cadastrar'),
    path('sae_detalhe/<int:pk>/',
         SAEDetailView.as_view(), name='sae_detalhe'),
    path('sae_editar/<int:pk>/',
         SAEUpdateView.as_view(), name='sae_editar'),

    path('get_aspecto_analisado/', get_aspecto_analisado,
         name='get_aspecto_analisado'),
    path('get_evidencia/', get_evidencia, name='get_evidencia'),
    path('get_diagnostico_enfermagem/', views.get_diagnostico_enfermagem,
         name='get_diagnostico_enfermagem'),
    path('get_fator_relacionado/', views.get_fator_relacionado,
         name='get_fator_relacionado'),
    path('get_intervencao/', views.get_intervencao, name='get_intervencao'),
    path('get_evidencia_by_diagnostico/', views.get_evidencia_by_diagnostico,
         name='get_evidencia_by_diagnostico'),

    path('prontuario_acessos/', ProntuarioAcessosCreateView.as_view(),
         name='prontuario_acessos'),

    path('prescricao_listar/<int:atendimento_id>/',
         PrescricaoListView.as_view(), name='prescricao_listar'),

    path('prescricao_geral_listar/',
         PrescricaoGeralListView.as_view(), name='prescricao_geral_listar'),


    path('itens_prescricao_listar/<int:prescricao_id>/',
         ItensPrescricaoListView.as_view(), name='itens_prescricao_listar'),
    path('prescricao_cadastrar/<int:atendimento_id>/',
         PrescricaoCreateView.as_view(), name='prescricao_cadastrar'),
    path('prescricao_editar/<int:pk>/',
         PrescricaoUpdateView.as_view(), name='prescricao_editar'),

    path('adep_listar/<int:atendimento_id>',
         AdepListView.as_view(), name='adep_listar'),
    path('adep_update_fase/<int:pk>/<str:new_fase>/',
         views.adep_update_fase,  name='adep_update_fase'),

    path('adep_listar_assinar', AdepListarAssinarView.as_view(),
         name='adep_listar_assinar'),


    path('adep_listar_administrar', AdepListarAdministrarView.as_view(),
         name='adep_listar_administrar'),

    path('suspend_prescricao/',
         SuspendPrescriptionView.as_view(), name='suspend_prescricao'),

    path('download_filtered_pdfs/<int:atendimento_id>/<str:model_name>/',
         download_filtered_pdfs, name='download_filtered_pdfs'),

    path('combine-pdfs-specific/<int:object_id>/<str:tipo>/',
         combine_pdfs_specific, name='combine_pdfs_specific'),

    path('diagnostico_listar/<int:atendimento_id>/',
         DiagnosticoListView.as_view(), name='diagnostico_listar'),
    path('diagnostico_cadastrar/<int:atendimento_id>/',
         DiagnosticoCreateView.as_view(), name='diagnostico_cadastrar'),
    path('diagnostico_detalhe/<int:pk>/',
         DiagnosticoDetailView.as_view(), name='diagnostico_detalhe'),
    path('diagnostico_editar/<int:pk>/',
         DiagnosticoUpdateView.as_view(), name='diagnostico_editar'),

    path('passagem_plantao_listar/',
         PassagemPlantaoListView.as_view(), name='passagem_plantao_listar'),
    path('passagem_plantao_cadastrar/',
         PassagemPlantaoCreateView.as_view(), name='passagem_plantao_cadastrar'),

    path('passagem_plantao/verificar_adeps/',
         check_adeps, name='verificar_adeps'),

    path('passagem_plantao_detalhe/<int:pk>/',
         PassagemPlantaoDetailView.as_view(), name='passagem_plantao_detalhe'),


    path('buscar_diagnosticos/<int:atendimento_id>/',
         buscar_diagnosticos, name='buscar_diagnosticos'),

    path('gestao_pacientes/',
         GestaoPacientesListView.as_view(), name='gestao_pacientes'),

]
