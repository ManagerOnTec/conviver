from django.contrib import admin
from django.utils import timezone

from admin_cadastros.utils import EstabelecimentoFilterAdminMixin
from dominios.utils import (
    AdminEstabelecimentoPadraoMixin,
    ExportToXLSMixin,
    StatusFilterAdminMixin,
)

from .forms import AgendaPacienteForm, TipoAgendamentoForm
from .models import (
    AgendaPaciente,
    ParametrosAgenda,
    TipoAgendamento,
)

# Setor e Local são cadastros de `admin_cadastros` (“10. Setores” / “11. Locais”).


class BaseAgendaAdmin(ExportToXLSMixin, admin.ModelAdmin):
    """Auditoria comum dos cadastros da agenda."""

    actions = ('export_as_xls',)
    readonly_fields = (
        'dt_registro', 'us_registro', 'dt_atualizacao', 'us_atualizacao',
    )

    def save_model(self, request, obj, form, change):
        if change:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()
        else:
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(TipoAgendamento)
class TipoAgendamentoAdmin(BaseAgendaAdmin):
    """Tipos de agendamento (exame, visita, dentista, perícia...)."""

    form = TipoAgendamentoForm
    list_display = (
        'id', 'descricao', 'externo', 'exige_exame_solicitado',
        'local', 'status', 'dt_registro', 'us_registro',
    )
    list_display_links = ('id', 'descricao')
    list_filter = (StatusFilterAdminMixin,)
    search_fields = ('descricao',)
    autocomplete_fields = ('local',)
    list_editable = ('externo', 'exige_exame_solicitado', 'status')

    def get_changelist(self, request, **kwargs):
        from admin_faturas.changelist_editavel import ChangeListEditavel
        return ChangeListEditavel

    def get_linhas_nao_editaveis(self, request):
        return set()


@admin.register(AgendaPaciente)
class AgendaPacienteAdmin(AdminEstabelecimentoPadraoMixin, BaseAgendaAdmin):
    """Agendamentos dos pacientes, por data."""

    form = AgendaPacienteForm
    date_hierarchy = 'data_hora'
    ordering = ('data_hora', 'pk')
    list_display = (
        'id', 'atendimento', 'tipo', 'exame', 'data_hora', 'local',
        'responsavel', 'efetuado', 'status', 'estabelecimento',
    )
    list_display_links = ('id', 'atendimento')
    list_filter = (
        EstabelecimentoFilterAdminMixin,
        StatusFilterAdminMixin,
        'tipo',
        'efetuado',
    )
    search_fields = (
        'id', 'atendimento__pessoa__nome', 'atendimento__pessoa__cpf',
        'local__nome', 'atendimento__id', 'tipo__descricao',
        'exame__tipo_exame__descricao',
    )

    def get_queryset(self, request):
        # Instrução do módulo: não expor registros inativos por padrão.
        queryset = super().get_queryset(request)
        if not request.GET:
            queryset = queryset.filter(status='A')
        return queryset

    autocomplete_fields = ('atendimento', 'local', 'responsavel', 'exame')
    readonly_fields = (
        'dt_registro', 'us_registro', 'dt_atualizacao', 'us_atualizacao',
        'dt_efetuado',
    )
    fieldsets = (
        ('Agendamento', {
            'fields': (
                'atendimento', 'tipo', 'exame', 'data_hora',
                'local', 'responsavel',
            ),
        }),
        ('Contato / acesso', {
            'fields': ('link_videochamada', 'link_whatsapp', 'observacao'),
        }),
        ('Execução', {
            'fields': ('efetuado', 'dt_efetuado', 'data_execucao',
                       'observacao_execucao'),
        }),
        ('Controle', {
            'fields': (
                'estabelecimento', 'status',
                'dt_registro', 'us_registro', 'dt_atualizacao',
                'us_atualizacao',
            ),
        }),
    )


@admin.register(ParametrosAgenda)
class ParametrosAgendaAdmin(AdminEstabelecimentoPadraoMixin, BaseAgendaAdmin):
    """admin_parametros_agendapaciente: quem vê, edita e exclui a agenda."""

    filter_horizontal = (
        'usuarios_visualizacao', 'usuarios_edicao', 'usuarios_exclusao',
        'grupos_visualizacao', 'grupos_edicao', 'grupos_exclusao',
    )
    list_display = ('id', 'estabelecimento', 'status', 'dt_registro', 'us_registro')
    list_display_links = ('id', 'estabelecimento')
    list_filter = (EstabelecimentoFilterAdminMixin, StatusFilterAdminMixin)
    search_fields = ('estabelecimento__nome_fantasia',)
    fieldsets = (
        ('Permissões da agenda', {
            'fields': (
                'estabelecimento',
                ('usuarios_visualizacao', 'grupos_visualizacao'),
                ('usuarios_edicao', 'grupos_edicao'),
                ('usuarios_exclusao', 'grupos_exclusao'),
            ),
            'description': (
                'Libera por usuário OU por grupo: basta estar em um dos dois '
                'para ter o acesso.'
            ),
        }),
        ('Controle', {
            'fields': (
                'status', 'dt_registro', 'us_registro',
                'dt_atualizacao', 'us_atualizacao',
            ),
        }),
    )
