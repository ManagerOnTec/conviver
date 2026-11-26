"""Views da Gestão de Leitos (padrão da Agenda/GTD/GP)."""
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView
from django.views.generic.edit import UpdateView

from admin_cadastros.models import Estabelecimento, Leito, Local, Setor
from atendimentos.models import Atendimento
from dominios.utils import (
    CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin,
)

from .forms import (
    LeitoMapaFiltroForm, OcuparLeitoForm, SaidaLeitoForm,
    StatusLeitoForm, TransferenciaLeitoForm, _atendimentos_sem_leito,
)
from .models import (
    GESTAO_STATUS, GestaoLeito, HistoricoLeito, ParametrosGestaoLeitos,
)


def _estabelecimento(request):
    estabelecimento_id = request.session.get('estabelecimento_id')
    if not estabelecimento_id:
        return None
    return Estabelecimento.objects.filter(pk=estabelecimento_id).first()


def _negado(request, mensagem):
    messages.warning(request, mensagem)
    return HttpResponseRedirect(reverse('cadastros_index'))


def _liberacao(request, acao):
    return ParametrosGestaoLeitos.pode(
        request.user, _estabelecimento(request), acao)


class LiberacaoGLmixin:
    acao_gl = 'ver'
    mensagem_negado = (
        'Você não tem acesso à Gestão de Leitos deste estabelecimento. '
        'Solicite a liberação em Admin > Parâmetros da Gestão de Leitos.')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not _liberacao(
                request, self.acao_gl):
            return _negado(request, self.mensagem_negado)
        return super().dispatch(request, *args, **kwargs)


def _contexto_base(request, titulo, title):
    estabelecimento = _estabelecimento(request)
    return {
        'titulo': titulo,
        'title': title,
        'func': title,
        'estabelecimento': estabelecimento,
        'cad_index': reverse_lazy('cadastros_index'),
        'list_index': reverse_lazy('gl_leito_mapa'),
        'menu_gl': True,
        'pode_ver': ParametrosGestaoLeitos.pode(
            request.user, estabelecimento, 'ver'),
        'pode_editar': ParametrosGestaoLeitos.pode(
            request.user, estabelecimento, 'editar'),
        'pode_excluir': ParametrosGestaoLeitos.pode(
            request.user, estabelecimento, 'excluir'),
    }


def _querystring_filtros(filtros):
    return urlencode({
        campo: valor for campo, valor in (filtros or {}).items() if valor
    })


def _retorno(request, fallback='gl_leito_mapa'):
    return redirect(request.META.get('HTTP_REFERER') or reverse(fallback))


def _erros_mensagem(erro):
    if hasattr(erro, 'error_dict'):
        return '; '.join(str(e) for erros in erro.error_dict.values()
                         for e in erros)
    return '; '.join(erro.messages)


# ---------------------------------------------------------------------------
# MAPA DE LEITOS
# ---------------------------------------------------------------------------
def _dados_filtros(request):
    campos = ('q', 'ala', 'setor', 'local', 'situacao', 'status')
    dados = request.GET
    if 'limpar' in dados:
        request.session.pop('gl_filters', None)
        filtros = {}
    elif any(campo in dados for campo in campos):
        filtros = dados
    else:
        filtros = request.session.get('gl_filters') or {}
    return dict(filtros)


def _aplicar_filtros(queryset, dados):
    filtros = {}

    busca = (dados.get('q') or '').strip()
    if busca:
        queryset = queryset.filter(
            Q(leito__leito__icontains=busca)
            | Q(leito__local__nome__icontains=busca)
            | Q(atendimento__pessoa__nome__icontains=busca)
            | Q(atendimento__pessoa__cpf__icontains=busca))
        filtros['q'] = busca

    for campo, caminho in (('ala', 'leito__local__setor__ala'),
                           ('setor', 'leito__local__setor'),
                           ('local', 'leito__local')):
        valor = dados.get(campo)
        if valor:
            try:
                queryset = queryset.filter(**{f'{caminho}_id': int(valor)})
                filtros[campo] = str(valor)
            except (TypeError, ValueError):
                pass

    situacao = dados.get('situacao')
    if situacao in ('O', 'L', 'B', 'H'):
        queryset = queryset.filter(situacao=situacao)
        filtros['situacao'] = situacao

    status = dados.get('status')
    if status in ('A', 'I'):
        queryset = queryset.filter(status=status)
        filtros['status'] = status

    return queryset, filtros


def _kpis_leitos(request, estabelecimento):
    """Indicadores navegáveis e coloridos do topo."""
    hoje = timezone.localdate()
    leitos_ativos = Leito.objects.filter(
        status='A', local__setor__estabelecimento=estabelecimento,
        local__setor__ala__internacao=True)
    total = leitos_ativos.count()
    ocupados = leitos_ativos.filter(ocupado=True).count()
    livres = total - ocupados

    vivos = GestaoLeito.objects.filter(
        status='A', estabelecimento=estabelecimento, dt_saida__isnull=True)
    bloqueados = vivos.filter(situacao='B').count()
    higienizacao = vivos.filter(situacao='H').count()
    internados = vivos.filter(situacao='O').count()

    # Pacientes do tipo PACIENTE internados (via atendimento.pessoa)
    internados_pacientes = vivos.filter(
        situacao='O', atendimento__pessoa__classificacao_pessoa='paciente') \
        .count()
    entradas_hoje = GestaoLeito.objects.filter(
        estabelecimento=estabelecimento,
        dt_entrada__date=hoje).count()
    altas_hoje = GestaoLeito.objects.filter(
        estabelecimento=estabelecimento,
        dt_saida__date=hoje).count()
    taxa = f'{(ocupados / total * 100):.0f}%' if total else '0%'

    base = reverse('gl_leito_mapa')
    return [
        {'title': 'Leitos ativos', 'value': str(total), 'subtitle': '',
         'color_class': 'kpi-blue', 'icon': '🛏', 'url': base},
        {'title': 'Ocupados', 'value': str(ocupados), 'subtitle': '',
         'color_class': 'kpi-green', 'icon': '🧑‍⚕️', 'url': f'{base}?situacao=O'},
        {'title': 'Livres', 'value': str(livres), 'subtitle': '',
         'color_class': 'kpi-blue', 'icon': '🟦', 'url': f'{base}?situacao=L'},
        {'title': 'Bloqueados', 'value': str(bloqueados), 'subtitle': '',
         'color_class': 'kpi-red', 'icon': '⛔', 'url': f'{base}?situacao=B'},
        {'title': 'Higienização', 'value': str(higienizacao), 'subtitle': '',
         'color_class': 'kpi-orange', 'icon': '🧹', 'url': f'{base}?situacao=H'},
        {'title': 'Internados (pacientes)', 'value': str(internados_pacientes),
         'subtitle': '', 'color_class': 'kpi-purple', 'icon': '👥',
         'url': f'{base}?situacao=O'},
        {'title': 'Internados hoje', 'value': str(entradas_hoje),
         'subtitle': '', 'color_class': 'kpi-blue', 'icon': '📥', 'url': ''},
        {'title': 'Altas hoje', 'value': str(altas_hoje), 'subtitle': '',
         'color_class': 'kpi-green', 'icon': '📤', 'url': ''},
        {'title': 'Taxa de ocupação', 'value': taxa, 'subtitle': '',
         'color_class': 'kpi-orange', 'icon': '📊', 'url': ''},
    ]


class LeitoMapView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        LiberacaoGLmixin, ListView):
    """MAPA DE LEITOS: ocupação por atendimento, filtros e KPIs."""

    template_name = 'gestao_leitos/leito_mapa.html'
    context_object_name = 'ocupacoes'
    permission_required = 'gestao_leitos.view_gestao'
    login_url = reverse_lazy('login')
    paginate_by = 15
    acao_gl = 'ver'

    def get_queryset(self):
        estabelecimento = _estabelecimento(self.request)
        queryset = GestaoLeito.objects.filter(
            estabelecimento=estabelecimento).select_related(
            'leito', 'leito__local', 'leito__local__setor',
            'leito__local__setor__ala', 'atendimento',
            'atendimento__pessoa')
        dados = _dados_filtros(self.request)
        queryset, self.filtros_sessao = _aplicar_filtros(queryset, dados)
        self.request.session['gl_filters'] = self.filtros_sessao
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_contexto_base(
            self.request, 'Gestão de Leitos', 'Mapa de Leitos'))
        estabelecimento = _estabelecimento(self.request)
        context['filter_form'] = LeitoMapaFiltroForm(
            initial=self.filtros_sessao, estabelecimento=estabelecimento)
        context['gl_filters'] = self.filtros_sessao
        context['filter'] = self.filtros_sessao
        context['querystring'] = _querystring_filtros(self.filtros_sessao)
        context['is_paginated'] = True
        context['today'] = timezone.localdate()
        context['kpis'] = _kpis_leitos(self.request, estabelecimento)
        # Opções dos modais: leitos livres do estabelecimento
        context['leitos_livres'] = Leito.objects.filter(
            status='A', ocupado=False,
            local__setor__estabelecimento=estabelecimento,
            local__setor__ala__internacao=True,
        ).select_related('local', 'local__setor', 'local__setor__ala')
        # Form do modal de ocupação (com o select2 de atendimento digitado);
        # o django_select2 injeta o request nos widgets na renderização.
        context['ocupar_form'] = OcuparLeitoForm(estabelecimento=estabelecimento)
        return context


def _leito_do_estabelecimento(request, pk):
    return get_object_or_404(
        GestaoLeito, pk=pk,
        estabelecimento_id=request.session.get('estabelecimento_id'))


class OcuparLeitoView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        LiberacaoGLmixin, View):
    """Ocupar leito (modal): atendimento sem alta/sem leito ativo."""

    permission_required = 'gestao_leitos.add_gestao'
    acao_gl = 'editar'

    def post(self, request, leito_id=None):
        estabelecimento = _estabelecimento(request)
        leito_id = leito_id or request.POST.get('leito')
        leito = get_object_or_404(
            Leito, pk=leito_id,
            local__setor__estabelecimento=estabelecimento)
        if GestaoLeito.objects.filter(
                leito=leito, dt_saida__isnull=True, status='A').exists():
            messages.info(request, 'Este leito já está ocupado.')
            return _retorno(request)
        form = OcuparLeitoForm(request.POST, estabelecimento=estabelecimento)
        if not form.is_valid():
            messages.warning(request, '; '.join(
                erro for erros in form.errors.values() for erro in erros))
            return _retorno(request)
        dados = form.cleaned_data
        try:
            with transaction.atomic():
                ocupacao = GestaoLeito(
                    leito=leito,
                    atendimento=dados['atendimento'],
                    dt_entrada=dados['dt_entrada'],
                    situacao='O',
                    observacoes=dados.get('observacoes') or '',
                    estabelecimento=estabelecimento,
                    us_registro=request.user)
                ocupacao.save()
                ocupacao._historico(
                    'ocupacao', request.user,
                    f'Leito ocupado pelo atendimento #{ocupacao.atendimento_id} '
                    f'({ocupacao.atendimento.pessoa}) em '
                    f'{timezone.localtime(ocupacao.dt_entrada):%d/%m/%Y %H:%M}.')
        except ValidationError as erro:
            messages.warning(
                request, 'Não foi possível ocupar: ' + _erros_mensagem(erro))
            return _retorno(request)
        messages.success(request, 'Leito ocupado com sucesso.')
        return _retorno(request)


class SaidaLeitoView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        LiberacaoGLmixin, View):
    """Registrar saída/alta do leito (libera e mantém histórico)."""

    permission_required = 'gestao_leitos.change_gestao'
    acao_gl = 'editar'

    def post(self, request, pk):
        ocupacao = _leito_do_estabelecimento(request, pk)
        form = SaidaLeitoForm(request.POST)
        if not form.is_valid():
            messages.warning(request, '; '.join(
                erro for erros in form.errors.values() for erro in erros))
            return _retorno(request)
        dados = form.cleaned_data
        try:
            with transaction.atomic():
                ocupacao.registrar_saida(
                    request.user, dt_saida=dados['dt_saida'],
                    observacoes=dados.get('observacoes') or '')
        except ValidationError as erro:
            messages.warning(
                request, 'Não foi possível registrar a saída: ' +
                _erros_mensagem(erro))
            return _retorno(request)
        messages.success(request, 'Saída registrada; leito liberado.')
        return _retorno(request)


class TransferirLeitoView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        LiberacaoGLmixin, View):
    """Trocar leito: fecha a ocupação atual e abre nova (transação única)."""

    permission_required = 'gestao_leitos.change_gestao'
    acao_gl = 'editar'

    def post(self, request, pk):
        ocupacao = _leito_do_estabelecimento(request, pk)
        if ocupacao.dt_saida is not None:
            messages.info(
                request, 'Esta ocupação já teve saída; abra uma nova '
                         'ocupação no leito destino.')
            return _retorno(request)
        form = TransferenciaLeitoForm(
            request.POST, leito_atual=ocupacao.leito,
            estabelecimento=ocupacao.estabelecimento)
        if not form.is_valid():
            messages.warning(request, '; '.join(
                erro for erros in form.errors.values() for erro in erros))
            return _retorno(request)
        destino = form.cleaned_data['leito_destino']
        try:
            with transaction.atomic():
                # Fecha a atual (sem mudar situação para 'L' — é transferência)
                ocupacao.dt_saida = timezone.now()
                ocupacao.us_atualizacao = request.user
                ocupacao.dt_atualizacao = timezone.now()
                ocupacao.save(update_fields=[
                    'dt_saida', 'us_atualizacao', 'dt_atualizacao'])
                ocupacao._historico(
                    'transferencia', request.user,
                    f'Transferido para o leito {destino} '
                    f'({destino.local.nome} / {destino.local.setor.nome}).')
                nova = GestaoLeito(
                    leito=destino,
                    atendimento=ocupacao.atendimento,
                    dt_entrada=timezone.now(),
                    situacao='O',
                    observacoes=form.cleaned_data.get('observacoes') or '',
                    estabelecimento=ocupacao.estabelecimento,
                    us_registro=request.user)
                nova.save()
                nova._historico(
                    'ocupacao', request.user,
                    f'Ocupação transferida do leito {ocupacao.leito} '
                    f'(atendimento #{ocupacao.atendimento_id}).')
        except ValidationError as erro:
            messages.warning(
                request, 'Não foi possível transferir: ' +
                _erros_mensagem(erro))
            return _retorno(request)
        messages.success(
            request, f'Atendimento transferido para o leito {destino.leito}.')
        return _retorno(request)


class StatusLeitoView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        LiberacaoGLmixin, View):
    """Bloquear/Desbloquear/Higienizar (mudança de situação com motivo)."""

    permission_required = 'gestao_leitos.change_gestao'
    acao_gl = 'editar'

    def post(self, request, pk):
        ocupacao = _leito_do_estabelecimento(request, pk)
        form = StatusLeitoForm(request.POST)
        if not form.is_valid():
            messages.warning(request, '; '.join(
                erro for erros in form.errors.values() for erro in erros))
            return _retorno(request)
        dados = form.cleaned_data
        try:
            with transaction.atomic():
                ocupacao.mudar_status(
                    request.user, dados['situacao'],
                    observacoes=dados.get('observacoes') or '')
        except ValidationError as erro:
            messages.warning(
                request, 'Não foi possível alterar: ' + _erros_mensagem(erro))
            return _retorno(request)
        messages.success(request, 'Situação do leito atualizada.')
        return _retorno(request)


class OcupacaoDetailView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        LiberacaoGLmixin, DetailView):
    model = GestaoLeito
    template_name = 'gestao_leitos/ocupacao_detalhe.html'
    permission_required = 'gestao_leitos.view_gestao'
    login_url = reverse_lazy('login')
    context_object_name = 'ocupacao'
    acao_gl = 'ver'

    def get_queryset(self):
        return super().get_queryset().select_related(
            'leito', 'leito__local', 'leito__local__setor',
            'leito__local__setor__ala', 'atendimento',
            'atendimento__pessoa')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_contexto_base(
            self.request, 'Gestão de Leitos', 'Detalhe da Ocupação'))
        context['objeto'] = self.object
        context['historico'] = self.object.historico.select_related('usuario')
        return context
