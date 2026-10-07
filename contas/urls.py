from django.urls import path, include
from . import views
from . views import *
from django.contrib.auth import views as auth_views


urlpatterns = [
     path('', views.login, name='home'),
     path('home/', views.home, name='home_legacy'),
    path('login/', views.login, name='login'),
    path('alterar/', views.alterar, name='alterar'),
    path('logout/', views.logout, name='logout'),
    path('esqueci/', views.esqueci, name='esqueci'),
    path('select_estabelecimento/', views.select_estabelecimento,
         name="select_estabelecimento"),
    path('resetar/<uidb64>/<token>/', views.password_reset_confirm,
         name='password_reset_confirm'),
]
