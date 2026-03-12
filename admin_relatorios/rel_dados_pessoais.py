from reportlab.platypus import Table, Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors


def genDadosPessoaisRel(dados_pessoais, width, height):
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

    # Criação do parágrafo com os dados pessoais
    if dados_pessoais:
        paragrafo_dados_pessoais = Paragraph(dados_pessoais, style)
    else:
        paragrafo_dados_pessoais = Paragraph(
            "Nenhum dado pessoal disponível.", style)

    # Estrutura da tabela ajustada para colocar os dados na coluna 1
    # A primeira e a última coluna estão vazias
    data = [['', paragrafo_dados_pessoais, '']]

    # Criação da tabela com as larguras das colunas especificadas
    res = Table(data, colWidths=widthList, rowHeights=height)
    res.setStyle([
        # ('GRID', (1, 0), (1, 0), 1, colors.blue),
        # Alinhamento centralizado apenas para a coluna com os dados
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        # Alinhamento vertical no meio apenas para a coluna com os dados
        ('VALIGN', (1, 0), (1, 0), 'MIDDLE'),
    ])
    return res
