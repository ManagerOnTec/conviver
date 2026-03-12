from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Sum
from django.utils import timezone
from django.db import OperationalError
from django.shortcuts import render, redirect
from decimal import Decimal
import csv
from io import TextIOWrapper
from datetime import datetime
from functools import wraps

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
                    'Banco de dados não foi inicializado. Execute: python manage.py migrate admin_conciliacao'
                )
            elif 'no such column' in error_msg:
                messages.error(
                    request,
                    'Estrutura do banco de dados está desatualizada. Execute: python manage.py migrate admin_conciliacao'
                )
            else:
                messages.error(request, f'Erro no banco de dados: {error_msg}')
            return redirect('cadastros_index')
    return wrapper

from .models import (
    ExtratoBancario,
    TransacaoExtrato,
    Conciliacao,
    DivergenciaConciliacao
)
from .forms import (
    ExtratoBancarioForm,
    TransacaoExtratoForm,
    ConciliacaoForm,
    DivergenciaConciliacaoForm,
    ImportarExtratoCSVForm,
    FiltrosConciliacaoForm
)
from admin_financeiro.models import CompetenciaBancaria, MovimentoBancario
from admin_cadastros.models import Estabelecimento


@login_required
@handle_database_error
@handle_database_error
def index_conciliacao(request):
    """
    View principal do módulo de conciliação.
    Exibe um resumo das conciliações e acesso aos diferentes módulos.
    """
    
    # Obter estatísticas gerais
    total_extratos = ExtratoBancario.objects.filter(status='A').count()
    total_transacoes = TransacaoExtrato.objects.filter(conciliada=False).count()
    total_conciliadas = Conciliacao.objects.filter(status='C').count()
    total_divergencias = DivergenciaConciliacao.objects.filter(resolvida=False).count()
    
    # Conciliações recentes
    conciliacoes_recentes = Conciliacao.objects.select_related(
        'transacao_extrato',
        'movimento_bancario',
        'competencia_bancaria'
    ).order_by('-dt_registro')[:10]
    
    # Divergências não resolvidas
    divergencias_nao_resolvidas = DivergenciaConciliacao.objects.filter(
        resolvida=False
    ).select_related('conciliacao').order_by('-prioridade', '-dt_registro')[:5]
    
    contexto = {
        'total_extratos': total_extratos,
        'total_transacoes': total_transacoes,
        'total_conciliadas': total_conciliadas,
        'total_divergencias': total_divergencias,
        'conciliacoes_recentes': conciliacoes_recentes,
        'divergencias_nao_resolvidas': divergencias_nao_resolvidas,
    }
    
    return render(request, 'admin_conciliacao/index.html', contexto)


@login_required
@handle_database_error
@handle_database_error
def listar_extratos(request):
    """
    Lista todos os extratos bancários importados.
    """
    
    extratos = ExtratoBancario.objects.select_related(
        'conta',
        'competencia_bancaria',
        'estabelecimento'
    ).filter(status='A').order_by('-dt_registro')
    
    # Filtros
    competencia = request.GET.get('competencia')
    conta = request.GET.get('conta')
    
    if competencia:
        extratos = extratos.filter(competencia_bancaria_id=competencia)
    
    if conta:
        extratos = extratos.filter(conta_id=conta)
    
    contexto = {
        'extratos': extratos,
        'competencias': CompetenciaBancaria.objects.filter(status='A'),
    }
    
    return render(request, 'admin_conciliacao/listar_extratos.html', contexto)


@login_required
@handle_database_error
@require_http_methods(["GET", "POST"])
def criar_extrato(request):
    """
    Cria um novo extrato bancário.
    """
    
    if request.method == 'POST':
        form = ExtratoBancarioForm(request.POST, request.FILES)
        if form.is_valid():
            extrato = form.save(commit=False)
            extrato.us_registro = request.user
            
            # Obter o estabelecimento do usuário (assumindo que existe uma relação)
            try:
                extrato.estabelecimento = request.user.estabelecimento_set.first() or Estabelecimento.objects.first()
            except:
                extrato.estabelecimento = Estabelecimento.objects.first()
            
            extrato.save()
            
            # Se houver arquivo, processar as transações
            if extrato.arquivo:
                processar_arquivo_extrato(extrato, request)
            
            messages.success(request, 'Extrato bancário criado com sucesso!')
            return redirect('admin_conciliacao:detalhar_extrato', pk=extrato.pk)
    else:
        form = ExtratoBancarioForm()
    
    contexto = {
        'form': form,
        'titulo': 'Criar Novo Extrato Bancário',
    }
    
    return render(request, 'admin_conciliacao/criar_extrato.html', contexto)


@login_required
@handle_database_error
def detalhar_extrato(request, pk):
    """
    Exibe os detalhes de um extrato bancário e suas transações.
    """
    
    extrato = get_object_or_404(ExtratoBancario, pk=pk)
    transacoes = extrato.transacoes.all().order_by('-data_transacao')
    
    # Estatísticas
    total_transacoes = transacoes.count()
    transacoes_conciliadas = transacoes.filter(conciliada=True).count()
    transacoes_pendentes = transacoes.filter(conciliada=False).count()
    
    contexto = {
        'extrato': extrato,
        'transacoes': transacoes,
        'total_transacoes': total_transacoes,
        'transacoes_conciliadas': transacoes_conciliadas,
        'transacoes_pendentes': transacoes_pendentes,
    }
    
    return render(request, 'admin_conciliacao/detalhar_extrato.html', contexto)


@login_required
@handle_database_error
def conciliar_transacoes(request):
    """
    Tela principal de conciliação.
    Exibe transações do extrato e movimentos internos para conciliação.
    """
    
    form = FiltrosConciliacaoForm(request.GET or None)
    
    # Transações do extrato não conciliadas
    transacoes_extrato = TransacaoExtrato.objects.filter(
        conciliada=False
    ).select_related('extrato_bancario').order_by('-data_transacao')
    
    # Movimentos bancários não conciliados
    movimentos = MovimentoBancario.objects.select_related(
        'competencia_bancaria',
        'transacao_financeira'
    ).order_by('-competencia_bancaria__dt_abertura_competencia')
    
    # Aplicar filtros
    if form.is_valid():
        competencia = form.cleaned_data.get('competencia_bancaria')
        conta = form.cleaned_data.get('conta')
        data_inicio = form.cleaned_data.get('data_inicio')
        data_fim = form.cleaned_data.get('data_fim')
        valor_minimo = form.cleaned_data.get('valor_minimo')
        valor_maximo = form.cleaned_data.get('valor_maximo')
        descricao = form.cleaned_data.get('descricao')
        
        if competencia:
            transacoes_extrato = transacoes_extrato.filter(
                extrato_bancario__competencia_bancaria=competencia
            )
            movimentos = movimentos.filter(competencia_bancaria=competencia)
        
        if conta:
            transacoes_extrato = transacoes_extrato.filter(
                extrato_bancario__conta=conta
            )
        
        if data_inicio:
            transacoes_extrato = transacoes_extrato.filter(
                data_transacao__gte=data_inicio
            )
        
        if data_fim:
            transacoes_extrato = transacoes_extrato.filter(
                data_transacao__lte=data_fim
            )
        
        if valor_minimo:
            transacoes_extrato = transacoes_extrato.filter(
                valor__gte=valor_minimo
            )
        
        if valor_maximo:
            transacoes_extrato = transacoes_extrato.filter(
                valor__lte=valor_maximo
            )
        
        if descricao:
            transacoes_extrato = transacoes_extrato.filter(
                Q(descricao__icontains=descricao) |
                Q(numero_documento__icontains=descricao)
            )
    
    contexto = {
        'form': form,
        'transacoes_extrato': transacoes_extrato[:50],  # Limitar para performance
        'movimentos': movimentos[:50],
    }
    
    return render(request, 'admin_conciliacao/conciliar_transacoes.html', contexto)


@login_required
@handle_database_error
@require_http_methods(["POST"])
def criar_conciliacao(request):
    """
    Cria uma nova conciliação entre uma transação do extrato e um movimento.
    """
    
    transacao_id = request.POST.get('transacao_id')
    movimento_id = request.POST.get('movimento_id')
    competencia_id = request.POST.get('competencia_id')
    
    try:
        transacao = TransacaoExtrato.objects.get(pk=transacao_id)
        movimento = MovimentoBancario.objects.get(pk=movimento_id) if movimento_id else None
        competencia = CompetenciaBancaria.objects.get(pk=competencia_id)
        
        # Criar a conciliação
        conciliacao = Conciliacao.objects.create(
            transacao_extrato=transacao,
            movimento_bancario=movimento,
            competencia_bancaria=competencia,
            valor_conciliado=transacao.valor,
            status='C' if movimento and abs(transacao.valor - (movimento.valor_entrada or movimento.valor_saida or Decimal('0'))) < Decimal('0.01') else 'D',
            us_registro=request.user,
            estabelecimento=competencia.estabelecimento,
        )
        
        # Marcar a transação como conciliada
        transacao.conciliada = True
        transacao.save()
        
        messages.success(request, 'Conciliação criada com sucesso!')
        return redirect('admin_conciliacao:conciliar_transacoes')
    
    except Exception as e:
        messages.error(request, f'Erro ao criar conciliação: {str(e)}')
        return redirect('admin_conciliacao:conciliar_transacoes')


@login_required
@handle_database_error
def listar_conciliações(request):
    """
    Lista todas as conciliações realizadas.
    """
    
    conciliacoes = Conciliacao.objects.select_related(
        'transacao_extrato',
        'movimento_bancario',
        'competencia_bancaria'
    ).order_by('-dt_registro')
    
    # Filtros
    status = request.GET.get('status')
    competencia = request.GET.get('competencia')
    
    if status:
        conciliacoes = conciliacoes.filter(status=status)
    
    if competencia:
        conciliacoes = conciliacoes.filter(competencia_bancaria_id=competencia)
    
    contexto = {
        'conciliacoes': conciliacoes,
        'competencias': CompetenciaBancaria.objects.filter(status='A'),
    }
    
    return render(request, 'admin_conciliacao/listar_conciliações.html', contexto)


@login_required
@handle_database_error
def detalhar_conciliacao(request, pk):
    """
    Exibe os detalhes de uma conciliação.
    """
    
    conciliacao = get_object_or_404(Conciliacao, pk=pk)
    divergencias = conciliacao.divergencias.all()
    
    contexto = {
        'conciliacao': conciliacao,
        'divergencias': divergencias,
    }
    
    return render(request, 'admin_conciliacao/detalhar_conciliacao.html', contexto)


@login_required
@handle_database_error
def listar_divergencias(request):
    """
    Lista todas as divergências encontradas.
    """
    
    divergencias = DivergenciaConciliacao.objects.select_related(
        'conciliacao'
    ).order_by('-prioridade', '-dt_registro')
    
    # Filtros
    resolvida = request.GET.get('resolvida')
    prioridade = request.GET.get('prioridade')
    tipo = request.GET.get('tipo')
    
    if resolvida:
        divergencias = divergencias.filter(resolvida=(resolvida == 'true'))
    
    if prioridade:
        divergencias = divergencias.filter(prioridade=prioridade)
    
    if tipo:
        divergencias = divergencias.filter(tipo_divergencia=tipo)
    
    contexto = {
        'divergencias': divergencias,
    }
    
    return render(request, 'admin_conciliacao/listar_divergencias.html', contexto)


def processar_arquivo_extrato(extrato, request):
    """
    Processa o arquivo do extrato e cria as transações.
    Suporta CSV.
    """
    
    try:
        arquivo = extrato.arquivo
        arquivo.seek(0)
        
        if extrato.tipo_arquivo == 'CSV':
            wrapper = TextIOWrapper(arquivo.file, encoding='utf-8')
            reader = csv.DictReader(wrapper)
            
            total_entradas = Decimal('0.00')
            total_saidas = Decimal('0.00')
            quantidade = 0
            
            for linha in reader:
                try:
                    data = datetime.strptime(linha.get('data', ''), '%d/%m/%Y').date()
                    descricao = linha.get('descricao', '')[:255]
                    tipo = linha.get('tipo', 'D').upper()[0]
                    valor = Decimal(str(linha.get('valor', '0').replace(',', '.')))
                    
                    TransacaoExtrato.objects.create(
                        extrato_bancario=extrato,
                        data_transacao=data,
                        descricao=descricao,
                        tipo_transacao=tipo,
                        valor=valor,
                        numero_documento=linha.get('numero_documento', '')[:50],
                        referencia_banco=linha.get('referencia_banco', '')[:100],
                    )
                    
                    if tipo == 'C':
                        total_entradas += valor
                    else:
                        total_saidas += valor
                    
                    quantidade += 1
                
                except Exception as e:
                    print(f'Erro ao processar linha: {str(e)}')
                    continue
            
            # Atualizar o extrato com as estatísticas
            extrato.total_entradas = total_entradas
            extrato.total_saidas = total_saidas
            extrato.quantidade_transacoes = quantidade
            extrato.save()
            
            messages.success(
                request,
                f'{quantidade} transações importadas com sucesso!'
            )
    
    except Exception as e:
        messages.error(request, f'Erro ao processar arquivo: {str(e)}')
