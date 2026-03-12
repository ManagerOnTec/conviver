from django.template.loader import render_to_string
from django.core import serializers
from admin_cadastros.models import Estado
from admin_cadastros.models import Cidade
from django.http import HttpResponseRedirect, JsonResponse
from django.db import models
from django.contrib import messages
from django.db.models.deletion import ProtectedError
from django.db.models import ProtectedError
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from admin_cadastros.models import Pessoa
import json
from datetime import datetime, time
from http.client import HTTPResponse
from smtplib import SMTPResponseException

from braces.views import GroupRequiredMixin
from django.contrib import auth, messages
from django.contrib.auth import (authenticate, login, logout,
                                 update_session_auth_hash)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import (AuthenticationForm, PasswordChangeForm,
                                       UserCreationForm)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, ListView, TemplateView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django_select2.forms import Select2Widget
from django.db import IntegrityError
from django.http import HttpResponse
from django.contrib.admin.sites import AdminSite
from django.shortcuts import render
from admin_cadastros_assistenciais.models import CadastroProfissional
from dominios.utils import AccessDenied, FilterObjectsByEstabelecimentoMixin, CustomPermissionRequiredMixin
from admin_cadastros.models import Estabelecimento
from django.conf import settings


def handler_exception(request, exception):
    if isinstance(exception, IntegrityError):
        return (request, "Erro ao criar o registro, o mesmo já está sendo usado por outro registro.")
    if isinstance(exception, ProtectedError):
        return (request, "Registro já utilizado, não pode ser excluído, você pode inativa-lo")
    else:
        return HttpResponse("Erro desconhecido.", status=500)


@login_required(login_url='login')
def cadastros_index(request):

    # Se o usuário não está autenticado, redirecione para a página de login
    if not request.user.is_authenticated:
        messages.warning(
            request, "Sua sessão expirou. Por favor, faça login novamente.")
        # substitua 'login' com sua URL de login
        return HttpResponseRedirect(reverse('login'))

    context = {
        'titulo': 'Funções do Sistema',
        'title': 'cadastros_index',
        'mostrar_nav': True,
        # adicione a URL correta aqui
        'prontuario_listar_url': reverse('prontuario_listar'),
        # adicione a URL correta aqui
        'prontuario_acessos_url': reverse('prontuario_acessos'),
    }

    estabelecimento_id = request.session.get("estabelecimento_id")
    if estabelecimento_id:
        context["estabelecimento"] = Estabelecimento.objects.get(
            pk=estabelecimento_id)
    else:
        context["estabelecimento"] = None

    try:
        cadastro_medico = CadastroProfissional.objects.get(
            profissional=request.user, status='A')
        context["is_assistencial"] = True
    except CadastroProfissional.DoesNotExist:
        context["is_assistencial"] = False

    if request.user.is_authenticated:
        return render(request, 'cadastros/cadastros_index.html', context)
    else:
        return redirect('logout', context=context)
