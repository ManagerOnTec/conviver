"""
Dashboards e filtros superiores das telas de ADMIN FATURAS.

Reaproveita a barra/grade de KPIs do projeto (``AdminDashboardAndTopFilterMixin``)
e acrescenta o que é específico do financeiro:

- presets de período baseados em Competência (mês a mês) e Vencimento;
- atalhos de Saldo (em aberto / quitado) e de pré-faturado/faturado;
- filtros por Convênio e Estabelecimento na própria barra superior;
- KPIs financeiros (total, em aberto, recebido, vencido...).

Todos os links preservam os demais parâmetros da URL, então os filtros
superiores convivem com a barra lateral e com a pesquisa.
"""
from datetime import date

from django.utils import timezone
from django.contrib import admin
from dominios.admin_dashboard_mixins import AdminDashboardAndTopFilterMixin
class ConvenioPagadorFilter(admin.SimpleListFilter):
    title = 'Convênio / Pagador'
    parameter_name = 'convenio_pagador'

    def lookups(self, request, model_admin):
        from admin_faturas.models import Convenio
        opcoes = {}
        for convenio in Convenio.objects.filter(status='A').select_related(
                'pagador_pj', 'pagador_pf'):
            if convenio.pagador_pj_id:
                chave = f'pj:{convenio.pagador_pj_id}'
                rotulo = str(convenio.pagador_pj)
            elif convenio.pagador_pf_id:
                chave = f'pf:{convenio.pagador_pf_id}'
                rotulo = str(convenio.pagador_pf)
            else:
                chave = f'convenio:{convenio.pk}'
                rotulo = f'{convenio.convenio} (sem pagador)'
            opcoes.setdefault(chave, rotulo)
        return sorted(opcoes.items(), key=lambda opcao: opcao[1].casefold())

    def queryset(self, request, queryset):
        valor = self.value()
        # O admin entrega o valor como string; a listagem editável usa a
        # mesma lista que o `ChangeList` monta para os filtros laterais.
        if isinstance(valor, (list, tuple)):
            valor = valor[0] if valor else None
        if not valor or not isinstance(valor, str):
            return queryset
        model = queryset.model
        if any(field.name == 'convenio' for field in model._meta.get_fields()):
            campo = model._meta.get_field('convenio')
            caminho = 'convenio' if campo.is_relation else ''
        elif any(field.name == 'fatura' for field in model._meta.get_fields()):
            caminho = 'fatura__convenio'
        else:
            caminho = 'convenio'

        if valor.startswith('pj:'):
            lookup = f'{caminho}__pagador_pj_id' if caminho else 'pagador_pj_id'
            return queryset.filter(**{lookup: valor[3:]}).distinct()
        if valor.startswith('pf:'):
            lookup = f'{caminho}__pagador_pf_id' if caminho else 'pagador_pf_id'
            return queryset.filter(**{lookup: valor[3:]}).distinct()
        if valor.startswith('convenio:'):
            lookup = f'{caminho}__id' if caminho else 'id'
            return queryset.filter(**{lookup: valor.split(':', 1)[1]}).distinct()
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


class FaturasDashboardMixin(AdminDashboardAndTopFilterMixin):
    """Base dos admins de faturas: competência, vencimento, saldo e status."""

    # Campo de competência (base dos presets de mês/ano).
    dashboard_competencia_field = 'competencia'
    # Campo de vencimento (presets de período e KPI "vencidas").
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

    def _presets_periodo(self, request):
        """Presets de Competência + Vencimento (datas com dois campos, que o
        valor do form não consegue representar no calendário do módulo)."""
        hoje = timezone.localdate()
        ano, mes = hoje.year, hoje.month

        periodos = [
            {'label': 'Todos', 'url': self._url_com(request),
             'active': not self._tem_filtro_periodo(request)},
        ]

        # Competência atual e anterior, sempre o mês inteiro.
        opcoes = [(f'Competência {mes:02d}/{ano}', date(ano, mes, 1))]
        if mes == 1:
            opcoes.append(('Competência anterior', date(ano - 1, 12, 1)))
        else:
            opcoes.append(('Competência anterior', date(ano, mes - 1, 1)))

        for rotulo, ref in opcoes:
            campo = self.dashboard_competencia_field
            periodos.append({
                'label': rotulo,
                'url': self._url_com(request, **{
                    f'{campo}__year': ref.year,
                    f'{campo}__month': ref.month,
                }),
                'active': (
                    request.GET.get(f'{campo}__year') == str(ref.year)
                    and request.GET.get(f'{campo}__month') == str(ref.month)
                ),
            })

        campo_venc = self.dashboard_vencimento_field
        periodos += [
            {
                'label': f'Vence {mes:02d}/{ano}',
                'url': self._url_com(request, **{
                    f'{campo_venc}__year': ano,
                    f'{campo_venc}__month': mes,
                }),
                'active': (request.GET.get(f'{campo_venc}__year') == str(ano)
                           and request.GET.get(f'{campo_venc}__month') == str(mes)),
            },
            {
                'label': 'Vencidas',
                'url': self._url_com(request, **{
                    f'{campo_venc}__lt': hoje.isoformat(),
                }),
                'active': f'{campo_venc}__lt' in request.GET,
            },
        ]
        return periodos

    # ------------------------------------------------------------------
    # KPIs
    # ------------------------------------------------------------------
    def _somas(self, queryset):
        from django.db.models import Sum, Count
        campos = {
            'total': Sum(self.dashboard_valor_field),
            'registros': Count('pk'),
        }
        if self.dashboard_saldo_field:
            campos['saldo'] = Sum(self.dashboard_saldo_field)
        return queryset.aggregate(**campos)

    def _tem_filtro_periodo(self, request):
        return any(chave.startswith((
            f'{self.dashboard_competencia_field}__',
            f'{self.dashboard_vencimento_field}__',
        )) for chave in request.GET.keys())

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

    # ------------------------------------------------------------------
    # Filtros superiores
    # ------------------------------------------------------------------
    def filtro_todos_status(self, request, parametros=None):
        # Limpa exclusivamente os filtros de estado, mantendo datas e demais
        # seleções (pagador, estabelecimento, busca) da listagem atual.
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
        status_param = 'status'
        ativo = request.GET.get(status_param) == 'A'

        filtros = [
            self.filtro_todos_status(request),
            {
                'label': 'Somente Ativos',
                'url': self._url_com(request, **{status_param: 'A'}),
                'active': ativo,
                'icon': '✅',
            },
            {
                'label': 'Inativos',
                'url': self._url_com(request, **{status_param: 'I'}),
                'active': request.GET.get(status_param) == 'I',
                'icon': '🚫',
            },
        ]

        # Saldo: só os modelos que têm o campo.
        if self.dashboard_saldo_field:
            filtros += [
                {
                    'label': 'Em Aberto',
                    'url': self._url_com(request, **{f'{self.dashboard_saldo_field}__gt': 0}),
                    'active': f'{self.dashboard_saldo_field}__gt' in request.GET,
                    'icon': '💰',
                },
                {
                    'label': 'Quitadas',
                    'url': self._url_com(request, **{f'{self.dashboard_saldo_field}__lte': 0}),
                    'active': f'{self.dashboard_saldo_field}__lte' in request.GET,
                    'icon': '🏁',
                },
            ]

        return filtros

    def _estabelecimento_padrao_id(self, request):
        perfil = getattr(request.user, 'perfil', None)
        estabelecimento_id = request.session.get('estabelecimento_id')
        if perfil:
            permitidos = perfil.estabelecimento.all()
            if estabelecimento_id and permitidos.filter(pk=estabelecimento_id).exists():
                return str(estabelecimento_id)
            if perfil.estabelecimento_padrao_id:
                return str(perfil.estabelecimento_padrao_id)
        elif estabelecimento_id:
            return str(estabelecimento_id)
        return None
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if (self._modelo_tem_campo('estabelecimento')
                and 'estabelecimento__id__exact' not in request.GET):
            estabelecimento_id = self._estabelecimento_padrao_id(request)
            if estabelecimento_id:
                queryset = queryset.filter(estabelecimento_id=estabelecimento_id)

        convenio_filtro = request.GET.get('convenio_pagador')
        if convenio_filtro:
            if self._modelo_tem_campo('convenio'):
                relation = self.model._meta.get_field('convenio')
                caminho = 'convenio' if relation.is_relation else ''
            elif self._modelo_tem_campo('fatura'):
                caminho = 'fatura__convenio'
            else:
                caminho = 'convenio'
            campo_pj = f'{caminho}__pagador_pj_id' if caminho else 'pagador_pj_id'
            campo_pf = f'{caminho}__pagador_pf_id' if caminho else 'pagador_pf_id'
            campo_id = f'{caminho}__id' if caminho else 'id'
            if convenio_filtro.startswith('pj:'):
                queryset = queryset.filter(**{campo_pj: convenio_filtro[3:]})
            elif convenio_filtro.startswith('pf:'):
                queryset = queryset.filter(**{campo_pf: convenio_filtro[3:]})
            elif convenio_filtro.startswith('convenio:'):
                queryset = queryset.filter(
                    **{campo_id: convenio_filtro.split(':', 1)[1]})
            queryset = queryset.distinct()
        return queryset
    def get_top_dropdown_subfilters(self, request):
        """Selects da barra superior: Convênio (do Convênio e/ou da Fatura) e
        flags booleanas do próprio modelo."""
        seletores = []

        def opcoes(param, objs, rotulo_vazio, fmt, default=None, key=None):
            atuais = set(filter(None, request.GET.getlist(param)))
            lista = [{
                'label': rotulo_vazio,
                'url': self._url_com(request, **{param: None}),
                'selected': not atuais and not default,
            }]
            vistos = set()
            for obj in objs:
                valor = key(obj) if key else obj.pk
                if valor in vistos:
                    continue
                vistos.add(valor)
                lista.append({
                    'label': fmt(obj),
                    'url': self._url_com(request, **{param: valor}),
                    'selected': (
                        str(valor) in atuais
                        or not atuais and str(valor) == str(default)
                    ),
                })
            return lista
        def pagadores():
            from admin_faturas.models import Convenio
            grupos = {}
            for convenio in Convenio.objects.filter(status='A').select_related(
                    'pagador_pj', 'pagador_pf'):
                if convenio.pagador_pj_id:
                    chave = f'pj:{convenio.pagador_pj_id}'
                    rotulo = str(convenio.pagador_pj)
                elif convenio.pagador_pf_id:
                    chave = f'pf:{convenio.pagador_pf_id}'
                    rotulo = str(convenio.pagador_pf)
                else:
                    chave = f'convenio:{convenio.pk}'
                    rotulo = f'{convenio.convenio} (sem pagador)'
                grupos.setdefault(chave, rotulo)
            return sorted(grupos.items(), key=lambda item: item[1].casefold())

        if (self._modelo_tem_campo('convenio')
                or self._modelo_tem_campo('fatura')):
            seletores.append({
                'label': 'Convênio / Pagador',
                'options': opcoes(
                    'convenio_pagador', pagadores(), 'Todos os pagadores',
                    lambda item: item[1], key=lambda item: item[0]),
            })

        try:
            from admin_cadastros.models import Estabelecimento
            perfil = getattr(request.user, 'perfil', None)
            if perfil:
                estabelecimentos = perfil.estabelecimento.filter(
                    status='A').order_by('estabelecimento')
                if perfil.estabelecimento_padrao_id:
                    estabelecimentos = estabelecimentos | Estabelecimento.objects.filter(
                        pk=perfil.estabelecimento_padrao_id, status='A')
                    estabelecimentos = estabelecimentos.distinct().order_by(
                        'estabelecimento')
            else:
                estabelecimentos = Estabelecimento.objects.filter(
                    status='A').order_by('estabelecimento')
            estabelecimento_padrao = self._estabelecimento_padrao_id(request)
            seletores.append({
                'label': 'Estabelecimento',
                'options': opcoes(
                    'estabelecimento__id__exact', estabelecimentos,
                    'Todos os estabelecimentos',
                    lambda e: e.estabelecimento,
                    default=estabelecimento_padrao),
            })
        except Exception:
            pass

        # O filtro já existente na barra lateral dispensa o select duplicado.
        for seletor in seletores:
            if seletor['label'] == 'Convênio da Fatura':
                seletor['options'] = [o for o in seletor['options']
                                      if o['label'] != 'Todos os convênios']

        # Flags booleanas do modelo (ex.: 'faturado' na Fatura) viram um
        # select Sim/Não. 'pre_faturado' fica de fora: já são botões.
        for campo, rotulo in (('faturado', 'Faturado'),):
            if not self._modelo_tem_campo(campo):
                continue
            atual = request.GET.get(campo)
            seletores.append({
                'label': rotulo,
                'options': [
                    {'label': 'Todos', 'url': self._url_com(request, **{campo: None}),
                     'selected': not atual},
                    {'label': 'Sim', 'url': self._url_com(request, **{campo: '1'}),
                     'selected': atual == '1'},
                    {'label': 'Não', 'url': self._url_com(request, **{campo: '0'}),
                     'selected': atual == '0'},
                ],
            })

        return seletores

    def _modelo_tem_campo(self, nome):
        return any(f.name == nome for f in self.model._meta.get_fields())

    def get_top_extra_filters(self, request):
        filtros = super().get_top_extra_filters(request)
        # Campos booleanos viram atalhos com rótulo próprio (o genérico
        # “Status” não descreve bem “Pré-faturado” / “Faturado”).
        if self._modelo_tem_campo('pre_faturado'):
            filtros += [
                {'label': 'Pré-Faturados',
                 'url': self._url_com(request, pre_faturado='1'),
                 'active': request.GET.get('pre_faturado') == '1',
                 'icon': '🧾'},
                {'label': 'Sem Pré-Fatura',
                 'url': self._url_com(request, pre_faturado='0'),
                 'active': request.GET.get('pre_faturado') == '0',
                 'icon': '➕'},
            ]
        if self._modelo_tem_campo('faturado') and getattr(
                self, 'dashboard_enable_faturado_shortcuts', True):
            filtros += [
                {'label': 'Faturadas',
                 'url': self._url_com(request, faturado='1'),
                 'active': request.GET.get('faturado') == '1',
                 'icon': '🧾'},
                {'label': 'A Faturar',
                 'url': self._url_com(request, faturado='0'),
                 'active': request.GET.get('faturado') == '0',
                 'icon': '➕'},
            ]
        return filtros

    # ------------------------------------------------------------------
    # Contexto
    # ------------------------------------------------------------------
    def get_top_filter_presets(self, request):
        return self._presets_periodo(request)

    # O mixin base olha o campo de data do período; aqui usamos competência.
    @property
    def dashboard_date_field(self):
        return getattr(self, '_dashboard_date_field',
                       self.dashboard_competencia_field or 'dt_registro')

    @dashboard_date_field.setter
    def dashboard_date_field(self, valor):
        self._dashboard_date_field = valor

    # Rótulos da barra superior no contexto financeiro.
    top_filter_search_label = 'Busca'
    top_filter_search_placeholder = (
        'Buscar por convênio, cliente, contrato, empenho, NF...')
    top_extra_filter_label = 'Status & Flags'
