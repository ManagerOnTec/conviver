"""Template tag do menu de telas do módulo no breadcrumb.

Usada pelas páginas que NÃO passam por um ModelAdmin (índice do app). Nos
ModelAdmins o mesmo contexto é injetado por `dominios.breadcrumbs`.
"""
from django import template

register = template.Library()


@register.inclusion_tag('admin/includes/breadcrumbs.html', takes_context=True)
def breadcrumbs_app(context, app_label=None):
    """Renderiza o breadcrumb para o app de `app_label`.

    No índice do app (`admin/app_index.html`) o Django envia `app_list` com um
    único app e `app_label`; daí saem o nome e todas as telas visíveis.
    """
    from dominios.breadcrumbs import breadcrumbs_context
    from django.contrib import admin

    request = context.get('request')
    app_label = app_label or context.get('app_label')
    if not (request and app_label):
        return {'app_telas': []}

    # `opts` é usado só no fallback do template quando não há telas.
    return breadcrumbs_context(admin.site, request, app_label)
