from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django import forms
from django.contrib.auth import get_user_model
import django_filters
from datetime import datetime
from dominios.choices import status_choices
from django.conf import settings
from django.http import FileResponse, Http404
from django.views import View
from django.db.models import Q
from admin_exames.models import TipoExame
from django.contrib.contenttypes.models import ContentType
from admin_relatorios.models import Relatorio
from django.core.files.storage import default_storage
from django.http import HttpResponse, JsonResponse
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction
from django.contrib import messages
from admin_cadastros.models import Estabelecimento
from admin_cadastros.forms import PessoaDetailForm
from admin_cadastros_assistenciais.models import CadastroProfissional
from admin_exames.models import ParametrosExames
from atendimentos.models import Atendimento
from dominios.utils import CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ParametrosProntuariosMixin, UserIsCreatorMixin, calcular_idade
from .forms_exames import ExameCreateForm, ExameUpdateForm, ResultadoExameForm
from .exames import ResultadoExameFormSet, salvar_resultados_exame
from .models import Exame, ResultadoExame
from .utils import salvar_pdf_prontuario

class ExameFilter(django_filters.FilterSet):
    id = django_filters.NumberFilter(label='ID')
    tipo_exame = django_filters.ModelChoiceFilter(
        queryset=TipoExame.objects.filter(status='A'), label='Tipo de Exame')
    dt_registro = django_filters.DateFilter(
        method='filter_by_date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'datepicker'}),
        label='Data do Registro')
    data_resultado = django_filters.DateFilter(
        method='filter_result_date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'datepicker'}),
        label='Data do Resultado')
    us_registro = django_filters.ModelChoiceFilter(
        queryset=get_user_model().objects.all(), label='Registrado por')
    dt_atualizacao = django_filters.DateFilter(
        method='filter_by_date',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'datepicker'}),
        label='Data da Atualização')
    us_atualizacao = django_filters.ModelChoiceFilter(
        queryset=get_user_model().objects.all(), label='Atualizado por')
    status = django_filters.ChoiceFilter(choices=status_choices, label='Status')

    class Meta:
        model = Exame
        fields = [
            'id', 'tipo_exame', 'dt_registro', 'data_resultado',
            'us_registro', 'dt_atualizacao', 'us_atualizacao', 'status',
        ]

    def filter_by_date(self, queryset, name, value):
        start_day = datetime.combine(value, datetime.min.time())
        end_day = datetime.combine(value, datetime.max.time())
        start_day = timezone.make_aware(start_day)
        end_day = timezone.make_aware(end_day)
        if name == 'dt_registro':
            return queryset.filter(dt_registro__range=(start_day, end_day))
        return queryset.filter(**{f'{name}__range': (start_day, end_day)})

    def filter_result_date(self, queryset, name, value):
        return queryset.filter(
            resultados__data_resultado=value, resultados__status='A')

class ExameListView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ListView):
    permission_required = 'prontuarios.view_exame'
    model = Exame
    template_name = 'prontuarios/exame_listar.html'
    context_object_name = 'exames'
    paginate_by = 15
    session_key = 'exame_filters'
    campos_ignorados = ('page', 'pagina', 'limpar', 'csrfmiddlewaretoken')

    # ------------------------------------------------------------------
    # Filtros (padrao evolucao_listar)
    # ------------------------------------------------------------------
    def _salvar_filtros(self, params):
        """Grava os filtros da tela na sessao como dict simples.

        Um QueryDict mutavel dentro do pickle da sessao quebra a paginacao e o
        urlencode dos links "page=N" no template, por isso o dict plano.
        """
        self.request.session[self.session_key] = {
            campo: valor for campo, valor in params.items()
            if campo not in self.campos_ignorados
        }

    def _restaurar_filtros(self, params):
        """Reaplica na tela os filtros salvos na sessao (ex.: ao paginar)."""
        salvos = self.request.session.get(self.session_key) or {}
        for campo, valor in salvos.items():
            if campo not in self.campos_ignorados:
                params[campo] = valor

    def _aplicar_filtros(self, params, queryset):
        """Monta o FilterSet com os parametros efetivos e devolve o queryset."""
        params.setdefault('status', 'A')
        # O QueryDict precisa ser imutavel ao montar o FilterSet.
        params._mutable = False
        self.filter = ExameFilter(params, queryset=queryset)
        return self.filter.qs.distinct()

    def get_queryset(self):
        estabelecimento_id = self.request.session.get('estabelecimento_id')
        queryset = Exame.objects.filter(
            atendimento_id=self.kwargs['atendimento_id'],
            estabelecimento_id=estabelecimento_id,
        ).select_related('tipo_exame', 'us_registro').prefetch_related('resultados')

        params = self.request.GET.copy()
        limpar_clicado = 'limpar' in params
        params.pop('limpar', None)
        if limpar_clicado:
            # 'Limpar' descarta os filtros e volta ao padrao (status ativo).
            params.clear()
            self.request.session.pop(self.session_key, None)
        elif any(field in params for field in ExameFilter.Meta.fields):
            self._salvar_filtros(params)
        elif self.request.session.get(self.session_key):
            self._restaurar_filtros(params)

        return self._aplicar_filtros(params, queryset)

    # ------------------------------------------------------------------
    # Contexto
    # ------------------------------------------------------------------
    def _context_resultados(self, context):
        """Resultados ativos agrupados por exame da pagina corrente."""
        ids = list(self.object_list.values_list('pk', flat=True))
        resultados = ResultadoExame.objects.filter(
            exame_id__in=ids, status='A').select_related(
                'us_registro').order_by('-data_resultado', '-pk')
        agrupado = {exame_id: [] for exame_id in ids}
        for resultado in resultados:
            agrupado.setdefault(resultado.exame_id, []).append(resultado)
        context['resultados_por_exame'] = agrupado

    def _context_atendimento(self, context):
        """Paciente/estabelecimento do atendimento (cabecalho do prontuario)."""
        atendimento = get_object_or_404(
            Atendimento, pk=self.kwargs['atendimento_id'])
        pessoa = atendimento.pessoa
        context.update({
            'atendimento': atendimento,
            'atendimento_id': atendimento.pk,
            'pessoa_form': PessoaDetailForm(instance=pessoa),
            'idade': calcular_idade(pessoa.dt_nascimento) if pessoa.dt_nascimento else '',
            'estabelecimento': Estabelecimento.objects.filter(
                pk=self.request.session.get('estabelecimento_id')).first(),
        })

    def _context_navegacao(self, context):
        """Titulos, breadcrumb e botoes de navegacao do cabecalho."""
        context.update({
            'titulo': 'Prontuários',
            'title': 'Exames',
            'func': 'Exames',
            'cad_index': reverse_lazy('cadastros_index'),
            'list_index': reverse_lazy('prontuario_listar'),
        })

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filter
        self._context_resultados(context)
        self._context_atendimento(context)
        self._context_navegacao(context)

        # Mesmo padrao de evolucao_listar/prescricao: a flag e estatica.
        # (self.paginator so existe depois de paginate_queryset, o que
        # derrubava a listagem com AttributeError.)
        context['is_paginated'] = True
        self._context_agendas_exame(context)
        return context

    def _context_agendas_exame(self, context):
        """Vincula à linha do exame os agendamentos ativos correspondentes."""
        from agenda_pacientes.models import (
            AgendaPaciente, ParametrosAgenda, TipoAgendamento,
        )

        estabelecimento = context.get('estabelecimento')
        estabelecimento_id = self.request.session.get('estabelecimento_id')
        exames = list(self.object_list)
        exame_ids = [exame.pk for exame in exames]
        pode_ver_agenda = (
            self.request.user.has_perm('agenda_pacientes.view_agendapaciente')
            and ParametrosAgenda.pode(
                self.request.user, estabelecimento, 'ver')
        )
        tipos_agendamento = TipoAgendamento.objects.filter(
            status='A', exige_exame_solicitado=True).order_by('descricao')
        pode_agendar = (
            self.request.user.has_perm('agenda_pacientes.add_agendapaciente')
            and ParametrosAgenda.pode(
                self.request.user, estabelecimento, 'editar')
            and tipos_agendamento.exists()
        )
        context['pode_ver_agenda_exame'] = pode_ver_agenda
        context['pode_agendar_exame'] = pode_agendar
        pode_registrar_resultado = self.request.user.has_perm(
            'prontuarios.add_resultadoexame')
        context['pode_registrar_resultado'] = pode_registrar_resultado
        context['tipos_agendamento_exame'] = tipos_agendamento
        context['agenda_opcoes_url'] = reverse('agendapaciente_opcoes')
        context['data_resultado_inicial'] = timezone.localdate().isoformat()

        por_exame = {}
        agendamentos_vinculados = set()
        agendamentos_executados = set()
        agendas_do_atendimento = AgendaPaciente.objects.filter(
            estabelecimento_id=estabelecimento_id,
            atendimento_id=self.kwargs['atendimento_id'],
            exame_id__in=exame_ids,
            status='A',
        )
        if exame_ids:
            agendamentos_vinculados = set(
                agendas_do_atendimento.values_list('exame_id', flat=True)
            )
            agendamentos_executados = set(
                agendas_do_atendimento.filter(
                    efetuado='S').values_list('exame_id', flat=True)
            )
        if pode_ver_agenda and exame_ids:
            agendas = agendas_do_atendimento.select_related(
                'tipo', 'local').order_by('data_hora', 'pk')
            for agenda in agendas:
                por_exame.setdefault(agenda.exame_id, []).append(agenda)
        resultados_por_exame = context['resultados_por_exame']
        for exame in exames:
            exame.agendamentos_vinculados = por_exame.get(exame.pk, [])
            exame.tem_agendamento = exame.pk in agendamentos_vinculados
            exame.agendamento_executado = (
                exame.pk in agendamentos_executados
            )
            exame.resultados_ativos = resultados_por_exame.get(
                exame.pk, [])
            exame.pode_registrar_resultado = (
                pode_registrar_resultado
                and exame.agendamento_executado
            )

        context['exames'] = exames
        context['pode_registrar_resultado_modal'] = (
            pode_registrar_resultado and bool(agendamentos_executados)
        )
        context['agendas_exame'] = [
            agenda for agendamentos in por_exame.values()
            for agenda in agendamentos
        ]


class ExameAgendaModalView(LoginRequiredMixin, View):
    """Cria, pela linha do exame, uma única agenda ativa para a solicitação."""

    def post(self, request, pk):
        from agenda_pacientes.forms import AgendaExameModalForm
        from agenda_pacientes.models import AgendaPaciente, ParametrosAgenda

        estabelecimento_id = request.session.get('estabelecimento_id')
        estabelecimento = Estabelecimento.objects.filter(
            pk=estabelecimento_id).first()
        if not request.user.has_perm('agenda_pacientes.add_agendapaciente') \
                or not ParametrosAgenda.pode(
                    request.user, estabelecimento, 'editar'):
            return JsonResponse(
                {'erro': 'Você não está liberado para agendar neste '
                         'estabelecimento.'},
                status=403)
        if not estabelecimento_id:
            return JsonResponse(
                {'erro': 'Selecione um estabelecimento antes de agendar.'},
                status=400)

        exame = get_object_or_404(
            Exame.objects.select_related('atendimento', 'tipo_exame'),
            pk=pk, estabelecimento_id=estabelecimento_id, status='A')
        if AgendaPaciente.objects.filter(exame=exame, status='A').exists():
            return JsonResponse(
                {'erro': 'Este exame já possui um agendamento ativo. Consulte '
                         'a data e o local na lista.'},
                status=409)

        form = AgendaExameModalForm(
            request.POST,
            atendimento=exame.atendimento,
            exame=exame,
            estabelecimento_id=estabelecimento_id,
            responsavel=request.user,
        )
        if not form.is_valid():
            return JsonResponse(
                {'erros': form.errors.get_json_data()},
                status=400)

        agenda = form.save(commit=False)
        agenda.estabelecimento_id = estabelecimento_id
        agenda.us_registro = request.user
        try:
            with transaction.atomic():
                agenda.full_clean()
                agenda.save()
        except ValidationError as erro:
            return JsonResponse(
                {'erro': '; '.join(erro.messages)},
                status=400)
        except IntegrityError:
            return JsonResponse(
                {'erro': 'Este exame já possui um agendamento ativo. Consulte '
                         'a data e o local na lista.'},
                status=409)

        return JsonResponse({
            'mensagem': 'Agendamento registrado com sucesso.',
        }, status=201)


class ExameResultadoModalView(LoginRequiredMixin, View):
    """Registra resultado somente após a execução do agendamento."""

    def post(self, request, pk):
        from agenda_pacientes.models import AgendaPaciente

        if not request.user.has_perm('prontuarios.add_resultadoexame'):
            return JsonResponse(
                {'erro': 'Você não tem permissão para registrar resultados.'},
                status=403)

        estabelecimento_id = request.session.get('estabelecimento_id')
        if not estabelecimento_id:
            return JsonResponse(
                {'erro': 'Selecione um estabelecimento antes de registrar o '
                         'resultado.'},
                status=400)
        exame = get_object_or_404(
            Exame, pk=pk, estabelecimento_id=estabelecimento_id, status='A')
        agenda_executada = AgendaPaciente.objects.filter(
            exame=exame,
            estabelecimento_id=estabelecimento_id,
            atendimento_id=exame.atendimento_id,
            status='A',
            efetuado='S',
        ).exists()
        if not agenda_executada:
            return JsonResponse(
                {'erro': 'Marque o agendamento deste exame como efetuado '
                         'antes de registrar o resultado.'},
                status=409)

        form = ResultadoExameForm(request.POST, request.FILES)
        if not form.is_valid():
            return JsonResponse(
                {'erros': form.errors.get_json_data()},
                status=400)

        resultado = form.save(commit=False)
        resultado.exame = exame
        resultado.us_registro = request.user
        try:
            with transaction.atomic():
                resultado.full_clean()
                resultado.save()
        except ValidationError as erro:
            return JsonResponse(
                {'erro': '; '.join(erro.messages)},
                status=400)

        return JsonResponse({
            'mensagem': 'Resultado registrado com sucesso.',
        }, status=201)


class ExameResultadoDetalheModalView(
        LoginRequiredMixin, CustomPermissionRequiredMixin,
        FilterObjectsByEstabelecimentoMixin, View):
    permission_required = 'prontuarios.view_exame'

    def get(self, request, pk, resultado_pk):
        estabelecimento_id = request.session.get('estabelecimento_id')
        exame = get_object_or_404(
            Exame, pk=pk, estabelecimento_id=estabelecimento_id, status='A')
        resultado = get_object_or_404(
            ResultadoExame,
            pk=resultado_pk,
            exame=exame,
            status='A',
        )

        anexos = []
        for numero in (1, 2, 3):
            arquivo = getattr(resultado, f'anexo_{numero}')
            if arquivo:
                anexos.append({
                    'nome': arquivo.name.rsplit('/', 1)[-1],
                    'url': reverse(
                        'resultado_exame_anexo',
                        kwargs={
                            'pk': exame.pk,
                            'resultado_pk': resultado.pk,
                            'numero': numero,
                        },
                    ),
                })

        return JsonResponse({
            'data': resultado.data_resultado.strftime('%d/%m/%Y'),
            'anotacoes': resultado.anotacoes or '',
            'anexos': anexos,
        })


class ExameCreateView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, ParametrosProntuariosMixin, CreateView):
    permission_required = 'prontuarios.add_exame'
    model = Exame
    form_class = ExameCreateForm
    template_name = 'prontuarios/exame_cadastrar.html'
    modelo_parametros = ParametrosExames
    def dispatch(self, request, *args, **kwargs):
        self.atendimento = get_object_or_404(Atendimento, pk=kwargs['atendimento_id'])
        self.kwargs['atendimento'] = self.atendimento
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('exame_listar', kwargs={'atendimento_id': self.atendimento.pk})

    def get_form_kwargs(self):
        return super().get_form_kwargs()

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        estabelecimento_id = self.request.session.get('estabelecimento_id')
        profissional = CadastroProfissional.objects.filter(
            profissional=self.request.user, status='A').order_by('-pk').first()
        liberados = ParametrosExames.objects.filter(
            estabelecimento_id=estabelecimento_id, status='A')
        if profissional:
            liberados = liberados.filter(
                Q(profissao=profissional.profissao) | Q(profissional=self.request.user))
        else:
            liberados = liberados.filter(profissional=self.request.user)
        tipo_ids = liberados.values_list('tipos_exame__id', flat=True)
        form.fields['tipo_exame'].queryset = TipoExame.objects.filter(
            pk__in=tipo_ids, status='A').distinct()
        padrao = liberados.filter(tipo_exame_padrao__isnull=False).values_list(
            'tipo_exame_padrao_id', flat=True).first()
        if padrao and not form.is_bound:
            form.fields['tipo_exame'].initial = padrao
        return form
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        atendimento = self.atendimento
        estabelecimento_id = self.request.session.get('estabelecimento_id')
        prof = CadastroProfissional.objects.filter(profissional=self.request.user, status='A').order_by('-pk').first()
        liberados = ParametrosExames.objects.filter(estabelecimento_id=estabelecimento_id, status='A')
        
        context['cad_index'] = reverse_lazy('cadastros_index')
        context['list_index'] = reverse_lazy('prontuario_listar')
        
        if prof:
            from django.db.models import Q
            liberados = liberados.filter(Q(profissao=prof.profissao) | Q(profissional=self.request.user))
        else:
            liberados = liberados.filter(profissional=self.request.user)
        tipos = liberados.values_list('tipos_exame__id', flat=True)



        context.update({'atendimento': atendimento, 'atendimento_id': atendimento.pk,
                        'tipos_exame': TipoExame.objects.filter(pk__in=tipos, status='A').distinct(),
                        'pessoa_form': PessoaDetailForm(instance=atendimento.pessoa),
                        'estabelecimento': Estabelecimento.objects.filter(pk=estabelecimento_id).first(),
                        'titulo': 'Prontuários', 'title': 'Novo Exame'})
        return context
    def form_valid(self, form):
        estabelecimento_id = self.request.session.get('estabelecimento_id')
        if not estabelecimento_id:
            form.add_error(None, 'Selecione um estabelecimento antes de registrar o exame.')
            return self.form_invalid(form)
        self.object = form.save(commit=False)
        self.object.atendimento = self.atendimento
        profissional = CadastroProfissional.objects.filter(
            profissional=self.request.user, status='A').order_by('-pk').first()
        liberados = ParametrosExames.objects.filter(
            estabelecimento_id=estabelecimento_id, status='A')
        if profissional:
            liberados = liberados.filter(
                Q(profissao=profissional.profissao) | Q(profissional=self.request.user))
        else:
            liberados = liberados.filter(profissional=self.request.user)
        if not liberados.filter(tipos_exame=self.object.tipo_exame).exists():
            form.add_error('tipo_exame', 'Você não está liberado para registrar este tipo de exame neste estabelecimento.')
            return self.form_invalid(form)
        self.object.estabelecimento_id = estabelecimento_id
        self.object.us_registro = self.request.user
        try:
            with transaction.atomic():
                self.object.full_clean()
                self.object.save()
                pdf_gerado = salvar_pdf_prontuario(self.request.user, self.object, assinar=self.object.assinar)
        except Exception as exc:
            form.add_error(None, f'Não foi possível salvar o exame e gerar o relatório: {exc}')
            return self.form_invalid(form)
        if pdf_gerado:
            messages.success(self.request, 'Exame salvo e relatório assinado digitalmente.')
        else:
            messages.warning(self.request, 'Exame salvo; relatório gerado sem assinatura digital.')
        return redirect(self.get_success_url())

class ExameDetailView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, DetailView):
    permission_required = 'prontuarios.view_exame'
    model = Exame
    template_name = 'prontuarios/exame_detalhe.html'
    context_object_name = 'exame'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        atendimento = self.object.atendimento
        pessoa = atendimento.pessoa if atendimento else None
        estabelecimento_id = self.request.session.get('estabelecimento_id')

        # Navegacao entre exames do mesmo atendimento (mesmo criterio da evolucao)
        base = Exame.objects.filter(
            estabelecimento_id=estabelecimento_id,
            atendimento=self.object.atendimento,
            status='A',
        ).order_by('dt_registro', 'pk')

        # Respeita os filtros salvos na sessao pela listagem (igual evolucao).
        filtros = self.request.session.get('exame_filters') or {}
        try:
            exames = ExameFilter(filtros, queryset=base).qs if filtros else base
        except Exception:
            exames = base

        ids_a = list(exames.values_list('id', flat=True))
        proximo_id = objeto_anterior_id = None
        if self.object.id in ids_a:
            index = ids_a.index(self.object.id)
            objeto_anterior_id = ids_a[index - 1] if index > 0 else None
            proximo_id = ids_a[index + 1] if index < len(ids_a) - 1 else None

        context['proximo_objeto'] = Exame.objects.filter(pk=proximo_id).first() if proximo_id else None
        context['objeto_anterior'] = Exame.objects.filter(pk=objeto_anterior_id).first() if objeto_anterior_id else None
        context['detail_url_name'] = 'exame_detalhe'
        context['nav_label'] = 'Navegar entre exames'

        context.update({
            'atendimento': atendimento,
            'atendimento_id': atendimento.pk if atendimento else None,
            'pessoa_form': PessoaDetailForm(instance=pessoa) if pessoa else None,
            'idade': calcular_idade(pessoa.dt_nascimento) if pessoa and pessoa.dt_nascimento else '',
            'estabelecimento': Estabelecimento.objects.filter(pk=estabelecimento_id).first(),
            'titulo': 'Prontuários',
            'cad_index': reverse_lazy('cadastros_index'),
            'list_index': reverse_lazy('prontuario_listar'),
        })

        return context

class ExameUpdateView(LoginRequiredMixin, UserIsCreatorMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, UpdateView):
    permission_required = 'prontuarios.change_exame'
    model = Exame
    form_class = ExameUpdateForm
    template_name = 'prontuarios/exame_editar.html'

    def get_resultados_formset(self):
        if not hasattr(self, '_resultados_formset'):
            kwargs = {
                'instance': self.object,
                'prefix': 'resultados',
            }
            if self.request.method == 'POST':
                kwargs.update({
                    'data': self.request.POST,
                    'files': self.request.FILES,
                })
            self._resultados_formset = ResultadoExameFormSet(**kwargs)
        return self._resultados_formset

    def get_success_url(self):
        return reverse_lazy('exame_listar', kwargs={'atendimento_id': self.object.atendimento_id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['resultado_formset'] = self.get_resultados_formset()
        atendimento = self.object.atendimento
        pessoa = atendimento.pessoa if atendimento else None

        context.update({
            'atendimento': atendimento,
            'atendimento_id': atendimento.pk if atendimento else None,
            'pessoa_form': PessoaDetailForm(instance=pessoa) if pessoa else None,
            'idade': calcular_idade(pessoa.dt_nascimento) if pessoa and pessoa.dt_nascimento else '',
            'estabelecimento': Estabelecimento.objects.filter(pk=self.request.session.get('estabelecimento_id')).first(),
            'titulo': 'Prontuários',
            'cad_index': reverse_lazy('cadastros_index'),
            'list_index': reverse_lazy('prontuario_listar'),
        })
        
        return context
    def form_valid(self, form):
        resultado_formset = self.get_resultados_formset()
        if not resultado_formset.is_valid():
            return self.form_invalid(form)

        try:
            with transaction.atomic():
                self.object = form.save(commit=False)
                self.object.us_atualizacao = self.request.user
                self.object.dt_atualizacao = timezone.now()
                self.object.full_clean()
                self.object.save()
                salvar_resultados_exame(
                    self.object, resultado_formset, self.request.user)
                from agenda_pacientes.models import AgendaPaciente
                for agenda in AgendaPaciente.objects.filter(
                        exame=self.object, status='A'):
                    agenda.sincronizar_execucao()
                from admin_relatorios.models import Relatorio
                from django.contrib.contenttypes.models import ContentType
                Relatorio.objects.filter(content_type=ContentType.objects.get_for_model(self.object), object_id=self.object.pk, status='A').update(status='I')
                if self.object.status == 'A':
                    salvar_pdf_prontuario(self.request.user, self.object, assinar=self.object.assinar)
        except Exception as exc:
            form.add_error(None, f'Não foi possível atualizar o exame e gerar o relatório: {exc}')
            return self.form_invalid(form)
        messages.success(self.request, 'Exame atualizado com sucesso.')
        return redirect(self.get_success_url())


class ExameAnexoView(LoginRequiredMixin, CustomPermissionRequiredMixin, FilterObjectsByEstabelecimentoMixin, View):
    permission_required = 'prontuarios.view_exame'

    def get_queryset(self):
        return super().get_queryset().filter(estabelecimento_id=self.request.session.get('estabelecimento_id'))

    def get(self, request, pk, numero, resultado_pk=None):
        estabelecimento_id = request.session.get('estabelecimento_id')
        exame = get_object_or_404(Exame, pk=pk, estabelecimento_id=estabelecimento_id)
        if numero == 0:
            arquivo = exame.anexo_exame
        elif numero in (1, 2, 3):
            resultados = exame.resultados.filter(status='A').order_by('-data_resultado', '-pk')
            resultado = (
                get_object_or_404(resultados, pk=resultado_pk)
                if resultado_pk is not None
                else resultados.first()
            )
            arquivo = getattr(resultado, f'anexo_{numero}') if resultado else None
        else:
            raise Http404('Anexo inexistente.')
        if not arquivo:
            raise Http404('Anexo inexistente.')
        try:
            arquivo.open('rb')
        except (OSError, ValueError):
            raise Http404('Arquivo indisponível.')
        return FileResponse(
            arquivo, as_attachment=False,
            filename=arquivo.name.rsplit('/', 1)[-1])

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return HttpResponse('Você não tem permissão para visualizar este exame.', status=403)
        return super().handle_no_permission()
