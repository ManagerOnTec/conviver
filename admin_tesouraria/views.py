import logging
from functools import wraps
from datetime import datetime, date, timedelta
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Sum, Q
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseForbidden
from django.db import OperationalError
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.utils import timezone

from .models import Caixa, SaldoCaixa, MovimentacaoCaixa
from .forms import CaixaForm, SaldoCaixaForm, MovimentacaoCaixaForm
from admin_cadastros.models import Estabelecimento

logger = logging.getLogger(__name__)


def handle_database_error(view_func):
    """Decorator para tratamento de erros de banco de dados"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except OperationalError as e:
            logger.error(f"Erro de banco de dados em {view_func.__name__}: {str(e)}")
            messages.error(
                request,
                "Erro ao acessar o banco de dados. Execute: python manage.py migrate admin_tesouraria"
            )
            return redirect('admin_cadastros:cadastros_index')
        except Exception as e:
            logger.error(f"Erro em {view_func.__name__}: {str(e)}")
            messages.error(request, f"Erro: {str(e)}")
            return redirect('admin_cadastros:cadastros_index')
    return wrapper


class HandleDatabaseErrorMixin:
    """Mixin para tratamento de erros em CBVs"""
    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except OperationalError as e:
            logger.error(f"Erro de banco de dados em {self.__class__.__name__}: {str(e)}")
            messages.error(
                request,
                "Erro ao acessar o banco de dados. Execute: python manage.py migrate admin_tesouraria"
            )
            return redirect('admin_cadastros:cadastros_index')
        except Exception as e:
            logger.error(f"Erro em {self.__class__.__name__}: {str(e)}")
            messages.error(request, f"Erro: {str(e)}")
            return redirect('admin_cadastros:cadastros_index')


# ============================================================================
# DASHBOARD E INDEX
# ============================================================================

@login_required
@handle_database_error
def tesouraria_index(request):
    """Dashboard principal de tesouraria"""
    try:
        # Obter estabelecimento da sessão
        estabelecimento_id = request.session.get('estabelecimento_id')
        if not estabelecimento_id:
            messages.warning(request, "Selecione um estabelecimento primeiro")
            return redirect('admin_cadastros:cadastros_index')
        
        estabelecimento = get_object_or_404(Estabelecimento, id=estabelecimento_id)
        
        # Estatísticas do dia
        hoje = date.today()
        caixas = Caixa.objects.filter(estabelecimento=estabelecimento, status='A')
        
        # Saldos de hoje
        saldos_hoje = SaldoCaixa.objects.filter(
            caixa__estabelecimento=estabelecimento,
            data_abertura=hoje
        )
        
        # Movimentações de hoje
        movimentacoes_hoje = MovimentacaoCaixa.objects.filter(
            saldo_caixa__caixa__estabelecimento=estabelecimento,
            data_criacao__date=hoje
        )
        
        # Totalizações
        total_entradas = movimentacoes_hoje.filter(tipo='ENTRADA').aggregate(
            total=Sum('valor')
        )['total'] or Decimal('0.00')
        
        total_saidas = movimentacoes_hoje.filter(tipo='SAIDA').aggregate(
            total=Sum('valor')
        )['total'] or Decimal('0.00')
        
        context = {
            'estabelecimento': estabelecimento,
            'caixas': caixas,
            'saldos_hoje': saldos_hoje,
            'movimentacoes_hoje': movimentacoes_hoje,
            'total_entradas': total_entradas,
            'total_saidas': total_saidas,
            'saldo_liquido': total_entradas - total_saidas,
            'quantidade_caixas': caixas.count(),
            'quantidade_movimentacoes': movimentacoes_hoje.count(),
        }
        
        return render(request, 'tesouraria/tesouraria_index.html', context)
    except Exception as e:
        logger.error(f"Erro em tesouraria_index: {str(e)}")
        messages.error(request, f"Erro ao carregar dashboard: {str(e)}")
        return redirect('admin_cadastros:cadastros_index')


# ============================================================================
# CAIXA - LISTAR, CRIAR, DETALHE, EDITAR
# ============================================================================

class CaixaListView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Listar caixas"""
    model = Caixa
    template_name = 'tesouraria/caixa_listar.html'
    context_object_name = 'caixas'
    permission_required = 'admin_tesouraria.view_caixa'
    paginate_by = 20
    
    def get_queryset(self):
        estabelecimento_id = self.request.session.get('estabelecimento_id')
        if estabelecimento_id:
            return Caixa.objects.filter(
                estabelecimento_id=estabelecimento_id,
                status='A'
            ).order_by('-data_criacao')
        return Caixa.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estabelecimento_id = self.request.session.get('estabelecimento_id')
        if estabelecimento_id:
            context['estabelecimento'] = get_object_or_404(
                Estabelecimento,
                id=estabelecimento_id
            )
        return context


class CaixaCreateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Criar novo caixa"""
    model = Caixa
    form_class = CaixaForm
    template_name = 'tesouraria/caixa_form.html'
    permission_required = 'admin_tesouraria.add_caixa'
    success_url = reverse_lazy('admin_tesouraria:caixa_listar')
    
    def form_valid(self, form):
        estabelecimento_id = self.request.session.get('estabelecimento_id')
        if estabelecimento_id:
            form.instance.estabelecimento_id = estabelecimento_id
            form.instance.us_registro = self.request.user
            messages.success(self.request, 'Caixa criado com sucesso!')
            return super().form_valid(form)
        messages.error(self.request, 'Estabelecimento não selecionado')
        return self.form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estabelecimento_id = self.request.session.get('estabelecimento_id')
        if estabelecimento_id:
            context['estabelecimento'] = get_object_or_404(
                Estabelecimento,
                id=estabelecimento_id
            )
        return context


class CaixaDetailView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalhes do caixa"""
    model = Caixa
    template_name = 'tesouraria/caixa_detalhe.html'
    context_object_name = 'caixa'
    permission_required = 'admin_tesouraria.view_caixa'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        caixa = self.get_object()
        
        # Saldos do caixa
        saldos = SaldoCaixa.objects.filter(caixa=caixa).order_by('-data_abertura')
        context['saldos'] = saldos[:10]  # Últimos 10
        
        # Movimentações recentes
        movimentacoes = MovimentacaoCaixa.objects.filter(
            saldo_caixa__caixa=caixa
        ).order_by('-data_criacao')[:20]
        context['movimentacoes'] = movimentacoes
        
        return context


class CaixaUpdateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Editar caixa"""
    model = Caixa
    form_class = CaixaForm
    template_name = 'tesouraria/caixa_form.html'
    permission_required = 'admin_tesouraria.change_caixa'
    success_url = reverse_lazy('admin_tesouraria:caixa_listar')
    
    def form_valid(self, form):
        form.instance.us_atualizacao = self.request.user
        messages.success(self.request, 'Caixa atualizado com sucesso!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['edit'] = True
        return context


# ============================================================================
# ABRIR E FECHAR CAIXA
# ============================================================================

@login_required
@permission_required('admin_tesouraria.add_saldocaixa')
@handle_database_error
def abrir_caixa(request, pk):
    """Abrir caixa para o dia"""
    caixa = get_object_or_404(Caixa, pk=pk)
    
    if request.method == 'POST':
        try:
            # Verificar se já existe saldo aberto para hoje
            hoje = date.today()
            saldo_existente = SaldoCaixa.objects.filter(
                caixa=caixa,
                data_abertura=hoje,
                status='A'
            ).first()
            
            if saldo_existente:
                messages.warning(request, 'Caixa já está aberto para hoje')
                return redirect('admin_tesouraria:caixa_detalhe', pk=pk)
            
            # Criar novo saldo
            saldo_inicial = Decimal(request.POST.get('saldo_inicial', '0.00'))
            
            saldo_caixa = SaldoCaixa.objects.create(
                caixa=caixa,
                data_abertura=hoje,
                saldo_inicial=saldo_inicial,
                us_registro=request.user
            )
            
            messages.success(request, f'Caixa aberto com saldo inicial R$ {saldo_inicial}')
            logger.info(f"Caixa {caixa.id} aberto por {request.user.username}")
            
            return redirect('admin_tesouraria:caixa_detalhe', pk=pk)
        except Exception as e:
            logger.error(f"Erro ao abrir caixa: {str(e)}")
            messages.error(request, f"Erro ao abrir caixa: {str(e)}")
            return redirect('admin_tesouraria:caixa_detalhe', pk=pk)
    
    context = {
        'caixa': caixa,
        'action': 'abrir'
    }
    return render(request, 'tesouraria/caixa_abrir.html', context)


@login_required
@permission_required('admin_tesouraria.change_saldocaixa')
@handle_database_error
def fechar_caixa(request, pk):
    """Fechar caixa do dia"""
    caixa = get_object_or_404(Caixa, pk=pk)
    
    if request.method == 'POST':
        try:
            # Obter saldo aberto de hoje
            hoje = date.today()
            saldo_caixa = SaldoCaixa.objects.filter(
                caixa=caixa,
                data_abertura=hoje,
                status='A'
            ).first()
            
            if not saldo_caixa:
                messages.error(request, 'Nenhum caixa aberto para hoje')
                return redirect('admin_tesouraria:caixa_detalhe', pk=pk)
            
            # Calcular saldo final
            movimentacoes = MovimentacaoCaixa.objects.filter(saldo_caixa=saldo_caixa)
            total_entradas = movimentacoes.filter(tipo='ENTRADA').aggregate(
                total=Sum('valor')
            )['total'] or Decimal('0.00')
            total_saidas = movimentacoes.filter(tipo='SAIDA').aggregate(
                total=Sum('valor')
            )['total'] or Decimal('0.00')
            
            saldo_final = saldo_caixa.saldo_inicial + total_entradas - total_saidas
            
            # Atualizar saldo
            saldo_caixa.saldo_final = saldo_final
            saldo_caixa.status = 'F'
            saldo_caixa.us_atualizacao = request.user
            saldo_caixa.save()
            
            messages.success(
                request,
                f'Caixa fechado com saldo final R$ {saldo_final}'
            )
            logger.info(f"Caixa {caixa.id} fechado por {request.user.username}")
            
            return redirect('admin_tesouraria:caixa_detalhe', pk=pk)
        except Exception as e:
            logger.error(f"Erro ao fechar caixa: {str(e)}")
            messages.error(request, f"Erro ao fechar caixa: {str(e)}")
            return redirect('admin_tesouraria:caixa_detalhe', pk=pk)
    
    # Obter informações para confirmação
    hoje = date.today()
    saldo_caixa = SaldoCaixa.objects.filter(
        caixa=caixa,
        data_abertura=hoje,
        status='A'
    ).first()
    
    if saldo_caixa:
        movimentacoes = MovimentacaoCaixa.objects.filter(saldo_caixa=saldo_caixa)
        total_entradas = movimentacoes.filter(tipo='ENTRADA').aggregate(
            total=Sum('valor')
        )['total'] or Decimal('0.00')
        total_saidas = movimentacoes.filter(tipo='SAIDA').aggregate(
            total=Sum('valor')
        )['total'] or Decimal('0.00')
        saldo_final = saldo_caixa.saldo_inicial + total_entradas - total_saidas
    else:
        saldo_final = Decimal('0.00')
        total_entradas = Decimal('0.00')
        total_saidas = Decimal('0.00')
    
    context = {
        'caixa': caixa,
        'saldo_caixa': saldo_caixa,
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'saldo_final': saldo_final,
        'action': 'fechar'
    }
    return render(request, 'tesouraria/caixa_fechar.html', context)


# ============================================================================
# MOVIMENTAÇÕES - LISTAR, CRIAR, EDITAR, DELETAR
# ============================================================================

class MovimentacaoCaixaListView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Listar movimentações de um caixa"""
    model = MovimentacaoCaixa
    template_name = 'tesouraria/movimentacao_listar.html'
    context_object_name = 'movimentacoes'
    permission_required = 'admin_tesouraria.view_movimentacaocaixa'
    paginate_by = 50
    
    def get_queryset(self):
        saldo_id = self.kwargs.get('saldo_id')
        return MovimentacaoCaixa.objects.filter(
            saldo_caixa_id=saldo_id,
            status='A'
        ).order_by('-data_criacao')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        saldo_id = self.kwargs.get('saldo_id')
        saldo_caixa = get_object_or_404(SaldoCaixa, id=saldo_id)
        context['saldo_caixa'] = saldo_caixa
        context['caixa'] = saldo_caixa.caixa
        
        # Totalizações
        movimentacoes = self.get_queryset()
        context['total_entradas'] = movimentacoes.filter(tipo='ENTRADA').aggregate(
            total=Sum('valor')
        )['total'] or Decimal('0.00')
        context['total_saidas'] = movimentacoes.filter(tipo='SAIDA').aggregate(
            total=Sum('valor')
        )['total'] or Decimal('0.00')
        
        return context


class MovimentacaoCaixaCreateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Criar movimentação de caixa"""
    model = MovimentacaoCaixa
    form_class = MovimentacaoCaixaForm
    template_name = 'tesouraria/movimentacao_form.html'
    permission_required = 'admin_tesouraria.add_movimentacaocaixa'
    
    def get_success_url(self):
        saldo_id = self.kwargs.get('saldo_id')
        return reverse_lazy('admin_tesouraria:movimentacao_listar', kwargs={'saldo_id': saldo_id})
    
    def form_valid(self, form):
        saldo_id = self.kwargs.get('saldo_id')
        saldo_caixa = get_object_or_404(SaldoCaixa, id=saldo_id)
        
        form.instance.saldo_caixa = saldo_caixa
        form.instance.us_registro = self.request.user
        
        messages.success(self.request, 'Movimentação criada com sucesso!')
        logger.info(
            f"Movimentação {form.instance.tipo} criada por {self.request.user.username}"
        )
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        saldo_id = self.kwargs.get('saldo_id')
        saldo_caixa = get_object_or_404(SaldoCaixa, id=saldo_id)
        context['saldo_caixa'] = saldo_caixa
        context['caixa'] = saldo_caixa.caixa
        return context


class MovimentacaoCaixaUpdateView(HandleDatabaseErrorMixin, LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Editar movimentação de caixa"""
    model = MovimentacaoCaixa
    form_class = MovimentacaoCaixaForm
    template_name = 'tesouraria/movimentacao_form.html'
    permission_required = 'admin_tesouraria.change_movimentacaocaixa'
    
    def get_success_url(self):
        saldo_id = self.object.saldo_caixa.id
        return reverse_lazy('admin_tesouraria:movimentacao_listar', kwargs={'saldo_id': saldo_id})
    
    def form_valid(self, form):
        form.instance.us_atualizacao = self.request.user
        messages.success(self.request, 'Movimentação atualizada com sucesso!')
        logger.info(
            f"Movimentação {form.instance.id} atualizada por {self.request.user.username}"
        )
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['edit'] = True
        context['saldo_caixa'] = self.object.saldo_caixa
        context['caixa'] = self.object.saldo_caixa.caixa
        return context


@login_required
@permission_required('admin_tesouraria.delete_movimentacaocaixa')
@handle_database_error
def deletar_movimentacao(request, pk):
    """Deletar movimentação de caixa"""
    movimentacao = get_object_or_404(MovimentacaoCaixa, pk=pk)
    saldo_id = movimentacao.saldo_caixa.id
    
    if request.method == 'POST':
        try:
            movimentacao.delete()
            messages.success(request, 'Movimentação deletada com sucesso!')
            logger.info(f"Movimentação {pk} deletada por {request.user.username}")
        except Exception as e:
            logger.error(f"Erro ao deletar movimentação: {str(e)}")
            messages.error(request, f"Erro ao deletar: {str(e)}")
        
        return redirect('admin_tesouraria:movimentacao_listar', saldo_id=saldo_id)
    
    context = {
        'movimentacao': movimentacao,
        'saldo_caixa': movimentacao.saldo_caixa
    }
    return render(request, 'tesouraria/movimentacao_deletar.html', context)


# ============================================================================
# RELATÓRIOS
# ============================================================================

@login_required
@handle_database_error
def relatorio_tesouraria(request):
    """Relatório de tesouraria"""
    estabelecimento_id = request.session.get('estabelecimento_id')
    if not estabelecimento_id:
        messages.warning(request, "Selecione um estabelecimento primeiro")
        return redirect('admin_cadastros:cadastros_index')
    
    estabelecimento = get_object_or_404(Estabelecimento, id=estabelecimento_id)
    
    # Filtros
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    tipo_movimentacao = request.GET.get('tipo')
    
    # Query base
    caixas = Caixa.objects.filter(estabelecimento=estabelecimento, status='A')
    saldos = SaldoCaixa.objects.filter(caixa__in=caixas)
    movimentacoes = MovimentacaoCaixa.objects.filter(saldo_caixa__in=saldos)
    
    # Aplicar filtros
    if data_inicio:
        try:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            saldos = saldos.filter(data_abertura__gte=data_inicio_obj)
            movimentacoes = movimentacoes.filter(data_criacao__date__gte=data_inicio_obj)
        except ValueError:
            pass
    
    if data_fim:
        try:
            data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
            saldos = saldos.filter(data_abertura__lte=data_fim_obj)
            movimentacoes = movimentacoes.filter(data_criacao__date__lte=data_fim_obj)
        except ValueError:
            pass
    
    if tipo_movimentacao:
        movimentacoes = movimentacoes.filter(tipo=tipo_movimentacao)
    
    # Totalizações
    total_entradas = movimentacoes.filter(tipo='ENTRADA').aggregate(
        total=Sum('valor')
    )['total'] or Decimal('0.00')
    
    total_saidas = movimentacoes.filter(tipo='SAIDA').aggregate(
        total=Sum('valor')
    )['total'] or Decimal('0.00')
    
    total_saldos = saldos.aggregate(total=Sum('saldo_final'))['total'] or Decimal('0.00')
    
    context = {
        'estabelecimento': estabelecimento,
        'caixas': caixas,
        'saldos': saldos.order_by('-data_abertura'),
        'movimentacoes': movimentacoes.order_by('-data_criacao'),
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'total_saldos': total_saldos,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'tipo': tipo_movimentacao,
    }
    
    return render(request, 'tesouraria/relatorio_tesouraria.html', context)
