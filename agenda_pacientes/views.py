import csv
import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic.detail import SingleObjectMixin
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, UpdateView

from admin_cadastros.forms import PessoaDetailForm
from admin_cadastros.models import Estabelecimento, Local
from atendimentos.models import Atendimento
from dominios.utils import (
    CustomPermissionRequiredMixin,
    FilterObjectsByEstabelecimentoMixin,
    calcular_idade,
)

from .forms import AgendaPacienteForm
from .models import AgendaPaciente, ParametrosAgenda, TipoAgendamento


def _estabelecimento(request):
    estabelecimento_id = request.session.get('estabelecimento_id')
    if not estabelecimento_id:
        return None
    return Estabelecimento.objects.filter(pk=estabelecimento_id).first()


def _negado(request, mensagem):
    """Negação de acesso amigável (não deixa 500 nem página branca)."""
    messages.warning(request, mensagem)
    return HttpResponseRedirect(reverse('cadastros_index'))


def _liberacao(request, acao):
    """
    Liberação da agenda pelo admin (ParametrosAgenda).

    `acao`: 'ver' | 'editar' | 'excluir'. É concedida quando o usuário tem a
    permissão Django correspondente **e** está liberado no parâmetro do
    estabelecimento ativo (superusuário sempre é liberado).
    """
    return ParametrosAgenda.pode(
        request.user, _estabelecimento(request), acao)


def _adicionar_erros_validacao(form, erro):
    if hasattr(erro, 'error_dict'):
        for campo, erros in erro.error_dict.items():
            campo_form = campo if campo in form.fields else None
            for erro_campo in erros:
                form.add_error(campo_form, erro_campo)
        return
    form.add_error(None, erro)


class LiberacaoAgendaMixin:
    """Bloqueia a view quando o usuário não está liberado no admin agenda.

    `acao_agenda` = 'ver' | 'editar' | 'excluir'. A permissão Django vem do
    `CustomPermissionRequiredMixin` (permission_required).
    """

    acao_agenda = 'ver'
    mensagem_negado = (
        'Você não tem acesso à agenda de pacientes deste estabelecimento. '
        'Solicite a liberação em Admin > Parâmetros da Agenda.')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not _liberacao(
                request, self.acao_agenda):
            return _negado(request, self.mensagem_negado)
        return super().dispatch(request, *args, **kwargs)


def _contexto_base(request, titulo, title):
    """Contexto comum às telas de agenda (menu, estabelecimento, índices)."""
    estabelecimento = _estabelecimento(request)
    return {
        'titulo': titulo,
        'title': title,
        'func': title,
        'estabelecimento': estabelecimento,
        'cad_index': reverse_lazy('cadastros_index'),
        'list_index': reverse_lazy('agendapaciente_listar'),
        'menu_agenda': True,
        'pode_ver': ParametrosAgenda.pode(request.user, estabelecimento, 'ver'),
        'pode_editar': ParametrosAgenda.pode(
            request.user, estabelecimento, 'editar'),
        'pode_excluir': ParametrosAgenda.pode(
            request.user, estabelecimento, 'excluir'),
    }


def _querystring_filtros(filtros):
    """Filtros da sessão como querystring (links de paginação/relatório)."""
    from urllib.parse import urlencode

    return urlencode({
        campo: valor for campo, valor in (filtros or {}).items() if valor
    })


def _dados_filtros_lista(request):
    """Usa os mesmos filtros explícitos ou salvos para lista e download."""
    campos = ('tipo', 'efetuado', 'data_inicio', 'data_fim', 'q')
    dados = request.GET
    if 'limpar' in dados:
        request.session.pop('agenda_filters', None)
        return {}
    if not any(dados.get(campo) for campo in campos):
        return request.session.get('agenda_filters') or {}
    return dados


def _data(valor):
    try:
        return datetime.date.fromisoformat(valor)
    except (TypeError, ValueError):
        return None


def _aplicar_filtros(queryset, dados):
    """Aplica os filtros da listagem, sempre tolerante a valores inválidos."""
    filtros = {}

    try:
        tipo = dados.get('tipo')
        if tipo:
            queryset = queryset.filter(tipo_id=int(tipo))
            filtros['tipo'] = str(tipo)
    except (TypeError, ValueError):
        pass

    efetuado = dados.get('efetuado')
    if efetuado in ('S', 'N'):
        queryset = queryset.filter(efetuado=efetuado)
        filtros['efetuado'] = efetuado

    data_inicio = _data(dados.get('data_inicio'))
    data_fim = _data(dados.get('data_fim'))
    if data_inicio:
        queryset = queryset.filter(data_hora__date__gte=data_inicio)
        filtros['data_inicio'] = dados.get('data_inicio')
    if data_fim:
        queryset = queryset.filter(data_hora__date__lte=data_fim)
        filtros['data_fim'] = dados.get('data_fim')

    busca = (dados.get('q') or '').strip()
    if busca:
        queryset = queryset.filter(
            Q(atendimento__pessoa__nome__icontains=busca)
            | Q(atendimento__pessoa__cpf__icontains=busca)
            | Q(exame__tipo_exame__descricao__icontains=busca)
            | Q(local__nome__icontains=busca)
            | Q(tipo__descricao__icontains=busca)
            | Q(observacao__icontains=busca)
        )
        filtros['q'] = busca

    return queryset, filtros


class AgendaPacienteListView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoAgendaMixin, ListView):
    """Agendas de pacientes, por data, com filtros e download de relatório."""

    model = AgendaPaciente
    template_name = 'agenda_pacientes/agenda_listar.html'
    context_object_name = 'agendas'
    permission_required = 'agenda_pacientes.view_agendapaciente'
    login_url = reverse_lazy('login')
    paginate_by = 15
    acao_agenda = 'ver'

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'tipo', 'local', 'responsavel', 'atendimento',
            'atendimento__pessoa', 'exame', 'exame__tipo_exame',
        )
        queryset = queryset.filter(status='A')
        queryset = queryset.order_by('data_hora', 'pk')
        dados = _dados_filtros_lista(self.request)
        queryset, self.filtros_sessao = _aplicar_filtros(queryset, dados)
        self.request.session['agenda_filters'] = self.filtros_sessao
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_contexto_base(
            self.request, 'Agenda de Pacientes', 'Agenda de Pacientes'))
        context['tipos_agendamento'] = TipoAgendamento.objects.filter(
            status='A').order_by('descricao')
        context['agenda_filters'] = self.filtros_sessao
        context['filter'] = self.filtros_sessao
        context['querystring'] = _querystring_filtros(self.filtros_sessao)
        context['is_paginated'] = (
            context.get('paginator') is not None
            and context['paginator'].num_pages > 1)
        context['today'] = timezone.localdate()
        return context


class AgendaPacienteCreateView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoAgendaMixin, CreateView):
    model = AgendaPaciente
    form_class = AgendaPacienteForm
    template_name = 'agenda_pacientes/agenda_cadastrar.html'
    permission_required = 'agenda_pacientes.add_agendapaciente'
    login_url = reverse_lazy('login')
    success_url = reverse_lazy('agendapaciente_listar')
    acao_agenda = 'editar'
    mensagem_negado = (
        'Você não está liberado para agendar neste estabelecimento. '
        'Solicite a liberação em Admin > Parâmetros da Agenda.')

    def get_initial(self):
        initial = super().get_initial()
        atendimento_id = (
            self.request.GET.get('atendimento')
            or self.request.POST.get('atendimento'))
        if atendimento_id:
            atendimento = Atendimento.objects.filter(
                pk=atendimento_id,
                estabelecimento_id=self.request.session.get(
                    'estabelecimento_id'),
            ).first()
            if atendimento:
                initial['atendimento'] = atendimento
                tipo_exame = TipoAgendamento.objects.filter(
                    exige_exame_solicitado=True, status='A').first()
                if tipo_exame:
                    initial['tipo'] = tipo_exame
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['estabelecimento_id'] = self.request.session.get(
            'estabelecimento_id')
        return kwargs

    def form_valid(self, form):
        form.instance.estabelecimento = _estabelecimento(self.request)
        if not form.instance.estabelecimento:
            form.add_error(
                None,
                'Selecione o estabelecimento na barra superior antes de '
                'cadastrar uma agenda.')
            return self.form_invalid(form)
        form.instance.us_registro = self.request.user
        try:
            with transaction.atomic():
                response = super().form_valid(form)
        except ValidationError as erro:
            _adicionar_erros_validacao(form, erro)
            return self.form_invalid(form)
        except IntegrityError:
            form.add_error(
                'exame',
                'Este exame já possui um agendamento ativo. Consulte a data '
                'e o local na lista de exames.')
            return self.form_invalid(form)
        messages.success(self.request, 'Agendamento cadastrado com sucesso.')
        return response

    def form_invalid(self, form):
        messages.warning(
            self.request, 'Revise os campos destacados para salvar o '
                          'agendamento.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_contexto_base(
            self.request, 'Agenda de Pacientes', 'Novo Agendamento'))
        context['pode_editar'] = True
        context.setdefault('is_paginated', False)
        return context


class AgendaOpcoesView(LoginRequiredMixin, View):
    """Opções dependentes de tipo/atendimento, sempre limitadas à sessão."""

    def get(self, request):
        tem_permissao = any(
            request.user.has_perm(permissao)
            for permissao in (
                'agenda_pacientes.add_agendapaciente',
                'agenda_pacientes.change_agendapaciente',
            )
        )
        if not tem_permissao or not _liberacao(request, 'editar'):
            return JsonResponse(
                {'erro': 'Você não está liberado para editar a agenda.'},
                status=403)

        estabelecimento_id = request.session.get('estabelecimento_id')
        if not estabelecimento_id:
            return JsonResponse(
                {'erro': 'Selecione um estabelecimento antes de continuar.'},
                status=400)

        tipo_id = request.GET.get('tipo')
        tipo = None
        if tipo_id:
            try:
                tipo = TipoAgendamento.objects.get(pk=int(tipo_id), status='A')
            except (TipoAgendamento.DoesNotExist, TypeError, ValueError):
                return JsonResponse(
                    {'erro': 'Selecione um tipo de agendamento ativo.'},
                    status=400)

        locais = Local.objects.none()
        if tipo:
            locais = Local.objects.filter(status='A')
            if tipo.externo:
                locais = locais.filter(
                    Q(setor__estabelecimento_id=estabelecimento_id,
                      setor__ala__internacao=False)
                    | Q(setor__isnull=True, online='S'))
            else:
                locais = locais.filter(
                    setor__estabelecimento_id=estabelecimento_id,
                    setor__ala__internacao=True)
            if tipo.exige_local_online == 'S':
                locais = locais.filter(online='S')

        local_id = tipo.local_id if tipo else None
        atendimento_id = request.GET.get('atendimento')
        if atendimento_id:
            atendimento = Atendimento.objects.filter(
                pk=atendimento_id,
                estabelecimento_id=estabelecimento_id,
            ).first()
            if not atendimento:
                return JsonResponse(
                    {'erro': 'O atendimento não pertence ao estabelecimento '
                             'selecionado.'},
                    status=400)

        return JsonResponse({
            'exige_exame_solicitado': bool(
                tipo and tipo.exige_exame_solicitado),
            'local_obrigatorio': bool(
                tipo and (
                    not tipo.externo
                    or tipo.exige_local_online == 'S')),
            'local_padrao': local_id,
            'locais': [{
                'id': local.pk,
                'nome': (
                    f'{local.nome} — {local.setor.ala.nome} / '
                    f'{local.setor.nome}'
                    if local.setor_id else f'{local.nome} — Online'
                ),
            } for local in locais.select_related(
                'setor__ala').order_by('nome')],
        })


class AgendaPacienteUpdateView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoAgendaMixin, UpdateView):
    model = AgendaPaciente
    form_class = AgendaPacienteForm
    template_name = 'agenda_pacientes/agenda_editar.html'
    permission_required = 'agenda_pacientes.change_agendapaciente'
    login_url = reverse_lazy('login')
    success_url = reverse_lazy('agendapaciente_listar')
    acao_agenda = 'editar'
    mensagem_negado = (
        'Você não está liberado para alterar agendamentos neste '
        'estabelecimento. Solicite a liberação em Admin > Parâmetros da '
        'Agenda.')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['estabelecimento_id'] = self.request.session.get(
            'estabelecimento_id')
        return kwargs

    def form_valid(self, form):
        form.instance.us_atualizacao = self.request.user
        form.instance.dt_atualizacao = timezone.now()
        try:
            with transaction.atomic():
                response = super().form_valid(form)
        except ValidationError as erro:
            _adicionar_erros_validacao(form, erro)
            return self.form_invalid(form)
        except IntegrityError:
            form.add_error(
                'exame',
                'Este exame já possui um agendamento ativo. Consulte a data '
                'e o local na lista de exames.')
            return self.form_invalid(form)
        messages.success(self.request, 'Agendamento atualizado com sucesso.')
        return response

    def form_invalid(self, form):
        messages.warning(
            self.request, 'Revise os campos destacados para salvar o '
                          'agendamento.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_contexto_base(
            self.request, 'Agenda de Pacientes', 'Editar Agendamento'))
        context['objeto'] = self.object
        context['pode_editar'] = True
        return context


class AgendaPacienteDetailView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoAgendaMixin, DetailView):
    model = AgendaPaciente
    template_name = 'agenda_pacientes/agenda_detalhe.html'
    permission_required = 'agenda_pacientes.view_agendapaciente'
    login_url = reverse_lazy('login')
    context_object_name = 'agenda'
    acao_agenda = 'ver'

    def get_queryset(self):
        return super().get_queryset().select_related(
            'tipo', 'local', 'responsavel', 'atendimento',
            'atendimento__pessoa', 'exame')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_contexto_base(
            self.request, 'Agenda de Pacientes', 'Detalhe do Agendamento'))
        context['objeto'] = self.object
        context['form'] = AgendaPacienteForm(instance=self.object)
        for field in context['form'].fields.values():
            field.widget.attrs['disabled'] = True
        pessoa = self.object.atendimento.pessoa
        context['pessoa_form'] = PessoaDetailForm(instance=pessoa)
        context['idade'] = calcular_idade(pessoa.dt_nascimento)
        return context


class AgendaPacienteDeleteView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoAgendaMixin,
        SingleObjectMixin, View):
    model = AgendaPaciente
    permission_required = 'agenda_pacientes.delete_agendapaciente'
    login_url = reverse_lazy('login')
    acao_agenda = 'excluir'
    mensagem_negado = (
        'Você não está liberado para excluir agendamentos neste '
        'estabelecimento. Solicite a liberação em Admin > Parâmetros da '
        'Agenda.')

    def post(self, request, *args, **kwargs):
        agenda = self.get_object()
        try:
            agenda.delete()
        except ProtectedError:
            messages.warning(
                request,
                'Não foi possível excluir este agendamento porque ele está '
                'vinculado a outros registros. Verifique os vínculos e tente '
                'novamente.')
        else:
            messages.success(request, 'Agendamento excluído com sucesso.')

        url = reverse('agendapaciente_listar')
        querystring = request.GET.urlencode()
        return HttpResponseRedirect(
            f'{url}?{querystring}' if querystring else url)


class AgendaPacienteEfetuarView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoAgendaMixin, View):
    """Marca/desmarca o agendamento como efetuado (check da listagem)."""

    permission_required = 'agenda_pacientes.change_agendapaciente'
    acao_agenda = 'editar'
    mensagem_negado = (
        'Você não está liberado para alterar agendamentos neste '
        'estabelecimento. Solicite a liberação em Admin > Parâmetros da '
        'Agenda.')

    def get(self, request, pk):
        return self.post(request, pk)

    def post(self, request, pk):
        agenda = get_object_or_404(
            AgendaPaciente,
            pk=pk,
            estabelecimento_id=request.session.get('estabelecimento_id'),
        )
        desfazer = agenda.efetuado == 'S'
        try:
            with transaction.atomic():
                agenda.efetuar(usuario=request.user, desfazer=desfazer)
        except ValidationError as erro:
            messages.warning(
                request,
                f'Não foi possível atualizar o agendamento. '
                f'{"; ".join(erro.messages)}')
            return redirect(request.META.get('HTTP_REFERER')
                            or reverse('agendapaciente_listar'))
        except IntegrityError:
            messages.warning(
                request,
                'Não foi possível atualizar o agendamento porque já existe '
                'um resultado ou agendamento ativo vinculado ao exame.')
            return redirect(request.META.get('HTTP_REFERER')
                            or reverse('agendapaciente_listar'))
        if desfazer:
            messages.warning(request, 'Agendamento reaberto (não efetuado).'
                             + (' Execução do exame também desfeita.'
                                if agenda.exame_id else ''))
        else:
            messages.success(request, 'Agendamento marcado como efetuado.'
                             + (' Exame marcado como executado.'
                                if agenda.exame_id else ''))
        return redirect(request.META.get('HTTP_REFERER')
                        or reverse('agendapaciente_listar'))


class AgendaPacienteRelatorioView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoAgendaMixin, View):
    """Baixa em CSV todos os agendamentos correspondentes aos filtros."""

    permission_required = 'agenda_pacientes.view_agendapaciente'
    acao_agenda = 'ver'

    def get(self, request):
        estabelecimento_id = request.session.get('estabelecimento_id')
        queryset = AgendaPaciente.objects.filter(
            estabelecimento_id=estabelecimento_id, status='A').select_related(
            'tipo', 'local', 'responsavel', 'atendimento',
            'atendimento__pessoa', 'exame', 'exame__tipo_exame')
        dados = _dados_filtros_lista(request)
        queryset, _ = _aplicar_filtros(queryset, dados)
        queryset = queryset.order_by('data_hora', 'pk')
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = (
            'attachment; filename="agenda_pacientes.csv"')
        response.write('\ufeff')
        writer = csv.writer(response, delimiter=';')
        writer.writerow([
            'ID', 'Data/Hora', 'Paciente', 'Tipo', 'Exame', 'Local',
            'Atendimento', 'Responsável', 'Efetuado', 'Dt. Efetuado',
            'Anotação', 'Status', 'Dt. Registro', 'Us. Registro',
        ])
        for agenda in queryset:
            writer.writerow([
                agenda.pk,
                timezone.localtime(agenda.data_hora).strftime('%d/%m/%Y %H:%M'),
                agenda.atendimento.pessoa,
                agenda.tipo,
                agenda.exame or '',
                agenda.local or '',
                agenda.atendimento_id,
                agenda.responsavel or '',
                'Sim' if agenda.efetuado == 'S' else 'Não',
                timezone.localtime(agenda.dt_efetuado).strftime('%d/%m/%Y %H:%M')
                if agenda.dt_efetuado else '',
                agenda.observacao or '',
                agenda.get_status_display(),
                timezone.localtime(agenda.dt_registro).strftime('%d/%m/%Y %H:%M')
                if agenda.dt_registro else '',
                agenda.us_registro or '',
            ])
        return response


class AgendaExameListaView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, View):
    """
    Retorna as agendas de exames do atendimento em JSON — usado pelo header
    da listagem de exames do prontuário.
    """

    permission_required = 'agenda_pacientes.view_agendapaciente'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not _liberacao(request, 'ver'):
            return JsonResponse(
                {'agendas': [], 'erro': 'Sem liberação para a agenda.'},
                status=403)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, atendimento_id):
        estabelecimento_id = request.session.get('estabelecimento_id')
        atendimento = get_object_or_404(
            Atendimento, pk=atendimento_id,
            estabelecimento_id=estabelecimento_id)
        queryset = AgendaPaciente.objects.filter(
            estabelecimento_id=estabelecimento_id,
            atendimento=atendimento,
        ).filter(Q(status='A')).select_related(
            'tipo', 'local', 'exame').order_by('data_hora', 'pk')
        queryset = queryset.filter(exame__isnull=False)
        dados = [{
            'id': a.pk,
            'data_hora': timezone.localtime(a.data_hora).strftime(
                '%d/%m/%Y %H:%M'),
            'data_iso': timezone.localtime(a.data_hora).strftime(
                '%Y-%m-%dT%H:%M'),
            'local': a.local.nome if a.local else '',
            'tipo': a.tipo.descricao if a.tipo else '',
            'efetuado': a.efetuado == 'S',
            'observacao': a.observacao or '',
            'link_videochamada': a.link_videochamada or '',
            'link_whatsapp': a.link_whatsapp or '',
            'detalhe_url': reverse('agendapaciente_detalhe', args=[a.pk]),
            'editar_url': reverse('agendapaciente_editar', args=[a.pk]),
            'efetuar_url': reverse('agendapaciente_efetuar', args=[a.pk]),
        } for a in queryset]
        return JsonResponse({'agendas': dados})
