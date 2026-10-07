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

from .models import CartaoPagamento, TransacaoCartao, FaturaCartao, PagamentoCartao
from .forms import CartaoPagamentoForm, TransacaoCartaoForm, FaturaCartaoForm, PagamentoCartaoForm
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
            return redirect('admin_cadastros:cadastros_index')
        except Exception as e:
            logger.error(f"Erro: {str(e)}")
            messages.error(request, f"Erro: {str(e)}")
            return redirect('admin_cadastros:cadastros_index')
    return wrapper


class HandleDatabaseErrorMixin:
    """Mixin para tratamento de erros em CBVs"""
    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except OperationalError as e:
            logger.error(f"Erro de banco de dados: {str(e)}")
            messages.error(request, "Erro ao acessar o banco de dados. Execute: python manage.py migrate")
            return redirect('admin_cadastros:cadastros_index')
        except Exception as e:
            logger.error(f"Erro: {str(e)}")
            messages.error(request, f"Erro: {str(e)}")
            return redirect('admin_cadastros:cadastros_index')


# ============================================================================
# CARTAO INDEX
# ============================================================================

@login_required
@handle_database_error
def cartao_index(request):
    """Dashboard de Cartão de Pagamento"""
    estabelecimento_id = request.session.get('estabelecimento_id')
    if not estabelecimento_id:
        messages.warning(request, "Selecione um estabelecimento")
        return redirect('admin_cadastros:cadastros_index')
    
    estabelecimento = get_object_or_404(Estabelecimento, id=estabelecimento_id)
    cartoes = CartaoPagamento.objects.filter(
        estabelecimento=estabelecimento,
        status='A'
    )
    
    context = {
        'estabelecimento': estabelecimento,
        'cartoes': cartoes,
        'total_cartoes': cartoes.count(),
    }
    return render(request, 'appcartao/cartao_index.html', context)


# ============================================================================
# CARTAO PAGAMENTO
# ============================================================================

class CartaoPagamentoListView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Listar Cartões de Pagamento"""
    model = CartaoPagamento
    template_name = 'appcartao/cartaopagamento_listar.html'
    context_object_name = 'cartoes'
    permission_required = 'appcartao.view_cartaopagamento'
    paginate_by = 20
    
    def get_queryset(self):
        estabelecimento_id = self.request.session.get('estabelecimento_id')
        if estabelecimento_id:
            return CartaoPagamento.objects.filter(
                estabelecimento_id=estabelecimento_id
            ).order_by('-data_criacao')
        return CartaoPagamento.objects.none()


class CartaoPagamentoCreateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Criar Cartão de Pagamento"""
    model = CartaoPagamento
    form_class = CartaoPagamentoForm
    template_name = 'appcartao/cartaopagamento_form.html'
    permission_required = 'appcartao.add_cartaopagamento'
    success_url = reverse_lazy('appcartao:cartaopagamento_listar')
    
    def form_valid(self, form):
        estabelecimento_id = self.request.session.get('estabelecimento_id')
        if estabelecimento_id:
            form.instance.estabelecimento_id = estabelecimento_id
            form.instance.us_registro = self.request.user
            messages.success(self.request, 'Cartão criado com sucesso!')
            return super().form_valid(form)
        messages.error(self.request, 'Estabelecimento não selecionado')
        return self.form_invalid(form)


class CartaoPagamentoDetailView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalhes do Cartão de Pagamento"""
    model = CartaoPagamento
    template_name = 'appcartao/cartaopagamento_detalhe.html'
    context_object_name = 'cartao'
    permission_required = 'appcartao.view_cartaopagamento'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cartao = self.get_object()
        context['faturas'] = cartao.faturas.order_by('-mes_referencia')[:5]
        context['transacoes_recentes'] = cartao.transacoes.order_by('-data_transacao')[:10]
        return context


class CartaoPagamentoUpdateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Editar Cartão de Pagamento"""
    model = CartaoPagamento
    form_class = CartaoPagamentoForm
    template_name = 'appcartao/cartaopagamento_form.html'
    permission_required = 'appcartao.change_cartaopagamento'
    success_url = reverse_lazy('appcartao:cartaopagamento_listar')
    
    def form_valid(self, form):
        form.instance.us_atualizacao = self.request.user
        messages.success(self.request, 'Cartão atualizado com sucesso!')
        return super().form_valid(form)


# ============================================================================
# TRANSACAO CARTAO
# ============================================================================

class TransacaoCartaoListView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Listar Transações do Cartão"""
    model = TransacaoCartao
    template_name = 'appcartao/transacaocartao_listar.html'
    context_object_name = 'transacoes'
    permission_required = 'appcartao.view_transacaocartao'
    paginate_by = 50
    
    def get_queryset(self):
        cartao_id = self.kwargs.get('cartao_id')
        if cartao_id:
            return TransacaoCartao.objects.filter(
                cartao_id=cartao_id,
                status='A'
            ).order_by('-data_transacao')
        return TransacaoCartao.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cartao_id = self.kwargs.get('cartao_id')
        if cartao_id:
            context['cartao'] = get_object_or_404(CartaoPagamento, id=cartao_id)
        return context


class TransacaoCartaoCreateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Criar Transação do Cartão"""
    model = TransacaoCartao
    form_class = TransacaoCartaoForm
    template_name = 'appcartao/transacaocartao_form.html'
    permission_required = 'appcartao.add_transacaocartao'
    
    def get_success_url(self):
        return reverse_lazy('appcartao:transacaocartao_listar', kwargs={'cartao_id': self.object.cartao.id})
    
    def form_valid(self, form):
        cartao_id = self.kwargs.get('cartao_id')
        cartao = get_object_or_404(CartaoPagamento, id=cartao_id)
        form.instance.cartao = cartao
        form.instance.us_registro = self.request.user
        messages.success(self.request, 'Transação criada com sucesso!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cartao_id = self.kwargs.get('cartao_id')
        if cartao_id:
            context['cartao'] = get_object_or_404(CartaoPagamento, id=cartao_id)
        return context


class TransacaoCartaoDetailView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalhes da Transação do Cartão"""
    model = TransacaoCartao
    template_name = 'appcartao/transacaocartao_detalhe.html'
    context_object_name = 'transacao'
    permission_required = 'appcartao.view_transacaocartao'


class TransacaoCartaoUpdateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Editar Transação do Cartão"""
    model = TransacaoCartao
    form_class = TransacaoCartaoForm
    template_name = 'appcartao/transacaocartao_form.html'
    permission_required = 'appcartao.change_transacaocartao'
    
    def get_success_url(self):
        return reverse_lazy('appcartao:transacaocartao_detalhe', kwargs={'pk': self.object.id})
    
    def form_valid(self, form):
        form.instance.us_atualizacao = self.request.user
        messages.success(self.request, 'Transação atualizada com sucesso!')
        return super().form_valid(form)


# ============================================================================
# FATURA CARTAO
# ============================================================================

class FaturaCartaoListView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Listar Faturas do Cartão"""
    model = FaturaCartao
    template_name = 'appcartao/faturacartao_listar.html'
    context_object_name = 'faturas'
    permission_required = 'appcartao.view_faturacartao'
    paginate_by = 30
    
    def get_queryset(self):
        cartao_id = self.kwargs.get('cartao_id')
        if cartao_id:
            return FaturaCartao.objects.filter(
                cartao_id=cartao_id
            ).order_by('-mes_referencia')
        return FaturaCartao.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cartao_id = self.kwargs.get('cartao_id')
        if cartao_id:
            context['cartao'] = get_object_or_404(CartaoPagamento, id=cartao_id)
        return context


class FaturaCartaoCreateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Criar Fatura do Cartão"""
    model = FaturaCartao
    form_class = FaturaCartaoForm
    template_name = 'appcartao/faturacartao_form.html'
    permission_required = 'appcartao.add_faturacartao'
    
    def get_success_url(self):
        return reverse_lazy('appcartao:faturacartao_listar', kwargs={'cartao_id': self.object.cartao.id})
    
    def form_valid(self, form):
        cartao_id = self.kwargs.get('cartao_id')
        cartao = get_object_or_404(CartaoPagamento, id=cartao_id)
        form.instance.cartao = cartao
        form.instance.us_registro = self.request.user
        messages.success(self.request, 'Fatura criada com sucesso!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cartao_id = self.kwargs.get('cartao_id')
        if cartao_id:
            context['cartao'] = get_object_or_404(CartaoPagamento, id=cartao_id)
        return context


class FaturaCartaoDetailView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalhes da Fatura do Cartão"""
    model = FaturaCartao
    template_name = 'appcartao/faturacartao_detalhe.html'
    context_object_name = 'fatura'
    permission_required = 'appcartao.view_faturacartao'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fatura = self.get_object()
        context['pagamentos'] = fatura.pagamentos.filter(status='A')
        context['total_pagamentos'] = fatura.pagamentos.filter(status='A').aggregate(
            total=Sum('valor_pagamento')
        )['total'] or Decimal('0.00')
        context['saldo_pendente'] = fatura.calcular_saldo_pendente()
        return context


class FaturaCartaoUpdateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Editar Fatura do Cartão"""
    model = FaturaCartao
    form_class = FaturaCartaoForm
    template_name = 'appcartao/faturacartao_form.html'
    permission_required = 'appcartao.change_faturacartao'
    
    def get_success_url(self):
        return reverse_lazy('appcartao:faturacartao_detalhe', kwargs={'pk': self.object.id})
    
    def form_valid(self, form):
        form.instance.us_atualizacao = self.request.user
        messages.success(self.request, 'Fatura atualizada com sucesso!')
        return super().form_valid(form)


# ============================================================================
# PAGAMENTO CARTAO
# ============================================================================

class PagamentoCartaoListView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Listar Pagamentos do Cartão"""
    model = PagamentoCartao
    template_name = 'appcartao/pagamentocartao_listar.html'
    context_object_name = 'pagamentos'
    permission_required = 'appcartao.view_pagamentocartao'
    paginate_by = 50
    
    def get_queryset(self):
        fatura_id = self.kwargs.get('fatura_id')
        if fatura_id:
            return PagamentoCartao.objects.filter(
                fatura_id=fatura_id,
                status='A'
            ).order_by('-data_pagamento')
        return PagamentoCartao.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fatura_id = self.kwargs.get('fatura_id')
        if fatura_id:
            context['fatura'] = get_object_or_404(FaturaCartao, id=fatura_id)
        return context


class PagamentoCartaoCreateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Criar Pagamento do Cartão"""
    model = PagamentoCartao
    form_class = PagamentoCartaoForm
    template_name = 'appcartao/pagamentocartao_form.html'
    permission_required = 'appcartao.add_pagamentocartao'
    
    def get_success_url(self):
        return reverse_lazy('appcartao:pagamentocartao_listar', kwargs={'fatura_id': self.object.fatura.id})
    
    def form_valid(self, form):
        fatura_id = self.kwargs.get('fatura_id')
        fatura = get_object_or_404(FaturaCartao, id=fatura_id)
        form.instance.fatura = fatura
        form.instance.us_registro = self.request.user
        messages.success(self.request, 'Pagamento criado com sucesso!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fatura_id = self.kwargs.get('fatura_id')
        if fatura_id:
            context['fatura'] = get_object_or_404(FaturaCartao, id=fatura_id)
        return context


class PagamentoCartaoDetailView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalhes do Pagamento do Cartão"""
    model = PagamentoCartao
    template_name = 'appcartao/pagamentocartao_detalhe.html'
    context_object_name = 'pagamento'
    permission_required = 'appcartao.view_pagamentocartao'


class PagamentoCartaoUpdateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Editar Pagamento do Cartão"""
    model = PagamentoCartao
    form_class = PagamentoCartaoForm
    template_name = 'appcartao/pagamentocartao_form.html'
    permission_required = 'appcartao.change_pagamentocartao'
    
    def get_success_url(self):
        return reverse_lazy('appcartao:pagamentocartao_detalhe', kwargs={'pk': self.object.id})
    
    def form_valid(self, form):
        form.instance.us_atualizacao = self.request.user
        messages.success(self.request, 'Pagamento atualizado com sucesso!')
        return super().form_valid(form)
