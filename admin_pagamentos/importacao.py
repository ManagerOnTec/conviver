"""Importação revisável de pagamentos a partir de PDFs, XML e planilhas."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
import logging
import re
import unicodedata
import xml.etree.ElementTree as ET
from uuid import uuid4
from zipfile import BadZipFile

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import IntegrityError, transaction
from django.forms import formset_factory
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

import pdfplumber
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from pdfplumber.utils.exceptions import PdfminerException

from admin_cadastros.models import Empresa, Estabelecimento
from admin_pagamentos.models import (
    ClassePagamento, ClassificacaoFornecedor, Fornecedor, Pagamento,
    PrePagamento,
)
from dominios.choices import forma_pagamento_choices


logger = logging.getLogger(__name__)

SESSION_KEY = 'importacoes_pagamentos'
TEMP_PREFIX = 'pagamentos/importacoes/'
FORMATO_CHOICES = (
    ('boleto', 'Boleto (PDF)'),
    ('nota_fiscal', 'Nota Fiscal (PDF)'),
    ('xml', 'Nota Fiscal (XML)'),
    ('excel', 'Planilha Excel (.xlsx)'),
)


class UploadPagamentoForm(forms.Form):
    tipo_arquivo = forms.ChoiceField(
        label='Tipo de importação', choices=FORMATO_CHOICES,
        initial='boleto')
    arquivo = forms.FileField(
        label='Arquivo',
        help_text='Selecione um PDF, XML de NF-e ou uma planilha .xlsx.')

    def clean_arquivo(self):
        arquivo = self.cleaned_data['arquivo']
        tipo = self.data.get('tipo_arquivo', 'boleto')
        extensao = arquivo.name.rsplit('.', 1)[-1].lower() \
            if '.' in arquivo.name else ''
        esperado = {
            'excel': 'xlsx',
            'xml': 'xml',
        }.get(tipo, 'pdf')
        if extensao != esperado:
            raise ValidationError(
                f'Para este tipo de importação, selecione um arquivo .{esperado}.')
        if tipo == 'excel' and arquivo.size == 0:
            raise ValidationError('A planilha está vazia.')
        return arquivo


class PagamentoImportRowForm(forms.Form):
    origem = forms.CharField(widget=forms.HiddenInput)
    grupo_fornecedor = forms.IntegerField(widget=forms.HiddenInput)
    grupo_classe = forms.IntegerField(widget=forms.HiddenInput)
    grupo_estabelecimento = forms.IntegerField(widget=forms.HiddenInput)
    incluir = forms.BooleanField(
        label='Importar', required=False, initial=True)
    competencia = forms.DateField(
        label='Competência',
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}))
    vencimento = forms.DateField(
        label='Vencimento',
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}))
    valor = forms.DecimalField(
        label='Valor', max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    forma_pagamento = forms.ChoiceField(
        label='Forma', choices=forma_pagamento_choices, initial='B')
    observacao = forms.CharField(
        label='Observação', max_length=100, required=False)


class MapeamentoPagamentoForm(forms.Form):
    """FKs resolvidas no preview; as listas ficam restritas ao usuário."""

    def __init__(
        self, *args, fornecedores, classificacoes, classes_pagamento,
        estabelecimentos, grupos_fornecedor, grupos_classe, grupos_estabelecimento,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        fornecedor_qs = Fornecedor.objects.select_related(
            'empresa', 'classificacao').all()
        classificacao_qs = ClassificacaoFornecedor.objects.all()
        classe_qs = ClassePagamento.objects.all()
        estabelecimento_qs = estabelecimentos

        self.fornecedor_groups = []
        for grupo in grupos_fornecedor:
            indice = grupo['indice']
            prefixo = f'fornecedor_{indice}'
            campo_fornecedor = forms.ModelChoiceField(
                label='Fornecedor existente', queryset=fornecedor_qs,
                required=False, empty_label='Criar/associar fornecedor')
            campo_fornecedor.initial = grupo['fornecedor_sugerido']
            campo_nome = forms.CharField(
                label='Nome do fornecedor', max_length=255,
                required=False, initial=grupo['nome'])
            campo_cnpj = forms.CharField(
                label='CNPJ', max_length=18, required=False,
                initial=grupo['cnpj'])
            campo_classificacao = forms.ModelChoiceField(
                label='Classificação do fornecedor',
                queryset=classificacao_qs, required=False,
                empty_label='Criar classificação abaixo')
            campo_classificacao.initial = grupo['classificacao_sugerida']
            campo_nova_classificacao = forms.CharField(
                label='Nova classificação (se necessário)', max_length=255,
                required=False,
                initial=grupo['nova_classificacao_sugerida'])
            self.fields[f'{prefixo}_obj'] = campo_fornecedor
            self.fields[f'{prefixo}_nome'] = campo_nome
            self.fields[f'{prefixo}_cnpj'] = campo_cnpj
            self.fields[f'{prefixo}_classificacao'] = campo_classificacao
            self.fields[f'{prefixo}_nova_classificacao'] = \
                campo_nova_classificacao
            grupo['fields'] = [
                self[f'{prefixo}_obj'], self[f'{prefixo}_nome'],
                self[f'{prefixo}_cnpj'], self[f'{prefixo}_classificacao'],
                self[f'{prefixo}_nova_classificacao'],
            ]
            self.fornecedor_groups.append(grupo)

        self.classe_groups = []
        for grupo in grupos_classe:
            indice = grupo['indice']
            prefixo = f'classe_{indice}'
            campo_classe = forms.ModelChoiceField(
                label='Classe de pagamento', queryset=classe_qs,
                required=False, empty_label='Criar/usar o nome detectado')
            campo_classe.initial = grupo['classe_sugerida']
            campo_nova_classe = forms.CharField(
                label='Nova classe (se necessário)', max_length=255,
                required=False,
                initial='' if grupo['classe_sugerida'] else grupo['nome'])
            self.fields[f'{prefixo}_obj'] = campo_classe
            self.fields[f'{prefixo}_nova'] = campo_nova_classe
            grupo['fields'] = [
                self[f'{prefixo}_obj'], self[f'{prefixo}_nova']]
            self.classe_groups.append(grupo)

        self.estabelecimento_groups = []
        for grupo in grupos_estabelecimento:
            indice = grupo['indice']
            nome = f'estabelecimento_{indice}'
            campo = forms.ModelChoiceField(
                label='Estabelecimento', queryset=estabelecimento_qs,
                required=True)
            campo.initial = grupo['estabelecimento_sugerido']
            self.fields[nome] = campo
            grupo['field'] = self[nome]
            self.estabelecimento_groups.append(grupo)

    def clean(self):
        dados = super().clean()
        fornecedores_ativos = getattr(self, 'fornecedores_ativos', None)
        for grupo in self.fornecedor_groups:
            if fornecedores_ativos is not None and \
                    grupo['indice'] not in fornecedores_ativos:
                continue
            prefixo = f"fornecedor_{grupo['indice']}"
            fornecedor = dados.get(f'{prefixo}_obj')
            nome = (dados.get(f'{prefixo}_nome') or '').strip()
            cnpj = _normalizar_cnpj(dados.get(f'{prefixo}_cnpj') or '')
            classificacao = dados.get(f'{prefixo}_classificacao')
            nova_classificacao = (
                dados.get(f'{prefixo}_nova_classificacao') or '').strip()
            if not fornecedor and not nome:
                self.add_error(
                    f'{prefixo}_nome',
                    'Informe o nome ou selecione um fornecedor existente.')
            if cnpj and len(cnpj) != 14:
                self.add_error(
                    f'{prefixo}_cnpj', 'Informe um CNPJ válido com 14 dígitos.')
            if not fornecedor and not classificacao and not nova_classificacao:
                self.add_error(
                    f'{prefixo}_nova_classificacao',
                    'Selecione uma classificação ou informe uma nova.')
            if fornecedor and cnpj:
                cnpj_atual = _normalizar_cnpj(
                    fornecedor.empresa.cnpj if fornecedor.empresa_id else '')
                if cnpj_atual and cnpj_atual != cnpj:
                    self.add_error(
                        f'{prefixo}_obj',
                        'O CNPJ do fornecedor selecionado não corresponde '
                        'ao CNPJ do documento.')
        return dados


class PagamentoImportSheetForm(forms.Form):
    abas = forms.MultipleChoiceField(
        label='Abas a importar', choices=(), widget=forms.CheckboxSelectMultiple,
        required=True, error_messages={
            'required': 'Selecione pelo menos uma aba para revisar.'})


PagamentoImportRowFormSet = formset_factory(
    PagamentoImportRowForm, extra=0)


def _normalizar(texto):
    texto = unicodedata.normalize('NFKD', str(texto or ''))
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return ' '.join(texto.upper().split())


def _normalizar_cnpj(texto):
    return re.sub(r'\D', '', str(texto or ''))


def _data(valor):
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor or '').strip()
    for formato in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def _decimal(valor):
    if isinstance(valor, Decimal):
        resultado = valor
    elif isinstance(valor, (int, float)):
        resultado = Decimal(str(valor))
    else:
        texto = str(valor or '').strip().replace('R$', '').replace(' ', '')
        if ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        try:
            resultado = Decimal(texto)
        except InvalidOperation:
            return None
    return resultado.quantize(Decimal('0.01'))


def _dinheiros(texto):
    return re.findall(r'(?<!\d)(?:R\$\s*)?(\d[\d.]*,\d{2}|\d+\.\d{2})', texto)


def _data_apos(texto, marcadores):
    for marcador in marcadores:
        posicao = re.search(marcador, texto, re.IGNORECASE)
        if posicao:
            trecho = texto[posicao.end():posicao.end() + 350]
            datas = re.findall(r'\b\d{2}/\d{2}/\d{4}\b', trecho)
            if datas:
                return _data(datas[0])
    return None


def _cnpjs(texto):
    padrao = r'(?<!\d)(?:\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})(?!\d)'
    return [_normalizar_cnpj(cnpj) for cnpj in re.findall(padrao, texto)]


def _registro_pdf(tipo, texto, arquivo_nome):
    texto = texto or ''
    if not texto.strip():
        raise ValidationError(
            'O PDF não possui texto legível. Confira o arquivo antes de '
            'importar; PDFs digitalizados sem OCR precisam de preenchimento '
            'manual.')

    nomes = []
    if tipo == 'boleto':
        favorecido = re.search(
            r'Benefici[aá]rio\s+CPF/CNPJ\s*\n\s*(.+?)\s+'
            r'(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})',
            texto, re.IGNORECASE | re.DOTALL)
        if favorecido:
            nomes.append(favorecido.group(1).strip())
    recibo = re.search(
        r'RECEBEMOS\s+DE\s+(.+?),\s*(?:OS\s+PRODUTOS|OS\s+PRODUTOS\s+E/OU)',
        texto, re.IGNORECASE | re.DOTALL)
    if recibo:
        nomes.append(recibo.group(1).strip())
    if not nomes:
        inicio = re.search(r'Identifica[cç][aã]o do Emitente', texto,
                           re.IGNORECASE)
        if inicio:
            trecho = texto[inicio.end():inicio.end() + 500]
            for linha in trecho.splitlines():
                linha = linha.strip()
                if (linha and re.search(r'[A-Za-zÀ-ÿ]', linha)
                        and not re.search(
                            r'DANFE|DOCUMENTO AUXILIAR|NOTA FISCAL|'
                            r'CHAVE DE ACESSO|ENTRADA|SAIDA|CNPJ',
                            linha, re.IGNORECASE)):
                    nomes.append(linha)
                    break
    cnpj = next(iter(_cnpjs(texto)), '')

    if tipo == 'boleto':
        trecho = re.search(
            r'Valor do Documento\s*\n(.{0,250})',
            texto, re.IGNORECASE | re.DOTALL)
        valor_texto = ''
        if trecho:
            valor_match = re.search(
                r'R\$\s*([\d.]+,\d{2}|\d+\.\d{2})',
                trecho.group(1), re.IGNORECASE)
            valor_texto = valor_match.group(1) if valor_match else ''
        vencimento = _data_apos(texto, (r'Vencimento', r'Dt\.\s*Vcto'))
        descricao = ''
        contrato = re.search(
            r'(CONTRATO\s*:\s*[\w./-]+(?:\s+PARCELA\s*:\s*[\w./-]+)?)',
            texto, re.IGNORECASE)
        if contrato:
            descricao = contrato.group(1).strip()
    else:
        marcador_valor = re.search(
            r'VALOR TOTAL DA NOTA', texto, re.IGNORECASE)
        valor_texto = ''
        if marcador_valor:
            linhas = [
                linha.strip()
                for linha in texto[marcador_valor.end():
                                  marcador_valor.end() + 250].splitlines()
                if linha.strip()
            ]
            if linhas:
                valores = _dinheiros(linhas[0])
                if valores:
                    valor_texto = valores[-1]
        vencimento = _data_apos(
            texto, (r'DT\.\s*VCTO', r'DATA\s+DE\s+VENCIMENTO'))
        emissao = re.search(
            r'EMISS[AÃ]O\s*:\s*(\d{2}/\d{2}/\d{4})',
            texto, re.IGNORECASE)
        if not emissao:
            emissao = re.search(
                r'DATA\s+DA\s+EMISS[AÃ]O\s*\n?.{0,100}?'
                r'(\d{2}/\d{2}/\d{4})',
                texto, re.IGNORECASE | re.DOTALL)
        data_emissao = _data(emissao.group(1)) if emissao else None
        vencimento = vencimento or data_emissao
        numero = re.search(
            r'(?:N[º°]\.?\s*:?|NF-e\s*N[º°]\.?\s*:?)\s*([\d.]+)',
            texto, re.IGNORECASE)
        descricao = f'Nota Fiscal {numero.group(1)}' if numero else ''

    valor = _decimal(valor_texto)
    # O usuário pode completar campos ausentes na tela de revisão. Os campos
    # obrigatórios são validados antes de qualquer gravação.
    return {
        'origem': arquivo_nome,
        'fornecedor_nome': nomes[0][:255] if nomes else '',
        'cnpj': cnpj,
        'empresa_origem': '',
        'categoria': _categoria_no_texto(texto),
        'data': (vencimento or timezone.localdate()).isoformat(),
        'valor': str(valor or Decimal('0.00')),
        'observacao': descricao[:100],
        'aviso': (
            'Confira o valor extraído.' if valor is None else ''),
    }


def _categoria_no_texto(texto):
    """Sugere a classe apenas quando uma classe existente aparece no PDF."""
    texto_normalizado = _normalizar(texto)
    for classe in ClassePagamento.objects.filter(status='A').order_by('descricao'):
        descricao = _normalizar(classe.descricao)
        if descricao and len(descricao) > 2 and descricao in texto_normalizado:
            return classe.descricao
    return ''


def _ler_pdf(tipo, conteudo, nome):
    try:
        with pdfplumber.open(BytesIO(conteudo)) as documento:
            texto = '\n'.join(pagina.extract_text() or ''
                              for pagina in documento.pages)
    except (PdfminerException, OSError, ValueError) as erro:
        raise ValidationError(
            f'Não foi possível ler o PDF: {erro}. Verifique se o arquivo '
            'está íntegro e tente novamente.') from erro
    return [_registro_pdf(tipo, texto, nome)]


def _elemento_xml(elemento, nome):
    if elemento is None:
        return None
    return next(
        (filho for filho in elemento
         if filho.tag.rsplit('}', 1)[-1] == nome),
        None)


def _texto_xml(elemento, caminho):
    atual = elemento
    for nome in caminho.split('/'):
        atual = _elemento_xml(atual, nome)
        if atual is None:
            return ''
    return (atual.text or '').strip()


def _data_xml(texto):
    if not texto:
        return None
    try:
        return datetime.fromisoformat(
            texto.strip().replace('Z', '+00:00')).date()
    except ValueError:
        return _data(texto)


def _ler_xml(conteudo, nome):
    if re.search(rb'<!\s*(?:DOCTYPE|ENTITY)\b', conteudo, re.IGNORECASE):
        raise ValidationError(
            'O XML contém declarações DTD/ENTITY não permitidas. Exporte a '
            'NF-e novamente sem essas declarações e tente outra vez.')
    if b'\x00' in conteudo:
        raise ValidationError(
            'O XML deve estar codificado em UTF-8. Exporte a NF-e novamente '
            'com essa codificação.')
    try:
        raiz = ET.fromstring(conteudo)
    except ET.ParseError as erro:
        raise ValidationError(
            f'Não foi possível ler o XML: {erro}. Confira o arquivo e tente '
            'novamente.') from erro

    inf_nfe = next(
        (elemento for elemento in raiz.iter()
         if elemento.tag.rsplit('}', 1)[-1] == 'infNFe'),
        None)
    if inf_nfe is None:
        raise ValidationError(
            'O XML não contém os dados de uma NF-e (infNFe). Selecione um '
            'XML autorizado da nota fiscal.')

    nome_fornecedor = (
        _texto_xml(inf_nfe, 'emit/xNome')
        or _texto_xml(inf_nfe, 'emit/xFant'))
    cnpj = _texto_xml(inf_nfe, 'emit/CNPJ')
    if not cnpj:
        cnpj = _texto_xml(inf_nfe, 'emit/CPF')
    numero = _texto_xml(inf_nfe, 'ide/nNF')
    natureza = _texto_xml(inf_nfe, 'ide/natOp')
    valor = (
        _texto_xml(inf_nfe, 'total/ICMSTot/vNF')
        or _texto_xml(inf_nfe, 'total/vNFTot'))
    vencimento = _texto_xml(inf_nfe, 'cobr/dup/dVenc')
    vencimento = _data_xml(vencimento) or _data_xml(
        _texto_xml(inf_nfe, 'ide/dhEmi'))
    destinatario = (
        _texto_xml(inf_nfe, 'dest/xNome')
        or _texto_xml(inf_nfe, 'dest/CNPJ'))
    classe_texto = ' '.join(
        (elemento.text or '').strip()
        for elemento in inf_nfe.iter()
        if elemento.text and elemento.text.strip())
    return [{
        'origem': nome,
        'fornecedor_nome': nome_fornecedor[:255],
        'cnpj': _normalizar_cnpj(cnpj),
        'empresa_origem': destinatario[:255],
        'categoria': _categoria_no_texto(classe_texto),
        'data': (vencimento or timezone.localdate()).isoformat(),
        'valor': str(_decimal(valor) or Decimal('0.00')),
        'observacao': (
            f'Nota Fiscal {numero}' + (f' - {natureza}' if natureza else '')
        )[:100],
        'aviso': (
            'Confira o valor extraído.'
            if _decimal(valor) is None else ''),
    }]


def _cabeçalho_planilha(worksheet):
    aliases = {
        'empresa': ('EMPRESA', 'ESTABELECIMENTO'),
        'fornecedor': ('FORNECEDORES', 'FORNECEDOR'),
        'cnpj': ('CNPJ', 'CPF/CNPJ'),
        'categoria': ('CONTA', 'CLASSE DE PAGAMENTO', 'CATEGORIA'),
        'data': ('DATA', 'DATA PAGAMENTO'),
        'competencia': (
            'COMPETENCIA', 'MES COMPETENCIA', 'COMPETENCIA PAGAMENTO'),
        'vencimento': (
            'VENCIMENTO', 'DT VENCIMENTO', 'DATA VENCIMENTO',
            'DATA DE VENCIMENTO', 'DT. VENCIMENTO'),
        'observacao': ('OBSERVACAO', 'OBSERVACOES', 'DESCRICAO'),
        'valor': ('VALOR', 'VALOR PAGAMENTO', 'VALOR A PAGAR'),
    }
    for linha_numero, linha in enumerate(
            worksheet.iter_rows(min_row=1, max_row=min(8, worksheet.max_row),
                                values_only=True), 1):
        nomes = [_normalizar(valor) for valor in linha]
        campos = {}
        for campo, alternativas in aliases.items():
            indice = next((nomes.index(nome) for nome in alternativas
                           if nome in nomes), None)
            if indice is not None:
                campos[campo] = indice
        tem_data = {'data', 'competencia', 'vencimento'}.intersection(campos)
        if {'fornecedor', 'valor'}.issubset(campos) and tem_data:
            return linha_numero, campos
    return None, {}


def _registros_aba(worksheet):
    linha_cabecalho, colunas = _cabeçalho_planilha(worksheet)
    if linha_cabecalho is None:
        return []
    registros = []
    for numero_linha, linha in enumerate(
            worksheet.iter_rows(min_row=linha_cabecalho + 1,
                                values_only=True),
            linha_cabecalho + 1):
        def obter(campo):
            indice = colunas.get(campo)
            return linha[indice] if indice is not None and indice < len(linha) \
                else None

        data_generica = _data(obter('data'))
        competencia = _data(obter('competencia'))
        vencimento = _data(obter('vencimento'))
        vencimento = vencimento or data_generica or competencia
        competencia = competencia or vencimento or data_generica
        valor = _decimal(obter('valor'))
        if competencia is None or vencimento is None or valor is None \
                or valor <= 0:
            continue
        cnpj = _normalizar_cnpj(obter('cnpj'))
        registros.append({
            'origem': f'{worksheet.title}, linha {numero_linha}',
            'fornecedor_nome': str(obter('fornecedor') or '').strip()[:255],
            'cnpj': cnpj,
            'empresa_origem': str(obter('empresa') or '').strip()[:255],
            'categoria': str(obter('categoria') or '').strip()[:255],
            'data': vencimento.isoformat(),
            'competencia': competencia.isoformat(),
            'vencimento': vencimento.isoformat(),
            'valor': str(valor),
            'observacao': str(obter('observacao') or '').strip()[:100],
            'aviso': '' if obter('fornecedor') else
                'Informe o fornecedor na revisão.',
        })
    return registros


def _ler_planilha(conteudo, abas=None):
    try:
        workbook = load_workbook(
            BytesIO(conteudo), read_only=True, data_only=True)
    except (BadZipFile, InvalidFileException, OSError, ValueError) as erro:
        raise ValidationError(
            f'Não foi possível ler a planilha: {erro}. Confira o arquivo '
            'e tente novamente.') from erro
    registros_por_aba = {}
    for worksheet in workbook.worksheets:
        registros = _registros_aba(worksheet)
        if registros:
            registros_por_aba[worksheet.title] = registros
    workbook.close()
    if abas is not None:
        registros_por_aba = {
            nome: registros_por_aba[nome]
            for nome in abas if nome in registros_por_aba
        }
    return registros_por_aba


def _ler_arquivo(tipo, conteudo, nome, abas=None):
    if tipo == 'excel':
        por_aba = _ler_planilha(conteudo, abas)
        registros = [registro for linhas in por_aba.values()
                     for registro in linhas]
        if not registros:
            raise ValidationError(
                'Não encontrei pagamentos nas abas selecionadas. Verifique '
                'se há colunas Fornecedor, Data e Valor com dados.')
        return registros
    if tipo == 'xml':
        return _ler_xml(conteudo, nome)
    return _ler_pdf(tipo, conteudo, nome)


def _buscar_empresa_cnpj(cnpj):
    if not cnpj:
        return None
    for empresa in Empresa.objects.exclude(cnpj__isnull=True).exclude(
            cnpj='').only('pk', 'cnpj', 'tipo', 'empresa', 'razao_social'):
        if _normalizar_cnpj(empresa.cnpj) == cnpj:
            return empresa
    return None


def _classe_mais_frequente_por_fornecedor(registros, indice_fornecedor):
    contagens = {}
    nomes = {}
    for registro in registros:
        if registro.get('grupo_fornecedor') != indice_fornecedor:
            continue
        nome = (registro.get('categoria') or '').strip()
        chave = _normalizar(nome)
        if not chave:
            continue
        contagens[chave] = contagens.get(chave, 0) + 1
        nomes.setdefault(chave, nome)

    if not contagens:
        return '', False
    maior_frequencia = max(contagens.values())
    mais_frequentes = [
        chave for chave, frequencia in contagens.items()
        if frequencia == maior_frequencia
    ]
    return nomes[mais_frequentes[0]], len(mais_frequentes) > 1


def _grupos(registros, estabelecimentos,
            sugerir_classificacao_excel=False):
    fornecedores = []
    classes = []
    empresas = []
    indice_fornecedor = {}
    indice_classe = {}
    indice_empresa = {}
    fornecedores_db = list(Fornecedor.objects.select_related(
        'empresa', 'classificacao').all())
    estabelecimentos_db = list(estabelecimentos.select_related('empresa'))

    for registro in registros:
        nome_fornecedor = registro['fornecedor_nome']
        cnpj = _normalizar_cnpj(registro['cnpj'])
        chave_fornecedor = cnpj or _normalizar(nome_fornecedor) or \
            registro['origem']
        if chave_fornecedor not in indice_fornecedor:
            indice = len(fornecedores)
            indice_fornecedor[chave_fornecedor] = indice
            empresa = _buscar_empresa_cnpj(cnpj)
            fornecedor_sugerido = None
            if empresa is not None:
                fornecedor_sugerido = next(
                    (item for item in fornecedores_db
                     if item.empresa_id == empresa.pk), None)
            elif nome_fornecedor:
                chave_nome = _normalizar(nome_fornecedor)
                fornecedor_sugerido = next(
                    (item for item in fornecedores_db
                     if _normalizar(item.descricao) == chave_nome), None)
            fornecedores.append({
                'indice': indice,
                'nome': nome_fornecedor,
                'cnpj': cnpj,
                'empresa_existente': empresa,
                'fornecedor_sugerido': fornecedor_sugerido,
                'classificacao_sugerida': (
                    fornecedor_sugerido.classificacao
                    if fornecedor_sugerido else None),
                'nova_classificacao_sugerida': (
                    '' if fornecedor_sugerido else 'Não classificado'),
                'situacao': (
                    f'Fornecedor existente #{fornecedor_sugerido.pk}'
                    if fornecedor_sugerido else
                    f'Empresa existente #{empresa.pk}; fornecedor será criado'
                    if empresa else 'Novo fornecedor será criado'),
            })
        registro['grupo_fornecedor'] = indice_fornecedor[chave_fornecedor]

        categoria = registro['categoria']
        chave_classe = _normalizar(categoria) or 'SEM CLASSE'
        if chave_classe not in indice_classe:
            indice = len(classes)
            indice_classe[chave_classe] = indice
            classe_sugerida = next(
                (classe for classe in ClassePagamento.objects.filter(
                    status='A').order_by('descricao')
                 if _normalizar(classe.descricao) == chave_classe), None)
            classes.append({
                'indice': indice,
                'nome': categoria,
                'classe_sugerida': classe_sugerida,
                'situacao': (
                    f'Classe existente: {classe_sugerida}'
                    if classe_sugerida else
                    f'Criar classe “{categoria}”' if categoria else
                    'Sem classe detectada; escolha ou deixe em branco'),
            })
        registro['grupo_classe'] = indice_classe[chave_classe]

        empresa_origem = registro['empresa_origem']
        chave_empresa = _normalizar(empresa_origem) or 'PADRAO'
        if chave_empresa not in indice_empresa:
            indice = len(empresas)
            indice_empresa[chave_empresa] = indice
            sugerido = _sugerir_estabelecimento(
                empresa_origem, estabelecimentos_db)
            empresas.append({
                'indice': indice,
                'nome': empresa_origem or 'Estabelecimento padrão',
                'estabelecimento_sugerido': sugerido,
                'situacao': (
                    f'Estabelecimento encontrado: {sugerido}'
                    if sugerido else
                    'Selecione o estabelecimento que receberá este pagamento'),
            })
        registro['grupo_estabelecimento'] = indice_empresa[chave_empresa]

    if sugerir_classificacao_excel:
        classificacoes_por_nome = {
            _normalizar(classificacao.descricao): classificacao
            for classificacao in ClassificacaoFornecedor.objects.all()
        }
        for grupo in fornecedores:
            fornecedor = grupo['fornecedor_sugerido']
            if fornecedor and fornecedor.classificacao_id:
                continue
            classe_nome, empate = _classe_mais_frequente_por_fornecedor(
                registros, grupo['indice'])
            if not classe_nome:
                continue
            classificacao = classificacoes_por_nome.get(
                _normalizar(classe_nome))
            grupo['classificacao_sugerida'] = classificacao
            grupo['nova_classificacao_sugerida'] = (
                '' if classificacao else classe_nome)
            grupo['classificacao_ambigua'] = empate
            if empate:
                grupo['situacao'] += (
                    f'; empate na classe mais frequente, sugestão “'
                    f'{classe_nome}” para revisar')
            else:
                grupo['situacao'] += (
                    f'; classificação sugerida pela classe de pagamento '
                    f'mais frequente: {classe_nome}')
    return fornecedores, classes, empresas


def _sugerir_estabelecimento(nome, estabelecimentos):
    chave = _normalizar(nome)
    if not chave:
        return None
    for estabelecimento in estabelecimentos:
        nomes = [
            estabelecimento.estabelecimento,
            estabelecimento.empresa.empresa,
            estabelecimento.empresa.fantasia,
            estabelecimento.empresa.razao_social,
        ]
        if any(_normalizar(candidato) == chave for candidato in nomes):
            return estabelecimento
    return None


def _estabelecimentos_permitidos(request):
    perfil = getattr(request.user, 'perfil', None)
    sessao_id = request.session.get('estabelecimento_id')
    if perfil is None:
        if not request.user.is_superuser:
            raise ValidationError(
                'Seu usuário não tem perfil com estabelecimento autorizado. '
                'Peça ao administrador para configurar seu perfil antes de '
                'importar pagamentos.')
        queryset = Estabelecimento.objects.all()
        ativo = queryset.filter(pk=sessao_id).first() if sessao_id else None
        return queryset, ativo or queryset.order_by('estabelecimento').first()

    liberados = perfil.estabelecimento.all()
    padrao = perfil.estabelecimento_padrao
    if padrao is not None:
        liberados = (Estabelecimento.objects.filter(pk__in=liberados.values('pk'))
                     | Estabelecimento.objects.filter(pk=padrao.pk))
    selecionado = Estabelecimento.objects.filter(pk=sessao_id).first() \
        if sessao_id else None
    if selecionado and not liberados.filter(pk=selecionado.pk).exists():
        raise ValidationError(
            'O estabelecimento selecionado na sessão não está liberado para '
            'o seu perfil. Escolha um estabelecimento autorizado antes de '
            'importar.')
    ativo = selecionado or padrao
    return liberados.distinct(), ativo


def _classificacao_por_nome(nome):
    chave = _normalizar(nome)
    if not chave:
        return None
    return next((item for item in ClassificacaoFornecedor.objects.all()
                 if _normalizar(item.descricao) == chave), None)


def _classe_pagamento_por_nome(nome):
    chave = _normalizar(nome)
    if not chave:
        return None
    return next((item for item in ClassePagamento.objects.all()
                 if _normalizar(item.descricao) == chave), None)


def _contexto_breadcrumb(request, model_admin, titulo):
    from dominios.breadcrumbs import breadcrumbs_context

    contexto = dict(model_admin.admin_site.each_context(request))
    opts = Pagamento._meta
    contexto.update(breadcrumbs_context(
        model_admin.admin_site, request, opts.app_label,
        modelo_nome=titulo,
        modelo_url=reverse('admin:admin_pagamentos_pagamento_changelist')))
    contexto['opts'] = opts
    return contexto


def _pendencia(request, token):
    pendencias = request.session.get(SESSION_KEY, {})
    pendencia = pendencias.get(token)
    if pendencia is None:
        return None
    if not default_storage.exists(pendencia['storage_name']):
        pendencias.pop(token, None)
        request.session[SESSION_KEY] = pendencias
        return None
    return pendencia


def _remover_pendencia(request, token, pendencia):
    default_storage.delete(pendencia['storage_name'])
    pendencias = request.session.get(SESSION_KEY, {})
    pendencias.pop(token, None)
    request.session[SESSION_KEY] = pendencias


def _permissoes_para_criar(
        usuario, form, fornecedores, classes, fornecedores_ativos,
        classes_ativas):
    faltantes = set()
    for grupo in fornecedores:
        indice = grupo['indice']
        if indice not in fornecedores_ativos:
            continue
        prefixo = f'fornecedor_{indice}'
        if form.cleaned_data.get(f'{prefixo}_obj'):
            continue
        empresa = grupo['empresa_existente']
        fornecedor_existente = bool(
            empresa and Fornecedor.objects.filter(empresa=empresa).exists())
        if not empresa and not usuario.has_perm(
                'admin_cadastros.add_empresa'):
            faltantes.add('empresas')
        if not fornecedor_existente and not usuario.has_perm(
                'admin_pagamentos.add_fornecedor'):
            faltantes.add('fornecedores')
        classificacao = form.cleaned_data.get(
            f'{prefixo}_classificacao')
        nome_classificacao = form.cleaned_data.get(
            f'{prefixo}_nova_classificacao', '').strip()
        if not fornecedor_existente and not classificacao and \
                not _classificacao_por_nome(nome_classificacao) and \
                not usuario.has_perm(
                    'admin_pagamentos.add_classificacaofornecedor'):
            faltantes.add('classificações de fornecedor')

    for grupo in classes:
        indice = grupo['indice']
        if indice not in classes_ativas:
            continue
        prefixo = f'classe_{indice}'
        nome = form.cleaned_data.get(f'{prefixo}_nova', '').strip()
        if not form.cleaned_data.get(f'{prefixo}_obj') and nome and \
                not _classe_pagamento_por_nome(nome) and \
                not usuario.has_perm('admin_pagamentos.add_classepagamento'):
            faltantes.add('classes de pagamento')

    if faltantes:
        lista = ', '.join(sorted(faltantes))
        form.add_error(
            None,
            f'Você não tem permissão para criar {lista}. Peça ao '
            'administrador as permissões correspondentes ou selecione '
            'cadastros existentes.')
        return False
    return True


def importar_pagamentos_view(request, model_admin):
    """Upload, prévia, escolha dos vínculos e gravação transacional."""
    if not model_admin.has_add_permission(request) or not \
            request.user.has_perm('admin_pagamentos.add_prepagamento'):
        from django.contrib import messages
        messages.error(
            request, 'Você não tem permissão para importar pagamentos. '
            'Solicite ao administrador o acesso de criação.')
        return redirect('admin:admin_pagamentos_pagamento_changelist')

    from django.contrib import messages
    token = request.GET.get('token') or request.POST.get('token')
    if request.method == 'POST' and request.POST.get('acao') == 'cancelar':
        pendencia = _pendencia(request, token) if token else None
        if pendencia:
            _remover_pendencia(request, token, pendencia)
        messages.info(request, 'Importação cancelada; nenhum pagamento foi criado.')
        return redirect('admin:admin_pagamentos_pagamento_changelist')

    if not token:
        form = UploadPagamentoForm(request.POST or None, request.FILES or None)
        if request.method == 'POST' and form.is_valid():
            arquivo = form.cleaned_data['arquivo']
            tipo = form.cleaned_data['tipo_arquivo']
            conteudo = arquivo.read()
            try:
                if tipo == 'excel':
                    abas = _ler_planilha(conteudo)
                    if not abas:
                        raise ValidationError(
                            'A planilha não contém abas com colunas Fornecedor, '
                            'Data e Valor.')
                else:
                    _ler_arquivo(tipo, conteudo, arquivo.name)
                    abas = {}
            except ValidationError as erro:
                form.add_error('arquivo', erro)
            else:
                token = uuid4().hex
                extensao = {
                    'excel': 'xlsx',
                    'xml': 'xml',
                }.get(tipo, 'pdf')
                storage_name = default_storage.save(
                    f'{TEMP_PREFIX}{token}.{extensao}',
                    ContentFile(conteudo))
                pendencias = request.session.get(SESSION_KEY, {})
                pendencias[token] = {
                    'storage_name': storage_name,
                    'nome': arquivo.name.rsplit('/', 1)[-1],
                    'tipo': tipo,
                }
                request.session[SESSION_KEY] = pendencias
                if tipo == 'excel':
                    return redirect(
                        f'{request.path}?token={token}&abas=1')
                return redirect(f'{request.path}?token={token}')

        contexto = _contexto_breadcrumb(
            request, model_admin, 'Importar Pagamentos')
        contexto.update({
            'title': 'Importar Pagamentos',
            'form': form,
            'cancel_url': reverse(
                'admin:admin_pagamentos_pagamento_changelist'),
        })
        return render(
            request, 'admin_pagamentos/importar_pagamentos.html', contexto)

    pendencia = _pendencia(request, token)
    if pendencia is None:
        messages.error(
            request, 'A importação expirou ou não foi encontrada. Selecione '
            'o arquivo novamente.')
        return redirect('admin:admin_pagamentos_pagamento_changelist')
    with default_storage.open(pendencia['storage_name'], 'rb') as arquivo:
        conteudo = arquivo.read()

    if pendencia['tipo'] == 'excel':
        por_aba = _ler_planilha(conteudo)
        nomes_abas = list(por_aba)
        if request.GET.get('abas') == '1' or not pendencia.get('abas'):
            labels = [(nome, f'{nome} — {len(por_aba[nome])} pagamento(s)')
                      for nome in nomes_abas]
            selecao_form = PagamentoImportSheetForm(
                request.POST or None, prefix='selecao')
            selecao_form.fields['abas'].choices = labels
            if not pendencia.get('abas'):
                mes = (
                    'JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO',
                    'JUNHO', 'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO',
                    'NOVEMBRO', 'DEZEMBRO',
                )[timezone.localdate().month - 1]
                nome_mes = f'{mes} {timezone.localdate():%y}'
                if nome_mes in nomes_abas:
                    selecao_form.initial['abas'] = [nome_mes]
            if request.method == 'POST' and \
                    request.POST.get('acao') == 'selecionar_abas' and \
                    selecao_form.is_valid():
                pendencia['abas'] = selecao_form.cleaned_data['abas']
                pendencias = request.session.get(SESSION_KEY, {})
                pendencias[token] = pendencia
                request.session[SESSION_KEY] = pendencias
                return redirect(f'{request.path}?token={token}')
            contexto = _contexto_breadcrumb(
                request, model_admin, 'Selecionar Abas da Planilha')
            contexto.update({
                'title': 'Selecionar Abas da Planilha',
                'pendencia': pendencia,
                'selecao_form': selecao_form,
                'token': token,
                'etapa_abas': True,
            })
            return render(
                request, 'admin_pagamentos/importar_pagamentos.html', contexto)
        abas = pendencia['abas']
        registros = [registro for nome in abas
                     for registro in por_aba.get(nome, [])]
    else:
        abas = None
        registros = _ler_arquivo(
            pendencia['tipo'], conteudo, pendencia['nome'])

    try:
        estabelecimentos, estabelecimento_ativo = \
            _estabelecimentos_permitidos(request)
    except ValidationError as erro:
        messages.error(request, erro.message)
        return redirect('admin:admin_pagamentos_pagamento_changelist')
    fornecedores, classes, empresas = _grupos(
        registros, estabelecimentos,
        sugerir_classificacao_excel=pendencia['tipo'] == 'excel')
    dados_mapeamento = request.POST if request.method == 'POST' else None
    mapeamento_form = MapeamentoPagamentoForm(
        dados_mapeamento, fornecedores=fornecedores,
        classificacoes=ClassificacaoFornecedor.objects.all(),
        classes_pagamento=ClassePagamento.objects.all(),
        estabelecimentos=estabelecimentos,
        grupos_fornecedor=fornecedores, grupos_classe=classes,
        grupos_estabelecimento=empresas, prefix='fk')
    dados_linhas = request.POST if request.method == 'POST' else None
    iniciais_linhas = []
    for registro in registros:
        data = _data(registro.get('data')) or timezone.localdate()
        competencia = _data(registro.get('competencia')) or data
        vencimento = _data(registro.get('vencimento')) or data or competencia
        iniciais_linhas.append({
            'origem': registro['origem'],
            'grupo_fornecedor': registro['grupo_fornecedor'],
            'grupo_classe': registro['grupo_classe'],
            'grupo_estabelecimento': registro['grupo_estabelecimento'],
            'incluir': True,
            'competencia': competencia,
            'vencimento': vencimento,
            'valor': registro['valor'],
            'forma_pagamento': 'B',
            'observacao': registro['observacao'],
        })
    linhas_formset = PagamentoImportRowFormSet(
        dados_linhas, initial=iniciais_linhas, prefix='linhas')
    for registro, linha_form in zip(registros, linhas_formset.forms):
        grupo_fornecedor = fornecedores[registro['grupo_fornecedor']]
        grupo_classe = classes[registro['grupo_classe']]
        grupo_estabelecimento = empresas[
            registro['grupo_estabelecimento']]
        registro['form'] = linha_form
        registro['fornecedor_label'] = (
            str(grupo_fornecedor['fornecedor_sugerido'])
            if grupo_fornecedor['fornecedor_sugerido']
            else grupo_fornecedor['nome'] or 'A criar na confirmação')
        registro['classe_label'] = (
            str(grupo_classe['classe_sugerida'])
            if grupo_classe['classe_sugerida']
            else grupo_classe['nome'] or 'Sem classe')
        registro['estabelecimento_label'] = (
            str(grupo_estabelecimento['estabelecimento_sugerido'])
            if grupo_estabelecimento['estabelecimento_sugerido']
            else grupo_estabelecimento['nome'])

    if request.method == 'POST' and \
            request.POST.get('acao') == 'confirmar':
        linhas_validas = linhas_formset.is_valid()
        for registro, form_linha in zip(registros, linhas_formset.forms):
            if not hasattr(form_linha, 'cleaned_data'):
                continue
            for campo in (
                    'grupo_fornecedor', 'grupo_classe',
                    'grupo_estabelecimento'):
                if form_linha.cleaned_data.get(campo) != registro[campo]:
                    form_linha.add_error(
                        None,
                        'Os vínculos desta linha foram alterados. Atualize '
                        'a revisão e tente novamente.')
                    linhas_validas = False
                    break
        fornecedores_ativos = {
            form_linha.cleaned_data.get('grupo_fornecedor')
            for form_linha in linhas_formset.forms
            if form_linha.cleaned_data.get('incluir')
            and form_linha.cleaned_data.get('grupo_fornecedor') is not None
        }
        classes_ativas = {
            form_linha.cleaned_data.get('grupo_classe')
            for form_linha in linhas_formset.forms
            if form_linha.cleaned_data.get('incluir')
            and form_linha.cleaned_data.get('grupo_classe') is not None
        }
        mapeamento_form.fornecedores_ativos = fornecedores_ativos
        validos = linhas_validas and mapeamento_form.is_valid()
        if validos and not any(
                form.cleaned_data.get('incluir')
                for form in linhas_formset.forms):
            linhas_formset.forms[0].add_error(
                'incluir', 'Selecione pelo menos um pagamento para importar.')
            validos = False
        if validos:
            validos = _permissoes_para_criar(
                request.user, mapeamento_form, fornecedores, classes,
                fornecedores_ativos, classes_ativas)
        if validos:
            arquivos_criados = []
            try:
                with transaction.atomic():
                    mapa_fornecedores = _salvar_fornecedores(
                        mapeamento_form,
                        [grupo for grupo in fornecedores
                         if grupo['indice'] in fornecedores_ativos],
                        request.user)
                    mapa_classes = _salvar_classes(
                        mapeamento_form,
                        [grupo for grupo in classes
                         if grupo['indice'] in classes_ativas],
                        request.user)
                    mapa_estabelecimentos = _salvar_estabelecimentos(
                        mapeamento_form,
                        [grupo for grupo in empresas
                         if any(
                             registro['grupo_estabelecimento']
                             == grupo['indice']
                             and form_linha.cleaned_data.get('incluir')
                             for registro, form_linha in zip(
                                 registros, linhas_formset.forms))])
                    importados = []
                    for registro, form_linha in zip(
                            registros, linhas_formset.forms):
                        dados_linha = form_linha.cleaned_data
                        if not dados_linha.get('incluir'):
                            continue
                        fornecedor = mapa_fornecedores[
                            registro['grupo_fornecedor']]
                        classe = mapa_classes.get(registro['grupo_classe'])
                        estabelecimento = mapa_estabelecimentos[
                            registro['grupo_estabelecimento']]
                        valor = dados_linha['valor']
                        pre_pagamento = PrePagamento.objects.create(
                            fornecedor=fornecedor,
                            classe_pagamento=classe,
                            valor=valor,
                            competencia=dados_linha['competencia'],
                            dt_vencimento=dados_linha['vencimento'],
                            forma_pagamento=dados_linha['forma_pagamento'],
                            estabelecimento=estabelecimento,
                            observacao=dados_linha['observacao'],
                            us_registro=request.user,
                            dt_registro=timezone.now(),
                            status='A',
                        )
                        pagamento = pre_pagamento.gerar_pagamento()
                        if pagamento is None:
                            raise ValidationError(
                                f'Não foi possível gerar o pagamento da '
                                f'origem “{registro["origem"]}”.')
                        if pendencia['tipo'] in (
                                'boleto', 'nota_fiscal', 'xml'):
                            campo_anexo = (
                                'anexo_boleto' if pendencia['tipo'] == 'boleto'
                                else 'anexo_nota_fiscal')
                            with default_storage.open(
                                    pendencia['storage_name'], 'rb') as origem:
                                conteudo_anexo = origem.read()
                            campo_arquivo = getattr(pagamento, campo_anexo)
                            try:
                                campo_arquivo.save(
                                    pendencia['nome'],
                                    ContentFile(conteudo_anexo),
                                    save=True)
                            finally:
                                if campo_arquivo.name:
                                    arquivos_criados.append(
                                        campo_arquivo.name)
                        importados.append(pagamento.pk)
            except (ValidationError, IntegrityError, OSError, ValueError) as erro:
                for nome_arquivo in arquivos_criados:
                    default_storage.delete(nome_arquivo)
                logger.exception('Falha ao importar pagamentos')
                detalhe = (
                    erro.messages[0]
                    if isinstance(erro, ValidationError) else str(erro))
                messages.error(
                    request, f'Não foi possível concluir a importação: {detalhe} '
                    'Nenhum pagamento foi gravado. Corrija os dados e tente '
                    'novamente.')
            else:
                _remover_pendencia(request, token, pendencia)
                messages.success(
                    request, f'{len(importados)} pagamento(s) importado(s) '
                    'com sucesso. Os registros permanecem abertos para '
                    'revisão na listagem.')
                return redirect(
                    'admin:admin_pagamentos_pagamento_changelist')

    contexto = _contexto_breadcrumb(
        request, model_admin, 'Revisar Importação de Pagamentos')
    contexto.update({
        'title': 'Revisar Importação de Pagamentos',
        'pendencia': pendencia,
        'token': token,
        'mapeamento_form': mapeamento_form,
        'linhas_formset': linhas_formset,
        'fornecedor_groups': fornecedores,
        'classe_groups': classes,
        'estabelecimento_groups': empresas,
        'registros': registros,
        'etapa_revisao': True,
    })
    return render(
        request, 'admin_pagamentos/importar_pagamentos.html', contexto)


def _salvar_fornecedores(form, grupos, usuario):
    resultado = {}
    for grupo in grupos:
        indice = grupo['indice']
        prefixo = f'fornecedor_{indice}'
        existente = form.cleaned_data.get(f'{prefixo}_obj')
        if existente:
            resultado[indice] = existente
            continue
        nome = form.cleaned_data[f'{prefixo}_nome'].strip()
        cnpj = _normalizar_cnpj(form.cleaned_data.get(f'{prefixo}_cnpj'))
        empresa = _buscar_empresa_cnpj(cnpj)
        if empresa and empresa.tipo != 'fornecedor':
            raise ValidationError(
                f'O CNPJ {cnpj} já está cadastrado como “'
                f'{empresa.get_tipo_display()}”, não como fornecedor. '
                'Corrija o cadastro da empresa antes de importar.')
        if empresa is None:
            empresa = Empresa.objects.create(
                tipo='fornecedor',
                razao_social=nome,
                fantasia=nome,
                empresa=nome,
                cnpj=cnpj or None,
                us_registro=usuario,
                dt_registro=timezone.now(),
                status='A',
            )
        fornecedor = Fornecedor.objects.filter(empresa=empresa).first()
        if fornecedor is None:
            classificacao = form.cleaned_data.get(
                f'{prefixo}_classificacao')
            if classificacao is None:
                nome_classificacao = (
                    form.cleaned_data.get(
                        f'{prefixo}_nova_classificacao') or '').strip()
                classificacao = _classificacao_por_nome(nome_classificacao)
                if classificacao is None:
                    classificacao = ClassificacaoFornecedor.objects.create(
                        descricao=nome_classificacao,
                        us_registro=usuario,
                        dt_registro=timezone.now(),
                        status='A',
                    )
            fornecedor = Fornecedor.objects.create(
                descricao=nome,
                empresa=empresa,
                classificacao=classificacao,
                us_registro=usuario,
                dt_registro=timezone.now(),
                status='A',
            )
        resultado[indice] = fornecedor
    return resultado


def _salvar_classes(form, grupos, usuario):
    resultado = {}
    for grupo in grupos:
        indice = grupo['indice']
        prefixo = f"classe_{indice}"
        classe = form.cleaned_data.get(f'{prefixo}_obj')
        if classe is None:
            nome = (form.cleaned_data.get(f'{prefixo}_nova') or '').strip()
            classe = _classe_pagamento_por_nome(nome)
            if classe is None and nome:
                classe = ClassePagamento.objects.create(
                    descricao=nome,
                    us_registro=usuario,
                    dt_registro=timezone.now(),
                    status='A',
                )
        if classe is not None:
            resultado[indice] = classe
    return resultado


def _salvar_estabelecimentos(form, grupos):
    return {
        grupo['indice']: form.cleaned_data[
            f"estabelecimento_{grupo['indice']}"]
        for grupo in grupos
    }
