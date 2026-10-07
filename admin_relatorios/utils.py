from admin_cadastros_assistenciais.models import CadastroProfissional
from reportlab.lib.pagesizes import A4
from django.conf import settings
from django.urls import reverse
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import models
from django.db import connection
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.core.exceptions import ValidationError
from datetime import datetime
from django import template
import re
from django import forms
from django.contrib.auth.models import Group
from django.db.models import Q
from admin_cadastros.models import Estabelecimento
from django.contrib.admin import SimpleListFilter
from admin_cadastros_assistenciais.models import CadastroProfissional
from admin_evolucoes.models import ParametrosEvolucao
from admin_adep.models import ParametrosAdep
from admin_prescricoes.models import ParametrosPrescricao
from admin_sae.models import ParametrosSAE
from admin_perdas_ganhos.models import ParametrosPerdasGanhos
from admin_plano_cuidados.models import ParametrosPlanoCuidados
from admin_sinais_vitais.models import ParametrosSinaisVitais
from django.forms import PasswordInput
from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken
import logging
from django.http import HttpResponse
import datetime
from io import BytesIO
from cryptography.hazmat import backends
from cryptography import x509
import os
import re
import hashlib
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from asn1crypto import cms, core
from endesive.pdf import cms as endesive_cms
from endesive import pdf
from PyPDF2 import PdfReader

from django.contrib.contenttypes.fields import ContentType
from admin_relatorios.models import Relatorio
from django.core.files.base import ContentFile


# metodo para assinatura digital por certificado do tipo e-cpf

def _validar_certificado_para_assinatura(cert):
    if cert is None:
        raise ValueError('Certificado digital ausente para assinatura.')

    now = datetime.datetime.utcnow()
    if cert.not_valid_before > now or cert.not_valid_after < now:
        raise ValueError('Certificado digital fora da validade atual.')

    if not cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME):
        raise ValueError('Certificado digital sem nome do assinante.')

    subject_country_values = cert.subject.get_attributes_for_oid(x509.NameOID.COUNTRY_NAME)
    issuer_country_values = cert.issuer.get_attributes_for_oid(x509.NameOID.COUNTRY_NAME)
    subject_org_values = cert.subject.get_attributes_for_oid(x509.NameOID.ORGANIZATION_NAME)
    issuer_org_values = cert.issuer.get_attributes_for_oid(x509.NameOID.ORGANIZATION_NAME)
    subject_ou_values = cert.subject.get_attributes_for_oid(x509.NameOID.ORGANIZATIONAL_UNIT_NAME)
    issuer_ou_values = cert.issuer.get_attributes_for_oid(x509.NameOID.ORGANIZATIONAL_UNIT_NAME)

    has_brazilian_identity = bool(
        subject_country_values or issuer_country_values or
        subject_org_values or issuer_org_values or
        subject_ou_values or issuer_ou_values
    )

    if not has_brazilian_identity:
        raise ValueError('Certificado digital sem dados de identificação do titular ou emissor.')

    if subject_country_values or issuer_country_values:
        values = [v.value.upper() for v in (subject_country_values or []) + (issuer_country_values or [])]
        if values and not all(v in {'BR', 'BRA', 'BRASIL'} for v in values):
            raise ValueError('Certificado digital não é emitido no Brasil ou não é um certificado válido para assinatura ICP-Brasil.')

    return True


def _extrair_cpf_certificado(cert):
    if cert is None:
        return None

    cpf_oid = x509.ObjectIdentifier('2.16.76.1.3.1')
    serial_number_oid = x509.NameOID.SERIAL_NUMBER

    def _normalizar_cpf(valor):
        if not valor:
            return None
        digitos = ''.join(filter(str.isdigit, str(valor)))
        if len(digitos) < 11:
            return None
        digitos = digitos[-11:]
        return f'{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}'

    try:
        for attr in cert.subject.get_attributes_for_oid(cpf_oid):
            cpf = _normalizar_cpf(attr.value)
            if cpf:
                return cpf
    except Exception:
        pass

    try:
        for attr in cert.subject.get_attributes_for_oid(serial_number_oid):
            valor = str(attr.value)
            if 'CPF' in valor.upper():
                cpf = _normalizar_cpf(valor)
                if cpf:
                    return cpf
    except Exception:
        pass

    return None


def obter_dados_assinatura_certificado(contasena, certificado):
    if not certificado:
        return None

    try:
        senha = contasena.encode('ascii') if contasena else None
        p12 = pkcs12.load_key_and_certificates(
            certificado,
            senha,
            default_backend(),
        )
        cert = p12[1]
        if cert is None:
            return None

        _validar_certificado_para_assinatura(cert)

        subject = cert.subject
        nome_assinante = subject.get_attributes_for_oid(
            x509.NameOID.COMMON_NAME)[0].value

        organization = ''
        if subject.get_attributes_for_oid(x509.NameOID.ORGANIZATION_NAME):
            organization = subject.get_attributes_for_oid(x509.NameOID.ORGANIZATION_NAME)[0].value

        email = None
        for ext in cert.extensions:
            if isinstance(ext.value, x509.SubjectAlternativeName):
                email_values = ext.value.get_values_for_type(x509.RFC822Name)
                if email_values:
                    email = email_values[0]
                    break

        cpf_assinante = _extrair_cpf_certificado(cert)
        data_assinatura = datetime.datetime.now().strftime('%d/%m/%Y às %H:%M:%S h')
        emissor = cert.issuer.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value if cert.issuer.get_attributes_for_oid(x509.NameOID.COMMON_NAME) else 'Autoridade Certificadora'
        nome_cpf = nome_assinante if not cpf_assinante else f'{nome_assinante} - CPF: {cpf_assinante}'
        texto_assinatura = (
            f"{nome_cpf}\n"
            f"Assinado de forma digital por {nome_cpf}\n"
            f"Data: {data_assinatura}"
        )

        return {
            'nome_assinante': nome_assinante,
            'cpf_assinante': cpf_assinante,
            'organizacao': organization,
            'email': email,
            'serial_number': str(cert.serial_number),
            'emissor': emissor,
            'data_validade_inicio': cert.not_valid_before.strftime('%d/%m/%Y'),
            'data_validade_fim': cert.not_valid_after.strftime('%d/%m/%Y'),
            'texto_assinatura': texto_assinatura,
        }
    except Exception:
        return None


def _extrair_conteudo_cms_do_pdf(pdf_bytes):
    if not pdf_bytes:
        return None

    matches = re.findall(rb'/Contents\s*<\s*([0-9A-Fa-f]+)\s*>', pdf_bytes)
    if not matches:
        return None

    hex_data = matches[-1]
    try:
        return bytes.fromhex(hex_data.decode('ascii'))
    except ValueError:
        return None


def _extrair_byte_range_do_pdf(pdf_bytes):
    if not pdf_bytes:
        return None

    match = re.search(rb'/ByteRange\s*\[\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*\]', pdf_bytes)
    if not match:
        return None

    return tuple(int(valor) for valor in match.groups())


def _pdf_tem_assinatura_embutida(pdf_bytes):
    if not pdf_bytes:
        return False

    if not isinstance(pdf_bytes, (bytes, bytearray)):
        return False

    bytes_pdf = bytes(pdf_bytes)
    if b'/ByteRange' not in bytes_pdf or b'/Contents' not in bytes_pdf or b'Signature1' not in bytes_pdf:
        return False

    cms_bytes = _extrair_conteudo_cms_do_pdf(bytes_pdf)
    if not cms_bytes:
        return False

    try:
        parsed = cms.ContentInfo.load(cms_bytes)
        signed = parsed['content']
        if not signed or 'signer_infos' not in signed or not signed['signer_infos']:
            return False
        if 'certificates' not in signed or not signed['certificates']:
            return False
        return True
    except Exception:
        return False


def verificar_assinatura_pdf(pdf_bytes, certificado, contasena=None):
    if not pdf_bytes or not certificado:
        return False

    try:
        senha = contasena.encode('ascii') if contasena else None
        p12 = pkcs12.load_key_and_certificates(certificado, senha, default_backend())
        cert = p12[1]
        if cert is None:
            return False

        _validar_certificado_para_assinatura(cert)
        cms_bytes = _extrair_conteudo_cms_do_pdf(pdf_bytes)
        if not cms_bytes:
            return False

        byte_range = _extrair_byte_range_do_pdf(pdf_bytes)
        if not byte_range:
            return False

        signed_data = cms.ContentInfo.load(cms_bytes)['content']
        signature = signed_data['signer_infos'][0]['signature'].native
        algorithm_name = signed_data['digest_algorithms'][0]['algorithm'].native
        attrs = signed_data['signer_infos'][0]['signed_attrs']

        inicio_1, tamanho_1, inicio_2, tamanho_2 = byte_range
        pdf_assinado_bytes = bytes(pdf_bytes)
        conteudo_assinado = (
            pdf_assinado_bytes[inicio_1:inicio_1 + tamanho_1] +
            pdf_assinado_bytes[inicio_2:inicio_2 + tamanho_2]
        )

        message_digest_attr = None
        for attr in attrs:
            if attr['type'].native == 'message_digest':
                message_digest_attr = attr['values'][0].native
                break

        if not message_digest_attr:
            return False

        digestor = getattr(hashlib, algorithm_name)()
        digestor.update(conteudo_assinado)
        if digestor.digest() != message_digest_attr:
            return False

        if attrs is not None and not isinstance(attrs, core.Void):
            signed_data_bytes = attrs.dump()
            signed_data_bytes = b"\x31" + signed_data_bytes[1:]
        else:
            signed_data_bytes = pdf_bytes

        serial = signed_data['signer_infos'][0]['sid'].native['serial_number']
        certificate_der = None
        for cert_info in signed_data['certificates']:
            cert_obj = cert_info.chosen
            if serial == cert_obj.native['tbs_certificate']['serial_number']:
                certificate_der = cert_obj.dump()
                break

        if certificate_der is None:
            return False

        signer_public_key = x509.load_der_x509_certificate(certificate_der).public_key()
        sigalgo = signed_data['signer_infos'][0]['signature_algorithm']
        sigalgoname = sigalgo.signature_algo

        if sigalgoname == 'rsassa_pss':
            parameters = sigalgo['parameters']
            salgo = parameters['hash_algorithm'].native['algorithm'].upper()
            mgf = getattr(padding, parameters['mask_gen_algorithm'].native['algorithm'].upper())(
                getattr(hashes, salgo)()
            )
            salt_length = parameters['salt_length'].native
            signer_public_key.verify(
                signature,
                signed_data_bytes,
                padding.PSS(mgf, salt_length),
                getattr(hashes, salgo)(),
            )
        elif sigalgoname == 'rsassa_pkcs1v15':
            signer_public_key.verify(
                signature,
                signed_data_bytes,
                padding.PKCS1v15(),
                getattr(hashes, algorithm_name.upper())(),
            )
        else:
            return False

        return True
    except Exception:
        return False


def assinar_pdf(contasena, certificado, pdf_buffer, posicao):
    try:
        pdf_buffer.seek(0)
        datau = pdf_buffer.read()

        if not datau:
            raise ValueError('PDF vazio para assinatura.')

        page_width, page_height = A4
        pdf_reader = PdfReader(BytesIO(datau))
        total_paginas = len(pdf_reader.pages)
        sigpage = max(0, total_paginas - 1)

        largura_assinatura = 330
        altura_assinatura = 50
        x_centro = ((page_width - largura_assinatura) / 2) + 10
        y_inferior = posicao

        date = datetime.datetime.utcnow() - datetime.timedelta(hours=0)
        date = date.strftime("D:%Y%m%d%H%M%S+00'00'")

        certificado_data = certificado
        p12 = pkcs12.load_key_and_certificates(
            certificado_data, contasena.encode("ascii"), default_backend()
        )

        cert = p12[1]
        _validar_certificado_para_assinatura(cert)

        subject = cert.subject
        nome_assinante = subject.get_attributes_for_oid(
            x509.NameOID.COMMON_NAME)[0].value

        email = None
        for ext in cert.extensions:
            if isinstance(ext.value, x509.SubjectAlternativeName):
                email_values = ext.value.get_values_for_type(x509.RFC822Name)
                if email_values:
                    email = email_values[0]
                    break

        contact = email if email else "contato@managerontecsolutions.com.br"
        data_assinatura = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M:%S h")
        texto_assinatura = f"{nome_assinante} em {data_assinatura} Assinatura Digital - ICP-Brasil\n"

        dct = {
            # O endesive calcula o tamanho exato do CMS quando aligned=0.
            # Reservar um bloco grande demais deixa padding extra no /Contents,
            # e validadores externos podem rejeitar a assinatura como
            # "SigDict /Contents illegal data".
            "aligned": 0,
            "sigflags": 3,
            "sigflagsft": 132,
            "sigpage": sigpage,
            "sigbutton": True,
            "sigfield": "Signature1",
            "auto_sigfield": True,
            "signaturebox": (x_centro, y_inferior, x_centro + largura_assinatura, y_inferior + altura_assinatura),
            "signature": texto_assinatura,
            "contact": contact,
            "location": "Brazil",
            "signingdate": date,
            "reason": "Assinado Digitalmente",
            "password": contasena,
        }

        datas = pdf.cms.sign(datau, dct, p12[0], p12[1], p12[2], "sha256")

        return datau, datas, True
    except Exception as e:
        print("Erro ao assinar o PDF:", e)
        try:
            pdf_buffer.seek(0)
            return pdf_buffer.read(), b'', False
        except Exception:
            return b'', b'', False


class RelatorioMixin:
    """
    Mixin para adicionar a funcionalidade de obter relatórios associados a qualquer modelo.
    """

    def get_relatorios(self):
        content_type = ContentType.objects.get_for_model(self)
        print(f"******************CONTENT{content_type}")
        rel = Relatorio.objects.filter(
            content_type=content_type, object_id=self.id)
        print(f"**************REL{rel}")
        return Relatorio.objects.filter(content_type=content_type, object_id=self.id)
