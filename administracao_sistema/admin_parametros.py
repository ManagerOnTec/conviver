from django.contrib import admin
from .models_parametros import ConfiguracaoSessao
from .permissions import AdminSomenteUsuarioAdminMixin


class ConfiguracaoSessaoAdmin(AdminSomenteUsuarioAdminMixin, admin.ModelAdmin):
    # O antigo `ConfiguracaoSessaoForm` nunca existiu no projeto (o import
    # quebrava o carregamento do app). Usamos o ModelForm gerado pelo Django.

    def has_add_permission(self, request):
        # Verificar se já existe algum registro antes de permitir adição
        return ConfiguracaoSessao.objects.count() == 0

    def has_delete_permission(self, request, obj=None):
        # Não permitir exclusão
        return False


admin.site.register(ConfiguracaoSessao, ConfiguracaoSessaoAdmin)
