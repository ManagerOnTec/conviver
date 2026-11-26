"""Views da Gestão de Tarefas e Documentos.

Espelha a estrutura da Agenda de Pacientes: contexto base (cad_index /
list_index / estabelecimento), liberação por `ParametrosGestaoDocumentos.pode`,
filtros em sessão, modais por POST na própria listagem e mensagens coloridas.
"""
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
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, UpdateView

from admin_cadastros.models import Estabelecimento
from dominios.utils import (
    CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin,
)

from .forms import (
    AnotacaoForm, DesvalidacaoForm, DocumentoFiltroForm, DocumentoForm,
    RenovacaoForm, TarefaFiltroForm, TarefaForm,
)
from .models import (
    ParametrosGestaoDocumentos, Tipo, Documento, Tarefa,
)


def _estabelecimento(request):
    estabelecimento_id = request.session.get('estabelecimento_id')
    if not estabelecimento_id:
        return None
    return Estabelecimento.objects.filter(pk=estabelecimento_id).first()


def _negado(request, mensagem):
    """Negação amigável (nunca 500 nem página branca)."""
    messages.warning(request, mensagem)
    return HttpResponseRedirect(reverse('cadastros_index'))


def _liberacao(request, acao):
    return ParametrosGestaoDocumentos.pode(
        request.user, _estabelecimento(request), acao)


class LiberacaoGTDmixin:
    """Bloqueia a view sem liberação (mesmo padrão do `LiberacaoAgendaMixin`)."""

    acao_gtd = 'ver'
    mensagem_negado = (
        'Você não tem acesso à Gestão de Tarefas e Documentos deste '
        'estabelecimento. Solicite a liberação em Admin > Parâmetros da '
        'Gestão de Documentos.')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not _liberacao(
                request, self.acao_gtd):
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
        'list_index': reverse_lazy('gtd_documento_listar'),
        'menu_gtd': True,
        'pode_ver': ParametrosGestaoDocumentos.pode(
            request.user, estabelecimento, 'ver'),
        'pode_editar': ParametrosGestaoDocumentos.pode(
            request.user, estabelecimento, 'editar'),
        'pode_excluir': ParametrosGestaoDocumentos.pode(
            request.user, estabelecimento, 'excluir'),
    }


def _querystring_filtros(filtros):
    return urlencode({
        campo: valor for campo, valor in (filtros or {}).items() if valor
    })


# ---------------------------------------------------------------------------
# DOCUMENTOS
# ---------------------------------------------------------------------------
def _dados_filtros_documento(request):
    campos = ('tipo', 'situacao', 'data_inicio', 'data_fim', 'q', 'status')
    dados = request.GET
    if 'limpar' in dados:
        request.session.pop('gtd_documento_filters', None)
        filtros = {}
    elif any(campo in dados for campo in campos):
        filtros = dados
    else:
        filtros = request.session.get('gtd_documento_filters') or {}
    return dict(filtros)


def _aplicar_filtros_documento(queryset, dados):
    filtros = {}

    status = dados.get('status')
    if status in ('A', 'I'):
        queryset = queryset.filter(status=status)
        filtros['status'] = status

    tipo = dados.get('tipo')
    if tipo:
        try:
            queryset = queryset.filter(tipo_id=int(tipo))
            filtros['tipo'] = str(tipo)
        except (TypeError, ValueError):
            pass

    situacao = dados.get('situacao')
    if situacao in (
            'vigente', 'proximo', 'vencido', 'aguardando_renovacao',
            'sem_vigencia'):
        hoje = timezone.localdate()
        if situacao == 'vigente':
            queryset = queryset.filter(
                vigencia_final__gte=hoje, status='A').filter(
                Q(inicio_renovacao__isnull=True)
                | Q(inicio_renovacao__gt=hoje))
        elif situacao == 'proximo':
            queryset = queryset.filter(
                vigencia_final__gte=hoje,
                vigencia_final__lte=hoje + timezone.timedelta(days=30),
                status='A')
        elif situacao == 'vencido':
            queryset = queryset.filter(
                vigencia_final__lt=hoje, status='A')
        elif situacao == 'aguardando_renovacao':
            queryset = queryset.filter(
                inicio_renovacao__lte=hoje, status='A').filter(
                Q(vigencia_final__isnull=True)
                | Q(vigencia_final__gte=hoje))
        elif situacao == 'sem_vigencia':
            queryset = queryset.filter(vigencia_final__isnull=True)
        filtros['situacao'] = situacao

    from datetime import date
    try:
        data_inicio = date.fromisoformat(dados.get('data_inicio')) \
            if dados.get('data_inicio') else None
    except (TypeError, ValueError):
        data_inicio = None
    try:
        data_fim = date.fromisoformat(dados.get('data_fim')) \
            if dados.get('data_fim') else None
    except (TypeError, ValueError):
        data_fim = None
    if data_inicio:
        queryset = queryset.filter(vigencia_final__gte=data_inicio)
        filtros['data_inicio'] = dados.get('data_inicio')
    if data_fim:
        queryset = queryset.filter(vigencia_final__lte=data_fim)
        filtros['data_fim'] = dados.get('data_fim')

    busca = (dados.get('q') or '').strip()
    if busca:
        queryset = queryset.filter(
            Q(descricao_documento__icontains=busca)
            | Q(anotacoes__icontains=busca)
            | Q(tipo__descricao__icontains=busca)
        )
        filtros['q'] = busca

    return queryset, filtros


def _kpis_documentos(request, queryset):
    """Indicadores clicáveis de DOCUMENTOS da barra superior."""
    hoje = timezone.localdate()
    vivos = queryset.filter(status='A')
    kpis = [
        ('Total de documentos', queryset.count(), '', 'kpi-blue'),
        ('Vigentes', vivos.filter(
            vigencia_final__gte=hoje).filter(
            Q(inicio_renovacao__isnull=True)
            | Q(inicio_renovacao__gt=hoje)).count(),
            'vigente', 'kpi-green'),
        ('Próximos do vencimento', vivos.filter(
            vigencia_final__gte=hoje,
            vigencia_final__lte=hoje + timezone.timedelta(days=30)).count(),
            'proximo', 'kpi-orange'),
        ('Vencidos', vivos.filter(vigencia_final__lt=hoje).count(),
            'vencido', 'kpi-red'),
        ('Aguardando renovação', vivos.filter(
            inicio_renovacao__lte=hoje).filter(
            Q(vigencia_final__isnull=True)
            | Q(vigencia_final__gte=hoje)).count(),
            'aguardando_renovacao', 'kpi-blue'),
    ]
    return [
        {'title': titulo, 'value': str(valor),
         'subtitle': '', 'color_class': cor, 'icon': '📑',
         'url': (f"{reverse('gtd_documento_listar')}?situacao={url_situacao}"
                 if url_situacao else '')}
        for titulo, valor, url_situacao, cor in kpis
    ]


def _kpis_tarefas(request, queryset=None):
    """Indicadores clicáveis de TAREFAS (listagem de tarefas)."""
    estabelecimento = _estabelecimento(request)
    base = Tarefa.objects.filter(estabelecimento=estabelecimento)
    pendentes = base.filter(status='P').count()
    em_andamento = base.filter(status='A').count()
    atrasadas = base.filter(status__in=('P', 'A'),
                            data_prazo__lt=timezone.localdate()).count()
    concluidas = base.filter(status='C').count()
    return [
        {'title': 'Tarefas pendentes', 'value': str(pendentes),
         'subtitle': '', 'color_class': 'kpi-orange', 'icon': '⏳',
         'url': f"{reverse('gtd_tarefa_listar')}?situacao=P"},
        {'title': 'Tarefas em andamento', 'value': str(em_andamento),
         'subtitle': '', 'color_class': 'kpi-blue', 'icon': '▶',
         'url': f"{reverse('gtd_tarefa_listar')}?situacao=A"},
        {'title': 'Tarefas atrasadas', 'value': str(atrasadas),
         'subtitle': '', 'color_class': 'kpi-red', 'icon': '🔥',
         'url': f"{reverse('gtd_tarefa_listar')}?situacao=atrasadas"},
        {'title': 'Tarefas concluídas', 'value': str(concluidas),
         'subtitle': '', 'color_class': 'kpi-green', 'icon': '✅',
         'url': f"{reverse('gtd_tarefa_listar')}?situacao=C"},
    ]


class DocumentoListView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGTDmixin, ListView):
    model = Documento
    template_name = 'gestao_tarefas_documentos/documento_listar.html'
    context_object_name = 'documentos'
    permission_required = 'gestao_tarefas_documentos.view_documento'
    login_url = reverse_lazy('login')
    paginate_by = 15
    acao_gtd = 'ver'

    def get_queryset(self):
        queryset = super().get_queryset().select_related('tipo')
        # Padrão do sistema: sem filtro escolhido, abre com status='A'
        # (Ativos); escolher “Inativos” na lista mostra os inativos.
        queryset = queryset.filter(
            status=self.request.GET.get('status') or 'A')
        dados = _dados_filtros_documento(self.request)
        queryset, self.filtros_sessao = _aplicar_filtros_documento(
            queryset, dados)
        self.request.session['gtd_documento_filters'] = self.filtros_sessao
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_contexto_base(
            self.request, 'Tarefas e Documentos', 'Documentos'))
        tipos = Tipo.objects.filter(status='A').order_by('descricao')
        context['filter_form'] = DocumentoFiltroForm(
            initial=self.filtros_sessao, tipos=tipos)
        context['gtd_filters'] = self.filtros_sessao
        context['filter'] = self.filtros_sessao
        context['querystring'] = _querystring_filtros(self.filtros_sessao)
        context['is_paginated'] = True
        context['today'] = timezone.localdate()
        context['kpis'] = _kpis_documentos(self.request, self.object_list)
        return context


class DocumentoCreateView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGTDmixin, CreateView):
    model = Documento
    form_class = DocumentoForm
    template_name = 'gestao_tarefas_documentos/documento_form.html'
    permission_required = 'gestao_tarefas_documentos.add_documento'
    login_url = reverse_lazy('login')
    success_url = reverse_lazy('gtd_documento_listar')
    acao_gtd = 'editar'
    mensagem_negado = (
        'Você não está liberado para editar documentos neste estabelecimento. '
        'Solicite a liberação em Admin > Parâmetros da Gestão de Documentos.')

    def form_valid(self, form):
        form.instance.estabelecimento = _estabelecimento(self.request)
        if not form.instance.estabelecimento:
            form.add_error(
                None, 'Selecione o estabelecimento na barra superior antes '
                      'de cadastrar o documento.')
            return self.form_invalid(form)
        form.instance.us_registro = self.request.user
        try:
            with transaction.atomic():
                response = super().form_valid(form)
                form.instance._historico(
                    'criacao', self.request.user,
                    'Documento cadastrado.')
        except ValidationError as erro:
            if hasattr(erro, 'error_dict'):
                for campo, erros in erro.error_dict.items():
                    campo_form = campo if campo in form.fields else None
                    for erro_campo in erros:
                        form.add_error(campo_form, erro_campo)
            else:
                form.add_error(None, erro)
            return self.form_invalid(form)
        messages.success(self.request, 'Documento cadastrado com sucesso.')
        return response

    def form_invalid(self, form):
        messages.warning(
            self.request, 'Revise os campos destacados para salvar o '
                          'documento.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_contexto_base(
            self.request, 'Tarefas e Documentos',
            'Novo Documento'))
        context['pode_editar'] = True
        context.setdefault('is_paginated', False)
        return context


class DocumentoUpdateView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGTDmixin, UpdateView):
    model = Documento
    form_class = DocumentoForm
    template_name = 'gestao_tarefas_documentos/documento_form.html'
    permission_required = 'gestao_tarefas_documentos.change_documento'
    login_url = reverse_lazy('login')
    success_url = reverse_lazy('gtd_documento_listar')
    acao_gtd = 'editar'

    def form_valid(self, form):
        form.instance.us_atualizacao = self.request.user
        form.instance.dt_atualizacao = timezone.now()
        mudou_anexo = 'anexo' in form.changed_data and form.instance.anexo
        try:
            with transaction.atomic():
                response = super().form_valid(form)
                if mudou_anexo:
                    form.instance._historico(
                        'anexo', self.request.user,
                        f'Anexo substituído por "{form.instance.anexo.name}".')
                else:
                    form.instance._historico(
                        'alteracao', self.request.user,
                        f'Campos alterados: '
                        f'{", ".join(form.changed_data) or "—"}.')
        except ValidationError as erro:
            if hasattr(erro, 'error_dict'):
                for campo, erros in erro.error_dict.items():
                    campo_form = campo if campo in form.fields else None
                    for erro_campo in erros:
                        form.add_error(campo_form, erro_campo)
            else:
                form.add_error(None, erro)
            return self.form_invalid(form)
        messages.success(self.request, 'Documento atualizado com sucesso.')
        return response

    def form_invalid(self, form):
        messages.warning(
            self.request, 'Revise os campos destacados para salvar o '
                          'documento.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_contexto_base(
            self.request, 'Tarefas e Documentos',
            'Editar Documento'))
        context['objeto'] = self.object
        context['pode_editar'] = True
        return context


class DocumentoDetailView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGTDmixin, DetailView):
    model = Documento
    template_name = 'gestao_tarefas_documentos/documento_detalhe.html'
    permission_required = 'gestao_tarefas_documentos.view_documento'
    login_url = reverse_lazy('login')
    context_object_name = 'documento'
    acao_gtd = 'ver'

    def get_queryset(self):
        return super().get_queryset().select_related('tipo', 'us_validacao')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_contexto_base(
            self.request, 'Tarefas e Documentos',
            'Detalhe do Documento'))
        context['objeto'] = self.object
        context['historico'] = self.object.historico.select_related(
            'usuario')
        context['tarefas'] = self.object.tarefas.all()
        # Form em modo LEITURA (padrão do detalhe da Agenda): todos os
        # campos desabilitados e exibidos como crispy fields.
        context['form'] = DocumentoForm(instance=self.object)
        for field in context['form'].fields.values():
            field.widget.attrs['disabled'] = True
        return context


def _retorno(request, fallback='gtd_documento_listar'):
    return redirect(request.META.get('HTTP_REFERER') or reverse(fallback))


class DocumentoValidarView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGTDmixin, View):
    """Validar documento (modal de confirmação da listagem)."""

    permission_required = 'gestao_tarefas_documentos.change_documento'
    acao_gtd = 'editar'

    def post(self, request, pk):
        documento = get_object_or_404(
            Documento, pk=pk,
            estabelecimento_id=request.session.get('estabelecimento_id'))
        if documento.validado:
            messages.info(request, 'Este documento já está validado.')
            return _retorno(request)
        observacao = (request.POST.get('observacao') or '').strip()
        try:
            with transaction.atomic():
                documento.validar(request.user, observacao)
        except ValidationError as erro:
            messages.warning(
                request, 'Não foi possível validar: ' +
                '; '.join(erro.messages))
            return _retorno(request)
        messages.success(request, 'Documento validado com sucesso.')
        return _retorno(request)


class DocumentoDesvalidarView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGTDmixin, View):
    """Desvalidar com justificativa (histórico preserva a validação)."""

    permission_required = 'gestao_tarefas_documentos.change_documento'
    acao_gtd = 'editar'

    def post(self, request, pk):
        documento = get_object_or_404(
            Documento, pk=pk,
            estabelecimento_id=request.session.get('estabelecimento_id'))
        if not documento.validado:
            messages.info(request, 'Este documento não está validado.')
            return _retorno(request)
        form = DesvalidacaoForm(request.POST)
        if not form.is_valid():
            messages.warning(
                request, '; '.join(
                    erro for erros in form.errors.values()
                    for erro in erros))
            return _retorno(request)
        try:
            with transaction.atomic():
                documento.desvalidar(request.user, form.cleaned_data['motivo'])
        except ValidationError as erro:
            messages.warning(
                request, 'Não foi possível desvalidar: ' +
                '; '.join(erro.messages))
            return _retorno(request)
        messages.success(
            request, 'Validação desfeita e registrada no histórico.')
        return _retorno(request)


class DocumentoRenovarView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGTDmixin, View):
    """Registrar renovação (novas vigências, próxima renovação e anexo)."""

    permission_required = 'gestao_tarefas_documentos.change_documento'
    acao_gtd = 'editar'

    def post(self, request, pk):
        documento = get_object_or_404(
            Documento, pk=pk,
            estabelecimento_id=request.session.get('estabelecimento_id'))
        form = RenovacaoForm(request.POST, request.FILES)
        if not form.is_valid():
            for campo, erros in form.errors.items():
                messages.warning(request, '; '.join(erros))
            return _retorno(request)
        dados = form.cleaned_data
        try:
            with transaction.atomic():
                documento.registrar_renovacao(
                    request.user,
                    dados['vigencia_inicial'], dados['vigencia_final'],
                    dados['inicio_renovacao'],
                    anexo=dados.get('anexo'),
                    observacao=dados.get('observacao') or '')
        except ValidationError as erro:
            if hasattr(erro, 'error_dict'):
                msg = '; '.join(
                    str(e) for erros in erro.error_dict.values() for e in erros)
            else:
                msg = '; '.join(erro.messages)
            messages.warning(request, f'Não foi possível renovar: {msg}')
            return _retorno(request)
        messages.success(request, 'Renovação registrada com sucesso.')
        return _retorno(request)


class DocumentoAnotarView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGTDmixin, View):
    """Adicionar anotação (as anteriores são preservadas)."""

    permission_required = 'gestao_tarefas_documentos.change_documento'
    acao_gtd = 'editar'

    def post(self, request, pk):
        documento = get_object_or_404(
            Documento, pk=pk,
            estabelecimento_id=request.session.get('estabelecimento_id'))
        form = AnotacaoForm(request.POST)
        if not form.is_valid():
            messages.warning(request, 'Informe a anotação.')
            return _retorno(request)
        try:
            with transaction.atomic():
                documento.registrar_anotacao(
                    request.user, form.cleaned_data['texto'])
        except ValidationError as erro:
            messages.warning(
                request, 'Não foi possível registrar: ' +
                '; '.join(erro.messages))
            return _retorno(request)
        messages.success(request, 'Anotação registrada com sucesso.')
        return _retorno(request)


class DocumentoInativarView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGTDmixin, View):
    """Inativação (nunca exclusão definitiva — preserva o histórico)."""

    permission_required = 'gestao_tarefas_documentos.delete_documento'
    acao_gtd = 'excluir'
    mensagem_negado = (
        'Você não está liberado para excluir/inativar documentos neste '
        'estabelecimento. Solicite a liberação em Admin > Parâmetros da '
        'Gestão de Documentos.')

    def post(self, request, pk):
        documento = get_object_or_404(
            Documento, pk=pk,
            estabelecimento_id=request.session.get('estabelecimento_id'))
        try:
            with transaction.atomic():
                documento.status = 'I'
                documento.us_atualizacao = request.user
                documento.dt_atualizacao = timezone.now()
                documento.save(update_fields=['status', 'us_atualizacao',
                                              'dt_atualizacao'])
                documento._historico(
                    'situacao', request.user,
                    'Documento INATIVADO (mantém histórico).')
        except ValidationError as erro:
            messages.warning(
                request, 'Não foi possível inativar: ' +
                '; '.join(erro.messages))
            return _retorno(request)
        messages.success(request, 'Documento inativado (histórico mantido).')
        return _retorno(request)


# ---------------------------------------------------------------------------
# TAREFAS
# ---------------------------------------------------------------------------
def _dados_filtros_tarefa(request):
    campos = ('documento', 'situacao', 'prioridade', 'q')
    dados = request.GET
    if 'limpar' in dados:
        request.session.pop('gtd_tarefa_filters', None)
        filtros = {}
    elif any(campo in dados for campo in campos):
        filtros = dados
    else:
        filtros = request.session.get('gtd_tarefa_filters') or {}
    return dict(filtros)


def _aplicar_filtros_tarefa(queryset, dados):
    filtros = {}

    documento = dados.get('documento')
    if documento:
        try:
            queryset = queryset.filter(documento_id=int(documento))
            filtros['documento'] = str(documento)
        except (TypeError, ValueError):
            pass

    situacao = dados.get('situacao')
    if situacao in ('P', 'A', 'C', 'X'):
        queryset = queryset.filter(status=situacao)
        filtros['situacao'] = situacao
    elif situacao == 'atrasadas':
        queryset = queryset.filter(
            status__in=('P', 'A'),
            data_prazo__lt=timezone.localdate())
        filtros['situacao'] = 'atrasadas'

    prioridade = dados.get('prioridade')
    if prioridade in ('B', 'M', 'A'):
        queryset = queryset.filter(prioridade=prioridade)
        filtros['prioridade'] = prioridade

    busca = (dados.get('q') or '').strip()
    if busca:
        queryset = queryset.filter(
            Q(titulo__icontains=busca)
            | Q(descricao__icontains=busca)
            | Q(anotacoes__icontains=busca)
            | Q(documento__tipo__descricao__icontains=busca)
            | Q(documento__descricao_documento__icontains=busca))
        filtros['q'] = busca

    return queryset, filtros


class TarefaListView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGTDmixin, ListView):
    model = Tarefa
    template_name = 'gestao_tarefas_documentos/tarefa_listar.html'
    context_object_name = 'tarefas'
    permission_required = 'gestao_tarefas_documentos.view_tarefa'
    login_url = reverse_lazy('login')
    paginate_by = 15
    acao_gtd = 'ver'

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'documento', 'documento__tipo', 'usuario_responsavel')
        queryset = queryset.filter(
            estabelecimento=_estabelecimento(self.request))
        dados = _dados_filtros_tarefa(self.request)
        queryset, self.filtros_sessao = _aplicar_filtros_tarefa(
            queryset, dados)
        self.request.session['gtd_tarefa_filters'] = self.filtros_sessao
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_contexto_base(
            self.request, 'Tarefas e Documentos', 'Tarefas'))
        documentos = Documento.objects.filter(
            estabelecimento=_estabelecimento(self.request), status='A')
        context['filter_form'] = TarefaFiltroForm(
            initial=self.filtros_sessao, documentos=documentos)
        context['gtd_filters'] = self.filtros_sessao
        context['filter'] = self.filtros_sessao
        context['querystring'] = _querystring_filtros(self.filtros_sessao)
        context['is_paginated'] = True
        context['today'] = timezone.localdate()
        context['kpis'] = _kpis_tarefas(self.request)
        return context


class TarefaCreateView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGTDmixin, CreateView):
    model = Tarefa
    form_class = TarefaForm
    template_name = 'gestao_tarefas_documentos/tarefa_form.html'
    permission_required = 'gestao_tarefas_documentos.add_tarefa'
    login_url = reverse_lazy('login')
    success_url = reverse_lazy('gtd_tarefa_listar')
    acao_gtd = 'editar'

    def form_valid(self, form):
        form.instance.estabelecimento = _estabelecimento(self.request)
        if not form.instance.estabelecimento:
            form.add_error(
                None, 'Selecione o estabelecimento na barra superior antes '
                      'de cadastrar a tarefa.')
            return self.form_invalid(form)
        form.instance.us_registro = self.request.user
        try:
            with transaction.atomic():
                response = super().form_valid(form)
                form.instance._historico(
                    'criacao', self.request.user, 'Tarefa cadastrada.')
        except ValidationError as erro:
            if hasattr(erro, 'error_dict'):
                for campo, erros in erro.error_dict.items():
                    campo_form = campo if campo in form.fields else None
                    for erro_campo in erros:
                        form.add_error(campo_form, erro_campo)
            else:
                form.add_error(None, erro)
            return self.form_invalid(form)
        messages.success(self.request, 'Tarefa cadastrada com sucesso.')
        return response

    def form_invalid(self, form):
        messages.warning(
            self.request, 'Revise os campos destacados para salvar a tarefa.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_contexto_base(
            self.request, 'Tarefas e Documentos', 'Nova Tarefa'))
        context['pode_editar'] = True
        context.setdefault('is_paginated', False)
        return context


class TarefaUpdateView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGTDmixin, UpdateView):
    model = Tarefa
    form_class = TarefaForm
    template_name = 'gestao_tarefas_documentos/tarefa_form.html'
    permission_required = 'gestao_tarefas_documentos.change_tarefa'
    login_url = reverse_lazy('login')
    success_url = reverse_lazy('gtd_tarefa_listar')
    acao_gtd = 'editar'

    def form_valid(self, form):
        form.instance.us_atualizacao = self.request.user
        form.instance.dt_atualizacao = timezone.now()
        try:
            with transaction.atomic():
                response = super().form_valid(form)
                form.instance._historico(
                    'alteracao', self.request.user,
                    f'Campos alterados: '
                    f'{", ".join(form.changed_data) or "—"}.')
        except ValidationError as erro:
            if hasattr(erro, 'error_dict'):
                for campo, erros in erro.error_dict.items():
                    campo_form = campo if campo in form.fields else None
                    for erro_campo in erros:
                        form.add_error(campo_form, erro_campo)
            else:
                form.add_error(None, erro)
            return self.form_invalid(form)
        messages.success(self.request, 'Tarefa atualizada com sucesso.')
        return response

    def form_invalid(self, form):
        messages.warning(
            self.request, 'Revise os campos destacados para salvar a tarefa.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_contexto_base(
            self.request, 'Tarefas e Documentos',
            'Editar Tarefa'))
        context['objeto'] = self.object
        context['pode_editar'] = True
        return context


def _tarefa_do_estabelecimento(request, pk):
    return get_object_or_404(
        Tarefa, pk=pk,
        estabelecimento_id=request.session.get('estabelecimento_id'))


class TarefaAcaoView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGTDmixin, View):
    """Transições de situação da tarefa: iniciar/concluir/reabrir/cancelar."""

    permission_required = 'gestao_tarefas_documentos.change_tarefa'
    acao_gtd = 'editar'
    acao_tarefa = None  # 'iniciar'|'concluir'|'reabrir'|'cancelar'

    def post(self, request, pk, acao=None):
        self.acao_tarefa = acao
        tarefa = _tarefa_do_estabelecimento(request, pk)
        texto = (request.POST.get('texto') or '').strip()
        try:
            with transaction.atomic():
                if self.acao_tarefa == 'iniciar':
                    if tarefa.status != 'P':
                        messages.info(
                            request,
                            'Só tarefas PENDENTES podem ser iniciadas.')
                        return _retorno(request, 'gtd_tarefa_listar')
                    tarefa.iniciar(request.user)
                    msg = 'Tarefa iniciada.'
                elif self.acao_tarefa == 'concluir':
                    if tarefa.status not in ('P', 'A'):
                        messages.info(
                            request,
                            'Só tarefas pendentes ou em andamento podem ser '
                            'concluídas.')
                        return _retorno(request, 'gtd_tarefa_listar')
                    tarefa.concluir(request.user, texto)
                    msg = 'Tarefa concluída.'
                elif self.acao_tarefa == 'reabrir':
                    if tarefa.status not in ('C', 'X'):
                        messages.info(
                            request,
                            'Só tarefas concluídas ou canceladas podem ser '
                            'reabertas.')
                        return _retorno(request, 'gtd_tarefa_listar')
                    tarefa.reabrir(request.user, texto)
                    msg = 'Tarefa reaberta.'
                else:  # cancelar
                    if tarefa.status in ('C', 'X'):
                        messages.info(
                            request,
                            'Esta tarefa já está concluída ou cancelada.')
                        return _retorno(request, 'gtd_tarefa_listar')
                    tarefa.cancelar(request.user, texto)
                    msg = 'Tarefa cancelada.'
        except ValidationError as erro:
            messages.warning(
                request, 'Não foi possível atualizar a tarefa: ' +
                '; '.join(erro.messages))
            return _retorno(request, 'gtd_tarefa_listar')
        messages.success(request, msg)
        return _retorno(request, 'gtd_tarefa_listar')


class TarefaAnotarView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGTDmixin, View):
    permission_required = 'gestao_tarefas_documentos.change_tarefa'
    acao_gtd = 'editar'

    def post(self, request, pk):
        tarefa = _tarefa_do_estabelecimento(request, pk)
        form = AnotacaoForm(request.POST)
        if not form.is_valid():
            messages.warning(request, 'Informe a anotação.')
            return _retorno(request, 'gtd_tarefa_listar')
        try:
            with transaction.atomic():
                tarefa.registrar_anotacao(
                    request.user, form.cleaned_data['texto'])
        except ValidationError as erro:
            messages.warning(
                request, 'Não foi possível registrar: ' +
                '; '.join(erro.messages))
            return _retorno(request, 'gtd_tarefa_listar')
        messages.success(request, 'Anotação registrada com sucesso.')
        return _retorno(request, 'gtd_tarefa_listar')


class TarefaInativarView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGTDmixin, View):
    """Inativação (status 'I') em vez de exclusão definitiva."""

    permission_required = 'gestao_tarefas_documentos.delete_tarefa'
    acao_gtd = 'excluir'
    mensagem_negado = (
        'Você não está liberado para excluir/inativar tarefas neste '
        'estabelecimento. Solicite a liberação em Admin > Parâmetros da '
        'Gestão de Documentos.')

    def post(self, request, pk):
        tarefa = _tarefa_do_estabelecimento(request, pk)
        try:
            with transaction.atomic():
                tarefa.status = 'X'
                tarefa.us_atualizacao = request.user
                tarefa.dt_atualizacao = timezone.now()
                tarefa.save(update_fields=['status', 'us_atualizacao',
                                           'dt_atualizacao'])
                tarefa._historico(
                    'alteracao', request.user,
                    'Tarefa CANCELADA/inativada (histórico mantido).')
        except ValidationError as erro:
            messages.warning(
                request, 'Não foi possível inativar: ' +
                '; '.join(erro.messages))
            return _retorno(request, 'gtd_tarefa_listar')
        messages.success(request, 'Tarefa cancelada (histórico mantido).')
        return _retorno(request, 'gtd_tarefa_listar')
