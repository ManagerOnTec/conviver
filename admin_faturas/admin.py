from django.forms import DateInput
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path
from django.shortcuts import redirect, get_object_or_404
from django.utils.html import format_html
from django.urls import reverse
from contas.models import Perfil
from .models import Convenio, PreFatura, Fatura, BaixaFatura
from .forms import BaixaFaturaForm, ConvenioForm, FaturaForm, PreFaturaForm
from django.contrib import messages
from django.utils import timezone
from dominios.utils import ExportToXLSMixin, AdminEstabelecimentoPadraoMixin, PreFaturadoFilterAdminMixin, StatusFilterAdminMixin, FaturadoFilterAdminMixin
from datetime import timedelta, date
import calendar
from decimal import Decimal
from django.db import models
from admin_cadastros.utils import EstabelecimentoFilterAdminMixin
from admin_cadastros_financeiros.models import TransacaoFinanceira
from admin_financeiro.models import CompetenciaBancaria
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django import forms
from django.utils.html import format_html
from django.urls import reverse
from datetime import datetime
from django.contrib import admin
from .models import Convenio, PreFatura, Fatura, BaixaFatura



class DateInput(forms.DateInput):
    input_type = 'date'
    format = '%d/%m/%Y'  # Define o formato de entrada de data


class CustomDateFilter(admin.SimpleListFilter):
    title = _('Competência')
    parameter_name = 'competencia'

    def lookups(self, request, model_admin):
        # Obtém todas as competências únicas do modelo PreFatura com status 'A'
        competencias = PreFatura.objects.filter(
            status='A'  # Adiciona o filtro para status 'A'
        ).values_list(
            'competencia', flat=True
        ).distinct().order_by('competencia')
        # Para fins de depuração, imprima as competências obtidas
        # print("Competências obtidas do banco de dados:", competencias)

        # Formata as datas no formato desejado para o filtro
        formatted_dates = [
            (competencia.strftime('%Y-%m-%d'), competencia.strftime('%d/%m/%Y'))
            for competencia in competencias
        ]

        # Para fins de depuração, imprima as datas formatadas
        # print("Datas formatadas para o filtro:", formatted_dates)

        return formatted_dates

    def queryset(self, request, queryset):
        if self.value():
            try:
                # Tenta converter o valor da URL para uma data no formato 'yyyy-mm-dd'
                date_obj = datetime.strptime(self.value(), '%Y-%m-%d')
                return queryset.filter(competencia=date_obj)
            except ValueError:
                return queryset
        return queryset

    # Removendo o método 'choices' que foi sobrescrito anteriormente
    # def choices(self, changelist):
    #     # Remove a escolha padrão 'All'
    #     return []

    # Mantém os métodos padrão abaixo, se necessário
    def expected_parameters(self):
        return [self.parameter_name]

    def field_name(self):
        return format_html(
            '<input type="date" name="competencia" value="{}" style="width: 110px; display: inline-block; margin-left: 5px;" />',
            self.value() if self.value() else ''
        )

    def value(self):
        if self.used_parameters.get(self.parameter_name):
            return self.used_parameters[self.parameter_name]
        return None


class PreFaturaAdmin(AdminEstabelecimentoPadraoMixin, ExportToXLSMixin, admin.ModelAdmin):

    form = PreFaturaForm

    actions = ['export_as_xls']

    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']

    list_display = ['id',  'convenio', 'pre_faturado', 'cliente', 'competencia', 'dia_envio', 'valor',
                    'empenho', 'nr_contrato', 'nr_aditivo',  'dt_vencimento', 'estabelecimento', 'status',]
    list_editable = ['valor', 'empenho', 'pre_faturado', 'status']

    list_display_links = ['id', 'convenio']

    search_fields = ['convenio__convenio', 'empenho',
                     'dia_envio', 'cliente', 'nr_contrato', 'nr_aditivo']
    list_filter = [PreFaturadoFilterAdminMixin, StatusFilterAdminMixin, EstabelecimentoFilterAdminMixin, 'pagador_pj', 'pagador_pf',
                   'cliente', 'dia_envio', CustomDateFilter]
    ordering = ['competencia', 'convenio', 'cliente', 'nr_contrato',
                'nr_aditivo', 'valor', 'dia_envio', 'pre_faturado', 'id']
    list_per_page = 99

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Se o objeto já existir (change)
            return self.readonly_fields  # Não altera o comportamento padrão
        else:  # Se for uma nova instância (add)
            # Converter para lista para permitir a concatenação
            return self.readonly_fields + ['pre_faturado', 'status']

    # TODO: AJUSTAR PARA FILTRAR PADRAO OU QQ UM OUTRO

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()
        super().save_model(request, obj, form, change)
        if obj.pre_faturado and not Fatura.objects.filter(prefatura_ptr=obj).exists():
            obj.create_fatura()

    def has_delete_permission(self, request, obj=None):
        """
        Permitir a exclusão apenas para o usuário 'admin'.
        """
        if request.user.username == 'admin':
            return True
        return False

    def delete_queryset(self, request, queryset):
        """
        Impede a exclusão de qualquer queryset de Fatura e exibe uma mensagem.
        """
        if not self.has_delete_permission(request):
            messages.error(
                request, "Não é possível excluir registros deste tipo.")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/admin/'))
        super().delete_queryset(request, queryset)

    def delete_model(self, request, obj):
        """
        Customização da exclusão do modelo para exibir uma mensagem
        se o usuário não tiver permissão.
        """
        if not self.has_delete_permission(request, obj):
            messages.error(
                request, "Não é possível excluir este objeto.")
            return
        super().delete_model(request, obj)


class ConvenioAdmin(AdminEstabelecimentoPadraoMixin, ExportToXLSMixin, admin.ModelAdmin):
    form = ConvenioForm

    actions = ['export_as_xls']

    list_display = ['id', 'convenio', 'pre_faturado', 'gerar_prefaturas_button', 'duplicate_button', 'inicio_vigencia', 'final_vigencia', 'valor_mensal', 'valor_diaria',  'empenho_global', 'client_count', 'total_value',
                    'tx_retencao_nf', 'vl_retencao_nf', 'modo_fatura', 'pagador_pj', 'pagador_pf', 'display_clientes', 'nr_contrato', 'nr_aditivo', 'dia_envio', 'dias_pagamento', 'estabelecimento', 'status']
    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao']
    list_filter = (StatusFilterAdminMixin, EstabelecimentoFilterAdminMixin, 'cliente',
                   'pre_faturado', 'dia_envio', 'dias_pagamento', 'modo_fatura', 'dt_registro', 'us_registro')
    search_fields = ['convenio',]
    list_display_links = ['id', 'convenio']
    list_editable = ['status', 'valor_mensal',
                     'valor_diaria', 'dia_envio', 'dias_pagamento', 'empenho_global']
    list_per_page = 99

    # Método para controlar campos read-only
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Se o objeto já existir (change)
            return self.readonly_fields  # Não altera o comportamento padrão
        else:  # Se for uma nova instância (add)
            # Converter para lista para permitir a concatenação
            return self.readonly_fields + ['pre_faturado', 'status']

    def save_model(self, request, obj, form, change):
        if not change:  # se estiver criando um novo objeto
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:  # se estiver editando um objeto existente
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()

        super().save_model(request, obj, form, change)

    def display_clientes(self, obj):
        return "; ".join([cliente.nome for cliente in obj.cliente.all()])
    display_clientes.short_description = 'Cliente'

    def client_count(self, obj):
        return obj.cliente.count()
    client_count.short_description = 'Qtd.Cliente(s)'

    def total_value(self, obj):
        valor_mensal = obj.valor_mensal if obj.valor_mensal else 0
        valor_diaria = obj.valor_diaria if obj.valor_diaria else 0
        total = (valor_mensal + (valor_diaria * 30)) * self.client_count(obj)
        return f"{total:.2f}"
    total_value.short_description = 'Vl.Mensal(30 dias)'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('duplicate/<int:convenio_id>/',
                 self.admin_site.admin_view(self.duplicate_view), name='duplicate_convenio'),
            path('gerar_prefaturas/<int:convenio_id>/', self.admin_site.admin_view(
                self.gerar_prefaturas_view), name='gerar_prefaturas'),
        ]
        return custom_urls + urls

    def duplicate_button(self, obj):
        if obj.pre_faturado:
            return format_html('<a class="button" href="{}">Duplicar</a>', reverse('admin:duplicate_convenio', args=[obj.pk]))
        return format_html('<span style="color:gray;">Duplicar</span>')
    duplicate_button.short_description = 'Duplicar'
    duplicate_button.allow_tags = True

    def gerar_prefaturas_button(self, obj):
        if obj.pre_faturado:
            return "OK"
        return format_html('<a class="button" href="{}">Gerar</a>', reverse('admin:gerar_prefaturas', args=[obj.pk]))
    gerar_prefaturas_button.short_description = 'Pré-Faturas'
    gerar_prefaturas_button.allow_tags = True

    def duplicate_view(self, request, convenio_id):
        original_convenio = get_object_or_404(Convenio, pk=convenio_id)
        new_convenio = Convenio.objects.get(pk=original_convenio.pk)
        new_convenio.pk = None
        new_convenio.nr_contrato = f"{original_convenio.nr_contrato}"
        new_convenio.pre_faturado = False
        new_convenio.status = 'A'
        new_convenio.save()
        original_convenio.status = 'I'
        original_convenio.save()
        # Duplicate ManyToMany relationships
        new_convenio.cliente.set(original_convenio.cliente.all())

        messages.success(request, 'Convênio duplicado com sucesso.')
        return redirect('admin:admin_faturas_convenio_change', new_convenio.pk)

    def gerar_prefaturas_view(self, request, convenio_id):
        convenio = get_object_or_404(Convenio, pk=convenio_id)

        if convenio.pre_faturado:
            messages.error(
                request, 'Pré-faturas já foram geradas para este convênio.')
            return redirect('admin:admin_faturas_convenio_changelist')

        start_date = convenio.inicio_vigencia
        end_date = convenio.final_vigencia
        dia_envio = convenio.dia_envio
        clientes = convenio.cliente.all()

        valor_mensal = convenio.valor_mensal if convenio.valor_mensal else 0
        valor_diaria = convenio.valor_diaria if convenio.valor_diaria else 0

        if not convenio.fatura_vig_inicial and not convenio.fatura_vig_final:
            start_date = start_date.replace(day=1) + timedelta(days=31)
            end_date = end_date.replace(day=1) - timedelta(days=31)
        elif not convenio.fatura_vig_inicial:
            start_date = start_date.replace(day=1) + timedelta(days=31)
        elif not convenio.fatura_vig_final:
            end_date = end_date.replace(day=1) - timedelta(days=31)

        current_date = start_date
        while current_date <= end_date:
            last_day_of_month = calendar.monthrange(
                current_date.year, current_date.month)[1]
            competencia = date(current_date.year, current_date.month, min(
                dia_envio, last_day_of_month))

            if convenio.modo_fatura == 'CO':
                total_valor = (valor_mensal + (valor_diaria *
                               last_day_of_month)) * clientes.count()
                cliente_names = "; ".join(
                    [cliente.nome for cliente in clientes])

                pre_fatura = PreFatura(
                    estabelecimento=convenio.estabelecimento,
                    dt_registro=timezone.now(),
                    us_registro=request.user,
                    status='A',
                    convenio=convenio,
                    cliente=cliente_names,
                    nr_contrato=convenio.nr_contrato,
                    nr_aditivo=convenio.nr_aditivo,
                    empenho=convenio.empenho_global,
                    dia_envio=convenio.dia_envio,
                    dias_pagamento=convenio.dias_pagamento,
                    competencia=competencia,
                    pagador_pj=convenio.pagador_pj,
                    pagador_pf=convenio.pagador_pf,
                    valor=total_valor,
                    dt_vencimento=competencia +
                    timedelta(days=convenio.dias_pagamento)
                )
                pre_fatura.save()
            else:
                for cliente in clientes:
                    if valor_mensal:
                        valor = valor_mensal
                    else:
                        dias_no_mes = last_day_of_month
                        valor = valor_diaria * dias_no_mes

                    pre_fatura = PreFatura(
                        estabelecimento=convenio.estabelecimento,
                        dt_registro=timezone.now(),
                        us_registro=request.user,
                        status='A',
                        convenio=convenio,
                        cliente=cliente.nome,
                        nr_contrato=convenio.nr_contrato,
                        nr_aditivo=convenio.nr_aditivo,
                        empenho=convenio.empenho_global,
                        dia_envio=convenio.dia_envio,
                        dias_pagamento=convenio.dias_pagamento,
                        competencia=competencia,
                        pagador_pj=convenio.pagador_pj,
                        pagador_pf=convenio.pagador_pf,
                        valor=valor,
                        dt_vencimento=competencia +
                        timedelta(days=convenio.dias_pagamento)
                    )
                    pre_fatura.save()

            current_date = (current_date.replace(day=1) + timedelta(days=31)).replace(
                day=1)  # Avança para o próximo mês

        convenio.pre_faturado = True
        convenio.save()

        messages.success(
            request, 'Pré-faturas geradas com sucesso.')
        return redirect('admin:admin_faturas_convenio_changelist')


class SaldoFilter(admin.SimpleListFilter):
    title = _('Saldo (Valor positivo)')
    parameter_name = 'saldo'

    def lookups(self, request, model_admin):
        return (
            ('positive', _('Saldo positivo')),
            ('negative', _('Saldo negativo')),
            ('zero', _('Saldo zero')),
            ('all', _('Todos')),  # Adiciona opção para exibir todos
        )

    def queryset(self, request, queryset):
        value = self.value()
        if 'saldo' not in request.GET:
            # Se o filtro de saldo não está na URL, aplica o filtro de saldo positivo por padrão
            return queryset.filter(valor_saldo__gt=0)
        elif value == 'positive':
            return queryset.filter(valor_saldo__gt=0)
        elif value == 'negative':
            return queryset.filter(valor_saldo__lt=0)
        elif value == 'zero':
            return queryset.filter(valor_saldo=0)
        elif value == 'all':
            # Retorna todos os objetos quando 'all' é selecionado ou nenhum filtro é aplicado
            return queryset
        return queryset


class FaturaAdmin(AdminEstabelecimentoPadraoMixin, ExportToXLSMixin, admin.ModelAdmin):

      
    actions = ['export_as_xls']

    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao', 'pre_faturado']

    list_display_links = ('id', 'convenio')

    search_fields = ('cliente__nome', 'id')

    form = FaturaForm

    list_display = ['id', 'convenio', 'get_documento_pagador', 'faturado', 'cliente', 'competencia', 'periodo_tratamento', 'dia_envio', 'valor', 'valor_fatura', 'valor_saldo',
                    'dt_liquidacao', 'descricao', 'nr_nota_fiscal', 'anexo_nf', 'dt_vencimento', 'estabelecimento', 'status', ]
    list_editable = ['valor_fatura', 'faturado', 'descricao', 'nr_nota_fiscal', 'anexo_nf', 'status']
    search_fields = ['convenio__convenio', 'cliente',
                     'nr_contrato', 'nr_aditivo', 'descricao', 'nr_nota_fiscal']
    list_filter = ['faturado', SaldoFilter, StatusFilterAdminMixin, EstabelecimentoFilterAdminMixin,
                   'pagador_pj', 'pagador_pf', 'cliente', 'dia_envio', CustomDateFilter]
    ordering = ['competencia', 'convenio', 'cliente',
                'nr_contrato', 'nr_aditivo', 'valor', 'dia_envio', 'faturado', 'id']
    list_per_page = 99

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Se o objeto já existir (change)
            return self.readonly_fields  # Não altera o comportamento padrão
        else:  # Se for uma nova instância (add)
            # Converter para lista para permitir a concatenação
            return self.readonly_fields + ['faturado', 'status']

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
            obj.valor_saldo = obj.valor_fatura
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()
        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        """
        Permitir a exclusão apenas para o usuário 'admin'.
        """
        if request.user.username == 'admin':
            return True
        return False

    def delete_queryset(self, request, queryset):
        """
        Impede a exclusão de qualquer queryset de Fatura e exibe uma mensagem.
        """
        if not self.has_delete_permission(request):
            messages.error(
                request, "Não é possível excluir registros deste tipo.")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/admin/'))
        super().delete_queryset(request, queryset)

    def delete_model(self, request, obj):
        """
        Customização da exclusão do modelo para exibir uma mensagem
        se o usuário não tiver permissão.
        """
        if not self.has_delete_permission(request, obj):
            messages.error(
                request, "Não é possível excluir este objeto.")
            return
        super().delete_model(request, obj)


    def get_documento_pagador(self, obj):
        """
        Retorna CNPJ se Pagador PJ
        Retorna CPF se Pagador PF
        """
        if obj.pagador_pj and hasattr(obj.pagador_pj, 'cnpj'):
            return obj.pagador_pj.cnpj

        if obj.pagador_pf and hasattr(obj.pagador_pf, 'cpf'):
            return obj.pagador_pf.cpf

        return "-"

    get_documento_pagador.short_description = "CNPJ / CPF"
        

# Este nao pode utilizar AdminEstabelecimentoMixin porque tem outros filtros associados ao get_form

# TODO: APOS IMPLANTAR O CAIXA, FIELD COMPETENCIA_CAIXA NA TRANSACAO_FINANCEIRA DE MOVIMENTO IGUAL CAIXA

class BaixaFaturaAdmin(AdminEstabelecimentoPadraoMixin, ExportToXLSMixin, admin.ModelAdmin):
    form = BaixaFaturaForm

    actions = ['export_as_xls']

    list_display = ('id',  'fatura', 'valor_baixa', 'dt_recebimento',
                    'transacao_financeira', 'competencia_bancaria', 'estabelecimento', 'status')

    list_display_links = ['id', 'fatura']

    search_fields = ('id', 'valor_baixa',)

    readonly_fields = ['us_registro', 'dt_registro',
                       'us_atualizacao', 'dt_atualizacao', 'estabelecimento']

    list_filter = ['transacao_financeira', CustomDateFilter,
                   StatusFilterAdminMixin, EstabelecimentoFilterAdminMixin]      

    list_per_page = 99

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)

        if 'HTTP_REFERER' in request.META:
            referer_path = request.META['HTTP_REFERER'].split(
                request.META['HTTP_HOST'])[1]
            if '/add/' in referer_path or '/change/' in referer_path:
                queryset = queryset.filter(status='A')

        return queryset, use_distinct

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        def form_init(form_instance, *args, **kwargs):
            super(form_instance.__class__, form_instance).__init__(
                *args, **kwargs)

            perfil_usuario = request.user.perfil
            estabelecimentos_permitidos = perfil_usuario.estabelecimento.all()

            form_instance.fields['fatura'].queryset = Fatura.objects.filter(
                valor_saldo__gt=0, status='A', faturado=True, estabelecimento__in=estabelecimentos_permitidos
            )

            form_instance.fields['transacao_financeira'].queryset = TransacaoFinanceira.objects.filter(
                tipo='entrada', status='A'
            )

            form_instance.fields['competencia_bancaria'].queryset = CompetenciaBancaria.objects.filter(
                dt_fechamento_competencia__isnull = True, status='A'
            )

        form.__init__ = form_init

        return form


    def save_model(self, request, obj, form, change):
        """
        Define os campos de auditoria e salva o objeto com as informações
        de registro e atualização de usuários e datas.
        """
        if not change:
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()

        if obj.fatura:
            obj.estabelecimento = obj.fatura.estabelecimento

        super().save_model(request, obj, form, change)


# Registro dos admins no Django
admin.site.register(PreFatura, PreFaturaAdmin)
admin.site.register(Convenio, ConvenioAdmin)
admin.site.register(Fatura, FaturaAdmin)
admin.site.register(BaixaFatura, BaixaFaturaAdmin)
