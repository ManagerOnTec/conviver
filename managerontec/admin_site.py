"""
Admin site do projeto.

O sistema tem UMA única tela de autenticação (``contas.views.login``, rota
``/login/``), que já direciona o usuário ``admin`` para ``/admin``. Por isso o
formulário nativo de login do Django Admin não deve existir:

- ``/admin/`` (sem sessão) -> redireciona para ``/login/``;
- ``/admin/login/``  -> redireciona para ``/login/`` (preservando ``?next=``);
- ``/admin/logout/`` -> usa a view ``contas.views.logout`` (encerra a sessão e
  volta para ``/login/`` com a mensagem "Usuário Deslogado!").

Não criamos um ``AdminSite`` novo: apenas reaproveitamos as rotas do site
padrão (``get_urls``) trocando essas três. Assim, todos os
``@admin.register`` / ``admin.site.register`` dos apps continuam valendo.
"""

from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path


def admin_login(request, extra_context=None):
    """Tela de login do admin: redireciona para a tela única do sistema."""
    user = request.user

    # Já autenticado com acesso ao admin: deixa o AdminSite seguir o fluxo
    # normal (ex.: renderizar o índice / redirecionar para ``next``).
    if user.is_authenticated and user.is_active and user.is_staff:
        return admin.site.login(request, extra_context)

    next_url = request.GET.get('next') or ''
    if next_url:
        return redirect(f'/login/?next={next_url}')
    return redirect('login')


def admin_logout(request, extra_context=None):
    """
    Logout do admin: encerra a sessão com a view do projeto
    (``contas.views.logout``) e volta para a tela de login do sistema.

    Chamamos a view diretamente em vez de redirecionar, porque um redirect
    não encerra a sessão.
    """
    from contas.views import logout as logout_view
    return logout_view(request)


def _get_app_list_com_extras(request, app_label=None):
    """`AdminSite.get_app_list` + as páginas próprias (Conciliação etc.)."""
    return _com_telas_extras(
        admin.site.get_app_list(request, app_label))


def _com_telas_extras(app_list):
    """Acrescenta ao menu as páginas PRÓPRIAS (que não são ModelAdmin).

    Hoje: "4. Conciliação Bancária" no app do Financeiro — a tela dedicada
    de importação/conciliação de extrato. Mantém a ordenação por número.
    """
    from django.urls import NoReverseMatch, reverse

    def _numero(nome):
        prefixo = nome.strip().split(' ')[0].rstrip('.')
        return int(prefixo) if prefixo.isdigit() else None

    paginas = [('admin_financeiro', '4. Conciliação Bancária',
                'admin_financeiro_conciliacao')]
    extras = {}
    for app_label, nome, rota in paginas:
        try:
            url = reverse(rota)
        except NoReverseMatch:
            continue
        extras.setdefault(app_label, []).append({
            'name': nome,
            'object_name': 'conciliacao_bancaria',
            'admin_url': url,
            'add_url': None,
            'view_only': True,
            'numero': _numero(nome),
        })
    if not extras:
        return app_list
    for app in app_list:
        novas = extras.get(app.get('app_label'))
        if not novas:
            continue
        # IDEMPOTENTE: não duplica um item já presente (mesma URL).
        existentes = {(m.get('admin_url') or '') for m in app.get('models', [])}
        acrescentar = [m for m in novas
                       if (m.get('admin_url') or '') not in existentes]
        if not acrescentar:
            continue
        app['models'] = list(app.get('models', [])) + acrescentar
        app['models'].sort(key=lambda m: (
            _numero(m.get('name', '')) is None,
            _numero(m.get('name', '')) or 0,
            (m.get('name') or '').lower()))
    return app_list


def admin_index(request, extra_context=None):
    """
    Índice do admin.

    Sem permissão, o AdminSite padrão redireciona para ``admin:login`` via
    ``catch_all_view``; aqui enviamos direto para a tela única do sistema.
    """
    if not admin.site.has_permission(request):
        return admin_login(request)
    return admin.site.index(request, extra_context)


def get_admin_urls():
    """
    Mesmas rotas do admin padrão, mas com ``/admin/``, ``/admin/login/`` e
    ``/admin/logout/`` apontando para a tela única do sistema.

    Mantém o namespace ``admin`` e todos os registros de models intactos.
    """
    # Aqui os admins de TODOS os apps já foram registrados (o autodiscover
    # acontece quando o admin é carregado), então o breadcrumb de "telas do
    # módulo" pode ser aplicado a cada ModelAdmin de uma vez. Idempotente.
    from dominios.breadcrumbs import instalar_breadcrumbs
    instalar_breadcrumbs(admin.site)

    # O ÍNDICE do admin (e o menu de "telas do módulo" do breadcrumb) passa a
    # listar as páginas PRÓPRIAS — a Conciliação Bancária (item 4 do
    # Financeiro) não é ModelAdmin, então não viria do `get_app_list` padrão.
    # Aplicado UMA única vez (o `get_admin_urls` pode ser chamado várias vezes
    # pelo URL resolver): envolver duas vezes duplicava o item do menu.
    site_atual = admin.site
    if not getattr(site_atual, '_telas_extras_aplicadas', False):
        _get_app_list_original = site_atual.get_app_list

        def _get_app_list(self, request, app_label=None):
            return _com_telas_extras(
                _get_app_list_original(request, app_label))

        site_atual.get_app_list = _get_app_list.__get__(
            site_atual, type(site_atual))
        site_atual._telas_extras_aplicadas = True

    urlpatterns = []

    for pattern in admin.site.get_urls():
        name = getattr(pattern, 'name', None)
        if name == 'index':
            urlpatterns.append(path('', admin_index, name='index'))
        elif name == 'login':
            urlpatterns.append(path('login/', admin_login, name='login'))
        elif name == 'logout':
            urlpatterns.append(path('logout/', admin_logout, name='logout'))
        elif name == 'password_change':
            urlpatterns.append(
                path('password_change/', redirect_alterar, name='password_change'))
        else:
            urlpatterns.append(pattern)

    return urlpatterns


def redirect_alterar(request, extra_context=None):
    """A troca de senha do sistema é a view própria (contas.views.alterar)."""
    return redirect('alterar')
