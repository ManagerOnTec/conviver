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
from atendimentos.forms import PessoaForm
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
    AtendimentoCreateForm, AtendimentoDetailForm, AtendimentoUpdateForm,
)
from .models import Atendimento
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
from .models import Atendimento
from django.http import FileResponse
from dominios.utils import AccessDenied, FilterObjectsByEstabelecimentoMixin, CustomPermissionRequiredMixin
from django.db.models import F
from django.conf import settings
from admin_cadastros.forms import TipoAtendimentoOpForm
from django_filters import rest_framework as filters
from admin_cadastros.models import TipoAtendimento, Cidade
from admin_faturas.models import Convenio
from dominios.choices import status_choices, entidade_encaminha_choices
from django import forms
import django_filters
from django_filters import DateFromToRangeFilter
from django_filters.widgets import RangeWidget
from django_select2.forms import Select2Widget
from dominios.choices import carater_atendimento_choices
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


class AtendimentoFilter(filters.FilterSet):
    id = filters.NumberFilter()
    pessoa = filters.CharFilter(
        field_name='pessoa__nome', lookup_expr='icontains', label='Pessoa'
    )
    tipo_atendimento = filters.ModelChoiceFilter(
        field_name='tipo_atendimento__tipo_atendimento',
        queryset=TipoAtendimento.objects.filter(status='A'), label='Tipo de Atendimento'
    )

    carater_atendimento = django_filters.ChoiceFilter(
        choices=carater_atendimento_choices)

    cidade_encaminhamento = filters.ModelChoiceFilter(
        # Especifique o campo do encaminhamento que deseja filtrar
        field_name='cidade_encaminhamento__cidade',
        queryset=Cidade.objects.all(),
        label='Cidade do Encaminhamento',)

    entidade_encaminhamento = django_filters.ChoiceFilter(
        choices=entidade_encaminha_choices, label='Entidade')

    convenio = filters.ModelChoiceFilter(
        # Especifique o campo da empresa que deseja filtrar
        field_name='convenio__convenio',
        queryset=Convenio.objects.all(), label='Convênio',)

    dt_alta = django_filters.BooleanFilter(method='filter_by_dt_alta', widget=forms.CheckboxInput(
        attrs={'checked': False, 'class': 'mt-2'}), label='Listar as altas?')

    dt_atendimento = DateFromToRangeFilter(
        widget=RangeWidget(attrs={'type': 'date', 'class': 'datepicker rounded p-3', 'style': 'width: 100%; height: 42px'}), label='Dt.Atendimento De/Até')

    dt_registro = django_filters.DateFilter(method='filter_by_date', widget=forms.DateInput(
        attrs={'type': 'date', 'class': 'datepicker'}))
    dt_atualizacao = django_filters.DateFilter(method='filter_by_date', widget=forms.DateInput(
        attrs={'type': 'date', 'class': 'datepicker'}))

    us_registro = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    us_atualizacao = django_filters.ModelChoiceFilter(
        queryset=User.objects.all())
    status = django_filters.ChoiceFilter(choices=status_choices)

    class Meta:
        model = Atendimento
        fields = ['id', 'pessoa', 'tipo_atendimento', 'dt_alta', 'us_registro', 'dt_registro',
                  'us_atualizacao', 'dt_atualizacao', 'status', 'dt_atendimento',]

    def filter_by_dt_alta(self, queryset, name, value):
        if value:
            return queryset.exclude(dt_alta__isnull=True)
        return queryset.filter(dt_alta__isnull=True)

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


class AtendimentoListView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ListView):
    permission_required = 'atendimentos.view_atendimento'
    template_name = "atendimentos/atendimento_listar.html"
    model = Atendimento
    context_object_name = "atendimento_listar"
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.GET.copy()

        if 'limpar' in params:
            self.request.session.pop('atendimento_filters', None)
            params.clear()
        elif any(field in params for field in AtendimentoFilter.Meta.fields):
            self.request.session['atendimento_filters'] = params
        elif 'atendimento_filters' in self.request.session:
            params.update(self.request.session['atendimento_filters'])

        # Definir valor padrão 'A' para o filtro de status
        params.setdefault('status', 'A')
        # Remover parâmetro dt_alta se não estiver definido
        if 'dt_alta' in params and not params['dt_alta']:
            params.pop('dt_alta')

        self.filter = AtendimentoFilter(params, queryset=queryset)
        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Atendimentos'
        context['title'] = 'atendimento_listar'

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('atendimento_listar')
        context['filter'] = self.filter

        context['is_paginated'] = True

        return context


class AtendimentoCreateView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, CreateView):
    permission_required = 'atendimentos.add_atendimento'
    template_name = "atendimentos/atendimento_cadastrar.html"
    form_class = AtendimentoCreateForm
    success_url = reverse_lazy("atendimento_listar")
    login_url = reverse_lazy('login')
    context_object_name = "atendimento_cadastrar"

    def get_initial(self):
        initial = super().get_initial()

        # verifica se o parâmetro success existe na URL
        success = self.request.GET.get('success')
        if success == '1':
            ultima_pessoa = Pessoa.objects.order_by('-id').first()
            if ultima_pessoa:
                initial['pessoa'] = ultima_pessoa.id

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Atendimentos"
        context['title'] = 'atendimento_cadastrar'

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('atendimento_listar')

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['usuario'] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not self.request.user.is_authenticated:
            messages.warning(
                self.request, "Sua sessão expirou. Por favor, faça login novamente.")
            # Substitua 'login' pela sua URL de login
            return HttpResponseRedirect(reverse('login'))

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            estabelecimento = Estabelecimento.objects.get(
                id=estabelecimento_id)
            form.instance.estabelecimento = estabelecimento
        else:
            messages.error(
                self.request, "Selecione um estabelecimento antes de criar um atendimento.")
            return self.form_invalid(form)

        if Atendimento.objects.filter(Q(pessoa=form.cleaned_data['pessoa']) & Q(dt_alta=None, status='A')).exists():
            messages.error(
                self.request, 'Registro não realizado, para novo atendimento gere alta no atendimento anterior')
            return self.form_invalid(form)

        try:
            # Salva o objeto Atendimento sem commit
            self.object = form.save(commit=False)
            self.object.us_registro = self.request.user  # Atribui o usuário da sessão
            self.object.save()  # Faz o commit no banco de dados
            form.save_m2m()  # Salva as relações ManyToMany

            messages.success(self.request, settings.MSG_ADD)
            # Redireciona para a URL de sucesso após salvar corretamente
            return HttpResponseRedirect(self.get_success_url())
        except IntegrityError as e:
            messages.error(
                self.request, 'Registro não realizado, já existe registro desta pessoa')
            return self.form_invalid(form)


class AtendimentoDetailView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, DetailView):
    permission_required = 'atendimentos.view_atendimento'
    model = Atendimento
    template_name = "atendimentos/atendimento_detalhe.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'atendimento_detalhe'

        # Recupere o objeto Pessoa associado ao Atendimento
        pessoa = self.object.pessoa

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['form'] = AtendimentoDetailForm(instance=self.object)
        context['titulo'] = "Atendimentos"
        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('atendimento_listar')

        # Obter os parâmetros de filtro salvos na sessão
        saved_filters = self.request.session.get('atendimento_filters', {})

        if saved_filters:
            # Aplicar o filtro ao queryset de Atendimento
            atendimentos = AtendimentoFilter(
                saved_filters, queryset=Atendimento.objects.filter(estabelecimento_id=estabelecimento_id)).qs
        else:
            # Se não tiver filtro, use o critério do estabelecimento e do status
            atendimentos = Atendimento.objects.filter(
                estabelecimento_id=estabelecimento_id, status='A', dt_alta__isnull=True)

        ##################

        # Obter IDs para botoes anterior e proximo na navegacao do detalhe
        ids_a = atendimentos.values_list('id', flat=True)

        # Obter o índice do objeto atual na lista de IDs
        index = list(ids_a).index(self.object.id)

        # Obter o ID do próximo objeto
        proximo_id = ids_a[index + 1] if index < len(ids_a) - 1 else None

        # Obter o ID do objeto anterior
        objeto_anterior_id = ids_a[index - 1] if index > 0 else None

# Se o objeto atual for o único no filtro, definir próximo e anterior como None
        if len(ids_a) == 1:
            proximo_id = None
            objeto_anterior_id = None

        # Obter o próximo objeto ou None se não existir
        proximo_objeto = Atendimento.objects.filter(
            id=proximo_id).first() if proximo_id else None

        # Obter o objeto anterior ou None se não existir
        objeto_anterior = Atendimento.objects.filter(
            id=objeto_anterior_id).first() if objeto_anterior_id else None

        context['proximo_objeto'] = proximo_objeto
        context['objeto_anterior'] = objeto_anterior
        # fim navegacao detalhe
        # Verificar se os arquivos existem
        context['anexo_um_exists'] = default_storage.exists(
            str(self.object.anexo_um))
        context['anexo_dois_exists'] = default_storage.exists(
            str(self.object.anexo_dois))
        context['anexo_tres_exists'] = default_storage.exists(
            str(self.object.anexo_tres))

        context['diagnostico_encaminhamento'] = self.object.diagnostico_encaminhamento.all()

        return context

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(
                self.request, 'Usuário não liberado para acessar registro de outro estabelecimento')
            return HttpResponseRedirect(reverse_lazy('prontuario_listar'))
        else:
            messages.warning(
                self.request, "Sua sessão expirou. Por favor, faça login novamente.")
            return redirect_to_login(self.request.get_full_path(), 'login')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(
                request, "Sua sessão expirou. Por favor, faça login novamente.")
            return redirect_to_login(self.request.get_full_path(), 'login')

        try:
            return super().dispatch(request, *args, **kwargs)
        except PermissionDenied:
            return self.handle_no_permission()


class AtendimentoUpdateView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, UpdateView):
    permission_required = 'atendimentos.change_atendimento'
    model = Atendimento
    form_class = AtendimentoUpdateForm
    template_name = "atendimentos/atendimento_editar.html"
    success_url = reverse_lazy("atendimento_listar")
    context_object_name = "atendimento_editar"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Atendimentos"
        context['title'] = 'atendimento_editar'

        context['titulo'] = "Atendimentos"
        context['title'] = 'atendimento_editar'

        pessoa = self.object.pessoa

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None
        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('atendimento_listar')
        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        return context

    def form_valid(self, form):

        if form.is_valid():
            form.instance.us_atualizacao = self.request.user
            form.instance.dt_atualizacao = timezone.now()
            response = super().form_valid(form)

            messages.success(self.request, settings.MSG_EDIT)
            return response
        else:
            # Se o formulário for inválido, retorne a resposta adequada aqui, como renderizar o template novamente com os erros.
            return self.form_invalid(form)


class AtendimentoDeleteView(LoginRequiredMixin, FilterObjectsByEstabelecimentoMixin, CustomPermissionRequiredMixin, DeleteView):
    permission_required = 'atendimentos.delete_atendimento'
    model = Atendimento
    template_name = "atendimentos/atendimento_excluir.html"
    success_url = reverse_lazy("atendimento_listar")

    def post(self, request, *args, **kwargs):
        atendimento = self.get_object()

        if not request.user.is_authenticated:
            messages.warning(
                request, "Sua sessão expirou. Por favor, faça login novamente.")
            return HttpResponseRedirect(reverse('login'))

        try:
            response = super().post(request, *args, **kwargs)
            messages.success(
                request, f"Atendimento {atendimento.id} excluído com sucesso.")
            return redirect('atendimento_listar')
        except ProtectedError:
            messages.error(
                request, f"Erro ao excluir o atendimento '{atendimento.id}'. O atendimento está protegido por referências a outros objetos.")
            return redirect('atendimento_listar')
        except Exception as e:
            messages.error(
                request, f"Erro ao excluir o atendimento '{atendimento.id}': {str(e)}")
            return redirect('atendimento_listar')


class PessoaCreateView(LoginRequiredMixin, FilterObjectsByEstabelecimentoMixin, CustomPermissionRequiredMixin, CreateView):
    permission_required = ['atendimentos.add_atendimento']
    template_name = "cadastros/pessoa_cadastrar.html"
    form_class = PessoaForm
    success_url = reverse_lazy("atendimento_cadastrar")
    login_url = reverse_lazy('login')
    context_object_name = "pessoa_cadastrar"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Pessoas'
        context['title'] = 'pessoa_cadastrar'

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('atendimento_listar')

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['usuario'] = self.request.user
        return kwargs

    # Sobrescreve form_valid para tratar o formulário válido.
    def form_valid(self, form):

        # Salvando o objeto Pessoa sem commit para adicionar informações adicionais.
        us = self.request.user

        pessoa = form.save(commit=False)

        pessoa.us_registro = self.request.user

        try:
            pessoa.save()  # Tentativa de salvar o objeto no banco de dados.
            # Mensagem de sucesso se a operação for bem-sucedida.
        except Exception as e:
            # Mensagem de erro se a operação falhar.
            messages.error(self.request, f"Erro ao salvar: {e}")
            return self.form_invalid(form)

        self.success_url = reverse_lazy('atendimento_cadastrar') + '?success=1'
        messages.success(self.request, settings.MSG_ADD)
        return super().form_valid(form)

    def form_invalid(self, form):
        # Exibindo erros do formulário no console para depuração.
        print("Erros do formulário:", form.errors)

        # Você também pode adicionar esses erros como mensagens para o usuário.
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field}: {error}")

        return super().form_invalid(form)


def obter_cidades(request):
    estado_id = request.GET.get('estado_id')
    cidades = Cidade.objects.filter(estado_id=estado_id).values('id', 'cidade')
    return JsonResponse({'cidades': list(cidades)})
