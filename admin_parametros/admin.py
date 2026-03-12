from django.contrib import admin
from .models import ConfiguracaoSessao
from .forms import ConfiguracaoSessaoForm


class ConfiguracaoSessaoAdmin(admin.ModelAdmin):
    form = ConfiguracaoSessaoForm

    def has_add_permission(self, request):
        # Verificar se já existe algum registro antes de permitir adição
        return ConfiguracaoSessao.objects.count() == 0

    def has_delete_permission(self, request, obj=None):
        # Não permitir exclusão
        return False


admin.site.register(ConfiguracaoSessao, ConfiguracaoSessaoAdmin)
