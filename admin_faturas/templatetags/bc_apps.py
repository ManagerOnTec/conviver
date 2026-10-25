"""Template tag do menu de telas do módulo no breadcrumb.

Usada pelas páginas que NÃO passam por um ModelAdmin (índice do app, formato
com `app_list`). Nos ModelAdmins o mesmo contexto é injetado por
`dominios.breadcrumbs.instalar_breadcrumbs`.
"""
from django import template
from django.contrib import admin

register = template.Library()


@register.inclusion_tag('admin/includes/breadcrumbs.html', takes_context=True)
def breadcrumbs_app(context, app_label=None):
    """Renderiza o breadcrumb do app de `app_label`.

    No índice do app, o Django envia `app_list` com um único app; o helper
    monta o mesmo contexto usado pelos ModelAdmin (telas visíveis do módulo).
    """
    from dominios.breadcrumbs import breadcrumbs_context

    request = context.get('request')
    app_label = app_label or context.get('app_label')
    if not (request and app_label):
        return {}

    dados = breadcrumbs_context(admin.site, request, app_label)
    # No índice do módulo não há modelo "atual": a lista abre na primeira tela.
    if dados.get('app_telas') and not dados.get('app_modelo_atual'):
        dados['app_modelo_atual'] = dados['app_telas'][0]['nome']
    return dados
