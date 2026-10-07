from .models import Diagnostico
from django.http import JsonResponse
from django.contrib.contenttypes.fields import ContentType
from PyPDF2 import PdfReader, PdfWriter
from admin_relatorios.utils import assinar_pdf, obter_dados_assinatura_certificado, verificar_assinatura_pdf
from contas.models import Perfil
from prontuarios.models import Adep
from prontuarios.relatorios import gerar_pdf_prontuario
from admin_relatorios.models import Relatorio
from io import BytesIO
from django.core.files.base import ContentFile

# Importações necessárias para o mixin
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.urls import reverse
from django.db.models import Q
from django.utils import timezone
from admin_cadastros_assistenciais.models import CadastroProfissional
from admin_prescricoes.models import ParametrosPrescricao
from prontuarios.models import Prescricao
from django.utils.timezone import now
##################


def _pdf_bytes_validos(pdf_bytes):
    if not pdf_bytes:
        return False
    if not isinstance(pdf_bytes, (bytes, bytearray)):
        return False
    if not pdf_bytes.startswith(b'%PDF'):
        return False
    try:
        PdfReader(BytesIO(pdf_bytes))
        return True
    except Exception:
        return False


def salvar_pdf_prontuario(user, obj, assinar=False):
    perfil_usuario = Perfil.objects.get(user=user)
    certificado_field = perfil_usuario.certificado_digital
    contrasena = perfil_usuario.senha_certificado
    nome_modelo = obj.__class__.__name__.lower()
    posicao = 62
    certificado = None
    # leitura segura do certificado independentemente do storage
    if certificado_field and contrasena:
        with certificado_field.open('rb') as f:  # Parte nova para GCP.
            certificado = f.read()

    if nome_modelo == 'prescricao':
        adeps = Adep.objects.filter(
            fase_adep__in=['A', 'N'], prescricao=obj, us_adep=user, assinar=False)
        if adeps.exists():
            nome_modelo = 'adep'

    buffer = gerar_pdf_prontuario(obj, user)
    pdf_base_bytes = buffer.getvalue()
    assinado = False

    # Tratamento de `atendimento` e `pessoa` conforme os atributos do modelo
    atendimento_id = None
    pessoa_id = None

    if hasattr(obj, 'atendimento_id'):
        atendimento_id = obj.atendimento_id if obj.atendimento_id else None
        if hasattr(obj, 'atendimento') and hasattr(obj.atendimento, 'pessoa_id'):
            pessoa_id = obj.atendimento.pessoa_id if obj.atendimento.pessoa_id else None

    # Processo de assinatura do PDF
    if assinar and certificado:
        try:
            datau, datas, assinado = assinar_pdf(
                contrasena,
                certificado,
                BytesIO(pdf_base_bytes),
                posicao
            )

            pdf_completo = BytesIO()
            pdf_completo.write(datau)
            if assinado:
                pdf_completo.write(datas)
            pdf_completo.seek(0)

            pdf_resultado_bytes = pdf_completo.read() if assinado else pdf_base_bytes
            if assinado and (
                not _pdf_bytes_validos(pdf_resultado_bytes)
                or b'/ByteRange' not in pdf_resultado_bytes
                or b'/Contents' not in pdf_resultado_bytes
            ):
                assinado = False
                pdf_resultado_bytes = pdf_base_bytes

            if assinado and not verificar_assinatura_pdf(
                pdf_resultado_bytes,
                certificado,
                contrasena,
            ):
                assinado = False
                pdf_resultado_bytes = pdf_base_bytes

            nome_arquivo = f'{nome_modelo}_{"dig" if assinado else "imp"}_{obj.id}.pdf'
            content_type = ContentType.objects.get_for_model(obj)

            Relatorio.objects.filter(
                content_type=content_type,
                object_id=obj.id,
                tipo=nome_modelo,
                status='A',
            ).update(status='I')

            relatorio = Relatorio(content_type=content_type, object_id=obj.id,
                                  tipo=nome_modelo, atendimento_id=atendimento_id, pessoa_id=pessoa_id)
            # Salvar o PDF assinado no Relatório
            relatorio.relatorio.save(nome_arquivo, ContentFile(pdf_resultado_bytes))
            return assinado
        except Exception as e:
            assinado = False

    # Caso o PDF não seja assinado
    if not assinado:
        nome_arquivo = f'{nome_modelo}_imp_{obj.id}.pdf'
        content_type = ContentType.objects.get_for_model(obj)

        Relatorio.objects.filter(
            content_type=content_type,
            object_id=obj.id,
            tipo=nome_modelo,
            status='A',
        ).update(status='I')

        relatorio = Relatorio(content_type=content_type,
                              object_id=obj.id, tipo=nome_modelo, atendimento_id=atendimento_id, pessoa_id=pessoa_id)
        # Salvar o PDF gerado sem assinatura
        relatorio.relatorio.save(nome_arquivo, ContentFile(pdf_base_bytes))
        return False


def buscar_diagnosticos(request, atendimento_id):
    estabelecimento_id = request.session.get("estabelecimento_id")
    diagnosticos = Diagnostico.objects.filter(
        atendimento_id=atendimento_id,
        estabelecimento_id=estabelecimento_id,
        status='A'
    ).prefetch_related('diagnostico')

    diagnostico_texto = []
    for diagnostico in diagnosticos:
        for cid in diagnostico.diagnostico.all():
            diagnostico_texto.append(str(cid))

    return JsonResponse({'diagnosticos': diagnostico_texto})
