from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

from django.contrib import admin
from django.test import RequestFactory, SimpleTestCase

from .admin import FaturaAdmin, SaldoFilter
from .importacao import AcordoImportRowForm
from .models import Fatura


class FaturaAnexoListDisplayTests(SimpleTestCase):
    def setUp(self):
        self.fatura_admin = FaturaAdmin(Fatura, admin.site)

    def test_fatura_finalizada_sem_anexo_mostra_acao_anexar(self):
        fatura = SimpleNamespace(
            pk=123,
            faturado=True,
            anexo_nf='',
        )

        link = str(self.fatura_admin.anexo_nf_link(fatura))

        self.assertIn('Anexar NF', link)
        self.assertIn('/123/anexo-nf/', link)

    def test_fatura_com_anexo_mostra_link_ver_nf(self):
        fatura = SimpleNamespace(
            pk=123,
            anexo_nf=SimpleNamespace(
                name='anexos/nf/2026/11/nota.pdf',
                url='/media/anexos/nf/2026/11/nota.pdf'),
        )

        link = str(self.fatura_admin.anexo_nf_link(fatura))

        self.assertIn('Ver NF', link)
        self.assertIn('target="_blank"', link)


class FaturaSaldoFilterTests(SimpleTestCase):
    def setUp(self):
        self.fatura_admin = FaturaAdmin(Fatura, admin.site)
        self.request_factory = RequestFactory()

    def test_sem_filtro_de_saldo_mantem_todas_as_faturas(self):
        request = self.request_factory.get('/admin/admin_faturas/fatura/')
        filtro = SaldoFilter(request, {}, Fatura, self.fatura_admin)
        queryset = Mock()

        resultado = filtro.queryset(request, queryset)

        self.assertIs(resultado, queryset)
        queryset.filter.assert_not_called()

    def test_filtro_de_saldo_positivo_aplica_o_recorte_solicitado(self):
        request = self.request_factory.get(
            '/admin/admin_faturas/fatura/', {'saldo': 'positive'})
        filtro = SaldoFilter(
            request, {'saldo': 'positive'}, Fatura, self.fatura_admin)
        queryset = Mock()

        resultado = filtro.queryset(request, queryset)

        queryset.filter.assert_called_once_with(valor_saldo__gt=0)
        self.assertIs(resultado, queryset.filter.return_value)


class AcordoImportRowFormTests(SimpleTestCase):
    def test_modalidade_padrao_e_convenio(self):
        form = AcordoImportRowForm()

        self.assertEqual(form['modo_fatura'].value(), 'CO')

    def test_revisao_normaliza_cnpj_e_aceita_modalidade_convenio(self):
        form = AcordoImportRowForm(data={
            'cidade': 'Itajaí',
            'cidade_rotulo': 'Itajaí - Saúde',
            'cnpj': '11.222.333/0001-44',
            'acordo_faturamento': 'Itajaí / CT 628',
            'nr_contrato': '628/2020',
            'nr_aditivo': '',
            'empenho_global': '2026NE000001',
            'inicio_vigencia': '2026-01-01',
            'final_vigencia': '2026-12-31',
            'dia_envio': '1',
            'dias_pagamento': '30',
            'valor_mensal': '100.00',
            'valor_diaria': '0.00',
            'modo_fatura': 'CO',
            'modalidade_contrato': 'CO',
            'descricao_internacao': 'acolhimento',
            'tx_retencao_nf': '0.00',
            'vl_retencao_nf': '0.00',
            'clientes': 'Maria da Silva | 05/06/2000\nJoão Souza',
        })

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['cnpj'], '11222333000144')
        self.assertEqual(form.cleaned_data['modo_fatura'], 'CO')
        self.assertEqual(form.cleaned_data['clientes'], [
            {'nome': 'Maria da Silva', 'nascimento': date(2000, 6, 5)},
            {'nome': 'João Souza', 'nascimento': None},
        ])

    def test_lista_de_clientes_vazia_permite_excluir_todos(self):
        form = AcordoImportRowForm(data={'clientes': ''})

        form.full_clean()

        self.assertEqual(form.cleaned_data['clientes'], [])
