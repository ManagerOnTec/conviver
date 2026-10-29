from django.contrib import admin
from django.contrib import messages as admin_messages
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from .models import ControleBancario, CompetenciaBancaria, MovimentoBancario
from admin_pagamentos.models import Pagamento
from admin_faturas.models import Fatura
from admin_faturas.dashboard import FaturasDashboardMixin
from django.urls import reverse, path
from dominios.utils import ExportToXLSMixin, AdminEstabelecimentoPadraoMixin, StatusFilterAdminMixin, chain_form_init
from datetime import timedelta, date
import calendar
from decimal import Decimal
from admin_cadastros.utils import EstabelecimentoFilterAdminMixin
from .models import CompetenciaBancaria
from admin_financeiro.forms import CompetenciaBancariaForm, MovimentoBancarioForm
from django.utils import timezone
from contas.models import Perfil
from admin_cadastros.models import Estabelecimento
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



class CompetenciaSelect2Filter(admin.SimpleListFilter):
    """Competência bancária em DROPDOWN com busca (select2).

    Lista TODAS as competências do estabelecimento ativo — abertas E fechadas
    — cada uma com banco/conta/período no rótulo e a situação. Permite
    consultar movimentos de qualquer competência, inclusive depois de
    fechada/concluída a conciliação.
    """
    title = _('Competência Bancária')
    parameter_name = 'competencia'
    template = 'admin/filter_select2.html'

    def _texto(self, comp):
        conta = getattr(comp.controle_bancario, 'conta', None)
        banco = getattr(getattr(conta, 'agencia', None), 'banco', None)
        situacao = ('Fechada' if comp.dt_fechamento_competencia else 'Aberta')
        fech = (comp.dt_fechamento_competencia.strftime('%d/%m/%Y')
                if comp.dt_fechamento_competencia else '')
        partes = [f'{comp.descricao}', situacao]
        if fech:
            partes[-1] += f' em {fech}'
        if banco is not None and conta is not None:
            partes.append(f'{banco} · {conta.numero_conta}')
        return ' — '.join(partes)

    def choices(self, changelist):
        """Opções do dropdown; `url` leva a listagem já filtrada."""
        selecionados = self.valores()
        yield {'value': '', 'url': changelist.get_query_string(
            remove=[self.parameter_name]), 'selected': not selecionados,
            'display': '— Todas —'}
        for valor, rotulo in self.lookup_choices:
            valor = str(valor)
            yield {
                'value': valor,
                'url': changelist.get_query_string(
                    {self.parameter_name: valor}),
                'selected': valor in selecionados,
                'display': rotulo,
            }

    def valores(self):
        valor = self.value()
        if isinstance(valor, (list, tuple)):
            return [str(v) for v in valor if v]
        return [str(valor)] if valor else []

    def lookups(self, request, model_admin):
        try:
            perfil = Perfil.objects.filter(user=request.user).first()
            qs = CompetenciaBancaria.objects.select_related(
                'controle_bancario__conta__agencia__banco')
            estabelecimento = BancoPadraoFilter._estabelecimento_ativo(
                request, perfil)
            if estabelecimento is not None:
                qs = qs.filter(estabelecimento=estabelecimento)
            elif perfil is not None:
                qs = qs.filter(
                    estabelecimento__in=perfil.estabelecimento.all())
            return [(c.pk, self._texto(c)) for c in
                    qs.order_by('-dt_abertura_competencia')[:300]]
        except Exception:
            return []  # nunca derruba a listagem

    def queryset(self, request, queryset):
        valor = self.value()
        if isinstance(valor, (list, tuple)):
            valor = valor[0] if valor else None
        if not valor:
            return queryset
        try:
            if queryset.model is CompetenciaBancaria:
                return queryset.filter(pk=valor)
            return queryset.filter(competencia_bancaria_id=valor)
        except Exception:
            return queryset


class BancoPadraoFilter(admin.SimpleListFilter):
    """Banco (conta) dos movimentos — de seleção MÚLTIPLA.

    Padrão: o(s) banco(s) PADRÃO do estabelecimento ativo (conta.padrao=True).
    Sem banco padrão cadastrado, NÃO restringe — a listagem mostra os demais
    bancos e avisa o usuário (nunca estoura exceção).
    """
    title = _("Banco")
    parameter_name = "banco"
    template = 'admin/filter_multiselect.html'

    def choices(self, changelist):
        """Choices em caixas de marcar (template próprio)."""
        selecionados = set(self.valores())
        for valor, rotulo in self.lookup_choices:
            valor = str(valor)
            yield {
                'selected': valor in selecionados,
                'query_string': changelist.get_query_string(
                    {self.parameter_name: valor}),
                'display': rotulo,
                'value': valor,
                'parameter_name': self.parameter_name,
            }

    @staticmethod
    def _estabelecimento_ativo(request, perfil):
        """Estabelecimento ativo na sessão; sem sessão, o padrão do perfil."""
        estabelecimento_id = request.session.get('estabelecimento_id')
        if estabelecimento_id:
            estabelecimento = Estabelecimento.objects.filter(
                pk=estabelecimento_id).first()
            if estabelecimento is not None:
                return estabelecimento
        return getattr(perfil, 'estabelecimento_padrao', None)

    def valores(self):
        """Todos os valores escolhidos na URL (multiseleção)."""
        valores = self.used_parameters.get(self.parameter_name)
        if isinstance(valores, (list, tuple)):
            return [str(v) for v in valores if v not in (None, '')]
        if valores in (None, ''):
            return []
        return [str(valores)]

    # ------------------------------------------------------------------
    # BANCO PADRÃO = banco da COMPETÊNCIA BANCÁRIA ABERTA do estabelecimento.
    # ------------------------------------------------------------------
    @classmethod
    def contas_padrao(cls, request):
        """Contas do(s) banco(s) com COMPETÊNCIA ABERTA no estabelecimento
        ativo. Se não houver competência aberta, cai nas contas marcadas
        `padrao`; sem nenhuma das duas, devolve queryset vazio."""
        perfil = Perfil.objects.filter(user=request.user).first()
        estabelecimento = cls._estabelecimento_ativo(request, perfil)
        abertas = CompetenciaBancaria.objects.filter(
            dt_fechamento_competencia=None, status='A',
            controle_bancario__isnull=False)
        if estabelecimento is not None:
            abertas = abertas.filter(estabelecimento=estabelecimento)
        elif perfil is not None:
            abertas = abertas.filter(
                estabelecimento__in=perfil.estabelecimento.all())
        contas = Conta.objects.filter(
            id__in=abertas.values('controle_bancario__conta_id'))
        if not contas.exists():
            contas = Conta.objects.filter(padrao=True)
            if estabelecimento is not None:
                contas = contas.filter(
                    agencia__estabelecimento=estabelecimento)
        return contas

    def lookups(self, request, model_admin):
        perfil = Perfil.objects.filter(user=request.user).first()
        estabelecimento = self._estabelecimento_ativo(request, perfil)
        try:
            padrao_ids = set(
                self.contas_padrao(request).values_list('pk', flat=True))
            contas = Conta.objects.select_related('agencia__banco')
            if estabelecimento is not None:
                contas = contas.filter(
                    agencia__estabelecimento=estabelecimento)
            elif perfil is not None:
                contas = contas.filter(
                    agencia__estabelecimento__in=perfil.estabelecimento.all())
            opcoes = []
            for conta in contas.distinct():
                banco = getattr(getattr(conta, 'agencia', None), 'banco', None)
                agencia = getattr(conta, 'agencia', None)
                rotulo = str(banco or conta)
                if agencia is not None:
                    rotulo = (f'{banco or "Conta"} · Ag '
                              f'{agencia.numero_agencia} · '
                              f'{conta.numero_conta}')
                if conta.pk in padrao_ids:
                    rotulo += ' (padrão)'
                opcoes.append((conta.pk, rotulo))
            return opcoes
        except Exception:
            # Nunca derruba a tela por causa do filtro.
            return []

    def queryset(self, request, queryset):
        # `banco` = conta bancária. O caminho muda conforme o modelo listado:
        # competência -> controle_bancario; movimento -> competencia_bancaria.
        model = queryset.model
        nomes = {f.name for f in model._meta.get_fields()}
        if 'controle_bancario' in nomes:
            caminho = 'controle_bancario__conta'
        elif 'competencia_bancaria' in nomes:
            caminho = 'competencia_bancaria__controle_bancario__conta'
        else:
            return queryset
        try:
            valores = self.valores()
            if valores:
                return queryset.filter(**{f'{caminho}__in': valores})
            # Sem escolha: recorta pelo banco da COMPETÊNCIA ABERTA.
            padroes = self.contas_padrao(request)
            if not padroes.exists():
                # Sem banco padrão/competência aberta: não restringe (a tela
                # avisa o usuário — nunca estoura).
                request._sem_banco_padrao = True
                return queryset
            return queryset.filter(**{f'{caminho}__in': padroes})
        except Exception:
            # Filtro com valor inválido (ex.: conta apagada) não derruba a
            # listagem: apenas não restringe.
            return queryset






# Inline de SaldoBanco para ser exibido dentro de ControleBancario
@admin.register(CompetenciaBancaria)
class CompetenciaBancariaAdmin(AdminEstabelecimentoPadraoMixin, ExportToXLSMixin, admin.ModelAdmin):
  
    form = CompetenciaBancariaForm

    actions = ['export_as_xls', 'fechar_competencias'] # Registrar a ação no admin

    # Necessário para o select2 de digitação (autocomplete) nas Baixas de Fatura.
    search_fields = ['descricao', 'controle_bancario__conta__observacao',
                     'estabelecimento__estabelecimento']


    readonly_fields = ['dt_registro', 'us_registro', 'dt_atualizacao', 'us_atualizacao']

    list_filter = [BancoPadraoFilter, StatusFilterAdminMixin,
                   EstabelecimentoFilterAdminMixin]

    list_display = [ 'descricao', 'saldo_inicial', 'saldo_anterior',
                     'saldo_atual', 'fechar_link', '__str__',]

    list_display_links = [ 'descricao', '__str__',]

    def fechar_link(self, obj):
        """Botão "Fechar competência" por linha.

        Abre a tela de EDIÇÃO da competência com a DATA DE FECHAMENTO já
        preenchida com a data de hoje (o usuário confirma/ajusta) — em vez
        do antigo botão "Conciliar".
        """
        from django.urls import reverse
        from django.utils.html import format_html
        if obj.dt_fechamento_competencia:
            return format_html(
                '<span style="color:#15803d; font-weight:600">✓ '
                'Fechada em {}</span>',
                obj.dt_fechamento_competencia.strftime('%d/%m/%Y'))
        url = reverse('admin:admin_financeiro_competenciabancaria_change',
                      args=[obj.pk])
        url += '?fechar=1'
        return format_html(
            '<a class="button" style="padding:3px 10px; background:#b91c1c" '
            'href="{}" title="Abrir com a data de fechamento de hoje">'
            'Fechar competência</a>', url)
    fechar_link.short_description = 'Fechamento'

    ordering = ['-dt_abertura_competencia',]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()  
        super().save_model(request, obj, form, change)

    @admin.action(description='Fechar competência (exige conciliação)')
    def fechar_competencias(self, request, queryset):
        """Fecha as competências selecionadas — cada uma SOMENTE se houver
        conciliação bancária FINALIZADA sem divergência (extrato importado e
        conferido). Mensagens amigáveis indicam o que falta em cada uma."""
        fechadas, problemas = [], []
        for comp in queryset:
            if comp.dt_fechamento_competencia:
                problemas.append(f'{comp.descricao}: já fechada em '
                                 f'{comp.dt_fechamento_competencia:%d/%m/%Y}.')
                continue
            conc = getattr(comp, 'conciliacao', None)
            if conc is None or not conc.finalizada:
                problemas.append(
                    f'{comp.descricao}: conciliação bancária não finalizada '
                    '(importe o extrato e conclua a conciliação).')
                continue
            if abs(conc.divergencia) >= Decimal('0.01'):
                problemas.append(
                    f'{comp.descricao}: divergência de R$ {conc.divergencia} '
                    'entre o sistema e o extrato.')
                continue
            comp.dt_fechamento_competencia = timezone.localdate()
            comp.us_atualizacao = request.user
            comp.dt_atualizacao = timezone.now()
            comp.save(update_fields=['dt_fechamento_competencia',
                                     'us_atualizacao', 'dt_atualizacao'])
            fechadas.append(comp.descricao)
        if fechadas:
            messages.success(request,
                             'Competência(s) fechada(s): ' + ', '.join(fechadas))
        for problema in problemas:
            messages.warning(request, problema)

    def get_form(self, request, obj=None, **kwargs):
        """No botão "Fechar competência" (`?fechar=1`), já preenche a DATA DE
        FECHAMENTO com hoje — o usuário só confirma ou ajusta a data correta.
        """
        form = super().get_form(request, obj, **kwargs)
        if (obj is not None and request.GET.get('fechar') == '1'
                and not obj.dt_fechamento_competencia):
            hoje = timezone.localdate()
            form.base_fields['dt_fechamento_competencia'].initial = hoje

            def form_init(form_instance, *args, **form_kwargs):
                if not form_instance.is_bound:
                    form_instance.initial['dt_fechamento_competencia'] = hoje
                # Aviso amigável: escolha/confirme a data real do fechamento.
                messages.info(
                    request,
                    'Data de fechamento preenchida com HOJE '
                    f'({hoje:%d/%m/%Y}). Confira e ajuste para a DATA CORRETA '
                    f'do fechamento antes de salvar. A conciliação bancária '
                    f'precisa estar finalizada e sem divergência.')

            chain_form_init(form, form_init)
        return form


# Admin de ControleBancario
@admin.register(ControleBancario)
class ControleBancarioAdmin(AdminEstabelecimentoPadraoMixin, ExportToXLSMixin, admin.ModelAdmin):
    list_display = ['conta']  # Exibir a conta no controle bancário

    # Necessário para o select2 de digitação (autocomplete) na Competência Bancária.
    search_fields = ['conta__agencia__numero_agencia', 'conta__numero_conta',
                     'conta__observacao']
     
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

        def form_init(form_instance, *args, **kwargs):
            # Configuração padrão para competências abertas
            competencias_abertas = CompetenciaBancaria.objects.filter(
                dt_fechamento_competencia__isnull=True
            )
            form_instance.fields['competencia_bancaria'].queryset = CompetenciaBancaria.objects.all()

            # Define valor inicial apenas para novas instâncias
            if not obj and competencias_abertas.exists():
                form_instance.fields['competencia_bancaria'].initial = competencias_abertas.first()

        # Encadeia em vez de substituir o __init__ aplicado pelo mixin.
        chain_form_init(form, form_init)

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
class MovimentoBancarioAdmin(CompetenciaAbertaMixin, FaturasDashboardMixin, ExportToXLSMixin, AdminEstabelecimentoPadraoMixin, admin.ModelAdmin):
    form = MovimentoBancarioForm

    actions = ['export_as_xls', 'empacotar_movimentos']

    # DASHBOARD: totais no recorte ATUAL (competência/banco/período/filtros).
    dashboard_competencia_field = 'dt_movimento'
    dashboard_vencimento_field = 'dt_movimento'
    dashboard_valor_field = 'valor_entrada'
    dashboard_saldo_field = None

    def get_dashboard_kpis(self, request, queryset):
        """KPIs do movimento: ENTRADAS, SAÍDAS, SALDO e quantidade — sempre
        calculados sobre o `queryset` já filtrado (competência, banco, datas)."""
        from django.db.models import Sum, Count
        from admin_faturas.dashboard import _money, _qtd

        somas = queryset.aggregate(
            entradas=Sum('valor_entrada'),
            saidas=Sum('valor_saida'),
            qtde=Count('pk'))
        entradas = somas['entradas'] or Decimal('0')
        saidas = somas['saidas'] or Decimal('0')
        qtde = somas['qtde'] or 0
        empacotados = queryset.exclude(baixa_fatura=None).exclude(
            baixa_fatura__baixas_empacotadas=None).count()

        return [
            {
                'title': 'Entradas',
                'value': _money(entradas),
                'subtitle': 'Soma dos créditos no filtro',
                'color_class': 'kpi-green',
                'icon': 'fa-arrow-down',
            },
            {
                'title': 'Saídas',
                'value': _money(saidas),
                'subtitle': 'Soma dos débitos no filtro',
                'color_class': 'kpi-red',
                'icon': 'fa-arrow-up',
            },
            {
                'title': 'Resultado (E − S)',
                'value': _money(entradas - saidas),
                'subtitle': 'Entradas menos saídas',
                'color_class': 'kpi-blue',
                'icon': 'fa-scale-balanced',
            },
            {
                'title': 'Lançamentos',
                'value': _qtd(qtde),
                'subtitle': f'{_qtd(empacotados)} empacotado(s)',
                'color_class': 'kpi-purple',
                'icon': 'fa-list',
            },
        ]

    readonly_fields = ['dt_registro', 'us_registro', 'dt_atualizacao',
                       'us_atualizacao', 'estabelecimento']

    # Campos exibidos no formulário: a `observacao` é EDITÁVEL — em
    # lançamento manual o usuário descreve (o sistema prefixa "Lançamento
    # manual"); nos movimentos de baixa a `origem` é gravada automaticamente.
    fields = ['competencia_bancaria', 'transacao_financeira', 'valor_entrada',
              'valor_saida', 'observacao', 'status']

    list_display = [
        'competencia_bancaria', 'dt_movimento', 'transacao_financeira',
        'valor_entrada', 'valor_saida',
        'baixa_origem_display', 'observacao', 'status_conciliacao',
        'baixa_fatura', 'us_registro', 'dt_registro', 'estabelecimento',
        'status'
    ]

    def status_conciliacao(self, obj):
        """Status da conciliação deste movimento (na coluna da listagem)."""
        from django.utils.html import format_html
        situacao = obj.situacao_conciliacao()
        cores = {'Conciliado': '#15803d', 'Pendente': '#b45309',
                 'Ignorado': '#6b7280', 'Não conciliado': '#b91c1c'}
        return format_html(
            '<span style="color:{}; font-weight:600">{}</span>',
            cores.get(situacao, '#374151'), situacao)
    status_conciliacao.short_description = 'Conciliação'

    def get_list_filter(self, request):
        """Competência em dropdown com busca (abertas E fechadas)."""
        filtros = list(self.list_filter)
        # Troca o filtro nativo de competência pelo select (mantém o resto).
        filtros = [f for f in filtros if f != 'competencia_bancaria']
        return [CompetenciaSelect2Filter] + filtros

    readonly_fields = ['dt_registro', 'us_registro', 'dt_atualizacao', 'us_atualizacao', 'baixa_fatura']

    list_filter = [
        'competencia_bancaria',  # Permite filtrar por qualquer competência bancária
        'transacao_financeira',
        'us_registro',
        'us_atualizacao',
        StatusFilterAdminMixin,
        EstabelecimentoFilterAdminMixin,
        BancoPadraoFilter,
        ('dt_movimento', admin.DateFieldListFilter),
        ('dt_registro', admin.DateFieldListFilter),
    ]

    def changelist_view(self, request, extra_context=None):
        """Avisa (sem estourar) quando não há banco PADRÃO cadastrado para o
        estabelecimento ativo — a listagem passa a mostrar todos os bancos."""
        extra_context = dict(extra_context or {})
        try:
            if not request.GET.get('banco'):
                tem_padrao = BancoPadraoFilter.contas_padrao(request).exists()
                if not tem_padrao:
                    admin_messages.warning(
                        request,
                        'Nenhum banco com COMPETÊNCIA BANCÁRIA ABERTA (nem '
                        'conta marcada como padrão) para o estabelecimento: '
                        'exibindo os movimentos de TODOS os bancos. Abra uma '
                        'competência ou marque o banco no filtro lateral.')
        except Exception:
            pass  # nunca derruba a listagem
        return super().changelist_view(request, extra_context)

    def get_form(self, request, obj=None, **kwargs):
        # O super() já inclui a filtragem/inicialização de 'estabelecimento'
        # feita pelo AdminEstabelecimentoPadraoMixin.
        form = super().get_form(request, obj, **kwargs)

        def form_init(form_instance, *args, **kwargs):
            form_instance.fields['transacao_financeira'].queryset = TransacaoFinanceira.objects.filter(
                movimento='banco', status='A'
            )

            form_instance.fields['competencia_bancaria'].queryset = CompetenciaBancaria.objects.filter(
                dt_fechamento_competencia__isnull = True, status='A'
            )

        # Encadeia em vez de substituir o __init__ aplicado pelo mixin.
        chain_form_init(form, form_init)

        return form

    @admin.action(description='Empacotar Movimentos (Dois ou mais)')
    def empacotar_movimentos(self, request, queryset):
        """Soma os lançamentos selecionados em UM único movimento.

        O movimento mais recente recebe o TOTAL dos demais e os demais
        lançamentos são EXCLUÍDOS — o banco fica com um lançamento único do
        valor consolidado. As baixas de fatura ligadas continuam existindo
        (elas movimentam o saldo da fatura); o movimento único lista todas as
        baixas de origem (e as que elas já empacotavam) na coluna "Origem".
        """
        movs = list(queryset.order_by('-pk'))
        if len(movs) < 2:
            self.message_user(
                request, 'Selecione 2 ou mais lançamentos para empacotar.',
                level=admin_messages.WARNING)
            return
        # VALIDADOR: nenhum lançamento selecionado pode já ser origem de um
        # pacote (uma baixa que já empacota outras baixas) — empacotar de novo
        # faria o mesmo valor somar em dois movimentos.
        ja_pacote = [m.pk for m in movs
                     if m.baixa_fatura_id
                     and m.baixa_fatura.baixas_empacotadas.exists()]
        if ja_pacote:
            self.message_user(
                request,
                'Lançamento(s) já é origem de pacote (a baixa dele já '
                'empacota outras baixas) e não pode ser empacotado de novo: '
                + ', '.join(f'#{p}' for p in ja_pacote),
                level=admin_messages.ERROR)
            return
        # VALIDADOR: movimentos sem baixa (lançamentos manuais) também podem
        # já ter absorvido outros — marca pela própria `origem` consolidada?
        # Não há marcador; a proteção acima cobre o caso de baixa.
        # Todos têm de ser da MESMA competência bancária (o lançamento único
        # pertence a uma competência só).
        competencias = {m.competencia_bancaria_id for m in movs}
        if len(competencias) > 1:
            self.message_user(
                request,
                'Os lançamentos são de competências bancárias DIFERENTES; '
                'empacote apenas lançamentos da mesma competência.',
                level=admin_messages.ERROR)
            return
        # Mesmo sentido: todas ENTRADAS ou todas SAÍDAS.
        tem_entrada = any((m.valor_entrada or 0) > 0 for m in movs)
        tem_saida = any((m.valor_saida or 0) > 0 for m in movs)
        if tem_entrada and tem_saida:
            self.message_user(
                request,
                'Não é possível empacotar ENTRADAS e SAÍDAS juntos.',
                level=admin_messages.ERROR)
            return
        pacote = movs[0]
        absorvidos = movs[1:]
        if tem_saida:
            total = sum((m.valor_saida or 0) for m in movs)
            pacote.valor_saida = total
            pacote.valor_entrada = 0
        else:
            total = sum((m.valor_entrada or 0) for m in movs)
            pacote.valor_entrada = total
            pacote.valor_saida = 0
        # As baixas dos lançamentos absorvidos passam a constar como
        # EMPACOTADAS na baixa do pacote (coluna "Origem").
        baixas_absorvidas = [m.baixa_fatura for m in absorvidos
                             if m.baixa_fatura_id]
        if pacote.baixa_fatura_id:
            pacote.baixa_fatura.baixas_empacotadas.add(*[
                b for b in baixas_absorvidas
                if b.pk != pacote.baixa_fatura_id])
        elif baixas_absorvidas:
            # O pacote não tinha baixa: herda a primeira como referência.
            pacote.baixa_fatura = baixas_absorvidas[0]
            pacote.baixa_fatura.baixas_empacotadas.add(*[
                b for b in baixas_absorvidas[1:]
                if b.pk != pacote.baixa_fatura_id])
        # A origem do lançamento único consolida TODAS as baixas de origem
        # (a do pacote + as absorvidas) — preserva a rastreabilidade mesmo
        # depois de os lançamentos individuais saírem.
        if pacote.baixa_fatura_id:
            pacote.origem = pacote.baixa_fatura.descricao_empacotado()
        pacote.us_atualizacao = request.user
        pacote.dt_atualizacao = timezone.now()
        pacote.save()
        # Os lançamentos absorvidos SAEM (ficou o lançamento único).
        for m in absorvidos:
            m.delete()
        self.message_user(
            request,
            f'Lançamentos empacotados no movimento #{pacote.pk}: total '
            f'{total} ({len(absorvidos)} lançamento(s) excluído(s)).',
            level=admin_messages.SUCCESS)

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
        # ORIGEM automática por contexto:
        # - movimento de BAIXA (gerado pelo save() da baixa): a descrição da
        #   baixa/fatura/empacotadas vai na `origem`;
        # - lançamento MANUAL (sem baixa): a `observacao` do usuário é
        #   prefixada de "Lançamento manual" (sem duplicar o prefixo).
        if obj.baixa_fatura_id:
            obj.origem = obj.baixa_fatura.descricao_empacotado()
        else:
            texto = (obj.observacao or '').strip()
            if texto.lower().startswith('lançamento manual'):
                pass  # já prefixado (edição)
            elif texto:
                obj.observacao = f'Lançamento manual – {texto}'
            else:
                obj.observacao = 'Lançamento manual'
        super().save_model(request, obj, form, change)
