"""
Utilitários de importação de medicamentos a partir de planilhas XLSX.

A planilha esperada (ex.: lista_medicamentos_completos.xlsx) tem o seguinte formato:

    Linha 0 (cabeçalho): Grupo | Grupo | Classe | Subclasse | UM | VA
    Linha 1 (rótulos):   Genérico | Comercial | Classe | Único | (vazio) | (vazio)
    Linhas 2..N (dados):
        col A -> nome do medicamento genérico (princípio ativo)
        col B -> nome(s) comercial(is) do(s) produto(s) de referência, separados por "/"
        col C -> classe
        col D -> subclasse (opcional)
        col E -> unidade de medida (opcional, ex.: CPR)
        col F -> via de administração (opcional, ex.: VO, EV, IM)

O importador cria/atualiza automaticamente:
    - Grupo "Medicamento Genérico" (grupo_de_medicamento=True, pode_ser_prescrito=True)
    - Grupo "Medicamento Referência/Comercial" (grupo_de_medicamento=True, pode_ser_prescrito=True)
    - Classe e SubClasse
    - Um Produto por princípio ativo (genérico) e um Produto por nome comercial,
      vinculando o genérico ao seu produto de referência (comercial).
"""

import unicodedata

# Rótulos esperados na segunda linha da planilha (linha de índice 1)
ROTULOS_ESPERADOS = {
    'generico': ['generico'],
    'comercial': ['comercial'],
    'classe': ['classe'],
    'subclasse': ['subclasse', 'sub classe'],
    'um': ['um', 'unidade', 'unidade de medida'],
    'via': ['va', 'via', 'via de administracao'],
}


def normalizar_texto(valor):
    """Normaliza um texto: remove acentos, espaços extras e coloca em maiúsculas."""
    if valor is None:
        return ''
    texto = str(valor).strip()
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return ' '.join(texto.upper().split())


def _limpar(valor):
    """Converte uma célula para string limpa ou None."""
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto if texto else None


def _split_comerciais(valor):
    """Separa os nomes comerciais quando há mais de um (ex.: 'Frontal / Apraz')."""
    if not valor:
        return []
    texto = str(valor)
    # Alguns registros usam vírgula/ponto-e-vírgula além da barra
    for separador in [';', ',']:
        texto = texto.replace(separador, '/')
    partes = [p.strip() for p in texto.split('/')]
    return [p for p in partes if p]


def ler_planilha(caminho_arquivo):
    """
    Lê a planilha e retorna (linhas, avisos).

    Cada item de `linhas` é um dicionário:
        {
            'linha': número da linha na planilha (1-based),
            'generico': str,
            'comerciais': [str, ...],
            'classe': str | None,
            'subclasse': str | None,
            'um': str | None,
            'via': str | None,
        }

    `avisos` é uma lista de mensagens sobre linhas ignoradas.
    """
    try:
        import openpyxl
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "A biblioteca 'openpyxl' é necessária para importar planilhas XLSX. "
            "Instale com: pip install openpyxl"
        ) from exc

    wb = openpyxl.load_workbook(caminho_arquivo, data_only=True)
    ws = wb.active

    linhas = []
    avisos = []

    # Índices das colunas conforme a linha de rótulos (linha 2 da planilha)
    indices = {
        'generico': 0,
        'comercial': 1,
        'classe': 2,
        'subclasse': 3,
        'um': 4,
        'via': 5,
    }

    for num_linha, row in enumerate(ws.iter_rows(values_only=True), start=1):
        # Cabeçalho (linha 1) e rótulos (linha 2)
        if num_linha <= 2:
            continue

        if row is None or all(celula is None for celula in row):
            continue

        def celula(chave):
            idx = indices.get(chave)
            if idx is None or idx >= len(row):
                return None
            return _limpar(row[idx])

        generico = celula('generico')
        comercial = celula('comercial')

        if not generico and not comercial:
            avisos.append(f"Linha {num_linha}: sem genérico e sem comercial, ignorada.")
            continue

        comerciais = _split_comerciais(comercial)

        linhas.append({
            'linha': num_linha,
            'generico': generico,
            'comerciais': comerciais,
            'classe': celula('classe'),
            'subclasse': celula('subclasse'),
            'um': celula('um'),
            'via': celula('via'),
        })

    if not linhas:
        avisos.append("Nenhuma linha de dados válida foi encontrada na planilha.")

    return linhas, avisos


# Mapeamento de via de administração -> registro de ViaAdministracao
VIAS_PADRAO = (
    ('VO', 'Via Oral'),
    ('EV', 'Via Endovenosa'),
    ('IM', 'Via Intramuscular'),
    ('--', 'Não informada'),
)


def _mapa_vias():
    """Monta um dicionário normalizado de sinônimos -> código da via padrão."""
    mapa = {}
    for codigo, descricao in VIAS_PADRAO:
        mapa[normalizar_texto(codigo)] = codigo
        mapa[normalizar_texto(descricao)] = codigo
    mapa[normalizar_texto('VIA ORAL')] = 'VO'
    mapa[normalizar_texto('ORAL')] = 'VO'
    mapa[normalizar_texto('IV')] = 'EV'
    mapa[normalizar_texto('VIA ENDOVENOSA')] = 'EV'
    mapa[normalizar_texto('ENDOVENOSA')] = 'EV'
    mapa[normalizar_texto('INTRAVENOSA')] = 'EV'
    mapa[normalizar_texto('VIA INTRAMUSCULAR')] = 'IM'
    mapa[normalizar_texto('INTRAMUSCULAR')] = 'IM'
    return mapa


def mapear_via(valor):
    """Converte o texto da planilha no código da via de administração."""
    texto = normalizar_texto(valor)
    if not texto:
        return '--'
    return _mapa_vias().get(texto, '--')