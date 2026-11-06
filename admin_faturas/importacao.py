"""
IMPORTAÇÃO de Acordos de Faturamento a partir da planilha CONVENIOS.xlsx.

Formato esperado (aba ativa, linha 1 = cabeçalho):

    [0]  (vazio)
    [1]  CIDADE                         ex.: "Itajai - Saúde"
    [2]  CNPJ do órgão/pagador          ex.: "11329956000158"
    [3]  acolhidos (um por linha)
    [4]  QUANTIDADE                     (nem sempre preenchida)
    [5]  EMITIDO EM                    data da competência
    [6]  MÊS REFERÊNCIA                data ou texto "25/10 A 24/11/2026"
    [7]  VALOR                         valor total da NF daquela competência
    [8]  (vazio)
    [9]  (vazio)
    [10] DESCRIÇÃO                     texto livre: "CT 628/2020", "Empenho",
                                        "Diária de R$ 375,84", "Período de ..."
    [...]

## Regra central: LINHAS REPETIDAS SÃO COMPETÊNCIAS

O mesmo `(cidade, cnpj, contrato)` aparece em **N linhas** — uma por
competência (mês). Essas N linhas NÃO são N acordos: são **UM acordo** cuja
vigência vai da primeira à última `EMITIDO EM`.

    inicio_vigencia  = min(EMITIDO EM)
    final_vigencia   = max(EMITIDO EM)
    qtd_competencias = quantidade de LINHAS do grupo (não é campo do modelo;
                       aparece só no relatório de importação)

## Decisores extraídos da DESCRIÇÃO (coluna J/[10])

- `CT <n>/<ano>` ou `Contrato: <n>`  → `nr_contrato`
- `Empenho <n>`                      → `empenho_global`
- `Diária de R$ <v>`                 → **valor_diaria** do acordo

Sobre o valor: quando a descrição traz diária, o `VALOR` da linha é
`diária × dias`. Então:
  - `valor_diaria` = a diária extraída da descrição;
  - `valor_mensal` = 0 quando o acordo é **por diária** (o valor real é
    recalculado mês a mês pela quantidade de dias);
  - sem diária na descrição → `valor_mensal` = VALOR e `valor_diaria` = 0.

## Normalização

- CNPJ: remove apóstrofo, pontos, barras e traços → só 14 dígitos.
- Cidade: remove acentos, espaços extras e sufixo depois de " - "
  ("Itajai - Saúde" → "Itajai"); a UF é fixa em **SC**.
- Mesmo CNPJ em cidades diferentes = acordos diferentes (o órgão muda).
"""

import re
import unicodedata
from decimal import Decimal, InvalidOperation

from django.utils import timezone


# ----------------------------------------------------------------------
# Normalização
# ----------------------------------------------------------------------
def normalizar_texto(valor):
    """Minúsculo, sem acento e sem espaço extra (para comparar/agrupar)."""
    if valor is None:
        return ''
    texto = str(valor).strip()
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return ' '.join(texto.casefold().split())


TITULO_CIDADE = {
    'camboriu': 'Camboriú',
    'itajai': 'Itajaí',
    'cubatao': 'Cubatão',
    'florianopolis': 'Florianópolis',
    'sao jose': 'São José',
    'balneario camboriu': 'Balneário Camboriú',
    'gaspar': 'Gaspar',
    'brusque': 'Brusque',
    'blumenau': 'Blumenau',
    'joinville': 'Joinville',
    'navegantes': 'Navegantes',
    'ilhota': 'Ilhota',
    'pomerode': 'Pomerode',
    'timbo': 'Timbó',
    'indial': 'Indaial',
    'tijucas': 'Tijucas',
    'porto belo': 'Porto Belo',
    'bombinhas': 'Bombinhas',
    'penha': 'Penha',
    'picarras': 'Piçarras',
    'barra velha': 'Barra Velha',
    'luis alves': 'Luís Alves',
    'massaranduba': 'Massaranduba',
    'jaragua do sul': 'Jaraguá do Sul',
    'guaramirim': 'Guaramirim',
    'schroeder': 'Schroeder',
    'corupa': 'Corupá',
    'rio dos cedros': 'Rio dos Cedros',
    'doutor pedrinho': 'Doutor Pedrinho',
}


def limpar_cnpj(valor):
    """Só os 14 dígitos (aceita "'08259606000158'", "08.259.606/0001-58")."""
    digitos = re.sub(r'\D', '', str(valor or ''))
    return digitos


def limpar_cidade(valor):
    """'Itajai - Saúde' → 'Itajaí' (nome do MUNICÍPIO, sem o setor)."""
    if not valor:
        return None
    bruto = str(valor).strip()
    # O sufixo depois de " - " é o SETOR (Saúde, Assistência, Educação...)
    municipio = bruto.split(' - ')[0].strip() if ' - ' in bruto else bruto
    municipio = ' '.join(municipio.split())
    chave = normalizar_texto(municipio)
    return TITULO_CIDADE.get(chave, municipio.title())


def _decimal(valor):
    """Converte célula (número ou texto 'R$ 1.234,56') em Decimal."""
    if valor is None or valor == '':
        return None
    if isinstance(valor, (int, float, Decimal)):
        return Decimal(str(valor)).quantize(Decimal('0.01'))
    texto = str(valor).strip()
    texto = texto.replace('R$', '').replace(' ', '')
    if ',' in texto:                       # 1.234,56 (pt-BR)
        texto = texto.replace('.', '').replace(',', '.')
    try:
        return Decimal(texto).quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError):
        return None


def _data(valor):
    """Devolve date se a célula for data; None se for texto de período."""
    from datetime import date, datetime
    if valor is None or valor == '':
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor).strip()
    for fmt in ('%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d'):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    return None


# ----------------------------------------------------------------------
# Decisores da DESCRIÇÃO
# ----------------------------------------------------------------------
RE_CONTRATO = re.compile(
    r'(?:\bCT\b|Contrato\s*N?[ºo°]?)\s*[:\s]*([0-9]+(?:\s*/\s*[0-9]+)?)',
    re.IGNORECASE)
RE_EMPENHO = re.compile(
    r'Empenho\s*[:\s]*([A-Za-z0-9][A-Za-z0-9./\-]*)', re.IGNORECASE)
RE_DIARIA = re.compile(
    r'di[aá]ria\s*(?:de|:)?\s*R?\$?\s*([0-9][0-9.\s]*,[0-9]{2}|[0-9]+(?:\.[0-9]{2})?)',
    re.IGNORECASE)


def extrair_contrato(descricao):
    m = RE_CONTRATO.search(descricao or '')
    if not m:
        return None
    return re.sub(r'\s+', '', m.group(1))


def extrair_empenho(descricao):
    m = RE_EMPENHO.search(descricao or '')
    if not m:
        return None
    return m.group(1).strip().rstrip('.')


RE_DIARIA_ROTULO = re.compile(r'di[aá]ria', re.IGNORECASE)


def extrair_diaria(texto):
    """Diária ROTULADA no texto: 'Diária de R$ 375,84' / 'Diária R$ 415,00'.

    Só aceita quando o texto **tem a palavra “diária”** — é o sinal seguro.
    Célula que é só um número (ex.: Joinville, com `8348.28` na coluna J)
    NÃO é diária: ali o número pode ser o total da competência.
    """
    bruto = str(texto or '')
    if not RE_DIARIA_ROTULO.search(bruto):
        return None
    m = RE_DIARIA.search(bruto)
    if m:
        return _decimal('R$ ' + m.group(1).strip())
    return None


RE_VALOR_TEXTO = re.compile(
    r'R\$\s*([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2}|[0-9]+(?:[.,][0-9]{2})?)',
    re.IGNORECASE)


def extrair_diaria_coluna(celula_j, texto_k, valor_h):
    """Diária POR CLIENTE — decide entre a coluna J e a K.

    A planilha registra a diária de três formas (todas reais):

    | Origem | Exemplo | Significa |
    |---|---|---|
    | K com “Diária R$” | `Diária R$ 375,84` | diária por cliente |
    | K com “R$ x” na 2ª linha | `9 Pacientes` / `R$ 415,00` | diária por cliente |
    | J só com o número | `277.52` | diária por cliente |

    E uma armadilha: em **Joinville** a coluna J repete o TOTAL da nota
    (`8348.28`) e a observação NÃO traz valor — ali J **não** é diária.

    Regra (nesta ordem):

    1. A observação (K) tem `Diária R$ …` → **é** a diária;
    2. A observação (K) tem `R$ …` (ex.: `415,00`) → **é** a diária. Esse
       é o sinal mais confiável: quem escreve o valor na nota está
       declarando o preço unitário;
    3. Sem valor em K, o número da coluna J só vale se **NÃO** for o
       total da linha (H) nem o valor por cliente calculado de H. Joinville
       cai aqui e é descartado; Navegantes (K sem `R$`) é aceito.
    """
    bruto_j = str(celula_j or '').strip()
    texto_k = str(texto_k or '')

    # 1) “Diária R$ …” em qualquer uma das colunas. Se a palavra “diária”
    #    aparece mas SEM valor colado (`62 diárias a 277,52 dia`), o
    #    `extrair_diaria` devolve None — então seguimos para o próximo
    #    sinal em vez de abortar (era o bug de Navegantes).
    if RE_DIARIA_ROTULO.search(texto_k) or RE_DIARIA_ROTULO.search(bruto_j):
        rotulada = extrair_diaria(texto_k) or extrair_diaria(bruto_j)
        if rotulada:
            return rotulada

    # 1.b) “<valor> dia” / “a <valor> dia” sem a palavra “diária”:
    #      `62 diárias a  277,52  dia` → 277,52.
    m_dia = re.search(
        r'(?:a\s+)?([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2}|[0-9]+(?:\.[0-9]+)?)'
        r'\s*(?:reais\s*)?(?:/|por\s+)?dia\b', texto_k, re.IGNORECASE)
    if m_dia:
        valor = _decimal(m_dia.group(1))
        if valor and not (valor_h is not None and valor == valor_h):
            return valor

    # 2) “R$ …” na observação = valor unitário declarado na nota.
    m_valor_k = RE_VALOR_TEXTO.search(texto_k)
    if m_valor_k:
        valor = _decimal(m_valor_k.group(1))
        # Igual ao TOTAL da nota? então é o total, não a diária.
        if valor and not (valor_h is not None and valor == valor_h):
            return valor

    # 3) Coluna J só com o número (contrato sem valor na nota).
    if not bruto_j:
        return None
    m_num = re.fullmatch(r'R?\$?\s*([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2}'
                         r'|[0-9]+(?:[.,][0-9]+)?)\s*', bruto_j)
    if not m_num:
        return None            # texto livre (ofício, reajuste…)
    numero = _decimal(m_num.group(1))
    if numero is None or numero <= 0:
        return None
    if valor_h is not None and numero >= valor_h:
        return None
    return numero


def refinar_diaria_do_grupo(diarias_por_linha):
    """Descarta a “diária” que é, na verdade, o TOTAL repetido da nota.

    Joinville lança `8348.28` na coluna J **em todas as competências**, sem
    valor na observação e sem total (H). Nenhuma regra de linha consegue
    provar que é diária — mas o PADRÃO do grupo prova que NÃO é: uma diária
    variaria com os dias do mês (31, 30, 28…), e um valor IGUAL em 3+ meses
    seguidos não varia.

    **O que distingue uma diária de um total repetido?**

    | Grupo | Coluna J | Diagnóstico |
    |---|---|---|
    | Itajaí (9 cli.) | `415` em todas | DIÁRIA — é pequena, cabe em 1 dia |
    | Joinville (12 cli.) | `8348.28` em todas | TOTAL — não é preço de 1 dia |

    O número igual em todos os meses **não** basta para decidir: uma diária
    de contrato também é fixa. O discriminador é a **ordem de grandeza**:
    se o valor por cliente é da magnitude de um dia de atendimento (até
    R$ 1.000), é diária; acima disso, é o total da nota repetido.

    Quando o grupo trazia `H` (total) nas linhas, esse teste nem chega
    aqui — a coluna J já foi descartada na leitura da linha.

    `diarias_por_linha` é a lista de diárias (uma por linha do grupo,
    já como `Decimal` ou None).
    """
    valores = [d for d in diarias_por_linha if d]
    if not valores:
        return None
    # Todos iguais: só é diária se couber em um dia de atendimento.
    if len(set(valores)) == 1:
        unico = valores[0]
        if len(diarias_por_linha) >= 3 and unico > Decimal('1000'):
            return None
        return unico
    # Oscilou entre competências → é a diária (multiplicada pelos dias).
    # Usa a mais frequente, que é a “diária da casa”.
    contagem = {}
    for d in valores:
        contagem[d] = contagem.get(d, 0) + 1
    return max(contagem, key=contagem.get)


RE_FORMULA_DIARIA = re.compile(
    r'^=\s*([0-9]+(?:[.,][0-9]+)?)\s*\*', re.IGNORECASE)


def extrair_diaria_formula(formula):
    """Diária que está na FÓRMULA da coluna de valor.

    Só consideramos fórmulas de MULTIPLICAÇÃO no formato
    `diária × acolhidos × dias`:

        =425*9*O$1      → diária 425, para 9 acolhidos, 31 dias
        =21*375.84      → 21 dias de diária 375,84

    Valor FIXO (ex.: `=77850` ou `92665.91`) NÃO tem diária — sem `*` não
    há o que extrair. Isso evita o falso positivo de pegar um número
algum (ex.: o `12` de uma referência) e tratar o acordo como diária.
    """
    if not formula or not str(formula).startswith('='):
        return None
    texto = str(formula)
    if '*' not in texto:            # valor fixo, não é diária
        return None
    # Só os fatores NUMÉRICOS (ignora refs como O$1, N$1, J134). O `(?![\d.])`
    # impede casar o pedaço numérico de uma referência de célula (O$1).
    fatores = re.findall(
        r'(?<![A-Za-z0-9$.])([0-9]+(?:\.[0-9]+)?)(?!\d)(?![A-Za-z])', texto)
    numeros = [_decimal(f) for f in fatores]
    numeros = [n for n in numeros if n is not None]
    if not numeros:
        return None
    # DIÁRIA só quando a fórmula tem 2+ fatores numéricos E pelo menos um
    # fator que NÃO seja só quantidade (o `=425*9*O$1` — ref `O$1` conta
    # como fator não-numérico — tem `425` e `9`).
    #
    # Casos:
    #   =425*9*O$1     → diária 425 (3 fatores, 2 numéricos: 425 e 9)
    #   =11*31*277.52  → diária 277.52 (tem centavos)
    #   =12*J134       → NÃO é diária (só 1 fator numérico: 12 = dias)
    if len(numeros) < 2:
        return None
    com_centavos = [n for n in numeros if n != n.to_integral_value()]
    if com_centavos:
        return max(com_centavos)
    return numeros[0]


def extrair_quantidade(texto):
    """Nº de clientes declarado na observação: '9 Pacientes' → 9.

    A coluna E ("QTD NF") pode vir vazia; a observação (K) sempre traz
    `<n> Paciente(s)`. Serve para CONFERIR o que foi lido da coluna D e
    avisar quando divergir.
    """
    m = re.search(r'(\d{1,4})\s*(?:pacientes?|acolhidos?|clientes?)\b',
                  str(texto or ''), re.IGNORECASE)
    return int(m.group(1)) if m else None


def _partes_clientes(texto):
    """Divide a célula da coluna D em NOMES, qualquer que seja o separador.

    Os três formatos convivem na mesma planilha:

        Valci Maria Lucindo - 31-08-26      (quebra de linha)
        Amarildo Forbici; Joao da Silva     (ponto e vírgula)
        Ester Amaral Batista, Laura ...     (vírgula)

    **Uma única função** para dividir e para CONTAR: se a contagem usasse
    outra regra, o divisor do valor por cliente divergiria da quantidade
    de nomes efetivamente criados.
    """
    bruto = str(texto or '').replace(';', '\n')
    partes = []
    for ln in bruto.splitlines():
        # Vírgula separa nomes só quando há `palavra, palavra` — evita
        # quebrar um nome com vírgula interna no meio de uma linha única.
        if ',' in ln and re.search(r'\w\s*,\s*\w', ln):
            partes.extend(ln.split(','))
        else:
            partes.append(ln)
    return [p.strip().strip(',;') for p in partes if p.strip().strip(',;')]


def contar_clientes_texto(texto):
    """Nº de nomes da coluna D (aceita `;`, `,` ou quebra de linha)."""
    return len(_partes_clientes(texto))


def extrair_clientes(texto):
    """Acolhidos da coluna D → lista de `(nome, data_nascimento)`.

    Os acolhidos vêm separados por **quebra de linha**, **`;`** ou
    **vírgula** (os três formatos aparecem na planilha):

        Valci Maria Lucindo - 31-08-26
        Amarildo Forbici; Joao da Silva
        Ester Amaral Batista, Laura Batista Tavares, Kleber...

    ATENÇÃO: a vírgula só separa nomes quando a célula é uma lista corrida
    (`A, B, C`) — se o nome traz vírgula no próprio texto (raro), a divisão
    geraria dois. Como a planilha usa o padrão `Nome, Nome,`, dividimos.

    A data depois do último hífen é a data de nascimento (dd-mm-aa). Nome
    é tudo o que vem antes. Linhas sem nome são descartadas.
    """
    from datetime import date, datetime

    clientes = []
    vistos = set()
    for linha in _partes_clientes(texto):
        nome = linha
        nascimento = None
        m = re.search(
            r'^(.*?)\s*[-–—]?\s*(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})\s*$',
            linha)
        if m:
            nome = m.group(1).strip()
            dia, mes, ano = (int(m.group(2)), int(m.group(3)),
                             int(m.group(4)))
            if ano < 100:
                ano += 2000 if ano <= 30 else 1900
            try:
                nascimento = date(ano, mes, dia)
            except ValueError:
                nascimento = None
        if not nome:
            continue
        chave = (normalizar_texto(nome), nascimento)
        if chave in vistos:
            continue
        vistos.add(chave)
        clientes.append((nome, nascimento))
    return clientes


# ----------------------------------------------------------------------
# Leitura da planilha
# ----------------------------------------------------------------------
# ÍNDICES 0-based (openpyxl é 1-based: `COLUNAS[x] + 1`).
#
#   A DATA | B CIDADE | C CNPJ | D ACOLHIDOS | E NF | F EMITIDO EM
#   G MÊS REFERÊNCIA | H VALOR DA NF | I VALOR RECEBIDO | J EMPENHO
#   K DESCRIÇÃO DA NOTA
COLUNAS = {
    'acolhidos': 3,       # D — nomes dos clientes
    'quantidade': 4,      # E — NF / QTD (pode vir vazia)
    'emitido': 5,         # F — EMITIDO EM (dia de envio + competência)
    'referencia': 6,      # G — MÊS REFERÊNCIA
    'valor': 7,           # H — VALOR DA NF (total do grupo/competência)
    'recebido': 8,        # I — VALOR RECEBIDO
    'descricao': 9,       # J — EMPENHO (o rótulo da coluna confunde)
    'observacao': 10,     # K — DESCRIÇÃO DA NOTA (diária, contrato...)
}


def ler_planilha(caminho_arquivo):
    """Lê a planilha e AGRUPA as linhas em acordos.

    Devolve `(acordos, avisos)`:

    `acordos`  → lista de dicts, um por `(cidade, cnpj, contrato)`:
        {
            'cidade': 'Itajaí', 'cnpj': '11329956000158',
            'nr_contrato': '628/2020', 'empenho_global': '2025NE000405',
            'acordo_faturamento': 'Itajaí - Saúde',   # rótulo do contrato
            'valor_mensal': Decimal, 'valor_diaria': Decimal,
            'inicio_vigencia': date, 'final_vigencia': date,
            'qtd_competencias': int, 'competencias': [date, ...],
            'acolhidos': [str, ...],     # nomes (clientes) do grupo
            'linhas': [int, ...],        # números de linha na planilha
            'emitido_no': date,          # dia do EMITIDO EM (para dia_envio)
        }

    `avisos`   → lista de tuplas `(nivel, mensagem)`,
                 nivel ∈ {'erro', 'alerta'} — linhas ignoradas ou divergências.
    """
    try:
        import openpyxl
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "A biblioteca 'openpyxl' é necessária para importar a planilha.\n"
            "Instale com: pip install openpyxl") from exc

    wb = openpyxl.load_workbook(caminho_arquivo, data_only=True)
    ws = wb.active
    # Segunda leitura SEM `data_only`: fórmulas e CORES não existem no modo
    # calculado. As fórmulas dão a DIÁRIA; a cor da coluna A diz quais
    # linhas NÃO são competência.
    wb_formulas = openpyxl.load_workbook(caminho_arquivo, data_only=False)
    ws_formulas = wb_formulas.active

    avisos = []
    grupos = {}
    linhas_vermelhas = 0

    for num_linha, row in enumerate(ws.iter_rows(values_only=True), start=1):
        if num_linha == 1:              # cabeçalho
            continue
        if row is None or all(c is None or str(c).strip() == ''
                              for c in row):
            continue                # linha totalmente vazia

        # LINHA VERMELHA (coluna A preenchida de vermelho) NÃO é competência:
        # são as previsões/futuras, que não entram na vigência.
        celula_a = ws_formulas.cell(row=num_linha, column=1)
        cor = (celula_a.fill.fgColor.rgb
               if celula_a.fill and celula_a.fill.fill_type else None)
        if cor and str(cor).upper() in ('FFFF0000', 'FF0000'):
            linhas_vermelhas += 1
            continue

        def cel(chave):
            idx = COLUNAS[chave]
            return row[idx] if idx < len(row) else None

        cidade_bruta = (str(row[1]).strip() if len(row) > 1 and row[1] else '')
        cnpj = limpar_cnpj(row[2] if len(row) > 2 else None)

        # Linhas separadoras ('-' na CIDADE, sem CNPJ) aparecem entre os
        # grupos da planilha e NÃO são erro: são só o espaçamento visual.
        if not cnpj and cidade_bruta in ('', '-'):
            continue
        if len(cnpj) != 14:
            avisos.append(
                ('alerta', f'Linha {num_linha}: CNPJ "{cnpj}" não tem 14 '
                           'dígitos — linha ignorada.'))
            continue

        emitido = _data(cel('emitido'))
        if emitido is None:
            avisos.append(
                ('alerta', f'Linha {num_linha}: "EMITIDO EM" não é data — '
                           'linha ignorada.'))
            continue

        descricao = str(cel('descricao') or '')
        observacao = str(cel('observacao') or '')
        formula_valor = ws_formulas.cell(
            row=num_linha, column=COLUNAS['valor'] + 1).value
        # Contrato/empenho aparecem tanto na coluna J quanto na K.
        contrato = (extrair_contrato(descricao)
                    or extrair_contrato(observacao))
        empenho = (extrair_empenho(descricao)
                   or extrair_empenho(observacao))
        valor = _decimal(cel('valor'))
        # A DIÁRIA POR CLIENTE, nesta ordem:
        #   1. valor declarado na nota (K: “Diária R$ …” ou “R$ …”) e, na
        #      falta dele, número puro da coluna J — ver
        #      `extrair_diaria_coluna`;
        #   2. FÓRMULA do valor: `=425*9*O$1` → diária 425.
        diaria = (extrair_diaria_coluna(descricao, observacao, valor)
                  or extrair_diaria_formula(formula_valor))
        clientes_da_linha = extrair_clientes(cel('acolhidos'))
        qtd_observacao = extrair_quantidade(observacao)
        if (qtd_observacao is not None and clientes_da_linha
                and qtd_observacao != len(clientes_da_linha)):
            avisos.append(
                ('alerta',
                 f'Linha {num_linha}: a observação diz {qtd_observacao} '
                 f'paciente(s), mas a coluna D lista '
                 f'{len(clientes_da_linha)}. Confira os nomes.'))

        cidade = limpar_cidade(cidade_bruta)
        chave = (normalizar_texto(cidade), cnpj, contrato or '')
        grupo = grupos.get(chave)
        if grupo is None:
            grupo = grupos[chave] = {
                'cidade': cidade,
                'cidade_rotulo': cidade_bruta,
                'cnpj': cnpj,
                'nr_contrato': contrato or '',
                'empenho_global': empenho or '',
                'valor_diaria': diaria or Decimal('0.00'),
                # Diárias LINHA a LINHA: o grupo decide no final se aquele
                # número é diária ou o total repetido (Joinville).
                '_diarias': [],
                'competencias': [],
                'valores': [],
                'clientes': [],
                '_clientes_vistos': set(),
                'linhas': [],
                'emitido_no': emitido.day,
            }
        # Diária/contrato podem aparecer só em algumas linhas do grupo.
        if diaria and not grupo['valor_diaria']:
            grupo['valor_diaria'] = diaria
        if empenho and not grupo['empenho_global']:
            grupo['empenho_global'] = empenho

        grupo['competencias'].append(emitido)
        grupo['linhas'].append(num_linha)
        grupo['_diarias'].append(diaria)   # refinado ao fechar o grupo
        # CLIENTES da coluna D (um acolhido por linha/quebra da célula, com
        # data de nascimento). Acumulados no grupo, sem repetir — o mesmo
        # cliente aparece em TODAS as competências do grupo.
        for nome, nascimento in clientes_da_linha:
            chave_cliente = (normalizar_texto(nome), nascimento)
            if chave_cliente in grupo['_clientes_vistos']:
                continue
            grupo['_clientes_vistos'].add(chave_cliente)
            grupo['clientes'].append(
                {'nome': nome, 'nascimento': nascimento})
        # O VALOR da planilha é por COMPETÊNCIA do grupo — NÃO por cliente.
        # Guardamos (valor_da_linha, nº de clientes DA LINHA) para dividir
        # depois. A coluna E pode vir vazia: aí o divisor é a própria
        # coluna D.
        qtd_linha = (extrair_quantidade(observacao)
                     or len(clientes_da_linha))
        grupo['valores'].append((valor, qtd_linha if qtd_linha else None))

    acordos = []
    for grupo in grupos.values():
        # COMPETÊNCIAS: dias de emissão distintos. O acordo é UM por grupo,
        # então a mesma data repetida em linhas diferentes não é uma nova
        # competência. As linhas VERMELHAS já saíram antes daqui.
        competencias = sorted(set(grupo['competencias']))
        n_clientes = len(grupo['clientes'])

        # DIÁRIA do grupo: o mesmo número repetido em TODAS as linhas é o
        # TOTAL da nota, não uma diária (ver `refinar_diaria_do_grupo`).
        diaria_grupo = refinar_diaria_do_grupo(grupo['_diarias'])
        grupo['valor_diaria'] = diaria_grupo or Decimal('0.00')
        pares = [(v, q) for v, q in grupo['valores'] if v is not None]
        valor_mensal = Decimal('0.00')
        valor_total_competencia = Decimal('0.00')

        # ---- REGRA: o VALOR É SEMPRE POR CLIENTE (individual) ----------
        # A planilha lança, por competência, o total do grupo. O sistema
        # fatura por cliente (`valor_mensal` × nº de clientes), então o
        # valor do acordo é o total DIVIDIDO pelo nº de clientes da linha.
        if grupo['valor_diaria']:
            # Por DIÁRIA: o valor real é diária × dias × clientes; o
            # `valor_mensal` do acordo fica 0 (não é mensal). O “total da
            # competência” exibido é a diária × clientes (o que a nota
            # cobraria em 1 dia) — não o valor fixo da coluna H.
            valor_mensal = Decimal('0.00')
            valor_total_competencia = (
                grupo['valor_diaria'] * Decimal(n_clientes or 1))
        elif pares:
            # H = MENSALIDADE POR CLIENTE → usa DIRETO, sem dividir.
            valor_mensal = pares[0][0]
            valor_total_competencia = valor_mensal * Decimal(n_clientes or 1)
            # Competências com TOTAIS diferentes podem significar valor por
            # cliente diferente (reajuste) ou grupo de clientes diferente.
            # O valor já É por cliente (não divide): deve ser o mesmo em
            # todas as competências do grupo.
            unitarios = sorted({v for v, _ in pares})
            if len(unitarios) > 1:
                if len(unitarios) > 1:
                    avisos.append(
                        ('alerta',
                         f'{grupo["cidade"]} / CNPJ {grupo["cnpj"]} / CT '
                         f'{grupo["nr_contrato"] or "-"}: o valor POR '
                         f'CLIENTE muda entre competências '
                         f'({", ".join(str(u) for u in sorted(unitarios))})'
                         ' — possível reajuste. Usando o primeiro; confira '
                         'antes de confirmar.'))
                else:
                    avisos.append(
                        ('alerta',
                         f'{grupo["cidade"]} / CNPJ {grupo["cnpj"]} / CT '
                         f'{grupo["nr_contrato"] or "-"}: totais diferentes '
                         'entre competências, mas o valor POR CLIENTE é o '
                         'mesmo — o nº de clientes deve ter variado.'))

        acordos.append({
            'cidade': grupo['cidade'],
            'cidade_rotulo': grupo['cidade_rotulo'],
            'cnpj': grupo['cnpj'],
            'nr_contrato': grupo['nr_contrato'],
            'empenho_global': grupo['empenho_global'],
            'acordo_faturamento': (
                f'{grupo["cidade_rotulo"]}'
                + (f' / CT {grupo["nr_contrato"]}'
                   if grupo['nr_contrato'] else '')),
            'valor_mensal': valor_mensal,
            'valor_total_competencia': valor_total_competencia,
            'qtd_clientes': n_clientes,
            'valor_diaria': grupo['valor_diaria'],
            'inicio_vigencia': competencias[0],
            'final_vigencia': competencias[-1],
            'qtd_competencias': len(competencias),
            'competencias': competencias,
            'clientes': grupo['clientes'],
            'linhas': grupo['linhas'],
            'emitido_no': grupo['emitido_no'],
        })

    acordos.sort(key=lambda a: (a['cidade'] or '', a['cnpj'],
                                a['nr_contrato']))
    if linhas_vermelhas:
        avisos.append(
            ('alerta',
             f'{linhas_vermelhas} linha(s) em VERMELHO na planilha foram '
             'IGNORADAS da vigência (são previsões/futuras, não '
             'competências já faturadas).'))
    if not acordos:
        avisos.append(('erro', 'Nenhum acordo válido encontrado na planilha.'))
    return acordos, avisos


# ----------------------------------------------------------------------
# Importação (gravação)
# ----------------------------------------------------------------------
def _estado_sc():
    from admin_cadastros.models import Estado
    return (Estado.objects.filter(uf='SC').first()
            or Estado.objects.filter(uf__iexact='SC').first())


def _cidade_obj(nome, criadas):
    """Acha (ou cria) a Cidade pelo nome, sempre em SC."""
    from admin_cadastros.models import Cidade
    estado = _estado_sc()
    if estado is None:
        return None, 'SC não cadastrada em admin_cadastros.Estado'
    # O campo do modelo é `cidade` (não `nome`).
    existente = Cidade.objects.filter(cidade__iexact=nome).first()
    if existente is not None:
        return existente, None
    nova = Cidade.objects.create(cidade=nome, estado=estado, status='A')
    criadas.append(nova)
    return nova, None


def importar(acordos, user, estabelecimento):
    """Grava os acordos na base. DEVE rodar dentro de `transaction.atomic()`.

    Devolve um dicionário de resumo:

        {
            'acordos_criados': [AcordoFaturamento, ...],
            'empresas_criadas': [...],
            'cidades_criadas':  [...],
            'acordos_ignorados': [(cnpj, motivo), ...],
        }

    Regras:
    - A EMPRESA do CNPJ é criada se não existir (o CNPJ é o pagador);
    - A CIDADE é criada em SC se não existir;
    - Os CLIENTES da coluna D viram `Pessoa` (classificação 'paciente') e
      são VINCULADOS ao acordo;
    - O ACORDO importado é criado com `modo_fatura='CO'` (fatura consolidada).
    """
    from admin_cadastros.models import Empresa, Pessoa
    from admin_faturas.models import AcordoFaturamento

    resumo = {
        'acordos_criados': [],
        'empresas_criadas': [],
        'cidades_criadas': [],
        'clientes_criados': [],
        'acordos_ignorados': [],
    }
    agora = timezone.now()

    def _cliente(dados_cliente):
        """Acha (nome + nascimento) ou cria o `Pessoa` paciente."""
        nome = (dados_cliente.get('nome') or '').strip()
        nascimento = dados_cliente.get('nascimento')
        if not nome:
            return None
        filtro = {'nome__iexact': nome}
        if nascimento:
            filtro['dt_nascimento'] = nascimento
        pessoa = Pessoa.objects.filter(**filtro).first()
        if pessoa is not None:
            return pessoa
        pessoa = Pessoa.objects.create(
            nome=nome[:255],
            classificacao_pessoa='paciente',
            nacionalidade='b',
            sexo='f',          # a planilha não traz; ajustável na tela
            alergico='N',
            # `rg`/`cpf` são UNIQUE: a planilha não os traz. Vai `None` (o
            # campo aceita null); `''` violaria a unicidade no 2º cliente.
            rg=None,
            cpf=None,
            dt_nascimento=nascimento,
            estado=_estado_sc(),
            us_registro=user,
            dt_registro=agora,
            status='A')
        resumo['clientes_criados'].append(pessoa)
        return pessoa

    for dados in acordos:
        cnpj = dados['cnpj']
        cidade, erro = _cidade_obj(dados['cidade'], resumo['cidades_criadas'])
        if erro:
            resumo['acordos_ignorados'].append((cnpj, erro))
            continue

        empresa = Empresa.objects.filter(cnpj=cnpj).first()
        if empresa is None:
            # Empresa exige nacionalidade/razao_social/fantasia/empresa/status.
            nome = dados['cidade_rotulo'].split(' - ')
            razao = (f'{nome[0]} - {nome[1]}' if len(nome) > 1
                     else dados['cidade_rotulo'])
            empresa = Empresa.objects.create(
                nacionalidade='Brasileira',
                razao_social=razao[:255],
                fantasia=razao[:255],
                empresa=razao[:255],
                cnpj=cnpj,
                estado=_estado_sc(),
                us_registro=user,
                dt_registro=agora,
                status='A')
            resumo['empresas_criadas'].append(empresa)

        acordo = AcordoFaturamento.objects.create(
            acordo_faturamento=dados['acordo_faturamento'][:255],
            pagador_pj=empresa,
            # Planilha de convênios importa acordos consolidados por padrão.
            modo_fatura='CO',
            modalidade_contrato='CO',
            nr_contrato=(dados['nr_contrato'] or '')[:30],
            empenho_global=(dados['empenho_global'] or '')[:30],
            descricao_internacao='acolhimento',
            inicio_vigencia=dados['inicio_vigencia'],
            final_vigencia=dados['final_vigencia'],
            dia_envio=dados['emitido_no'],
            dias_pagamento=30,
            valor_mensal=dados['valor_mensal'],
            valor_diaria=dados['valor_diaria'],
            tx_retencao_nf=Decimal('0.00'),
            vl_retencao_nf=Decimal('0.00'),
            estabelecimento=estabelecimento,
            us_registro=user,
            dt_registro=agora,
            status='A')
        # CLIENTES: cria (ou acha) as Pessoas da coluna D e vincula ao acordo.
        clientes = [p for p in (_cliente(c) for c in dados.get('clientes', []))
                    if p is not None]
        if clientes:
            acordo.cliente.set(clientes)
        resumo['acordos_criados'].append(acordo)

    return resumo
