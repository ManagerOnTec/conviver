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
        coluna_produto, coluna_intervalo, coluna_sn, coluna_dose, coluna_observacoes, coluna_admin = [
            75 * mm, 20 * mm, 17 * mm, 17 * mm, 30 * mm, 30 * mm]

        for i, linha in enumerate(linhas):
            # Determina o estilo baseado na linha ser cabeçalho ou conteúdo
            estilo_atual = estilo_cabecalho if i == 0 else estilo_paragrafo
            celulas = [Paragraph(c, estilo_atual) for c in linha.split('\t')]
            data_sub_table.append(celulas)

        sub_table = Table(data_sub_table, colWidths=[
                          coluna_produto, coluna_intervalo, coluna_sn, coluna_dose, coluna_observacoes, coluna_admin])
        sub_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
        ]))

        data = [['', sub_table, '']]
        widthList = [width * 5 / 100, width * 90 / 100, width * 5 / 100]

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
