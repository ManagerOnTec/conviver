from reportlab.platypus import Table, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle


def genFooterRel(footer_data, width, height):
    # Define o estilo do texto do rodapé
    style = ParagraphStyle(
        name='FooterStyle',
        fontSize=8,
        alignment=1,  # Centralizado
        leftIndent=5,
        rightIndent=5,
        wordWrap='CJK',
        leading=15,
        spaceAfter=5,
    )

    # Verifica se há dados para o rodapé
    if footer_data:
        text = Paragraph(footer_data, style)
    else:
        text = Paragraph("", style)  # Rodapé vazio ou placeholder

    # Lista com as larguras das colunas como frações da largura total
    widthList = [
        width * 5 / 100,  # Largura da primeira coluna (15%)
        width * 90 / 100,  # Largura da segunda coluna (70%)
        width * 5 / 100,  # Largura da terceira coluna (15%)
    ]

    # Estrutura da tabela com o rodapé na coluna central
    data = [['', text, '']]

    # Criação da tabela com as larguras das colunas especificadas
    res = Table(data, colWidths=widthList, rowHeights=[height])

    # Define a cor de fundo para a tabela
    color = colors.HexColor('#003363')

    res.setStyle([
        # Remova ou comente esta linha se a grade não for necessária
        # ('GRID', (0, 0), (-1, -1), 1, 'red'),

        ('LEFTPADDING', (1, 0), (1, 0), 0),
        ('BOTTOMPADDING', (1, 0), (1, 0), 0),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('VALIGN', (1, 0), (1, 0), 'MIDDLE'),
        # ('BACKGROUND', (0, 0), (-1, -1), color),
    ])
    print("Footer Table: ", res)  # Debugging
    return res
