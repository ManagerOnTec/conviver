from django.views import View
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from .models import TextoDocumentoPadrao


class TextoPadraoFiltradoPorTipoView(LoginRequiredMixin, View):
    """
    Retorna os textos padronizados de admin_relatorios.TextoDocumentoPadrao
    filtrados pelo tipo de documento (atas, oficios, orcamentos).
    Aceita singular/plural e retorna JSON consumivel pelo modal do front.
    """

    MAPA_TIPOS = {
        'ata': 'atas', 'atas': 'atas',
        'oficio': 'oficios', 'oficios': 'oficios',
        'orcamento': 'orcamentos', 'orcamentos': 'orcamentos',
        'documento': 'atas', 'documentos': 'atas',
    }

    def get(self, request, *args, **kwargs):
        try:
            tipo_raw = (kwargs.get('tipo_documento') or '').strip().lower()
            tipo_normalizado = self.MAPA_TIPOS.get(tipo_raw, tipo_raw)

            # Monta o conjunto de tipos aceitos (singular + plural + variacoes de caixa)
            variacoes = {tipo_raw, tipo_normalizado, tipo_raw.capitalize(), tipo_normalizado.capitalize()}
            variacoes.discard('')

            queryset = TextoDocumentoPadrao.objects.filter(status='A')

            if variacoes:
                filtro = Q()
                for v in variacoes:
                    filtro |= Q(tipo__iexact=v)
                queryset = queryset.filter(filtro)

            textos_padrao = queryset.values(
                'id', 'descricao', 'texto', 'tipo'
            ).order_by('descricao')

            response_data = list(textos_padrao)
            return JsonResponse(response_data, safe=False)

        except Exception as e:
            print(f"Erro ao obter textos padrao por tipo: {e}")
            return JsonResponse([], safe=False)
