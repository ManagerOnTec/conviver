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
    list_display = ('nome_modelo', 'tipo_documento', 'estabelecimento', 'status')
    search_fields = ('nome_modelo', 'titulo_documento', 'conteudo_html')
    list_filter = (StatusFilterAdminMixin, 'tipo_documento', 'estabelecimento')
    autocomplete_fields = ('tipo_documento', 'estabelecimento')


@admin.register(DocumentoLegalInternacao)
class DocumentoLegalInternacaoAdmin(admin.ModelAdmin):
    list_display = ('codigo_documento', 'titulo_documento', 'tipo_documento', 'atendimento', 'responsavel_nome', 'dt_assinatura', 'status')
    search_fields = ('codigo_documento', 'titulo_documento', 'responsavel_nome', 'responsavel_cpf', 'atendimento__pessoa__nome')
    list_filter = (StatusFilterAdminMixin, 'tipo_documento', 'estabelecimento', 'dt_assinatura')
    readonly_fields = ('codigo_documento', 'conteudo_html', 'hash_pdf', 'dt_registro', 'dt_atualizacao', 'us_registro', 'us_atualizacao')
    autocomplete_fields = ('tipo_documento', 'modelo_documento')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()
        super().save_model(request, obj, form, change)
