from django.contrib import admin
from django.urls import path, include, reverse_lazy
from django.conf import settings
from django.conf.urls.static import static
from admin_relatorios.views import TextoPadraoFiltradoPorTipoView

# Define o destino do link "Ver o site" no Django Admin.
admin.site.site_url = reverse_lazy('select_estabelecimento')

urlpatterns = [
    path('', include('contas.urls')),
    path('admin_cadastros/', include('admin_cadastros.urls')),

    path('admin_cadastros_assistenciais/',
         include('admin_cadastros_assistenciais.urls')),
    path('atendimentos/', include('atendimentos.urls')),
    path('prontuarios/', include('prontuarios.urls')),
    path('oficios/', include('oficios.urls')),
    path('orcamentos/', include('orcamentos.urls')),
    path('atas/', include('atas.urls')),
    path('documentos-legais/', include('documentos_legais.urls')),
    path('admin_prescricoes/', include('admin_prescricoes.urls')),
    path('admin_pagamentos/', include('admin_pagamentos.urls')),
    
    path('apptesouraria/', include('apptesouraria.urls')),
    path('appconciliacao/', include('appconciliacao.urls')),
    path('appcartao/', include('appcartao.urls')),
    path('appbaixa_fatura/', include('appbaixa_fatura.urls')),
    path('admin/', admin.site.urls),

    path('select2/', include('django_select2.urls')),
    path('chaining/', include('smart_selects.urls')),
    path(
        'texto-padrao/<str:tipo_documento>/',  # Ex: /texto-padrao/atas/
        TextoPadraoFiltradoPorTipoView.as_view(),
        name='texto_padrao_filtrado_por_tipo'
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
