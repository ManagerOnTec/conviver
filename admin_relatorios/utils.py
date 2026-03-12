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
from cryptography.hazmat import backends
from cryptography import x509
import os
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import pkcs12
from endesive.pdf import cms
from endesive import pdf

from django.contrib.contenttypes.fields import ContentType
from admin_relatorios.models import Relatorio
from django.core.files.base import ContentFile


# metodo para assinatura digital por certificado do tipo e-cpf


def assinar_pdf(contasena, certificado, pdf_buffer, posicao):
    try:
        page_width, page_height = A4
        # coordenadas da assinatura visual no PDF
        largura_assinatura = 330
        altura_assinatura = 50
        x_centro = ((page_width - largura_assinatura) / 2) + 10
        # Posição y do fundo da página
        y_inferior = posicao

        # data para certificado
        date = datetime.datetime.utcnow() - datetime.timedelta(hours=0)
        date = date.strftime("D:%Y%m%d%H%M%S+00'00'")

        # Ler o certificado e extrair informações
        certificado_data = certificado
        p12 = pkcs12.load_key_and_certificates(
            certificado_data, contasena.encode(
                "ascii"), default_backend()
        )

        # Extrair informações do certificado
        cert = p12[1]
        subject = cert.subject

        # Extrair nome do assinante do certificado
        nome_assinante = subject.get_attributes_for_oid(
            x509.NameOID.COMMON_NAME)[0].value

        # Tentar extrair e-mail do assinante do certificado
        email = None
        for ext in cert.extensions:
            if isinstance(ext.value, x509.SubjectAlternativeName):
                email_values = ext.value.get_values_for_type(x509.RFC822Name)
                if email_values:
                    email = email_values[0]
                    break

        # Definir um valor padrão para 'contact' se o e-mail não for encontrado
        contact = email if email else "contato@managerontecsolutions.com.br"

        # Formatar o texto da assinatura
        data_assinatura = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M:%S h")
        texto_assinatura = f"{nome_assinante} em {data_assinatura} Assinatura Digital - ICP-Brasil\n"

        # Configurações da assinatura
        dct = {
            "aligned": 0,
            "sigflags": 3,
            "sigflagsft": 132,
            "sigpage": 0,
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

        # Assinar o PDF
        datau = pdf_buffer.read()
        datas = pdf.cms.sign(datau, dct, p12[0], p12[1], p12[2], "sha256")

        return datau, datas, True
    except Exception as e:
        print("Erro ao assinar o PDF:", e)
        return pdf_buffer.read(), b'', False


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
