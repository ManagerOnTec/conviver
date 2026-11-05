"""
Dashboards e filtros superiores das telas de ADMIN PAGAMENTOS (fluxo de
SAÍDA).

Espelha o `admin_faturas/dashboard.py` (fluxo de ENTRADA). Reaproveita a
barra/grade de KPIs do projeto (`AdminDashboardAndTopFilterMixin`) e
acrescenta o que é específico de contas a pagar:

- presets de período por Competência e Vencimento (mês a mês);
- atalhos de Saldo (em aberto / quitado), finalizado e pré-pago;
- filtro por Fornecedor na própria barra superior;
- KPIs financeiros (valor, em aberto, pago, vencido...).
"""
from datetime import date

from django.contrib import admin
from django.utils import timezone

from dominios.admin_dashboard_mixins import AdminDashboardAndTopFilterMixin


class FornecedorPagadorFilter(admin.SimpleListFilter):
    """Fornecedor das telas de pagamento (o “pagador” do fluxo de saída).

    Funciona nos dois níveis: nos modelos que TÊM `fornecedor` (acordo,
    previsão, pagamento) filtra direto; nos que têm `acordo_pagamento`
    entra pelo acordo. Sempre dentro de `try/except`: filtro inválido não
    pode derrubar a listagem (AGENTS.md, item 9).
    """
    title = 'Fornecedor'
    parameter_name = 'fornecedor_pagador'

    def lookups(self, request, model_admin):
        try:
            from admin_pagamentos.models import Fornecedor
            return [(str(f.pk), f.descricao)
                    for f in Fornecedor.objects.filter(
                        status='A').order_by('descricao')]
        except Exception:
            return []

    def queryset(self, request, queryset):
        try:
            valor = self.value()
            if isinstance(valor, (list, tuple)):
                valor = valor[0] if valor else None
            if not valor:
                return queryset
            model = queryset.model
            campos = {f.name for f in model._meta.get_fields()}
            if 'fornecedor' in campos:
                return queryset.filter(fornecedor_id=valor)
            if 'acordo_pagamento' in campos:
                return queryset.filter(
                    acordo_pagamento__fornecedor_id=valor)
        except Exception:
            return queryset
        return queryset


def _money(valor):
    """Formata em Reais no padrão brasileiro (sem depender do locale)."""
    try:
        valor = float(valor or 0)
    except (TypeError, ValueError):
        valor = 0.0
    inteiro, centavos = f"{valor:,.2f}".split('.')
    return f"R$ {inteiro.replace(',', '.')},{centavos}"


def _qtd(valor):
    return f"{int(valor or 0):,}".replace(',', '.')


class PagamentosDashboardMixin(AdminDashboardAndTopFilterMixin):
    """Base dos admins de pagamentos: competência, vencimento, saldo e flags.

    Mesma estrutura do `FaturasDashboardMixin` — o que muda são os campos
    lidos em cada tela:
    """

    # Campo de competência (base dos presets de mês/ano).
    dashboard_competencia_field = 'competencia'
    # Campo de vencimento (presets de período e KPI “vencidas”).
    dashboard_vencimento_field = 'dt_vencimento'
    # Campos de valor lido nos KPIs.
    dashboard_valor_field = 'valor'
    dashboard_saldo_field = None

    # ------------------------------------------------------------------
    # Utilitários
    # ------------------------------------------------------------------
    @staticmethod
    def _query_params(request):
        params = request.GET.copy()
        params.pop('p', None)  # volta para a 1ª página ao filtrar
        for chave in list(params.keys()):
            if any(valor == '' for valor in params.getlist(chave)):
                params.pop(chave, None)
        return params

    def _url_com(self, request, **mudancas):
        """URL da própria changelist trocando/removendo apenas as chaves dadas
        (``None`` ou ``''`` removem a chave)."""
        params = self._query_params(request)
        for chave, valor in mudancas.items():
            if valor in (None, ''):
                params.pop(chave, None)
            elif isinstance(valor, bool):
                params[chave] = '1' if valor else '0'
            else:
                params[chave] = valor
        qs = params.urlencode()
        return f"{request.path}?{qs}" if qs else request.path

    def _tem_filtro_periodo(self, request):
        return any(chave.startswith((
            f'{self.dashboard_competencia_field}__',
            f'{self.dashboard_vencimento_field}__',
        )) for chave in request.GET.keys())

    # ------------------------------------------------------------------
    # Presets do período (barra superior)
    # ------------------------------------------------------------------
    def get_top_filter_presets(self, request):
        hoje = timezone.localdate()
        ano, mes = hoje.year, hoje.month
        if mes == 1:
            mes_anterior = date(ano - 1, 12, 1)
        else:
            mes_anterior = date(ano, mes - 1, 1)
        if mes == 12:
            mes_proximo = date(ano + 1, 1, 1)
        else:
            mes_proximo = date(ano, mes + 1, 1)

        campo_comp = self.dashboard_competencia_field
        campo_venc = self.dashboard_vencimento_field

        def url_periodo(**filtros):
            params = self._query_params(request)
            for chave in list(params.keys()):
                if chave.startswith((f'{campo_comp}__', f'{campo_venc}__')):
                    params.pop(chave, None)
            params.update(filtros)
            query = params.urlencode()
            return f'{request.path}?{query}' if query else request.path

        def ativo(**filtros):
            return all(request.GET.get(chave) == str(valor)
                       for chave, valor in filtros.items())

        return [
            {'label': 'Todos', 'url': url_periodo(),
             'active': not self._tem_filtro_periodo(request)},
            {'label': f'Competência {mes:02d}/{ano}',
             'url': url_periodo(**{f'{campo_comp}__year': ano,
                                   f'{campo_comp}__month': mes}),
             'active': ativo(**{f'{campo_comp}__year': ano,
                                f'{campo_comp}__month': mes})},
            {'label': 'Competência anterior',
             'url': url_periodo(**{f'{campo_comp}__year': mes_anterior.year,
                                   f'{campo_comp}__month': mes_anterior.month}),
             'active': ativo(**{f'{campo_comp}__year': mes_anterior.year,
                                f'{campo_comp}__month': mes_anterior.month})},
            {'label': f'Venc. {mes:02d}/{ano}',
             'url': url_periodo(**{f'{campo_venc}__year': ano,
                                   f'{campo_venc}__month': mes}),
             'active': ativo(**{f'{campo_venc}__year': ano,
                                f'{campo_venc}__month': mes})},
            {'label': 'Vencidas',
             'url': url_periodo(**{f'{campo_venc}__lt': hoje.isoformat()}),
             'active': request.GET.get(
                 f'{campo_venc}__lt') == hoje.isoformat()},
            {'label': 'A vencer',
             'url': url_periodo(**{f'{campo_venc}__gte': hoje.isoformat()}),
             'active': request.GET.get(
                 f'{campo_venc}__gte') == hoje.isoformat()},
        ]

    # ------------------------------------------------------------------
    # Filtros superiores (atalhos)
    # ------------------------------------------------------------------
    def filtro_todos_status(self, request, parametros=None):
        """Botão “Todos”: limpa SÓ os filtros de estado informados."""
        parametros = ('status', *(parametros or ()))
        filtros_ativos = any(
            request.GET.get(chave) not in (None, '') for chave in parametros
        )
        return {
            'label': 'Todos',
            'url': self._url_com(
                request, **{chave: None for chave in parametros}),
            'active': not filtros_ativos,
            'icon': 'fa-list',
        }

    def get_top_extra_filters(self, request):
        status = request.GET.get('status')
        filtros = [
            self.filtro_todos_status(request),
            {'label': 'Ativos', 'url': self._url_com(request, status='A'),
             'active': status == 'A', 'icon': '✅'},
            {'label': 'Inativos', 'url': self._url_com(request, status='I'),
             'active': status == 'I', 'icon': '🚫'},
        ]

        # Saldo: só as telas que têm o campo (pagamento).
        if self.dashboard_saldo_field:
            filtros += [
                {'label': 'Em aberto',
                 'url': self._url_com(
                     request, **{f'{self.dashboard_saldo_field}__gt': 0}),
                 'active': f'{self.dashboard_saldo_field}__gt' in request.GET,
                 'icon': 'fa-hourglass-half'},
                {'label': 'Quitados',
                 'url': self._url_com(
                     request, **{f'{self.dashboard_saldo_field}__lte': 0}),
                 'active': f'{self.dashboard_saldo_field}__lte' in request.GET,
                 'icon': 'fa-circle-check'},
            ]

        # Flags do próprio modelo.
        if self._modelo_tem_campo('pre_pago'):
            filtros += [
                {'label': 'Pré-Pagos',
                 'url': self._url_com(request, pre_pago='1'),
                 'active': request.GET.get('pre_pago') == '1',
                 'icon': '🧾'},
                {'label': 'Sem Previsão',
                 'url': self._url_com(request, pre_pago='0'),
                 'active': request.GET.get('pre_pago') == '0',
                 'icon': '➕'},
            ]
        if self._modelo_tem_campo('finalizado'):
            filtros += [
                {'label': 'Finalizados',
                 'url': self._url_com(request, finalizado='1'),
                 'active': request.GET.get('finalizado') == '1',
                 'icon': '🧾'},
                {'label': 'Abertos',
                 'url': self._url_com(request, finalizado='0'),
                 'active': request.GET.get('finalizado') == '0',
                 'icon': '➕'},
            ]
        return filtros

    def _modelo_tem_campo(self, nome):
        return any(f.name == nome for f in self.model._meta.get_fields())

    def classe_fornecedor(self, obj):
        """Classe do fornecedor para o `list_display`.

        Fica no MIXIN (e não num admin específico) porque as três telas do
        fluxo mostram a coluna: o nome acompanha o par `classe_pagamento`.
        """
        return obj.fornecedor.classificacao if obj.fornecedor_id else '-'
    classe_fornecedor.short_description = "Classe Fornecedor"
    classe_fornecedor.admin_order_field = 'fornecedor__classificacao'

    # ------------------------------------------------------------------
    # Dropdown do topo: fornecedor
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Lookups LIBERADOS (o Django só aceita traversal de FK por padrão)
    # ------------------------------------------------------------------
    LOOKUPS_LIBERADOS = (
        'fornecedor__classificacao__id__exact',
    )

    def lookup_allowed(self, lookup, value, request=None):
        """Libera a consulta por um campo de FK ANINHADA do fornecedor.

        O Django só deixa passar o lookup de chave estrangeira quando o campo
        base está em `list_filter`/`search_fields` (traversal de 1 nível).
        `fornecedor__classificacao` é de 2 níveis e cairia em
        `DisallowedModelAdminLookup` (tela 400) — o seletor “Classe
        Fornecedor” do topo usa justamente esse look-up, então ele é liberado
        explicitamente aqui.
        """
        if lookup in self.LOOKUPS_LIBERADOS:
            return True
        try:
            return super().lookup_allowed(lookup, value, request)
        except TypeError:
            # Django < 4.1 não recebe o `request`.
            return super().lookup_allowed(lookup, value)

    def get_top_dropdown_subfilters(self, request):
        from admin_pagamentos.models import (
            ClassificacaoFornecedor, ClassePagamento, Fornecedor)

        def opcoes(param, objs, rotulo_vazio, fmt, key=None, default=None):
            atuais = set(filter(None, request.GET.getlist(param)))
            lista = [{
                'label': rotulo_vazio,
                'url': self._url_com(request, **{param: None}),
                'selected': not atuais and not default,
            }]
            vistos = set()
            for obj in objs:
                valor = key(obj) if key is not None else obj.pk
                if valor in vistos:
                    continue
                vistos.add(valor)
                lista.append({
                    'label': fmt(obj),
                    'url': self._url_com(request, **{param: valor}),
                    'selected': (str(valor) in atuais
                                 or (not atuais
                                     and str(valor) == str(default))),
                })
            return lista

        seletores = []

        # FORNECEDOR (o “pagador” do fluxo de saída).
        if self._modelo_tem_campo('fornecedor'):
            fornecedores = Fornecedor.objects.filter(
                status='A').order_by('descricao')
            seletores.append({
                'label': 'Fornecedor',
                'options': opcoes(
                    'fornecedor_pagador', fornecedores,
                    'Todos os fornecedores', lambda f: f.descricao),
            })

        # CLASSE DO FORNECEDOR — NÃO tem campo próprio: é a classificação do
        # `fornecedor` (FK do acordo, que tem a FK `classificacao`). Nos
        # modelos derivados (pré-pagamento/pagamento) o fornecedor também
        # existe, então o look-up `fornecedor__classificacao` vale nos três.
        if self._modelo_tem_campo('fornecedor'):
            param = 'fornecedor__classificacao__id__exact'
            classificacoes = ClassificacaoFornecedor.objects.filter(
                status='A').order_by('descricao')
            seletores.append({
                'label': 'Classe Fornecedor',
                'options': opcoes(
                    param, classificacoes, 'Todas as classes',
                    lambda c: c.descricao),
            })

        # CLASSIFICAÇÃO DO PAGAMENTO (campo próprio no Acordo/Previsão/
        # Pagamento, herdado pelo multitable).
        if self._modelo_tem_campo('classe_pagamento'):
            classificacoes = ClassePagamento.objects.filter(
                status='A').order_by('descricao')
            seletores.append({
                'label': 'Classe Pagamento',
                'options': opcoes(
                    'classe_pagamento__id__exact', classificacoes,
                    'Todas as classes', lambda c: c.descricao),
            })

        # ESTABELECIMENTO — seletor do topo (o mesmo padrão do fluxo de
        # faturas). Lista os estabelecimentos LIBERADOS para o perfil (ou
        # todos, para superuser sem perfil) — o seletor aparece SEMPRE, mesmo
        # com um único liberado: é ali que o usuário vê e troca o recorte.
        if self._modelo_tem_campo('estabelecimento'):
            from admin_cadastros.models import Estabelecimento
            perfil = getattr(request.user, 'perfil', None)
            if perfil is not None:
                estabelecimentos = perfil.estabelecimento.filter(
                    status='A')
                if perfil.estabelecimento_padrao_id:
                    estabelecimentos = (estabelecimentos |
                                        Estabelecimento.objects.filter(
                                            pk=perfil.estabelecimento_padrao_id,
                                            status='A'))
            else:
                estabelecimentos = Estabelecimento.objects.filter(
                    status='A')
            estabelecimentos = estabelecimentos.distinct().order_by(
                'estabelecimento')
            if estabelecimentos.exists():
                # Mesmo parâmetro do fluxo de faturas: o Django resolve
                # `estabelecimento__id__exact` como FILTRO DE CAMPO (a
                # listagem recorta direto); o `EstabelecimentoFilterAdminMixin`
                # (`parameter_name = 'estabelecimento'`) segue como o filtro da
                # barra lateral, aplicando o padrão da sessão quando nada é
                # escolhido aqui.
                atual = (request.GET.get('estabelecimento__id__exact')
                         or request.GET.get('estabelecimento'))
                seletores.append({
                    'label': 'Estabelecimento',
                    'options': opcoes(
                        'estabelecimento__id__exact', estabelecimentos,
                        'Todos os meus', lambda e: str(e),
                        default=atual),
                })

        return seletores

    # ------------------------------------------------------------------
    # KPIs (cada admin sobrescreve com os seus)
    # ------------------------------------------------------------------
    def get_dashboard_kpis(self, request, queryset):
        return [
            {
                'title': 'Registros',
                'value': _qtd(queryset.count()),
                'subtitle': 'No filtro atual',
                'color_class': 'kpi-blue',
                'icon': '📑',
            },
        ]

    def _somas(self, queryset):
        from django.db.models import Count, Sum
        campos = {
            'total': Sum(self.dashboard_valor_field),
            'registros': Count('pk'),
        }
        if self.dashboard_saldo_field:
            campos['saldo'] = Sum(self.dashboard_saldo_field)
        return queryset.aggregate(**campos)

    # ------------------------------------------------------------------
    # Contexto
    # ------------------------------------------------------------------
    @property
    def dashboard_date_field(self):
        return getattr(self, '_dashboard_date_field',
                       self.dashboard_competencia_field or 'dt_registro')

    @dashboard_date_field.setter
    def dashboard_date_field(self, valor):
        self._dashboard_date_field = valor

    top_filter_search_label = 'Busca'
    top_filter_search_placeholder = (
        'Buscar por fornecedor, classificação, nota fiscal...')
    top_extra_filter_label = 'Status & Flags'
