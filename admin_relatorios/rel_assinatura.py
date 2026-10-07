from reportlab.platypus import Table, Paragraph
from reportlab.lib.styles import ParagraphStyle


def genAssinaturaRel(width, height, texto_assinatura=None):
    estilo = ParagraphStyle(
        name='EstiloAssinatura',
        fontSize=8,
        alignment=1,
        leading=10,
        spaceBefore=8,
        spaceAfter=4,
    )

    if texto_assinatura:
        texto_formatado = texto_assinatura.replace('\n', '<br/>')
    else:
        texto_formatado = 'Assinatura Digital'

    paragrafo_assinatura = Paragraph(f"<b>{texto_formatado}</b>", estilo)

    widthList = [
        width * 5 / 100,
        width * 90 / 100,
        width * 5 / 100,
    ]

    data = [['', paragrafo_assinatura, '']]

    tabela_assinatura = Table(data, colWidths=widthList, rowHeights=height)
    tabela_assinatura.setStyle([
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('VALIGN', (1, 0), (1, 0), 'MIDDLE'),
    ])

    return tabela_assinatura
