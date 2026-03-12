
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO
from managerontec import settings
from atendimentos.models import Atendimento
from contas.models import Perfil
from django.core.files.base import ContentFile
from reportlab.lib.units import mm, cm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from dominios.utils import assinar_pdf
import html
import re


def gerar_pdf_evolucao(evolucao):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)

    def desenhar_cabecalho_rodape(p, y_pos_logo):
        # Desenhando bordas
        p.setStrokeColor(colors.black)
        p.rect(margem, margem, width, height, stroke=1, fill=0)

        # Desenhando cabeçalho
        if estabelecimento.logo and os.path.exists(logo_path):
            p.drawImage(logo_path, x_pos_logo, y_pos_logo, 25*mm, 20*mm)
        p.setFont("Helvetica-Bold", 12)
        p.drawCentredString(x_pos_titulo, y_pos_titulo,
                            f"{evolucao.tipo_evolucao}")
        p.line(margem, y_pos_logo - 1*mm, width + margem, y_pos_logo - 1*mm)

        # Desenhando rodapé
        p.line(margem, 15*mm, width + margem, 15*mm)
        p.setFont("Helvetica", 8)
        p.drawString(margem + 5*mm, 11*mm,
                     f"Usuário: {evolucao.us_registro.username}")
        p.drawString(width - 100*mm, 11*mm,
                     f"Data registro: {evolucao.dt_registro.strftime('%d/%m/%Y %H:%M')}")

    # Configurações iniciais
    margem = 1*cm
    espaco_assinatura = 5*cm
    width, height = A4
    width -= 2*margem
    height -= 2*margem

    # Preparando cabeçalho
    x_pos_logo = margem + 5*mm
    y_pos_logo = height + margem - 25*mm
    x_pos_titulo = (width + margem) / 2
    y_pos_titulo = height + margem - 25*mm
    estabelecimento = evolucao.estabelecimento
    logo_path = os.path.join(
        settings.MEDIA_ROOT, estabelecimento.logo.name) if estabelecimento.logo else None

    # Primeira página - Cabeçalho e Rodapé
    desenhar_cabecalho_rodape(p, y_pos_logo)

    # Subcabeçalho com dados da pessoa
    y_pos_corpo = y_pos_logo - 5*mm
    nome_pessoa = evolucao.atendimento.pessoa.nome if evolucao.atendimento.pessoa else "Nome não disponível"
    p.drawString(x_pos_logo, y_pos_corpo, f"Pessoa: {nome_pessoa}")
    y_pos_corpo -= 18*mm

    # Corpo - Campo Evolução
    texto_evolucao = html.unescape(evolucao.evolucao)
    texto_evolucao = re.sub('<[^<]+?>', '', texto_evolucao)
    linhas = texto_evolucao.split('\n')
    for linha in linhas:
        if y_pos_corpo < margem + espaco_assinatura:
            p.showPage()
            desenhar_cabecalho_rodape(p, height + margem - 25*mm)
            y_pos_corpo = height + margem - 25*mm
        p.drawString(x_pos_logo, y_pos_corpo, linha)
        y_pos_corpo -= 15*mm

    # Adicionando assinatura na última página
    if y_pos_corpo >= margem + espaco_assinatura:
        # Espaço para assinatura
        y_pos_assinatura = margem + espaco_assinatura

    # Finalizando o PDF
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer
