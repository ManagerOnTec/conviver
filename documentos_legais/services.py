import hashlib
from io import BytesIO

from bs4 import BeautifulSoup, NavigableString, Tag
from django.core.files.base import ContentFile
from django.db import connection
from django.db.utils import OperationalError, ProgrammingError
from django.template import Context, Template
from django.utils import timezone
from PyPDF2 import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from admin_relatorios.models import GerenciadorRelatorioGeral, GerenciadorRelatorioPersonalizado
from admin_relatorios.rel_footer import genFooterRel
from admin_relatorios.rel_header import genHeaderRel
from admin_relatorios.utils import assinar_pdf, verificar_assinatura_pdf
from contas.models import Perfil


INLINE_TAGS = {'b', 'strong', 'i', 'em', 'u', 'br'}

# Geometria do campo visual da assinatura digital do certificado (em pontos).
# Precisa ser idêntica à usada em admin_relatorios.utils.assinar_pdf para que o
# espaço reservado no fluxo do PDF não sobreponha a assinatura nem o rodapé.
SIG_BOX_WIDTH_PT = 330
SIG_BOX_HEIGHT_PT = 50
SIG_BOX_BOTTOM_PT = 62
SIG_BOX_TOP_PT = SIG_BOX_BOTTOM_PT + SIG_BOX_HEIGHT_PT

# Altura reservada para o bloco de identificação (título + tabela do código/IP),
# desenhado no rodapé da última página.
SIG_CODIGO_HEIGHT_PT = 58


def obter_ip_cliente(request):
    """Retorna o IP do cliente considerando proxy reverso (X-Forwarded-For).

    Em ambientes atrás de proxy (ex.: GCP/Nginx), REMOTE_ADDR contém o IP do
    proxy, não do cliente. O primeiro valor de X-Forwarded-For é o IP original
    do cliente. Há fallback para REMOTE_ADDR quando o header não existe.
    """
    if request is None:
        return ''

    encaminhado = request.META.get('HTTP_X_FORWARDED_FOR')
    if encaminhado:
        ip = encaminhado.split(',')[0].strip()
        if ip:
            return ip

    return (request.META.get('REMOTE_ADDR') or '').strip()


def _table_has_column(model, column_name):
    table_name = model._meta.db_table

    try:
        if table_name not in set(connection.introspection.table_names()):
            return False

        with connection.cursor() as cursor:
            description = connection.introspection.get_table_description(cursor, table_name)
    except (OperationalError, ProgrammingError):
        return False

    return any(column.name == column_name for column in description)


def _resolve_documento_relatorio(documento):
    gerenciador_personalizado = None
    gerenciador_geral = None

    try:
        if _table_has_column(GerenciadorRelatorioPersonalizado, 'tipo_documento_legal_id'):
            gerenciador_personalizado = GerenciadorRelatorioPersonalizado.objects.filter(
                relatorio='documentos_legais',
                tipo_documento_legal=documento.tipo_documento,
                estabelecimento_id=documento.estabelecimento_id,
                status='A',
            ).first()
    except (OperationalError, ProgrammingError):
        gerenciador_personalizado = None

    try:
        if GerenciadorRelatorioGeral._meta.db_table in set(connection.introspection.table_names()):
            gerenciador_geral = GerenciadorRelatorioGeral.objects.filter(
                estabelecimento_id=documento.estabelecimento_id,
                status='A',
            ).first()
    except (OperationalError, ProgrammingError):
        gerenciador_geral = None

    return gerenciador_personalizado or gerenciador_geral


def build_document_context(atendimento, responsavel_data=None):
    pessoa = atendimento.pessoa
    estabelecimento = atendimento.estabelecimento
    responsavel_data = responsavel_data or {}

    data_nascimento = pessoa.dt_nascimento.strftime('%d/%m/%Y') if pessoa and pessoa.dt_nascimento else ''
    responsavel_nascimento = responsavel_data.get('responsavel_data_nascimento')
    if responsavel_nascimento:
        responsavel_nascimento = responsavel_nascimento.strftime('%d/%m/%Y')
    else:
        responsavel_nascimento = ''

    return {
        'atendimento_id': atendimento.pk,
        'paciente_nome': pessoa.nome if pessoa else '',
        'paciente_cpf': pessoa.cpf if pessoa else '',
        'paciente_dt_nascimento': data_nascimento,
        'estabelecimento_nome': estabelecimento.estabelecimento if estabelecimento else '',
        'responsavel_nome': responsavel_data.get('responsavel_nome', ''),
        'responsavel_cpf': responsavel_data.get('responsavel_cpf', ''),
        'responsavel_documento': responsavel_data.get('responsavel_documento', ''),
        'responsavel_data_nascimento': responsavel_nascimento,
        'responsavel_telefone': responsavel_data.get('responsavel_telefone', ''),
        'responsavel_email': responsavel_data.get('responsavel_email', ''),
        'data_documento': timezone.localtime().strftime('%d/%m/%Y %H:%M'),
    }


def render_documento_html(modelo_documento, atendimento, responsavel_data=None):
    contexto = build_document_context(atendimento, responsavel_data)
    template = Template(modelo_documento.conteudo_html)
    return template.render(Context(contexto))


def _sanitize_inline_html(html):
    soup = BeautifulSoup(html or '', 'html.parser')
    for tag in list(soup.find_all(True)):
        if tag.name not in INLINE_TAGS:
            tag.unwrap()
            continue
        if tag.name == 'strong':
            tag.name = 'b'
        elif tag.name == 'em':
            tag.name = 'i'
        tag.attrs = {}
    return str(soup)


def html_to_flowables(html_content, body_style):
    soup = BeautifulSoup(html_content or '', 'html.parser')
    flowables = []
    block_tags = {'p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}

    def append_block(text_html, style=None, prefix=''):
        sanitized = _sanitize_inline_html(text_html)
        text_only = BeautifulSoup(sanitized, 'html.parser').get_text(' ', strip=True)
        if not text_only and '&nbsp;' not in sanitized:
            flowables.append(Spacer(1, 4 * mm))
            return
        if prefix:
            sanitized = f'{prefix}{sanitized}'
        flowables.append(Paragraph(sanitized, style or body_style))
        flowables.append(Spacer(1, 3 * mm))

    for node in soup.contents:
        if isinstance(node, NavigableString):
            text = str(node).strip()
            if text:
                append_block(text)
            continue

        if not isinstance(node, Tag):
            continue

        if node.name in block_tags:
            append_block(node.decode_contents())
            continue

        if node.name in {'ul', 'ol'}:
            for index, li in enumerate(node.find_all('li', recursive=False), start=1):
                prefix = '• ' if node.name == 'ul' else f'{index}. '
                append_block(li.decode_contents(), prefix=prefix)
            continue

        append_block(node.decode_contents())

    if not flowables:
        flowables.append(Paragraph('Nenhum conteúdo disponível.', body_style))
    return flowables


def _scaled_reportlab_image(file_field, max_width_mm=80, max_height_mm=55):
    image = Image(file_field.path)
    max_width = max_width_mm * mm
    max_height = max_height_mm * mm
    ratio = min(max_width / image.drawWidth, max_height / image.drawHeight)
    image.drawWidth *= ratio
    image.drawHeight *= ratio
    return image


def _pdf_bytes_validos(pdf_bytes):
    if not pdf_bytes or not isinstance(pdf_bytes, (bytes, bytearray)):
        return False
    if not bytes(pdf_bytes).startswith(b'%PDF'):
        return False
    try:
        PdfReader(BytesIO(pdf_bytes))
        return True
    except Exception:
        return False


def gerar_pdf_documento_legal(documento, reservar_assinatura_digital=False):
    buffer = BytesIO()
    gerenciador_relatorio = _resolve_documento_relatorio(documento)

    logo_path = None
    header_data = None
    right_data = None
    footer_data = None

    if gerenciador_relatorio:
        logo_path = gerenciador_relatorio.logo_header.path if gerenciador_relatorio.logo_header else None
        header_data = str(gerenciador_relatorio.dados_header) if gerenciador_relatorio.dados_header else None
        right_data = str(gerenciador_relatorio.dados_right_header) if gerenciador_relatorio.dados_right_header else None
        footer_data = str(gerenciador_relatorio.dados_footer) if gerenciador_relatorio.dados_footer else None

    # Reserva a faixa inferior empilhando, de baixo para cima: rodapé, campo visual da
    # assinatura digital do certificado (quando aplicável) e o bloco de identificação com
    # o código. Assim o fluxo do conteúdo nunca sobrepõe nenhum desses elementos.
    footer_top_pt = (6 * mm) + (10 * mm) if footer_data else 0
    faixa_inferior_pt = max(footer_top_pt, SIG_BOX_TOP_PT if reservar_assinatura_digital else 0)
    bottom_margin_pt = faixa_inferior_pt + SIG_CODIGO_HEIGHT_PT + (4 * mm)

    output = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=26 * mm,
        bottomMargin=bottom_margin_pt,
        title=documento.titulo_documento,
        author=documento.us_registro.username if documento.us_registro else 'Sistema',
        subject=f'Documento legal {documento.codigo_documento}',
    )

    styles = getSampleStyleSheet()
    section_style = ParagraphStyle('DocLegalSecao', parent=styles['Heading4'], fontSize=11, leading=13, spaceAfter=6)
    body_style = ParagraphStyle('DocLegalCorpo', parent=styles['BodyText'], fontSize=10, leading=14, spaceAfter=4)

    pessoa = documento.pessoa

    def _build_story():
        story = []

        story.append(Paragraph('Dados do Paciente', section_style))
        paciente_rows = [
            ['Atendimento', str(documento.atendimento_id)],
            ['Paciente', pessoa.nome if pessoa else ''],
            ['CPF', pessoa.cpf if pessoa else ''],
            ['Data de Nascimento', pessoa.dt_nascimento.strftime('%d/%m/%Y') if pessoa and pessoa.dt_nascimento else ''],
        ]
        paciente_table = Table(paciente_rows, colWidths=[40 * mm, 125 * mm])
        paciente_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
        story.extend([paciente_table, Spacer(1, 4 * mm)])

        story.append(Paragraph('Dados do Responsável', section_style))
        responsavel_rows = [
            ['Nome', documento.responsavel_nome],
            ['CPF', documento.responsavel_cpf],
            ['Documento', documento.responsavel_documento],
            ['Nascimento', documento.responsavel_data_nascimento.strftime('%d/%m/%Y') if documento.responsavel_data_nascimento else ''],
            ['Telefone', documento.responsavel_telefone or ''],
            ['E-mail', documento.responsavel_email or ''],
            ['Assinado em', timezone.localtime(documento.dt_assinatura).strftime('%d/%m/%Y %H:%M') if documento.dt_assinatura else ''],
        ]
        responsavel_table = Table(responsavel_rows, colWidths=[40 * mm, 125 * mm])
        responsavel_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
        story.extend([responsavel_table, Spacer(1, 5 * mm)])

        story.append(Paragraph('Dados do Atendente', section_style))
        atendente_rows = [
            ['Nome', atendente_nome],
            ['CPF', atendente_cpf],
        ]
        atendente_table = Table(atendente_rows, colWidths=[40 * mm, 125 * mm])
        atendente_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
        story.extend([atendente_table, Spacer(1, 5 * mm)])

        story.extend(html_to_flowables(documento.conteudo_html, body_style))
        story.append(Spacer(1, 6 * mm))

        if documento.assinatura_imagem:
            story.append(KeepTogether([
                _scaled_reportlab_image(documento.assinatura_imagem, 70, 30),
                Spacer(1, 2 * mm),
                Paragraph('Assinatura do Responsável', section_style),
            ]))
            story.append(Spacer(1, 4 * mm))

        foto_validacao = documento.selfie or documento.documento_frente or documento.documento_verso
        if foto_validacao:
            story.append(KeepTogether([
                _scaled_reportlab_image(foto_validacao),
                Spacer(1, 2 * mm),
                Paragraph('Foto de Validação', section_style),
            ]))

        return story

    atendente = getattr(getattr(documento.us_registro, 'perfil', None), 'pessoa', None) if documento.us_registro else None
    if atendente:
        atendente_nome = atendente.nome
    elif documento.us_registro:
        atendente_nome = documento.us_registro.get_full_name() or documento.us_registro.username
    else:
        atendente_nome = ''
    atendente_cpf = (atendente.cpf or '') if atendente else ''

    codigo_style = ParagraphStyle(
        'DocLegalCodigo',
        parent=styles['BodyText'],
        fontSize=12,
        leading=15,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1a1a1a'),
    )
    codigo_table = Table(
        [
            ['Código do Documento', Paragraph(documento.codigo_documento, codigo_style)],
            ['Emitido em', timezone.localtime(documento.dt_registro).strftime('%d/%m/%Y %H:%M') if documento.dt_registro else ''],
            ['IP', documento.ip_assinatura or 'não registrado'],
        ],
        colWidths=[40 * mm, 125 * mm],
    )
    codigo_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f2f4f7')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#adb5bd')),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    codigo_titulo = Paragraph('Identificação do Documento', section_style)

    draw_state = {'total_pages': 1}

    def draw_header_footer(canvas_obj, doc):
        page_width, page_height = A4

        if logo_path or header_data or right_data:
            header_table = genHeaderRel(logo_path, header_data, right_data, doc.width, 16 * mm)
            header_table.wrapOn(canvas_obj, doc.width, page_height)
            header_y = page_height - 10 * mm
            table_h = getattr(header_table, '_height', 16 * mm)
            header_table.drawOn(canvas_obj, doc.leftMargin, header_y - table_h)

        if footer_data:
            footer_table = genFooterRel(footer_data, doc.width, 10 * mm)
            footer_table.wrapOn(canvas_obj, doc.width, page_height)
            footer_table.drawOn(canvas_obj, doc.leftMargin, 6 * mm)

        # Bloco de identificação desenhado apenas na última página, empilhado acima do
        # rodapé e da faixa reservada para a assinatura digital do certificado.
        if doc.page == draw_state['total_pages']:
            footer_top = (6 * mm) + (10 * mm) if footer_data else 0
            base_y = max(footer_top, SIG_BOX_TOP_PT if reservar_assinatura_digital else 0) + (2 * mm)
            try:
                tw, th = codigo_titulo.wrap(doc.width, page_height)
                codigo_titulo.drawOn(canvas_obj, doc.leftMargin, base_y + SIG_CODIGO_HEIGHT_PT - th)
            except Exception:
                pass
            try:
                ctw, cth = codigo_table.wrap(doc.width, page_height)
                codigo_table.drawOn(canvas_obj, doc.leftMargin, base_y)
            except Exception:
                pass

    # Primeira passada: descobre o total de páginas usando um story novo (os flowables
    # são mutados durante o build, então cada passada precisa de objetos próprios).
    preview_buffer = BytesIO()
    preview_output = SimpleDocTemplate(
        preview_buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=26 * mm,
        bottomMargin=bottom_margin_pt,
    )
    preview_output.build(_build_story(), onFirstPage=lambda c, d: None, onLaterPages=lambda c, d: None)
    try:
        import pymupdf as _pymupdf
        draw_state['total_pages'] = _pymupdf.open(stream=preview_buffer.getvalue(), filetype='pdf').page_count
    except Exception:
        draw_state['total_pages'] = 1

    output.build(_build_story(), onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
    buffer.seek(0)
    return buffer.getvalue()


def atualizar_pdf_documento(documento, user=None, assinar_funcionario=False):
    perfil = None
    certificado_field = None
    senha_certificado = None

    if assinar_funcionario and user:
        perfil = Perfil.objects.filter(user=user).first()
        certificado_field = getattr(perfil, 'certificado_digital', None) if perfil else None
        senha_certificado = getattr(perfil, 'senha_certificado', None) if perfil else None

    # Só reserva a faixa da assinatura digital no PDF quando ela realmente será aplicada.
    reservar_assinatura_digital = bool(certificado_field and senha_certificado)

    pdf_bytes = gerar_pdf_documento_legal(documento, reservar_assinatura_digital=reservar_assinatura_digital)
    pdf_final_bytes = pdf_bytes
    assinatura_funcionario_aplicada = False

    if reservar_assinatura_digital:
        with certificado_field.open('rb') as certificado_file:
            certificado_bytes = certificado_file.read()

        datau, datas, assinado = assinar_pdf(
            senha_certificado,
            certificado_bytes,
            BytesIO(pdf_bytes),
            62,
        )

        pdf_completo = BytesIO()
        pdf_completo.write(datau)
        if assinado:
            pdf_completo.write(datas)
        pdf_completo.seek(0)

        candidato = pdf_completo.read() if assinado else pdf_bytes
        if assinado and _pdf_bytes_validos(candidato) and verificar_assinatura_pdf(candidato, certificado_bytes, senha_certificado):
            pdf_final_bytes = candidato
            assinatura_funcionario_aplicada = True

    documento.hash_pdf = hashlib.sha256(pdf_final_bytes).hexdigest()
    documento.pdf_gerado.save(f'{documento.codigo_documento}.pdf', ContentFile(pdf_final_bytes), save=False)
    documento.save(update_fields=['pdf_gerado', 'hash_pdf'])
    return assinatura_funcionario_aplicada
