from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import ControleBancario, CompetenciaBancaria, MovimentoBancario
from admin_pagamentos.models import Pagamento
from admin_faturas.models import Fatura
from dominios.utils import ExportToXLSMixin, AdminEstabelecimentoPadraoMixin, StatusFilterAdminMixin
from datetime import timedelta, date
import calendar
from decimal import Decimal
from admin_cadastros.utils import EstabelecimentoFilterAdminMixin
from .models import CompetenciaBancaria
from admin_financeiro.forms import CompetenciaBancariaForm, MovimentoBancarioForm
from django.utils import timezone
from contas.models import Perfil
from admin_cadastros_financeiros.models import Banco, Agencia, Conta, TransacaoFinanceira
import xlwt
from django.http import HttpResponse
from django.contrib import admin
from django.apps import apps
from django.db.models import Model

"""
@admin.action(description="Exportar todos os campos para XLS")
def exportar_competencia_xls(modeladmin, request, queryset):
    # Configurar o arquivo XLS
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="competencia_bancaria_dados_exportados.xls"'

    # Criar o workbook e a worksheet
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Dados')

    # Cabeçalhos das colunas (ajustados para todos os campos)
    colunas = [
        'ID', 'Controle Bancário', 'Descrição', 'Data de Abertura', 
        'Data de Fechamento', 'Saldo Inicial', 'Saldo Anterior', 
        'Saldo Atual', 'Observação', 'Usuário Registro', 
        'Data Registro', 'Usuário Atualização', 'Data Atualização', 
        'Estabelecimento', 'Status'
    ]

    # Criar cabeçalhos no arquivo
    for coluna_num, coluna_nome in enumerate(colunas):
        ws.write(0, coluna_num, coluna_nome, xlwt.easyxf('font: bold 1'))

    # Preencher os dados
    for linha_num, objeto in enumerate(queryset, start=1):
        ws.write(linha_num, 0, objeto.id)  # ID do objeto
        ws.write(linha_num, 1, str(objeto.controle_bancario))  # ForeignKey para ControleBancario
        ws.write(linha_num, 2, objeto.descricao)  # Descrição
        ws.write(linha_num, 3, objeto.dt_abertura_competencia.strftime('%d/%m/%Y'))  # Data de Abertura
        ws.write(linha_num, 4, objeto.dt_fechamento_competencia.strftime('%d/%m/%Y') if objeto.dt_fechamento_competencia else 'Em aberto')  # Data de Fechamento
        ws.write(linha_num, 5, float(objeto.saldo_inicial))  # Saldo Inicial
        ws.write(linha_num, 6, float(objeto.saldo_anterior))  # Saldo Anterior
        ws.write(linha_num, 7, float(objeto.saldo_atual))  # Saldo Atual
        ws.write(linha_num, 8, objeto.observacao or '')  # Observação
        ws.write(linha_num, 9, str(objeto.us_registro))  # Usuário Registro
        ws.write(linha_num, 10, objeto.dt_registro.strftime('%d/%m/%Y %H:%M:%S'))  # Data Registro
        ws.write(linha_num, 11, str(objeto.us_atualizacao) if objeto.us_atualizacao else '')  # Usuário Atualização
        ws.write(linha_num, 12, objeto.dt_atualizacao.strftime('%d/%m/%Y %H:%M:%S') if objeto.dt_atualizacao else '')  # Data Atualização
        ws.write(linha_num, 13, str(objeto.estabelecimento))  # Estabelecimento
        ws.write(linha_num, 14, objeto.get_status_display())  # Status (usando display do campo choices)

    # Salvar o workbook no response
    wb.save(response)
    return response


@admin.action(description="Exportar todos os campos para XLS")
def exportar_movimento_xls(modeladmin, request, queryset):
    # Configurar o arquivo XLS
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="movimentos_bancarios_dados_exportados.xls"'

    # Criar o workbook e a worksheet
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Dados')

    # Cabeçalhos das colunas (ajustados para todos os campos)
    colunas = [
        'ID', 'Competência Bancária', 'Transação Financeira', 'Valor Entrada',
        'Valor Saída', 'Usuário Registro', 'Data Registro', 'Usuário Atualização',
        'Data Atualização', 'Estabelecimento', 'Status'
    ]

    # Criar cabeçalhos no arquivo
    for coluna_num, coluna_nome in enumerate(colunas):
        ws.write(0, coluna_num, coluna_nome, xlwt.easyxf('font: bold 1'))

    # Preencher os dados
    for linha_num, objeto in enumerate(queryset, start=1):
        ws.write(linha_num, 0, objeto.id)  # ID do objeto
        ws.write(linha_num, 1, str(objeto.competencia_bancaria))  # ForeignKey para Competência Bancária
        ws.write(linha_num, 2, str(objeto.transacao_financeira))  # ForeignKey para Transação Financeira
        ws.write(linha_num, 3, float(objeto.valor_entrada) if objeto.valor_entrada else 0.0)  # Valor Entrada
        ws.write(linha_num, 4, float(objeto.valor_saida) if objeto.valor_saida else 0.0)  # Valor Saída
        ws.write(linha_num, 5, str(objeto.us_registro))  # Usuário Registro
        ws.write(linha_num, 6, objeto.dt_registro.strftime('%d/%m/%Y %H:%M:%S'))  # Data Registro
        ws.write(linha_num, 7, str(objeto.us_atualizacao) if objeto.us_atualizacao else '')  # Usuário Atualização
        ws.write(linha_num, 8, objeto.dt_atualizacao.strftime('%d/%m/%Y %H:%M:%S') if objeto.dt_atualizacao else '')  # Data Atualização
        ws.write(linha_num, 9, str(objeto.estabelecimento))  # Estabelecimento
        ws.write(linha_num, 10, objeto.get_status_display())  # Status (usando display do campo choices)

    # Salvar o workbook no response
    wb.save(response)
    return response
"""



class BancoPadraoFilter(admin.SimpleListFilter):
    title = _("Banco Padrão")
    parameter_name = "banco_padrao"

    def lookups(self, request, model_admin):
        perfil = Perfil.objects.filter(user=request.user).first()
        if not perfil or not perfil.estabelecimento_padrao:
            return []
        
        # Obter as contas padrão associadas ao estabelecimento padrão do perfil
        contas_padroes = Conta.objects.filter(
            padrao=True,
            agencia__estabelecimento=perfil.estabelecimento_padrao  # Associa conta ao estabelecimento
        ).select_related('agencia__banco').distinct()

        # Retornar uma lista de tuplas (id da conta, descrição do banco) para o filtro
        return [(conta.id, conta.agencia.banco.descricao_banco) for conta in contas_padroes]

    def queryset(self, request, queryset):
        perfil = Perfil.objects.filter(user=request.user).first()
        if not perfil:
            return queryset.none()  # Retorna queryset vazio se o usuário não tiver um perfil

        if self.value():
            # Filtra pelo banco selecionado manualmente pelo usuário (por conta_id)
            return queryset.filter(competencia_bancaria__controle_bancario__conta_id=self.value())
        
        # Filtra automaticamente pelo banco padrão do estabelecimento padrão do perfil
        return queryset.filter(
            competencia_bancaria__controle_bancario__conta__padrao=True,
            competencia_bancaria__controle_bancario__conta__agencia__estabelecimento=perfil.estabelecimento_padrao  # Filtra por estabelecimento padrão
        )






# Inline de SaldoBanco para ser exibido dentro de ControleBancario
@admin.register(CompetenciaBancaria)
class CompetenciaBancariaAdmin(AdminEstabelecimentoPadraoMixin, ExportToXLSMixin, admin.ModelAdmin):
  
    form = CompetenciaBancariaForm

    actions = ['export_as_xls'] # Registrar a ação no admin


    readonly_fields = ['dt_registro', 'us_registro', 'dt_atualizacao', 'us_atualizacao']

    list_filter = [StatusFilterAdminMixin, EstabelecimentoFilterAdminMixin]

    list_display = [ 'descricao', 'saldo_inicial', 'saldo_anterior', 'saldo_atual', '__str__',]

    list_display_links = [ 'descricao', '__str__',]

    ordering = ['-dt_abertura_competencia',]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()           
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()
        super().save_model(request, obj, form, change)


# Admin de ControleBancario
@admin.register(ControleBancario)
class ControleBancarioAdmin(AdminEstabelecimentoPadraoMixin, ExportToXLSMixin, admin.ModelAdmin):
    list_display = ['conta']  # Exibir a conta no controle bancário
     
    actions = ['export_as_xls'] # Registrar a ação no admin

    readonly_fields = ['dt_registro', 'us_registro', 'dt_atualizacao', 'us_atualizacao',]

    list_filter = [StatusFilterAdminMixin, EstabelecimentoFilterAdminMixin]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()           
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()
       
        super().save_model(request, obj, form, change)



class CompetenciaAbertaMixin:
    """
    Mixin para exibir movimentos relacionados a competências sem 'dt_fechamento_competencia' por padrão,
    mas permitir filtrar por qualquer competência ao realizar uma pesquisa.
    """

    def get_form(self, request, obj=None, **kwargs):
        """
        Personaliza o formulário no Admin para definir competências abertas como padrão.
        """
        form = super().get_form(request, obj, **kwargs)

        # Sobrescreve o método init do formulário
        def form_init(form_instance, *args, **kwargs):
            # Chama o init original
            super(form_instance.__class__, form_instance).__init__(*args, **kwargs)

            # Configuração padrão para competências abertas
            competencias_abertas = CompetenciaBancaria.objects.filter(
                dt_fechamento_competencia__isnull=True
            )
            form_instance.fields['competencia_bancaria'].queryset = CompetenciaBancaria.objects.all()

            # Define valor inicial apenas para novas instâncias
            if not obj and competencias_abertas.exists():
                form_instance.fields['competencia_bancaria'].initial = competencias_abertas.first()

        # Substitui o __init__ do formulário com a lógica de inicialização personalizada
        form.__init__ = form_init

        return form

    def get_queryset(self, request):
        """
        Exibe inicialmente movimentos relacionados a competências abertas,
        mas permite a visualização de todos os objetos quando o filtro é aplicado.
        """
        qs = super().get_queryset(request)

        # Verifica se algum filtro foi aplicado
        if 'competencia_bancaria__id__exact' not in request.GET:
            # Filtra apenas movimentos relacionados a competências abertas
            return qs.filter(competencia_bancaria__dt_fechamento_competencia__isnull=True)

        # Retorna todos os movimentos sem restrições adicionais
        return qs


@admin.register(MovimentoBancario)
class MovimentoBancarioAdmin(CompetenciaAbertaMixin, ExportToXLSMixin, AdminEstabelecimentoPadraoMixin, admin.ModelAdmin):
    form = MovimentoBancarioForm

    actions = ['export_as_xls'] # Registrar a ação no admin
  
  
    readonly_fields = ['dt_registro', 'us_registro', 'dt_atualizacao', 'us_atualizacao','estabelecimento']

    list_display = [
        'competencia_bancaria', 'transacao_financeira', 'valor_entrada', 'valor_saida',
        'us_registro', 'dt_registro', 'us_atualizacao', 'dt_atualizacao', 'estabelecimento', 'status'
    ]

    readonly_fields = ['dt_registro', 'us_registro', 'dt_atualizacao', 'us_atualizacao']

    list_filter = [
        'competencia_bancaria',  # Permite filtrar por qualquer competência bancária
        'transacao_financeira',
        'us_registro',
        'us_atualizacao',
        StatusFilterAdminMixin,
        EstabelecimentoFilterAdminMixin,
        BancoPadraoFilter,
        ('dt_registro', admin.DateFieldListFilter),
        ('dt_atualizacao', admin.DateFieldListFilter),
    ]



    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        def form_init(form_instance, *args, **kwargs):
            super(form_instance.__class__, form_instance).__init__(
                *args, **kwargs)

            perfil_usuario = request.user.perfil
            estabelecimentos_permitidos = perfil_usuario.estabelecimento.all()
          

            form_instance.fields['transacao_financeira'].queryset = TransacaoFinanceira.objects.filter(
                movimento='banco', status='A'
            )

            form_instance.fields['competencia_bancaria'].queryset = CompetenciaBancaria.objects.filter(
                dt_fechamento_competencia__isnull = True, status='A'
            )

        form.__init__ = form_init

        return form



    def save_model(self, request, obj, form, change):
        """
        Salva o registro com informações do usuário e timestamps.
        """
        if not change:
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
            obj.estabelecimento = obj.competencia_bancaria.estabelecimento
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()  
        super().save_model(request, obj, form, change)
