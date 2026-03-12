from django.core.files.storage import default_storage
from django.forms import formset_factory
from dominios.utils import FilterByStatusMixin, calcular_idade
from django.utils.decorators import method_decorator
from django.template.loader import render_to_string
from django.utils.encoding import smart_str
from django.views.generic import View
from django.shortcuts import get_object_or_404
from django.db.models.functions import ExtractDay, ExtractMonth, ExtractYear
from django.core.serializers.json import DjangoJSONEncoder
from urllib.parse import urlencode
from admin_cadastros.forms import PessoaDetailForm
from admin_cadastros.models import Pessoa, Estabelecimento
from django.db import models
from django.db.models.deletion import ProtectedError
from django.db.models import ProtectedError
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
import json
from datetime import datetime, time, date
from django.utils import timezone
from http.client import HTTPResponse
from smtplib import SMTPResponseException
from django.http import HttpResponseRedirect
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
from .forms import (
    AtasCreateForm, AtasDetailForm, AtasUpdateForm,
)
from .models import Atas
from prontuarios.models import Evolucao
from django_select2.forms import Select2Widget
from django.db import IntegrityError
from django.http import HttpResponse
from django.contrib.admin.sites import AdminSite
from django.shortcuts import render
from django.http import JsonResponse
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.views.generic import ListView
from django.utils.http import urlencode
from datetime import datetime
from .models import Atas
from django.http import FileResponse
from dominios.utils import AccessDenied, FilterObjectsByEstabelecimentoMixin, CustomPermissionRequiredMixin
from django.db.models import F
from django.conf import settings
from django_filters import rest_framework as filters

from admin_faturas.models import Convenio
from dominios.choices import status_choices, tipo_atas_choices
from django import forms
import django_filters
from django_filters import DateFromToRangeFilter
from django_filters.widgets import RangeWidget
from django_select2.forms import Select2Widget

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from prontuarios.views import salvar_pdf_prontuario
from django.core.exceptions import PermissionDenied
from admin_relatorios.utils import RelatorioMixin
from admin_relatorios.models import Relatorio
from django.contrib.contenttypes.models import ContentType


class AtasFilter(filters.FilterSet):
    id = filters.NumberFilter()

    tipo_atas = django_filters.ChoiceFilter(choices=tipo_atas_choices)

    dt_registro = django_filters.DateFilter(method='filter_by_date', widget=forms.DateInput(
        attrs={'type': 'date', 'class': 'datepicker'}))
    dt_atualizacao = django_filters.DateFilter(method='filter_by_date', widget=forms.DateInput(
        attrs={'type': 'date', 'class': 'datepicker'}))

    us_registro = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    us_atualizacao = django_filters.ModelChoiceFilter(
        queryset=User.objects.all())
    status = django_filters.ChoiceFilter(choices=status_choices)

    class Meta:
        model = Atas
        fields = ['id', 'tipo_atas', 'us_registro', 'dt_registro',
                  'us_atualizacao', 'dt_atualizacao', 'status', ]

    def filter_by_date(self, queryset, name, value):
        if isinstance(value, slice):
            # value can be a slice when using DateFromToRangeFilter
            start_date, stop_date = value.start, value.stop

            if start_date and stop_date:
                start_day = datetime.combine(start_date, datetime.min.time())
                start_day = timezone.make_aware(start_day)

                end_day = datetime.combine(stop_date, datetime.max.time())
                end_day = timezone.make_aware(end_day)

                return queryset.filter(**{f'{name}__range': (start_day, end_day)})
        else:
            start_day = datetime.combine(value, datetime.min.time())
            start_day = timezone.make_aware(start_day)

            end_day = datetime.combine(value, datetime.max.time())
            end_day = timezone.make_aware(end_day)

            return queryset.filter(**{f'{name}__range': (start_day, end_day)})


class AtasListView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ListView):
    permission_required = 'atas.view_atas'
    template_name = "atas/atas_listar.html"
    model = Atas
    context_object_name = "atas_listar"
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.GET.copy()

        if 'limpar' in params:
            self.request.session.pop('atas_filters', None)
            params.clear()
        elif any(field in params for field in AtasFilter.Meta.fields):
            self.request.session['atas_filters'] = params
        elif 'atas_filters' in self.request.session:
            params.update(self.request.session['atas_filters'])

        # Definir valor padrão 'A' para o filtro de status
        params.setdefault('status', 'A')
        # Remover parâmetro dt_alta se não estiver definido

        self.filter = AtasFilter(params, queryset=queryset)
        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Atas'
        context['title'] = 'atas_listar'

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('atas_listar')
        context['filter'] = self.filter

        context['is_paginated'] = True

        return context


class AtasCreateView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, CreateView):
    permission_required = 'atas.add_atas'
    template_name = "atas/atas_cadastrar.html"
    form_class = AtasCreateForm
    success_url = reverse_lazy("atas_listar")
    login_url = reverse_lazy('login')
    context_object_name = "atas_cadastrar"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Atas"
        context['title'] = 'atas_cadastrar'

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('atas_listar')

        return context

    def form_valid(self, form):
        if not self.request.user.is_authenticated:
            messages.warning(
                self.request, "Sua sessão expirou. Por favor, faça login novamente.")
            return HttpResponseRedirect(reverse('login'))

        # Atribuir o atendimento e o estabelecimento ao objeto Atas
        atendimento = None
        form.instance.atendimento = atendimento

        pessoa = None
        form.instance.pessoa = pessoa

        estabelecimento_id = self.request.session.get("estabelecimento_id")

        if estabelecimento_id:
            estabelecimento = Estabelecimento.objects.get(
                id=estabelecimento_id)
            form.instance.estabelecimento = estabelecimento
        else:
            messages.error(
                self.request, "Selecione um estabelecimento antes de criar um atendimento.")
            return self.form_invalid(form)

        # Atribuir o usuário logado ao objeto Evolucao
        form.instance.us_registro = self.request.user

        # Salvar o objeto Evolucao
        atas = form.save(commit=False)
        # Salvar para obter um ID
        atas.save()

        # Gerar e salvar PDF, assinado se necessário
        relatorio = salvar_pdf_prontuario(
            self.request.user, atas, assinar=atas.assinar)
        if relatorio:
            messages.success(
                self.request, f"PDF assinado com sucesso! & {settings.MSG_ADD}")
        else:
            messages.warning(
                self.request, f"PDF gerado sem assinatura! & {settings.MSG_ADD}")

        return HttpResponseRedirect(self.success_url)

    def form_invalid(self, form):
        # Verifica se há erro no campo 'ata'
        if 'ata' in form.errors:
            # Captura a mensagem de erro específica
            msg_erro = form.errors['ata'][0]
            # Exibe a mesma mensagem do form
            messages.warning(self.request, msg_erro)

        else:
            messages.warning(
                self.request, 'Verifique as instruções e tente novamente!')

        return super().form_invalid(form)


class AtasUpdateView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, UpdateView):
    permission_required = 'atas.change_atas'
    model = Atas
    form_class = AtasUpdateForm
    template_name = "atas/atas_editar.html"
    success_url = reverse_lazy("atas_listar")
    context_object_name = "atas_editar"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Atas"
        context['title'] = 'atas_editar'

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None
        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('atas_listar')

        return context

    def form_valid(self, form):
        if not self.request.user.is_authenticated:
            messages.warning(
                self.request, "Sua sessão expirou. Por favor, faça login novamente."
            )
            return HttpResponseRedirect(reverse('login'))

        # Atribuir o atendimento e o estabelecimento ao objeto Atas
        atendimento = None
        form.instance.atendimento = atendimento

        pessoa = None
        form.instance.pessoa = pessoa

        estabelecimento_id = self.request.session.get("estabelecimento_id")

        # Atualizar os campos de atualização
        form.instance.us_atualizacao = self.request.user
        form.instance.dt_atualizacao = timezone.now()

        # Salvar o objeto atualizado
        atas = form.save(commit=False)
        atas.save()

        Relatorio.objects.filter(
            content_type=ContentType.objects.get_for_model(self.object),
            object_id=self.object.pk
        ).update(status='I')

        if self.object.status != 'I':
            relatorio = salvar_pdf_prontuario(
                self.request.user, self.object, assinar=self.object.assinar)
            if relatorio:
                messages.success(self.request, "PDF assinado com sucesso!")
            else:
                messages.warning(self.request, "PDF gerado sem assinatura!")

        messages.success(self.request, "Ata atualizada com sucesso.")
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        # Verifica se há erro no campo 'ata'
        if 'ata' in form.errors:
            # Captura a mensagem de erro específica
            msg_erro = form.errors['ata'][0]
            # Exibe a mesma mensagem do form
            messages.warning(self.request, msg_erro)

        else:
            messages.warning(
                self.request, 'Verifique as instruções e tente novamente!')

        return super().form_invalid(form)


class AtasDeleteView(LoginRequiredMixin, FilterObjectsByEstabelecimentoMixin, CustomPermissionRequiredMixin, DeleteView):
    permission_required = 'atas.delete_atas'
    model = Atas
    template_name = "atas/atas_excluir.html"
    success_url = reverse_lazy("atas_listar")

    def post(self, request, *args, **kwargs):
        atas = self.get_object()

        if not request.user.is_authenticated:
            messages.warning(
                request, "Sua sessão expirou. Por favor, faça login novamente.")
            return HttpResponseRedirect(reverse('login'))

        try:
            response = super().post(request, *args, **kwargs)
            messages.success(
                request, f"atas {atas.id} excluído com sucesso.")
            return redirect('atas_listar')
        except ProtectedError:
            messages.error(
                request, f"Erro ao excluir o atas '{atas.id}'. O atas está protegido por referências a outros objetos.")
            return redirect('atas_listar')
        except Exception as e:
            messages.error(
                request, f"Erro ao excluir o atas '{atas.id}': {str(e)}")
            return redirect('atas_listar')
