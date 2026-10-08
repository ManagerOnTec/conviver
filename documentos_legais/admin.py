from django.contrib import admin
from django.utils import timezone

from dominios.utils import AdminEstabelecimentoPadraoMixin, AdminSaveModelAuditMixin, StatusFilterAdminMixin
from .forms import ModeloDocumentoLegalAdminForm, TipoDocumentoLegalAdminForm
from .models import DocumentoLegalInternacao, ModeloDocumentoLegal, TipoDocumentoLegal


@admin.register(TipoDocumentoLegal)
class TipoDocumentoLegalAdmin(AdminSaveModelAuditMixin, admin.ModelAdmin):
    form = TipoDocumentoLegalAdminForm
    list_display = ('nome', 'slug', 'ordem', 'padrao_sistema', 'status')
    list_editable = ('ordem', 'status')
    search_fields = ('nome', 'slug')
    list_filter = (StatusFilterAdminMixin, 'padrao_sistema')
    ordering = ('ordem', 'nome')


@admin.register(ModeloDocumentoLegal)
class ModeloDocumentoLegalAdmin(AdminEstabelecimentoPadraoMixin, AdminSaveModelAuditMixin, admin.ModelAdmin):
    form = ModeloDocumentoLegalAdminForm
    list_display = ('nome_modelo', 'tipo_documento', 'estabelecimento', 'exige_assinatura_responsavel', 'exige_assinatura_atendente', 'status')
    list_filter = (StatusFilterAdminMixin, 'tipo_documento', 'estabelecimento', 'exige_assinatura_responsavel', 'exige_assinatura_atendente')
    search_fields = ('nome_modelo', 'titulo_documento', 'conteudo_html')
    autocomplete_fields = ('tipo_documento', 'estabelecimento')

