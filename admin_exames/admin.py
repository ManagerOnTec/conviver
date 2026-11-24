from django.contrib import admin
from django.utils import timezone
from dominios.utils import ExportToXLSMixin, StatusFilterAdminMixin
from .forms import ParametrosExamesForm, TipoExameForm
from .models import ParametrosExames, TipoExame
@admin.register(TipoExame)
class TipoExameAdmin(ExportToXLSMixin, admin.ModelAdmin):
    form = TipoExameForm
    actions = ['export_as_xls']
    list_display = ('id', 'descricao', 'cor', 'iniciais_nome', 'status', 'dt_registro', 'us_registro', 'dt_atualizacao', 'us_atualizacao')
    list_display_links = ('id', 'descricao')
    list_filter = (StatusFilterAdminMixin,)
    search_fields = ('descricao',)
    readonly_fields = ('dt_registro', 'us_registro', 'dt_atualizacao', 'us_atualizacao')
    list_editable = ('status',)

    def save_model(self, request, obj, form, change):
        if change:
            obj.us_atualizacao, obj.dt_atualizacao = request.user, timezone.now()
        else:
            obj.us_registro, obj.dt_registro = request.user, timezone.now()
        super().save_model(request, obj, form, change)

@admin.register(ParametrosExames)
class ParametrosExamesAdmin(ExportToXLSMixin, admin.ModelAdmin):
    form = ParametrosExamesForm
    actions = ['export_as_xls']
    filter_horizontal = ('tipos_exame',)
    list_display = ('id', 'profissional', 'profissao', 'estabelecimento', 'tipo_exame_padrao', 'status', 'dt_registro', 'us_registro')
    list_display_links = ('id', 'profissional', 'profissao')
    list_filter = (StatusFilterAdminMixin, 'estabelecimento')
    search_fields = ('id', 'profissional__username', 'profissao__profissao', 'estabelecimento__estabelecimento')
    readonly_fields = ('dt_registro', 'us_registro', 'dt_atualizacao', 'us_atualizacao')
    list_editable = ('status',)

    def save_model(self, request, obj, form, change):
        if change:
            obj.us_atualizacao, obj.dt_atualizacao = request.user, timezone.now()
        else:
            obj.us_registro, obj.dt_registro = request.user, timezone.now()
        super().save_model(request, obj, form, change)
