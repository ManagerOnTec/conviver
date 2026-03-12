from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, Image, Table
from reportlab.lib import colors


def genHeaderRel(logo_path, header_data, right_data, width, height):
    styles = getSampleStyleSheet()
    centered_style = ParagraphStyle(
        name='CenteredStyle',
        parent=styles['Normal'],
        alignment=1,
        fontSize=14,
        leftIndent=0,  # Ajuste conforme necessário
        rightIndent=0,  # Ajuste conforme necessário
        wordWrap='CJK',
        leading=15,
        spaceAfter=5,
    )

    widthList = [width * 15 / 100, width * 70 / 100, width * 15 / 100]

    leftImage = Image(
        logo_path, widthList[0], height, kind='proportional') if logo_path else ' '
    centerText = Paragraph(header_data, centered_style) if header_data else ' '
    rightText = Paragraph(right_data, centered_style) if right_data else ' '

    res = Table([[leftImage, centerText, rightText]],
                colWidths=widthList, rowHeights=[height])

    res.setStyle([
        # ('GRID', (0, 0), (-1, -1), 1, colors.white),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])

    return res
