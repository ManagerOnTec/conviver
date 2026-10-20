"""
Views de PRESCRIÇÃO PADRÃO (app admin_prescricoes).

- `PrescricoesPadraoDisponiveisView` (JSON): alimenta o modal de inserção no cadastro de
  prescrição. Lista apenas modelos ATIVOS do estabelecimento da sessão que estão
  liberados para o profissional logado (via `PrescricaoPadrao.pode_ser_usada_por`) E que
  possuem `ParametrosPrescricao` ativo (profissional ou profissão) — ou seja, o mesmo
  critério que já libera o cadastro de prescrição.

Remoção completa: bash .rollback/2026-10-20_prescricao_padrao/rollback.sh
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch
from django.http import JsonResponse
from django.views import View

from admin_cadastros_assistenciais.models import CadastroProfissional

from .models import ParametrosPrescricao
from .models_prescricao_padrao import PrescricaoPadrao, ProdutoPrescricaoPadrao


def _profissional_logado(user):
    return CadastroProfissional.objects.filter(
        profissional=user, status='A').select_related('profissao').first()


def _parametros_do_usuario(user, estabelecimento_id, profissional):
    """Mesmo filtro de ParametrosPrescricao usado em PrescricaoForm.clean()."""
    filtro = ParametrosPrescricao.objects.filter(
        profissional=user, estabelecimento_id=estabelecimento_id, status='A')
    if profissional and profissional.profissao_id:
        filtro = filtro | ParametrosPrescricao.objects.filter(
            profissao_id=profissional.profissao_id,
            estabelecimento_id=estabelecimento_id,
            status='A')
    return filtro


class PrescricoesPadraoDisponiveisView(LoginRequiredMixin, View):
    """JSON: prescrições padrão que o usuário logado pode inserir."""

    def get(self, request, *args, **kwargs):
        estabelecimento_id = request.session.get('estabelecimento_id')
        if not estabelecimento_id:
            return JsonResponse([], safe=False)

        profissional = _profissional_logado(request.user)

        # Sem parâmetro de prescrição o formulário de prescrição nem abre; aqui devolvemos
        # lista vazia para o modal exibir a mensagem de "nenhum modelo disponível".
        if not profissional and not request.user.is_superuser:
            return JsonResponse([], safe=False)
        if not _parametros_do_usuario(request.user, estabelecimento_id, profissional).exists() \
                and not request.user.is_superuser:
            return JsonResponse([], safe=False)

        produtos_qs = ProdutoPrescricaoPadrao.objects.filter(status='A').select_related(
            'produto', 'intervalo_horas', 'hora_inicio_produto', 'produto__unidade_medida',
            'produto__via',
        ).order_by('ordem', 'pk')

        padroes = PrescricaoPadrao.objects.filter(
            status='A', estabelecimento_id=estabelecimento_id,
        ).select_related('profissional', 'profissao').prefetch_related(
            Prefetch('produtos', queryset=produtos_qs, to_attr='produtos_ativos')
        ).order_by('descricao')

        resposta = []
        for padrao in padroes:
            if not padrao.pode_ser_usada_por(request.user, estabelecimento_id):
                continue
            itens = []
            for item in padrao.produtos_ativos:
                produto = item.produto
                itens.append({
                    'id': item.pk,
                    'produto_id': produto.pk,
                    'produto': produto.descricao,
                    'unidade': produto.unidade_medida.unidade_medida if produto.unidade_medida_id else '',
                    'via': produto.via.descricao if produto.via_id else '',
                    'intervalo_horas_id': item.intervalo_horas_id,
                    'intervalo_horas': str(item.intervalo_horas),
                    'hora_inicio_produto_id': item.hora_inicio_produto_id,
                    'hora_inicio_produto': str(item.hora_inicio_produto),
                    'se_necessario': item.se_necessario,
                    'dose_unica': item.dose_unica,
                    'observacao': item.observacao or '',
                })
            resposta.append({
                'id': padrao.pk,
                'descricao': padrao.descricao,
                'observacao': padrao.observacao or '',
                'liberacao': padrao.liberacao_resumida,
                'total_itens': len(itens),
                'itens': itens,
            })

        return JsonResponse(resposta, safe=False)
