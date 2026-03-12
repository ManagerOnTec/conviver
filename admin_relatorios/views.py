from django.views import View
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
# Substitua pelo caminho correto do seu modelo
from .models import TextoDocumentoPadrao


class TextoPadraoFiltradoPorTipoView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            # Obtém o tipo do documento a partir dos parâmetros da URL
            # Ex: 'atas', 'oficios', 'orcamentos'
            tipo_documento = kwargs.get('tipo_documento')

            # Filtra os TextoDocumentoPadrao pelo tipo e status ativo
            textos_padrao = TextoDocumentoPadrao.objects.filter(
                tipo=tipo_documento, status='A'
            ).values(
                'id', 'descricao', 'texto', 'tipo'
            )

            # Converte o QuerySet em uma lista de dicionários
            response_data = list(textos_padrao)

            # Retorna os dados em formato JSON
            return JsonResponse(response_data, safe=False)

        except ObjectDoesNotExist as e:
            print(f"Erro ao obter query: {e}")
            return JsonResponse([], safe=False)
