"""Tela DEDICADA de Conciliação Bancária (item do menu do financeiro).

Fluxo:
  1) escolhe a COMPETÊNCIA (lista só as abertas do banco/estabelecimento);
  2) importa o extrato (OFX/PDF) dessa competência — cria as linhas;
  3) concilia linha × movimento (sugestão por data+valor), concilia/ignora;
  4) finaliza a conciliação → habilita o FECHAMENTO da competência.

Fica FORA do admin de competência: é uma página própria no menu.
"""
from decimal import Decimal

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import (CompetenciaBancaria, MovimentoBancario, ExtratoImportado,
                     LinhaExtrato, ConciliacaoBancaria)
from .extrato_parser import parse_arquivo


@staff_member_required
def conciliacao_index(request):
    """Seleção da competência + importação do extrato."""
    competencias = CompetenciaBancaria.objects.filter(
        dt_fechamento_competencia=None, status='A'
    ).select_related('controle_bancario__conta__agencia__banco').order_by(
        '-dt_abertura_competencia')

    competencia_id = request.GET.get('competencia') or request.POST.get(
        'competencia')
    competencia = None
    if competencia_id:
        competencia = CompetenciaBancaria.objects.filter(
            pk=competencia_id, dt_fechamento_competencia=None).first()
        if competencia is None:
            messages.warning(
                request,
                'Competência não encontrada ou já fechada. Escolha uma '
                'competência aberta.')
    if competencia is None and competencias.exists():
        competencia = competencias.first()

    if request.method == 'POST' and request.POST.get('acao') == 'importar':
        if competencia is None:
            messages.error(request, 'Escolha a competência antes de importar.')
        else:
            arquivo = request.FILES.get('arquivo')
            if arquivo is None:
                messages.error(request, 'Selecione o arquivo (OFX ou PDF).')
            else:
                _importar(request, competencia, arquivo)
        return redirect(f"{request.path}?competencia={competencia.pk}"
                        if competencia else request.path)

    extrato = None
    conc = None
    if competencia is not None:
        extrato = ExtratoImportado.objects.filter(
            competencia_bancaria=competencia).order_by('-pk').first()
        conc = getattr(competencia, 'conciliacao', None)

    return render(request, 'admin_financeiro/conciliacao_index.html', {
        **admin_context(request),
        'competencias': competencias,
        'competencia': competencia,
        'extrato': extrato,
        'conciliacao': conc,
    })


def _importar(request, competencia, arquivo):
    """Lê o arquivo e cria o extrato + linhas (dedupe por fitid)."""
    try:
        tipo, transacoes, saldo_final = parse_arquivo(
            arquivo.name, arquivo.read())
    except Exception as erro:
        messages.error(
            request, f'Não foi possível ler o extrato "{arquivo.name}": '
                     f'{erro}')
        return
    if not transacoes:
        messages.warning(
            request, 'Nenhuma transação encontrada no arquivo. Confira se o '
                     'extrato é do formato OFX ou PDF do banco.')
        return
    with transaction.atomic():
        extrato = ExtratoImportado.objects.create(
            competencia_bancaria=competencia, arquivo=arquivo, tipo=tipo,
            dt_inicio=min(t['data'] for t in transacoes),
            dt_fim=max(t['data'] for t in transacoes),
            saldo_final_extrato=saldo_final, us_registro=request.user)
        criadas = 0
        for t in transacoes:
            _, criada = LinhaExtrato.objects.get_or_create(
                extrato=extrato, fitid=t['fitid'],
                defaults={'dt_lancamento': t['data'], 'valor': t['valor'],
                          'descricao': t['descricao'][:255],
                          'documento': t['documento']})
            criadas += 1 if criada else 0
        ConciliacaoBancaria.objects.get_or_create(
            competencia_bancaria=competencia,
            defaults={'us_registro': request.user,
                      'saldo_informado': saldo_final or 0,
                      'saldo_calculado': competencia.saldo_atual or 0})
    messages.success(
        request, f'Extrato importado: {criadas} linha(s) de '
                 f'{len(transacoes)} transação(ões).')


@staff_member_required
def conciliacao_detalhe(request, extrato_id):
    """Conciliação das linhas do extrato × movimentos da competência."""
    extrato = ExtratoImportado.objects.filter(pk=extrato_id).select_related(
        'competencia_bancaria').first()
    if extrato is None:
        messages.warning(request, 'Extrato não encontrado.')
        return redirect(reverse('admin_financeiro_conciliacao'))
    competencia = extrato.competencia_bancaria

    if request.method == 'POST':
        acao = request.POST.get('acao')
        if acao == 'sugerir':
            total = _sugerir(extrato)
            messages.success(
                request, f'{total} linha(s) conciliada(s) automaticamente '
                         '(mesma data e valor).')
        elif acao == 'conciliar':
            pks = request.POST.getlist('linhas')
            for linha in LinhaExtrato.objects.filter(pk__in=pks,
                                                     extrato=extrato):
                linha.movimento_bancario_id = request.POST.get(
                    f'movimento_{linha.pk}') or None
                linha.status = 'C'
                linha.save()
            messages.success(request, f'{len(pks)} linha(s) conciliada(s).')
        elif acao == 'ignorar':
            pks = request.POST.getlist('linhas')
            LinhaExtrato.objects.filter(pk__in=pks, extrato=extrato).update(
                status='I')
            messages.success(request, f'{len(pks)} linha(s) ignorada(s).')
        elif acao == 'lancar':
            _lancar_movimentos(request, extrato)
        elif acao == 'finalizar':
            _finalizar(request, extrato)
        elif acao == 'reabrir':
            _reabrir(request, extrato)
        return redirect(reverse('admin_financeiro_conciliacao_detalhe',
                                args=[extrato.pk]))

    conc, _ = ConciliacaoBancaria.objects.get_or_create(
        competencia_bancaria=competencia,
        defaults={'us_registro': request.user,
                  'saldo_informado': extrato.saldo_final_extrato or 0,
                  'saldo_calculado': competencia.saldo_atual or 0})
    conc.saldo_calculado = competencia.saldo_atual or 0
    conc.divergencia = (conc.saldo_calculado or 0) - (conc.saldo_informado or 0)
    conc.save(update_fields=['saldo_calculado', 'divergencia'])

    vinculados = LinhaExtrato.objects.exclude(
        movimento_bancario=None).values_list('movimento_bancario_id',
                                             flat=True)
    movimentos = MovimentoBancario.objects.filter(
        competencia_bancaria=competencia).exclude(pk__in=list(vinculados))

    return render(request, 'admin_financeiro/conciliacao_detalhe.html', {
        **admin_context(request, trail=[(str(competencia), None)]),
        'extrato': extrato,
        'competencia': competencia,
        'linhas': extrato.linhas.all(),
        'movimentos': movimentos,
        'conciliacao': conc,
        'pendentes': extrato.linhas.exclude(status__in=['C', 'I']).count(),
    })


def _sugerir(extrato):
    """Casa linha ↔ movimento por (mesma data, mesmo valor)."""
    total = 0
    usados = set(LinhaExtrato.objects.exclude(
        movimento_bancario=None).values_list('movimento_bancario_id',
                                             flat=True))
    movs = list(MovimentoBancario.objects.filter(
        competencia_bancaria=extrato.competencia_bancaria))
    for linha in extrato.linhas.filter(status='P'):
        for mov in movs:
            if mov.pk in usados:
                continue
            valor_mov = mov.valor_entrada or Decimal('0')
            if valor_mov == 0:
                valor_mov = -(mov.valor_saida or Decimal('0'))
            if (mov.dt_movimento == linha.dt_lancamento
                    and valor_mov == linha.valor):
                linha.movimento_bancario = mov
                linha.status = 'C'
                linha.save(update_fields=['movimento_bancario', 'status'])
                usados.add(mov.pk)
                total += 1
                break
    return total


def _lancar_movimentos(request, extrato):
    """Cria um movimento bancário para cada linha PENDENTE (lançamento do
    sistema a partir do extrato) e concilia a linha."""
    pendentes = extrato.linhas.filter(status='P')
    if not pendentes.exists():
        messages.warning(request, 'Não há linhas pendentes para lançar.')
        return
    competencia = extrato.competencia_bancaria
    banco = competencia.controle_bancario.conta.agencia.banco
    transacao = MovimentoBancario._meta.get_field(
        'transacao_financeira').remote_field.model.objects.filter(
        tipo='entrada', status='A').first()
    if transacao is None:
        messages.error(
            request, 'Cadastre uma Transação Financeira de ENTRADA ativa '
                     'antes de lançar os movimentos do extrato.')
        return
    criados = 0
    fora_periodo = 0
    from django.core.exceptions import ValidationError
    for linha in pendentes:
        entrada = linha.valor if linha.valor > 0 else None
        saida = -linha.valor if linha.valor < 0 else None
        mov = MovimentoBancario(
            competencia_bancaria=competencia,
            transacao_financeira=transacao,
            valor_entrada=entrada, valor_saida=saida,
            dt_movimento=linha.dt_lancamento,
            observacao=(linha.descricao or '')[:250],
            estabelecimento=competencia.estabelecimento,
            us_registro=request.user)
        try:
            mov.save()
        except ValidationError:
            # Linha com data FORA do período da competência (extrato de outro
            # mês): não é um erro do sistema — avisa quantas ficaram.
            fora_periodo += 1
            continue
        linha.movimento_bancario = mov
        linha.status = 'C'
        linha.save(update_fields=['movimento_bancario', 'status'])
        criados += 1
    if criados:
        messages.success(
            request, f'{criados} movimento(s) lançado(s) a partir do extrato '
                     f'({banco}). Saldos da competência atualizados.')
    if fora_periodo:
        messages.warning(
            request,
            f'{fora_periodo} linha(s) NÃO foram lançadas porque a DATA está '
            f'fora do período da competência "{competencia.descricao}" '
            f'(aberta em {competencia.dt_abertura_competencia:%d/%m/%Y}). '
            'Abra a competência do mês do extrato e importe-o lá.')
    if not criados and not fora_periodo:
        messages.info(request, 'Nenhuma linha pendente para lançar.')


def _finalizar(request, extrato):
    """Finaliza a conciliação — só com todas as linhas tratadas e sem
    divergência de saldo."""
    competencia = extrato.competencia_bancaria
    pendentes = extrato.linhas.exclude(status__in=['C', 'I']).count()
    if pendentes:
        messages.error(
            request,
            f'Existem {pendentes} linha(s) do extrato ainda pendente(s). '
            'Concilie ou ignore todas antes de finalizar.')
        return
    conc, _ = ConciliacaoBancaria.objects.get_or_create(
        competencia_bancaria=competencia,
        defaults={'us_registro': request.user,
                  'saldo_informado': extrato.saldo_final_extrato or 0,
                  'saldo_calculado': competencia.saldo_atual or 0})
    conc.saldo_informado = extrato.saldo_final_extrato or 0
    conc.saldo_calculado = competencia.saldo_atual or 0
    conc.divergencia = conc.saldo_calculado - conc.saldo_informado
    if abs(conc.divergencia) >= Decimal('0.01'):
        conc.finalizada = False
        conc.save()
        messages.error(
            request,
            f'Divergência de R$ {conc.divergencia} entre o sistema '
            f'(R$ {conc.saldo_calculado}) e o extrato '
            f'(R$ {conc.saldo_informado}). Lance/corrija os movimentos que '
            'faltam para bater o saldo.')
        return
    conc.finalizada = True
    conc.dt_conciliacao = timezone.now()
    conc.save()
    messages.success(
        request, 'Conciliação FINALIZADA sem divergência. A competência já '
                 'pode ser fechada.')


def _reabrir(request, extrato):
    """Reabre uma conciliação FINALIZADA para correção.

    A competência não pode estar FECHADA (o fechamento é o ponto final).
    """
    competencia = extrato.competencia_bancaria
    if competencia.dt_fechamento_competencia:
        messages.error(
            request,
            'A competência já está FECHADA em '
            f'{competencia.dt_fechamento_competencia:%d/%m/%Y}: reabra a '
            'competência (removendo a data de fechamento) antes de reabrir a '
            'conciliação.')
        return
    conc = getattr(competencia, 'conciliacao', None)
    if conc is None:
        messages.warning(request, 'Não há conciliação para reabrir.')
        return
    conc.finalizada = False
    conc.save(update_fields=['finalizada'])
    messages.success(
        request, 'Conciliação REABERTA: as linhas podem ser corrigidas e '
                 'finalizadas novamente.')


def admin_context(request, titulo='4. Conciliação Bancária', trail=None):
    """Contexto do admin + BREADCRUMB PADRÃO do app Financeiro.

    Usa o mesmo `breadcrumbs_context` dos ModelAdmins (Home > Financeiro >
    tela), com o menu de telas do módulo — a tela fica idêntica às demais.
    """
    from django.contrib.admin.sites import site
    from dominios.breadcrumbs import breadcrumbs_context

    contexto = dict(site.each_context(request))
    contexto.update(breadcrumbs_context(
        site, request, 'admin_financeiro',
        modelo_nome=titulo,
        modelo_url=reverse('admin_financeiro_conciliacao'),
        trail=list(trail or [])))
    return contexto
