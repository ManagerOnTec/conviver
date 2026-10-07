from django.urls import path

from .views import (
    DocumentoLegalCreateView,
    DocumentoLegalDeleteView,
    DocumentoLegalFilteredPdfDownloadView,
    DocumentoLegalListView,
    DocumentoLegalPdfView,
    DocumentoLegalTemplatePreviewView,
)


urlpatterns = [
    path('atendimento/<int:atendimento_id>/listar/', DocumentoLegalListView.as_view(), name='documentos_legais_listar'),
    path('atendimento/<int:atendimento_id>/cadastrar/', DocumentoLegalCreateView.as_view(), name='documentos_legais_cadastrar'),
    path('atendimento/<int:atendimento_id>/download-filtrados/', DocumentoLegalFilteredPdfDownloadView.as_view(), name='documentos_legais_download_filtrados'),
    path('excluir/<int:pk>/', DocumentoLegalDeleteView.as_view(), name='documentos_legais_excluir'),
    path('pdf/<int:pk>/', DocumentoLegalPdfView.as_view(), name='documentos_legais_pdf'),
    path('atendimento/<int:atendimento_id>/modelo-preview/', DocumentoLegalTemplatePreviewView.as_view(), name='documentos_legais_modelo_preview'),
]
