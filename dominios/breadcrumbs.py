"""Breadcrumbs do admin: o botão do app abre o menu das telas do módulo.

O item do app no breadcrumb mantém o visual de botão; ao clicar (ou usar o
teclado), abre um painel com TODOS os modelos do módulo que o usuário pode
acessar, sem sair da tela atual.

Aplicação global
----------------
`instalar_breadcrumbs()` embrulha os métodos de contexto de TODOS os
ModelAdmin registrados — inclusive os que não usam mixin nenhum. Nenhum admin
precisa ser alterado: basta importar este módulo no startup (ver
`managerontec/admin_site.py`).
"""
from django.contrib import admin
from django.template.defaultfilters import capfirst


def _numero_ordem(nome):
    """Extrai o prefixo numérico de verbose_name_plural ("2. Pré-Faturas").

    O admin ordena pelo nome traduzido, então "1. ..." e "10. ..." ficam
    intercalados em ordem alfabética. Devolve None quando não há número.
    """
    prefixo = nome.strip().split(' ')[0].rstrip('.')
    return int(prefixo) if prefixo.isdigit() else None


def telas_do_app(admin_site, request, app_label):
    """Telas visiveis do app, como dicts prontos para o template.

    Fonte: `admin_site.get_app_list(request)` -- a MESMA lista do indice do
    admin, ja filtrada por has_module_permission/has_view_permission, entao
    nunca oferece uma tela que o usuario nao poderia abrir. O parametro
    `app_label` de get_app_list so filtra quando ha `model_name`; por isso a
    lista completa e recortada aqui.
    """
    app_atual = next(
        (a for a in admin_site.get_app_list(request)
         if a.get('app_label') == app_label), None)
    if not app_atual:
        return []

    # As páginas PRÓPRIAS (ex.: Conciliação Bancária) já vêm no `models` do
    # app: o `admin.site.get_app_list` é envolvido em `managerontec/
    # admin_site.py` para acrescentá-las. Somar aqui de novo DUPLICAVA o item
    # no menu.
    telas = [
        {'nome': m['name'], 'url': m['admin_url'],
         'numero': _numero_ordem(m['name'])}
        for m in app_atual.get('models', []) if m.get('admin_url')
    ]
    # Dedupe defensivo (mesma URL só uma vez), caso alguma fonte repita.
    vistos = set()
    unicas = []
    for tela in telas:
        if tela['url'] in vistos:
            continue
        vistos.add(tela['url'])
        unicas.append(tela)
    unicas.sort(key=lambda t: (t['numero'] is None, t['numero'] or 0,
                               t['nome'].lower()))
    return unicas


def _telas_extras(request):
    """{app_label: [{nome, url, numero}]} das páginas próprias."""
    from django.urls import NoReverseMatch, reverse
    extras = {}
    paginas = [
        ('admin_financeiro', '4. Conciliação Bancária',
         'admin_financeiro_conciliacao'),
    ]
    for app_label, nome, rota in paginas:
        try:
            url = reverse(rota)
        except NoReverseMatch:
            continue
        extras.setdefault(app_label, []).append({
            'nome': nome, 'url': url, 'numero': _numero_ordem(nome)})
    return extras


def breadcrumbs_context(admin_site, request, app_label, modelo_nome='',
                        modelo_url='', trail=None):
    """Contexto do include `admin/includes/breadcrumbs.html`."""
    apps = admin_site.get_app_list(request)
    app = next((a for a in apps if a.get('app_label') == app_label), None)
    if app is None:
        app = {'name': '', 'app_url': ''}
    # Nome do app: o verbose do índice do admin; sem ele, o app_label legível.
    app_nome = app.get('name') or capfirst(app_label.replace(u'_', u' '))
    return {
        'app_telas': telas_do_app(admin_site, request, app_label),
        'app_nome': app_nome,
        'app_url': app.get('app_url', ''),
        'app_telas_indice_url': app.get('app_url', ''),
        'app_modelo_atual': modelo_nome or '',
        'app_modelo_url': modelo_url or '',
        'app_trail': trail or [],
    }


def breadcrumbs_from_opts(admin_site, request, opts, modelo_nome=None,
                          modelo_url=None, trail=None):
    """Atalho para changelist e formulários de alteração/cadastro."""
    from django.urls import NoReverseMatch, reverse
    nome = modelo_nome or opts.verbose_name_plural
    if modelo_url is None:
        try:
            modelo_url = reverse(
                f"{admin_site.name}:{opts.app_label}_{opts.model_name}_changelist")
        except NoReverseMatch:
            modelo_url = ''

    # O breadcrumb para no MODELO em TODAS as telas: nem "Adicionar", nem o
    # texto do objeto (ex.: nome da pessoa), nem "Histórico" no caminho. O
    # `trail` continua aceito para breadcrumbs extras de customizações.
    return breadcrumbs_context(admin_site, request, opts.app_label,
                               modelo_nome=nome, modelo_url=modelo_url,
                               trail=list(trail or []))


def _url_changelist(admin_site, opts):
    from django.urls import NoReverseMatch, reverse
    try:
        return reverse(f"{admin_site.name}:{opts.app_label}_"
                       f"{opts.model_name}_changelist")
    except NoReverseMatch:
        return ''


def _contexto_changelist(self, request):
    return breadcrumbs_from_opts(
        self.admin_site, request, self.opts,
        modelo_url=_url_changelist(self.admin_site, self.opts))


def _contexto_form(self, request):
    # Formulário (alterar/cadastrar): o caminho termina no modelo.
    return breadcrumbs_from_opts(
        self.admin_site, request, self.opts,
        modelo_url=_url_changelist(self.admin_site, self.opts))


def instalar_breadcrumbs(admin_site=admin.site):
    """Injeta o contexto do breadcrumb em TODOS os ModelAdmin registrados."""
    for model_admin in admin_site._registry.values():
        cls = type(model_admin)
        if getattr(cls, '_breadcrumbs_global', False):
            continue

        original_changelist = cls.changelist_view
        original_form = cls.render_change_form
        original_add = cls.add_view
        original_delete = cls.delete_view
        original_change = cls.change_view

        def changelist_view(self, request, extra_context=None,
                            _original=original_changelist):
            extra = dict(extra_context or {})
            extra.update(_contexto_changelist(self, request))
            return _original(self, request, extra_context=extra)

        def render_change_form(self, request, context, *args,
                               _original=original_form, **kwargs):
            # O breadcrumb termina no modelo (sem o nome do objeto).
            contexto = _contexto_form(self, request)
            context.update(contexto)
            return _original(self, request, context, *args, **kwargs)

        def add_view(self, request, form_url='', extra_context=None,
                     _original=original_add):
            extra = dict(extra_context or {})
            extra.update(_contexto_form(self, request))
            return _original(self, request, form_url, extra_context=extra)

        def delete_view(self, request, object_id, extra_context=None,
                        _original=original_delete):
            extra = dict(extra_context or {})
            extra.update(_contexto_form(self, request))
            return _original(self, request, object_id, extra_context=extra)

        def change_view(self, request, object_id, form_url='',
                        extra_context=None, _original=original_change):
            # O `render_change_form` já injeta; aqui só garantimos o dicionário.
            extra = dict(extra_context or {})
            return _original(self, request, object_id, form_url,
                             extra_context=extra)

        cls.changelist_view = changelist_view
        cls.render_change_form = render_change_form
        cls.add_view = add_view
        cls.delete_view = delete_view
        cls.change_view = change_view
        cls._breadcrumbs_global = True

