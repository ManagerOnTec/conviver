from io import BytesIO
from types import SimpleNamespace
from zipfile import ZipFile

from django.test import RequestFactory, SimpleTestCase
from django.db import models
from openpyxl import load_workbook

from admin_financeiro.models import MovimentoBancario
from admin_faturas.dashboard import FaturasDashboardMixin
from admin_faturas.models import (
    AcordoFaturamento, BaixaFatura, Fatura, PreFatura,
)
from admin_pagamentos.dashboard import PagamentosDashboardMixin
from admin_pagamentos.models import (
    AcordoPagamento, BaixaPagamento, Pagamento, PrePagamento,
)
from dominios.admin_dashboard_mixins import AdminDashboardAndTopFilterMixin
from dominios.utils import ExportToXLSWithAttachmentsMixin


class StorageStub:
    def __init__(self, files):
        self.files = files

    def open(self, name, mode):
        return BytesIO(self.files[name])


class ExportXLSAnexosTests(SimpleTestCase):
    class Exporter(ExportToXLSWithAttachmentsMixin):
        model = Pagamento
        export_xls_attachment_fields = (
            'anexo_nota_fiscal', 'anexo_boleto',
        )

        def message_user(self, request, message, level=None):
            raise AssertionError(message)

    class FaturaExporter(ExportToXLSWithAttachmentsMixin):
        model = Fatura
        export_xls_attachment_fields = ('anexo_nf',)

        def message_user(self, request, message, level=None):
            raise AssertionError(message)

    def _registro(self, pk, files):
        storage = StorageStub(files)
        campos = {field.name: '' for field in Pagamento._meta.fields}
        campos.update({
            'pk': pk,
            'anexo_nota_fiscal': SimpleNamespace(
                name='docs/nota.xml', storage=storage)
                if 'docs/nota.xml' in files else '',
            'anexo_boleto': SimpleNamespace(
                name='docs/boleto.pdf', storage=storage)
                if 'docs/boleto.pdf' in files else '',
        })
        return SimpleNamespace(**campos)

    def test_planilha_zip_tem_links_para_todos_os_anexos(self):
        registro = self._registro(41, {
            'docs/nota.xml': b'conteudo XML',
            'docs/boleto.pdf': b'conteudo boleto',
        })
        request = SimpleNamespace(get_full_path=lambda: '/admin/')

        resposta = self.Exporter().export_as_xls(request, [registro])

        self.assertEqual(resposta['Content-Type'], 'application/zip')
        with ZipFile(BytesIO(resposta.content)) as pacote:
            nome_planilha = next(
                nome for nome in pacote.namelist()
                if nome.endswith('.xlsx'))
            planilha = load_workbook(BytesIO(pacote.read(nome_planilha)))
            ws = planilha.active
            colunas = {
                cell.value: cell.column
                for cell in ws[1]
            }
            for campo, caminho in (
                    ('anexo_nota_fiscal', 'anexos/anexo_nota_fiscal/41.xml'),
                    ('anexo_boleto', 'anexos/anexo_boleto/41.pdf')):
                titulo = Pagamento._meta.get_field(
                    campo).verbose_name.title()
                celula = ws.cell(row=2, column=colunas[titulo])
                self.assertEqual(celula.value, 'Abrir anexo')
                self.assertEqual(celula.hyperlink.target, caminho)
                self.assertTrue(celula.hyperlink.tooltip)
                self.assertIn(caminho, pacote.namelist())
            self.assertEqual(
                pacote.read('anexos/anexo_nota_fiscal/41.xml'),
                b'conteudo XML')
            self.assertEqual(
                pacote.read('anexos/anexo_boleto/41.pdf'),
                b'conteudo boleto')

    def test_sem_anexos_preserva_exportacao_xlsx_existente(self):
        registro = self._registro(42, {})
        request = SimpleNamespace(get_full_path=lambda: '/admin/')

        resposta = self.Exporter().export_as_xls(request, [registro])

        self.assertEqual(
            resposta['Content-Type'],
            'application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.sheet')

    def test_exportacao_fatura_inclui_anexo_nf(self):
        caminho = 'docs/fatura.pdf'
        campos = {field.name: '' for field in Fatura._meta.fields}
        campos.update({
            'pk': 51,
            'anexo_nf': SimpleNamespace(
                name=caminho,
                storage=StorageStub({caminho: b'conteudo NF'})),
        })
        request = SimpleNamespace(get_full_path=lambda: '/admin/')

        resposta = self.FaturaExporter().export_as_xls(
            request, [SimpleNamespace(**campos)])

        self.assertEqual(resposta['Content-Type'], 'application/zip')
        with ZipFile(BytesIO(resposta.content)) as pacote:
            caminho_zip = 'anexos/anexo_nf/51.pdf'
            self.assertEqual(pacote.read(caminho_zip), b'conteudo NF')
            nome_planilha = next(
                nome for nome in pacote.namelist()
                if nome.endswith('.xlsx'))
            ws = load_workbook(
                BytesIO(pacote.read(nome_planilha))).active
            coluna_nf = next(
                cell.column for cell in ws[1]
                if cell.value == Fatura._meta.get_field(
                    'anexo_nf').verbose_name.title())
            self.assertEqual(
                ws.cell(row=2, column=coluna_nf).hyperlink.target,
                caminho_zip)


class FiltroSuperiorDeDatasTests(SimpleTestCase):
    class MovimentoDashboard(AdminDashboardAndTopFilterMixin):
        model = MovimentoBancario
        dashboard_date_field = 'dt_movimento'
        dashboard_date_filter_fields = '__all__'

    def test_oferece_campos_de_data_e_aplica_lookup_de_data_inteira(self):
        dashboard = self.MovimentoDashboard()
        fields = dashboard.get_top_date_filter_fields()
        fields_by_name = {field['name']: field for field in fields}

        self.assertIn('dt_movimento', fields_by_name)
        self.assertIn('dt_registro', fields_by_name)
        self.assertIn('dt_atualizacao', fields_by_name)
        self.assertEqual(
            fields_by_name['dt_movimento']['gte_key'],
            'dt_movimento__gte')
        self.assertEqual(
            fields_by_name['dt_registro']['gte_key'],
            'dt_registro__date__gte')
        queryset = MovimentoBancario.objects.filter(
            **{fields_by_name['dt_registro']['gte_key']: '2025-02-01'})
        sql, params = queryset.query.sql_with_params()
        self.assertIn('dt_registro', sql)
        self.assertIn('2025-02-01', params)

        request = RequestFactory().get(
            '/', {'dt_atualizacao__date__gte': '2025-02-01'})
        selected = dashboard.get_selected_top_date_filter_field(
            request, fields)

        self.assertEqual(selected['name'], 'dt_atualizacao')
        self.assertIn(
            'dt_atualizacao__date__lte',
            dashboard.get_top_date_filter_range_keys(fields))

    def test_telas_financeiras_incluem_todos_os_campos_de_data_do_modelo(self):
        modelos = (
            (FaturasDashboardMixin, AcordoFaturamento),
            (FaturasDashboardMixin, PreFatura),
            (FaturasDashboardMixin, Fatura),
            (FaturasDashboardMixin, BaixaFatura),
            (PagamentosDashboardMixin, AcordoPagamento),
            (PagamentosDashboardMixin, PrePagamento),
            (PagamentosDashboardMixin, Pagamento),
            (PagamentosDashboardMixin, BaixaPagamento),
        )
        for dashboard_mixin, model in modelos:
            with self.subTest(model=model.__name__):
                dashboard_class = type(
                    f'{model.__name__}Dashboard',
                    (dashboard_mixin,),
                    {'model': model},
                )
                fields = {
                    field['name']
                    for field in dashboard_class().get_top_date_filter_fields()
                }
                expected = {
                    field.name for field in model._meta.fields
                    if isinstance(field, models.DateField)
                }
                self.assertEqual(fields, expected)
