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
from django.views.generic.edit import CreateView, UpdateView

from admin_cadastros.models import Ala, Estabelecimento, Leito, Local, Setor
from atendimentos.models import Atendimento
from dominios.utils import (
    CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin,
)

from .forms import (
    LeitoMapaFiltroForm, OcupacaoForm, OcuparLeitoForm, SaidaLeitoForm,
    StatusLeitoForm, TransferenciaLeitoForm, _atendimentos_sem_leito,
)
from .models import (
    GESTAO_STATUS, GestaoLeito, HistoricoLeito, MovimentoLeito,
    ParametrosGestaoLeitos,
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
    """Filtros da sessão/GET como DICIONÁRIO de strings simples.

    `dict(request.GET)` transformaria cada valor em LISTA (QueryDict) e
    quebraria os filtros com `.strip()`/comparação — sempre converter para
    escalar (último valor).
    """
    campos = ('q', 'ala', 'setor', 'local', 'situacao', 'status')
    dados = request.GET
    if 'limpar' in dados:
        request.session.pop('gl_filters', None)
        filtros = {}
    elif any(campo in dados for campo in campos):
        filtros = dados
    else:
        filtros = request.session.get('gl_filters') or {}
    # QueryDict → dicionário de ESCALARES (getlist → último valor)
    return {chave: (valor[0] if isinstance(valor, (list, tuple))
                    else valor)
            for chave, valor in dict(filtros).items()}


def _aplicar_filtros_leitos(queryset, dados):
    """Filtros do mapa aplicados à hierarquia DE LEITOS (tabela Leito)."""
    filtros = {}

    try:
        busca = str(dados.get('q') or '').strip()
        if busca:
            queryset = queryset.filter(
                Q(leito__icontains=busca)
                | Q(local__nome__icontains=busca)
                | Q(gestao__atendimento__pessoa__nome__icontains=busca)
                | Q(gestao__atendimento__pessoa__cpf__icontains=busca))
            filtros['q'] = busca
    except Exception:
        pass  # filtro inválido nunca derruba a listagem

    for campo, caminho in (('ala', 'local__setor__ala'),
                           ('setor', 'local__setor'),
                           ('local', 'local')):
        valor = dados.get(campo)
        if valor:
            try:
                queryset = queryset.filter(**{f'{caminho}_id': int(valor)})
                filtros[campo] = str(valor)
            except (TypeError, ValueError):
                pass

    try:
        situacao = str(dados.get('situacao') or '')
        if situacao in ('O', 'L', 'B', 'H'):
            queryset = queryset.filter(gestao__situacao=situacao)
            filtros['situacao'] = situacao
    except Exception:
        pass

    try:
        status = str(dados.get('status') or '')
        if status in ('A', 'I'):
            queryset = queryset.filter(status=status)
            filtros['status'] = status
    except Exception:
        pass

    return queryset, filtros


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
        {'title': 'Taxa de ocupação', 'value': taxa, 'subtitle': '',
         'color_class': 'kpi-orange', 'icon': '📊', 'url': ''},
    ]


class LeitoMapView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        LiberacaoGLmixin, ListView):
    """MAPA DE LEITOS: ocupação por atendimento, filtros e KPIs."""

    template_name = 'gestao_leitos/leito_mapa.html'
    context_object_name = 'leitos'
    permission_required = 'gestao_leitos.view_gestao'
    login_url = reverse_lazy('login')
    paginate_by = 15
    acao_gl = 'ver'

    def get_queryset(self):
        """MAPA: TODOS os leitos ativos do estabelecimento — um por leito,
        com ou sem registro de gestão (o estado vem de `leito.gestao`)."""
        estabelecimento = _estabelecimento(self.request)
        queryset = Leito.objects.filter(
            status='A',
            local__setor__estabelecimento=estabelecimento,
            local__setor__ala__internacao=True,
        ).select_related(
            'local', 'local__setor', 'local__setor__ala',
            'gestao', 'gestao__atendimento', 'gestao__atendimento__pessoa',
        )
        dados = _dados_filtros(self.request)
        queryset, self.filtros_sessao = _aplicar_filtros_leitos(
            queryset, dados)
        self.request.session['gl_filters'] = self.filtros_sessao
        return queryset.order_by(
            'local__setor__ala__nome', 'local__setor__nome', 'leito')

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
        # Form dos modais de ocupação e transferência (select2 digitável);
        # o django_select2 injeta o request nos widgets na renderização.
        context['ocupar_form'] = OcuparLeitoForm(estabelecimento=estabelecimento)
        context['transferir_form'] = TransferenciaLeitoForm(
            estabelecimento=estabelecimento)
        # PACIENTES SEM LEITO: atendimentos ativos, sem alta e sem leito,
        # do estabelecimento da sessão (modal do menul).
        context['pacientes_sem_leito'] = _atendimentos_sem_leito(
            estabelecimento).select_related('pessoa')[:100]
        # Pode adicionar = permissão Django de ADD (usada no menul/botão).
        # Alinha com as demais telas: mostra o botão "Novo" quando o usuário
        # pode alterar a ocupação (registrar ocupação é função de gestor).
        context['pode_add'] = self.request.user.has_perm(
            'gestao_leitos.add_gestao') or \
            self.request.user.has_perm('gestao_leitos.change_gestao') and _liberacao(self.request, 'editar')
        # Leitos livres do estabelecimento (controla exibição do botão).
        context['leitos_livres'] = Leito.objects.filter(
            status='A', ocupado=False,
            local__setor__estabelecimento=estabelecimento,
            local__setor__ala__internacao=True)
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
        form = OcuparLeitoForm(request.POST, estabelecimento=estabelecimento)
        if not form.is_valid():
            messages.warning(request, '; '.join(
                erro for erros in form.errors.values() for erro in erros))
            return _retorno(request)
        dados = form.cleaned_data
        leito = dados['leito']
        if GestaoLeito.objects.filter(
                leito=leito, dt_saida__isnull=True, status='A').exists():
            messages.info(request, 'Este leito já está ocupado.')
            return _retorno(request)
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


class ExcluirOcupacaoView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        LiberacaoGLmixin, View):
    """EXCLUIR/LIBERAR registro do leito (botão lixeira da lista).

    Segue o padrão dos demais módulos: POST com confirmação. Ambos os
    botões (Excluir e Registrar saída) terminam com o leito em status
    LIVRE: aqui a linha NÃO é apagada — ela é atualizada para “Livre” com
    a data de saída de agora (o atendimento sai do leito), e o movimento é
    registrado. Só quem pode excluir vê o botão (`pode_excluir`).
    """

    permission_required = 'gestao_leitos.delete_gestao'
    acao_gl = 'excluir'
    mensagem_negado = (
        'Você não está liberado para excluir/liberar registros de leito '
        'neste estabelecimento. Solicite a liberação em Admin > Parâmetros '
        'da Gestão de Leitos.')

    def post(self, request, pk):
        ocupacao = _leito_do_estabelecimento(request, pk)
        try:
            with transaction.atomic():
                if ocupacao.dt_saida is None:
                    ocupacao.registrar_saida(
                        request.user,
                        observacoes='Registro excluído/liberado pelo usuário '
                                    '(leito liberado).')
                else:
                    # Já tinha saída: garante apenas o status LIVRE.
                    ocupacao.mudar_status(
                        request.user, 'L',
                        observacoes='Registro excluído/liberado pelo usuário.')
        except ValidationError as erro:
            messages.warning(
                request, 'Não foi possível excluir: ' + _erros_mensagem(erro))
            return _retorno(request)
        messages.success(
            request,
            f'Registro do leito {ocupacao.leito.leito} excluído; leito '
            f'liberado (status LIVRE).')
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


class RegistrarOcupacaoViewBase(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGLmixin):
    """Base das telas de REGISTRAR OCUPAÇÃO (tela própria, não modal).

    Contexto completo igual ao mapa (menul/cabdados/listar) e o form com os
    dois selects digitáveis (django_select2), com o `form.media` no template.
    """

    model = GestaoLeito
    form_class = OcupacaoForm
    context_object_name = 'ocupacao'
    login_url = reverse_lazy('login')
    success_url = reverse_lazy('gl_leito_mapa')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['estabelecimento'] = _estabelecimento(self.request)
        return kwargs

    def form_valid(self, form):
        estabelecimento = _estabelecimento(self.request)
        if not estabelecimento:
            form.add_error(
                None, 'Selecione o estabelecimento na barra superior antes '
                      'de registrar a ocupação.')
            return self.form_invalid(form)
        form.instance.estabelecimento = estabelecimento
        form.instance.us_registro = self.request.user
        try:
            with transaction.atomic():
                # UMA linha por LEITO: se o leito já tem registro de gestão,
                # atualiza (reocupação) em vez de criar outra.
                existente = GestaoLeito.objects.filter(
                    leito_id=form.instance.leito_id).first()
                import sys as _sys
                print('FV existente:', existente is not None,
                      '| post_at:', form.instance.atendimento_id, file=_sys.stderr)
                if existente is not None:
                    self.object = existente
                    self.object.atendimento = form.instance.atendimento
                    self.object.dt_entrada = (
                        form.instance.dt_entrada or timezone.now())
                    self.object.dt_saida = None
                    self.object.situacao = form.instance.situacao or 'O'
                    self.object.observacoes = form.instance.observacoes
                    self.object.us_atualizacao = self.request.user
                    self.object.dt_atualizacao = timezone.now()
                    self.object.save()
                    operacao = 'ocupacao'
                else:
                    response = super().form_valid(form)
                    operacao = None
                if self.object.atendimento_id:
                    self.object._historico(
                        operacao or 'ocupacao', self.request.user,
                        f'Leito ocupado pelo atendimento '
                        f'#{self.object.atendimento_id} '
                        f'({self.object.atendimento.pessoa}) em '
                        f'{timezone.localtime(self.object.dt_entrada):%d/%m/%Y %H:%M}.')
                else:
                    self.object._historico(
                        operacao or 'status', self.request.user,
                        f'Leito registrado como '
                        f'"{self.object.get_situacao_display()}" (sem '
                        f'atendimento) em '
                        f'{timezone.localtime(self.object.dt_entrada):%d/%m/%Y %H:%M}.')
                self.object._movimento(
                    operacao or 'ocupacao', self.request.user,
                    form.instance.observacoes or '')
        except ValidationError as erro:
            form.add_error(None, _erros_mensagem(erro))
            return self.form_invalid(form)
        messages.success(
            self.request,
            'Ocupação registrada com sucesso.'
            if self.object.atendimento_id
            else f'Leito registrado como '
                 f'"{self.object.get_situacao_display()}".')
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        messages.warning(
            self.request, 'Revise os campos destacados para registrar a '
                          'ocupação.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estabelecimento = _estabelecimento(self.request)
        context.update(_contexto_base(
            self.request, 'Gestão de Leitos',
            getattr(self, 'titulo_tela', 'Registrar Ocupação')))
        context['pode_editar'] = context['pode_editar']
        context.setdefault('is_paginated', False)
        # Dependentes dos selects (mesma fonte do filtro do mapa)
        context['alas'] = Ala.objects.filter(
            estabelecimento=estabelecimento, status='A').order_by('nome')
        context['setores'] = Setor.objects.filter(
            estabelecimento=estabelecimento, status='A').select_related('ala')
        context['locais'] = Local.objects.filter(
            status='A',
            setor__estabelecimento=estabelecimento,
            setor__ala__internacao=True).select_related(
            'setor', 'setor__ala')
        context['atendimentos_disponiveis'] = _atendimentos_sem_leito(
            estabelecimento).select_related('pessoa')[:200]
        return context


class RegistrarOcupacaoCreateView(RegistrarOcupacaoViewBase, CreateView):
    template_name = 'gestao_leitos/ocupacao_cadastrar.html'
    permission_required = 'gestao_leitos.add_gestao'
    acao_gl = 'editar'
    titulo_tela = 'Registrar Ocupação'

    def get_initial(self):
        initial = super().get_initial()
        initial.setdefault('dt_entrada', timezone.localtime()
                           .strftime('%Y-%m-%dT%H:%M'))
        initial.setdefault('situacao', 'O')
        # Pré-seleciona o leito (?leito=) e o ATENDIMENTO (?atendimento=)
        # vindos da listagem (modal “Pacientes sem Leitos”).
        leito_id = self.request.GET.get('leito')
        if leito_id:
            initial['leito'] = leito_id
        atendimento_id = self.request.GET.get('atendimento')
        if atendimento_id:
            atendimento = _atendimentos_sem_leito(_estabelecimento(
                self.request)).filter(pk=atendimento_id).first()
            if atendimento:
                initial['atendimento'] = atendimento
        return initial


class RegistrarOcupacaoUpdateView(RegistrarOcupacaoViewBase, UpdateView):
    template_name = 'gestao_leitos/ocupacao_editar.html'
    permission_required = 'gestao_leitos.change_gestao'
    acao_gl = 'editar'
    titulo_tela = 'Editar Ocupação'

    def get_initial(self):
        """TROCA de leito (?leito=<outro>): a ENTRADA no novo leito é AGORA
        por default (o usuário pode alterar); edição sem troca mantém a
        data existente."""
        initial = super().get_initial()
        leito_param = self.request.GET.get('leito')
        if leito_param and self.object and \
                str(self.object.leito_id) != str(leito_param):
            initial.setdefault(
                'dt_entrada', timezone.localtime().strftime('%Y-%m-%dT%H:%M'))
        return initial

    def form_valid(self, form):
        form.instance.us_atualizacao = self.request.user
        form.instance.dt_atualizacao = timezone.now()
        trocou_leito = 'leito' in form.changed_data
        try:
            with transaction.atomic():
                response = super().form_valid(form)
                if trocou_leito:
                    self.object._historico(
                        'transferencia', self.request.user,
                        f'Leito alterado para {self.object.leito} '
                        f'({self.object.leito.local.nome} / '
                        f'{self.object.leito.local.setor.nome}).')
        except ValidationError as erro:
            form.add_error(None, _erros_mensagem(erro))
            return self.form_invalid(form)
        messages.success(self.request, 'Ocupação atualizada com sucesso.')
        return response


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
        # MOVIMENTAÇÃO do leito (tabela auxiliar) — fica no DETALHE, nunca na
        # lista (o mapa mostra uma linha por leito com o estado atual).
        context['movimentos'] = self.object.leito.movimentos.select_related(
            'atendimento', 'atendimento__pessoa', 'usuario')
        # NAVEGADOR DE OBJETOS (padrão do projeto, como no Atendimento):
        # anterior/próximo dentro do recorte do estabelecimento da sessão.
        ids = list(GestaoLeito.objects.filter(
            estabelecimento_id=self.request.session.get(
                'estabelecimento_id')).values_list('pk', flat=True))
        if self.object.pk in ids:
            index = ids.index(self.object.pk)
            anterior_id = ids[index - 1] if index > 0 else None
            proximo_id = ids[index + 1] if index < len(ids) - 1 else None
            if len(ids) == 1:
                anterior_id = None
                proximo_id = None
            context['objeto_anterior'] = GestaoLeito.objects.filter(
                pk=anterior_id).first() if anterior_id else None
            context['proximo_objeto'] = GestaoLeito.objects.filter(
                pk=proximo_id).first() if proximo_id else None
        context['detail_url_name'] = 'gl_ocupacao_detalhe'
        context['nav_label'] = 'Navegar entre ocupações de leitos'
        return context
