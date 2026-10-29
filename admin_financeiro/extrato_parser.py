"""Leitura de extratos bancários: OFX (SGML v102) e PDF (fácil/table).

Cada formato devolve uma lista de transações:
    {'data': date, 'valor': Decimal(+/-), 'descricao': str,
     'documento': str|None, 'fitid': str|None}

O OFX usa o FITID como id único (dedupe). No PDF a dedupe é por
(data, valor, descrição).
"""
import re
from datetime import datetime, date
from decimal import Decimal


# ---------------------------------------------------------------------------
# OFX
# ---------------------------------------------------------------------------
def _ofx_decode(brutos: bytes) -> str:
    """OFX SGML em cp1252 (padrão dos bancos BR) com fallback."""
    for enc in ('cp1252', 'latin-1', 'utf-8'):
        try:
            return brutos.decode(enc)
        except UnicodeDecodeError:
            continue
    return brutos.decode('latin-1', errors='replace')


_DT_RE = re.compile(r'^(\d{4})(\d{2})(\d{2})')


def _ofx_data(bruto: str) -> date:
    """'20260901120000[-3:BRT]' → date(2026, 9, 1)."""
    m = _DT_RE.match(bruto or '')
    if not m:
        return None
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def parse_ofx(conteudo_bytes: bytes):
    """Extrai as STMTTRN do OFX SGML (sem dependências externas)."""
    texto = _ofx_decode(conteudo_bytes)
    transacoes = []
    # Cada bloco <STMTTRN> ... </STMTTRN>
    for bloco in re.findall(
            r'<STMTTRN>(.*?)</STMTTRN>', texto, re.S | re.I):
        campos = {}
        for tag in ('TRNTYPE', 'DTPOSTED', 'TRNAMT', 'FITID', 'CHECKNUM',
                    'REFNUM', 'MEMO', 'NAME'):
            m = re.search(rf'<{tag}>([^<\r\n]*)', bloco, re.I)
            if m:
                campos[tag.lower()] = m.group(1).strip()
        data = _ofx_data(campos.get('dtposted'))
        valor = Decimal(campos.get('trnamt') or '0').quantize(Decimal('0.01'))
        descricao = (campos.get('memo') or campos.get('name') or '').strip()
        documento = campos.get('checknum') or campos.get('refnum') or None
        if documento in ('0', ''):
            documento = campos.get('refnum') or None
        transacoes.append({
            'data': data,
            'valor': valor,
            'descricao': descricao or '(sem descrição)',
            'documento': documento,
            'fitid': campos.get('fitid') or None,
        })
    # saldo final (LEDGERBAL/BALAMT), se houver
    m = re.search(r'<LEDGERBAL>.*?<BALAMT>([-\d.]+)', texto, re.S | re.I)
    saldo_final = Decimal(m.group(1)) if m else None
    return transacoes, saldo_final


# ---------------------------------------------------------------------------
# PDF — Sicoob "EXTRATO DE CONTA CORRENTE" (linhas:
#   dd/mm  doc  HISTÓRICO  R$ valor D|C   + linha de continuação da descrição)
# e fallback genérico "dd/mm/aaaa ... valor".
# ---------------------------------------------------------------------------
_LINHA_SICOOB = re.compile(
    r'^(\d{2}/\d{2})\s+'                        # data dd/mm
    r'(?:(\S+)\s+)?'                            # documento (opcional)
    r'(.+?)\s+'                                 # histórico
    r'R\$\s*([\d.]+,\d\d)([DC])\s*$')           # valor + D/C

_SALDO_SICOOB = re.compile(r'SALDO (?:ANTERIOR|DO DIA|BLOQUEADO)', re.I)


def _dec_sicoob(texto: str, sufixo: str) -> Decimal:
    valor = Decimal(texto.replace('.', '').replace(',', '.'))
    return -valor if sufixo.upper() == 'D' else valor


_CABECALHO_PDF = ('SICOOB', 'SISTEMA', 'PLATAFORMA', 'EXTRATO', 'Cooperativa',
                  'Conta:', 'Periodo:', 'HISTÓRICO', 'Data Documento')


def parse_pdf_sicoob(texto: str):
    transacoes = []
    saldo_final = None
    ultimo_idx = None
    # ano do extrato: 'Periodo: dd/mm/yyyy - dd/mm/yyyy'
    ano = None
    m = re.search(r'Periodo:\s*\d{2}/\d{2}/(\d{4})', texto)
    if m:
        ano = int(m.group(1))
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha:
            continue
        if _SALDO_SICOOB.search(linha):
            # guarda o saldo do dia como candidato a saldo final
            vm = re.findall(r'R\$\s*([\d.]+,\d\d)([DC])', linha)
            if vm and 'DO DIA' in linha.upper():
                saldo_final = _dec_sicoob(vm[-1][0], vm[-1][1])
            ultimo_idx = None
            continue
        if 'LEDGERBAL' in linha or linha.startswith(('SICOOB', 'SISTEMA',
                'PLATAFORMA', 'EXTRATO', 'Cooperativa', 'Conta:',
                'Periodo:', 'HISTÓRICO', 'Data Documento')):
            continue
        m = _LINHA_SICOOB.match(linha)
        if not m:
            # continuação da descrição da transação anterior
            if ultimo_idx is not None:
                transacoes[ultimo_idx]['descricao'] = (
                    transacoes[ultimo_idx]['descricao'] + ' – ' + linha)[:255]
            continue
        data_str, doc, hist, val_str, dc = m.groups()
        mes = int(data_str.split('/')[1])
        if ano is None:
            ano = date.today().year
        try:
            data = date(ano, mes, int(data_str.split('/')[0]))
        except ValueError:
            continue
        transacoes.append({
            'data': data,
            'valor': _dec_sicoob(val_str, dc),
            'descricao': hist.strip()[:255],
            'documento': doc,
            'fitid': None,
        })
        ultimo_idx = len(transacoes) - 1
    return transacoes, saldo_final


def parse_pdf(conteudo_bytes: bytes):
    """Extrai transações de um extrato PDF (Sicoob ou genérico)."""
    try:
        import pdfplumber
    except ImportError:
        raise RuntimeError(
            "Instale 'pdfplumber' para importar extratos em PDF.")
    import io
    with pdfplumber.open(io.BytesIO(conteudo_bytes)) as pdf:
        texto = '\n'.join(page.extract_text() or '' for page in pdf.pages)
    if 'Sicoob' in texto or 'SICOOB' in texto:
        return parse_pdf_sicoob(texto)
    # fallback genérico: linhas 'dd/mm/aaaa ... valor'
    transacoes = []
    saldo_final = None
    for linha in texto.splitlines():
        m = _DATA_VAL.search(linha)
        if not m:
            continue
        data_str, desc, val_str = m.groups()
        try:
            data = datetime.strptime(data_str, '%d/%m/%Y').date()
        except ValueError:
            continue
        valor = _dec_br(val_str)
        transacoes.append({
            'data': data,
            'valor': valor,
            'descricao': desc.strip()[:255] or '(sem descrição)',
            'documento': None,
            'fitid': None,
        })
    for linha in texto.splitlines():
        if 'SALDO' in linha.upper():
            vm = _VAL_NEG.findall(linha)
            if vm:
                saldo_final = _dec_br(vm[-1])
    return transacoes, saldo_final


def parse_arquivo(nome: str, conteudo_bytes: bytes):
    """Escolhe o parser pela extensão."""
    if nome.lower().endswith('.ofx'):
        return 'ofx', *parse_ofx(conteudo_bytes)
    if nome.lower().endswith('.pdf'):
        return 'pdf', *parse_pdf(conteudo_bytes)
    raise ValueError('Formato não suportado: use OFX ou PDF.')
