import logging
from functools import wraps
from datetime import date
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Sum, Q
from django.urls import reverse_lazy
from django.db import OperationalError
from django.contrib import messages

from .models import ExtratoBancario, LancamentoBancario, Conciliacao, RelatorioConciliacao
from .forms import ExtratoBancarioForm, LancamentoBancarioForm, ConciliacaoForm, RelatorioConciliacaoForm
from admin_cadastros.models import Estabelecimento

logger = logging.getLogger(__name__)


def handle_database_error(view_func):
    """Decorator para tratamento de erros de banco de dados"""
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except OperationalError as e:
            logger.error(f"Erro de banco de dados: {str(e)}")
            messages.error(request, "Erro ao acessar o banco de dados. Execute: python manage.py migrate")
            return redirect('cadastros_index')
        except Exception as e:
            logger.error(f"Erro: {str(e)}")
            messages.error(request, f"Erro: {str(e)}")
            return redirect('cadastros_index')
    return wrapper


class HandleDatabaseErrorMixin:
    """Mixin para tratamento de erros em CBVs"""
    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except OperationalError as e:
            logger.error(f"Erro de banco de dados: {str(e)}")
            messages.error(request, "Erro ao acessar o banco de dados. Execute: python manage.py migrate")
            return redirect('cadastros_index')
        except Exception as e:
            logger.error(f"Erro: {str(e)}")
            messages.error(request, f"Erro: {str(e)}")
            return redirect('cadastros_index')


# ============================================================================
# CONCILIACAO INDEX
# ============================================================================

@login_required
@handle_database_error
def conciliacao_index(request):
    """Dashboard de Conciliação"""
    estabelecimento_id = request.session.get('estabelecimento_id')
    if not estabelecimento_id:
        messages.warning(request, "Selecione um estabelecimento")
        return redirect('cadastros_index')
    
    estabelecimento = get_object_or_404(Estabelecimento, id=estabelecimento_id)
    extratos = ExtratoBancario.objects.filter(
        estabelecimento=estabelecimento
    ).order_by('-data_fim')[:10]
    
    conciliacoes_pendentes = Conciliacao.objects.filter(
        status='PENDENTE'
    ).count()
    
    context = {
        'estabelecimento': estabelecimento,
        'extratos': extratos,
        'conciliacoes_pendentes': conciliacoes_pendentes,
    }
    return render(request, 'appconciliacao/conciliacao_index.html', context)


# ============================================================================
# EXTRATO BANCARIO
# ============================================================================

class ExtratoBancarioListView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Listar Extratos Bancários"""
    model = ExtratoBancario
    template_name = 'appconciliacao/extratobancario_listar.html'
    context_object_name = 'extratos'
    permission_required = 'appconciliacao.view_extratobancario'
    paginate_by = 20
    
    def get_queryset(self):
        estabelecimento_id = self.request.session.get('estabelecimento_id')
        if estabelecimento_id:
            return ExtratoBancario.objects.filter(
                estabelecimento_id=estabelecimento_id
            ).order_by('-data_fim')
        return ExtratoBancario.objects.none()


class ExtratoBancarioCreateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Criar Extrato Bancário"""
    model = ExtratoBancario
    form_class = ExtratoBancarioForm
    template_name = 'appconciliacao/extratobancario_form.html'
    permission_required = 'appconciliacao.add_extratobancario'
    success_url = reverse_lazy('appconciliacao:extratobancario_listar')
    
    def form_valid(self, form):
        estabelecimento_id = self.request.session.get('estabelecimento_id')
        if estabelecimento_id:
            form.instance.estabelecimento_id = estabelecimento_id
            form.instance.us_registro = self.request.user
            messages.success(self.request, 'Extrato bancário criado com sucesso!')
            return super().form_valid(form)
        messages.error(self.request, 'Estabelecimento não selecionado')
        return self.form_invalid(form)


class ExtratoBancarioDetailView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalhes do Extrato Bancário"""
    model = ExtratoBancario
    template_name = 'appconciliacao/extratobancario_detalhe.html'
    context_object_name = 'extrato'
    permission_required = 'appconciliacao.view_extratobancario'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        extrato = self.get_object()
        context['lancamentos'] = extrato.lancamentos.all()
        context['total_lancamentos'] = extrato.lancamentos.count()
        context['total_creditos'] = extrato.lancamentos.filter(tipo='CREDITO').aggregate(
            total=Sum('valor')
        )['total'] or Decimal('0.00')
        context['total_debitos'] = extrato.lancamentos.filter(tipo='DEBITO').aggregate(
            total=Sum('valor')
        )['total'] or Decimal('0.00')
        return context


class ExtratoBancarioUpdateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Editar Extrato Bancário"""
    model = ExtratoBancario
    form_class = ExtratoBancarioForm
    template_name = 'appconciliacao/extratobancario_form.html'
    permission_required = 'appconciliacao.change_extratobancario'
    success_url = reverse_lazy('appconciliacao:extratobancario_listar')
    
    def form_valid(self, form):
        form.instance.us_atualizacao = self.request.user
        messages.success(self.request, 'Extrato bancário atualizado com sucesso!')
        return super().form_valid(form)


# ============================================================================
# LANCAMENTO BANCARIO
# ============================================================================

class LancamentoBancarioListView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Listar Lançamentos Bancários"""
    model = LancamentoBancario
    template_name = 'appconciliacao/lancamentobancario_listar.html'
    context_object_name = 'lancamentos'
    permission_required = 'appconciliacao.view_lancamentobancario'
    paginate_by = 50
    
    def get_queryset(self):
        extrato_id = self.kwargs.get('extrato_id')
        if extrato_id:
            return LancamentoBancario.objects.filter(
                extrato_id=extrato_id
            ).order_by('-data_lancamento')
        return LancamentoBancario.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        extrato_id = self.kwargs.get('extrato_id')
        if extrato_id:
            context['extrato'] = get_object_or_404(ExtratoBancario, id=extrato_id)
        return context


class LancamentoBancarioCreateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Criar Lançamento Bancário"""
    model = LancamentoBancario
    form_class = LancamentoBancarioForm
    template_name = 'appconciliacao/lancamentobancario_form.html'
    permission_required = 'appconciliacao.add_lancamentobancario'
    
    def get_success_url(self):
        return reverse_lazy('appconciliacao:lancamentobancario_listar', kwargs={'extrato_id': self.object.extrato.id})
    
    def form_valid(self, form):
        extrato_id = self.kwargs.get('extrato_id')
        extrato = get_object_or_404(ExtratoBancario, id=extrato_id)
        form.instance.extrato = extrato
        messages.success(self.request, 'Lançamento criado com sucesso!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        extrato_id = self.kwargs.get('extrato_id')
        if extrato_id:
            context['extrato'] = get_object_or_404(ExtratoBancario, id=extrato_id)
        return context


class LancamentoBancarioDetailView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalhes do Lançamento Bancário"""
    model = LancamentoBancario
    template_name = 'appconciliacao/lancamentobancario_detalhe.html'
    context_object_name = 'lancamento'
    permission_required = 'appconciliacao.view_lancamentobancario'


class LancamentoBancarioUpdateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Editar Lançamento Bancário"""
    model = LancamentoBancario
    form_class = LancamentoBancarioForm
    template_name = 'appconciliacao/lancamentobancario_form.html'
    permission_required = 'appconciliacao.change_lancamentobancario'
    
    def get_success_url(self):
        return reverse_lazy('appconciliacao:lancamentobancario_detalhe', kwargs={'pk': self.object.id})
    
    def form_valid(self, form):
        messages.success(self.request, 'Lançamento atualizado com sucesso!')
        return super().form_valid(form)


# ============================================================================
# CONCILIACAO
# ============================================================================

class ConciliacaoListView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Listar Conciliações"""
    model = Conciliacao
    template_name = 'appconciliacao/conciliacao_listar.html'
    context_object_name = 'conciliacoes'
    permission_required = 'appconciliacao.view_conciliacao'
    paginate_by = 50
    
    def get_queryset(self):
        lancamento_id = self.kwargs.get('lancamento_id')
        if lancamento_id:
            return Conciliacao.objects.filter(
                lancamento_bancario_id=lancamento_id
            ).order_by('-data_criacao')
        return Conciliacao.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lancamento_id = self.kwargs.get('lancamento_id')
        if lancamento_id:
            context['lancamento'] = get_object_or_404(LancamentoBancario, id=lancamento_id)
        return context


class ConciliacaoCreateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Criar Conciliação"""
    model = Conciliacao
    form_class = ConciliacaoForm
    template_name = 'appconciliacao/conciliacao_form.html'
    permission_required = 'appconciliacao.add_conciliacao'
    
    def get_success_url(self):
        return reverse_lazy('appconciliacao:conciliacao_listar', kwargs={'lancamento_id': self.object.lancamento_bancario.id})
    
    def form_valid(self, form):
        lancamento_id = self.kwargs.get('lancamento_id')
        lancamento = get_object_or_404(LancamentoBancario, id=lancamento_id)
        form.instance.lancamento_bancario = lancamento
        form.instance.us_registro = self.request.user
        messages.success(self.request, 'Conciliação criada com sucesso!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lancamento_id = self.kwargs.get('lancamento_id')
        if lancamento_id:
            context['lancamento'] = get_object_or_404(LancamentoBancario, id=lancamento_id)
        return context


class ConciliacaoDetailView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalhes da Conciliação"""
    model = Conciliacao
    template_name = 'appconciliacao/conciliacao_detalhe.html'
    context_object_name = 'conciliacao'
    permission_required = 'appconciliacao.view_conciliacao'


class ConciliacaoUpdateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Editar Conciliação"""
    model = Conciliacao
    form_class = ConciliacaoForm
    template_name = 'appconciliacao/conciliacao_form.html'
    permission_required = 'appconciliacao.change_conciliacao'
    
    def get_success_url(self):
        return reverse_lazy('appconciliacao:conciliacao_detalhe', kwargs={'pk': self.object.id})
    
    def form_valid(self, form):
        form.instance.us_atualizacao = self.request.user
        messages.success(self.request, 'Conciliação atualizada com sucesso!')
        return super().form_valid(form)


# ============================================================================
# RELATORIO CONCILIACAO
# ============================================================================

class RelatorioConciliacaoListView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Listar Relatórios de Conciliação"""
    model = RelatorioConciliacao
    template_name = 'appconciliacao/relatorioconci liacao_listar.html'
    context_object_name = 'relatorios'
    permission_required = 'appconciliacao.view_relatorioconci liacao'
    paginate_by = 20
    
    def get_queryset(self):
        estabelecimento_id = self.request.session.get('estabelecimento_id')
        if estabelecimento_id:
            return RelatorioConciliacao.objects.filter(
                estabelecimento_id=estabelecimento_id
            ).order_by('-data_fim')
        return RelatorioConciliacao.objects.none()


class RelatorioConciliacaoCreateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Criar Relatório de Conciliação"""
    model = RelatorioConciliacao
    form_class = RelatorioConciliacaoForm
    template_name = 'appconciliacao/relatorioconci liacao_form.html'
    permission_required = 'appconciliacao.add_relatorioconci liacao'
    success_url = reverse_lazy('appconciliacao:relatorioconci liacao_listar')
    
    def form_valid(self, form):
        estabelecimento_id = self.request.session.get('estabelecimento_id')
        if estabelecimento_id:
            form.instance.estabelecimento_id = estabelecimento_id
            form.instance.us_registro = self.request.user
            messages.success(self.request, 'Relatório criado com sucesso!')
            return super().form_valid(form)
        messages.error(self.request, 'Estabelecimento não selecionado')
        return self.form_invalid(form)


class RelatorioConciliacaoDetailView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalhes do Relatório de Conciliação"""
    model = RelatorioConciliacao
    template_name = 'appconciliacao/relatorioconci liacao_detalhe.html'
    context_object_name = 'relatorio'
    permission_required = 'appconciliacao.view_relatorioconci liacao'
