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


def extrair_diaria(descricao):
    """'Diária de R$ 375,84' → Decimal('375.84')."""
    m = RE_DIARIA.search(descricao or '')
    if not m:
        return None
    return _decimal('R$ ' + m.group(1).strip())


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


def extrair_clientes(texto):
    """Acolhidos da coluna D → lista de `(nome, data_nascimento)`.

    Cada acolhido vem em UMA linha da célula:

        Valci Maria Lucindo - 31-08-26
        Marli Moreira de Sa - 16-05-26

    A data depois do último hífen é a data de nascimento (dd-mm-aa). Nome
    é tudo o que vem antes. Linhas sem nome são descartadas.
    """
    from datetime import date, datetime

    clientes = []
    vistos = set()
    for bruto in str(texto or '').splitlines():
        linha = bruto.strip()
        if not linha:
            continue
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
COLUNAS = {
    'acolhidos': 3,
    'quantidade': 4,
    'emitido': 5,
    'referencia': 6,
    'valor': 7,
    'descricao': 10,
    'observacao': 11,
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
        contrato = extrair_contrato(descricao)
        empenho = extrair_empenho(descricao)
        # A DIÁRIA pode estar em TRÊS lugares:
        #   1. na descrição (coluna J): "Diária de R$ 375,84";
        #   2. na observação (coluna K);
        #   3. na FÓRMULA do valor: `=425*9*O$1` → diária 425.
        diaria = (extrair_diaria(descricao)
                  or extrair_diaria(observacao)
                  or extrair_diaria_formula(formula_valor))
        valor = _decimal(cel('valor'))

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
        grupo['valores'].append(valor)
        grupo['linhas'].append(num_linha)
        # CLIENTES da coluna D (um acolhido por linha da célula, com data de
        # nascimento). São acumulados no grupo, sem repetir.
        for nome, nascimento in extrair_clientes(cel('acolhidos')):
            chave_cliente = (normalizar_texto(nome), nascimento)
            if chave_cliente in grupo['_clientes_vistos']:
                continue
            grupo['_clientes_vistos'].add(chave_cliente)
            grupo['clientes'].append(
                {'nome': nome, 'nascimento': nascimento})

    acordos = []
    for grupo in grupos.values():
        competencias = sorted(grupo['competencias'])
        valores = [v for v in grupo['valores'] if v is not None]
        # Acordo POR DIÁRIA: valor_mensal = 0 (o valor real é diária × dias).
        if grupo['valor_diaria']:
            valor_mensal = Decimal('0.00')
        elif valores:
            valor_mensal = valores[0]
            if len(set(valores)) > 1:
                avisos.append(
                    ('alerta',
                     f'{grupo["cidade"]} / CNPJ {grupo["cnpj"]} / CT '
                     f'{grupo["nr_contrato"] or "-"}: valores diferentes no '
                     f'grupo ({", ".join(str(v) for v in sorted(set(valores)))})'
                     ' — usando o primeiro. Confira antes de confirmar.'))
        else:
            valor_mensal = Decimal('0.00')

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
    - O ACORDO é criado com `modo_fatura='CL'` (um cliente por linha).
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
            modo_fatura='CL',
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
