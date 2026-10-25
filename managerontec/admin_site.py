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
