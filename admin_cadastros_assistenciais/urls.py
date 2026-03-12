from django.urls import path
from . import views


"""
EXEMPLO TEMPLATEVIEW
path('exemplo/', Exemplo.as_view(), name='exemplo'),

"""

urlpatterns = [

    # INDEX##############################################
    path('cadastros_assistenciais/', views.cadastros_assistenciais,
         name='cadastros_assistenciais'),
]
