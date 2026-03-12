import logging
from functools import wraps
from datetime import date
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Sum
from django.urls import reverse_lazy
from django.db import OperationalError
from django.contrib import messages

from .models import BaixaFatura, BaixaPagamento, ProcessoBaixa, RelatorioBaixa
from .forms import BaixaFaturaForm, BaixaPagamentoForm, ProcessoBaixaForm, RelatorioBaixaForm
from admin_cadastros.models import Estabelecimento
from admin_faturas.models import Fatura
from admin_pagamentos.models import Pagamento

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
# BAIXA FATURA INDEX
# ============================================================================

@login_required
@handle_database_error
def baixa_fatura_index(request):
    """Dashboard de Baixa de Fatura"""
    estabelecimento_id = request.session.get('estabelecimento_id')
    if not estabelecimento_id:
        messages.warning(request, "Selecione um estabelecimento")
        return redirect('cadastros_index')
    
    estabelecimento = get_object_or_404(Estabelecimento, id=estabelecimento_id)
    
    # Estatísticas
    total_baixas_fatura = BaixaFatura.objects.count()
    total_baixas_pagamento = BaixaPagamento.objects.count()
    valor_total_baixado = BaixaFatura.objects.aggregate(total=Sum('valor_baixa'))['total'] or Decimal('0.00')
    
    context = {
        'estabelecimento': estabelecimento,
        'total_baixas_fatura': total_baixas_fatura,
        'total_baixas_pagamento': total_baixas_pagamento,
        'valor_total_baixado': valor_total_baixado,
    }
    return render(request, 'appbaixa_fatura/baixa_fatura_index.html', context)


# ============================================================================
# BAIXA FATURA
# ============================================================================

class BaixaFaturaListView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Listar Baixas de Fatura"""
    model = BaixaFatura
    template_name = 'appbaixa_fatura/baixafatura_listar.html'
    context_object_name = 'baixas'
    permission_required = 'appbaixa_fatura.view_baixafatura'
    paginate_by = 50
    
    def get_queryset(self):
        fatura_id = self.kwargs.get('fatura_id')
        if fatura_id:
            return BaixaFatura.objects.filter(
                fatura_id=fatura_id
            ).order_by('-data_baixa')
        return BaixaFatura.objects.all().order_by('-data_baixa')


class BaixaFaturaCreateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Criar Baixa de Fatura"""
    model = BaixaFatura
    form_class = BaixaFaturaForm
    template_name = 'appbaixa_fatura/baixafatura_form.html'
    permission_required = 'appbaixa_fatura.add_baixafatura'
    
    def get_success_url(self):
        fatura_id = self.kwargs.get('fatura_id')
        if fatura_id:
            return reverse_lazy('appbaixa_fatura:baixafatura_listar', kwargs={'fatura_id': fatura_id})
        return reverse_lazy('appbaixa_fatura:baixafatura_listar')
    
    def form_valid(self, form):
        fatura_id = self.kwargs.get('fatura_id')
        if fatura_id:
            fatura = get_object_or_404(Fatura, id=fatura_id)
            form.instance.fatura = fatura
        form.instance.us_registro = self.request.user
        messages.success(self.request, 'Baixa de fatura criada com sucesso!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fatura_id = self.kwargs.get('fatura_id')
        if fatura_id:
            context['fatura'] = get_object_or_404(Fatura, id=fatura_id)
        return context


class BaixaFaturaDetailView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalhes da Baixa de Fatura"""
    model = BaixaFatura
    template_name = 'appbaixa_fatura/baixafatura_detalhe.html'
    context_object_name = 'baixa'
    permission_required = 'appbaixa_fatura.view_baixafatura'


class BaixaFaturaUpdateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Editar Baixa de Fatura"""
    model = BaixaFatura
    form_class = BaixaFaturaForm
    template_name = 'appbaixa_fatura/baixafatura_form.html'
    permission_required = 'appbaixa_fatura.change_baixafatura'
    
    def get_success_url(self):
        return reverse_lazy('appbaixa_fatura:baixafatura_detalhe', kwargs={'pk': self.object.id})
    
    def form_valid(self, form):
        form.instance.us_atualizacao = self.request.user
        messages.success(self.request, 'Baixa de fatura atualizada com sucesso!')
        return super().form_valid(form)


# ============================================================================
# BAIXA PAGAMENTO
# ============================================================================

class BaixaPagamentoListView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Listar Baixas de Pagamento"""
    model = BaixaPagamento
    template_name = 'appbaixa_fatura/baixapagamento_listar.html'
    context_object_name = 'baixas'
    permission_required = 'appbaixa_fatura.view_baixapagamento'
    paginate_by = 50
    
    def get_queryset(self):
        pagamento_id = self.kwargs.get('pagamento_id')
        if pagamento_id:
            return BaixaPagamento.objects.filter(
                pagamento_id=pagamento_id
            ).order_by('-data_baixa')
        return BaixaPagamento.objects.all().order_by('-data_baixa')


class BaixaPagamentoCreateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Criar Baixa de Pagamento"""
    model = BaixaPagamento
    form_class = BaixaPagamentoForm
    template_name = 'appbaixa_fatura/baixapagamento_form.html'
    permission_required = 'appbaixa_fatura.add_baixapagamento'
    
    def get_success_url(self):
        pagamento_id = self.kwargs.get('pagamento_id')
        if pagamento_id:
            return reverse_lazy('appbaixa_fatura:baixapagamento_listar', kwargs={'pagamento_id': pagamento_id})
        return reverse_lazy('appbaixa_fatura:baixapagamento_listar')
    
    def form_valid(self, form):
        pagamento_id = self.kwargs.get('pagamento_id')
        if pagamento_id:
            pagamento = get_object_or_404(Pagamento, id=pagamento_id)
            form.instance.pagamento = pagamento
        form.instance.us_registro = self.request.user
        messages.success(self.request, 'Baixa de pagamento criada com sucesso!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pagamento_id = self.kwargs.get('pagamento_id')
        if pagamento_id:
            context['pagamento'] = get_object_or_404(Pagamento, id=pagamento_id)
        return context


class BaixaPagamentoDetailView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalhes da Baixa de Pagamento"""
    model = BaixaPagamento
    template_name = 'appbaixa_fatura/baixapagamento_detalhe.html'
    context_object_name = 'baixa'
    permission_required = 'appbaixa_fatura.view_baixapagamento'


class BaixaPagamentoUpdateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Editar Baixa de Pagamento"""
    model = BaixaPagamento
    form_class = BaixaPagamentoForm
    template_name = 'appbaixa_fatura/baixapagamento_form.html'
    permission_required = 'appbaixa_fatura.change_baixapagamento'
    
    def get_success_url(self):
        return reverse_lazy('appbaixa_fatura:baixapagamento_detalhe', kwargs={'pk': self.object.id})
    
    def form_valid(self, form):
        form.instance.us_atualizacao = self.request.user
        messages.success(self.request, 'Baixa de pagamento atualizada com sucesso!')
        return super().form_valid(form)


# ============================================================================
# PROCESSO BAIXA
# ============================================================================

class ProcessoBaixaListView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Listar Processos de Baixa"""
    model = ProcessoBaixa
    template_name = 'appbaixa_fatura/processoBaixa_listar.html'
    context_object_name = 'processos'
    permission_required = 'appbaixa_fatura.view_processoBaixa'
    paginate_by = 30
    
    def get_queryset(self):
        return ProcessoBaixa.objects.all().order_by('-data_criacao')


class ProcessoBaixaDetailView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalhes do Processo de Baixa"""
    model = ProcessoBaixa
    template_name = 'appbaixa_fatura/processoBaixa_detalhe.html'
    context_object_name = 'processo'
    permission_required = 'appbaixa_fatura.view_processoBaixa'


# ============================================================================
# RELATORIO BAIXA
# ============================================================================

class RelatorioBaixaListView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Listar Relatórios de Baixa"""
    model = RelatorioBaixa
    template_name = 'appbaixa_fatura/relatoriobaixa_listar.html'
    context_object_name = 'relatorios'
    permission_required = 'appbaixa_fatura.view_relatoriobaixa'
    paginate_by = 20
    
    def get_queryset(self):
        return RelatorioBaixa.objects.all().order_by('-data_fim')


class RelatorioBaixaCreateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Criar Relatório de Baixa"""
    model = RelatorioBaixa
    form_class = RelatorioBaixaForm
    template_name = 'appbaixa_fatura/relatoriobaixa_form.html'
    permission_required = 'appbaixa_fatura.add_relatoriobaixa'
    success_url = reverse_lazy('appbaixa_fatura:relatoriobaixa_listar')
    
    def form_valid(self, form):
        form.instance.us_registro = self.request.user
        messages.success(self.request, 'Relatório criado com sucesso!')
        return super().form_valid(form)


class RelatorioBaixaDetailView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalhes do Relatório de Baixa"""
    model = RelatorioBaixa
    template_name = 'appbaixa_fatura/relatoriobaixa_detalhe.html'
    context_object_name = 'relatorio'
    permission_required = 'appbaixa_fatura.view_relatoriobaixa'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        relatorio = self.get_object()
        context['baixas_fatura'] = BaixaFatura.objects.filter(
            data_baixa__range=[relatorio.data_inicio, relatorio.data_fim]
        )
        context['baixas_pagamento'] = BaixaPagamento.objects.filter(
            data_baixa__range=[relatorio.data_inicio, relatorio.data_fim]
        )
        return context


class RelatorioBaixaUpdateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Editar Relatório de Baixa"""
    model = RelatorioBaixa
    form_class = RelatorioBaixaForm
    template_name = 'appbaixa_fatura/relatoriobaixa_form.html'
    permission_required = 'appbaixa_fatura.change_relatoriobaixa'
    success_url = reverse_lazy('appbaixa_fatura:relatoriobaixa_listar')
    
    def form_valid(self, form):
        form.instance.us_atualizacao = self.request.user
        messages.success(self.request, 'Relatório atualizado com sucesso!')
        return super().form_valid(form)
