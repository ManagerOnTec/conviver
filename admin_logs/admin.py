from django.contrib import admin
from . models import ProntuarioAcessos
from dominios.utils import ExportToXLSMixin

class ProntuarioAcessosAdmin(ExportToXLSMixin, admin.ModelAdmin):
    model = ProntuarioAcessos

    actions = ['export_as_xls']
    
    list_display = ('id', 'atendimento_id', 'atendimento', 'us_acesso',
                    'dt_acesso', 'item_prontuario', 'motivo_acesso',)
    list_filter = ('us_acesso', 'dt_acesso',)
    list_display_links = ('id', 'atendimento_id', 'atendimento', )
    search_fields = ['id', 'atendimento__id', 'atendimento__pessoa__nome',
                     'us_acesso__username', 'motivo_acesso', ]
    readonly_fields = ['us_acesso', 'dt_acesso', 'motivo_acesso',]
    ordering = ['-pk']
    list_per_page = 11

    def has_add_permission(self, request):
        return False  # Remove a permissão de adicionar registros

    def has_change_permission(self, request, obj=None):
        return False  # Remove a permissão de editar registros

    def has_delete_permission(self, request, obj=None):
        return False  # Remove a permissão de excluir registros


admin.site.register(ProntuarioAcessos, ProntuarioAcessosAdmin)
