"""Views da Gestão de Pessoas.

Padrão da Agenda de Pacientes: contexto base (cad_index/list_index/
estabelecimento), liberação por `ParametrosGestaoPessoas.pode`, filtros em
sessão, modais por POST na própria listagem e histórico permanente.
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

from admin_cadastros.models import Estabelecimento, Pessoa
from dominios.utils import (
    CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin,
)

from .forms import (
    AsoAgendarForm, AsoRegistrarForm, CartaoPontoForm, CursoFuncionarioForm,
    DocumentoFuncionarioForm, FeriasForm, FichaRegistroForm,
    FuncionarioForm,
    PeriodicoAgendarForm, PeriodicoRegistrarForm,
)
from .models import (
    ASO, CartaoPonto, CursoFuncionario, DocumentoFuncionario, ExamePeriodico,
    Ferias, FichaRegistro, Funcionario, ParametrosGestaoPessoas,
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
    return ParametrosGestaoPessoas.pode(
        request.user, _estabelecimento(request), acao)


class LiberacaoGPmixin:
    acao_gp = 'ver'
    mensagem_negado = (
        'Você não tem acesso à Gestão de Pessoas deste estabelecimento. '
        'Solicite a liberação em Admin > Parâmetros da Gestão de Pessoas.')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not _liberacao(
                request, self.acao_gp):
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
        'list_index': reverse_lazy('gp_funcionario_listar'),
        'menu_gp': True,
        'pode_ver': ParametrosGestaoPessoas.pode(
            request.user, estabelecimento, 'ver'),
        'pode_editar': ParametrosGestaoPessoas.pode(
            request.user, estabelecimento, 'editar'),
        'pode_excluir': ParametrosGestaoPessoas.pode(
            request.user, estabelecimento, 'excluir'),
    }


def _querystring_filtros(filtros):
    return urlencode({
        campo: valor for campo, valor in (filtros or {}).items() if valor
    })


def _retorno(request, fallback='gp_funcionario_listar'):
    return redirect(request.META.get('HTTP_REFERER') or reverse(fallback))


def _erros_mensagem(erro):
    if hasattr(erro, 'error_dict'):
        return '; '.join(str(e) for erros in erro.error_dict.values()
                         for e in erros)
    return '; '.join(erro.messages)


# ---------------------------------------------------------------------------
# FUNCIONÁRIOS
# ---------------------------------------------------------------------------
def _dados_filtros_funcionario(request):
    campos = ('q', 'situacao', 'admissao_inicio', 'admissao_fim',
              'sem_aso_agendado', 'sem_ficha', 'sem_periodico',
              'cursos_vencidos', 'ferias_pendentes')
    dados = request.GET
    if 'limpar' in dados:
        request.session.pop('gp_filters', None)
        filtros = {}
    elif any(campo in dados for campo in campos):
        filtros = dados
    else:
        filtros = request.session.get('gp_filters') or {}
    return dict(filtros)


def _aplicar_filtros_funcionario(queryset, dados):
    filtros = {}

    busca = (dados.get('q') or '').strip()
    if busca:
        queryset = queryset.filter(
            Q(pessoa__nome__icontains=busca)
            | Q(pessoa__cpf__icontains=busca))
        filtros['q'] = busca

    situacao = dados.get('situacao')
    if situacao in ('A', 'F', 'D'):
        queryset = queryset.filter(status_funcionario=situacao)
        filtros['situacao'] = situacao

    from datetime import date
    try:
        inicio = date.fromisoformat(dados['admissao_inicio']) \
            if dados.get('admissao_inicio') else None
    except (TypeError, ValueError):
        inicio = None
    try:
        fim = date.fromisoformat(dados['admissao_fim']) \
            if dados.get('admissao_fim') else None
    except (TypeError, ValueError):
        fim = None
    if inicio:
        queryset = queryset.filter(data_admissao__gte=inicio)
        filtros['admissao_inicio'] = dados.get('admissao_inicio')
    if fim:
        queryset = queryset.filter(data_admissao__lte=fim)
        filtros['admissao_fim'] = dados.get('admissao_fim')

    hoje = timezone.localdate()
    if dados.get('sem_aso_agendado'):
        queryset = queryset.exclude(
            pk__in=ASO.objects.filter(status__in=('AG', 'R'))
            .values('funcionario_id'))
        filtros['sem_aso_agendado'] = '1'
    if dados.get('sem_ficha'):
        queryset = queryset.exclude(
            pk__in=FichaRegistro.objects.values('funcionario_id'))
        filtros['sem_ficha'] = '1'
    if dados.get('sem_periodico'):
        queryset = queryset.exclude(
            pk__in=ExamePeriodico.objects.filter(status__in=('AG', 'R'))
            .values('funcionario_id'))
        filtros['sem_periodico'] = '1'
    if dados.get('cursos_vencidos'):
        queryset = queryset.filter(
            cursos_funcionario__status='R',
            cursos_funcionario__data_validade__lt=hoje).distinct()
        filtros['cursos_vencidos'] = '1'
    if dados.get('ferias_pendentes'):
        queryset = queryset.filter(
            ferias__status__in=('P', 'G', 'E')).distinct()
        filtros['ferias_pendentes'] = '1'

    return queryset, filtros


def _kpis_funcionarios(request, queryset):
    hoje = timezone.localdate()
    ativos = queryset.filter(status_funcionario='A')
    sem_aso = queryset.exclude(
        pk__in=ASO.objects.filter(status__in=('AG', 'R'))
        .values('funcionario_id')).count()
    aso_agendado = ASO.objects.filter(
        status='AG', funcionario__in=queryset).count()
    sem_periodico = queryset.exclude(
        pk__in=ExamePeriodico.objects.filter(status__in=('AG', 'R'))
        .values('funcionario_id')).count()
    sem_ficha = queryset.exclude(
        pk__in=FichaRegistro.objects.values('funcionario_id')).count()
    cursos_vencidos = queryset.filter(
        cursos_funcionario__status='R',
        cursos_funcionario__data_validade__lt=hoje).distinct().count()
    cursos_pendentes = queryset.filter(
        cursos_funcionario__status='P').distinct().count()
    ferias_limite = Ferias.objects.filter(
        funcionario__in=queryset, status__in=('P', 'G'),
        periodo_concessivo_final__lte=hoje + timezone.timedelta(days=30)
    ).count()
    base = reverse('gp_funcionario_listar')
    return [
        {'title': 'Funcionários ativos', 'value': str(ativos.count()),
         'subtitle': '', 'color_class': 'kpi-green', 'icon': '👥',
         'url': f'{base}?situacao=A'},
        {'title': 'Sem ficha de registro', 'value': str(sem_ficha),
         'subtitle': '', 'color_class': 'kpi-red', 'icon': '📄',
         'url': f'{base}?sem_ficha=1'},
        {'title': 'ASO não agendado', 'value': str(sem_aso),
         'subtitle': '', 'color_class': 'kpi-red', 'icon': '🩺',
         'url': f'{base}?sem_aso_agendado=1'},
        {'title': 'ASO agendado', 'value': str(aso_agendado),
         'subtitle': '', 'color_class': 'kpi-blue', 'icon': '📅',
         'url': ''},
        {'title': 'Periódico pendente', 'value': str(sem_periodico),
         'subtitle': '', 'color_class': 'kpi-orange', 'icon': '🔬',
         'url': f'{base}?sem_periodico=1'},
        {'title': 'Cursos vencidos', 'value': str(cursos_vencidos),
         'subtitle': '', 'color_class': 'kpi-red', 'icon': '🎓',
         'url': f'{base}?cursos_vencidos=1'},
        {'title': 'Cursos pendentes', 'value': str(cursos_pendentes),
         'subtitle': '', 'color_class': 'kpi-orange', 'icon': '🎓',
         'url': ''},
        {'title': 'Férias próximas do limite', 'value': str(ferias_limite),
         'subtitle': '', 'color_class': 'kpi-purple', 'icon': '🏖',
         'url': f'{base}?ferias_pendentes=1'},
    ]


class FuncionarioListView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGPmixin, ListView):
    """TELA PRINCIPAL: todas as informações do funcionário em uma listagem."""

    model = Funcionario
    template_name = 'gestao_pessoas/funcionario_listar.html'
    context_object_name = 'funcionarios'
    permission_required = 'gestao_pessoas.view_funcionario'
    login_url = reverse_lazy('login')
    paginate_by = 15
    acao_gp = 'ver'

    def get_queryset(self):
        queryset = super().get_queryset().select_related('pessoa')
        queryset = queryset.filter(status='A')
        dados = _dados_filtros_funcionario(self.request)
        queryset, self.filtros_sessao = _aplicar_filtros_funcionario(
            queryset, dados)
        self.request.session['gp_filters'] = self.filtros_sessao
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_contexto_base(
            self.request, 'Gestão de Pessoas', 'Funcionários'))
        context['gp_filters'] = self.filtros_sessao
        context['filter'] = self.filtros_sessao
        # Filtros do menu lateral (padrão da Agenda: form crispy único).
        from .forms import FuncionarioFiltroForm
        context['filter_form'] = FuncionarioFiltroForm(
            initial=self.filtros_sessao)
        context['querystring'] = _querystring_filtros(self.filtros_sessao)
        context['is_paginated'] = True
        context['today'] = timezone.localdate()
        # prefetch dos relacionamentos de coluna
        funcionarios = context['funcionarios']
        if hasattr(funcionarios, 'object_list'):
            funcionarios = funcionarios.object_list
        for funcionario in funcionarios:
            funcionario.documentos_lista = funcionario.documentos.all()
            funcionario.aso_lista = funcionario.asos.all()
            funcionario.periodico_lista = funcionario.exames_periodicos.all()
            funcionario.cursos_lista = funcionario.cursos_funcionario \
                .select_related('curso')
            funcionario.ferias_lista = funcionario.ferias.all()
        # KPIs sobre o queryset NÃO paginado (o paginado é uma slice).
        context['kpis'] = _kpis_funcionarios(
            self.request, self.get_queryset())
        # Cursos ativos para os modais (registrar realizado/pendente)
        from .models import Curso
        context['cursos'] = Curso.objects.filter(status='A').order_by('nome')
        # FUNCIONÁRIOS PENDENTES: pessoas do tipo FUNCIONÁRIO ATIVAS do
        # estabelecimento da sessão SEM registro na lista (modal do menul;
        # o clique abre o cadastro com a pessoa já carregada).
        from admin_cadastros.models import Pessoa
        estabelecimento = _estabelecimento(self.request)
        registradas = Funcionario.objects.filter(
            estabelecimento=estabelecimento).values_list('pessoa_id',
                                                         flat=True)
        context['funcionarios_pendentes'] = Pessoa.objects.filter(
            status='A', classificacao_pessoa='funcionario',
        ).exclude(pk__in=registradas).order_by('nome')[:100]
        return context




class FuncionarioCreateView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGPmixin, CreateView):
    model = Funcionario
    form_class = FuncionarioForm
    template_name = 'gestao_pessoas/funcionario_form.html'
    permission_required = 'gestao_pessoas.add_funcionario'
    login_url = reverse_lazy('login')
    success_url = reverse_lazy('gp_funcionario_listar')
    acao_gp = 'editar'

    def get_initial(self):
        """PRÉ-CARGA: pessoa clicada no modal “Funcionários sem Registro”
        (?pessoa=<pk>) já inicia o objeto de cadastro."""
        initial = super().get_initial()
        pessoa_id = self.request.GET.get('pessoa')
        if pessoa_id:
            pessoa = Pessoa.objects.filter(
                pk=pessoa_id, classificacao_pessoa='funcionario',
                status='A').first()
            if pessoa:
                initial['pessoa'] = pessoa.pk
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # PRÉ-CARGA pelo modal: a pessoa escolhida já vem selecionada.
        pessoa_id = self.request.GET.get('pessoa')
        if pessoa_id:
            kwargs['pessoa_pre_carga'] = Pessoa.objects.filter(
                pk=pessoa_id).first()
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Estabelecimento não é editável (padrão do projeto: vem da sessão).
        form.fields.pop('estabelecimento', None)
        return form
        # O ESTABELECIMENTO sai do formulário: é o da SESSÃO (padrão do
        # projeto — usuário nunca escolhe).
        form.fields.pop('estabelecimento', None)
        return form

    def form_valid(self, form):
        # PADRÃO DO PROJETO: todo objeto novo grava usuário logado e o
        # ESTABELECIMENTO DA SESSÃO (nunca escolhido pelo usuário).
        form.instance.estabelecimento = _estabelecimento(self.request)
        if not form.instance.estabelecimento:
            form.add_error(
                None, 'Selecione o estabelecimento na barra superior antes '
                      'de cadastrar o funcionário.')
            return self.form_invalid(form)
        form.instance.usuario_cadastro = self.request.user
        try:
            with transaction.atomic():
                response = super().form_valid(form)
                form.instance._historico(
                    'criacao', self.request.user,
                    f'Funcionário cadastrado (admissão '
                    f'{form.instance.data_admissao:%d/%m/%Y}).')
        except ValidationError as erro:
            form.add_error(None, _erros_mensagem(erro))
            return self.form_invalid(form)
        messages.success(self.request, 'Funcionário cadastrado com sucesso.')
        return response

    def form_invalid(self, form):
        messages.warning(
            self.request, 'Revise os campos destacados para salvar o '
                          'funcionário.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_contexto_base(
            self.request, 'Gestão de Pessoas', 'Novo Funcionário'))
        context['pode_editar'] = True
        context.setdefault('is_paginated', False)
        return context


class FuncionarioUpdateView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGPmixin, UpdateView):
    model = Funcionario
    form_class = FuncionarioForm
    template_name = 'gestao_pessoas/funcionario_form.html'
    permission_required = 'gestao_pessoas.change_funcionario'
    login_url = reverse_lazy('login')
    success_url = reverse_lazy('gp_funcionario_listar')
    acao_gp = 'editar'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['pessoa'].queryset = Pessoa.objects.filter(
            status='A').order_by('nome')
        # Estabelecimento não é editável (padrão do projeto: vem da sessão).
        form.fields.pop('estabelecimento', None)
        return form

    def form_valid(self, form):
        form.instance.usuario_atualizacao = self.request.user
        form.instance.dt_atualizacao = timezone.now()
        mudou_situacao = (
            'status_funcionario' in form.changed_data
            and form.instance.status_funcionario)
        try:
            with transaction.atomic():
                response = super().form_valid(form)
                if mudou_situacao:
                    form.instance._historico(
                        'situacao', self.request.user,
                        f'Situação funcional alterada para '
                        f'"{form.instance.get_status_funcionario_display()}".')
                else:
                    form.instance._historico(
                        'alteracao', self.request.user,
                        f'Campos alterados: '
                        f'{", ".join(form.changed_data) or "—"}.')
        except ValidationError as erro:
            form.add_error(None, _erros_mensagem(erro))
            return self.form_invalid(form)
        messages.success(self.request, 'Funcionário atualizado com sucesso.')
        return response

    def form_invalid(self, form):
        messages.warning(
            self.request, 'Revise os campos destacados para salvar o '
                          'funcionário.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_contexto_base(
            self.request, 'Gestão de Pessoas', 'Editar Funcionário'))
        context['objeto'] = self.object
        context['pode_editar'] = True
        return context


class FuncionarioDetailView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGPmixin, DetailView):
    model = Funcionario
    template_name = 'gestao_pessoas/funcionario_detalhe.html'
    permission_required = 'gestao_pessoas.view_funcionario'
    login_url = reverse_lazy('login')
    context_object_name = 'funcionario'
    acao_gp = 'ver'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_contexto_base(
            self.request, 'Gestão de Pessoas', 'Detalhe do Funcionário'))
        context['objeto'] = self.object
        context['historico'] = self.object.historico.select_related('usuario')
        # Form em modo LEITURA (padrão do detalhe da Agenda).
        from django.forms.models import modelform_factory
        context['form'] = modelform_factory(
            Funcionario, fields=['pessoa', 'data_admissao',
                                 'status_funcionario', 'anotacoes'])(
                instance=self.object)
        for field in context['form'].fields.values():
            field.widget.attrs['disabled'] = True
        return context


# ---------------------------------------------------------------------------
# MODAIS (POST por funcionário) — cada um registra histórico
# ---------------------------------------------------------------------------
def _funcionario(request, pk):
    return get_object_or_404(
        Funcionario, pk=pk,
        estabelecimento_id=request.session.get('estabelecimento_id'))


class DocumentoFuncionarioView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGPmixin, View):
    """Anexar documento (modal); nunca apaga os anteriores."""

    permission_required = 'gestao_pessoas.change_funcionario'
    acao_gp = 'editar'

    def post(self, request, pk):
        funcionario = _funcionario(request, pk)
        form = DocumentoFuncionarioForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.warning(request, '; '.join(
                erro for erros in form.errors.values() for erro in erros))
            return _retorno(request)
        try:
            with transaction.atomic():
                documento = form.save(commit=False)
                documento.funcionario = funcionario
                documento.usuario_cadastro = request.user
                documento.save()
                funcionario._historico(
                    'documento', request.user,
                    f'Documento "{documento.tipo_documento}" anexado '
                    f'(dt. {documento.data_documento:%d/%m/%Y}).')
        except ValidationError as erro:
            messages.warning(
                request, 'Não foi possível anexar: ' + _erros_mensagem(erro))
            return _retorno(request)
        messages.success(request, 'Documento anexado com sucesso.')
        return _retorno(request)


class DocumentoExcluirView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGPmixin, View):
    """Excluir documento funcional (com registro no histórico)."""

    permission_required = 'gestao_pessoas.change_funcionario'
    acao_gp = 'editar'

    def post(self, request, pk, documento_id):
        funcionario = _funcionario(request, pk)
        documento = get_object_or_404(
            DocumentoFuncionario, pk=documento_id, funcionario=funcionario)
        with transaction.atomic():
            funcionario._historico(
                'documento', request.user,
                f'Documento "{documento.tipo_documento}" excluído.')
            documento.delete()
        messages.success(request, 'Documento excluído.')
        return _retorno(request)


class AsoView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGPmixin, View):
    """ASO por modal: agendar / registrar realização.

    NÃO apaga o histórico: agendar cria um ASO novo (status AG); registrar
    preenche realização/validade/anexo do ASO agendado. O botão “visualizar”
    lista todos os ASOs anteriores.
    """

    permission_required = 'gestao_pessoas.change_funcionario'
    acao_gp = 'editar'

    def post(self, request, pk, acao):
        funcionario = _funcionario(request, pk)
        if acao == 'agendar':
            form = AsoAgendarForm(request.POST)
            if not form.is_valid():
                messages.warning(request, '; '.join(
                    erro for erros in form.errors.values() for erro in erros))
                return _retorno(request)
            with transaction.atomic():
                ASO.objects.create(
                    funcionario=funcionario,
                    tipo_exame=form.cleaned_data['tipo_exame'],
                    data_agendamento=form.cleaned_data['data_agendamento'],
                    status='AG',
                    usuario_cadastro=request.user)
                funcionario._historico(
                    'aso_agendamento', request.user,
                    f'ASO ({form.cleaned_data["tipo_exame"]}) agendado para '
                    f'{form.cleaned_data["data_agendamento"]:%d/%m/%Y}.')
            messages.success(request, 'ASO agendado com sucesso.')
            return _retorno(request)

        if acao == 'registrar':
            # registra no ASO agendado mais recente (sem cancelar o histórico)
            aso = funcionario.asos.filter(status='AG').order_by(
                '-pk').first()
            if aso is None:
                # nenhum agendado: cria com a data de realização informada
                aso = ASO(
                    funcionario=funcionario, tipo_exame='periodico',
                    status='N', usuario_cadastro=request.user)
            form = AsoRegistrarForm(request.POST, request.FILES)
            if not form.is_valid():
                messages.warning(request, '; '.join(
                    erro for erros in form.errors.values() for erro in erros))
                return _retorno(request)
            dados = form.cleaned_data
            with transaction.atomic():
                aso.data_realizacao = dados['data_realizacao']
                aso.data_validade = dados.get('data_validade')
                if dados.get('anexo'):
                    aso.anexo = dados['anexo']
                aso.observacoes = dados.get('observacoes') or aso.observacoes
                aso.status = 'R'
                try:
                    aso.save()
                except ValidationError as erro:
                    messages.warning(
                        request, 'Não foi possível registrar: ' +
                        _erros_mensagem(erro))
                    return _retorno(request)
                funcionario._historico(
                    'aso_realizacao', request.user,
                    f'ASO realizado em {aso.data_realizacao:%d/%m/%Y}'
                    + (f', válido até {aso.data_validade:%d/%m/%Y}.'
                       if aso.data_validade else '.') )
            messages.success(request, 'Realização do ASO registrada.')
            return _retorno(request)

        if acao == 'cancelar':
            aso = funcionario.asos.filter(status='AG').order_by(
                '-pk').first()
            if aso is None:
                messages.info(request, 'Não há ASO agendado para cancelar.')
                return _retorno(request)
            with transaction.atomic():
                aso.status = 'C'
                aso.save()
                funcionario._historico(
                    'aso_agendamento', request.user,
                    f'ASO de {aso.data_agendamento:%d/%m/%Y} cancelado.')
            messages.success(request, 'ASO cancelado.')
            return _retorno(request)

        messages.warning(request, 'Operação de ASO desconhecida.')
        return _retorno(request)


class FichaRegistroView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGPmixin, View):
    """Anexar/substituir ficha de registro (versões anteriores preservadas)."""

    permission_required = 'gestao_pessoas.change_funcionario'
    acao_gp = 'editar'

    def post(self, request, pk):
        funcionario = _funcionario(request, pk)
        form = FichaRegistroForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.warning(request, '; '.join(
                erro for erros in form.errors.values() for erro in erros))
            return _retorno(request)
        dados = form.cleaned_data
        with transaction.atomic():
            ficha = funcionario.fichas_registro.order_by('-pk').first()
            if ficha is not None and ficha.anexo:
                # SUBSTITUIÇÃO: preserva a versão anterior como histórico —
                # cria uma nova linha (nunca apaga a anterior).
                ficha = None
            if ficha is None:
                ficha = FichaRegistro(
                    funcionario=funcionario,
                    usuario_cadastro=request.user)
            ficha.anexo = dados['anexo']
            ficha.data_registro = dados['data_registro']
            ficha.observacoes = dados.get('observacoes') or ''
            ficha.save()
            funcionario._historico(
                'ficha', request.user,
                f'Ficha de registro anexada (dt. '
                f'{ficha.data_registro:%d/%m/%Y}).')
        messages.success(request, 'Ficha de registro salva com sucesso.')
        return _retorno(request)


class CartaoPontoView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGPmixin, View):
    """Registrar/editar cartão-ponto (modal)."""

    permission_required = 'gestao_pessoas.change_funcionario'
    acao_gp = 'editar'

    def post(self, request, pk):
        funcionario = _funcionario(request, pk)
        cartao = funcionario.cartoes_ponto.order_by('-pk').first()
        form = CartaoPontoForm(request.POST, instance=cartao)
        if not form.is_valid():
            messages.warning(request, '; '.join(
                erro for erros in form.errors.values() for erro in erros))
            return _retorno(request)
        with transaction.atomic():
            cartao = form.save(commit=False)
            cartao.funcionario = funcionario
            cartao.save()
            funcionario._historico(
                'cartao', request.user,
                f'Cartão-ponto registrado: nº {cartao.numero_cartao}.')
        messages.success(request, 'Cartão-ponto salvo com sucesso.')
        return _retorno(request)


class PeriodicoView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGPmixin, View):
    """Exame periódico: agendar / registrar / cancelar (histórico mantido)."""

    permission_required = 'gestao_pessoas.change_funcionario'
    acao_gp = 'editar'

    def post(self, request, pk, acao):
        funcionario = _funcionario(request, pk)
        if acao == 'agendar':
            form = PeriodicoAgendarForm(request.POST)
            if not form.is_valid():
                messages.warning(request, '; '.join(
                    erro for erros in form.errors.values() for erro in erros))
                return _retorno(request)
            with transaction.atomic():
                ExamePeriodico.objects.create(
                    funcionario=funcionario,
                    data_agendamento=form.cleaned_data['data_agendamento'],
                    status='AG', usuario_cadastro=request.user)
                funcionario._historico(
                    'periodico_agendamento', request.user,
                    'Exame periódico agendado para '
                    f'{form.cleaned_data["data_agendamento"]:%d/%m/%Y}.')
            messages.success(request, 'Exame periódico agendado com sucesso.')
            return _retorno(request)

        if acao == 'registrar':
            exame = funcionario.exames_periodicos.filter(status='AG') \
                .order_by('-pk').first()
            if exame is None:
                exame = ExamePeriodico(
                    funcionario=funcionario, status='N',
                    usuario_cadastro=request.user)
            form = PeriodicoRegistrarForm(request.POST, request.FILES)
            if not form.is_valid():
                messages.warning(request, '; '.join(
                    erro for erros in form.errors.values() for erro in erros))
                return _retorno(request)
            dados = form.cleaned_data
            with transaction.atomic():
                exame.data_realizacao = dados['data_realizacao']
                exame.data_proximo_exame = dados.get('data_proximo_exame')
                if dados.get('anexo'):
                    exame.anexo = dados['anexo']
                exame.observacoes = dados.get('observacoes') or exame.observacoes
                exame.status = 'R'
                try:
                    exame.save()
                except ValidationError as erro:
                    messages.warning(
                        request, 'Não foi possível registrar: ' +
                        _erros_mensagem(erro))
                    return _retorno(request)
                funcionario._historico(
                    'periodico_realizacao', request.user,
                    f'Exame periódico realizado em '
                    f'{exame.data_realizacao:%d/%m/%Y}'
                    + (f'; próximo previsto para '
                       f'{exame.data_proximo_exame:%d/%m/%Y}.'
                       if exame.data_proximo_exame else '.'))
            messages.success(request, 'Exame periódico registrado.')
            return _retorno(request)

        if acao == 'cancelar':
            exame = funcionario.exames_periodicos.filter(status='AG') \
                .order_by('-pk').first()
            if exame is None:
                messages.info(request, 'Não há exame periódico agendado.')
                return _retorno(request)
            with transaction.atomic():
                exame.status = 'C'
                exame.save()
                funcionario._historico(
                    'periodico_agendamento', request.user,
                    'Exame periódico cancelado.')
            messages.success(request, 'Exame periódico cancelado.')
            return _retorno(request)

        messages.warning(request, 'Operação desconhecida.')
        return _retorno(request)


class CursoFuncionarioView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGPmixin, View):
    """Registrar curso realizado (certificado + validade) por modal."""

    permission_required = 'gestao_pessoas.change_funcionario'
    acao_gp = 'editar'

    def post(self, request, pk):
        funcionario = _funcionario(request, pk)
        form = CursoFuncionarioForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.warning(request, '; '.join(
                erro for erros in form.errors.values() for erro in erros))
            return _retorno(request)
        try:
            with transaction.atomic():
                curso = form.save(commit=False)
                curso.funcionario = funcionario
                curso.save()
                funcionario._historico(
                    'curso', request.user,
                    f'Curso "{curso.curso}" registrado (realização '
                    f'{curso.data_realizacao or "—"}; validade '
                    f'{curso.data_validade or "sem vencimento"}).')
        except ValidationError as erro:
            messages.warning(
                request, 'Não foi possível registrar: ' +
                _erros_mensagem(erro))
            return _retorno(request)
        messages.success(request, 'Curso registrado com sucesso.')
        return _retorno(request)


class CursoFuncionarioPendenteView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGPmixin, View):
    """Marcar curso obrigatório PENDENTE para o funcionário."""

    permission_required = 'gestao_pessoas.change_funcionario'
    acao_gp = 'editar'

    def post(self, request, pk):
        funcionario = _funcionario(request, pk)
        curso_id = request.POST.get('curso')
        try:
            from .models import Curso
            curso = Curso.objects.get(pk=curso_id, status='A')
        except Exception:
            messages.warning(request, 'Selecione o curso obrigatório.')
            return _retorno(request)
        with transaction.atomic():
            CursoFuncionario.objects.create(
                funcionario=funcionario, curso=curso, status='P')
            funcionario._historico(
                'curso', request.user,
                f'Curso "{curso}" marcado como OBRIGATÓRIO (pendente).')
        messages.success(request, 'Curso pendente registrado.')
        return _retorno(request)


class FeriasView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, LiberacaoGPmixin, View):
    """Férias por modal: registrar aquisitivo / programar / início / retorno."""

    permission_required = 'gestao_pessoas.change_funcionario'
    acao_gp = 'editar'

    def post(self, request, pk, acao):
        funcionario = _funcionario(request, pk)
        if acao in ('aquisitivo', 'programar'):
            ferias = None
            if acao == 'programar':
                ferias = funcionario.ferias.filter(status='P').order_by(
                    '-pk').first()
            if ferias is None:
                ferias = Ferias(
                    funcionario=funcionario,
                    periodo_aquisitivo_inicio=timezone.localdate(),
                    periodo_aquisitivo_final=timezone.localdate()
                    + timezone.timedelta(days=365),
                    usuario_cadastro=request.user)
            form = FeriasForm(request.POST, instance=ferias)
            if not form.is_valid():
                messages.warning(request, '; '.join(
                    erro for erros in form.errors.values() for erro in erros))
                return _retorno(request)
            try:
                with transaction.atomic():
                    form.instance.funcionario = funcionario
                    form.instance.usuario_cadastro = (
                        form.instance.usuario_cadastro or request.user)
                    ferias = form.save()
                    if acao == 'aquisitivo':
                        ferias.status = 'P'
                        ferias.save(update_fields=['status'])
                    else:
                        ferias.status = 'G'
                        ferias.save(update_fields=['status'])
                    funcionario._historico(
                        'ferias', request.user,
                        f'Período aquisitivo '
                        f'{ferias.periodo_aquisitivo_inicio:%d/%m/%Y} a '
                        f'{ferias.periodo_aquisitivo_final:%d/%m/%Y} '
                        + ('programado para férias.' if acao == 'programar'
                           else 'registrado.'))
            except ValidationError as erro:
                messages.warning(
                    request, 'Não foi possível salvar: ' +
                    _erros_mensagem(erro))
                return _retorno(request)
            messages.success(
                request,
                'Período aquisitivo registrado.' if acao == 'aquisitivo'
                else 'Férias programadas.')
            return _retorno(request)

        ferias = funcionario.ferias.order_by('-pk').first()
        if ferias is None:
            messages.info(request, 'Registre o período aquisitivo primeiro.')
            return _retorno(request)
        if acao == 'iniciar':
            ferias.data_inicio_ferias = ferias.data_inicio_ferias or \
                timezone.localdate()
            ferias.status = 'E'
        elif acao == 'retorno':
            ferias.data_final_ferias = ferias.data_final_ferias or \
                timezone.localdate()
            dias = (ferias.data_final_ferias - (
                ferias.data_inicio_ferias or ferias.data_final_ferias)
            ).days + 1
            if ferias.dias_gozados + dias > ferias.dias_direito:
                messages.warning(
                    request,
                    f'Os {dias} dias excedem o saldo disponível '
                    f'({ferias.saldo_dias}). Ajuste as datas.')
                return _retorno(request)
            ferias.dias_gozados = ferias.dias_gozados + dias
            ferias.status = 'C'
        else:
            messages.warning(request, 'Operação de férias desconhecida.')
            return _retorno(request)
        try:
            with transaction.atomic():
                ferias.save()
                funcionario._historico(
                    'ferias', request.user,
                    f'Férias {ferias.get_status_display().lower()} — '
                    f'início {ferias.data_inicio_ferias or "—"} / final '
                    f'{ferias.data_final_ferias or "—"}; gozados '
                    f'{ferias.dias_gozados}/{ferias.dias_direito}.')
        except ValidationError as erro:
            messages.warning(
                request, 'Não foi possível salvar: ' + _erros_mensagem(erro))
            return _retorno(request)
        messages.success(request, 'Férias atualizadas com sucesso.')
        return _retorno(request)
