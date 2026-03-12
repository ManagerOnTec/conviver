from reportlab.platypus import Table, Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors


def genDadosUsuarioRel(dados, width, height):
    # Lista com as larguras das colunas como frações da largura total
    widthList = [
        width * 5 / 100,  # col 0 - largura
        width * 90 / 100,  # col 1 - largura
        width * 5 / 100,  # col 2 - largura
    ]

    style = ParagraphStyle(
        name='DadosStyle',
        fontSize=12,
        leftIndent=5,
        rightIndent=5,
        wordWrap='CJK',
        leading=15,
        spaceAfter=2,
    )

    # Criação do parágrafo com os dados pessoais
    if dados:
        paragrafo_dados = Paragraph(dados, style)
    else:
        paragrafo_dados = Paragraph(
            "Nenhum dado pessoal disponível.", style)

    # Estrutura da tabela ajustada para colocar os dados na coluna 1
    # A primeira e a última coluna estão vazias
    data = [['', paragrafo_dados, '']]

    # Criação da tabela com as larguras das colunas especificadas
    res = Table(data, colWidths=widthList, rowHeights=height)
    res.setStyle([
        # Alinhamento centralizado apenas para a coluna com os dados
        ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        # Alinhamento vertical no meio apenas para a coluna com os dados
        ('VALIGN', (1, 0), (1, 0), 'MIDDLE'),
        # ('LEFTPADDING', (0, 0), (-1, -1), 0),
        # ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ])
    return res
