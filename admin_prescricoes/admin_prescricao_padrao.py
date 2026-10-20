"""
Admin de PRESCRIÇÃO PADRÃO (modelos PrescricaoPadrao/ProdutoPrescricaoPadrao).

Importado no final de admin_prescricoes/admin.py para manter a lógica de prescrição
padrão isolada da administração já existente.

Edição: o cabeçalho (descricao, liberação, estabelecimento) é editado no form do
`PrescricaoPadraoAdmin` e os itens (produto, intervalo, horário, flags) são editados
como inline (`ProdutoPrescricaoPadraoInline`).
"""
from django.contrib import admin
from django.forms.models import BaseInlineFormSet
from django.forms.formsets import ValidationError as FormsetValidationError
from django.utils import timezone

from dominios.utils import StatusFilterAdminMixin

from .forms_prescricao_padrao import (
    PrescricaoPadraoForm,
    ProdutoPrescricaoPadraoForm,
)
from .models_prescricao_padrao import (
    PrescricaoPadrao,
    PrescricaoPadraoUtilizacao,
    ProdutoPrescricaoPadrao,
)


class ProdutoPrescricaoPadraoInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        # Garante pelo menos um item ATIVO no modelo (sem produtos o modal não insere nada).
        ativos = 0
        for form in self.forms:
            if not hasattr(form, 'cleaned_data') or not form.cleaned_data:
                continue
            if form.cleaned_data.get('DELETE'):
                continue
            if form.cleaned_data.get('produto'):
                ativos += 1
        if self.instance.pk and ativos == 0 and not any(
                f.cleaned_data.get('DELETE') for f in self.forms
                if hasattr(f, 'cleaned_data') and f.cleaned_data):
            raise FormsetValidationError(
                'A prescrição padrão precisa ter pelo menos um item informado.')


class ProdutoPrescricaoPadraoInline(admin.TabularInline):
    model = ProdutoPrescricaoPadrao
    form = ProdutoPrescricaoPadraoForm
    formset = ProdutoPrescricaoPadraoInlineFormSet
    # Sem linha vazia: os itens são adicionados por
    # "Adicionar outro(a) Produto da Prescrição Padrão" (JS do Django cria a linha).
    extra = 0
    # Prefixo próprio: o padrão do Django seria "produtos", o mesmo do
    # related_name `Prescricao.produtos`, o que confundia o formset/JS.
    verbose_name_plural = 'Produtos da Prescrição Padrão'
    fields = ('produto', 'intervalo_horas', 'hora_inicio_produto',
              'se_necessario', 'dose_unica', 'observacao', 'ordem', 'status')
    # Select2 de digitação também no inline do modelo.
    autocomplete_fields = ('produto', 'intervalo_horas', 'hora_inicio_produto')

    def get_formset(self, request, obj=None, **kwargs):
        # A prescrição padrão vem do objeto pai no inline: o campo é ocultado.
        kwargs['form'] = type(self.form.__name__, (self.form,), {
            'inline_parent': True,
        })
        return super().get_formset(request, obj, **kwargs)


@admin.register(PrescricaoPadrao)
class PrescricaoPadraoAdmin(admin.ModelAdmin):
    form = PrescricaoPadraoForm

    class Media:
        js = ('js/admin_select2_largura.js',)

    # Select2 de digitação para liberação e estabelecimento.
    autocomplete_fields = ('profissional', 'profissao', 'estabelecimento')
    list_display = ('id', 'descricao', 'liberacao_display', 'estabelecimento',
                    'total_itens_display', 'status', 'dt_registro', 'us_registro')
    list_display_links = ('id', 'descricao')
    list_filter = (StatusFilterAdminMixin, 'estabelecimento',
                   'profissao', 'profissional')
    search_fields = ('id', 'descricao')
    readonly_fields = ('us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao')
    list_editable = ('status',)
    inlines = (ProdutoPrescricaoPadraoInline,)
    ordering = ('-pk',)
    list_per_page = 11

    @admin.display(description='Liberação')
    def liberacao_display(self, obj):
        return obj.liberacao_resumida

    @admin.display(description='Itens ativos')
    def total_itens_display(self, obj):
        return obj.produtos.filter(status='A').count()

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if 'HTTP_REFERER' in request.META:
            referer_path = request.META['HTTP_REFERER'].split(
                request.META['HTTP_HOST'])[-1]
            if '/add/' in referer_path or '/change/' in referer_path:
                queryset = queryset.filter(status='A')
        return queryset, use_distinct

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        for instance in instances:
            if not change or not instance.pk:
                instance.us_registro = request.user
                instance.dt_registro = timezone.now()
            else:
                instance.us_atualizacao = request.user
                instance.dt_atualizacao = timezone.now()
            instance.save()
        formset.save_m2m()
