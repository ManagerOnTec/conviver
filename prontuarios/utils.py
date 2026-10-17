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


def _salvar_relatorios_pdf(nome_modelo, obj, adeps_do_lote, atendimento_id,
                           pessoa_id, pdf_bytes, assinado,
                           us_registro=None, dt_registro=None):
    """Grava o PDF gerado/assinado no(s) relatório(s) correspondente(s).

    - Para o fluxo normal, grava um relatório apontando para o próprio objeto
      (ex.: ``tipo='prescricao'`` na prescrição).
    - Para o fluxo de ADEP, o PDF é um lote combinado de administrações; ele é
      gravado em cada Adep do lote (``tipo='adep'``), de modo que a prescrição
      mantém o seu PDF próprio e cada ADEP passa a ter o seu relatório assinado
      (um mesmo arquivo é referenciado por todos os ADEPs do lote, sem
      duplicar o conteúdo em disco).

    ``us_registro`` e ``dt_registro`` registram no modelo de auditoria o usuário
    logado e o momento em que o PDF foi gerado.
    """
    sufixo = 'dig' if assinado else 'imp'
    dt_registro = dt_registro or timezone.now()

    if nome_modelo == 'adep' and adeps_do_lote is not None:
        adeps = list(adeps_do_lote)
        if not adeps:
            return

        content_type = ContentType.objects.get_for_model(Adep)

        ## Desativação de relatórios anteriores dos mesmos Adeps (comentado).
        # adep_ids = [adep.id for adep in adeps]
        # Inativa relatórios de ADEP anteriores dos mesmos Adeps.
        # Relatorio.objects.filter(
        #     content_type=content_type,
        #     object_id__in=adep_ids,
        #     tipo='adep',
        #     status='A',
        # ).update(status='I')

        # Salva o arquivo uma única vez no primeiro Adep e reaproveita o mesmo
        # caminho nos demais, evitando cópias idênticas em disco.
        primeiro = adeps[0]
        nome_arquivo = f'adep_{sufixo}_{primeiro.id}.pdf'
        relatorio = Relatorio(
            content_type=content_type,
            object_id=primeiro.id,
            tipo='adep',
            atendimento_id=atendimento_id,
            pessoa_id=pessoa_id,
            us_registro=us_registro,
            dt_registro=dt_registro,
        )
        relatorio.relatorio.save(nome_arquivo, ContentFile(pdf_bytes))
        caminho = relatorio.relatorio.name

        for adep in adeps[1:]:
            irmao = Relatorio(
                content_type=content_type,
                object_id=adep.id,
                tipo='adep',
                atendimento_id=atendimento_id,
                pessoa_id=pessoa_id,
                us_registro=us_registro,
                dt_registro=dt_registro,
            )
            irmao.relatorio.name = caminho
            irmao.save()
        return

    # Fluxo normal (prescricao, evolucao, etc.).
    nome_arquivo = f'{nome_modelo}_{sufixo}_{obj.id}.pdf'
    content_type = ContentType.objects.get_for_model(obj)

    ## Desativação de relatórios anteriores do mesmo tipo para o objeto atual (comentado).
    # Relatorio.objects.filter(
    #     content_type=content_type,
    #     object_id=obj.id,
    #     tipo=nome_modelo,
    #     status='A',
    # ).update(status='I')

    relatorio = Relatorio(
        content_type=content_type,
        object_id=obj.id,
        tipo=nome_modelo,
        atendimento_id=atendimento_id,
        pessoa_id=pessoa_id,
        us_registro=us_registro,
        dt_registro=dt_registro,
    )
    relatorio.relatorio.save(nome_arquivo, ContentFile(pdf_bytes))


def salvar_pdf_prontuario(user, obj, assinar=False, adeps=None):
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

    # Adeps do lote que será impresso junto da prescrição. Quando existem, o
    # PDF do lote de ADEPs é gravado em cada Adep (tipo='adep'), mas o PDF
    # próprio da prescrição (tipo='prescricao') continua sendo gravado. Antes
    # o nome_modelo era trocado para 'adep', o que fazia o PDF da prescrição
    # nunca ser salvo e a tela de prescrição exibir o relatório de ADEP.
    adeps_do_lote = Adep.objects.none()
    if nome_modelo == 'prescricao':
        if adeps is not None:
            # Lote informado explicitamente (ex.: seleção na tela de assinatura
            # de ADEP), independentemente do estado do campo ``assinar``.
            adeps_do_lote = adeps
        else:
            adeps_do_lote = Adep.objects.filter(
                fase_adep__in=['A', 'N'], prescricao=obj, us_adep=user,
                assinar=False)
        if not adeps_do_lote.exists():
            adeps_do_lote = Adep.objects.none()

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

            _salvar_relatorios_pdf(
                nome_modelo,
                obj,
                adeps_do_lote,
                atendimento_id,
                pessoa_id,
                pdf_resultado_bytes,
                assinado,
                us_registro=user,
                dt_registro=timezone.now(),
            )
            return assinado
        except Exception as e:
            assinado = False

    # Caso o PDF não seja assinado
    if not assinado:
        _salvar_relatorios_pdf(
            nome_modelo,
            obj,
            adeps_do_lote,
            atendimento_id,
            pessoa_id,
            pdf_base_bytes,
            False,
            us_registro=user,
            dt_registro=timezone.now(),
        )
        return False
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
