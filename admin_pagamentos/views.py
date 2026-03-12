from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q, Sum, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.db import OperationalError
from decimal import Decimal
from functools import wraps

from .models_cartao import CartaoPagamento, TransacaoCartao, FaturaCartao, PagamentoCartao
from .forms_cartao import CartaoPagamentoForm, TransacaoCartaoForm, FaturaCartaoForm, PagamentoCartaoForm
from admin_cadastros.models import Estabelecimento


def handle_database_error(view_func):
    """Decorator para tratar erros de banco de dados"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except OperationalError as e:
            error_msg = str(e)
            if 'no such table' in error_msg:
                messages.error(
                    request,
                    'Banco de dados não foi inicializado. Execute: python manage.py migrate admin_pagamentos'
                )
            elif 'no such column' in error_msg:
                messages.error(
                    request,
                    'Estrutura do banco de dados está desatualizada. Execute: python manage.py migrate admin_pagamentos'
                )
            else:
                messages.error(request, f'Erro no banco de dados: {error_msg}')
            return redirect('cadastros_index')
    return wrapper


@login_required(login_url='login')
@handle_database_error
def cartao_index(request):
    """Dashboard principal de Cartão de Pagamento"""
    estabelecimento_id = request.session.get('estabelecimento_id')
    
    if not estabelecimento_id:
        messages.warning(request, 'Estabelecimento não selecionado.')
        return redirect('cadastros_index')
    
    try:
        estabelecimento = Estabelecimento.objects.get(pk=estabelecimento_id)
    except Estabelecimento.DoesNotExist:
        messages.error(request, 'Estabelecimento não encontrado.')
        return redirect('cadastros_index')
    
    try:
        # Cartões do estabelecimento
        cartoes = CartaoPagamento.objects.filter(
            estabelecimento=estabelecimento,
            status='A'
        )
        
        # Faturas abertas
        faturas_abertas = FaturaCartao.objects.filter(
            cartao__estabelecimento=estabelecimento,
            status__in=['ABERTA', 'PARCIAL']
        )
        
        # Transações do mês
        hoje = timezone.now().date()
        transacoes_mes = TransacaoCartao.objects.filter(
            cartao__estabelecimento=estabelecimento,
            data_transacao__month=hoje.month,
            data_transacao__year=hoje.year,
            status='A'
        ).order_by('-data_transacao')
        
        # Totais
        totais = transacoes_mes.aggregate(
            total_transacoes=Coalesce(
                Sum('valor'),
                Decimal('0.00'),
                output_field=DecimalField()
            )
        )
        
    except OperationalError:
        messages.error(
            request,
            'Banco de dados não foi inicializado. Execute: python manage.py migrate admin_pagamentos'
        )
        return redirect('cadastros_index')
    
    context = {
        'titulo': 'Cartão de Pagamento',
        'title': 'cartao_index',
        'estabelecimento': estabelecimento,
        'cartoes': cartoes,
        'faturas_abertas': faturas_abertas,
        'transacoes_mes': transacoes_mes[:10],
        'totais': totais,
    }
    
    return render(request, 'pagamentos/cartao_index.html', context)


class CartaoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista todos os cartões"""
    model = CartaoPagamento
    template_name = 'pagamentos/cartao_listar.html'
    context_object_name = 'cartoes'
    permission_required = 'admin_pagamentos.view_cartaopagamento'
    paginate_by = 20

    def get_queryset(self):
        try:
            estabelecimento_id = self.request.session.get('estabelecimento_id')
            queryset = CartaoPagamento.objects.filter(estabelecimento_id=estabelecimento_id)
            
            # Filtro por status
            status = self.request.GET.get('status')
            if status:
                queryset = queryset.filter(status=status)
            
            # Busca por número
            search = self.request.GET.get('search')
            if search:
                queryset = queryset.filter(
                    Q(numero_cartao__icontains=search) |
                    Q(titular__icontains=search)
                )
            
            return queryset.order_by('-dt_registro')
        except OperationalError:
            messages.error(
                self.request,
                'Banco de dados não foi inicializado. Execute: python manage.py migrate admin_pagamentos'
            )
            return CartaoPagamento.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cartões de Pagamento'
        context['title'] = 'cartao_listar'
        return context


class CartaoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Criar novo cartão"""
    model = CartaoPagamento
    form_class = CartaoPagamentoForm
    template_name = 'pagamentos/cartao_form.html'
    permission_required = 'admin_pagamentos.add_cartaopagamento'
    success_url = reverse_lazy('admin_pagamentos:cartao_listar')

    def form_valid(self, form):
        form.instance.us_registro = self.request.user
        estabelecimento_id = self.request.session.get('estabelecimento_id')
        form.instance.estabelecimento_id = estabelecimento_id
        messages.success(self.request, 'Cartão criado com sucesso!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Novo Cartão'
        context['title'] = 'cartao_criar'
        return context


class CartaoDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalhar cartão"""
    model = CartaoPagamento
    template_name = 'pagamentos/cartao_detalhe.html'
    permission_required = 'admin_pagamentos.view_cartaopagamento'
    context_object_name = 'cartao'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f'Cartão: {self.object.numero_cartao}'
        context['title'] = 'cartao_detalhe'
        
        # Transações do cartão
        context['transacoes'] = self.object.transacaocartao_set.all().order_by('-data_transacao')[:10]
        
        # Faturas
        context['faturas'] = self.object.faturacartao_set.all().order_by('-data_vencimento')[:5]
        
        return context


class CartaoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Editar cartão"""
    model = CartaoPagamento
    form_class = CartaoPagamentoForm
    template_name = 'pagamentos/cartao_form.html'
    permission_required = 'admin_pagamentos.change_cartaopagamento'
    success_url = reverse_lazy('admin_pagamentos:cartao_listar')

    def form_valid(self, form):
        form.instance.us_atualizacao = self.request.user
        form.instance.dt_atualizacao = timezone.now()
        messages.success(self.request, 'Cartão atualizado com sucesso!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Cartão'
        context['title'] = 'cartao_editar'
        return context


class TransacaoCartaoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista transações de um cartão"""
    model = TransacaoCartao
    template_name = 'pagamentos/transacao_listar.html'
    context_object_name = 'transacoes'
    permission_required = 'admin_pagamentos.view_transacaocartao'
    paginate_by = 20

    def get_queryset(self):
        try:
            cartao_id = self.kwargs.get('cartao_id')
            queryset = TransacaoCartao.objects.filter(cartao_id=cartao_id)
            
            # Filtro por status
            status = self.request.GET.get('status')
            if status:
                queryset = queryset.filter(status=status)
            
            return queryset.order_by('-data_transacao')
        except OperationalError:
            messages.error(
                self.request,
                'Banco de dados não foi inicializado. Execute: python manage.py migrate admin_pagamentos'
            )
            return TransacaoCartao.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cartao_id = self.kwargs.get('cartao_id')
        try:
            cartao = CartaoPagamento.objects.get(pk=cartao_id)
            context['cartao'] = cartao
            context['titulo'] = f'Transações - {cartao.numero_cartao}'
            context['title'] = 'transacao_listar'
        except CartaoPagamento.DoesNotExist:
            messages.error(self.request, 'Cartão não encontrado.')
        
        return context


class TransacaoCartaoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Criar nova transação"""
    model = TransacaoCartao
    form_class = TransacaoCartaoForm
    template_name = 'pagamentos/transacao_form.html'
    permission_required = 'admin_pagamentos.add_transacaocartao'

    def get_success_url(self):
        return reverse_lazy('admin_pagamentos:transacao_listar', kwargs={'cartao_id': self.object.cartao.pk})

    def form_valid(self, form):
        cartao_id = self.kwargs.get('cartao_id')
        try:
            cartao = CartaoPagamento.objects.get(pk=cartao_id)
        except CartaoPagamento.DoesNotExist:
            messages.error(self.request, 'Cartão não encontrado.')
            return redirect('admin_pagamentos:cartao_listar')
        
        form.instance.cartao = cartao
        form.instance.us_registro = self.request.user
        messages.success(self.request, 'Transação registrada com sucesso!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cartao_id = self.kwargs.get('cartao_id')
        try:
            cartao = CartaoPagamento.objects.get(pk=cartao_id)
            context['cartao'] = cartao
            context['titulo'] = f'Nova Transação - {cartao.numero_cartao}'
            context['title'] = 'transacao_criar'
        except CartaoPagamento.DoesNotExist:
            messages.error(self.request, 'Cartão não encontrado.')
        
        return context


class TransacaoCartaoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Editar transação"""
    model = TransacaoCartao
    form_class = TransacaoCartaoForm
    template_name = 'pagamentos/transacao_form.html'
    permission_required = 'admin_pagamentos.change_transacaocartao'

    def get_success_url(self):
        return reverse_lazy('admin_pagamentos:transacao_listar', kwargs={'cartao_id': self.object.cartao.pk})

    def form_valid(self, form):
        form.instance.us_atualizacao = self.request.user
        form.instance.dt_atualizacao = timezone.now()
        messages.success(self.request, 'Transação atualizada com sucesso!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Transação'
        context['title'] = 'transacao_editar'
        return context


@login_required(login_url='login')
@permission_required('admin_pagamentos.delete_transacaocartao', raise_exception=True)
@handle_database_error
def deletar_transacao(request, pk):
    """Deletar transação"""
    try:
        transacao = TransacaoCartao.objects.get(pk=pk)
    except TransacaoCartao.DoesNotExist:
        messages.error(request, 'Transação não encontrada.')
        return redirect('admin_pagamentos:cartao_listar')
    
    cartao_id = transacao.cartao.pk
    
    if request.method == 'POST':
        transacao.delete()
        messages.success(request, 'Transação deletada com sucesso!')
        return redirect('admin_pagamentos:transacao_listar', cartao_id=cartao_id)
    
    context = {
        'titulo': 'Deletar Transação',
        'title': 'deletar_transacao',
        'transacao': transacao,
    }
    
    return render(request, 'pagamentos/deletar_transacao.html', context)


class FaturaCartaoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista faturas de um cartão"""
    model = FaturaCartao
    template_name = 'pagamentos/fatura_listar.html'
    context_object_name = 'faturas'
    permission_required = 'admin_pagamentos.view_faturacartao'
    paginate_by = 20

    def get_queryset(self):
        try:
            cartao_id = self.kwargs.get('cartao_id')
            queryset = FaturaCartao.objects.filter(cartao_id=cartao_id)
            
            # Filtro por status
            status = self.request.GET.get('status')
            if status:
                queryset = queryset.filter(status=status)
            
            return queryset.order_by('-data_vencimento')
        except OperationalError:
            messages.error(
                self.request,
                'Banco de dados não foi inicializado. Execute: python manage.py migrate admin_pagamentos'
            )
            return FaturaCartao.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cartao_id = self.kwargs.get('cartao_id')
        try:
            cartao = CartaoPagamento.objects.get(pk=cartao_id)
            context['cartao'] = cartao
            context['titulo'] = f'Faturas - {cartao.numero_cartao}'
            context['title'] = 'fatura_listar'
        except CartaoPagamento.DoesNotExist:
            messages.error(self.request, 'Cartão não encontrado.')
        
        return context


class FaturaCartaoDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalhar fatura"""
    model = FaturaCartao
    template_name = 'pagamentos/fatura_detalhe.html'
    permission_required = 'admin_pagamentos.view_faturacartao'
    context_object_name = 'fatura'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f'Fatura: {self.object.numero_fatura}'
        context['title'] = 'fatura_detalhe'
        
        # Transações da fatura
        context['transacoes'] = self.object.transacaocartao_set.all().order_by('-data_transacao')
        
        # Pagamentos
        context['pagamentos'] = self.object.pagamentocartao_set.all().order_by('-data_pagamento')
        
        return context


@login_required(login_url='login')
@permission_required('admin_pagamentos.add_pagamentocartao', raise_exception=True)
@handle_database_error
def pagar_fatura(request, fatura_id):
    """Pagar fatura de cartão"""
    try:
        fatura = FaturaCartao.objects.get(pk=fatura_id)
    except FaturaCartao.DoesNotExist:
        messages.error(request, 'Fatura não encontrada.')
        return redirect('admin_pagamentos:cartao_listar')
    
    if request.method == 'POST':
        valor_pagamento = request.POST.get('valor_pagamento')
        data_pagamento = request.POST.get('data_pagamento')
        
        try:
            valor = Decimal(valor_pagamento)
            
            # Criar pagamento
            pagamento = PagamentoCartao.objects.create(
                fatura=fatura,
                valor_pagamento=valor,
                data_pagamento=data_pagamento,
                status='PAGO',
                us_registro=request.user
            )
            
            # Atualizar status da fatura
            fatura.valor_pago += valor
            if fatura.valor_pago >= fatura.valor_total:
                fatura.status = 'PAGA'
            else:
                fatura.status = 'PARCIAL'
            fatura.save()
            
            messages.success(request, f'Pagamento de R$ {valor} registrado com sucesso!')
            return redirect('admin_pagamentos:fatura_detalhe', pk=fatura.pk)
        
        except (ValueError, Decimal.InvalidOperation):
            messages.error(request, 'Valor de pagamento inválido.')
    
    context = {
        'titulo': f'Pagar Fatura: {fatura.numero_fatura}',
        'title': 'fatura_pagar',
        'fatura': fatura,
    }
    
    return render(request, 'pagamentos/pagar_fatura.html', context)
