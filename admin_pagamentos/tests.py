from datetime import date
from io import BytesIO
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from openpyxl import Workbook

from .importacao import (
    PagamentoImportRowForm, UploadPagamentoForm, _ler_arquivo,
    _classe_mais_frequente_por_fornecedor, _ler_planilha, _ler_xml,
    _registro_pdf,
)


class PagamentoImportacaoTests(SimpleTestCase):
    def test_campos_de_data_exibem_valores_no_formato_html_date(self):
        form = PagamentoImportRowForm(initial={
            'competencia': date(2026, 11, 24),
            'vencimento': date(2026, 12, 10),
        })

        self.assertIn('value="2026-11-24"', str(form['competencia']))
        self.assertIn('value="2026-12-10"', str(form['vencimento']))

    def test_formulario_aceita_xml_para_importacao_xml(self):
        arquivo = SimpleUploadedFile('nota.XML', b'<nfe/>')
        form = UploadPagamentoForm(
            {'tipo_arquivo': 'xml'}, {'arquivo': arquivo})

        self.assertTrue(form.is_valid(), form.errors)

    @patch('admin_pagamentos.importacao._categoria_no_texto', return_value='')
    def test_importa_dados_de_nfe_xml_namespaceado(self, _categoria):
        conteudo = b'''<?xml version="1.0" encoding="UTF-8"?>
        <nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
          <NFe><infNFe>
            <ide><natOp>VENDA</natOp><nNF>327</nNF>
              <dhEmi>2026-11-18T23:30:00-03:00</dhEmi></ide>
            <emit><CNPJ>82873068000140</CNPJ>
              <xNome>Fornecedor Exemplo Ltda</xNome></emit>
            <dest><xNome>Estabelecimento Exemplo</xNome></dest>
            <cobr><dup><dVenc>2026-12-09</dVenc></dup></cobr>
            <total><ICMSTot><vNF>1770.70</vNF></ICMSTot></total>
          </infNFe></NFe></nfeProc>'''

        registro = _ler_xml(conteudo, 'nota.xml')[0]

        self.assertEqual(registro['fornecedor_nome'], 'Fornecedor Exemplo Ltda')
        self.assertEqual(registro['cnpj'], '82873068000140')
        self.assertEqual(registro['empresa_origem'], 'Estabelecimento Exemplo')
        self.assertEqual(registro['valor'], '1770.70')
        self.assertEqual(registro['data'], '2026-12-09')
        self.assertEqual(registro['observacao'], 'Nota Fiscal 327 - VENDA')
        self.assertEqual(_ler_arquivo('xml', conteudo, 'nota.xml'), [registro])

    def test_recusa_xml_com_declaracao_de_entidade(self):
        conteudo = b'''<!DOCTYPE nfe [<!ENTITY x "valor">]>
        <nfeProc><NFe><infNFe /></NFe></nfeProc>'''

        with self.assertRaisesMessage(ValidationError, 'DTD/ENTITY'):
            _ler_xml(conteudo, 'nota.xml')

    @patch('admin_pagamentos.importacao._categoria_no_texto', return_value='')
    def test_extrai_boleto_e_nota_fiscal_pdf(self, _categoria):
        boleto = _registro_pdf(
            'boleto',
            'Beneficiário CPF/CNPJ\n'
            'CAIXA ECONOMICA FEDERAL 00.360.305/0001-04\n'
            'Valor do Documento\nR$ 2.267,57\n'
            'Vencimento\n13/11/2026\n',
            'boleto.pdf')
        nota = _registro_pdf(
            'nota_fiscal',
            'RECEBEMOS DE CARLOS EDUARDO DE FREITAS,\n'
            'OS PRODUTOS CONSTANTES DA NOTA FISCAL\n'
            'CNPJ 11.758.933/0001-69\n'
            'VALOR TOTAL DA NOTA\n460,00\n'
            'DATA DA EMISSÃO 20/11/2026\nNº 114\n',
            'nota.pdf')

        self.assertEqual(boleto['fornecedor_nome'],
                         'CAIXA ECONOMICA FEDERAL')
        self.assertEqual(boleto['valor'], '2267.57')
        self.assertEqual(boleto['data'], '2026-11-13')
        self.assertEqual(nota['fornecedor_nome'],
                         'CARLOS EDUARDO DE FREITAS')
        self.assertEqual(nota['cnpj'], '11758933000169')
        self.assertEqual(nota['valor'], '460.00')
        self.assertEqual(nota['observacao'], 'Nota Fiscal 114')

    def test_ler_planilha_excel_com_datas_e_valores(self):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = 'JANEIRO 26'
        worksheet.append(['FORNECEDORES', 'DATA', 'VALOR', 'CONTA'])
        worksheet.append(['Fornecedor Exemplo', '18/11/2026', '1.234,56',
                          'Material'])
        arquivo = BytesIO()
        workbook.save(arquivo)

        resultado = _ler_planilha(arquivo.getvalue())

        registro = resultado['JANEIRO 26'][0]
        self.assertEqual(registro['fornecedor_nome'], 'Fornecedor Exemplo')
        self.assertEqual(registro['valor'], '1234.56')
        self.assertEqual(registro['categoria'], 'Material')
        self.assertEqual(registro['data'], '2026-11-18')
        self.assertEqual(registro['competencia'], '2026-11-18')
        self.assertEqual(registro['vencimento'], '2026-11-18')

    def test_sugere_classe_de_pagamento_mais_frequente_para_fornecedor(self):
        registros = [
            {'grupo_fornecedor': 0, 'categoria': 'Alimentação'},
            {'grupo_fornecedor': 0, 'categoria': 'Limpeza'},
            {'grupo_fornecedor': 0, 'categoria': 'ALIMENTACAO'},
            {'grupo_fornecedor': 1, 'categoria': 'Transporte'},
        ]

        sugestao, empate = _classe_mais_frequente_por_fornecedor(
            registros, 0)

        self.assertEqual(sugestao, 'Alimentação')
        self.assertFalse(empate)

    def test_empate_de_classes_mantem_sugestao_para_revisao(self):
        registros = [
            {'grupo_fornecedor': 0, 'categoria': 'Alimentação'},
            {'grupo_fornecedor': 0, 'categoria': 'Limpeza'},
            {'grupo_fornecedor': 0, 'categoria': 'Limpeza'},
            {'grupo_fornecedor': 0, 'categoria': 'Alimentação'},
        ]

        sugestao, empate = _classe_mais_frequente_por_fornecedor(
            registros, 0)

        self.assertEqual(sugestao, 'Alimentação')
        self.assertTrue(empate)

    def test_vencimento_e_competencia_excel_com_fallback(self):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append([
            'FORNECEDOR', 'DATA', 'VENCIMENTO', 'COMPETÊNCIA', 'VALOR'])
        worksheet.append([
            'Fornecedor A', '01/11/2026', '10/12/2026', None, '100,00'])
        worksheet.append([
            'Fornecedor B', None, '31/12/2026', '01/11/2026', '200,00'])
        arquivo = BytesIO()
        workbook.save(arquivo)

        registros = _ler_planilha(arquivo.getvalue())['Sheet']

        self.assertEqual(registros[0]['vencimento'], '2026-12-10')
        self.assertEqual(registros[0]['competencia'], '2026-12-10')
        self.assertEqual(registros[1]['vencimento'], '2026-12-31')
        self.assertEqual(registros[1]['competencia'], '2026-11-01')
