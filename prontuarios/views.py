from django.views.generic import TemplateView
from django.utils.timezone import make_aware
from django.apps import apps
from admin_cadastros_assistenciais.models import CID
from admin_diagnosticos.models import ParametrosDiagnostico
from admin_passagem_plantao.admin import ParametrosPassagemPlantaoAdmin
from admin_passagem_plantao.models import ParametrosPassagemPlantao, TipoPassagemPlantao
from .models import Adep, Diagnostico, PassagemPlantao, Prescricao
from django.db.models import Count, Prefetch
from django.urls import resolve
from django.http import HttpResponse, QueryDict
from django.db import transaction
from django.core.files.storage import default_storage
from admin_psicoterapia.models import ParametrosPsicoterapia
from .models import Evolucao, Psicoterapia  # Importe o modelo Evolucao
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO
from PyPDF2 import PdfFileReader, PdfFileWriter
from prontuarios.utils import salvar_pdf_prontuario
from django.http import HttpResponse
from django.views.generic.edit import FormView
from cryptography.exceptions import InvalidKey
from dominios.utils import NoneToEmptyMixin, ParametrosProntuariosMixin
from django.urls import path
from django.utils.decorators import method_decorator
from typing import Any
from cryptography.fernet import Fernet
from django.db import models
from admin_adep.models import ParametrosAdep
from admin_estoques.models import Produto
from admin_evolucoes.admin import ParametrosEvolucao
from admin_perdas_ganhos.models import ParametrosPerdasGanhos
from admin_plano_cuidados.models import ParametrosPlanoCuidados
from admin_sinais_vitais.models import ParametrosSinaisVitais
from .models import Adep
from .forms import AdepForm, PassagemPlantaoCreateForm, PassagemPlantaoDetailForm, PsicoterapiaCreateForm, PsicoterapiaDetailForm, PsicoterapiaUpdateForm, SinaisVitaisListForm
from copy import copy
from django.http import HttpResponseRedirect
from django.contrib.auth.views import redirect_to_login
from django.db.models import Prefetch
from django.db.models import Q
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.forms import HiddenInput
from django.urls import reverse, reverse_lazy
from admin_logs.forms import ProntuarioAcessosCreateForm
from admin_prescricoes.models import HorarioRestritoPrescricao, InicioPlanoTerapeutico, IntervaloHoras, ParametrosPrescricao
from prontuarios.models import Prescricao, ProdutoPrescricao
from admin_evolucoes.models import ParametrosEvolucao, TextoPadrao
from dominios.utils import AccessDenied, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, UserIsCreatorMixin, calcular_idade, parametros_prontuarios
from admin_cadastros_assistenciais.models import CadastroProfissional
from admin_cadastros.models import Estabelecimento
from admin_cadastros.forms import PessoaDetailForm
from django.forms import formset_factory
from django.shortcuts import render, redirect
from rest_framework.views import APIView
from django.forms import inlineformset_factory
from .models import Prescricao, ProdutoPrescricao
from admin_sae.models import ParametrosSAE
from admin_cadastros_assistenciais.admin import CadastroProfissional
from .models import Evidencia
from .models import DiagnosticoEnfermagem
from rest_framework import serializers
from admin_sae.models import Aspecto, AspectoAnalisado, Evidencia, DiagnosticoEnfermagem, FatorRelacionado, Intervencao, ParametrosSAE
from django.urls import reverse
from django import forms
from dominios.choices import status_choices, fase_prescricao_choices, fase_adep_choices
from django.contrib.auth.models import User
import django_filters
from django.http import JsonResponse
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from admin_cadastros_assistenciais.models import CadastroProfissional
from admin_evolucoes.models import TipoEvolucao
from .models import SAE, PerdasGanhos, PlanoCuidados, SinaisVitais
from admin_evolucoes.models import TextoPadrao
from django.shortcuts import redirect
from django.views import View
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, View
from atendimentos.forms import AtendimentoDetailForm
from admin_cadastros.forms import PessoaDetailForm, TipoAtendimentoOpForm
from admin_cadastros.models import Pessoa, Estabelecimento, TipoAtendimento
from atendimentos.models import Atendimento
from .models import Evolucao
from .forms import (PerdasGanhosCreateForm, PerdasGanhosDetailForm, PerdasGanhosUpdateForm, EvolucaoCreateForm, EvolucaoDetailForm, EvolucaoUpdateForm, PlanoCuidadosCreateForm, PlanoCuidadosDetailForm, PlanoCuidadosUpdateForm,
                    ProdutoPrescricaoUpForm, SAECreateForm, SAEDetailForm, SAEUpdateForm, SinaisVitaisCreateForm, SinaisVitaisDetailForm, SinaisVitaisUpdateForm, PrescricaoForm, PrescricaoForm, ProdutoPrescricaoForm, DiagnosticoCreateForm, DiagnosticoDetailForm, DiagnosticoUpdateForm)
from django.contrib.auth.decorators import login_required
from dominios.utils import UserIsCreatorMixin, AccessDenied, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, calcular_idade
from django.contrib.auth.mixins import LoginRequiredMixin
from datetime import datetime
from django.utils import timezone
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django_filters import rest_framework as filters
from datetime import datetime
from atendimentos.models import Atendimento
from atendimentos.views import AtendimentoFilter
from django.core.exceptions import PermissionDenied
from admin_relatorios.utils import RelatorioMixin
from admin_relatorios.models import Relatorio
from django.contrib.contenttypes.models import ContentType
from django.db.models import Max
from django.db.models import Subquery, OuterRef

# FIM IMPORTS

# FUNCAO PARA CONCATENAR PDFS POR TIPO E OBJECT ID IGUIS DO MODELO E ABRIR EM TELA - UM OBJETO PK POR VEZ


def combine_pdfs_specific(request, object_id, tipo):
    content_type = ContentType.objects.get(model=tipo.lower())
    relatorios = Relatorio.objects.filter(
        content_type=content_type, object_id=object_id, status='A')

    pdf_paths = [relatorio.relatorio.name for relatorio in relatorios]

    combined_pdf = combine_pdfs(pdf_paths)

    response = HttpResponse(combined_pdf.getvalue(),
                            content_type='application/pdf')
    # Altere 'attachment' por 'inline' para abrir no navegador, ou simplesmente remova essa linha.
    response['Content-Disposition'] = f'inline; filename="{tipo}_report_{object_id}.pdf"'

    return response


# FUNÇÃO PARA JUNTAR PDFS E DISPONIBILIZAR NA DOWNLOAD_FILTERED_PDFS
def combine_pdfs(pdfs):
    pdf_writer = PdfWriter()
    for pdf_path in pdfs:
        if default_storage.exists(pdf_path) and default_storage.size(pdf_path) > 0:
            try:
                with default_storage.open(pdf_path, 'rb') as f:
                    pdf_reader = PdfReader(f)
                    for page in pdf_reader.pages:
                        pdf_writer.add_page(page)
            except Exception as e:
                print(f"Erro ao ler o arquivo PDF {pdf_path}: {e}")
        else:
            print(f"Arquivo não encontrado ou vazio: {pdf_path}")
    output = BytesIO()
    pdf_writer.write(output)
    return output

# DOWNLOAD DOS PDFS FILTRADOS NA SESSAO DAS LISTVIEWS

# TODO: Esta view serve para download dos pdfs de prontuarios, alterar para um gerenciador de relatorios, por tipo e id, atendimento e/ou pessoa


def download_filtered_pdfs(request, atendimento_id, model_name):

    # Define o modelo e o filtro com base em model_name
    if model_name == 'evolucao':
        model = Evolucao
        model_filter = EvolucaoFilter
    elif model_name == 'prescricao':
        model = Prescricao
        model_filter = PrescricaoFilter
    elif model_name == 'diagnostico':
        model = Diagnostico
        model_filter = DiagnosticoFilter
    elif model_name == 'sinais_vitais':
        model = SinaisVitais
        model_filter = SinaisVitaisFilter
    elif model_name == 'sae':
        model = SAE
        model_filter = SAEFilter
    elif model_name == 'plano_cuidados':
        model = PlanoCuidados
        model_filter = PlanoCuidadosFilter
    elif model_name == 'perdas_ganhos':
        model = PerdasGanhos
        model_filter = PerdasGanhosFilter
    else:
        return HttpResponse("Modelo inválido", status=400)

    # Obtém os filtros da sessão, se houver
    session_filters = request.session.get(f'{model_name}_filters', {})
    filters = QueryDict('', mutable=True)
    filters.update(session_filters)
    filters['atendimento_id'] = atendimento_id

    filtered_objects = model_filter(filters, queryset=model.objects.filter(
        atendimento_id=atendimento_id)).qs

    # Obtém os IDs dos objetos filtrados
    object_ids = [obj.id for obj in filtered_objects]

    # Obtém os Relatorios correspondentes aos objetos filtrados
    content_type = ContentType.objects.get_for_model(model)
    relatorios = Relatorio.objects.filter(
        content_type=content_type, object_id__in=object_ids, status='A').order_by('object_id')

    pdf_paths = [relatorio.relatorio.name for relatorio in relatorios]

    # Combina os PDFs em um único documento
    combined_pdf = combine_pdfs(pdf_paths)

    # Prepara a resposta HTTP com o PDF combinado
    response = HttpResponse(combined_pdf.getvalue(),
                            content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{model_name}_combined_report.pdf"'

    return response


class ProntuarioListView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ListView):
    permission_required = 'prontuarios.view_prontuario'
    template_name = "prontuarios/prontuario_listar.html"
    model = Atendimento
    context_object_name = "prontuario_listar"
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
        context['titulo'] = 'Prontuários'
        context['title'] = 'prontuario_listar'

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')
        context['filter'] = self.filter

        context['is_paginated'] = True

        return context


class ProntuarioDetailView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, DetailView):
    permission_required = 'prontuarios.view_prontuario'
    model = Atendimento
    template_name = "prontuarios/prontuario_detalhe.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'prontuario_detalhe'

        # Recupere o objeto Pessoa associado ao Atendimento
        pessoa = self.object.pessoa

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['form'] = AtendimentoDetailForm(instance=self.object)
        context['titulo'] = "Prontuários"
        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)
        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        # Filtra apenas os atendimentos do mesmo estabelecimento com status ativo e ordena por ID
        atendimentos = Atendimento.objects.filter(
            estabelecimento_id=estabelecimento_id, status='A'
        ).order_by('id')

        # Obter a lista de IDs ordenados
        ids_a = list(atendimentos.values_list('id', flat=True))

        # Obter o índice do objeto atual na lista de IDs
        try:
            index = ids_a.index(self.object.id)
        except ValueError:
            index = None

        proximo_id = ids_a[index +
                           1] if index is not None and index < len(ids_a) - 1 else None
        objeto_anterior_id = ids_a[index -
                                   1] if index is not None and index > 0 else None

        # Obter os objetos correspondentes
        proximo_objeto = Atendimento.objects.filter(
            id=proximo_id).first() if proximo_id else None
        objeto_anterior = Atendimento.objects.filter(
            id=objeto_anterior_id).first() if objeto_anterior_id else None

        context['proximo_objeto'] = proximo_objeto
        context['objeto_anterior'] = objeto_anterior

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


class EvolucaoFilter(filters.FilterSet):
    id = django_filters.NumberFilter()
    tipo_evolucao = django_filters.ModelChoiceFilter(
        queryset=TipoEvolucao.objects.all()
    )
    dt_registro = django_filters.DateFilter(
        method='filter_by_date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'datepicker'})
    )
    dt_atualizacao = django_filters.DateFilter(
        method='filter_by_date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'datepicker'})
    )
    us_registro = django_filters.ModelChoiceFilter(
        queryset=User.objects.all()
    )

    us_atualizacao = django_filters.ModelChoiceFilter(
        queryset=User.objects.all()
    )
    status = django_filters.ChoiceFilter(choices=status_choices)

    class Meta:
        model = Evolucao
        fields = ['id', 'tipo_evolucao', 'us_registro', 'dt_registro',
                  'us_atualizacao', 'dt_atualizacao', 'status']

    def filter_by_date(self, queryset, name, value):
        start_day = datetime.combine(value, datetime.min.time())
        start_day = timezone.make_aware(start_day)

        end_day = datetime.combine(value, datetime.max.time())
        end_day = timezone.make_aware(end_day)

        return queryset.filter(**{f'{name}__range': (start_day, end_day)})


class EvolucaoListView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, RelatorioMixin, ListView):
    permission_required = 'prontuarios.view_evolucao'
    template_name = "prontuarios/evolucao_listar.html"
    model = Evolucao
    context_object_name = "evolucao_listar"
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset()
        atendimento_id = self.kwargs.get('atendimento_id')
        queryset = Evolucao.objects.filter(atendimento_id=atendimento_id)

        # Get a mutable copy of the request.GET QueryDict
        params = self.request.GET.copy()

        # If the 'limpar' button was clicked, clear the saved filters in the session
        if 'limpar' in params:
            self.request.session.pop('evolucao_filters', None)
            params.clear()
        # If there are any filters in the GET request, update the saved filters in the session
        elif any(field in params for field in EvolucaoFilter.Meta.fields):
            self.request.session['evolucao_filters'] = params
        # If there are no filters in the GET request but there are saved filters in the session, update the GET request with the saved filters
        elif 'evolucao_filters' in self.request.session:
            params.update(self.request.session['evolucao_filters'])

        # Pass the updated GET request to the filter
        params.setdefault('status', 'A')
        self.filter = EvolucaoFilter(params, queryset=queryset)

        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Prontuários"
        context['title'] = "evolucao_listar"
        context['func'] = 'Evoluções'
        context['atendimento_id'] = self.kwargs['atendimento_id']
        estabelecimento_id = self.request.session.get("estabelecimento_id")
        estabelecimento = Estabelecimento.objects.get(pk=estabelecimento_id)

        # Recupere o objeto Pessoa associado ao Atendimento
        atendimento_id = self.kwargs['atendimento_id']
        atendimento = Atendimento.objects.get(id=atendimento_id)
        pessoa = atendimento.pessoa

        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        context['evolucao'] = None
        evolucoes = self.get_queryset()
        if evolucoes:
            context['evolucao'] = evolucoes[0]

        context['filter'] = self.filter

        context['is_paginated'] = True

        current_filters = self.request.GET or self.request.session.get(
            'evolucao_filters', {})
        disable_button = current_filters.get('status') == 'I'

        # Adiciona a flag de controle no contexto
        context['disable_button'] = disable_button

        return context


class EvolucaoCreateView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ParametrosProntuariosMixin, CreateView):
    permission_required = 'prontuarios.add_evolucao'
    template_name = "prontuarios/evolucao_cadastrar.html"
    form_class = EvolucaoCreateForm
    context_object_name = "evolucao_cadastrar"
    modelo_parametros = ParametrosEvolucao

    def get_success_url(self):
        return reverse_lazy('evolucao_listar', kwargs={'atendimento_id': self.kwargs['atendimento_id'], })

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'user': self.request.user,
            'atendimento': Atendimento.objects.get(pk=self.kwargs.get('atendimento_id')),
            'estabelecimento': Estabelecimento.objects.get(pk=self.request.session.get("estabelecimento_id"))
        })
        return kwargs

    def form_valid(self, form):
        if not self.request.user.is_authenticated:
            messages.warning(
                self.request, "Sua sessão expirou. Por favor, faça login novamente.")
            return HttpResponseRedirect(reverse('login'))

        # Atribuir o atendimento e o estabelecimento ao objeto Evolucao
        atendimento_id = self.kwargs.get('atendimento_id')
        atendimento = Atendimento.objects.get(pk=atendimento_id)
        form.instance.atendimento = atendimento
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
        evolucao = form.save(commit=False)
        # Salvar para obter um ID
        evolucao.save()

        # Gerar e salvar PDF, assinado se necessário
        relatorio = salvar_pdf_prontuario(
            self.request.user, evolucao, assinar=evolucao.assinar)
        if relatorio:
            messages.success(
                self.request, f"PDF assinado com sucesso! & {settings.MSG_ADD}")
        else:
            messages.warning(
                self.request, f"PDF gerado sem assinatura! & {settings.MSG_ADD}")

        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        # Verifica se há erro no campo 'ata'
        if 'evolucao' in form.errors:
            # Captura a mensagem de erro específica
            msg_erro = form.errors['evolucao'][0]
            # Exibe a mesma mensagem do form
            messages.warning(self.request, msg_erro)

        else:
            messages.warning(
                self.request, 'Verifique as instruções e tente novamente!')

        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        atendimento_id = self.kwargs.get('atendimento_id')
        estabelecimento_id = self.request.session.get("estabelecimento_id")
        atendimento = Atendimento.objects.get(
            pk=atendimento_id) if atendimento_id else None
        estabelecimento = Estabelecimento.objects.get(
            pk=estabelecimento_id) if estabelecimento_id else None
        prof = CadastroProfissional.objects.filter(
            profissional=self.request.user, status='A').order_by('-id').first()

        tipo_evolucao_list = []
        tipo_evolucao_padrao = None

        if prof:
            par = ParametrosEvolucao.objects.filter(
                Q(profissao=prof.profissao, estabelecimento=estabelecimento, status='A') |
                Q(profissional=self.request.user,
                  estabelecimento=estabelecimento, status='A')
            ).distinct()

            for obj in par:
                tipo_evolucao_list.extend(list(obj.tipo_evolucao.all()))
                if obj.tipo_evolucao_padrao and obj.tipo_evolucao_padrao in obj.tipo_evolucao.all():
                    tipo_evolucao_padrao = obj.tipo_evolucao_padrao

        if tipo_evolucao_padrao:
            tipo_evolucao_list = [tipo_evolucao_padrao] + \
                [te for te in tipo_evolucao_list if te != tipo_evolucao_padrao]

        context.update({
            'titulo': "Prontuários",
            'title': "Cadastrar Evolução",
            'atendimento_id': atendimento_id,
            'atendimento': atendimento,
            'pessoa_form': PessoaDetailForm(instance=atendimento.pessoa) if atendimento and atendimento.pessoa else None,
            'idade': calcular_idade(atendimento.pessoa.dt_nascimento) if atendimento and atendimento.pessoa and atendimento.pessoa.dt_nascimento else '',
            'estabelecimento': estabelecimento,
            'user': self.request.user,
            'tipo_evolucao_form': tipo_evolucao_list,
            'cad_index': reverse_lazy('cadastros_index'),
            'list_index': reverse_lazy('prontuario_listar'),
        })

        return context

    def dispatch(self, request, *args, **kwargs):
        atendimento_id = self.kwargs.get('atendimento_id')
        atendimento = Atendimento.objects.get(pk=atendimento_id)
        self.kwargs['atendimento'] = atendimento

        # Verificar permissões aqui, em vez de usar `get_object()`
        if not self.has_permission():
            messages.error(
                request, 'Usuário sem permissão ou não autenticado')
            # Redirecione o usuário para a página desejada, por exemplo, a lista de atendimentos
            return HttpResponseRedirect(reverse_lazy('evolucao_listar', kwargs={'atendimento_id': atendimento_id}))

        return super().dispatch(request, *args, **kwargs)


class EvolucaoDetailView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, DetailView):
    permission_required = 'prontuarios.view_evolucao'
    model = Evolucao
    template_name = "prontuarios/evolucao_detalhe.html"
    form_class = EvolucaoDetailForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['evolucao_form'] = EvolucaoDetailForm(instance=self.object)

        # Recupere o objeto Pessoa associado ao Atendimento
        pessoa = self.object.atendimento.pessoa

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = ' '

        context['evolucao_list'] = Evolucao.objects.filter(
            atendimento=self.object.atendimento)

        context['titulo'] = "Prontuários"
        context['title'] = "evolucao_detalhe"
        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        # Obter os parâmetros de filtro salvos na sessão
        saved_filters = self.request.session.get('evolucao_filters', {})

        if saved_filters:
            # Aplicar o filtro ao queryset de Atendimento
            evolucoes = EvolucaoFilter(
                saved_filters, queryset=Evolucao.objects.filter(estabelecimento_id=estabelecimento_id, atendimento=self.object.atendimento)).qs
        else:
            # Se não tiver filtro, use o critério do estabelecimento e do status
            evolucoes = Evolucao.objects.filter(
                estabelecimento_id=estabelecimento_id, atendimento=self.object.atendimento, status='A')

        # Obter IDs para botoes anterior e proximo na navegacao do detalhe
        ids_a = evolucoes.values_list('id', flat=True)

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
        proximo_objeto = Evolucao.objects.filter(
            id=proximo_id).first() if proximo_id else None

        # Obter o objeto anterior ou None se não existir
        objeto_anterior = Evolucao.objects.filter(
            id=objeto_anterior_id).first() if objeto_anterior_id else None

        context['proximo_objeto'] = proximo_objeto
        context['objeto_anterior'] = objeto_anterior
        # fim navegacao detalhe

        context['is_paginated'] = False

        return context


"""
class EvolucaoUpdateView(LoginRequiredMixin, UserIsCreatorMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ParametrosProntuariosMixin, UpdateView):
    permission_required = 'prontuarios.change_evolucao'
    model = Evolucao
    form_class = EvolucaoUpdateForm
    template_name = "prontuarios/evolucao_editar.html"
    success_url = reverse_lazy("evolucao_listar")
    context_object_name = "evolucao_editar"
    modelo_parametros = ParametrosEvolucao

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['data'] = self.request.POST
        return kwargs

    def form_valid(self, form):

        if not self.request.user.is_authenticated:
            messages.warning(
                self.request, "Sua sessão expirou. Por favor, faça login novamente.")
            # substitua 'login' com sua URL de login
            return HttpResponseRedirect(reverse('login'))

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        estabelecimento = Estabelecimento.objects.get(pk=estabelecimento_id)

        form.instance.us_atualizacao = self.request.user
        form.instance.dt_atualizacao = timezone.now()

        if form.is_valid():
            evolucao = form.save(commit=False)

            evolucao.save()

            Relatorio.objects.filter(
                content_type=ContentType.objects.get_for_model(evolucao),
                object_id=evolucao.pk
            ).update(status='I')
            # Salvar para obter um ID

            if not evolucao.status == 'I':
                # Gerar e salvar PDF, assinado se necessário
                relatorio = salvar_pdf_prontuario(
                    self.request.user, evolucao, assinar=evolucao.assinar)
                if relatorio:
                    messages.success(
                        self.request, f"PDF assinado com sucesso!")
                else:
                    messages.warning(
                        self.request, f"PDF gerado sem assinatura!")

            messages.success(self.request, settings.MSG_EDIT)

            return super().form_valid(form)

        else:
            messages.warning(
                self.request, "Verifique as instruções e tente novamente!")
            return super().form_invalid(form)

    def dispatch(self, request, *args, **kwargs):

        try:
            self.object = self.get_object()
            atendimento = self.object.atendimento
            self.kwargs['atendimento'] = atendimento
            return super().dispatch(request, *args, **kwargs)
        except AccessDenied:
            messages.error(
                request, 'Usuário não liberado para acessar registros de outro estabelecimento')
            # Redirecione o usuário para a página desejada, por exemplo, a lista de atendimentos
            return HttpResponseRedirect(reverse_lazy('evolucao_listar', kwargs={'atendimento_id': self.kwargs['atendimento'].id}))

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        atendimento = self.object.atendimento
        self.kwargs['atendimento_id'] = atendimento
        return super().get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('evolucao_listar', kwargs={'atendimento_id': self.kwargs['atendimento'].id, })

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context['atendimento_id'] = self.object.atendimento.id
        context['titulo'] = "Prontuários"
        context['title'] = "evolucao_editar"

        pessoa = self.object.atendimento.pessoa
        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['user'] = self.request.user

        prof = CadastroProfissional.objects.filter(
            profissional=self.request.user, status='A').order_by('-id').first()

        if prof:
            par = ParametrosEvolucao.objects.filter(
                Q(profissao=prof.profissao, estabelecimento=estabelecimento_id, status='A') |
                Q(profissional=prof.profissional,
                  estabelecimento=estabelecimento_id, status='A')
            ).order_by('-id')

        if par.exists():
            tipo_evolucao_list = []
            tipo_evolucao_padrao = None  # Inicializar como None

            for obj in par:
                tipo_evolucao_list.extend(list(obj.tipo_evolucao.all()))

                # Verificar se tipo_evolucao_padrao existe e é igual a algum tipo_evolucao
                if obj.tipo_evolucao_padrao and obj.tipo_evolucao_padrao in obj.tipo_evolucao.all():
                    tipo_evolucao_padrao = obj.tipo_evolucao_padrao

            # Se tipo_evolucao_padrao foi encontrado, movê-lo para o início da lista
            if tipo_evolucao_padrao:
                tipo_evolucao_list.remove(tipo_evolucao_padrao)
                tipo_evolucao_list.insert(0, tipo_evolucao_padrao)

            context['tipo_evolucao_form'] = tipo_evolucao_list

        else:
            context['tipo_evolucao_form'] = []

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        context['is_paginated'] = False

        evolucao = self.object

        evolucao_form = EvolucaoUpdateForm(instance=evolucao)

        context['evolucao_form'] = evolucao_form

        if self.request.method == 'POST':
            context['form'] = EvolucaoUpdateForm(
                self.request.POST, instance=self.object)
        else:
            context['form'] = EvolucaoUpdateForm(instance=self.object)

        return context

    def form_invalid(self, form):
        messages.warning(
            self.request, "Verifique as instruções e tente novamente!")
        # Esta chamada já deve renderizar o formulário com os dados submetidos
        return super(EvolucaoUpdateView, self).form_invalid(form)

"""


class EvolucaoUpdateView(LoginRequiredMixin, UserIsCreatorMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ParametrosProntuariosMixin, UpdateView):
    permission_required = 'prontuarios.change_evolucao'
    model = Evolucao
    form_class = EvolucaoUpdateForm
    template_name = "prontuarios/evolucao_editar.html"
    success_url = reverse_lazy("evolucao_listar")
    context_object_name = "evolucao_editar"
    modelo_parametros = ParametrosEvolucao

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.method == 'POST':
            kwargs['data'] = self.request.POST
        return kwargs

    def form_valid(self, form):
        super().form_valid(form)

        if not self.request.user.is_authenticated:
            messages.warning(
                self.request, "Sua sessão expirou. Por favor, faça login novamente.")
            # substitua 'login' com sua URL de login
            return HttpResponseRedirect(reverse('login'))

        self.object = form.save(commit=False)
        self.object.us_atualizacao = self.request.user
        self.object.dt_atualizacao = timezone.now()
        self.object.save()

        # Atualizar status dos Relatórios relacionados à Evolução
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

        messages.success(self.request, "Evolução atualizada com sucesso.")
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        # Verifica se há erro no campo 'ata'
        if 'evolucao' in form.errors:
            # Captura a mensagem de erro específica
            msg_erro = form.errors['evolucao'][0]
            # Exibe a mesma mensagem do form
            messages.warning(self.request, msg_erro)

        else:
            messages.warning(
                self.request, 'Verifique as instruções e tente novamente!')

        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        atendimento_id = self.object.atendimento.id if self.object and self.object.atendimento else None
        estabelecimento_id = self.request.session.get("estabelecimento_id")

        # Prepara a lista de tipos de evolução com base na profissão ou no profissional e estabelecimento
        prof = CadastroProfissional.objects.filter(
            profissional=self.request.user, status='A').order_by('-id').first()
        tipo_evolucao_list = []
        tipo_evolucao_padrao = None

        if prof:
            par = ParametrosEvolucao.objects.filter(
                Q(profissao=prof.profissao, estabelecimento=estabelecimento_id, status='A') |
                Q(profissional=self.request.user,
                  estabelecimento=estabelecimento_id, status='A')
            ).order_by('-id').distinct()

            for obj in par:
                tipo_evolucao_list.extend(list(obj.tipo_evolucao.all()))
                if obj.tipo_evolucao_padrao and obj.tipo_evolucao_padrao in obj.tipo_evolucao.all():
                    tipo_evolucao_padrao = obj.tipo_evolucao_padrao

        if tipo_evolucao_padrao:
            tipo_evolucao_list = [tipo_evolucao_padrao] + \
                [te for te in tipo_evolucao_list if te != tipo_evolucao_padrao]

        # Atualiza o contexto incluindo a lógica para 'tipo_evolucao_form'
        context.update({
            'atendimento_id': atendimento_id,
            'titulo': "Prontuários",
            'title': "Editar Evolução",
            'pessoa_form': PessoaDetailForm(instance=self.object.atendimento.pessoa) if self.object and self.object.atendimento and self.object.atendimento.pessoa else None,
            'idade': calcular_idade(self.object.atendimento.pessoa.dt_nascimento) if self.object and self.object.atendimento and self.object.atendimento.pessoa and self.object.atendimento.pessoa.dt_nascimento else '',
            'estabelecimento': Estabelecimento.objects.get(pk=estabelecimento_id) if estabelecimento_id else None,
            'user': self.request.user,
            'cad_index': reverse_lazy('cadastros_index'),
            'list_index': reverse_lazy('prontuario_listar'),
            'is_paginated': False,
            # Inclui a lista de tipos de evolução no contexto
            'tipo_evolucao_form': tipo_evolucao_list,
        })

        if self.request.method == 'POST':
            context['form'] = EvolucaoUpdateForm(
                self.request.POST, instance=self.object)
        else:
            context['form'] = EvolucaoUpdateForm(
                instance=self.object)

        return context

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except PermissionDenied:
            messages.error(request, "Acesso negado.")
            return HttpResponseRedirect(reverse_lazy('evolucao_listar', kwargs={'atendimento_id': self.object.atendimento.id}))

    def get_success_url(self):
        # Ajuste para garantir que o redirecionamento considere o atendimento_id corretamente
        return reverse_lazy('evolucao_listar', kwargs={'atendimento_id': self.object.atendimento.id})


class TextoPadraoFiltradoView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            user = self.request.user
            estabelecimento_id = request.session.get('estabelecimento_id')
            print(f"User: {user}, Estabelecimento ID: {estabelecimento_id}")

            # Obtém o único CadastroProfissional para o usuário logado
            prof = CadastroProfissional.objects.get(
                profissional=user, status='A')
            print(f"CadastroProfissional: {prof}")

            # IDs de TipoEvolucao
            te_ids = set()

            # Obtém o ID de CadastroProfissional e Profissao
            if prof:
                prof_id = prof.id
                profissional_id = prof.profissional.id
                profissao_id = prof.profissao.id
            else:
                profissao_id = None
                prof_id = None
            print(
                f"Prof ID: {prof_id}, Profisisonal ID: {profissional_id}, Profissao ID: {profissao_id}")

            # Filtra os ParametrosEvolucao com base no profissional e na profissão
            pars = ParametrosEvolucao.objects.filter(
                Q(profissional=profissional_id, estabelecimento=estabelecimento_id, status='A') |
                Q(profissao=profissao_id,
                  estabelecimento=estabelecimento_id, status='A')
            )
            print(f"ParametrosEvolucao: {pars}")

            # Coleta os IDs de TipoEvolucao
            if pars:
                for par in pars:
                    te_ids.update(
                        par.tipo_evolucao.values_list('id', flat=True))
                print(f"TipoEvolucao IDs: {te_ids}")

            # Inicializa o filtro Q
            query_filter = Q()
            # Adiciona os filtros ao query_filter
            if te_ids:
                query_filter |= Q(tipo_evolucao__id__in=te_ids, status='A')
            if prof_id:
                query_filter |= Q(profissional__id=prof_id, status='A')
            if profissao_id:
                query_filter |= Q(profissao__id=profissao_id, status='A')

            # Filtra os TextoPadrao
            textos_padrao = TextoPadrao.objects.filter(query_filter).values(
                'id', 'descricao', 'texto', 'profissional__profissional', 'profissao__profissao', 'tipo_evolucao__tipo_evolucao'
            )
            print(
                f"te ids: {te_ids}, prof_id: {prof_id}, profissao_id: {profissao_id}, query_filter: {query_filter}")
            print(f"TextoPadrao: {textos_padrao}")

            response_data = list(textos_padrao)
            return JsonResponse(response_data, safe=False)

        except ObjectDoesNotExist as e:
            print(f"Erro ao obter query: {e}")
            return JsonResponse([], safe=False)


class SinaisVitaisFilter(django_filters.FilterSet):
    id = django_filters.NumberFilter()
    temperatura = django_filters.NumberFilter()
    pressao_arterial = django_filters.CharFilter(
        lookup_expr='icontains', label='Pressão Arterial (mmHg)')
    frequencia_cardiaca = django_filters.NumberFilter()
    frequencia_respiratoria = django_filters.NumberFilter()
    saturacao_oxigenio = django_filters.NumberFilter()
    observacoes = django_filters.CharFilter(
        lookup_expr='icontains', label='Observações')
    us_registro = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    dt_registro = django_filters.DateFilter(method='filter_by_date', widget=forms.DateInput(
        attrs={'type': 'date', 'class': 'datepicker'}))
    us_atualizacao = django_filters.ModelChoiceFilter(
        queryset=User.objects.all())
    dt_atualizacao = django_filters.DateFilter(method='filter_by_date', widget=forms.DateInput(
        attrs={'type': 'date', 'class': 'datepicker'}))
    status = django_filters.ChoiceFilter(choices=status_choices)

    class Meta:
        model = SinaisVitais
        fields = ['id', 'temperatura', 'pressao_arterial', 'frequencia_cardiaca',
                  'frequencia_respiratoria', 'saturacao_oxigenio', 'observacoes',
                  'us_registro', 'dt_registro', 'us_atualizacao', 'dt_atualizacao', 'status']

    def filter_by_date(self, queryset, name, value):
        start_day = datetime.combine(value, datetime.min.time())
        start_day = timezone.make_aware(start_day)

        end_day = datetime.combine(value, datetime.max.time())
        end_day = timezone.make_aware(end_day)

        return queryset.filter(**{f'{name}__range': (start_day, end_day)})


class SinaisVitaisListView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ListView):
    permission_required = 'prontuarios.view_sinaisvitais'
    template_name = "prontuarios/sinais_vitais_listar.html"
    model = SinaisVitais
    form_class = SinaisVitaisListForm
    context_object_name = "sinais_vitais_listar"

    paginate_by = 15

    def get_queryset(self):
        atendimento_id = self.kwargs.get('atendimento_id')
        queryset = SinaisVitais.objects.filter(atendimento_id=atendimento_id)

        # Get a mutable copy of the request.GET QueryDict
        params = self.request.GET.copy()

        # If the 'limpar' button was clicked, clear the saved filters in the session
        if 'limpar' in params:
            self.request.session.pop('sinais_vitais_filters', None)
            params.clear()
        # If there are any filters in the GET request, update the saved filters in the session
        elif any(field in params for field in SinaisVitaisFilter.Meta.fields):
            self.request.session['sinais_vitais_filters'] = params
        # If there are no filters in the GET request but there are saved filters in the session, update the GET request with the saved filters
        elif 'sinais_vitais_filters' in self.request.session:
            params.update(self.request.session['sinais_vitais_filters'])

        params.setdefault('status', 'A')
        # Pass the updated GET request to the filter
        self.filter = SinaisVitaisFilter(params, queryset=queryset)

        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Prontuários"
        context['title'] = "sinais_vitais_listar"
        context['func'] = 'Sinais Vitais'
        context['atendimento_id'] = self.kwargs['atendimento_id']
        estabelecimento_id = self.request.session.get("estabelecimento_id")
        estabelecimento = Estabelecimento.objects.get(pk=estabelecimento_id)
        # Recupere o objeto Pessoa associado ao Atendimento
        atendimento_id = self.kwargs['atendimento_id']
        pessoa = Pessoa.objects.get(atendimento__id=atendimento_id)

        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        # Adicione estas linhas
        if context['sinais_vitais_listar']:
            context['sinais_vitais'] = context['sinais_vitais_listar'][0]
        else:
            context['sinais_vitais'] = None

        context['filter'] = self.filter

        us = self.request.user

        context['is_paginated'] = True

        current_filters = self.request.GET or self.request.session.get(
            'sinais_vitais_filters', {})
        disable_button = current_filters.get('status') == 'I'

        # Adiciona a flag de controle no contexto
        context['disable_button'] = disable_button

        return context


class SinaisVitaisCreateView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ParametrosProntuariosMixin, CreateView):
    permission_required = 'prontuarios.add_sinaisvitais'
    template_name = "prontuarios/sinais_vitais_cadastrar.html"
    form_class = SinaisVitaisCreateForm
    context_object_name = "sinais_vitais_cadastrar"
    modelo_parametros = ParametrosSinaisVitais

    def get_success_url(self):
        return reverse_lazy('sinais_vitais_listar', kwargs={'atendimento_id': self.kwargs['atendimento_id'], })

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['request'] = self.request
        atendimento_id = self.kwargs.get('atendimento_id')
        estabelecimento_id = self.request.session.get(
            "estabelecimento_id")  # Obtendo da sessão

        try:
            kwargs['estabelecimento'] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
            kwargs['atendimento'] = Atendimento.objects.get(pk=atendimento_id)
        except ObjectDoesNotExist:
            messages.error(
                self.request, "Estabelecimento ou Atendimento não encontrado.")
            # Tratamento de erro aqui
        return kwargs

    def form_valid(self, form):

        # Atribuir o atendimento ao objeto
        atendimento_id = self.kwargs.get('atendimento_id')
        atendimento = Atendimento.objects.get(pk=atendimento_id)
        estabelecimento_id = self.request.session.get(
            "estabelecimento_id")

        estabelecimento = Estabelecimento.objects.get(pk=estabelecimento_id)
        form.instance.atendimento = atendimento
        form.instance.estabelecimento = estabelecimento
        form.instance.us_registro = self.request.user

        sinais_vitais = form.save(commit=False)
        # Salvar para obter um ID
        sinais_vitais.save()

        relatorio = salvar_pdf_prontuario(
            self.request.user, sinais_vitais, assinar=sinais_vitais.assinar)
        if relatorio:
            messages.success(
                self.request, f"PDF assinado com sucesso! & {settings.MSG_ADD}")
        else:
            messages.warning(
                self.request, f"PDF gerado sem assinatura! & {settings.MSG_ADD}")

        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(
            self.request, 'Preencha todos campos obrigatórios dentro do padrão recomendado!')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Prontuários"
        context['title'] = "sinais_vitais_cadastrar"
        context['atendimento_id'] = self.kwargs.get('atendimento_id')

        atendimento_id = self.kwargs.get('atendimento_id')
        context['atendimento'] = Atendimento.objects.get(pk=atendimento_id)
        pessoa = context['atendimento'].pessoa
        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        if self.object:
            context['sinais_vitais_form'] = SinaisVitaisCreateForm(
                instance=self.object, request=self.request)
        else:
            context['sinais_vitais_form'] = self.get_form()

        estabelecimento_id = self.request.session.get("estabelecimento_id")

        try:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        except ObjectDoesNotExist:
            context["estabelecimento"] = None
            messages.error(self.request, "Estabelecimento não encontrado.")

        context['user'] = self.request.user

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        return context


class SinaisVitaisDetailView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, DetailView):
    permission_required = 'prontuarios.view_sinaisvitais'
    model = SinaisVitais
    template_name = "prontuarios/sinais_vitais_detalhe.html"
    form_class = SinaisVitaisDetailForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['sinais_vitais_form'] = SinaisVitaisDetailForm(
            instance=self.object)

        # Recupere o objeto Pessoa associado ao Atendimento
        pessoa = self.object.atendimento.pessoa

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = ' '

        context['sinais_vitais_list'] = SinaisVitais.objects.filter(
            atendimento=self.object.atendimento)

        context['titulo'] = "Prontuários"
        context['title'] = "sinais_vitais_detalhe"
        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        context['atendimento_id'] = self.object.atendimento_id

        saved_filters = self.request.session.get('sinais_vitais_filters', {})

        if saved_filters:
            # Aplicar o filtro ao queryset de Atendimento
            sinais_vitais = SinaisVitaisFilter(
                saved_filters, queryset=SinaisVitais.objects.filter(estabelecimento_id=estabelecimento_id, atendimento=self.object.atendimento)).qs
        else:
            # Se não tiver filtro, use o critério do estabelecimento e do status
            sinais_vitais = SinaisVitais.objects.filter(
                estabelecimento_id=estabelecimento_id, atendimento=self.object.atendimento, status='A')

        # Obter IDs para botoes anterior e proximo na navegacao do detalhe
        ids_a = sinais_vitais.values_list('id', flat=True)

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
        proximo_objeto = SinaisVitais.objects.filter(
            id=proximo_id).first() if proximo_id else None

        # Obter o objeto anterior ou None se não existir
        objeto_anterior = SinaisVitais.objects.filter(
            id=objeto_anterior_id).first() if objeto_anterior_id else None

        context['proximo_objeto'] = proximo_objeto
        context['objeto_anterior'] = objeto_anterior
        # fim navegacao detalhe
        return context

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(
                self.request, 'Usuário não liberado para acessar registro de outro estabelecimento')
            return HttpResponseRedirect(reverse_lazy('sinais_vitais_listar', kwargs={'atendimento_id': self.kwargs['atendimento'].id}))
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
            self.object = self.get_object()
            atendimento = self.object.atendimento
            self.kwargs['atendimento'] = atendimento
            return super().dispatch(request, *args, **kwargs)
        except PermissionDenied:
            return self.handle_no_permission()
        except AccessDenied:
            messages.error(
                request, 'Usuário não liberado para acessar registros de outro estabelecimento')
            return HttpResponseRedirect(reverse_lazy('sinais_vitais_listar', kwargs={'atendimento_id': self.kwargs['atendimento'].id}))


class SinaisVitaisUpdateView(LoginRequiredMixin, UserIsCreatorMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ParametrosProntuariosMixin, UpdateView):
    permission_required = 'prontuarios.change_sinaisvitais'
    model = SinaisVitais
    form_class = SinaisVitaisUpdateForm
    template_name = "prontuarios/sinais_vitais_editar.html"
    modelo_parametros = ParametrosSinaisVitais

    def get_success_url(self):
        # Aqui estamos usando reverse_lazy com os argumentos de URL necessários
        # Isso deve resolver o problema NoReverseMatch que você está enfrentando.
        return reverse_lazy("sinais_vitais_listar", kwargs={'atendimento_id': self.object.atendimento.id})

    def get_form_kwargs(self):
        kwargs = super(SinaisVitaisUpdateView, self).get_form_kwargs()
        kwargs['request'] = self.request
        kwargs['user'] = self.request.user
        kwargs['estabelecimento'] = self.request.session.get(
            'estabelecimento_id', None)
        return kwargs

    def form_valid(self, form):
        self.object = form.save(commit=False)
        estabelecimento_id = self.request.session.get(
            'estabelecimento_id', None)
        if estabelecimento_id is not None:
            try:
                estabelecimento = Estabelecimento.objects.get(
                    pk=estabelecimento_id)
                self.object.estabelecimento = estabelecimento
            except ObjectDoesNotExist:
                messages.error(self.request, 'Estabelecimento não encontrado.')
                return self.form_invalid(form)

        form.instance.us_atualizacao = self.request.user
        form.instance.dt_atualizacao = timezone.now()

        sinais_vitais = form.save(commit=False)

        sinais_vitais.save()

        Relatorio.objects.filter(
            content_type=ContentType.objects.get_for_model(sinais_vitais),
            object_id=sinais_vitais.pk
        ).update(status='I')
        # Salvar para obter um ID

        if not sinais_vitais.status == 'I':
            # Gerar e salvar PDF, assinado se necessário
            relatorio = salvar_pdf_prontuario(
                self.request.user, sinais_vitais, assinar=sinais_vitais.assinar)
            if relatorio:
                messages.success(
                    self.request, f"PDF assinado com sucesso!")
            else:
                messages.warning(
                    self.request, f"PDF gerado sem assinatura!")

        messages.success(self.request, settings.MSG_EDIT)

        response = super(SinaisVitaisUpdateView, self).form_valid(form)
        return response

    def form_invalid(self, form):
        messages.error(
            self.request, 'Revise campos obrigatórios ou valores informados incorretamente. Ex: Pressão Arterial (120/80)')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Prontuários"
        context['title'] = "sinais_vitais_editar"
        context['sinais_vitais_form'] = SinaisVitaisUpdateForm(
            instance=self.object)
        pessoa = self.object.atendimento.pessoa
        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)
        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None
        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        return context


class PerdasGanhosFilter(django_filters.FilterSet):
    id = django_filters.NumberFilter()
    peso = django_filters.NumberFilter()
    altura = django_filters.NumberFilter()
    dt_registro = django_filters.DateFilter(method='filter_by_date', widget=forms.DateInput(
        attrs={'type': 'date', 'class': 'datepicker'}))
    dt_atualizacao = django_filters.DateFilter(method='filter_by_date', widget=forms.DateInput(
        attrs={'type': 'date', 'class': 'datepicker'}))
    us_registro = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    us_atualizacao = django_filters.ModelChoiceFilter(
        queryset=User.objects.all())
    status = django_filters.ChoiceFilter(choices=status_choices)

    class Meta:
        model = PerdasGanhos
        fields = ['id', 'peso', 'altura', 'us_registro', 'dt_registro',
                  'us_atualizacao', 'dt_atualizacao', 'status']

    def filter_by_date(self, queryset, name, value):
        start_day = datetime.combine(value, datetime.min.time())
        start_day = timezone.make_aware(start_day)

        end_day = datetime.combine(value, datetime.max.time())
        end_day = timezone.make_aware(end_day)

        return queryset.filter(**{f'{name}__range': (start_day, end_day)})


class PerdasGanhosListView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ListView):
    permission_required = 'prontuarios.view_perdasganhos'
    template_name = "prontuarios/perdas_ganhos_listar.html"
    model = PerdasGanhos
    context_object_name = "perdas_ganhos_listar"
    paginate_by = 15

    def get_queryset(self):
        atendimento_id = self.kwargs.get('atendimento_id')
        queryset = PerdasGanhos.objects.filter(atendimento_id=atendimento_id)

        # Get a mutable copy of the request.GET QueryDict
        params = self.request.GET.copy()

        # If the 'limpar' button was clicked, clear the saved filters in the session
        if 'limpar' in params:
            self.request.session.pop('perdas_ganhos_filters', None)
            params.clear()
        # If there are any filters in the GET request, update the saved filters in the session
        elif any(field in params for field in PerdasGanhosFilter.Meta.fields):
            self.request.session['perdas_ganhos_filters'] = params
        # If there are no filters in the GET request but there are saved filters in the session, update the GET request with the saved filters
        elif 'perdas_ganhos_filters' in self.request.session:
            params.update(self.request.session['perdas_ganhos_filters'])

        params.setdefault('status', 'A')
        # Pass the updated GET request to the filter
        self.filter = PerdasGanhosFilter(params, queryset=queryset)

        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Prontuários"
        context['title'] = "perdas_ganhos_listar"
        context['func'] = 'Perdas e Ganhos'
        context['atendimento_id'] = self.kwargs['atendimento_id']
        estabelecimento_id = self.request.session.get("estabelecimento_id")
        estabelecimento = Estabelecimento.objects.get(pk=estabelecimento_id)
        # Recupere o objeto Pessoa associado ao Atendimento
        atendimento_id = self.kwargs['atendimento_id']
        pessoa = Pessoa.objects.get(atendimento__id=atendimento_id)

        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        # Adicione estas linhas
        if context['perdas_ganhos_listar']:
            context['perdas_ganhos'] = context['perdas_ganhos_listar'][0]
        else:
            context['perdas_ganhos'] = None

        context['filter'] = self.filter

        context['is_paginated'] = True

        current_filters = self.request.GET or self.request.session.get(
            'perdas_ganhos_filters', {})
        disable_button = current_filters.get('status') == 'I'

        # Adiciona a flag de controle no contexto
        context['disable_button'] = disable_button

        return context


class PerdasGanhosCreateView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ParametrosProntuariosMixin, CreateView):
    permission_required = 'prontuarios.add_perdasganhos'
    template_name = "prontuarios/perdas_ganhos_cadastrar.html"
    form_class = PerdasGanhosCreateForm
    context_object_name = "perdas_ganhos_cadastrar"
    modelo_parametros = ParametrosPerdasGanhos

    def get_success_url(self):
        return reverse_lazy('perdas_ganhos_listar', kwargs={'atendimento_id': self.kwargs['atendimento_id'], })

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        atendimento_id = self.kwargs.get('atendimento_id')
        kwargs['atendimento'] = Atendimento.objects.get(pk=atendimento_id)

        return kwargs

    def form_valid(self, form):
        if not self.request.user.is_authenticated:
            messages.warning(
                self.request, "Sua sessão expirou. Por favor, faça login novamente.")
            # substitua 'login' com sua URL de login
            return HttpResponseRedirect(reverse('login'))

        # Atribuir o atendimento ao objeto
        atendimento_id = self.kwargs.get('atendimento_id')
        atendimento = Atendimento.objects.get(pk=atendimento_id)
        form.instance.atendimento = atendimento

        # Atribuir o estabelecimento da sessão ao objeto Atendimento
        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            estabelecimento = Estabelecimento.objects.get(
                id=estabelecimento_id)
            form.instance.estabelecimento = estabelecimento
        else:
            messages.error(
                self.request, "Selecione um estabelecimento antes de criar um atendimento.")
            return self.form_invalid(form)

        form.instance.us_registro = self.request.user

        if not parametros_prontuarios(self.request.user, estabelecimento, ParametrosPerdasGanhos):
            messages.error(
                self.request, 'Você não tem permissão, contate o administrador do sistema!')
            return self.form_invalid(form)

        perdas_ganhos = form.save()

        # Gerar e salvar PDF, assinado se necessário
        relatorio = salvar_pdf_prontuario(
            self.request.user, perdas_ganhos, assinar=perdas_ganhos.assinar)
        if relatorio:
            messages.success(
                self.request, "PDF assinado com sucesso! & " + settings.MSG_ADD)
        else:
            messages.warning(
                self.request, "PDF gerado sem assinatura! & " + settings.MSG_ADD)

        return super().form_valid(form)

    def form_invalid(self, form):
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Prontuários"
        context['title'] = "perdas_ganhos_cadastrar"
        context['atendimento_id'] = self.kwargs.get('atendimento_id')

        atendimento_id = self.kwargs.get('atendimento_id')
        context['atendimento'] = Atendimento.objects.get(pk=atendimento_id)
        pessoa = context['atendimento'].pessoa
        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        context['perdas_ganhos_form'] = PerdasGanhosCreateForm(
            instance=self.object, request=self.request)

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['user'] = self.request.user

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')
        context['func'] = 'Perdas e Ganhos'

        return context


class PerdasGanhosDetailView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, DetailView):
    permission_required = 'prontuarios.view_perdasganhos'
    model = PerdasGanhos
    template_name = "prontuarios/perdas_ganhos_detalhe.html"
    form_class = PerdasGanhosDetailForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['perdas_ganhos_form'] = PerdasGanhosDetailForm(
            instance=self.object)

        # Recupere o objeto Pessoa associado ao Atendimento
        pessoa = self.object.atendimento.pessoa

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = ' '

        context['perdas_ganhos_list'] = PerdasGanhos.objects.filter(
            atendimento=self.object.atendimento)

        context['titulo'] = "Prontuários"
        context['title'] = "perdas_ganhos_detalhe"
        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        context['atendimento_id'] = self.object.atendimento_id

        saved_filters = self.request.session.get('perdas_ganhos_filters', {})

        if saved_filters:
            # Aplicar o filtro ao queryset de Atendimento
            perdas_ganhos = PerdasGanhosFilter(
                saved_filters, queryset=PerdasGanhos.objects.filter(estabelecimento_id=estabelecimento_id, atendimento=self.object.atendimento)).qs
        else:
            # Se não tiver filtro, use o critério do estabelecimento e do status
            perdas_ganhos = PerdasGanhos.objects.filter(
                estabelecimento_id=estabelecimento_id, atendimento=self.object.atendimento, status='A')

        # Obter IDs para botoes anterior e proximo na navegacao do detalhe
        ids_a = perdas_ganhos.values_list('id', flat=True)

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
        proximo_objeto = PerdasGanhos.objects.filter(
            id=proximo_id).first() if proximo_id else None

        # Obter o objeto anterior ou None se não existir
        objeto_anterior = PerdasGanhos.objects.filter(
            id=objeto_anterior_id).first() if objeto_anterior_id else None

        context['proximo_objeto'] = proximo_objeto
        context['objeto_anterior'] = objeto_anterior
        # fim navegacao detalhe
        context['func'] = 'Perdas e Ganhos'
        return context

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(
                self.request, 'Usuário não liberado para acessar registro de outro estabelecimento')
            return HttpResponseRedirect(reverse_lazy('sinais_vitais_listar', kwargs={'atendimento_id': self.kwargs['atendimento'].id}))
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
            self.object = self.get_object()
            atendimento = self.object.atendimento
            self.kwargs['atendimento'] = atendimento
            return super().dispatch(request, *args, **kwargs)
        except PermissionDenied:
            return self.handle_no_permission()
        except AccessDenied:
            messages.error(
                request, 'Usuário não liberado para acessar registros de outro estabelecimento')
            return HttpResponseRedirect(reverse_lazy('perdas_ganhos_listar', kwargs={'atendimento_id': self.kwargs['atendimento'].id}))


class PerdasGanhosUpdateView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, UserIsCreatorMixin, ParametrosProntuariosMixin, UpdateView):
    permission_required = 'prontuarios.change_perdasganhos'
    model = PerdasGanhos
    form_class = PerdasGanhosUpdateForm
    template_name = "prontuarios/perdas_ganhos_editar.html"
    success_url = reverse_lazy("perdas_ganhos_listar")
    context_object_name = "perdas_ganhos_editar"
    modelo_parametros = ParametrosPerdasGanhos

    atendimento_id = None  # Adicionado como atributo da classe

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Prontuários"
        context['title'] = "perdas_ganhos_editar"
        context['perdas_ganhos_form'] = PerdasGanhosUpdateForm(
            instance=self.object)
        pessoa = self.object.atendimento.pessoa
        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None
        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        return context

    def form_valid(self, form):
        if not self.request.user.is_authenticated:
            messages.warning(
                self.request, "Sua sessão expirou. Por favor, faça login novamente.")
            # substitua 'login' com sua URL de login
            return HttpResponseRedirect(reverse('login'))

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        estabelecimento = Estabelecimento.objects.get(pk=estabelecimento_id)

        if not parametros_prontuarios(self.request.user, estabelecimento, ParametrosPerdasGanhos):
            messages.error(
                self.request, 'Você não tem permissão, contate o administrador do sistema!')
            return self.form_invalid(form)

        form.instance.us_atualizacao = self.request.user
        form.instance.dt_atualizacao = timezone.now()

        perdas_ganhos = form.save()

        Relatorio.objects.filter(
            content_type=ContentType.objects.get_for_model(perdas_ganhos),
            object_id=perdas_ganhos.pk
        ).update(status='I')

        if not perdas_ganhos.status == 'I':

            # Gerar e salvar PDF, assinado se necessário
            relatorio = salvar_pdf_prontuario(
                self.request.user, perdas_ganhos, assinar=perdas_ganhos.assinar)
            if relatorio:
                messages.success(
                    self.request, "PDF assinado com sucesso!")
            else:
                messages.warning(
                    self.request, "PDF gerado sem assinatura!")

        messages.success(self.request, settings.MSG_EDIT)

        response = super().form_valid(form)
        return response

    def form_invalid(self, form):
        print("Form data:", form.data)
        print("Form errors:", form.errors)
        return super().form_invalid(form)

    def dispatch(self, request, *args, **kwargs):
        self.atendimento_id = self.kwargs.get('atendimento_id')
        try:
            return super().dispatch(request, *args, **kwargs)
        except AccessDenied:
            messages.error(
                request, 'Usuário não liberado para acessar registros de outro estabelecimento')
            # Redirecione o usuário para a página desejada, por exemplo, a lista de atendimentos
            return HttpResponseRedirect(reverse_lazy('perdas_ganhos_listar'))

    def get_success_url(self):
        return reverse_lazy("perdas_ganhos_listar", kwargs={'atendimento_id': self.object.atendimento.id})


class PlanoCuidadosFilter(django_filters.FilterSet):
    id = django_filters.NumberFilter()
    dt_registro = django_filters.DateFilter(
        field_name='dt_registro',
        label='Data de Criação',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'datepicker'}),
        method='filter_by_date'
    )
    dt_atualizacao = django_filters.DateFilter(
        field_name='dt_atualizacao',
        label='Data de Atualização',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'datepicker'}),
        method='filter_by_date'
    )
    us_registro = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    us_atualizacao = django_filters.ModelChoiceFilter(
        queryset=User.objects.all())
    status = django_filters.ChoiceFilter(choices=status_choices)

    class Meta:
        model = PlanoCuidados
        fields = ['id', 'turnos', 'humor', 'dt_registro',
                  'dt_atualizacao', 'us_registro', 'us_atualizacao', 'status']

    def filter_by_date(self, queryset, name, value):
        start_day = datetime.combine(value, datetime.min.time())
        start_day = timezone.make_aware(start_day)

        end_day = datetime.combine(value, datetime.max.time())
        end_day = timezone.make_aware(end_day)

        return queryset.filter(**{f'{name}__range': (start_day, end_day)})


class PlanoCuidadosListView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ListView):
    permission_required = 'prontuarios.view_planocuidados'
    template_name = "prontuarios/plano_cuidados_listar.html"
    model = PlanoCuidados
    context_object_name = "plano_cuidados_listar"

    paginate_by = 15

    def get_queryset(self):
        atendimento_id = self.kwargs.get('atendimento_id')
        queryset = PlanoCuidados.objects.filter(atendimento_id=atendimento_id)

        # Get a mutable copy of the request.GET QueryDict
        params = self.request.GET.copy()

        # If the 'limpar' button was clicked, clear the saved filters in the session
        if 'limpar' in params:
            self.request.session.pop('plano_cuidados_filters', None)
            params.clear()
        # If there are any filters in the GET request, update the saved filters in the session
        elif any(field in params for field in PlanoCuidadosFilter.Meta.fields):
            self.request.session['plano_cuidados_filters'] = params
        # If there are no filters in the GET request but there are saved filters in the session, update the GET request with the saved filters
        elif 'plano_cuidados_filters' in self.request.session:
            params.update(self.request.session['plano_cuidados_filters'])

        params.setdefault('status', 'A')

        # Pass the updated GET request to the filter
        self.filter = PlanoCuidadosFilter(params, queryset=queryset)

        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Prontuários"
        context['title'] = "plano_cuidados_listar"
        context['func'] = 'Plano de Cuidados'
        context['atendimento_id'] = self.kwargs['atendimento_id']
        estabelecimento_id = self.request.session.get("estabelecimento_id")
        estabelecimento = Estabelecimento.objects.get(pk=estabelecimento_id)

        # Recupere o objeto Pessoa associado ao Atendimento
        atendimento_id = self.kwargs['atendimento_id']
        pessoa = Pessoa.objects.get(atendimento__id=atendimento_id)

        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        # Adicione estas linhas
        if context['plano_cuidados_listar']:
            context['plano_cuidados'] = context['plano_cuidados_listar'][0]
        else:
            context['plano_cuidados'] = None

        context['filter'] = self.filter

        us = self.request.user

        context['is_paginated'] = True

        current_filters = self.request.GET or self.request.session.get(
            'plano_cuidados_filters', {})
        disable_button = current_filters.get('status') == 'I'

        # Adiciona a flag de controle no contexto
        context['disable_button'] = disable_button

        return context


class PlanoCuidadosCreateView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ParametrosProntuariosMixin, CreateView):
    permission_required = 'prontuarios.add_planocuidados'
    template_name = "prontuarios/plano_cuidados_cadastrar.html"
    form_class = PlanoCuidadosCreateForm
    context_object_name = "plano_cuidados_cadastrar"
    modelo_parametros = ParametrosPlanoCuidados

    def get_success_url(self):
        return reverse_lazy('plano_cuidados_listar', kwargs={'atendimento_id': self.kwargs['atendimento_id'], })

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        atendimento_id = self.kwargs.get('atendimento_id')
        kwargs['atendimento'] = Atendimento.objects.get(pk=atendimento_id)

        return kwargs

    def form_valid(self, form):
        if not self.request.user.is_authenticated:
            messages.warning(
                self.request, "Sua sessão expirou. Por favor, faça login novamente.")
            # substitua 'login' com sua URL de login
            return HttpResponseRedirect(reverse('login'))
        # Atribuir o atendimento ao objeto
        atendimento_id = self.kwargs.get('atendimento_id')
        atendimento = Atendimento.objects.get(pk=atendimento_id)
        form.instance.atendimento = atendimento

        # Atribuir o estabelecimento da sessão ao objeto Atendimento
        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            estabelecimento = Estabelecimento.objects.get(
                id=estabelecimento_id)
            form.instance.estabelecimento = estabelecimento
        else:
            messages.error(
                self.request, "Selecione um estabelecimento antes de criar um atendimento.")
            return self.form_invalid(form)

        form.instance.us_registro = self.request.user

        if not parametros_prontuarios(self.request.user, estabelecimento, ParametrosPlanoCuidados):
            messages.error(
                self.request, 'Você não tem permissão, contate o administrador do sistema!')
            return self.form_invalid(form)

        plano_cuidados = form.save()

        # Gerar e salvar PDF, assinado se necessário
        relatorio = salvar_pdf_prontuario(
            self.request.user, plano_cuidados, assinar=plano_cuidados.assinar)
        if relatorio:
            messages.success(
                self.request, "PDF assinado com sucesso! & " + settings.MSG_ADD)
        else:
            messages.warning(
                self.request, "PDF gerado sem assinatura! & " + settings.MSG_ADD)

        return super().form_valid(form)

    def form_invalid(self, form):
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Prontuários"
        context['title'] = "plano_cuidados_cadastrar"
        context['atendimento_id'] = self.kwargs.get('atendimento_id')

        atendimento_id = self.kwargs.get('atendimento_id')
        context['atendimento'] = Atendimento.objects.get(pk=atendimento_id)
        pessoa = context['atendimento'].pessoa
        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        context['plano_cuidados_form'] = PlanoCuidadosCreateForm(
            instance=self.object, request=self.request)

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['user'] = self.request.user

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        return context


class PlanoCuidadosDetailView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, DetailView):
    permission_required = 'prontuarios.view_planocuidados'
    model = PlanoCuidados
    template_name = "prontuarios/plano_cuidados_detalhe.html"
    form_class = PlanoCuidadosDetailForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['plano_cuidados_form'] = PlanoCuidadosDetailForm(
            instance=self.object)

        # Recupere o objeto Pessoa associado ao Atendimento
        pessoa = self.object.atendimento.pessoa

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = ' '

        context['perdas_ganhos_list'] = PlanoCuidados.objects.filter(
            atendimento=self.object.atendimento)

        context['titulo'] = "Prontuários"
        context['title'] = "plano_cuidados_detalhe"
        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        context['atendimento_id'] = self.object.atendimento_id

        saved_filters = self.request.session.get('plano_cuidados_filters', {})

        if saved_filters:
            # Aplicar o filtro ao queryset de Atendimento
            plano_cuidados = PlanoCuidadosFilter(
                saved_filters, queryset=PlanoCuidados.objects.filter(estabelecimento_id=estabelecimento_id, atendimento=self.object.atendimento)).qs
        else:
            # Se não tiver filtro, use o critério do estabelecimento e do status
            plano_cuidados = PlanoCuidados.objects.filter(
                estabelecimento_id=estabelecimento_id, atendimento=self.object.atendimento, status='A')

        # Obter IDs para botoes anterior e proximo na navegacao do detalhe
        ids_a = plano_cuidados.values_list('id', flat=True)

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
        proximo_objeto = PlanoCuidados.objects.filter(
            id=proximo_id).first() if proximo_id else None

        # Obter o objeto anterior ou None se não existir
        objeto_anterior = PlanoCuidados.objects.filter(
            id=objeto_anterior_id).first() if objeto_anterior_id else None

        context['proximo_objeto'] = proximo_objeto
        context['objeto_anterior'] = objeto_anterior
        # fim navegacao detalhe
        return context

    def dispatch(self, request, *args, **kwargs):

        try:
            self.object = self.get_object()
            atendimento = self.object.atendimento
            self.kwargs['atendimento'] = atendimento
            return super().dispatch(request, *args, **kwargs)
        except PermissionDenied:
            return self.handle_no_permission()
        except AccessDenied:
            messages.error(
                request, 'Usuário não liberado para acessar registros de outro estabelecimento')
            return HttpResponseRedirect(reverse_lazy('plano_cuidados_listar', kwargs={'atendimento_id': self.kwargs['atendimento'].id}))


class PlanoCuidadosUpdateView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, UserIsCreatorMixin, ParametrosProntuariosMixin, UpdateView):
    permission_required = 'prontuarios.change_planocuidados'
    model = PlanoCuidados
    form_class = PlanoCuidadosUpdateForm
    template_name = "prontuarios/plano_cuidados_editar.html"
    success_url = reverse_lazy("plano_cuidados_listar")
    context_object_name = "plano_cuidados_editar"
    modelo_parametros = ParametrosPlanoCuidados

    atendimento_id = None  # Adicionado como atributo da classe

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Prontuários"
        context['title'] = "plano_cuidados_editar"
        context['plano_cuidados_form'] = PlanoCuidadosUpdateForm(
            instance=self.object)
        pessoa = self.object.atendimento.pessoa
        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None
        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        return context

    def form_valid(self, form):
        if not self.request.user.is_authenticated:
            messages.warning(
                self.request, "Sua sessão expirou. Por favor, faça login novamente.")
            # substitua 'login' com sua URL de login
            return HttpResponseRedirect(reverse('login'))
        # Verifica se o usuário atual é o mesmo que criou o registro

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        estabelecimento = Estabelecimento.objects.get(pk=estabelecimento_id)

        if not parametros_prontuarios(self.request.user, estabelecimento, ParametrosPlanoCuidados):
            messages.error(
                self.request, 'Você não tem permissão, contate o administrador do sistema!')
            return self.form_invalid(form)

        form.instance.us_atualizacao = self.request.user
        form.instance.dt_atualizacao = timezone.now()

        plano_cuidados = form.save()

        Relatorio.objects.filter(
            content_type=ContentType.objects.get_for_model(plano_cuidados),
            object_id=plano_cuidados.pk
        ).update(status='I')

        if not plano_cuidados.status == 'I':

            # Gerar e salvar PDF, assinado se necessário
            relatorio = salvar_pdf_prontuario(
                self.request.user, plano_cuidados, assinar=plano_cuidados.assinar)
            if relatorio:
                messages.success(
                    self.request, "PDF assinado com sucesso!")
            else:
                messages.warning(
                    self.request, "PDF gerado sem assinatura!")

        messages.success(self.request, settings.MSG_EDIT)

        response = super().form_valid(form)
        return response

    def form_invalid(self, form):
        print("Form data:", form.data)
        print("Form errors:", form.errors)
        return super().form_invalid(form)

    def dispatch(self, request, *args, **kwargs):
        # Definindo o valor de atendimento_id
        self.atendimento_id = self.kwargs.get('atendimento_id')
        try:
            return super().dispatch(request, *args, **kwargs)
        except AccessDenied:
            messages.error(
                request, 'Usuário não liberado para acessar registros de outro estabelecimento')
            # Redirecione o usuário para a página desejada, por exemplo, a lista de atendimentos
            return HttpResponseRedirect(reverse_lazy('plano_cuidados_listar'))

    def get_success_url(self):
        return reverse_lazy("plano_cuidados_listar", kwargs={'atendimento_id': self.object.atendimento.id})


class SAEFilter(django_filters.FilterSet):
    id = django_filters.NumberFilter()
    aspecto = django_filters.ModelChoiceFilter(
        queryset=Aspecto.objects.filter(status='A'), label='Aspecto')
    aspecto_analisado = django_filters.ModelChoiceFilter(
        queryset=AspectoAnalisado.objects.filter(status='A'), label='Aspecto Analisado')
    evidencia = django_filters.ModelMultipleChoiceFilter(
        queryset=Evidencia.objects.filter(status='A'), label='Evidências')
    diagnostico_enfermagem = django_filters.ModelChoiceFilter(
        queryset=DiagnosticoEnfermagem.objects.filter(status='A'), label='Diagnosticos de Enfermagem')
    fator_relacionado = django_filters.ModelMultipleChoiceFilter(
        queryset=FatorRelacionado.objects.filter(status='A'), label='Fatores Relacionados')
    intervencao = django_filters.ModelMultipleChoiceFilter(
        queryset=Intervencao.objects.filter(status='A'), label='Intervenções')

    dt_registro = django_filters.DateFilter(method='filter_by_date', widget=forms.DateInput(
        attrs={'type': 'date', 'class': 'datepicker'}))

    dt_atualizacao = django_filters.DateFilter(method='filter_by_date', widget=forms.DateInput(
        attrs={'type': 'date', 'class': 'datepicker'}))

    us_registro = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    us_atualizacao = django_filters.ModelChoiceFilter(
        queryset=User.objects.all())
    status = django_filters.ChoiceFilter(choices=status_choices)

    class Meta:
        model = SAE
        fields = ['id', 'aspecto', 'aspecto_analisado', 'evidencia', 'diagnostico_enfermagem', 'fator_relacionado', 'intervencao', 'dt_registro',
                  'dt_atualizacao', 'us_registro', 'us_atualizacao', 'status']

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


class SAEListView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ListView):
    permission_required = 'prontuarios.view_sae'
    template_name = "prontuarios/sae_listar.html"
    model = SAE
    context_object_name = "sae_listar"
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset()
        atendimento_id = self.kwargs.get('atendimento_id')
        queryset = SAE.objects.filter(atendimento_id=atendimento_id)

        # Get a mutable copy of the request.GET QueryDict
        params = self.request.GET.copy()

        # If the 'limpar' button was clicked, clear the saved filters in the session
        if 'limpar' in params:
            self.request.session.pop('sae_filters', None)
            params.clear()
        # If there are any filters in the GET request, update the saved filters in the session
        elif any(field in params for field in SAEFilter.Meta.fields):
            self.request.session['sae_filters'] = params
        # If there are no filters in the GET request but there are saved filters in the session, update the GET request with the saved filters
        elif 'sae_filters' in self.request.session:
            params.update(self.request.session['sae_filters'])

        params.setdefault('status', 'A')

        # Pass the updated GET request to the filter
        self.filter = SAEFilter(params, queryset=queryset)

        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Prontuários"
        context['title'] = "sae_listar"
        context['func'] = 'SAE'
        context['atendimento_id'] = self.kwargs['atendimento_id']
        estabelecimento_id = self.request.session.get("estabelecimento_id")
        estabelecimento = Estabelecimento.objects.get(pk=estabelecimento_id)

        # Recupere o objeto Pessoa associado ao Atendimento
        atendimento_id = self.kwargs['atendimento_id']
        atendimento = Atendimento.objects.get(id=atendimento_id)
        pessoa = atendimento.pessoa

        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        context['sae'] = None
        saes = self.get_queryset()
        if saes:
            context['sae'] = saes[0]

        context['filter'] = self.filter

        context['is_paginated'] = True

        current_filters = self.request.GET or self.request.session.get(
            'sae_filters', {})
        disable_button = current_filters.get('status') == 'I'

        # Adiciona a flag de controle no contexto
        context['disable_button'] = disable_button

        return context


class SAECreateView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ParametrosProntuariosMixin, CreateView):
    permission_required = 'prontuarios.add_sae'
    template_name = "prontuarios/sae_cadastrar.html"
    form_class = SAECreateForm
    context_object_name = "sae_cadastrar"
    modelo_parametros = ParametrosSAE

    def get_success_url(self):
        return reverse_lazy('sae_listar', kwargs={'atendimento_id': self.kwargs['atendimento_id'], })

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        atendimento_id = self.kwargs.get('atendimento_id')
        kwargs['atendimento'] = Atendimento.objects.get(pk=atendimento_id)

        return kwargs

    def form_valid(self, form):
        if not self.request.user.is_authenticated:
            messages.warning(
                self.request, "Sua sessão expirou. Por favor, faça login novamente.")
            return HttpResponseRedirect(reverse('login'))

        try:
            # Atribuir o atendimento ao objeto SAE
            atendimento_id = self.kwargs.get('atendimento_id')
            atendimento = Atendimento.objects.get(pk=atendimento_id)
            form.instance.atendimento = atendimento
            form.instance.us_registro = self.request.user

            # Atribuir o estabelecimento da sessão ao objeto SAE
            estabelecimento_id = self.request.session.get("estabelecimento_id")
            if estabelecimento_id:
                estabelecimento = Estabelecimento.objects.get(
                    id=estabelecimento_id)
                form.instance.estabelecimento = estabelecimento
            else:
                raise ValueError(
                    "Selecione um estabelecimento antes de criar um atendimento.")

            # Salvar o objeto SAE no banco de dados
            instance = form.save()

            # Configurar relacionamentos ManyToMany
            instance.evidencia.set(form.cleaned_data['evidencia'])
            instance.fator_relacionado.set(
                form.cleaned_data['fator_relacionado'])
            instance.intervencao.set(form.cleaned_data['intervencao'])
            instance.save()

            sae = instance

            # Gerar e salvar PDF, assinado se necessário
            relatorio = salvar_pdf_prontuario(
                self.request.user, sae, assinar=sae.assinar)
            if relatorio:
                messages.success(
                    self.request, "PDF assinado com sucesso! & " + settings.MSG_ADD)
            else:
                messages.warning(
                    self.request, "PDF gerado sem assinatura! & " + settings.MSG_ADD)

        except Exception as e:
            messages.error(
                self.request, f'Erro ao processar o formulário: {e}')
            return self.form_invalid(form)

        return super().form_valid(form)

    def form_invalid(self, form):

        cleaned_data = form.cleaned_data

        # Mantém os dados em tela
        self.object = None
        context = self.get_context_data(form=form, cleaned_data=cleaned_data)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Prontuários"
        context['title'] = "sae_cadastrar"
        context['atendimento_id'] = self.kwargs.get('atendimento_id')

        atendimento_id = self.kwargs.get('atendimento_id')
        context['atendimento'] = Atendimento.objects.get(pk=atendimento_id)
        pessoa = context['atendimento'].pessoa
        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        context['sae_form'] = SAECreateForm(
            instance=self.object, request=self.request)

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['user'] = self.request.user

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        return context


class SAEDetailView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, DetailView):
    permission_required = 'prontuarios.view_sae'
    model = SAE
    template_name = "prontuarios/sae_detalhe.html"
    form_class = SAEDetailForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['sae_form'] = SAEDetailForm(instance=self.object)

        # Recupere o objeto Pessoa associado ao Atendimento
        pessoa = self.object.atendimento.pessoa

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = ' '

        context['sae_list'] = SAE.objects.filter(
            atendimento=self.object.atendimento)

        context['titulo'] = "Prontuários"
        context['title'] = "sae_detalhe"
        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        context['atendimento_id'] = self.object.atendimento_id

        saved_filters = self.request.session.get('sae_filters', {})

        if saved_filters:
            sae = SAEFilter(saved_filters, queryset=SAE.objects.filter(
                estabelecimento_id=estabelecimento_id, atendimento=self.object.atendimento)).qs

        else:
            sae = SAE.objects.filter(
                estabelecimento_id=estabelecimento_id, status='A', atendimento=self.object.atendimento)

        # Obter IDs para botoes anterior e proximo na navegacao do detalhe
        ids_a = sae.values_list('id', flat=True)

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
        proximo_objeto = SAE.objects.filter(
            id=proximo_id).first() if proximo_id else None

        # Obter o objeto anterior ou None se não existir
        objeto_anterior = SAE.objects.filter(
            id=objeto_anterior_id).first() if objeto_anterior_id else None

        context['proximo_objeto'] = proximo_objeto
        context['objeto_anterior'] = objeto_anterior
        # fim navegacao deta

        context['evidencias'] = self.object.evidencia.all()
        context['fatores_relacionados'] = self.object.fator_relacionado.all()
        context['intervencoes'] = self.object.intervencao.all()

        return context

    def dispatch(self, request, *args, **kwargs):

        try:
            self.object = self.get_object()
            atendimento = self.object.atendimento
            self.kwargs['atendimento'] = atendimento
            return super().dispatch(request, *args, **kwargs)
        except PermissionDenied:
            return self.handle_no_permission()
        except AccessDenied:
            messages.error(
                request, 'Usuário não liberado para acessar registros de outro estabelecimento')
            return HttpResponseRedirect(reverse_lazy('sae_listar', kwargs={'atendimento_id': self.kwargs['atendimento'].id}))


class SAEUpdateView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, UserIsCreatorMixin, ParametrosProntuariosMixin, UpdateView):
    permission_required = 'prontuarios.change_sae'
    model = SAE
    form_class = SAEUpdateForm
    template_name = "prontuarios/sae_editar.html"
    success_url = reverse_lazy("sae_listar")
    context_object_name = "sae_editar"
    modelo_parametros = ParametrosSAE

    atendimento_id = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Prontuários"
        context['title'] = "plano_cuidados_editar"
        context['sae_form'] = SAEUpdateForm(
            instance=self.object,
            request=self.request,
            user=self.request.user,
        )
        pessoa = self.object.atendimento.pessoa
        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)
        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None
        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        return context

    def form_valid(self, form):
        if not self.request.user.is_authenticated:
            messages.warning(
                self.request, "Sua sessão expirou. Por favor, faça login novamente.")
            # substitua 'login' com sua URL de login
            return HttpResponseRedirect(reverse('login'))

        instance = form.save(commit=False)
        instance.us_atualizacao = self.request.user
        instance.dt_atualizacao = timezone.now()
        instance.save()

        sae = instance

        Relatorio.objects.filter(
            content_type=ContentType.objects.get_for_model(sae),
            object_id=sae.pk
        ).update(status='I')

        if not sae.status == 'I':

            # Gerar e salvar PDF, assinado se necessário
            relatorio = salvar_pdf_prontuario(
                self.request.user, sae, assinar=sae.assinar)
            if relatorio:
                messages.success(
                    self.request, "PDF assinado com sucesso!")
            else:
                messages.warning(
                    self.request, "PDF gerado sem assinatura!")

        messages.success(self.request, settings.MSG_EDIT)
        return super().form_valid(form)

    def form_invalid(self, form):
        response = super().form_invalid(form)
        if self.request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse(form.errors, status=400)
        else:
            print(form.errors)
            return response

    def get_success_url(self):
        return reverse_lazy("sae_listar", kwargs={'atendimento_id': self.object.atendimento.id})

    def dispatch(self, request, *args, **kwargs):

        try:
            self.object = self.get_object()
            atendimento = self.object.atendimento
            self.kwargs['atendimento'] = atendimento
            return super().dispatch(request, *args, **kwargs)
        except PermissionDenied:
            return self.handle_no_permission()
        except AccessDenied:
            messages.error(
                request, 'Usuário não liberado para acessar registros de outro estabelecimento')
            return HttpResponseRedirect(reverse_lazy('sae_listar', kwargs={'atendimento_id': self.kwargs['atendimento'].id}))


class DiagnosticoEnfermagemSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiagnosticoEnfermagem
        fields = ['id', 'descricao']


class IntervencaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Intervencao
        fields = ['id', 'descricao']


class EvidenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evidencia
        fields = ['id', 'descricao']


def get_aspecto_analisado(request):
    aspecto_id = request.GET.get('aspecto_id')
    if aspecto_id:
        aspecto_analisado = AspectoAnalisado.objects.filter(
            aspecto_id=aspecto_id, status='A').values('id', 'descricao')
    else:
        aspecto_analisado = AspectoAnalisado.objects.none()
    return JsonResponse(list(aspecto_analisado), safe=False)


def get_evidencia(request):
    aspecto_analisado_id = request.GET.get('aspecto_analisado_id')
    if aspecto_analisado_id:
        evidencias = Evidencia.objects.filter(
            aspecto_analisado_id=aspecto_analisado_id, status='A')
    else:
        evidencias = Evidencia.objects.none()
    serializer = EvidenciaSerializer(evidencias, many=True)
    return JsonResponse(serializer.data, safe=False)


def get_diagnostico_enfermagem(request):
    evidencia_id = request.GET.get('evidencia_id')
    if evidencia_id:
        evidencias = Evidencia.objects.filter(status='A',
                                              id__in=[int(e) for e in evidencia_id.split(',')])
        diagnosticos = DiagnosticoEnfermagem.objects.filter(
            evidencia__in=evidencias, status='A').distinct()
    else:
        diagnosticos = DiagnosticoEnfermagem.objects.none()
    diagnostico_serializer = DiagnosticoEnfermagemSerializer(
        diagnosticos, many=True)
    return JsonResponse(diagnostico_serializer.data, safe=False)


def get_evidencia_by_diagnostico(request):
    diagnostico_id = request.GET.get('diagnostico_id')
    if diagnostico_id:
        diagnostico = DiagnosticoEnfermagem.objects.get(
            id=diagnostico_id, status='A')  # Aqui mudei de filter para get
        # Adicionei o filtro de status aqui também
        evidencias = diagnostico.evidencia.filter(status='A')
    else:
        evidencias = Evidencia.objects.none()
    evidencia_serializer = EvidenciaSerializer(evidencias, many=True)
    return JsonResponse(evidencia_serializer.data, safe=False)


def get_fator_relacionado(request):
    diagnostico_id = request.GET.get('diagnostico_id')
    if diagnostico_id:
        fatores = FatorRelacionado.objects.filter(
            diagnostico_enfermagem_id=diagnostico_id, status='A').values('id', 'descricao')
    else:
        fatores = FatorRelacionado.objects.none()
    return JsonResponse(list(fatores), safe=False)


def get_intervencao(request):
    fator_id = request.GET.get('fator_id')
    if fator_id:
        fator_ids = fator_id.split(',')
        intervencoes = Intervencao.objects.filter(status='A',
                                                  fator_relacionado_id__in=[int(id) for id in fator_ids])
    else:
        intervencoes = Intervencao.objects.none()
    serializer = IntervencaoSerializer(intervencoes, many=True)
    return JsonResponse(serializer.data, safe=False)


class ProntuarioAcessosCreateView(CreateView):
    form_class = ProntuarioAcessosCreateForm
    template_name = 'prontuarios/prontuario_acessos.html'  # Substitua pelo seu template
    success_url = reverse_lazy('prontuario_listar')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Acesso justificado!')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Prontuários"
        context['title'] = "prontuario_acessos"
        context['atendimento_id'] = self.kwargs.get('atendimento_id')

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['user'] = self.request.user

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_acessos')

        return context


class PrescricaoFilter(filters.FilterSet):
    id = django_filters.NumberFilter()

    dt_registro = django_filters.DateFilter(
        method='filter_by_date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'datepicker'})
    )
    dt_atualizacao = django_filters.DateFilter(
        method='filter_by_date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'datepicker'})
    )
    us_registro = django_filters.ModelChoiceFilter(
        queryset=User.objects.all()
    )

    us_atualizacao = django_filters.ModelChoiceFilter(
        queryset=User.objects.all()
    )
    fase = django_filters.ChoiceFilter(choices=fase_prescricao_choices)
    status = django_filters.ChoiceFilter(choices=status_choices)

    class Meta:
        model = Prescricao
        fields = ['id', 'us_registro', 'dt_registro',
                  'us_atualizacao', 'dt_atualizacao', 'status']

    def filter_by_date(self, queryset, name, value):
        start_day = datetime.combine(value, datetime.min.time())
        start_day = timezone.make_aware(start_day)

        end_day = datetime.combine(value, datetime.max.time())
        end_day = timezone.make_aware(end_day)

        return queryset.filter(**{f'{name}__range': (start_day, end_day)})


class PrescricaoListView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, RelatorioMixin, ListView):
    permission_required = 'prontuarios.view_prescricao'
    template_name = "prontuarios/prescricao_listar.html"
    model = Prescricao
    context_object_name = "prescricao_listar"
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset()
        atendimento_id = self.kwargs.get('atendimento_id')

        # Aplicar filtros iniciais para evitar consultar todos os objetos do modelo
        queryset = Prescricao.objects.filter(
            atendimento_id=atendimento_id)

        # Get a mutable copy of the request.GET QueryDict
        params = self.request.GET.copy()

        # If the 'limpar' button was clicked, clear the saved filters in the session
        if 'limpar' in params:
            self.request.session.pop('prescricao_filters', None)
            params.clear()
        # If there are any filters in the GET request, update the saved filters in the session
        elif any(field in params for field in PrescricaoFilter.Meta.fields):
            self.request.session['prescricao_filters'] = params
        # If there are no filters in the GET request but there are saved filters in the session, update the GET request with the saved filters
        elif 'prescricao_filters' in self.request.session:
            params.update(self.request.session['prescricao_filters'])

        # Pass the updated GET request to the filter
        params.setdefault('status', 'A')
        params.setdefault('fase', 'U')
        self.filter = PrescricaoFilter(params, queryset=queryset)

        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Prontuários"
        context['title'] = "prescricao_listar"
        context['func'] = 'Prescrições'
        context['atendimento_id'] = self.kwargs['atendimento_id']
        estabelecimento_id = self.request.session.get("estabelecimento_id")
        estabelecimento = Estabelecimento.objects.get(
            pk=estabelecimento_id)

        # Recupere o objeto Pessoa associado ao Atendimento
        atendimento_id = self.kwargs['atendimento_id']
        atendimento = Atendimento.objects.get(id=atendimento_id)
        pessoa = atendimento.pessoa

        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        context['prescricao'] = None
        prescricoes = self.get_queryset()
        if prescricoes:
            context['prescricao'] = prescricoes[0]

        context['prescricao_listar'] = self.get_queryset()

        context['filter'] = self.filter

        context['is_paginated'] = True

        current_filters = self.request.GET or self.request.session.get(
            'prescricao_filters', {})
        disable_button = current_filters.get('status') == 'I'

        # Adiciona a flag de controle no contexto
        context['disable_button'] = disable_button

        return context


class PrescricaoGeralListView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, RelatorioMixin, ListView):
    permission_required = 'prontuarios.change_prescricao'
    template_name = "prontuarios/prescricao_geral_listar.html"
    model = Prescricao
    context_object_name = "prescricao_listar"
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset()
        atendimento_id = self.kwargs.get('atendimento_id')

        # Se atendimento_id for fornecido, filtra as prescrições por ele, senão, retorna todas
        if atendimento_id:
            queryset = queryset.filter(atendimento_id=atendimento_id)
        else:
            queryset = Prescricao.objects.all()

        # Ordenação pela data final mais recente
        queryset = queryset.order_by('-dt_final')

        # Get a mutable copy of the request.GET QueryDict
        params = self.request.GET.copy()

        if 'limpar' in params:
            self.request.session.pop('prescricao_filters', None)
            params.clear()
        elif any(field in params for field in PrescricaoFilter.Meta.fields):
            self.request.session['prescricao_filters'] = params
        elif 'prescricao_filters' in self.request.session:
            params.update(self.request.session['prescricao_filters'])

        params.setdefault('status', 'A')
        params.setdefault('fase', 'U')
        self.filter = PrescricaoFilter(params, queryset=queryset)

        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Gestão de Prescrições"
        context['title'] = "prescricao_geral_listar"
        context['func'] = 'Gestão de Prescrições'
        atendimento_id = self.kwargs.get('atendimento_id', None)
        estabelecimento_id = self.request.session.get("estabelecimento_id")

        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        if atendimento_id:
            atendimento = Atendimento.objects.get(id=atendimento_id)
            pessoa = atendimento.pessoa
            context['pessoa_form'] = PessoaDetailForm(instance=pessoa)
            context['idade'] = calcular_idade(
                pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '
            context['atendimento_id'] = atendimento_id
        else:
            context['pessoa_form'] = None
            context['idade'] = None
            context['atendimento_id'] = None

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        context['prescricao'] = None
        prescricoes = self.get_queryset()
        if prescricoes:
            context['prescricao'] = prescricoes[0]

        context['prescricao_listar'] = prescricoes
        context['filter'] = self.filter
        context['is_paginated'] = True

        current_filters = self.request.GET or self.request.session.get(
            'prescricao_filters', {})
        disable_button = current_filters.get('status') == 'I'

        context['disable_button'] = disable_button

        return context


PrescricaoProdutoFormSet = inlineformset_factory(
    Prescricao,
    ProdutoPrescricao,
    form=ProdutoPrescricaoForm,
    fields=('produto', 'intervalo_horas', 'hora_inicio_produto',
            'se_necessario', 'dose_unica', 'observacao'),
    extra=1,
    can_delete=True
)

PrescricaoProdutoUpFormSet = inlineformset_factory(
    Prescricao,
    ProdutoPrescricao,
    form=ProdutoPrescricaoUpForm,
    fields=('produto', 'intervalo_horas', 'hora_inicio_produto',
            'se_necessario', 'dose_unica', 'observacao'),
    extra=0,
    can_delete=True
)
###########################


class PrescricaoCreateView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ParametrosProntuariosMixin, CreateView):
    permission_required = 'prontuarios.add_prescricao'
    template_name = "prontuarios/prescricao_cadastrar.html"
    form_class = PrescricaoForm
    context_object_name = "prescricao_cadastrar"
    modelo_parametros = ParametrosPrescricao

    def get_success_url(self):
        return reverse_lazy('prescricao_listar', kwargs={'atendimento_id': self.kwargs['atendimento_id'], })

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        try:
            atendimento_id = self.kwargs.get('atendimento_id')
            atendimento = Atendimento.objects.get(pk=atendimento_id)
        except ObjectDoesNotExist:
            return redirect('prontuarios:prontuario_listar')

        kwargs['user'] = self.request.user
        kwargs['atendimento'] = atendimento
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        atendimento_id = self.kwargs.get('atendimento_id')
        estabelecimento_id = self.request.session.get("estabelecimento_id")

        with transaction.atomic():
            prescricao = form.save(commit=False)
            prescricao.atendimento = Atendimento.objects.get(pk=atendimento_id)
            prescricao.us_registro = self.request.user
            prescricao.us_prescricao_inicial = self.request.user

            if estabelecimento_id:
                prescricao.estabelecimento = Estabelecimento.objects.get(
                    pk=estabelecimento_id)

            # add salvamento fora do if self validate
            # prescricao.save()
            # add geracao do pdf e assinatura
            # Log para depuração

            ##################################################

            formset = PrescricaoProdutoFormSet(
                self.request.POST, instance=prescricao)
            if self._validate_and_save_formset(formset, atendimento_id):
                prescricao.save()
                formset.save()
                # messages.success(self.request, settings.MSG_ADD)

                response = super().form_valid(form)

                relatorio = salvar_pdf_prontuario(
                    self.request.user, prescricao, assinar=prescricao.assinar)
                if relatorio:
                    messages.success(
                        self.request, f"PDF assinado com sucesso! & {settings.MSG_ADD}")
                else:
                    messages.warning(
                        self.request, f"PDF gerado sem assinatura!  & {settings.MSG_ADD}")
                return response
            else:
                return self.form_invalid(form)

    def _validate_and_save_formset(self, formset, atendimento_id):
        if formset.is_valid():
            for formset_form in formset:
                produto = formset_form.instance.produto
                formset_form.instance.us_registro = self.request.user
            formset.save(commit=False)

            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Prontuários"
        context['title'] = "prescricao_cadastrar"
        atendimento_id = self.kwargs.get('atendimento_id')
        context['atendimento_id'] = atendimento_id
        self.request.session['atendimento_id'] = atendimento_id
        context['atendimento'] = Atendimento.objects.get(pk=atendimento_id)
        pessoa = context['atendimento'].pessoa
        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)
        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '
        context['prescricao_form'] = PrescricaoForm(
            instance=self.object, request=self.request)
        estabelecimento_id = self.request.session.get("estabelecimento_id")
        context["estabelecimento"] = Estabelecimento.objects.get(
            pk=estabelecimento_id) if estabelecimento_id else None
        context['user'] = self.request.user

        if self.request.POST:
            context['form'] = self.form_class(self.request.POST)
            context['formset'] = PrescricaoProdutoFormSet(
                self.request.POST, instance=self.object, form_kwargs={'request': self.request})
        else:
            context['form'] = self.form_class(initial={
                                              'atendimento': context['atendimento'], 'estabelecimento': context['estabelecimento']})
            context['formset'] = PrescricaoProdutoFormSet(
                instance=Prescricao())

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')
        return context

    def form_invalid(self, form):
        print("Formulário principal é inválido. Erros:")
        for field, errors in form.errors.items():
            print(f"Campo {field}: {errors}")
            for error in errors:
                messages.error(self.request, f"{error}")

        context = self.get_context_data()
        formset = context['formset']

        if not formset.is_valid():

            for form_error in formset.errors:
                for field, errors in form_error.items():
                    messages.error(self.request, f"{errors}")

        return super().form_invalid(form)


####################################################
# PRESCRICAO UPDATE VIEW
class PrescricaoUpdateView(LoginRequiredMixin, CustomPermissionRequiredMixin,  CreateView):
    permission_required = 'prontuarios.add_prescricao'
    template_name = "prontuarios/prescricao_editar.html"
    form_class = PrescricaoForm
    context_object_name = "prescricao_editar"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        prescricao_anterior = self.get_prescricao_anterior()

        # Verifique se o campo específico tem valor 'S' ou 'F'
        if prescricao_anterior.fase in ['S', 'F']:
            # Desabilita todos os campos do formulário
            for field_name in form.fields:
                form.fields[field_name].disabled = True

        return form

    def post(self, request, *args, **kwargs):
        prescricao_anterior = self.get_prescricao_anterior()

        # Se a prescrição não pode ser editada, redirecione para outra página
        if prescricao_anterior.fase in ['S', 'F']:
            messages.error(
                request, "Prescricoes suspensas ou finalizadas nao podem ser editadas.")
            return redirect(self.get_success_url())

        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        kwargs.update({
            'request': self.request,
            'user': self.request.user,
        })

        # Certifique-se de que self.request não é None antes de acessar 'session'
        if self.request is not None:
            kwargs['request'] = self.request
        return kwargs

    def get_success_url(self):
        prescricao_anterior = self.get_prescricao_anterior()
        atendimento_id = prescricao_anterior.atendimento.id
        return reverse_lazy('prescricao_listar', kwargs={'atendimento_id': atendimento_id})

    def get_prescricao_anterior(self):
        return get_object_or_404(Prescricao, pk=self.kwargs.get('pk'))

    def get_initial(self):
        initial = super().get_initial()
        prescricao_anterior = self.get_prescricao_anterior()

        # Pegando o usuário logado atualmente
        current_user = self.request.user

        # Loop pelos campos do modelo e atualize os valores iniciais
        for field in Prescricao._meta.fields:
            # Exclui 'id' e 'us_registro' dos campos iniciais
            if field.name not in ['id', 'us_registro']:
                initial[field.name] = getattr(prescricao_anterior, field.name)

        # Atribui o usuário logado a 'us_registro'
        initial['us_registro'] = current_user

        # Atribuir valores iniciais a partir do formulário se eles existem
        form_initial = self.form_class(initial=self.initial).initial
        for field in form_initial:
            if field not in initial:
                initial[field] = form_initial[field]

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        prescricao_anterior = self.get_prescricao_anterior()
        initial_data = self.get_initial()
        # Não existe mais hora inicio, ver como tratar esse inicio do update
        dt_inicio = initial_data.get('dt_inicio')
        initial_formset_data = [{'dt_inicio': dt_inicio} for _ in range(5)]

        if self.request.POST:
            context['formset'] = PrescricaoProdutoUpFormSet(self.request.POST)
        else:
            context['formset'] = PrescricaoProdutoUpFormSet(
                instance=prescricao_anterior, initial=initial_formset_data)

        estabelecimento = self.request.session.get("estabelecimento_id")

        context['atendimento'] = initial_data.get('atendimento')
        context['atendimento_id'] = prescricao_anterior.atendimento.id
        context['estabelecimento'] = initial_data.get('estabelecimento')
        context['estabelecimento_id'] = prescricao_anterior.estabelecimento.id

        pessoa = context['atendimento'].pessoa
        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)
        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '
        context['titulo'] = "Prontuários"
        context['title'] = "prescricao_editar"
        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        context['prescricao_anterior_id'] = prescricao_anterior.id

        return context

    def form_valid(self, form):
        if not self.request.user.is_authenticated:
            messages.warning(
                self.request, "Sua sessão expirou. Por favor, faça login novamente.")
            return HttpResponseRedirect(reverse('login'))

        context = self.get_context_data()
        formset = context['formset']

        estabelecimento = self.request.session.get("estabelecimento_id")

        if formset.is_valid():
            prescricao_anterior = self.get_prescricao_anterior()
            prescricao_anterior.us_atualizacao = self.request.user
            prescricao_anterior.dt_atualizacao = timezone.now()
            prescricao_anterior.fase = "S"
            prescricao_anterior.save()

            prescricao = form.save(commit=False)
            prescricao.atendimento = prescricao_anterior.atendimento
            prescricao.estabelecimento = prescricao_anterior.estabelecimento
            prescricao.us_prescricao_inicial = prescricao_anterior.us_prescricao_inicial
            prescricao.us_registro = self.request.user
            prescricao.prescricao_anterior_id = prescricao_anterior.id
            prescricao.save()

            for formset_form in formset:
                produto_prescricao = formset_form.save(commit=False)
                produto_prescricao.prescricao = prescricao
                produto_prescricao.atendimento = prescricao.atendimento
                produto_prescricao.estabelecimento = prescricao.estabelecimento
                produto_prescricao.us_registro = self.request.user
                produto_prescricao.save()

            response = super().form_valid(form)

            relatorio = salvar_pdf_prontuario(
                self.request.user, prescricao, assinar=prescricao.assinar)
            if relatorio:
                # messages.success(self.request, settings.MSG_EDIT)
                messages.success(
                    self.request, f"PDF assinado com sucesso! & {settings.MSG_EDIT}")
            else:
                messages.warning(
                    self.request, f"PDF gerado sem assinatura! & {settings.MSG_EDIT}")
            return response
        else:
            return self.form_invalid(form)

    def form_invalid(self, form):
        # print("Formulário principal é inválido. Erros:")
        for field, errors in form.errors.items():
            # print(f"Campo {field}: {errors}")
            for error in errors:
                messages.error(self.request, f"{error}")

        context = self.get_context_data()
        formset = context['formset']

        if not formset.is_valid():
            # print("Formset é inválido. Erros:")
            for form_error in formset.errors:
                for field, errors in form_error.items():
                    messages.error(self.request, f"{errors}")

        return super().form_invalid(form)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Sua sessão expirou!')
            return HttpResponseRedirect(reverse('logout'))

        # Obtenha o objeto 'prescricao_anterior' para verificar a permissão
        prescricao_anterior = self.get_prescricao_anterior()
        atendimento_id = prescricao_anterior.atendimento.id

        # Verifique se o 'us_registro' do objeto 'prescricao_anterior' é igual ao usuário logado
        if prescricao_anterior.us_registro != request.user:
            # Obtenha o profissional associado ao usuário logado
            try:
                profissional = CadastroProfissional.objects.get(
                    profissional=request.user, status='A')
            except CadastroProfissional.DoesNotExist:
                profissional = None

            # Verifique se o profissional ou a profissão tem permissão para editar
            if profissional:
                estabelecimento_id = request.session.get("estabelecimento_id")
                parametros = ParametrosPrescricao.objects.filter(
                    Q(profissao=profissional.profissao, status='A', estabelecimento=estabelecimento_id) |
                    Q(profissional=profissional.profissional,
                      status='A', estabelecimento=estabelecimento_id)
                )
                if parametros.exists() and any(param.permite_editar_outras for param in parametros):
                    return super().dispatch(request, *args, **kwargs)

            messages.warning(
                request, "Voce nao tem permissao para editar esta prescricao / Somente o usuario do registro esta liberado, contate o administrador do sistema.")
            return HttpResponseRedirect(reverse('prescricao_listar', kwargs={'atendimento_id': atendimento_id}))

        return super().dispatch(request, *args, **kwargs)


###############################
# lista produtos prescritos

class ItensPrescricaoFilter(filters.FilterSet):
    id = django_filters.NumberFilter()

    dt_registro = django_filters.DateFilter(
        method='filter_by_date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'datepicker'})
    )
    dt_atualizacao = django_filters.DateFilter(
        method='filter_by_date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'datepicker'})
    )
    us_registro = django_filters.ModelChoiceFilter(
        queryset=User.objects.all()
    )

    us_atualizacao = django_filters.ModelChoiceFilter(
        queryset=User.objects.all()
    )
    status = django_filters.ChoiceFilter(
        choices=status_choices)

    class Meta:
        model = Prescricao
        fields = ['id', 'us_registro', 'dt_registro',
                  'us_atualizacao', 'dt_atualizacao', 'status']

    def filter_by_date(self, queryset, name, value):
        start_day = datetime.combine(value, datetime.min.time())
        start_day = timezone.make_aware(start_day)

        end_day = datetime.combine(value, datetime.max.time())
        end_day = timezone.make_aware(end_day)

        return queryset.filter(**{f'{name}__range': (start_day, end_day)})


class ItensPrescricaoListView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ListView):
    permission_required = 'prontuarios.view_prescricao'
    template_name = "prontuarios/itens_prescricao_listar.html"
    model = Prescricao
    context_object_name = "itens_prescricao_listar"
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset()
        atendimento_id = self.kwargs.get('atendimento_id')
        prescricao_id = self.kwargs.get('prescricao_id')
        # Aplicar filtros iniciais para evitar consultar todos os objetos do modelo
        queryset = ProdutoPrescricao.objects.filter(
            prescricao_id=prescricao_id)

        # Get a mutable copy of the request.GET QueryDict
        params = self.request.GET.copy()

        # If the 'limpar' button was clicked, clear the saved filters in the session
        if 'limpar' in params:
            self.request.session.pop('itens_prescricao_filters', None)
            params.clear()
        # If there are any filters in the GET request, update the saved filters in the session
        elif any(field in params for field in PrescricaoFilter.Meta.fields):
            self.request.session['itens_prescricao_filters'] = params
        # If there are no filters in the GET request but there are saved filters in the session, update the GET request with the saved filters
        elif 'itens_prescricao_filters' in self.request.session:
            params.update(self.request.session['itens_prescricao_filters'])

        # Pass the updated GET request to the filter
        params.setdefault('status', 'A')
        params.setdefault('fase', 'U')
        self.filter = ItensPrescricaoFilter(params, queryset=queryset)

        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Prontuários"
        context['title'] = "itens_prescricao_listar"
        context['func'] = 'Prescrições'

    # Obtendo o 'prescricao_id' do request ou do contexto atual
        prescricao_id = self.kwargs.get('prescricao_id', None)

        if prescricao_id:
            try:
                # Use filter em vez de get para evitar erros MultipleObjectsReturned
                produto_prescricao_query = ProdutoPrescricao.objects.filter(
                    prescricao_id=prescricao_id)

                # Se o QuerySet não estiver vazio, pegue o primeiro objeto
                if produto_prescricao_query.exists():
                    produto_prescricao = produto_prescricao_query.first()

                    # Extraíndo o valor do campo 'atendimento'
                    atendimento = produto_prescricao.atendimento

                    # Adicionando 'atendimento' ao contexto
                    context['atendimento_id'] = atendimento.id

                    # Obter o objeto Pessoa relacionado ao atendimento
                    pessoa = atendimento.pessoa

                    # Adicionando 'pessoa' ao contexto
                    context['pessoa'] = pessoa

            except ProdutoPrescricao.DoesNotExist:
                # Este bloco será executado se o filter não encontrar nenhum objeto,
                # o que é improvável dado que nós já verificamos com 'exists'
                pass

        estabelecimento_id = self.request.session.get("estabelecimento_id")

        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        context['itens_prescricao'] = None
        itens_prescricoes = self.get_queryset()
        if itens_prescricoes:
            context['itens_prescricao'] = itens_prescricoes[0]

        context['itens_prescricao_listar'] = self.get_queryset()

        context['filter'] = self.filter

        return context

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Sua sessão expirou!')
            return HttpResponseRedirect(reverse('logout'))
        return super().dispatch(request, *args, **kwargs)


##########

class AdepFilter(filters.FilterSet):

    prescricao = django_filters.NumberFilter()

    id = django_filters.NumberFilter()

    dt_registro = django_filters.DateFilter(
        method='filter_by_date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'datepicker'})
    )
    dt_atualizacao = django_filters.DateFilter(
        method='filter_by_date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'datepicker'})
    )
    us_registro = django_filters.ModelChoiceFilter(
        queryset=User.objects.all()
    )

    us_atualizacao = django_filters.ModelChoiceFilter(
        queryset=User.objects.all()
    )
    fase_prescricao = django_filters.ChoiceFilter(
        choices=fase_prescricao_choices)
    fase_adep = django_filters.ChoiceFilter(choices=fase_adep_choices)
    status = django_filters.ChoiceFilter(choices=status_choices)

    class Meta:
        model = Adep
        fields = ['id', 'prescricao', 'us_registro', 'dt_registro', 'fase_adep', 'fase_prescricao',
                  'us_atualizacao', 'dt_atualizacao', 'status']

    def filter_by_date(self, queryset, name, value):
        start_day = datetime.combine(value, datetime.min.time())
        start_day = timezone.make_aware(start_day)

        end_day = datetime.combine(value, datetime.max.time())
        end_day = timezone.make_aware(end_day)

        return queryset.filter(**{f'{name}__range': (start_day, end_day)})


class AdepListView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ListView):
    permission_required = 'prontuarios.view_adep'
    model = Adep
    template_name = 'prontuarios/adep_listar.html'
    context_object_name = 'adep_listar'
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset()
        atendimento_id = self.kwargs.get('atendimento_id')
        # Aplicar filtros iniciais para evitar consultar todos os objetos do modelo
        queryset = Adep.objects.filter(
            atendimento_id=atendimento_id).order_by('data_hora')

        # Get a mutable copy of the request.GET QueryDict
        params = self.request.GET.copy()

        # If the 'limpar' button was clicked, clear the saved filters in the session
        if 'limpar' in params:
            self.request.session.pop('addep_filters', None)
            params.clear()
        # If there are any filters in the GET request, update the saved filters in the session
        elif any(field in params for field in AdepFilter.Meta.fields):
            self.request.session['adep_filters'] = params
        # If there are no filters in the GET request but there are saved filters in the session, update the GET request with the saved filters
        elif 'adep_filters' in self.request.session:
            params.update(self.request.session['adep_filters'])

        # Pass the updated GET request to the filter
        params.setdefault('status', 'A')
        params.setdefault('fase_adep', 'P')
        self.filter = AdepFilter(params, queryset=queryset)

        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Prontuários"
        context['title'] = "adep_listar"
        context['func'] = 'Adep'
        context['atendimento_id'] = self.kwargs['atendimento_id']
        estabelecimento_id = self.request.session.get("estabelecimento_id")
        estabelecimento = Estabelecimento.objects.get(pk=estabelecimento_id)

        # Recupere o objeto Pessoa associado ao Atendimento
        atendimento_id = self.kwargs['atendimento_id']
        atendimento = Atendimento.objects.get(id=atendimento_id)
        pessoa = atendimento.pessoa

        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        # Correção do trecho de código para verificar a liberação

        context['adep'] = None
        adeps = self.get_queryset()
        if adeps:
            context['adep'] = adeps[0]

        context['filter'] = self.filter

        context['is_paginated'] = True

        return context


@login_required
def adep_update_fase(request, pk, new_fase):
    if request.method == "POST":
        if new_fase not in ['A', 'N']:
            return JsonResponse({"success": False, "error": "Fase inválida."})

        cadastro_medico_assistencial = CadastroProfissional.objects.filter(
            profissional=request.user, status='A').first()
        if not cadastro_medico_assistencial:
            return JsonResponse({"success": False, "error": "Usuário não possui cadastro profissional de saude, contate o administrador do sistema!"})

        user_profissao = cadastro_medico_assistencial.profissao

        adep = Adep.objects.get(pk=pk)

        # Agora, podemos obter o estabelecimento_id de Adep
        estabelecimento_id = adep.estabelecimento_id

        profissao_adep = ParametrosAdep.objects.filter(
            profissao=user_profissao, estabelecimento_id=estabelecimento_id, status='A').first()
        usuario_adep = ParametrosAdep.objects.filter(
            profissional=cadastro_medico_assistencial.profissional, estabelecimento_id=estabelecimento_id, status='A').first()

        if profissao_adep or usuario_adep:
            adep.fase_adep = new_fase

            # Atualizando os campos com o usuário logado e a data/hora atual
            # adep.us_atualizacao = request.user
            # adep.dt_atualizacao = timezone.now()
            adep.dt_adep = timezone.now()
            adep.us_adep = request.user

            adep.save()
            adep = Adep.objects.get(pk=pk)
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False, "error": "Usuario nao possui permissao para administrar a prescricao!"})

    return JsonResponse({"success": False, "error": "Metodo invalido."})


class SuspendPrescriptionView(LoginRequiredMixin, View):
    permission_required = 'prontuarios.change_prescricao'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'logout': True, 'message': 'Sessão expirada. Por favor, faça login novamente.'})

        # Verifique as permissões aqui
        if not request.user.has_perm(self.permission_required):
            return JsonResponse({'warning': False, 'message': 'Usuario nao autorizado para suspender esta prescricao.'})

        # Tente recuperar prescricao_id do POST data
        prescricao_id = request.POST.get('prescricao_id')

        try:
            # Busque a prescrição pelo ID
            prescricao = Prescricao.objects.get(pk=prescricao_id)

            # Verifique se o usuário logado é o mesmo que possui a prescrição
            if prescricao.us_registro == request.user:
                return super().dispatch(request, *args, **kwargs)

            # Se não for o mesmo usuário, verifique se ele tem permissão para suspender outras prescrições
            else:
                try:
                    profissional = CadastroProfissional.objects.get(
                        profissional=request.user, status='A')
                except CadastroProfissional.DoesNotExist:
                    profissional = None

                if profissional:
                    estabelecimento_id = request.session.get(
                        "estabelecimento_id")
                    parametros = ParametrosPrescricao.objects.filter(
                        Q(profissao=profissional.profissao, status='A', estabelecimento=estabelecimento_id) |
                        Q(profissional=profissional.profissional,
                          status='A', estabelecimento=estabelecimento_id)
                    )
                    if parametros.exists() and any(param.permite_suspender_outras for param in parametros):
                        return super().dispatch(request, *args, **kwargs)

                return JsonResponse({'success': False, 'message': 'Usuario nao autorizado para suspender / Somente usuario do registro pode suspender.'})

        except Prescricao.DoesNotExist:
            return JsonResponse({'success': False})

    def post(self, request, *args, **kwargs):
        # O código para suspender a prescrição aqui permanece o mesmo
        prescricao_id = request.POST.get('prescricao_id')
        try:
            prescricao = Prescricao.objects.get(pk=prescricao_id)
            prescricao.fase = 'S'
            prescricao.us_suspensao = request.user
            prescricao.us_atualizacao = request.user
            prescricao.dt_atualizacao = timezone.now()
            prescricao.dt_suspensao = timezone.now()
            prescricao.save()
            messages.success(self.request, settings.MSG_SUSP)
            return JsonResponse({'success': True, 'message': 'Prescricao suspensa com sucesso.'})
        except Prescricao.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Prescricao nao encontrada.'})


###################### PSICOTERAPIAS#######################################

class PsicoterapiaFilter(filters.FilterSet):
    id = django_filters.NumberFilter()

    dt_registro = django_filters.DateFilter(
        method='filter_by_date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'datepicker'})
    )
    dt_atualizacao = django_filters.DateFilter(
        method='filter_by_date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'datepicker'})
    )
    us_registro = django_filters.ModelChoiceFilter(
        queryset=User.objects.all()
    )

    us_atualizacao = django_filters.ModelChoiceFilter(
        queryset=User.objects.all()
    )
    status = django_filters.ChoiceFilter(choices=status_choices)

    class Meta:
        model = Psicoterapia
        fields = ['id', 'us_registro', 'dt_registro',
                  'us_atualizacao', 'dt_atualizacao', 'status']

    def filter_by_date(self, queryset, name, value):
        start_day = datetime.combine(value, datetime.min.time())
        start_day = timezone.make_aware(start_day)

        end_day = datetime.combine(value, datetime.max.time())
        end_day = timezone.make_aware(end_day)

        return queryset.filter(**{f'{name}__range': (start_day, end_day)})


class PsicoterapiaListView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ListView):
    permission_required = 'prontuarios.view_psicoterapia'
    template_name = "prontuarios/psicoterapia_listar.html"
    model = Psicoterapia
    context_object_name = "psicoterapia_listar"
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset()
        atendimento_id = self.kwargs.get('atendimento_id')
        queryset = Psicoterapia.objects.filter(atendimento_id=atendimento_id)

        # Get a mutable copy of the request.GET QueryDict
        params = self.request.GET.copy()

        # If the 'limpar' button was clicked, clear the saved filters in the session
        if 'limpar' in params:
            self.request.session.pop('psicoterapia_filters', None)
            params.clear()
        # If there are any filters in the GET request, update the saved filters in the session
        elif any(field in params for field in PsicoterapiaFilter.Meta.fields):
            self.request.session['psicoterapia_filters'] = params
        # If there are no filters in the GET request but there are saved filters in the session, update the GET request with the saved filters
        elif 'psicoterapia_filters' in self.request.session:
            params.update(self.request.session['psicoterapia_filters'])

        # Pass the updated GET request to the filter
        params.setdefault('status', 'A')
        self.filter = PsicoterapiaFilter(params, queryset=queryset)

        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Prontuários"
        context['title'] = "psicoterapia_listar"
        context['func'] = 'Psicoterapia'
        context['atendimento_id'] = self.kwargs['atendimento_id']
        estabelecimento_id = self.request.session.get("estabelecimento_id")
        estabelecimento = Estabelecimento.objects.get(pk=estabelecimento_id)

        # Recupere o objeto Pessoa associado ao Atendimento
        atendimento_id = self.kwargs['atendimento_id']
        atendimento = Atendimento.objects.get(id=atendimento_id)
        pessoa = atendimento.pessoa

        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        context['psicoterapia'] = None
        psicoterapias = self.get_queryset()
        if psicoterapias:
            context['psicoterapia'] = psicoterapias[0]

        context['filter'] = self.filter

        context['is_paginated'] = True

        return context


class PsicoterapiaCreateView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ParametrosProntuariosMixin, CreateView):
    permission_required = 'prontuarios.add_psicoterapia'
    template_name = "prontuarios/psicoterapia_cadastrar.html"
    form_class = PsicoterapiaCreateForm
    context_object_name = "psicoterapia_cadastrar"
    modelo_parametros = ParametrosPsicoterapia

    def get_success_url(self):
        return reverse_lazy('psicoterapia_listar', kwargs={'atendimento_id': self.kwargs['atendimento_id'], })

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'user': self.request.user,
            'atendimento': Atendimento.objects.get(pk=self.kwargs.get('atendimento_id')),
            'estabelecimento': Estabelecimento.objects.get(pk=self.request.session.get("estabelecimento_id"))
        })
        return kwargs

    def form_valid(self, form):
        if not self.request.user.is_authenticated:
            messages.warning(
                self.request, "Sua sessão expirou. Por favor, faça login novamente.")
            return HttpResponseRedirect(reverse('login'))

        # Atribuir o atendimento e o estabelecimento ao objeto Psicoterapia
        atendimento_id = self.kwargs.get('atendimento_id')
        atendimento = Atendimento.objects.get(pk=atendimento_id)
        form.instance.atendimento = atendimento
        estabelecimento_id = self.request.session.get("estabelecimento_id")

        if estabelecimento_id:
            estabelecimento = Estabelecimento.objects.get(
                id=estabelecimento_id)
            form.instance.estabelecimento = estabelecimento
        else:
            messages.error(
                self.request, "Selecione um estabelecimento antes de criar um atendimento.")
            return self.form_invalid(form)

        # Atribuir o usuário logado ao objeto Psicoterapia
        form.instance.us_registro = self.request.user

        # Salvar o objeto Psicoterapia
        psicoterapia = form.save(commit=False)

        # Salvar para obter um ID
        psicoterapia.save()

        if psicoterapia:
            messages.success(
                self.request, "Psicoterapia registrada com sucesso! ")
        else:
            messages.warning(
                self.request, "Psicoterapia não registrada!")

        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        messages.warning(
            self.request, 'Verifique as instruções e tente novamente!')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        form = self.get_form()
        context['titulo'] = "Prontuários"
        context['title'] = "psicoterapia_cadastrar"
        context['atendimento_id'] = self.kwargs.get('atendimento_id')

        atendimento_id = self.kwargs.get('atendimento_id')
        context['atendimento'] = Atendimento.objects.get(pk=atendimento_id)
        pessoa = context['atendimento'].pessoa
        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        context['psicoterapia_form'] = form

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        estabelecimento = Estabelecimento.objects.get(pk=estabelecimento_id)
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        return context

    def dispatch(self, request, *args, **kwargs):
        atendimento_id = self.kwargs.get('atendimento_id')
        atendimento = Atendimento.objects.get(pk=atendimento_id)
        self.kwargs['atendimento'] = atendimento

        # Verificar permissões aqui, em vez de usar `get_object()`
        if not self.has_permission():
            messages.error(
                request, 'Usuário sem permissão ou não autenticado')
            # Redirecione o usuário para a página desejada, por exemplo, a lista de atendimentos
            return HttpResponseRedirect(reverse_lazy('psicoterapia_listar', kwargs={'atendimento_id': atendimento_id}))

        return super().dispatch(request, *args, **kwargs)


class PsicoterapiaDetailView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, DetailView):
    permission_required = 'prontuarios.view_psicoterapia'
    model = Psicoterapia
    template_name = "prontuarios/psicoterapia_detalhe.html"
    form_class = PsicoterapiaDetailForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['psicoterapia_form'] = PsicoterapiaDetailForm(
            instance=self.object)

        # Recupere o objeto Pessoa associado ao Atendimento
        pessoa = self.object.atendimento.pessoa

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = ' '

        context['psicoterapia_list'] = Psicoterapia.objects.filter(
            atendimento=self.object.atendimento)

        context['titulo'] = "Prontuários"
        context['title'] = "psicoterapia_detalhe"
        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        # Obter os parâmetros de filtro salvos na sessão
        saved_filters = self.request.session.get('psicoterapia_filters', {})

        if saved_filters:
            # Aplicar o filtro ao queryset de Atendimento
            psicoterapias = PsicoterapiaFilter(
                saved_filters, queryset=Psicoterapia.objects.filter(estabelecimento_id=estabelecimento_id, atendimento=self.object.atendimento)).qs
        else:
            # Se não tiver filtro, use o critério do estabelecimento e do status
            psicoterapias = Psicoterapia.objects.filter(
                estabelecimento_id=estabelecimento_id, atendimento=self.object.atendimento, status='A')

        # Obter IDs para botoes anterior e proximo na navegacao do detalhe
        ids_a = psicoterapias.values_list('id', flat=True)

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
        proximo_objeto = Psicoterapia.objects.filter(
            id=proximo_id).first() if proximo_id else None

        # Obter o objeto anterior ou None se não existir
        objeto_anterior = Psicoterapia.objects.filter(
            id=objeto_anterior_id).first() if objeto_anterior_id else None

        context['proximo_objeto'] = proximo_objeto
        context['objeto_anterior'] = objeto_anterior
        # fim navegacao detalhe

        psicoterapia = self.object  # O objeto Psicoterapia sendo exibido

        # Inicialize o formulário com o conteúdo descriptografado, se aplicável
        psicoterapia_form = PsicoterapiaDetailForm(instance=psicoterapia, initial={
            'psicoterapia': psicoterapia})
        context['psicoterapia_form'] = psicoterapia_form

        psicoterapia_form.fields['psicoterapia'].widget.attrs.update(
            {'style': 'height: 900px;'})

        context['is_paginated'] = False

        return context


class PsicoterapiaUpdateView(LoginRequiredMixin, UserIsCreatorMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ParametrosProntuariosMixin, UpdateView):
    permission_required = 'prontuarios.change_psicoterapia'
    model = Psicoterapia
    form_class = PsicoterapiaUpdateForm
    template_name = "prontuarios/psicoterapia_editar.html"
    context_object_name = "psicoterapia_editar"
    modelo_parametros = ParametrosPsicoterapia  # Configuração do mixin mantida

    def get_success_url(self):
        # URL de sucesso mantida conforme solicitado
        return reverse_lazy('psicoterapia_listar', kwargs={'atendimento_id': self.object.atendimento.id})

    def get_form_kwargs(self):
        # Garante que os dados POST sejam passados ao form, mas somente em caso de método POST
        kwargs = super().get_form_kwargs()
        if self.request.method == 'POST':
            kwargs['data'] = self.request.POST
        return kwargs

    def get_context_data(self, **kwargs):
        # Contexto mantido e adicionado suporte para manter dados submetidos em caso de erro
        context = super().get_context_data(**kwargs)

        # Se for POST e o formulário for inválido, os dados submetidos são mantidos
        if self.request.method == 'POST':
            context['form'] = self.form_class(
                self.request.POST, instance=self.object)
        else:
            context['form'] = self.form_class(instance=self.object)

        # Contextos adicionais mantidos conforme sua implementação original
        context.update({
            'atendimento_id': self.object.atendimento.id,
            'titulo': "Prontuários",
            'title': "psicoterapia_editar",
            'pessoa_form': PessoaDetailForm(instance=self.object.atendimento.pessoa),
            'idade': calcular_idade(self.object.atendimento.pessoa.dt_nascimento) if self.object.atendimento.pessoa.dt_nascimento else ' ',
            'estabelecimento': Estabelecimento.objects.get(pk=self.request.session.get("estabelecimento_id")) if self.request.session.get("estabelecimento_id") else None,
            'user': self.request.user,
            'cad_index': reverse_lazy('cadastros_index'),
            'list_index': reverse_lazy('prontuario_listar'),
            'is_paginated': False,
        })

        return context

    def form_valid(self, form):
        if not self.request.user.is_authenticated:
            messages.warning(
                self.request, "Sua sessão expirou. Por favor, faça login novamente.")
            # substitua 'login' com sua URL de login
            return HttpResponseRedirect(reverse('login'))
        # Lógica de validação do formulário mantida com pequenas otimizações
        form.instance.us_atualizacao = self.request.user
        form.instance.dt_atualizacao = timezone.now()
        response = super().form_valid(form)
        messages.success(self.request, "Psicoterapia atualizada com sucesso.")
        return response

    def form_invalid(self, form):
        # Chamada padrão para form inválido com mensagem de erro
        messages.error(self.request, "Por favor, corrija os erros abaixo.")
        return super().form_invalid(form)

    def dispatch(self, request, *args, **kwargs):
        # Antes de qualquer coisa, obtenha o objeto para verificar permissões, etc.
        self.object = self.get_object()
        atendimento = self.object.atendimento

        # Aqui você pode adicionar qualquer lógica de pré-processamento ou verificação de acesso
        if not self.has_permission():
            raise PermissionDenied("Usuário não tem permissão para esta ação.")

        return super().dispatch(request, *args, **kwargs)

# TODO: AJUSTAR FILTERS AQUI E NO TEMPLATE ADEP_LISTAR_ASSINAR


class AdepAssinarFilter(filters.FilterSet):

    id = django_filters.NumberFilter()

    prescricao = django_filters.NumberFilter()

    data_hora = django_filters.DateFilter(
        method='filter_by_date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'datepicker'})
    )

    dt_adep = django_filters.DateFilter(
        method='filter_by_date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'datepicker'})
    )

    fase_prescricao = django_filters.ChoiceFilter(
        choices=fase_prescricao_choices)
    fase_adep = django_filters.ChoiceFilter(choices=fase_adep_choices)

    class Meta:
        model = Adep
        fields = ['id', 'prescricao', 'data_hora', 'dt_adep',
                  'fase_prescricao', 'fase_adep']

    def filter_by_date(self, queryset, name, value):
        start_day = datetime.combine(value, datetime.min.time())
        start_day = timezone.make_aware(start_day)

        end_day = datetime.combine(value, datetime.max.time())
        end_day = timezone.make_aware(end_day)

        return queryset.filter(**{f'{name}__range': (start_day, end_day)})


class AdepListarAssinarView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ParametrosProntuariosMixin, ListView):
    model = Adep
    template_name = 'prontuarios/adep_listar_assinar.html'
    context_object_name = 'adeps'
    permission_required = 'prontuarios.view_adep'
    modelo_parametros = ParametrosAdep
    paginate_by = 33

    def get_queryset(self):
        # atendimento_id = self.kwargs.get('atendimento_id')

        # Começa com um queryset base filtrado por condições específicas e atendimento_id
        queryset = Adep.objects.filter(
            Q(fase_adep='N') | Q(fase_adep='A'),
            us_adep=self.request.user,
            assinar=False,
            status='A',
            # atendimento_id=atendimento_id
        ).select_related('prescricao').distinct().order_by('data_hora')

        # Copia os parâmetros GET de forma mutável
        params = self.request.GET.copy()

        if 'limpar' in params:
            # Limpa os filtros salvos na sessão se o botão 'limpar' foi clicado
            self.request.session.pop('adep_assinar_filters', None)
            params.clear()
        elif any(field in params for field in AdepAssinarFilter.Meta.fields):
            # Atualiza os filtros salvos na sessão com os atuais do GET request
            self.request.session['aded_assinar_filters'] = params
        elif 'adep_assinar_filters' in self.request.session:
            # Usa os filtros salvos na sessão se não houver filtros no GET request
            params.update(self.request.session['adep_assinar_filters'])

        # Aplica os filtros ao queryset inicial
        self.filter = AdepAssinarFilter(params, queryset=queryset)

        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Adeps"
        context['title'] = "adep_listar_assinar"
        context['func'] = 'ADEPs'
        estabelecimento_id = self.request.session.get("estabelecimento_id")
        estabelecimento = Estabelecimento.objects.get(pk=estabelecimento_id)

        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('adep_listar_assinar')

        # Correção do trecho de código para verificar a liberação

        context['adep'] = None
        adeps = self.get_queryset()
        if adeps:
            context['adep'] = adeps[0]

        context['filter'] = self.filter

        context['is_paginated'] = True

        return context

    def post(self, request, *args, **kwargs):
        selected_adep_ids = request.POST.getlist('adep_ids')

        # Verifica se nenhum Adep foi selecionado
        if not selected_adep_ids:
            messages.error(
                request, 'Por favor, selecione pelo menos um item!')
            # Use o nome correto da rota se for diferente
            return redirect('adep_listar_assinar')

        adeps = Adep.objects.filter(
            id__in=selected_adep_ids).select_related('prescricao')

        # Agrupa Adeps por Prescricao
        prescricao_to_adeps = {}
        for adep in adeps:
            if adep.prescricao_id not in prescricao_to_adeps:
                prescricao_to_adeps[adep.prescricao_id] = []
            prescricao_to_adeps[adep.prescricao_id].append(adep)

        for prescricao_id, adeps_list in prescricao_to_adeps.items():
            if len(adeps_list) > 33:
                messages.warning(
                    request, 'Por favor, selecione no máximo 33 itens por número de prescrição!')
                return redirect('adep_listar_assinar')

            prescricao = Prescricao.objects.get(id=prescricao_id)

            # Marca os Adep processados como assinados
            Adep.objects.filter(us_adep=self.request.user, prescricao_id=prescricao_id, fase_adep__in=[
                                'N', 'A'], assinar=False, id__in=[adep.id for adep in adeps_list]).update(assinar=True)

            # Chama a funcao de gerar o pdf e assinar dentro do loop.
            rel = salvar_pdf_prontuario(
                request.user, prescricao, assinar=True)

            if rel:
                messages.success(
                    request, f"PDF assinado com sucesso! & {settings.MSG_ADD}")
            else:
                messages.warning(
                    request, f"PDF gerado sem assinatura! & {settings.MSG_ADD}")

        return redirect('adep_listar_assinar')  # Ajuste aqui também


# ADEP ADMINSITRACAO POR TURNO / SELETORES
class AdepAdministrarFilter(django_filters.FilterSet):
    id = django_filters.NumberFilter()
    prescricao = django_filters.NumberFilter()

    data_hora_min = django_filters.DateTimeFilter(
        field_name='data_hora',
        lookup_expr='gte',
        label='Data e Hora Mínima',
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local', 'class': 'form-control'}, format='%Y-%m-%dT%H:%M')
    )

    data_hora_max = django_filters.DateTimeFilter(
        field_name='data_hora',
        lookup_expr='lte',
        label='Data e Hora Máxima',
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local', 'class': 'form-control', 'readonly': 'readonly'}, format='%Y-%m-%dT%H:%M')
    )

    class Meta:
        model = Adep
        fields = ['id', 'prescricao', 'data_hora_min', 'data_hora_max']

    def __init__(self, *args, **kwargs):
        super(AdepAdministrarFilter, self).__init__(*args, **kwargs)
        now = timezone.now().strftime('%Y-%m-%dT%H:%M')
        # Define o valor de data_hora_max para agora se não for fornecido
        self.filters['data_hora_max'].field.widget.attrs['value'] = now


class AdepListarAdministrarView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ParametrosProntuariosMixin, ListView):
    model = Adep
    template_name = 'prontuarios/adep_listar_administrar.html'
    context_object_name = 'adeps'
    permission_required = 'prontuarios.view_adep'
    modelo_parametros = ParametrosAdep
    paginate_by = 33

    def get_queryset(self):
        queryset = Adep.objects.filter(
            fase_adep='P', assinar=False, status='A').distinct().order_by('data_hora')
        params = self.request.GET.copy()

        if 'limpar' in params:
            self.request.session.pop('adep_administrar_filters', None)
            params.clear()
        else:
            # Verifica se data_hora_max está presente nos parâmetros; se não, define para o momento atual
            if 'data_hora_max' not in params or not params['data_hora_max']:
                params['data_hora_max'] = timezone.now().strftime(
                    '%Y-%m-%dT%H:%M')
            self.request.session['adep_administrar_filters'] = params

        self.filter = AdepAdministrarFilter(params, queryset=queryset)
        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'titulo': "Adeps/Turno",
            'title': "adep_listar_administrar",
            'func': 'ADEPs/Turno',
            'cad_index': reverse_lazy('cadastros_index'),
            'list_index': reverse_lazy('adep_listar_administrar'),
            'filter': self.filter,
            'is_paginated': True,
        })
        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        # Reintegrando o contexto de 'adep' conforme o código original
        adeps = self.get_queryset()
        if adeps:
            # Utiliza .first() para obter o primeiro item, se existir
            context['adep'] = adeps.first()

        return context

    def post(self, request, *args, **kwargs):
        selected_adep_ids = request.POST.getlist('adep_ids')
        acao = request.POST.get('acao')  # 'administrar' ou 'nao_administrar'
        if not selected_adep_ids:
            messages.error(request, 'Por favor, selecione pelo menos um item!')
            return redirect('adep_listar_administrar')

        # Define a nova fase de Adep baseada na ação
        fase_adep_nova = 'A' if acao == 'administrar' else 'N'

        # Data e hora atuais
        now = timezone.now()

        # Usuário logado
        user = request.user

        # Atualiza os Adeps selecionados
        for adep_id in selected_adep_ids:
            Adep.objects.filter(id=adep_id).update(
                fase_adep=fase_adep_nova,
                us_adep=user,  # Atualiza com o usuário logado
                dt_adep=now,  # Atualiza com a data e hora atuais
            )

        messages.success(request, f"{settings.MSG_EDIT}")
        return redirect('adep_listar_administrar')


# FIM ADEP TURNOS / SELETORES


# INICIO DIAGNOSTICOS
class DiagnosticoFilter(filters.FilterSet):
    id = django_filters.NumberFilter()

    diagnostico = django_filters.CharFilter(
        method='filtro_diagnostico_customizado', label='CIDs')

    dt_registro = django_filters.DateFilter(
        method='filter_by_date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'datepicker'})
    )
    dt_atualizacao = django_filters.DateFilter(
        method='filter_by_date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'datepicker'})
    )
    us_registro = django_filters.ModelChoiceFilter(
        queryset=User.objects.all()
    )

    us_atualizacao = django_filters.ModelChoiceFilter(
        queryset=User.objects.all()
    )
    status = django_filters.ChoiceFilter(choices=status_choices)

    class Meta:
        model = Diagnostico
        fields = ['id', 'diagnostico', 'us_registro', 'dt_registro',
                  'us_atualizacao', 'dt_atualizacao', 'status']

    def filtro_diagnostico_customizado(self, queryset, name, value):
        # Filtra por descrição ou código no modelo Cid
        return queryset.filter(
            Q(diagnostico__descricao__icontains=value) |
            Q(diagnostico__codigo__icontains=value)
        )

    def filter_by_date(self, queryset, name, value):
        start_day = datetime.combine(value, datetime.min.time())
        start_day = timezone.make_aware(start_day)

        end_day = datetime.combine(value, datetime.max.time())
        end_day = timezone.make_aware(end_day)

        return queryset.filter(**{f'{name}__range': (start_day, end_day)})


class DiagnosticoListView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, RelatorioMixin, ListView):
    permission_required = 'prontuarios.view_diagnostico'
    template_name = "prontuarios/diagnostico_listar.html"
    model = Diagnostico
    context_object_name = "diagnostico_listar"
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset()
        atendimento_id = self.kwargs.get('atendimento_id')
        queryset = Diagnostico.objects.filter(atendimento_id=atendimento_id)

        # Get a mutable copy of the request.GET QueryDict
        params = self.request.GET.copy()

        # If the 'limpar' button was clicked, clear the saved filters in the session
        if 'limpar' in params:
            self.request.session.pop('diagnostico_filters', None)
            params.clear()
        # If there are any filters in the GET request, update the saved filters in the session
        elif any(field in params for field in DiagnosticoFilter.Meta.fields):
            self.request.session['diagnostico_filters'] = params
        # If there are no filters in the GET request but there are saved filters in the session, update the GET request with the saved filters
        elif 'diagnostico_filters' in self.request.session:
            params.update(self.request.session['diagnostico_filters'])

        # Pass the updated GET request to the filter
        params.setdefault('status', 'A')
        self.filter = DiagnosticoFilter(params, queryset=queryset)

        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Prontuários"
        context['title'] = "diagnostico_listar"
        context['func'] = 'Diagnósticos'
        context['atendimento_id'] = self.kwargs['atendimento_id']
        estabelecimento_id = self.request.session.get("estabelecimento_id")
        estabelecimento = Estabelecimento.objects.get(pk=estabelecimento_id)

        # Recupere o objeto Pessoa associado ao Atendimento
        atendimento_id = self.kwargs['atendimento_id']
        atendimento = Atendimento.objects.get(id=atendimento_id)
        pessoa = atendimento.pessoa

        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        context['diagnostico'] = None
        diagnosticos = self.get_queryset()
        if diagnosticos:
            context['diagnostico'] = diagnosticos[0]

        context['filter'] = self.filter

        context['is_paginated'] = True

        current_filters = self.request.GET or self.request.session.get(
            'diagnostico_filters', {})
        disable_button = current_filters.get('status') == 'I'

        # Adiciona a flag de controle no contexto
        context['disable_button'] = disable_button

        return context


class DiagnosticoCreateView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ParametrosProntuariosMixin, CreateView):
    permission_required = 'prontuarios.add_diagnostico'
    template_name = "prontuarios/diagnostico_cadastrar.html"
    form_class = DiagnosticoCreateForm
    context_object_name = "diagnostico_cadastrar"
    modelo_parametros = ParametrosDiagnostico

    def get_success_url(self):
        return reverse_lazy('diagnostico_listar', kwargs={'atendimento_id': self.kwargs['atendimento_id'], })

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        atendimento_id = self.kwargs.get('atendimento_id')
        kwargs['atendimento'] = Atendimento.objects.get(pk=atendimento_id)

        estabelecimento_id = self.request.session.get("estabelecimento_id")

        if estabelecimento_id:
            estabelecimento = Estabelecimento.objects.get(
                id=estabelecimento_id)
            kwargs['estabelecimento'] = estabelecimento

        return kwargs

    def form_valid(self, form):
        if not self.request.user.is_authenticated:
            messages.warning(
                self.request, "Sua sessão expirou. Por favor, faça login novamente.")
            return HttpResponseRedirect(reverse('login'))

        # Atribuir o atendimento e o estabelecimento ao objeto Evolucao
        atendimento_id = self.kwargs.get('atendimento_id')
        atendimento = Atendimento.objects.get(pk=atendimento_id)
        form.instance.atendimento = atendimento

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
        diagnostico = form.save(commit=False)
        # Salvar para obter um ID
        diagnostico.save()

        form.save_m2m()

        # Gerar e salvar PDF, assinado se necessário
        relatorio = salvar_pdf_prontuario(
            self.request.user, diagnostico, assinar=diagnostico.assinar)
        if relatorio:
            messages.success(
                self.request, f"PDF assinado com sucesso! & {settings.MSG_ADD}")
        else:
            messages.warning(
                self.request, f"PDF gerado sem assinatura! & {settings.MSG_ADD}")

        return super().form_valid(form)

    def form_invalid(self, form):
        messages.warning(
            self.request, 'Verifique as instruções e tente novamente!')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        form = self.get_form()
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Prontuários"
        context['title'] = "diagnostico_cadastrar"
        context['atendimento_id'] = self.kwargs.get('atendimento_id')

        atendimento_id = self.kwargs.get('atendimento_id')
        context['atendimento'] = Atendimento.objects.get(pk=atendimento_id)
        pessoa = context['atendimento'].pessoa
        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        context['diagnostico_form'] = form

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        estabelecimento = Estabelecimento.objects.get(pk=estabelecimento_id)
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['user'] = self.request.user

        prof = CadastroProfissional.objects.filter(
            profissional=self.request.user, status='A').order_by('-id').first()

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        context['is_paginated'] = False

        return context

    def dispatch(self, request, *args, **kwargs):
        atendimento_id = self.kwargs.get('atendimento_id')
        atendimento = Atendimento.objects.get(pk=atendimento_id)
        self.kwargs['atendimento'] = atendimento

        # Verificar permissões aqui, em vez de usar `get_object()`
        if not self.has_permission():
            messages.error(
                request, 'Usuário sem permissão ou não autenticado')
            # Redirecione o usuário para a página desejada, por exemplo, a lista de atendimentos
            return HttpResponseRedirect(reverse_lazy('diagnostico_listar', kwargs={'atendimento_id': atendimento_id}))

        return super().dispatch(request, *args, **kwargs)


class DiagnosticoDetailView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, DetailView):
    permission_required = 'prontuarios.view_diagnostico'
    model = Diagnostico
    template_name = "prontuarios/diagnostico_detalhe.html"
    form_class = DiagnosticoDetailForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['diagnostico_form'] = DiagnosticoDetailForm(
            instance=self.object)

        # Recupere o objeto Pessoa associado ao Atendimento
        pessoa = self.object.atendimento.pessoa

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = ' '

        context['diagnostico_list'] = Diagnostico.objects.filter(
            atendimento=self.object.atendimento)

        context['titulo'] = "Prontuários"
        context['title'] = "diagnostico_detalhe"
        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        # Obter os parâmetros de filtro salvos na sessão
        saved_filters = self.request.session.get('diagnostico_filters', {})

        if saved_filters:
            # Aplicar o filtro ao queryset de Atendimento
            diagnosticos = DiagnosticoFilter(
                saved_filters, queryset=Diagnostico.objects.filter(estabelecimento_id=estabelecimento_id, atendimento=self.object.atendimento)).qs
        else:
            # Se não tiver filtro, use o critério do estabelecimento e do status
            diagnosticos = Diagnostico.objects.filter(
                estabelecimento_id=estabelecimento_id, atendimento=self.object.atendimento, status='A')

        # Obter IDs para botoes anterior e proximo na navegacao do detalhe
        ids_a = diagnosticos.values_list('id', flat=True)

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
        proximo_objeto = Diagnostico.objects.filter(
            id=proximo_id).first() if proximo_id else None

        # Obter o objeto anterior ou None se não existir
        objeto_anterior = Diagnostico.objects.filter(
            id=objeto_anterior_id).first() if objeto_anterior_id else None

        context['proximo_objeto'] = proximo_objeto
        context['objeto_anterior'] = objeto_anterior
        # fim navegacao detalhe

        diagnostico = self.object  # O objeto Evolucao sendo exibido
        # Acessa o campo protegido do objeto TipoEvolucao relacionado
        # Inicialize o formulário com o conteúdo descriptografado, se aplicável
        diagnostico_form = DiagnosticoDetailForm(instance=diagnostico, initial={
            'diagnostico': diagnostico})
        context['diagnostico_form'] = diagnostico_form

        context['is_paginated'] = False

        return context


class DiagnosticoUpdateView(LoginRequiredMixin, UserIsCreatorMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ParametrosProntuariosMixin, UpdateView):
    permission_required = 'prontuarios.change_diagnostico'
    model = Diagnostico
    form_class = DiagnosticoUpdateForm
    template_name = "prontuarios/diagnostico_editar.html"
    success_url = reverse_lazy("diagnostico_listar")
    context_object_name = "diagnostico_editar"
    modelo_parametros = ParametrosDiagnostico

    def form_valid(self, form):
        super().form_valid(form)
        if not self.request.user.is_authenticated:
            messages.warning(
                self.request, "Sua sessão expirou. Por favor, faça login novamente.")
            # substitua 'login' com sua URL de login
            return HttpResponseRedirect(reverse('login'))

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        estabelecimento = Estabelecimento.objects.get(pk=estabelecimento_id)

        form.instance.us_atualizacao = self.request.user
        form.instance.dt_atualizacao = timezone.now()

        diagnostico = form.save(commit=False)
        # Salvar para obter um ID

        # Marcar os relatórios antigos como inativos
        Relatorio.objects.filter(
            content_type=ContentType.objects.get_for_model(diagnostico),
            object_id=diagnostico.pk
        ).update(status='I')

        diagnostico.save()
        form.save_m2m()

        if not diagnostico.status == 'I':
            # Gerar e salvar PDF, assinado se necessário
            relatorio = salvar_pdf_prontuario(
                self.request.user, diagnostico, assinar=diagnostico.assinar)
            if relatorio:
                messages.success(
                    self.request, f"PDF assinado com sucesso!")
            else:
                messages.warning(
                    self.request, f"PDF gerado sem assinatura!")

        messages.success(self.request, settings.MSG_EDIT)

        response = super().form_valid(form)
        return response

    def form_invalid(self, form):
        # Mensagem de erro para o usuário
        messages.warning(
            self.request, 'Verifique as instruções e tente novamente!')

        # Recriar o formulário com os dados submetidos para manter as tentativas do usuário
        form_with_user_data = self.form_class(
            self.request.POST, self.request.FILES, instance=self.object)

        # Atualizar o contexto com o novo formulário contendo os dados do usuário
        return self.render_to_response(self.get_context_data(form=form_with_user_data))

    def dispatch(self, request, *args, **kwargs):

        try:
            self.object = self.get_object()
            atendimento = self.object.atendimento
            self.kwargs['atendimento'] = atendimento
            return super().dispatch(request, *args, **kwargs)
        except AccessDenied:
            messages.error(
                request, 'Usuário não liberado para acessar registros de outro estabelecimento')
            # Redirecione o usuário para a página desejada, por exemplo, a lista de atendimentos
            return HttpResponseRedirect(reverse_lazy('diagnostico_listar', kwargs={'atendimento_id': self.kwargs['atendimento'].id}))

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        atendimento = self.object.atendimento
        self.kwargs['atendimento_id'] = atendimento
        return super().get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('diagnostico_listar', kwargs={'atendimento_id': self.kwargs['atendimento'].id, })

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context['atendimento_id'] = self.object.atendimento.id
        context['titulo'] = "Prontuários"
        context['title'] = "diagnostico_editar"

        pessoa = self.object.atendimento.pessoa
        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)

        context['idade'] = calcular_idade(
            pessoa.dt_nascimento) if pessoa.dt_nascimento else ' '

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['user'] = self.request.user

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        diagnostico = self.object  # O objeto sendo editado

        # Inicialize o formulário com o conteúdo descriptografado, se aplicável
        diagnostico_form = DiagnosticoUpdateForm(instance=diagnostico, initial={
            'diagnostico': diagnostico})

        context['diagnostico_form'] = diagnostico_form

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')

        context['is_paginated'] = False

        if self.request.method == 'POST':
            # Se a submissão falhar, use os dados POST como valor inicial
            context['form'] = self.form_class(
                self.request.POST,
                self.request.FILES,
                instance=self.object,
                initial={'diagnostico': self.request.POST.get(
                    'diagnostico', '')}
            )
        else:
            context['form'] = self.form_class(instance=self.object)

        return context


# FIM DIAGNOSTICOS


# INICIO PASSAGEM PLANTAO


class PassagemPlantaoFilter(filters.FilterSet):
    id = django_filters.NumberFilter()

    dt_registro = django_filters.DateFilter(
        method='filter_by_date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'datepicker'})
    )
    dt_atualizacao = django_filters.DateFilter(
        method='filter_by_date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'datepicker'})
    )
    us_registro = django_filters.ModelChoiceFilter(
        queryset=User.objects.all()
    )

    us_atualizacao = django_filters.ModelChoiceFilter(
        queryset=User.objects.all()
    )
    status = django_filters.ChoiceFilter(choices=status_choices)

    class Meta:
        model = PassagemPlantao
        fields = ['id', 'us_registro', 'dt_registro',
                  'us_atualizacao', 'dt_atualizacao', 'status']

    def filter_by_date(self, queryset, name, value):
        start_day = datetime.combine(value, datetime.min.time())
        start_day = timezone.make_aware(start_day)

        end_day = datetime.combine(value, datetime.max.time())
        end_day = timezone.make_aware(end_day)

        return queryset.filter(**{f'{name}__range': (start_day, end_day)})


# TODO: ALTERAR DAQUI PARA BAIXO DE PSICO PARA PASSAGEM DE PLANTÃO
class PassagemPlantaoListView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ListView):
    permission_required = 'prontuarios.view_passagemplantao'
    template_name = "prontuarios/passagem_plantao_listar.html"
    model = PassagemPlantao
    context_object_name = "passagem_plantao_listar"
    paginate_by = 15

    # O restante da sua classe continua como antes, sem modificações

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        estabelecimento_id = self.request.session.get("estabelecimento_id")
        queryset = queryset.filter(
            status='A', estabelecimento_id=estabelecimento_id)

        try:

            # Primeiro, obtém a profissão do usuário logado
            profissao_usuario = CadastroProfissional.objects.get(
                profissional=user, status='A')

            # Filtrar por tipo_passagem_plantao permitidos para o usuário
            tipos_permitidos = ParametrosPassagemPlantao.objects.filter(
                Q(profissao_id=profissao_usuario.profissao) | Q(profissional=user),
                estabelecimento_id=estabelecimento_id,
                status='A'
            ).distinct().values_list('tipo_passagem_plantao', flat=True)

            if tipos_permitidos:
                queryset = queryset.filter(
                    tipo_passagem_plantao__in=tipos_permitidos)
            else:
                queryset = queryset.none()

        except CadastroProfissional.DoesNotExist:
            queryset = queryset.none()

        # Get a mutable copy of the request.GET QueryDict
        params = self.request.GET.copy()

        # If the 'limpar' button was clicked, clear the saved filters in the session
        if 'limpar' in params:
            self.request.session.pop('passagem_plantao_filters', None)
            params.clear()
        # If there are any filters in the GET request, update the saved filters in the session
        elif any(field in params for field in PassagemPlantaoFilter.Meta.fields):
            self.request.session['passagem_plantao_filters'] = params
        # If there are no filters in the GET request but there are saved filters in the session, update the GET request with the saved filters
        elif 'passagem_plantao_filters' in self.request.session:
            params.update(self.request.session['passagem_plantao_filters'])

        # Pass the updated GET request to the filter
        params.setdefault('status', 'A')
        self.filter = PassagemPlantaoFilter(params, queryset=queryset)

        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Passagem Plantão"
        context['title'] = "passagem_plantao_listar"
        context['func'] = 'Passagem Plantão'
        estabelecimento_id = self.request.session.get("estabelecimento_id")
        estabelecimento = Estabelecimento.objects.get(pk=estabelecimento_id)

        # Recupere o objeto Pessoa associado ao Atendimento
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = None

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('passagem_plantao_listar')

        context['passagem_plantao'] = None
        passagens = self.get_queryset()
        if passagens:
            context['passagem_plantao'] = passagens[0]

        context['filter'] = self.filter

        context['is_paginated'] = True

        return context


class PassagemPlantaoCreateView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ParametrosProntuariosMixin, CreateView):
    permission_required = 'prontuarios.add_passagemplantao'
    template_name = "prontuarios/passagem_plantao_cadastrar.html"
    form_class = PassagemPlantaoCreateForm
    context_object_name = "passagem_plantao_cadastrar"
    modelo_parametros = ParametrosPassagemPlantao

    def get_success_url(self):
        return reverse_lazy('passagem_plantao_listar')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'user': self.request.user,
            'estabelecimento': Estabelecimento.objects.get(pk=self.request.session.get("estabelecimento_id"))
        })
        return kwargs

    def form_valid(self, form):
        if not self.request.user.is_authenticated:
            messages.warning(
                self.request, "Sua sessão expirou. Por favor, faça login novamente.")
            return HttpResponseRedirect(reverse('login'))
        # Atribuir o atendimento e o estabelecimento ao objeto Psicoterapia
        estabelecimento_id = self.request.session.get("estabelecimento_id")

        if estabelecimento_id:
            estabelecimento = Estabelecimento.objects.get(
                id=estabelecimento_id)
            form.instance.estabelecimento = estabelecimento
        else:
            messages.error(
                self.request, "Selecione um estabelecimento antes de criar um atendimento.")
            return self.form_invalid(form)

        # Atribuir o usuário logado ao objeto Psicoterapia
        form.instance.us_registro = self.request.user

        # Salvar o objeto Psicoterapia
        passagem = form.save(commit=False)
        # Salvar para obter um ID
        passagem.save()

        if passagem:
            messages.success(
                self.request, f"Passagem de plantão registrada com sucesso!")
        else:
            messages.warning(
                self.request, "Passagem de plantão não registrada!")

        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        messages.warning(
            self.request, 'Verifique as instruções e tente novamente!')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estabelecimento_id = self.request.session.get("estabelecimento_id")
        estabelecimento = Estabelecimento.objects.get(
            pk=estabelecimento_id) if estabelecimento_id else None
        prof = CadastroProfissional.objects.filter(
            profissional=self.request.user, status='A').order_by('-id').first()

        tipo_passagem_plantao_list = []
        tipo_passagem_plantao_padrao = None

        if prof:
            par = ParametrosPassagemPlantao.objects.filter(
                Q(profissao=prof.profissao, estabelecimento=estabelecimento, status='A') |
                Q(profissional=self.request.user,
                  estabelecimento=estabelecimento, status='A')
            ).distinct()

            for obj in par:
                tipo_passagem_plantao_list.extend(
                    list(obj.tipo_passagem_plantao.all()))
                if obj.tipo_passagem_plantao_padrao and obj.tipo_passagem_plantao_padrao in obj.tipo_passagem_plantao.all():
                    tipo_passagem_plantao_padrao = obj.tipo_passagem_plantao_padrao

        if tipo_passagem_plantao_padrao:
            tipo_passagem_plantao_list = [tipo_passagem_plantao_padrao] + \
                [te for te in tipo_passagem_plantao_list if te !=
                    tipo_passagem_plantao_padrao]

        context.update({
            'titulo': "Passagem Plantão",
            'title': "Cadastrar Passagem Plantões",
            'estabelecimento': estabelecimento,
            'user': self.request.user,
            'tipo_passagem_plantao_form': tipo_passagem_plantao_list,
            'cad_index': reverse_lazy('cadastros_index'),
            'list_index': reverse_lazy('passagem_plantao_listar'),
        })

        return context

    def dispatch(self, request, *args, **kwargs):

        # Verificar permissões aqui, em vez de usar `get_object()`
        if not self.has_permission():
            messages.error(
                request, 'Usuário sem permissão ou não autenticado')
            # Redirecione o usuário para a página desejada, por exemplo, a lista de atendimentos
            return HttpResponseRedirect(reverse_lazy('passagem_plantao_listar'))

        return super().dispatch(request, *args, **kwargs)


class PassagemPlantaoDetailView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, DetailView):
    permission_required = 'prontuarios.view_passagemplantao'
    model = PassagemPlantao
    template_name = "prontuarios/passagem_plantao_detalhe.html"
    form_class = PassagemPlantaoDetailForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['passagem_plantao_form'] = PassagemPlantaoDetailForm(
            instance=self.object)

        estabelecimento_id = self.request.session.get("estabelecimento_id")
        if estabelecimento_id:
            context["estabelecimento"] = Estabelecimento.objects.get(
                pk=estabelecimento_id)
        else:
            context["estabelecimento"] = ' '

        context['passagem_plantao_list'] = PassagemPlantao.objects.filter(
            status='A')

        context['titulo'] = "Passagem Plantão"
        context['title'] = "passagem_plantao_detalhe"

        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('passagem_plantao_listar')

        # Obter os parâmetros de filtro salvos na sessão
        saved_filters = self.request.session.get(
            'passagem_plantao_filters', {})

        if saved_filters:
            # Aplicar o filtro ao queryset de Atendimento
            passagens = PassagemPlantaoFilter(
                saved_filters, queryset=PassagemPlantao.objects.filter(estabelecimento_id=estabelecimento_id)).qs
        else:
            # Se não tiver filtro, use o critério do estabelecimento e do status
            passagens = PassagemPlantao.objects.filter(
                estabelecimento_id=estabelecimento_id, status='A')

        # Obter IDs para botoes anterior e proximo na navegacao do detalhe
        ids_a = passagens.values_list('id', flat=True)

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
        proximo_objeto = PassagemPlantao.objects.filter(
            id=proximo_id).first() if proximo_id else None

        # Obter o objeto anterior ou None se não existir
        objeto_anterior = PassagemPlantao.objects.filter(
            id=objeto_anterior_id).first() if objeto_anterior_id else None

        context['proximo_objeto'] = proximo_objeto
        context['objeto_anterior'] = objeto_anterior
        # fim navegacao detalhe

        passagem_plantao = self.object  # O objeto Psicoterapia sendo exibido

        # Inicialize o formulário com o conteúdo descriptografado, se aplicável
        passagem_form = PassagemPlantaoDetailForm(instance=passagem_plantao, initial={
            'passagem_planto': passagem_plantao})
        context['passagem_form'] = passagem_form

        passagem_form.fields['passagem_plantao'].widget.attrs.update(
            {'style': 'height: 1900px;'})

        context['is_paginated'] = False

        return context


# FIM PASSAGEM PLANTAO


# UTILIZADA NO BOTAO DE CRIACAO DE PASSAGEM DE PLANTAO, SE TIVER ADEPS PENDENTES DE PDF E ASSINATURAS DIRECIONA PARA ELES
def check_adeps(request):

    estabelecimento_id = request.session.get("estabelecimento_id")
    user = request.user

    # Aqui você coloca a lógica para verificar se existem ADEPs pendentes
    tem_adeps_pendentes = Adep.objects.filter(
        Q(fase_adep='N') | Q(fase_adep='A'),
        us_adep=user,
        assinar=False,
        status='A',
        estabelecimento_id=estabelecimento_id,
    ).exists()

    if tem_adeps_pendentes:
        messages.warning(
            request, 'Para registrar a passagem do plantão não pode ter itens de adminsitração de prescrição pendente de geração de PDF e assinatura eletrônica!')
        return redirect('adep_listar_assinar')
    else:
        return redirect('passagem_plantao_cadastrar')


class GestaoPacientesListView(TemplateView):
    template_name = 'prontuarios/gestao_pacientes.html'

    def dispatch(self, request, *args, **kwargs):
        # Limpa os filtros da sessão relacionados ao AtendimentoFilter
        for key in list(request.session.keys()):
            # Se os filtros são armazenados com esse prefixo
            if key.startswith('django_filters_'):
                del request.session[key]

        request.session.modified = True  # Garante que a sessão será atualizada

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estabelecimento_id = self.request.session.get('estabelecimento_id')

        filtro = Atendimento.objects.filter(
            estabelecimento_id=estabelecimento_id, dt_alta=None, status='A')

        atendimentos_filtrados = filtro

        for atendimento in atendimentos_filtrados:
            atendimento.ultimo_diagnostico = Diagnostico.objects.filter(
                atendimento=atendimento, status='A'
            ).order_by('-dt_registro').first()

            atendimento.ultima_evolucao = Evolucao.objects.filter(
                atendimento=atendimento, status='A'
            ).order_by('-dt_registro').first()

            atendimento.ultima_psicoterapia = Psicoterapia.objects.filter(
                atendimento=atendimento, status='A'
            ).order_by('-dt_registro').first()

            atendimento.ultima_prescricao = Prescricao.objects.filter(
                atendimento=atendimento, status='A'
            ).order_by('-dt_registro').first()

            atendimento.ultimo_adep = Adep.objects.filter(
                atendimento=atendimento, status='A'
            ).order_by('-dt_registro').first()

            atendimento.ultimo_sinal_vital = SinaisVitais.objects.filter(
                atendimento=atendimento, status='A'
            ).order_by('-dt_registro').first()

            atendimento.ultimo_sae = SAE.objects.filter(
                atendimento=atendimento, status='A'
            ).order_by('-dt_registro').first()

            atendimento.ultimo_plano_cuidados = PlanoCuidados.objects.filter(
                atendimento=atendimento, status='A'
            ).order_by('-dt_registro').first()

            atendimento.ultimo_perdas_ganhos = PerdasGanhos.objects.filter(
                atendimento=atendimento, status='A'
            ).order_by('-dt_registro').first()

        context.update({
            'atendimentos': atendimentos_filtrados,
            'estabelecimento': Estabelecimento.objects.get(pk=estabelecimento_id) if estabelecimento_id else None,
            'filtro': filtro,
            'titulo': "Gestão de Pacientes",
            'title': "gestao_pacientes",
            'cad_index': reverse_lazy('cadastros_index'),
        })

        return context
