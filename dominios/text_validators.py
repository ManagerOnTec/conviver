import html
import re

from django.core.exceptions import ValidationError
from django.utils.html import strip_tags


MAX_RICH_TEXT_LENGTH = 20000


def rich_text_to_plain_text(value):
    if value in (None, ''):
        return ''

    texto = html.unescape(str(value))
    texto = texto.replace('&nbsp;', ' ').replace('\xa0', ' ')
    texto = strip_tags(texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()


def validate_rich_text_length(value, *, limit=MAX_RICH_TEXT_LENGTH, field_label='texto'):
    texto_limpo = rich_text_to_plain_text(value)
    tamanho = len(texto_limpo)

    if tamanho > limit:
        raise ValidationError(
            f'O {field_label} excedeu o limite de {limit} caracteres de texto puro. Atual: {tamanho}.'
        )


def validate_evolucao_like_text(value):
    validate_rich_text_length(value, limit=MAX_RICH_TEXT_LENGTH, field_label='texto')