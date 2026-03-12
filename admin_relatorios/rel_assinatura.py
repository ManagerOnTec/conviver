from reportlab.platypus import Table, Paragraph
from reportlab.lib.styles import ParagraphStyle


def genAssinaturaRel(width, height):
    # Defina o estilo do parágrafo
    estilo = ParagraphStyle(
        name='EstiloAssinatura',
        fontSize=6,
        alignment=1  # Centralizado
    )

    # Texto de marcação para a assinatura
    texto_assinatura = " "

    # Criação do parágrafo
    paragrafo_assinatura = Paragraph(texto_assinatura, estilo)

    # Lista com as larguras das colunas como frações da largura total
    widthList = [
        width * 5 / 100,  # Largura da primeira coluna (15%)
        width * 90 / 100,  # Largura da segunda coluna (70%)
        width * 5 / 100,  # Largura da terceira coluna (15%)
    ]

    # Estrutura da tabela com o parágrafo na coluna central
    data = [['', paragrafo_assinatura, '']]

    # Criação da tabela com as larguras das colunas especificadas
    tabela_assinatura = Table(data, colWidths=widthList, rowHeights=height)
    tabela_assinatura.setStyle([
        # Alinhamento centralizado apenas para a coluna com o parágrafo
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        # Alinhamento vertical no meio apenas para a coluna com o parágrafo
        ('VALIGN', (1, 0), (1, 0), 'MIDDLE'),
    ])

    # Retorne a tabela como um elemento que pode ser adicionado ao seu PDF
    return tabela_assinatura
