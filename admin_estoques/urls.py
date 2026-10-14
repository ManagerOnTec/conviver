from django.urls import path, include

from . import views

app_name = 'admin_estoques'

urlpatterns = [
    path('chaining/', include('smart_selects.urls')),
    path('importar-medicamentos/', views.importar_medicamentos,
         name='importar'),
    path('importar-medicamentos/confirmar/', views.importar_confirmar,
         name='importar_confirmar'),
]
