from prontuarios.utils import salvar_pdf_prontuario
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
    OrcamentosCreateForm, OrcamentosDetailForm, OrcamentosUpdateForm,
)
from .models import Orcamentos
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
from .models import Orcamentos
from django.http import FileResponse
from dominios.utils import AccessDenied, FilterObjectsByEstabelecimentoMixin, CustomPermissionRequiredMixin
from django.db.models import F
from django.conf import settings

from django_filters import rest_framework as filters

from dominios.choices import status_choices
from django import forms
import django_filters
from django_filters import DateFromToRangeFilter
from django_filters.widgets import RangeWidget
from django_select2.forms import Select2Widget

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from admin_relatorios.utils import RelatorioMixin
from admin_relatorios.models import Relatorio
from django.contrib.contenttypes.models import ContentType


class OrcamentosFilter(filters.FilterSet):
    id = filters.NumberFilter()

    dt_registro = django_filters.DateFilter(method='filter_by_date', widget=forms.DateInput(
        attrs={'type': 'date', 'class': 'datepicker'}))
    dt_atualizacao = django_filters.DateFilter(method='filter_by_date', widget=forms.DateInput(
        attrs={'type': 'date', 'class': 'datepicker'}))

    us_registro = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    us_atualizacao = django_filters.ModelChoiceFilter(
        queryset=User.objects.all())
    status = django_filters.ChoiceFilter(choices=status_choices)

    class Meta:
        model = Orcamentos
        fields = ['id', 'us_registro', 'dt_registro',
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


class OrcamentosListView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ListView):
    permission_required = 'orcamentos.view_orcamentos'
    template_name = "orcamentos/orcamentos_listar.html"
    model = Orcamentos
    context_object_name = "orcamentos_listar"
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.GET.copy()

        if 'limpar' in params:
            self.request.session.pop('orcamentos_filters', None)
            params.clear()
        elif any(field in params for field in OrcamentosFilter.Meta.fields):
            self.request.session['orcamentos_filters'] = params
        elif 'orcamentos_filters' in self.request.session:
            params.update(self.request.session['orcamentos_filters'])

        # Definir valor padrão 'A' para o filtro de status
        params.setdefault('status', 'A')
        # Remover parâmetro dt_alta se não estiver definido

        self.filter = OrcamentosFilter(params, queryset=queryset)
        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Orçamentos'
        context['title'] = 'orcamentos_listar'

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('orcamentos_listar')
        context['filter'] = self.filter

        context['is_paginated'] = True

        return context


class OrcamentosCreateView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, CreateView):
    permission_required = 'orcamentos.add_orcamentos'
    template_name = "orcamentos/orcamentos_cadastrar.html"
    form_class = OrcamentosCreateForm
    success_url = reverse_lazy("orcamentos_listar")
    login_url = reverse_lazy('login')
    context_object_name = "orcamentos_cadastrar"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Orçamentos"
        context['title'] = 'orcamentos_cadastrar'

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('orcamentos_listar')

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
        orcamentos = form.save(commit=False)
        # Salvar para obter um ID
        orcamentos.save()

        # Gerar e salvar PDF, assinado se necessário
        relatorio = salvar_pdf_prontuario(
            self.request.user, orcamentos, assinar=orcamentos.assinar)
        if relatorio:
            messages.success(
                self.request, f"PDF assinado com sucesso! & {settings.MSG_ADD}")
        else:
            messages.warning(
                self.request, f"PDF gerado sem assinatura! & {settings.MSG_ADD}")

        return HttpResponseRedirect(self.success_url)

    def form_invalid(self, form):
        # Verifica se há erro no campo 'ata'
        if 'orcamento' in form.errors:
            # Captura a mensagem de erro específica
            msg_erro = form.errors['orcamento'][0]
            # Exibe a mesma mensagem do form
            messages.warning(self.request, msg_erro)

        else:
            messages.warning(
                self.request, 'Verifique as instruções e tente novamente!')

        return super().form_invalid(form)


class OrcamentosUpdateView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, UpdateView):
    permission_required = 'orcamentoss.change_orcamentos'
    model = Orcamentos
    form_class = OrcamentosUpdateForm
    template_name = "orcamentos/orcamentos_editar.html"
    success_url = reverse_lazy("orcamentos_listar")
    context_object_name = "orcamentos_editar"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "orcamentos"
        context['title'] = 'orcamentos_editar'

        context['titulo'] = "orcamentoss"
        context['title'] = 'orcamentos_editar'

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None
        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('orcamentos_listar')

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
        orcamentos = form.save(commit=False)
        orcamentos.save()

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

        messages.success(self.request, "Orçamento atualizado com sucesso.")
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        # Verifica se há erro no campo 'ata'
        if 'orcamento' in form.errors:
            # Captura a mensagem de erro específica
            msg_erro = form.errors['orcamento'][0]
            # Exibe a mesma mensagem do form
            messages.warning(self.request, msg_erro)

        else:
            messages.warning(
                self.request, 'Verifique as instruções e tente novamente!')

        return super().form_invalid(form)


class OrcamentosDeleteView(LoginRequiredMixin, FilterObjectsByEstabelecimentoMixin, CustomPermissionRequiredMixin, DeleteView):
    permission_required = 'orcamentos.delete_orcamentos'
    model = Orcamentos
    template_name = "orcamentos/orcamentos_excluir.html"
    success_url = reverse_lazy("orcamentos_listar")

    def post(self, request, *args, **kwargs):
        orcamentos = self.get_object()

        if not request.user.is_authenticated:
            messages.warning(
                request, "Sua sessão expirou. Por favor, faça login novamente.")
            return HttpResponseRedirect(reverse('login'))

        try:
            response = super().post(request, *args, **kwargs)
            messages.success(
                request, f"orcamentos {orcamentos.id} excluído com sucesso.")
            return redirect('orcamentos_listar')
        except ProtectedError:
            messages.error(
                request, f"Erro ao excluir o orcamentos '{orcamentos.id}'. O orcamentos está protegido por referências a outros objetos.")
            return redirect('orcamentos_listar')
        except Exception as e:
            messages.error(
                request, f"Erro ao excluir o orcamentos '{orcamentos.id}': {str(e)}")
            return redirect('orcamentos_listar')
