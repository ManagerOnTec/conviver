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

from .models import Tesouraria, Caixa, SaldoCaixa, MovimentacaoCaixa
from .forms import TesourariaForm, CaixaForm, SaldoCaixaForm, MovimentacaoCaixaForm
from admin_cadastros.models import Estabelecimento

logger = logging.getLogger(__name__)


def handle_database_error(view_func):
    """Decorator para tratamento de erros de banco de dados"""
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except OperationalError as e:
            logger.error(f"Erro de banco de dados: {str(e)}")
            messages.error(
                request,
                "Erro ao acessar o banco de dados. Execute: python manage.py migrate"
            )
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
# TESOURARIA
# ============================================================================

@login_required
@handle_database_error
def tesouraria_index(request):
    """Dashboard de Tesouraria"""
    estabelecimento_id = request.session.get('estabelecimento_id')
    if not estabelecimento_id:
        messages.warning(request, "Selecione um estabelecimento")
        return redirect('admin_cadastros:cadastros_index')
    
    estabelecimento = get_object_or_404(Estabelecimento, id=estabelecimento_id)
    tesourarias = Tesouraria.objects.filter(
        estabelecimento=estabelecimento,
        status='A'
    )
    
    context = {
        'estabelecimento': estabelecimento,
        'tesourarias': tesourarias,
        'total_tesourarias': tesourarias.count(),
    }
    return render(request, 'apptesouraria/tesouraria_index.html', context)


class TesourariaListView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Listar Tesourarias"""
    model = Tesouraria
    template_name = 'apptesouraria/tesouraria_listar.html'
    context_object_name = 'tesourarias'
    permission_required = 'apptesouraria.view_tesouraria'
    paginate_by = 20
    
    def get_queryset(self):
        estabelecimento_id = self.request.session.get('estabelecimento_id')
        if estabelecimento_id:
            return Tesouraria.objects.filter(
                estabelecimento_id=estabelecimento_id
            ).order_by('-data_criacao')
        return Tesouraria.objects.none()


class TesourariaCreateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Criar Tesouraria"""
    model = Tesouraria
    form_class = TesourariaForm
    template_name = 'apptesouraria/tesouraria_form.html'
    permission_required = 'apptesouraria.add_tesouraria'
    success_url = reverse_lazy('apptesouraria:tesouraria_listar')
    
    def form_valid(self, form):
        estabelecimento_id = self.request.session.get('estabelecimento_id')
        if estabelecimento_id:
            form.instance.estabelecimento_id = estabelecimento_id
            form.instance.us_registro = self.request.user
            messages.success(self.request, 'Tesouraria criada com sucesso!')
            return super().form_valid(form)
        messages.error(self.request, 'Estabelecimento não selecionado')
        return self.form_invalid(form)


class TesourariaDetailView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalhes da Tesouraria"""
    model = Tesouraria
    template_name = 'apptesouraria/tesouraria_detalhe.html'
    context_object_name = 'tesouraria'
    permission_required = 'apptesouraria.view_tesouraria'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tesouraria = self.get_object()
        context['caixas'] = tesouraria.caixas.filter(status='A')
        return context


class TesourariaUpdateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Editar Tesouraria"""
    model = Tesouraria
    form_class = TesourariaForm
    template_name = 'apptesouraria/tesouraria_form.html'
    permission_required = 'apptesouraria.change_tesouraria'
    success_url = reverse_lazy('apptesouraria:tesouraria_listar')
    
    def form_valid(self, form):
        form.instance.us_atualizacao = self.request.user
        messages.success(self.request, 'Tesouraria atualizada com sucesso!')
        return super().form_valid(form)


# ============================================================================
# CAIXA
# ============================================================================

class CaixaListView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Listar Caixas"""
    model = Caixa
    template_name = 'apptesouraria/caixa_listar.html'
    context_object_name = 'caixas'
    permission_required = 'apptesouraria.view_caixa'
    paginate_by = 20
    
    def get_queryset(self):
        tesouraria_id = self.kwargs.get('tesouraria_id')
        if tesouraria_id:
            return Caixa.objects.filter(
                tesouraria_id=tesouraria_id,
                status='A'
            ).order_by('-data_criacao')
        return Caixa.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tesouraria_id = self.kwargs.get('tesouraria_id')
        if tesouraria_id:
            context['tesouraria'] = get_object_or_404(Tesouraria, id=tesouraria_id)
        return context


class CaixaCreateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Criar Caixa"""
    model = Caixa
    form_class = CaixaForm
    template_name = 'apptesouraria/caixa_form.html'
    permission_required = 'apptesouraria.add_caixa'
    
    def get_success_url(self):
        return reverse_lazy('apptesouraria:caixa_listar', kwargs={'tesouraria_id': self.object.tesouraria.id})
    
    def form_valid(self, form):
        tesouraria_id = self.kwargs.get('tesouraria_id')
        tesouraria = get_object_or_404(Tesouraria, id=tesouraria_id)
        form.instance.tesouraria = tesouraria
        form.instance.us_registro = self.request.user
        messages.success(self.request, 'Caixa criado com sucesso!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tesouraria_id = self.kwargs.get('tesouraria_id')
        if tesouraria_id:
            context['tesouraria'] = get_object_or_404(Tesouraria, id=tesouraria_id)
        return context


class CaixaDetailView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalhes do Caixa"""
    model = Caixa
    template_name = 'apptesouraria/caixa_detalhe.html'
    context_object_name = 'caixa'
    permission_required = 'apptesouraria.view_caixa'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        caixa = self.get_object()
        context['saldos'] = caixa.saldos.order_by('-data_abertura')[:10]
        return context


class CaixaUpdateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Editar Caixa"""
    model = Caixa
    form_class = CaixaForm
    template_name = 'apptesouraria/caixa_form.html'
    permission_required = 'apptesouraria.change_caixa'
    
    def get_success_url(self):
        return reverse_lazy('apptesouraria:caixa_detalhe', kwargs={'pk': self.object.id})
    
    def form_valid(self, form):
        form.instance.us_atualizacao = self.request.user
        messages.success(self.request, 'Caixa atualizado com sucesso!')
        return super().form_valid(form)


# ============================================================================
# SALDO CAIXA
# ============================================================================

class SaldoCaixaListView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Listar Saldos de Caixa"""
    model = SaldoCaixa
    template_name = 'apptesouraria/saldocaixa_listar.html'
    context_object_name = 'saldos'
    permission_required = 'apptesouraria.view_saldocaixa'
    paginate_by = 30
    
    def get_queryset(self):
        caixa_id = self.kwargs.get('caixa_id')
        if caixa_id:
            return SaldoCaixa.objects.filter(
                caixa_id=caixa_id
            ).order_by('-data_abertura')
        return SaldoCaixa.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        caixa_id = self.kwargs.get('caixa_id')
        if caixa_id:
            context['caixa'] = get_object_or_404(Caixa, id=caixa_id)
        return context


class SaldoCaixaCreateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Abrir Saldo de Caixa"""
    model = SaldoCaixa
    form_class = SaldoCaixaForm
    template_name = 'apptesouraria/saldocaixa_form.html'
    permission_required = 'apptesouraria.add_saldocaixa'
    
    def get_success_url(self):
        return reverse_lazy('apptesouraria:saldocaixa_listar', kwargs={'caixa_id': self.object.caixa.id})
    
    def form_valid(self, form):
        caixa_id = self.kwargs.get('caixa_id')
        caixa = get_object_or_404(Caixa, id=caixa_id)
        form.instance.caixa = caixa
        form.instance.us_registro = self.request.user
        messages.success(self.request, 'Saldo de caixa aberto com sucesso!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        caixa_id = self.kwargs.get('caixa_id')
        if caixa_id:
            context['caixa'] = get_object_or_404(Caixa, id=caixa_id)
        return context


class SaldoCaixaDetailView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalhes do Saldo de Caixa"""
    model = SaldoCaixa
    template_name = 'apptesouraria/saldocaixa_detalhe.html'
    context_object_name = 'saldo'
    permission_required = 'apptesouraria.view_saldocaixa'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        saldo = self.get_object()
        movimentacoes = saldo.movimentacoes.filter(status='A')
        context['movimentacoes'] = movimentacoes
        context['total_entradas'] = movimentacoes.filter(tipo='ENTRADA').aggregate(
            total=Sum('valor')
        )['total'] or Decimal('0.00')
        context['total_saidas'] = movimentacoes.filter(tipo='SAIDA').aggregate(
            total=Sum('valor')
        )['total'] or Decimal('0.00')
        context['saldo_final_calculado'] = saldo.calcular_saldo_final()
        return context


class SaldoCaixaUpdateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Fechar Saldo de Caixa"""
    model = SaldoCaixa
    form_class = SaldoCaixaForm
    template_name = 'apptesouraria/saldocaixa_form.html'
    permission_required = 'apptesouraria.change_saldocaixa'
    
    def get_success_url(self):
        return reverse_lazy('apptesouraria:saldocaixa_detalhe', kwargs={'pk': self.object.id})
    
    def form_valid(self, form):
        form.instance.us_atualizacao = self.request.user
        messages.success(self.request, 'Saldo de caixa atualizado com sucesso!')
        return super().form_valid(form)


# ============================================================================
# MOVIMENTAÇÃO CAIXA
# ============================================================================

class MovimentacaoCaixaListView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Listar Movimentações de Caixa"""
    model = MovimentacaoCaixa
    template_name = 'apptesouraria/movimentacaocaixa_listar.html'
    context_object_name = 'movimentacoes'
    permission_required = 'apptesouraria.view_movimentacaocaixa'
    paginate_by = 50
    
    def get_queryset(self):
        saldo_id = self.kwargs.get('saldo_id')
        if saldo_id:
            return MovimentacaoCaixa.objects.filter(
                saldo_caixa_id=saldo_id,
                status='A'
            ).order_by('-data_criacao')
        return MovimentacaoCaixa.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        saldo_id = self.kwargs.get('saldo_id')
        if saldo_id:
            saldo = get_object_or_404(SaldoCaixa, id=saldo_id)
            context['saldo'] = saldo
            movimentacoes = self.get_queryset()
            context['total_entradas'] = movimentacoes.filter(tipo='ENTRADA').aggregate(
                total=Sum('valor')
            )['total'] or Decimal('0.00')
            context['total_saidas'] = movimentacoes.filter(tipo='SAIDA').aggregate(
                total=Sum('valor')
            )['total'] or Decimal('0.00')
        return context


class MovimentacaoCaixaCreateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Criar Movimentação de Caixa"""
    model = MovimentacaoCaixa
    form_class = MovimentacaoCaixaForm
    template_name = 'apptesouraria/movimentacaocaixa_form.html'
    permission_required = 'apptesouraria.add_movimentacaocaixa'
    
    def get_success_url(self):
        return reverse_lazy('apptesouraria:movimentacaocaixa_listar', kwargs={'saldo_id': self.object.saldo_caixa.id})
    
    def form_valid(self, form):
        saldo_id = self.kwargs.get('saldo_id')
        saldo = get_object_or_404(SaldoCaixa, id=saldo_id)
        form.instance.saldo_caixa = saldo
        form.instance.us_registro = self.request.user
        messages.success(self.request, 'Movimentação criada com sucesso!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        saldo_id = self.kwargs.get('saldo_id')
        if saldo_id:
            context['saldo'] = get_object_or_404(SaldoCaixa, id=saldo_id)
        return context


class MovimentacaoCaixaDetailView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalhes da Movimentação de Caixa"""
    model = MovimentacaoCaixa
    template_name = 'apptesouraria/movimentacaocaixa_detalhe.html'
    context_object_name = 'movimentacao'
    permission_required = 'apptesouraria.view_movimentacaocaixa'


class MovimentacaoCaixaUpdateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Editar Movimentação de Caixa"""
    model = MovimentacaoCaixa
    form_class = MovimentacaoCaixaForm
    template_name = 'apptesouraria/movimentacaocaixa_form.html'
    permission_required = 'apptesouraria.change_movimentacaocaixa'
    
    def get_success_url(self):
        return reverse_lazy('apptesouraria:movimentacaocaixa_detalhe', kwargs={'pk': self.object.id})
    
    def form_valid(self, form):
        form.instance.us_atualizacao = self.request.user
        messages.success(self.request, 'Movimentação atualizada com sucesso!')
        return super().form_valid(form)
