from django.urls import path
from . import views

urlpatterns = [

    # INDEX##############################################
    path('cadastros_index/', views.cadastros_index, name='cadastros_index'),
]
