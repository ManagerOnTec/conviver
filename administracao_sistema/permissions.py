"""
Restrição de acesso do módulo Administração do Sistema.

Todo o módulo (Configurações de Sessões, E-mails, Quantidade de Usuários
Simultâneos e Log de Acessos) é visível — e editável — apenas pelo usuário
``admin``. Demais usuários (inclusive superusers criados depois) não enxergam
o app no menu e recebem 403 ao tentar acessar as URLs diretamente.
"""

from django.contrib import admin

APP_LABEL = 'administracao_sistema'
USUARIO_RESTRITO = 'admin'


def usuario_com_acesso(user):
    """Retorna True apenas para o usuário 'admin' autenticado."""
    return bool(
        user and user.is_authenticated and user.is_active
        and user.username == USUARIO_RESTRITO)


class AdminSomenteUsuarioAdminMixin:
    """
    ModelAdmin restrito ao usuário 'admin'.

    Aplicar como PRIMEIRO mixin da classe:

        class XAdmin(AdminSomenteUsuarioAdminMixin, admin.ModelAdmin):
            ...
    """

    def _tem_acesso(self, request):
        return usuario_com_acesso(getattr(request, 'user', None))

    def has_view_permission(self, request, obj=None):
        return self._tem_acesso(request)

    def has_add_permission(self, request, obj=None):
        return self._tem_acesso(request)

    def has_change_permission(self, request, obj=None):
        return self._tem_acesso(request)

    def has_delete_permission(self, request, obj=None):
        return self._tem_acesso(request)

    def has_module_permission(self, request):
        return self._tem_acesso(request)


def restringir_app_no_admin_site(admin_site):
    """
    Garante que o app não apareça no index do admin para outros usuários.

    O Django já esconde apps sem módulos visíveis (``has_module_permission``),
    então aplicar o mixin nos ModelAdmins basta. Este helper existe para
    reafirmar a intenção e servir de ponto único de verdade.
    """
    return admin_site
