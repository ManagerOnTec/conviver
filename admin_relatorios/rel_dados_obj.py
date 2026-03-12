from reportlab.platypus import Table, Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors


def genDadosObjRel(chave, width, height):
    # Lista com as larguras das colunas como frações da largura total
    widthList = [
        width * 5 / 100,  # col 0 - largura
        width * 90 / 100,  # col 1 - largura
        width * 5 / 100,  # col 2 - largura
    ]

    style = ParagraphStyle(
        name='DadosPessoaisStyle',
        fontSize=12,
        leftIndent=5,
        rightIndent=5,
        wordWrap='CJK',
        leading=15,
        spaceAfter=5,
    )

    # Formatando dados_objeto para garantir que a primeira letra seja maiúscula
    # e concatenando com a chave (pk) para formar o conteúdo do parágrafo
    if chave:
        conteudo_paragrafo = f"Documento : {chave}"
    else:
        conteudo_paragrafo = f"Nenhum dado disponível."

    # Criação do parágrafo com os dados pessoais e a chave
    paragrafo_dados_obj = Paragraph(conteudo_paragrafo, style)

    # Estrutura da tabela ajustada para colocar os dados na coluna 1
    # A primeira e a última coluna estão vazias
    data = [['', paragrafo_dados_obj, '']]

    # Criação da tabela com as larguras das colunas especificadas
    res = Table(data, colWidths=widthList, rowHeights=height)
    res.setStyle([
        # Alinhamento centralizado apenas para a coluna com os dados
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        # Alinhamento vertical no meio apenas para a coluna com os dados
        ('VALIGN', (1, 0), (1, 0), 'MIDDLE'),
    ])
    return res
