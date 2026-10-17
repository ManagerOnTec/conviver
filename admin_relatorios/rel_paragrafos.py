from reportlab.platypus import Table, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
from reportlab.platypus import TableStyle
from reportlab.lib.units import mm
from prontuarios.models import Adep
import re
from bs4 import BeautifulSoup, NavigableString, Tag


INLINE_TAGS = {'b', 'strong', 'i', 'em', 'u', 'br'}
BLOCK_ALIGNMENT_MAP = {
    'left': 0,
    'center': 1,
    'right': 2,
    'justify': 4,
}


def _style_contains(style_value, css_property, expected_values):
    if not style_value:
        return False

    normalized = style_value.lower().replace(' ', '')
    for expected in expected_values:
        if f'{css_property}:{expected}' in normalized:
            return True
    return False


def _extract_text_align(style_value):
    if not style_value:
        return None

    match = re.search(r'text-align\s*:\s*(left|center|right|justify)', style_value, re.IGNORECASE)
    if not match:
        return None

    return match.group(1).lower()


def limpar_html_para_pdf(texto):
    # Limpa HTML, removendo atributos de estilo e convertendo tags inválidas para as válidas pelo ReportLab.

    if not texto:
        return ""

    soup = BeautifulSoup(texto, "html.parser")

    for tag in soup.find_all(True):  # Itera sobre todas as tags
        if tag.has_attr('style'):
            del tag['style']  # Remove estilos inline

        # Mapeamento para substituição de tags incompatíveis
        substituicoes = {
            'h1': 'para',
            'h2': 'para',
            'h3': 'para',
            'span': None  # Removemos a tag e mantemos apenas o texto
        }

        if tag.name in substituicoes:
            tag.name = substituicoes[tag.name]

        # Garante que todas as tags estão corretamente fechadas
        if tag.name in ['b', 'i', 'u', 'para'] and not tag.text.strip():
            tag.decompose()  # Remove tags vazias para evitar erro de fechamento

    # Converte o HTML final para string garantindo formatação válida
    html_corrigido = str(soup)

    return html_corrigido


def _sanitize_inline_html(texto):
    soup = BeautifulSoup(texto or '', 'html.parser')

    for tag in list(soup.find_all(True)):
        style_value = tag.attrs.get('style', '')

        if tag.name == 'span':
            wrapper_names = []
            if _style_contains(style_value, 'font-weight', {'bold', '700', '800', '900'}):
                wrapper_names.append('b')
            if _style_contains(style_value, 'font-style', {'italic', 'oblique'}):
                wrapper_names.append('i')
            if _style_contains(style_value, 'text-decoration', {'underline'}):
                wrapper_names.append('u')

            if wrapper_names:
                tag.name = wrapper_names[0]
                current_tag = tag
                for wrapper_name in wrapper_names[1:]:
                    wrapper = soup.new_tag(wrapper_name)
                    while current_tag.contents:
                        wrapper.append(current_tag.contents[0].extract())
                    current_tag.append(wrapper)
                    current_tag = wrapper

        if tag.name not in INLINE_TAGS:
            tag.unwrap()
            continue

        if tag.name == 'strong':
            tag.name = 'b'
        elif tag.name == 'em':
            tag.name = 'i'

        tag.attrs = {}

    return str(soup)


def _append_html_block(flowables, texto, estilo, prefixo=''):
    texto_sanitizado = _sanitize_inline_html(texto)
    texto_limpo = BeautifulSoup(texto_sanitizado, 'html.parser').get_text(' ', strip=True)

    if not texto_limpo and '&nbsp;' not in texto_sanitizado:
        flowables.append(Spacer(1, 3 * mm))
        return

    if prefixo:
        texto_sanitizado = f'{prefixo}{texto_sanitizado}'

    flowables.append(Paragraph(texto_sanitizado, estilo))
    flowables.append(Spacer(1, 2 * mm))


def _resolve_block_style(node, estilo_base, cache):
    alignment_name = None

    if isinstance(node, Tag):
        alignment_name = _extract_text_align(node.attrs.get('style', ''))
        if not alignment_name:
            align_attr = (node.attrs.get('align') or '').strip().lower()
            if align_attr in BLOCK_ALIGNMENT_MAP:
                alignment_name = align_attr

    if not alignment_name:
        return estilo_base

    alignment_value = BLOCK_ALIGNMENT_MAP[alignment_name]
    if alignment_value not in cache:
        cache[alignment_value] = ParagraphStyle(
            name=f'{estilo_base.name}_{alignment_name}',
            parent=estilo_base,
            alignment=alignment_value,
        )

    return cache[alignment_value]


def _build_html_flowables(parag, estilo):
    soup = BeautifulSoup(parag or '', 'html.parser')
    flowables = []
    block_tags = {'p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
    style_cache = {}

    for node in soup.contents:
        if isinstance(node, NavigableString):
            texto = str(node).strip()
            if texto:
                _append_html_block(flowables, texto, estilo)
            continue

        if not isinstance(node, Tag):
            continue

        if node.name in block_tags:
            _append_html_block(flowables, node.decode_contents(), _resolve_block_style(node, estilo, style_cache))
            continue

        if node.name in {'ul', 'ol'}:
            for indice, item in enumerate(node.find_all('li', recursive=False), start=1):
                prefixo = '• ' if node.name == 'ul' else f'{indice}. '
                _append_html_block(
                    flowables,
                    item.decode_contents(),
                    _resolve_block_style(item, estilo, style_cache),
                    prefixo=prefixo,
                )
            continue

        _append_html_block(flowables, node.decode_contents(), _resolve_block_style(node, estilo, style_cache))

    if not flowables:
        flowables.append(Paragraph('Nenhum texto disponível.', estilo))

    return flowables


def _build_tabela_prescricao_adep(parag, width, estilo_paragrafo, estilo_cabecalho):
    """Monta a tabela de prescrição/ADEP de forma paginável.

    Devolve uma **única** ``Table`` com o cabeçalho na primeira linha e
    ``repeatRows=1``. Assim o ReportLab repete o cabeçalho **apenas** quando a
    tabela é quebrada entre páginas, garantindo exatamente um cabeçalho no
    início de cada página.

    Antes a tabela era fatiada manualmente em blocos, cada bloco com o seu
    próprio cabeçalho. Isso fazia o cabeçalho reaparecer uma vez por bloco,
    inclusive no meio de uma página, gerando cabeçalhos repetidos (ex.: duas
    páginas com três cabeçalhos).

    Colunas:
      * ``produto``      -> única coluna que aceita quebrar em várias linhas;
      * ``intervalo``, ``sn``, ``dose``, ``observacoes``, ``administrado``
                         -> dados curtos, sempre em linha (uma linha só).

    O conteúdo de cada célula é interpretado como HTML pelo ``Paragraph``,
    então é possível enviar marcações simples (``<b>``, ``<i>``, ``<br/>``).
    O separador de linhas da tabela é o fim de linha (``\\n``); o ``<br/>``
    fica restrito ao interior da célula (quebra dentro do produto).
    """
    # Remove tags HTML incompatíveis com o ReportLab, preservando <br/>,
    # <b>, <i> e <u> (que o Paragraph entende).
    parag = limpar_html_para_pdf(parag)

    # Normaliza CRLF e separa as linhas da tabela por fim de linha.
    linhas = [linha for linha in parag.replace('\r\n', '\n').split('\n')]

    # A soma das larguras deve caber na largura útil da página (A4 = 210mm
    # menos as margens laterais de 12mm de cada lado = 186mm). A versão
    # anterior somava 189mm e forçava o ReportLab a comprimir/quebrar as
    # células do cabeçalho em várias linhas.
    #
    # Somente a coluna do produto pode quebrar em várias linhas. As demais
    # colunas (H, SN, Única/Sim, Obs/Administrado, Adep/Não Adm.) têm largura
    # dimensionada para caber o conteúdo em uma única linha por produto.
    #
    # Ajuste de proporção: Intervalos/SN/Única reduzidos, Administrados e Não
    # administrados reduzidos levemente e Vigência (coluna do produto, que traz
    # "Vigência: início à fim") ampliada para exibir o período com folga.
    coluna_produto = 72 * mm
    coluna_intervalo = 18 * mm
    coluna_sn = 12 * mm
    coluna_dose = 12 * mm
    coluna_observacoes = 33 * mm
    coluna_admin = 39 * mm
    col_widths = [coluna_produto, coluna_intervalo, coluna_sn,
                  coluna_dose, coluna_observacoes, coluna_admin]

    col_style = TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        # A coluna de produto é alinhada à esquerda e aceita quebra de linha;
        # as demais permanecem centralizadas e em uma única linha.
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
    ])

    # Estilo do cabeçalho: fonte um pouco menor para que descrições como
    # "Vigência", "Administrado" e "Não Adm." caibam em uma única linha.
    estilo_cabecalho = ParagraphStyle(
        name='CabecalhoTabelaStyle',
        parent=estilo_cabecalho,
        fontSize=8,
        leading=10,
        spaceAfter=0,
        wordWrap=False,
        splitLongWords=False,
    )

    # Estilo das células de dados: nunca quebra linha (uma linha por produto).
    estilo_dados = ParagraphStyle(
        name='DadosTabelaStyle',
        parent=estilo_paragrafo,
        fontSize=9,
        leading=11,
        spaceAfter=0,
        leftIndent=0,
        rightIndent=0,
        wordWrap=False,
        splitLongWords=False,
    )

    # Converte cada linha textual (separada por tabulações) em células Paragraph.
    linhas_celulas = []
    for indice, linha in enumerate(linhas):
        if not linha.strip():
            continue
        eh_cabecalho = not linhas_celulas
        celulas = []
        for coluna in linha.split('\t'):
            # O cabeçalho usa o estilo compacto; as demais células usam o
            # estilo de dados que não quebra linha. A coluna do produto
            # (índice 0) continua podendo quebrar em várias linhas.
            if eh_cabecalho:
                celulas.append(Paragraph(coluna, estilo_cabecalho))
            else:
                celulas.append(Paragraph(coluna, estilo_dados))
        linhas_celulas.append(celulas)

    if not linhas_celulas:
        return [Paragraph('Nenhum item prescrito.', estilo_paragrafo)]

    cabecalho = linhas_celulas[0]
    corpo = linhas_celulas[1:]

    # Uma única ``Table`` contínua com ``repeatRows=1``: o próprio ReportLab
    # pagina o conteúdo (via ``split``) e repete o cabeçalho APENAS nas quebras
    # de página. A versão anterior dividia em blocos de 14 linhas e cada bloco
    # carregava o seu próprio cabeçalho, o que fazia o cabeçalho aparecer no
    # meio da página (2 ou 3 cabeçalhos por página) — o bug relatado.
    dados = [cabecalho] + corpo
    tabela = Table(dados, colWidths=col_widths, repeatRows=1)
    tabela.setStyle(col_style)
    return [tabela]


def genParagrafosRel(parag, width, height, p, tipo="evolucao"):
    margem_lateral = width * 5 / 100

    estilo_paragrafo = ParagraphStyle(
        name='ParagrafoStyle',
        fontSize=10,
        leftIndent=margem_lateral,
        rightIndent=margem_lateral,
        wordWrap=True,
        leading=15,
        spaceAfter=6,
    )

    # Definindo o estilo do cabeçalho
    estilo_cabecalho = ParagraphStyle(
        name='CabecalhoStyle',
        fontSize=10,
        alignment=1,  # Centralizado
        leftIndent=margem_lateral,
        rightIndent=margem_lateral,
        wordWrap=True,
        leading=15,
        spaceAfter=6,
    )

    if tipo in {"evolucao", "atas", "oficios", "orcamentos"}:
        return _build_html_flowables(parag, estilo_paragrafo)

    # Prescrição/ADEP precisam manter as quebras internas de célula (<br/>)
    # e usar o fim de linha (\n) como separador de linhas da tabela. Por isso
    # são tratados antes do split global por '<br/>' abaixo.
    if tipo in ["prescricao", "adep"]:
        return _build_tabela_prescricao_adep(
            parag, width, estilo_paragrafo, estilo_cabecalho)

    parag = limpar_html_para_pdf(parag)  # Limpa o HTML antes de processar

    # Substitui quebras de linha por <br/> e divide o texto
    # Corrigido: substitui '\n' por '<br/>'
    parag = parag.replace('\n', '<br/>')
    linhas = parag.split('<br/>')  # Divide o texto por '<br/>'

    data_sub_table = []

    # Tratamento específico para o tipo "diagnostico"
    if tipo == "diagnostico":
        # Supondo que 'parag' seja uma string formatada com diagnósticos e observação como descrito

        parag = limpar_html_para_pdf(parag)  # Limpa o HTML antes de processar

        # Substitui quebras de linha por <br/> e divide o texto
        # Corrigido: substitui '\n' por '<br/>'
        parag = parag.replace('\n', '<br/>')
        linhas = parag.split('<br/>')  # Divide o texto por '<br/>'

        data_sub_table = []

        for linha in linhas:
            celula = [Paragraph(linha, estilo_paragrafo)]
            data_sub_table.append(celula)

        sub_table = Table(data_sub_table, colWidths=[width * 90 / 100])
        sub_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            # ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
            # ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
        ]))

        data = [['', sub_table, '']]
        widthList = [width * 5 / 100, width * 90 / 100, width * 5 / 100]

    elif tipo in ["prescricao", "adep"]:
        # Tratado acima (antes do split global), mantido apenas por segurança.
        return _build_tabela_prescricao_adep(
            linhas, width, estilo_paragrafo, estilo_cabecalho)

    elif tipo == "sinaisvitais":
        # Primeiro, dividimos o parágrafo por linhas
        parag = limpar_html_para_pdf(parag)  # Limpa o HTML antes de processar

        # Substitui quebras de linha por <br/> e divide o texto
        # Corrigido: substitui '\n' por '<br/>'
        parag = parag.replace('\n', '<br/>')
        linhas = parag.split('<br/>')  # Divide o texto por '<br/>'

        data_sub_table = []

        for linha in linhas:
            # Aqui, dividimos cada linha por tabulações, esperando que cada parte seja tratada como uma nova linha na tabela
            partes = linha.split('\t')
            for parte in partes:
                # Para cada parte, criamos uma nova linha na tabela com a parte como conteúdo
                if parte:  # Verifica se a parte não está vazia
                    celula = [Paragraph(parte, estilo_paragrafo)]
                    data_sub_table.append(celula)

        # Cria a sub-tabela com os dados formatados dos sinais vitais, considerando cada tabulação como uma nova linha
        sub_table = Table(data_sub_table, colWidths=[width * 90 / 100])
        sub_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        # Define a estrutura geral da tabela como feito para os outros tipos
        data = [['', sub_table, '']]
        widthList = [width * 5 / 100, width * 90 / 100, width * 5 / 100]

    elif tipo == "sae":
        # Primeiro, dividimos o parágrafo por linhas, considerando que cada '\t' inicia uma nova linha
        parag = limpar_html_para_pdf(parag)  # Limpa o HTML antes de processar

        # Substitui quebras de linha por <br/> e divide o texto
        # Corrigido: substitui '\n' por '<br/>'
        parag = parag.replace('\n', '<br/>')
        linhas = parag.split('<br/>')  # Divide o texto por '<br/>'

        data_sub_table = []

        for linha in linhas:
            # Verifica se a linha não está vazia antes de adicionar à tabela
            if linha.strip():  # Remove espaços em branco e verifica se a linha não está vazia
                # Cria uma nova célula de parágrafo para cada linha
                celula = [Paragraph(linha, estilo_paragrafo)]
                data_sub_table.append(celula)

        # Cria a sub-tabela com os dados formatados do SAE, considerando cada parte como uma nova linha
        sub_table = Table(data_sub_table, colWidths=[width * 90 / 100])
        sub_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        # Define a estrutura geral da tabela como feito para os outros tipos
        data = [['', sub_table, '']]
        widthList = [width * 5 / 100, width * 90 / 100, width * 5 / 100]

    elif tipo == "planocuidados":
        # Primeiro, dividimos o parágrafo por linhas
        parag = limpar_html_para_pdf(parag)  # Limpa o HTML antes de processar

        # Substitui quebras de linha por <br/> e divide o texto
        # Corrigido: substitui '\n' por '<br/>'
        parag = parag.replace('\n', '<br/>')
        linhas = parag.split('<br/>')  # Divide o texto por '<br/>'

        data_sub_table = []

        for linha in linhas:
            # Aqui, dividimos cada linha por tabulações, esperando que cada parte seja tratada como uma nova linha na tabela
            partes = linha.split('\t')
            for parte in partes:
                # Para cada parte, criamos uma nova linha na tabela com a parte como conteúdo
                if parte:  # Verifica se a parte não está vazia
                    celula = [Paragraph(parte, estilo_paragrafo)]
                    data_sub_table.append(celula)

        # Cria a sub-tabela com os dados formatados do Plano de Cuidados, considerando cada tabulação como uma nova linha
        sub_table = Table(data_sub_table, colWidths=[width * 90 / 100])
        sub_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        # Define a estrutura geral da tabela como feito para os outros tipos
        data = [['', sub_table, '']]
        widthList = [width * 5 / 100, width * 90 / 100, width * 5 / 100]

    elif tipo == "perdasganhos":
        # Primeiro, dividimos o parágrafo por linhas
        parag = limpar_html_para_pdf(parag)  # Limpa o HTML antes de processar

        # Substitui quebras de linha por <br/> e divide o texto
        # Corrigido: substitui '\n' por '<br/>'
        parag = parag.replace('\n', '<br/>')
        linhas = parag.split('<br/>')  # Divide o texto por '<br/>'

        data_sub_table = []

        for linha in linhas:
            # Aqui, dividimos cada linha por tabulações, esperando que cada parte seja tratada como uma nova linha na tabela
            partes = linha.split('\t')
            for parte in partes:
                # Para cada parte, criamos uma nova linha na tabela com a parte como conteúdo
                if parte:  # Verifica se a parte não está vazia
                    celula = [Paragraph(parte, estilo_paragrafo)]
                    data_sub_table.append(celula)

        # Cria a sub-tabela com os dados formatados de Perdas e Ganhos, considerando cada tabulação como uma nova linha
        sub_table = Table(data_sub_table, colWidths=[width * 90 / 100])
        sub_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        # Define a estrutura geral da tabela como feito para os outros tipos
        data = [['', sub_table, '']]
        widthList = [width * 5 / 100, width * 90 / 100, width * 5 / 100]

    else:
        # Para outros tipos que não são 'prescricao' nem 'adep', usa-se um parágrafo simples
        paragrafo = Paragraph(parag, estilo_paragrafo) if parag else Paragraph(
            "Nenhum texto disponível.", estilo_paragrafo)
        data = [['', paragrafo, '']]
        widthList = [width * 5 / 100, width * 90 / 100, width * 5 / 100]

    # Cria a tabela resultante com as configurações definidas.
    # A altura deve ser calculada pelo próprio flowable para permitir a quebra automática de páginas.
    res = Table(data, colWidths=widthList)
    res.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('VALIGN', (1, 0), (1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    return res
