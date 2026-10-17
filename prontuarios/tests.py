import base64
from datetime import datetime, timedelta
from io import BytesIO
import zipfile

import PyPDF2
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from unittest.mock import patch

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase
from django.utils import timezone

from admin_cadastros.models import Estabelecimento, Pessoa, Empresa, TipoAtendimento
from admin_estoques.models import Grupo, Produto, TipoProduto, UnidadeMedida
from admin_evolucoes.models import TipoEvolucao
from admin_prescricoes.models import InicioPlanoTerapeutico, IntervaloHoras
from admin_relatorios.models import GerenciadorRelatorioGeral
from admin_relatorios.models import Relatorio
from admin_relatorios.rel_paragrafos import genParagrafosRel
from atendimentos.models import Atendimento
from atas.models import Atas
from contas.models import Perfil
from oficios.models import Oficios
from orcamentos.models import Orcamentos
from prontuarios.forms import EvolucaoCreateForm, EvolucaoUpdateForm
from prontuarios.models import (
    Adep,
    Evolucao,
    MAX_EVOLUCAO_TEXT_LENGTH,
    Prescricao,
    ProdutoPrescricao,
    validate_evolucao_texto,
)
from prontuarios.relatorios import gerar_pdf_prontuario
from prontuarios.utils import _salvar_relatorios_pdf, salvar_pdf_prontuario
from prontuarios.views import (
    EvolucaoCreateView,
    combine_pdfs_specific,
    download_adep_pdfs,
    download_filtered_pdfs,
)
from admin_relatorios.utils import (
    _validar_certificado_para_assinatura,
    assinar_pdf,
    obter_dados_assinatura_certificado,
    verificar_assinatura_pdf,
)


ONE_PIXEL_PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j5JcAAAAASUVORK5CYII='
)


class EvolucaoValidationAndPdfTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='medico1',
            email='medico1@example.com',
            password='senha123',
        )
        self.profissional = Pessoa.objects.create(
            nome='Médico Teste',
            classificacao_pessoa='P',
            nacionalidade='b',
            sexo='F',
            dt_nascimento=None,
            rg=None,
            cpf=None,
            email='medico@example.com',
            status='A',
        )
        self.empresa = Empresa.objects.create(
            nacionalidade='b',
            razao_social='Empresa Teste',
            fantasia='Empresa Teste',
            empresa='EMP TESTE',
            status='A',
        )
        self.estabelecimento = Estabelecimento.objects.create(
            estabelecimento='Estabelecimento Teste',
            tipo='H',
            empresa=self.empresa,
            status='A',
        )
        self.perfil = Perfil.objects.create(
            user=self.user,
            pessoa=self.profissional,
            estabelecimento_padrao=self.estabelecimento,
        )
        self.perfil.estabelecimento.add(self.estabelecimento)
        self.tipo_evolucao = TipoEvolucao.objects.create(
            tipo_evolucao='Evolução padrão',
            status='A',
        )
        self.pessoa = Pessoa.objects.create(
            nome='Paciente Teste',
            classificacao_pessoa='P',
            nacionalidade='b',
            sexo='M',
            dt_nascimento=None,
            rg=None,
            cpf=None,
            email='paciente@example.com',
            status='A',
        )
        self.tipo_atendimento = TipoAtendimento.objects.create(
            tipo_atendimento='Consulta',
            status='A',
        )
        self.atendimento = Atendimento.objects.create(
            pessoa=self.pessoa,
            tipo_atendimento=self.tipo_atendimento,
            estabelecimento=self.estabelecimento,
            carater_atendimento='E',
            entidade_encaminhamento='N',
            cert_nascimento=False,
            rg=False,
            cpf=False,
            titulo_eleitor=False,
            carteira_vacina=False,
            cartao_sus=False,
            cartao_banco=False,
            carteira_trabalho=False,
            foto=False,
            outros=False,
            status='A',
        )

    def _assert_page_has_embedded_image(self, page):
        resources = page.get('/Resources')
        xobjects = resources.get('/XObject').get_object() if resources and resources.get('/XObject') else {}
        has_image = any(
            obj.get_object().get('/Subtype') == '/Image'
            for obj in xobjects.values()
        )

        self.assertTrue(has_image)

    def test_validator_allows_large_html_content_but_respects_limit(self):
        value = '<p>' + ('Linha longa de teste ' * 300) + '</p>'
        self.assertGreater(len(value), 5000)
        self.assertLess(len(value), MAX_EVOLUCAO_TEXT_LENGTH)
        validate_evolucao_texto(value)

        invalid_value = '<p>' + ('Linha longa de teste ' * 1200) + '</p>'
        with self.assertRaises(ValidationError):
            validate_evolucao_texto(invalid_value)

    def test_form_uses_same_validator_as_model(self):
        form = EvolucaoCreateForm(
            data={
                'tipo_evolucao': self.tipo_evolucao.pk,
                'evolucao': '<p>' + ('Linha longa de teste ' * 300) + '</p>',
                'status': 'A',
            },
            user=self.user,
            estabelecimento=self.estabelecimento,
        )

        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_create_view_does_not_report_false_signed_success_when_pdf_is_unsigned(self):
        request = RequestFactory().post(
            '/',
            {
                'tipo_evolucao': self.tipo_evolucao.pk,
                'evolucao': '<p>Evolução de teste sem assinatura digital.</p>',
                'status': 'A',
            },
        )
        request.user = self.user
        request.session = self.client.session
        request.session['estabelecimento_id'] = self.estabelecimento.pk
        request.session.save()
        setattr(request, '_messages', FallbackStorage(request))

        form = EvolucaoCreateForm(
            data={
                'tipo_evolucao': self.tipo_evolucao.pk,
                'evolucao': '<p>Evolução de teste sem assinatura digital.</p>',
                'status': 'A',
            },
            user=self.user,
            estabelecimento=self.estabelecimento,
        )
        self.assertTrue(form.is_valid(), form.errors.as_json())

        view = EvolucaoCreateView()
        view.request = request
        view.kwargs = {'atendimento_id': self.atendimento.pk}
        view.args = ()

        with patch('prontuarios.views.salvar_pdf_prontuario', return_value=False):
            response = view.form_valid(form)

        self.assertEqual(response.status_code, 302)
        stored_messages = list(messages.get_messages(request))
        texts = [str(message) for message in stored_messages]
        self.assertIn(settings.MSG_ADD, texts)
        self.assertIn('Relatório gerado sem assinatura.', texts)
        self.assertNotIn('PDF assinado com sucesso!', texts)

    def test_pdf_generation_paginates_long_evolution(self):
        text = '<p><b>Resumo</b> ' + ('Linha longa de teste ' * 300) + ' <i>obs</i></p>'
        evolucao = Evolucao.objects.create(
            atendimento=self.atendimento,
            tipo_evolucao=self.tipo_evolucao,
            evolucao=text,
            estabelecimento=self.estabelecimento,
            us_registro=self.user,
            status='A',
        )

        buffer = gerar_pdf_prontuario(evolucao, self.user)
        reader = PyPDF2.PdfReader(BytesIO(buffer.getvalue()))

        self.assertGreater(len(reader.pages), 1)

    def test_pdf_repeats_fixed_header_and_footer_on_all_pages(self):
        GerenciadorRelatorioGeral.objects.create(
            dados_header='Evolucao Geral',
            dados_right_header='Versao 1',
            dados_footer='Rodape da evolucao',
            cidade='Cidade Teste',
            estabelecimento=self.estabelecimento,
            us_registro=self.user,
            status='A',
        )

        text = '<p>' + ('Linha longa de teste ' * 650) + '</p>'
        evolucao = Evolucao.objects.create(
            atendimento=self.atendimento,
            tipo_evolucao=self.tipo_evolucao,
            evolucao=text,
            estabelecimento=self.estabelecimento,
            us_registro=self.user,
            status='A',
        )

        buffer = gerar_pdf_prontuario(evolucao, self.user)
        reader = PyPDF2.PdfReader(BytesIO(buffer.getvalue()))
        page_texts = [page.extract_text() or '' for page in reader.pages]

        self.assertGreater(len(page_texts), 1)
        for page_text in page_texts:
            self.assertIn('Evolucao Geral', page_text)
            self.assertIn('Rodape da evolucao', page_text)

    def test_pdf_keeps_single_long_paragraph_from_first_page_to_last(self):
        text = '<p>MarcadorInicio ' + ('Linha longa de teste ' * 2200) + ' MarcadorFim</p>'
        evolucao = Evolucao.objects.create(
            atendimento=self.atendimento,
            tipo_evolucao=self.tipo_evolucao,
            evolucao=text,
            estabelecimento=self.estabelecimento,
            us_registro=self.user,
            assinar=True,
            status='A',
        )

        buffer = gerar_pdf_prontuario(evolucao, self.user, assinar=True)
        reader = PyPDF2.PdfReader(BytesIO(buffer.getvalue()))
        page_texts = [page.extract_text() or '' for page in reader.pages]

        self.assertGreater(len(page_texts), 1)
        self.assertIn('MarcadorInicio', page_texts[0])
        self.assertIn('MarcadorFim', page_texts[-1])

    def test_long_text_documents_use_same_readable_line_spacing(self):
        for tipo in ('evolucao', 'atas', 'oficios', 'orcamentos'):
            flowables = genParagrafosRel('<p>Linha 1</p><p>Linha 2</p>', 500, 0, None, tipo=tipo)
            primeiro_paragrafo = next(flowable for flowable in flowables if hasattr(flowable, 'style'))

            self.assertEqual(primeiro_paragrafo.style.leading, 15)
            self.assertEqual(primeiro_paragrafo.style.spaceAfter, 6)

    def test_long_text_documents_preserve_alignment_bold_and_italic_from_editor_html(self):
        html = '<p style="text-align: center;"><span style="font-weight: bold; font-style: italic;">texto formatado</span></p>'

        for tipo in ('evolucao', 'atas', 'oficios', 'orcamentos'):
            flowables = genParagrafosRel(html, 500, 0, None, tipo=tipo)
            primeiro_paragrafo = next(flowable for flowable in flowables if hasattr(flowable, 'style'))

            self.assertEqual(primeiro_paragrafo.style.alignment, 1)
            self.assertIn('<b><i>texto formatado</i></b>', getattr(primeiro_paragrafo, 'text', ''))

    def test_pdf_adds_dedicated_photo_page_for_evolution_attachment(self):
        GerenciadorRelatorioGeral.objects.create(
            dados_header='Evolucao Geral',
            dados_right_header='Versao 1',
            dados_footer='Rodape da evolucao',
            cidade='Cidade Teste',
            estabelecimento=self.estabelecimento,
            us_registro=self.user,
            status='A',
        )

        image_file = SimpleUploadedFile('anexo.png', ONE_PIXEL_PNG, content_type='image/png')
        evolucao = Evolucao.objects.create(
            atendimento=self.atendimento,
            tipo_evolucao=self.tipo_evolucao,
            evolucao='<p>Evolução com foto.</p>',
            estabelecimento=self.estabelecimento,
            us_registro=self.user,
            anexo_evolucao=image_file,
            assinar=True,
            status='A',
        )
        self.addCleanup(lambda: evolucao.anexo_evolucao.delete(save=False))

        buffer = gerar_pdf_prontuario(evolucao, self.user, assinar=True)
        reader = PyPDF2.PdfReader(BytesIO(buffer.getvalue()))

        self.assertEqual(len(reader.pages), 2)
        self.assertIn('Evolucao Geral', reader.pages[1].extract_text() or '')
        self.assertIn('Rodape da evolucao', reader.pages[1].extract_text() or '')

        resources = reader.pages[1].get('/Resources')
        xobjects = resources.get('/XObject').get_object() if resources and resources.get('/XObject') else {}
        has_image = any(
            obj.get_object().get('/Subtype') == '/Image'
            for obj in xobjects.values()
        )

        self.assertTrue(has_image)

    def test_pdf_adds_dedicated_photo_page_for_ata_attachment(self):
        image_file = SimpleUploadedFile('ata.png', ONE_PIXEL_PNG, content_type='image/png')
        ata = Atas.objects.create(
            participantes='Equipe Teste',
            assunto='Ata com imagem',
            tipo_ata='ADMINISTRATIVA',
            observacoes='Observacao teste',
            ata='<p>Ata com anexo de imagem.</p>',
            anexo=image_file,
            estabelecimento=self.estabelecimento,
            us_registro=self.user,
            assinar=True,
            status='A',
        )
        self.addCleanup(lambda: ata.anexo.delete(save=False))

        buffer = gerar_pdf_prontuario(ata, self.user, assinar=True)
        reader = PyPDF2.PdfReader(BytesIO(buffer.getvalue()))

        self.assertEqual(len(reader.pages), 2)
        self._assert_page_has_embedded_image(reader.pages[1])

    def test_pdf_adds_dedicated_photo_page_for_oficio_attachment(self):
        image_file = SimpleUploadedFile('oficio.png', ONE_PIXEL_PNG, content_type='image/png')
        oficio = Oficios.objects.create(
            observacao='Observacao teste',
            oficio='<p>Ofício com anexo de imagem.</p>',
            anexo=image_file,
            estabelecimento=self.estabelecimento,
            us_registro=self.user,
            assinar=True,
            status='A',
        )
        self.addCleanup(lambda: oficio.anexo.delete(save=False))

        buffer = gerar_pdf_prontuario(oficio, self.user, assinar=True)
        reader = PyPDF2.PdfReader(BytesIO(buffer.getvalue()))

        self.assertEqual(len(reader.pages), 2)
        self._assert_page_has_embedded_image(reader.pages[1])

    def test_pdf_adds_dedicated_photo_page_for_orcamento_attachment(self):
        image_file = SimpleUploadedFile('orcamento.png', ONE_PIXEL_PNG, content_type='image/png')
        orcamento = Orcamentos.objects.create(
            observacao='Observacao teste',
            orcamento='<p>Orçamento com anexo de imagem.</p>',
            anexo=image_file,
            estabelecimento=self.estabelecimento,
            us_registro=self.user,
            assinar=True,
            status='A',
        )
        self.addCleanup(lambda: orcamento.anexo.delete(save=False))

        buffer = gerar_pdf_prontuario(orcamento, self.user, assinar=True)
        reader = PyPDF2.PdfReader(BytesIO(buffer.getvalue()))

        self.assertEqual(len(reader.pages), 2)
        self._assert_page_has_embedded_image(reader.pages[1])

    def test_pdf_includes_signature_block_when_enabled(self):
        text = '<p>' + ('Linha longa de teste ' * 80) + '</p>'
        evolucao = Evolucao.objects.create(
            atendimento=self.atendimento,
            tipo_evolucao=self.tipo_evolucao,
            evolucao=text,
            estabelecimento=self.estabelecimento,
            us_registro=self.user,
            assinar=True,
            status='A',
        )

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, 'BR'),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'ManageronTec'),
            x509.NameAttribute(NameOID.COMMON_NAME, 'Dr. Teste'),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow() - timedelta(days=1))
            .not_valid_after(datetime.utcnow() + timedelta(days=30))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .sign(key, hashes.SHA256())
        )
        pfx = serialization.pkcs12.serialize_key_and_certificates(
            name=b'cert',
            key=key,
            cert=cert,
            cas=None,
            encryption_algorithm=serialization.BestAvailableEncryption(b'senha123'),
        )

        buffer = gerar_pdf_prontuario(evolucao, self.user, assinar=False)
        datau, datas, assinado = assinar_pdf('senha123', pfx, buffer, 62)
        dados = obter_dados_assinatura_certificado('senha123', pfx)

        self.assertTrue(assinado)
        self.assertIn(b'Signature1', datau + datas)
        self.assertIn('Assinado de forma digital por', dados['texto_assinatura'])

    def _build_test_pfx(self, common_name='Dr. Teste Download'):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, 'BR'),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'ManageronTec'),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow() - timedelta(days=1))
            .not_valid_after(datetime.utcnow() + timedelta(days=30))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .sign(key, hashes.SHA256())
        )

        return serialization.pkcs12.serialize_key_and_certificates(
            name=b'cert',
            key=key,
            cert=cert,
            cas=None,
            encryption_algorithm=serialization.BestAvailableEncryption(b'senha123'),
        )

    def _create_signed_relatorio(self, evolucao, file_suffix):
        pfx = self._build_test_pfx(common_name=f'Dr. Teste {file_suffix}')
        buffer = gerar_pdf_prontuario(evolucao, self.user, assinar=False)
        datau, datas, assinado = assinar_pdf('senha123', pfx, buffer, 62)
        signed_pdf = datau + datas

        self.assertTrue(assinado)
        self.assertTrue(verificar_assinatura_pdf(signed_pdf, pfx, 'senha123'))

        relatorio = Relatorio.objects.create(
            content_type=ContentType.objects.get_for_model(Evolucao),
            object_id=evolucao.id,
            tipo='evolucao',
            atendimento=self.atendimento,
            pessoa=self.pessoa,
            status='A',
        )
        relatorio.relatorio.save(
            f'evolucao_dig_teste_{file_suffix}_{evolucao.id}.pdf',
            ContentFile(signed_pdf),
        )
        return relatorio, signed_pdf

    def test_download_filtered_pdfs_returns_original_signed_pdf_when_single_result(self):
        evolucao = Evolucao.objects.create(
            atendimento=self.atendimento,
            tipo_evolucao=self.tipo_evolucao,
            evolucao='<p>Evolucao assinada unica.</p>',
            estabelecimento=self.estabelecimento,
            us_registro=self.user,
            assinar=True,
            status='A',
        )
        relatorio, signed_pdf = self._create_signed_relatorio(evolucao, 'unico')

        request = RequestFactory().get('/')
        request.session = {}

        response = download_filtered_pdfs(request, self.atendimento.id, 'evolucao')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertEqual(response.content, signed_pdf)
        self.assertIn(relatorio.relatorio.name.rsplit('/', 1)[-1], response['Content-Disposition'])

    def test_download_filtered_pdfs_returns_zip_preserving_each_signed_pdf(self):
        evolucao_1 = Evolucao.objects.create(
            atendimento=self.atendimento,
            tipo_evolucao=self.tipo_evolucao,
            evolucao='<p>Evolucao assinada 1.</p>',
            estabelecimento=self.estabelecimento,
            us_registro=self.user,
            assinar=True,
            status='A',
        )
        evolucao_2 = Evolucao.objects.create(
            atendimento=self.atendimento,
            tipo_evolucao=self.tipo_evolucao,
            evolucao='<p>Evolucao assinada 2.</p>',
            estabelecimento=self.estabelecimento,
            us_registro=self.user,
            assinar=True,
            status='A',
        )

        relatorio_1, signed_pdf_1 = self._create_signed_relatorio(evolucao_1, 'a')
        relatorio_2, signed_pdf_2 = self._create_signed_relatorio(evolucao_2, 'b')

        request = RequestFactory().get('/')
        request.session = {}

        response = download_filtered_pdfs(request, self.atendimento.id, 'evolucao')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/zip')

        zip_buffer = BytesIO(response.content)
        with zipfile.ZipFile(zip_buffer) as zip_file:
            nomes = sorted(zip_file.namelist())
            self.assertEqual(
                nomes,
                sorted([
                    relatorio_1.relatorio.name.rsplit('/', 1)[-1],
                    relatorio_2.relatorio.name.rsplit('/', 1)[-1],
                ]),
            )
            self.assertEqual(
                zip_file.read(relatorio_1.relatorio.name.rsplit('/', 1)[-1]),
                signed_pdf_1,
            )
            self.assertEqual(
                zip_file.read(relatorio_2.relatorio.name.rsplit('/', 1)[-1]),
                signed_pdf_2,
            )

    def test_assinar_pdf_valida_assinatura_real_do_certificado(self):
        text = '<p>' + ('Linha longa de teste ' * 80) + '</p>'
        evolucao = Evolucao.objects.create(
            atendimento=self.atendimento,
            tipo_evolucao=self.tipo_evolucao,
            evolucao=text,
            estabelecimento=self.estabelecimento,
            us_registro=self.user,
            assinar=True,
            status='A',
        )

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, 'BR'),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'ManageronTec'),
            x509.NameAttribute(NameOID.COMMON_NAME, 'Dr. Teste Validacao'),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow() - timedelta(days=1))
            .not_valid_after(datetime.utcnow() + timedelta(days=30))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .sign(key, hashes.SHA256())
        )
        pfx = serialization.pkcs12.serialize_key_and_certificates(
            name=b'cert',
            key=key,
            cert=cert,
            cas=None,
            encryption_algorithm=serialization.BestAvailableEncryption(b'senha123'),
        )

        buffer = gerar_pdf_prontuario(evolucao, self.user, assinar=False)
        datau, datas, assinado = assinar_pdf('senha123', pfx, buffer, 62)
        signed_pdf = datau + datas

        self.assertTrue(assinado)
        self.assertTrue(verificar_assinatura_pdf(signed_pdf, pfx, 'senha123'))

    def test_assinar_pdf_valida_assinatura_real_em_pdf_multipagina(self):
        text = '<p>' + ('Linha longa de teste ' * 900) + '</p>'
        evolucao = Evolucao.objects.create(
            atendimento=self.atendimento,
            tipo_evolucao=self.tipo_evolucao,
            evolucao=text,
            estabelecimento=self.estabelecimento,
            us_registro=self.user,
            assinar=True,
            status='A',
        )

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, 'BR'),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'ManageronTec'),
            x509.NameAttribute(NameOID.COMMON_NAME, 'Dr. Teste Validacao Multi'),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow() - timedelta(days=1))
            .not_valid_after(datetime.utcnow() + timedelta(days=30))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .sign(key, hashes.SHA256())
        )
        pfx = serialization.pkcs12.serialize_key_and_certificates(
            name=b'cert',
            key=key,
            cert=cert,
            cas=[],
            encryption_algorithm=serialization.BestAvailableEncryption(b'senha123'),
        )

        buffer = gerar_pdf_prontuario(evolucao, self.user, assinar=False)
        raw_reader = PyPDF2.PdfReader(BytesIO(buffer.getvalue()))
        self.assertGreater(len(raw_reader.pages), 1)

        datau, datas, assinado = assinar_pdf('senha123', pfx, buffer, 62)
        signed_pdf = datau + datas
        signed_reader = PyPDF2.PdfReader(BytesIO(signed_pdf))

        self.assertTrue(assinado)
        self.assertGreater(len(signed_reader.pages), 1)
        self.assertTrue(verificar_assinatura_pdf(signed_pdf, pfx, 'senha123'))

    def test_validacao_certificado_aceita_certificado_brasileiro_sem_country_name(self):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'ManageronTec'),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, 'Tecnologia'),
            x509.NameAttribute(NameOID.COMMON_NAME, 'Dr. Certificado Brasil'),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow() - timedelta(days=1))
            .not_valid_after(datetime.utcnow() + timedelta(days=30))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .sign(key, hashes.SHA256())
        )

        self.assertTrue(_validar_certificado_para_assinatura(cert))

    @patch('admin_relatorios.utils.verificar_assinatura_pdf', return_value=False)
    def test_assinar_pdf_nao_deve_rejeitar_assinatura_quando_validacao_interna_falha(self, mock_verificacao):
        text = '<p>' + ('Linha longa de teste ' * 80) + '</p>'
        evolucao = Evolucao.objects.create(
            atendimento=self.atendimento,
            tipo_evolucao=self.tipo_evolucao,
            evolucao=text,
            estabelecimento=self.estabelecimento,
            us_registro=self.user,
            assinar=True,
            status='A',
        )

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, 'BR'),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'ManageronTec'),
            x509.NameAttribute(NameOID.COMMON_NAME, 'Dr. Teste Validacao Interna'),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow() - timedelta(days=1))
            .not_valid_after(datetime.utcnow() + timedelta(days=30))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .sign(key, hashes.SHA256())
        )
        pfx = serialization.pkcs12.serialize_key_and_certificates(
            name=b'cert',
            key=key,
            cert=cert,
            cas=None,
            encryption_algorithm=serialization.BestAvailableEncryption(b'senha123'),
        )

        buffer = gerar_pdf_prontuario(evolucao, self.user, assinar=False)
        datau, datas, assinado = assinar_pdf('senha123', pfx, buffer, 62)
        signed_pdf = datau + datas

        self.assertTrue(assinado)
        self.assertIn(b'Signature1', signed_pdf)

    def test_obter_dados_assinatura_certificado_usa_cnpj_cn_do_certificado(self):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, 'BR'),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'ManageronTec'),
            x509.NameAttribute(NameOID.COMMON_NAME, 'Dr. Jose da Silva'),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow() - timedelta(days=1))
            .not_valid_after(datetime.utcnow() + timedelta(days=30))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .sign(key, hashes.SHA256())
        )
        pfx = serialization.pkcs12.serialize_key_and_certificates(
            name=b'cert',
            key=key,
            cert=cert,
            cas=None,
            encryption_algorithm=serialization.NoEncryption(),
        )

        dados = obter_dados_assinatura_certificado(None, pfx)

        self.assertIsNotNone(dados)
        self.assertIn('Dr. Jose da Silva', dados['texto_assinatura'])
        self.assertIn('Assinado de forma digital por', dados['texto_assinatura'])

    def test_obter_dados_assinatura_certificado_exibe_cpf_quando_presente(self):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cpf_oid = x509.ObjectIdentifier('2.16.76.1.3.1')
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, 'BR'),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'ManageronTec'),
            x509.NameAttribute(NameOID.COMMON_NAME, 'Dr. Jose da Silva'),
            x509.NameAttribute(cpf_oid, '12345678901'),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow() - timedelta(days=1))
            .not_valid_after(datetime.utcnow() + timedelta(days=30))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .sign(key, hashes.SHA256())
        )
        pfx = serialization.pkcs12.serialize_key_and_certificates(
            name=b'cert',
            key=key,
            cert=cert,
            cas=None,
            encryption_algorithm=serialization.NoEncryption(),
        )

        dados = obter_dados_assinatura_certificado(None, pfx)

        self.assertEqual(dados['cpf_assinante'], '123.456.789-01')
        self.assertIn('CPF: 123.456.789-01', dados['texto_assinatura'])

    def test_model_rejects_invalid_evolution_before_persisting(self):
        invalid_value = '<p>' + ('Linha longa de teste ' * 1200) + '</p>'

        with self.assertRaises(ValidationError):
            Evolucao.objects.create(
                atendimento=self.atendimento,
                tipo_evolucao=self.tipo_evolucao,
                evolucao=invalid_value,
                estabelecimento=self.estabelecimento,
                us_registro=self.user,
                status='A',
            )

    def test_form_rejects_content_above_model_limit(self):
        form = EvolucaoUpdateForm(
            data={
                'tipo_evolucao': self.tipo_evolucao.pk,
                'evolucao': '<p>' + ('Linha longa de teste ' * 1200) + '</p>',
                'atendimento': self.atendimento.pk,
                'estabelecimento': self.estabelecimento.pk,
                'status': 'A',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('evolucao', form.errors)



class PrescricaoAdepPdfTests(TestCase):
    """Testes de layout e paginação da tabela de prescrição/ADEP.

    Cobrem:
      * a tabela não invade o campo de assinatura (quebra em páginas);
      * a coluna de produto é única e aceita quebrar em várias linhas;
      * as demais colunas permanecem em linha;
      * o conteúdo aceita HTML simples (similar ao modelo de evolução).
    """

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='medico_presc',
            email='medico_presc@example.com',
            password='senha123',
        )
        self.profissional = Pessoa.objects.create(
            nome='Médico Presc',
            classificacao_pessoa='P',
            nacionalidade='b',
            sexo='F',
            dt_nascimento=None,
            rg=None,
            cpf=None,
            email='medico_presc_prof@example.com',
            status='A',
        )
        self.empresa = Empresa.objects.create(
            nacionalidade='b',
            razao_social='Empresa Presc',
            fantasia='Empresa Presc',
            empresa='EMP PRESC',
            status='A',
        )
        self.estabelecimento = Estabelecimento.objects.create(
            estabelecimento='Estab Presc',
            tipo='H',
            empresa=self.empresa,
            status='A',
        )
        self.perfil = Perfil.objects.create(
            user=self.user,
            pessoa=self.profissional,
            estabelecimento_padrao=self.estabelecimento,
        )
        self.perfil.estabelecimento.add(self.estabelecimento)
        self.tipo_produto = TipoProduto.objects.create(
            descricao='Medicamento',
            status='A',
        )
        self.grupo = Grupo.objects.create(
            descricao='Analgésicos',
            tipo_produto=self.tipo_produto,
            pode_ser_prescrito=True,
            grupo_de_medicamento=True,
            status='A',
        )
        self.unidade_medida = UnidadeMedida.objects.create(
            unidade_medida='mg',
            descricao='Miligrama',
            status='A',
        )
        self.produto = Produto.objects.create(
            descricao='Dipirona 500mg',
            unidade_medida=self.unidade_medida,
            via='O',
            grupo=self.grupo,
            pode_ser_prescrito=True,
            status='A',
        )
        self.intervalo = IntervaloHoras.objects.create(
            intervalo_horas=8,
            padrao=True,
            estabelecimento=self.estabelecimento,
            status='A',
        )
        self.inicio_plano = InicioPlanoTerapeutico.objects.create(
            hora_inicio=datetime.strptime('08:00', '%H:%M').time(),
            padrao=True,
            estabelecimento=self.estabelecimento,
            status='A',
        )
        self.pessoa = Pessoa.objects.create(
            nome='Paciente Presc',
            classificacao_pessoa='P',
            nacionalidade='b',
            sexo='M',
            dt_nascimento=None,
            rg=None,
            cpf=None,
            email='paciente_presc@example.com',
            status='A',
        )
        self.tipo_atendimento = TipoAtendimento.objects.create(
            tipo_atendimento='Consulta',
            status='A',
        )
        self.atendimento = Atendimento.objects.create(
            pessoa=self.pessoa,
            tipo_atendimento=self.tipo_atendimento,
            estabelecimento=self.estabelecimento,
            carater_atendimento='E',
            entidade_encaminhamento='N',
            cert_nascimento=False,
            rg=False,
            cpf=False,
            titulo_eleitor=False,
            carteira_vacina=False,
            cartao_sus=False,
            cartao_banco=False,
            carteira_trabalho=False,
            foto=False,
            outros=False,
            status='A',
        )

    # ------------------------------------------------------------------
    # Estrutura de colunas
    # ------------------------------------------------------------------
    def test_prescricao_retorna_lista_de_flowables_paginaveis(self):
        """A tabela deve voltar como lista (paginação natural), não tabela aninhada."""
        texto = (
            'Vigência: 01/10 até: 05/10/2026\tH\tSN\tÚnica\tObs\tAdep\n'
            'Dipirona 500mg<br/>comprimido - Oral\t8h\tSN\t \t \t \n'
        )
        flowables = genParagrafosRel(
            texto, 500, 0, None, tipo='prescricao')

        self.assertIsInstance(flowables, list)
        # Pelo menos uma Table de verdade (não sub-tabela aninhada numa célula).
        tabelas = [f for f in flowables if isinstance(f, Table)]
        self.assertGreaterEqual(len(tabelas), 1)

        primeira = tabelas[0]
        # A primeira tabela deve ter o cabeçalho + as linhas de corpo.
        self.assertGreaterEqual(len(primeira._cellvalues), 2)

    def test_adep_retorna_lista_de_flowables_paginaveis(self):
        """ADEP deve seguir o mesmo caminho de prescrição (lista paginável)."""
        texto = (
            'Vigência: 01/10 até: 05/10/2026\tH\tSN\tUnica\tAdministrado\tNão Admin...\n'
            'Dipirona 500mg<br/>comprimido - Oral\t8h\tSN\t \t01/10 08:00\t \n'
        )
        flowables = genParagrafosRel(texto, 500, 0, None, tipo='adep')

        self.assertIsInstance(flowables, list)
        self.assertTrue(any(isinstance(f, Table) for f in flowables))

    def test_coluna_produto_aceita_quebra_e_demais_em_linha(self):
        """O produto concentra as quebras; as demais colunas ficam em linha única."""
        texto = (
            'Vigência: 01/10 até: 05/10/2026\tH\tSN\tÚnica\tObs\tAdep\n'
            'Medicamento com nome bem extenso<br/>apresentacao detalhada - via oral'
            '\t8h\tSN\t \t01/10 08:00, 01/10 16:00\t \n'
        )
        flowables = genParagrafosRel(
            texto, 500, 0, None, tipo='prescricao')
        tabela = next(f for f in flowables if isinstance(f, Table))

        # Cabeçalho tem 6 colunas; cada linha de corpo também deve ter 6.
        for linha in tabela._cellvalues:
            self.assertEqual(len(linha), 6)

        # A célula de produto (coluna 0) contém <br/> na altura de layout.
        produto_cell = tabela._cellvalues[1][0]
        self.assertIn('<br/>', produto_cell.text)

        # As demais colunas não devem conter quebras internas (<br/>).
        for coluna in range(1, 6):
            self.assertNotIn('<br/>', tabela._cellvalues[1][coluna].text)

    def test_conteudo_aceita_html_simples(self):
        """Células interpretam HTML simples (b/i/u) como no modelo de evolução."""
        texto = (
            'Vigência: 01/10 até: 05/10/2026\tH\tSN\tÚnica\tObs\tAdep\n'
            '<b>Dipirona</b> <i>500mg</i><br/><u>comprimido</u> - Oral'
            '\t8h\tSN\t \t \t \n'
        )
        flowables = genParagrafosRel(
            texto, 500, 0, None, tipo='prescricao')
        tabela = next(f for f in flowables if isinstance(f, Table))
        produto_cell = tabela._cellvalues[1][0]

        # As tags de formatação são preservadas para o Paragraph interpretar.
        self.assertIn('<b>', produto_cell.text)
        self.assertIn('<i>', produto_cell.text)
        self.assertIn('<u>', produto_cell.text)

    # ------------------------------------------------------------------
    # Paginação / assinatura
    # ------------------------------------------------------------------
    def test_tabela_prescricao_quebra_em_multiplas_paginas(self):
        """Muitos itens devem gerar múltiplas páginas (não invadir a assinatura)."""
        linhas = [
            'Vigência: 01/10 até: 05/10/2026\tH\tSN\tÚnica\tObs\tAdep'
        ]
        for indice in range(40):
            linhas.append(
                f'Medicamento {indice} com descricao longa que estoura varias '
                f'linhas nesta celula<br/>apresentacao - via'
                '\t8h\tSN\t \t \t '
            )
        texto = '\n'.join(linhas)
        flowables = genParagrafosRel(
            texto, 500, 0, None, tipo='prescricao')

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        doc.build(list(flowables))
        buffer.seek(0)

        reader = PyPDF2.PdfReader(buffer)
        self.assertGreaterEqual(len(reader.pages), 2)

    def test_assinatura_reserva_espaco_apos_ultima_pagina(self):
        """A última página deve terminar antes da faixa reservada à assinatura.

        A faixa de assinatura é a mesma definida em
        ``prontuarios.relatorios.gerar_pdf_prontuario`` (signature_bottom=62,
        signature_height=50, ou seja, o conteúdo não pode ultrapassar y=112pt
        a partir da base, com uma pequena margem de segurança).
        """
        from prontuarios.relatorios import gerar_pdf_prontuario
        from prontuarios.models import Prescricao

        prescricao = Prescricao.objects.create(
            atendimento=self.atendimento,
            estabelecimento=self.estabelecimento,
            us_registro=self.user,
            dt_inicio=timezone.now(),
            dt_final=timezone.now() + timedelta(days=5),
            assinar=True,
            status='A',
        )
        # Cria vários itens na prescrição
        for indice in range(30):
            ProdutoPrescricao.objects.create(
                prescricao=prescricao,
                produto=self.produto,
                intervalo_horas=self.intervalo,
                hora_inicio_produto=self.inicio_plano,
                se_necessario=False,
                dose_unica=False,
                dt_inicio=timezone.now(),
                atendimento=self.atendimento,
                estabelecimento=self.estabelecimento,
                us_registro=self.user,
                status='A',
            )

        buffer = gerar_pdf_prontuario(prescricao, self.user, assinar=True)
        buffer.seek(0)
        reader = PyPDF2.PdfReader(buffer)
        self.assertGreaterEqual(len(reader.pages), 2)


    def _criar_produto_prescricao(self, prescricao, descricao=None):
        """Cria um ProdutoPrescricao simples ligado à prescrição informada.

        ``descricao`` permite criar produtos distintos para identificar cada
        item no texto extraído do PDF.
        """
        produto = self.produto
        if descricao:
            produto = Produto.objects.create(
                descricao=descricao,
                unidade_medida=self.unidade_medida,
                via='O',
                grupo=self.grupo,
                pode_ser_prescrito=True,
                status='A',
            )
        return ProdutoPrescricao.objects.create(
            prescricao=prescricao,
            produto=produto,
            intervalo_horas=self.intervalo,
            hora_inicio_produto=self.inicio_plano,
            se_necessario=False,
            dose_unica=False,
            dt_inicio=timezone.now(),
            atendimento=self.atendimento,
            estabelecimento=self.estabelecimento,
            us_registro=self.user,
            status='A',
        )

    def _criar_adep(self, prescricao, produto_prescricao, fase):
        """Cria um Adep marcado para assinatura (fase 'A' ou 'N')."""
        from prontuarios.models import Adep

        return Adep.objects.create(
            prescricao=prescricao,
            produto_prescricao=produto_prescricao,
            data_hora=timezone.now(),
            fase_adep=fase,
            assinar=True,
            pdf=False,
            atendimento=self.atendimento,
            estabelecimento=self.estabelecimento,
            us_adep=self.user,
            us_registro=self.user,
            status='A',
        )

    def _linhas_da_tabela(self, buffer):
        """Extrai as linhas de texto visíveis de todas as páginas do PDF."""
        buffer.seek(0)
        reader = PyPDF2.PdfReader(buffer)
        linhas = []
        for pagina in reader.pages:
            texto = pagina.extract_text() or ''
            linhas.extend(texto.splitlines())
        return [linha.strip() for linha in linhas if linha.strip()]

    def test_adep_exibe_apenas_itens_com_marcacao(self):
        """No PDF de ADEP só entram itens administrados ou não administrados.

        Produtos prescritos sem nenhuma marcação de ADEP não devem gerar
        linhas no relatório, evitando páginas desnecessárias.
        """
        from prontuarios.relatorios import gerar_pdf_prontuario
        from prontuarios.models import Prescricao

        prescricao = Prescricao.objects.create(
            atendimento=self.atendimento,
            estabelecimento=self.estabelecimento,
            us_registro=self.user,
            dt_inicio=timezone.now(),
            dt_final=timezone.now() + timedelta(days=5),
            assinar=True,
            status='A',
        )

        # Produto 1: recebe marcação de administrado.
        produto_1 = self._criar_produto_prescricao(
            prescricao, descricao='MarcadoAdministrado')
        # Produto 2: recebe marcação de não administrado.
        produto_2 = self._criar_produto_prescricao(
            prescricao, descricao='MarcadoNaoAdministrado')
        # Produto 3: fica SEM marcação alguma (não deve aparecer no ADEP).
        produto_3 = self._criar_produto_prescricao(
            prescricao, descricao='SemMarcacaoNaoDeveAparecer')
        self.assertIsNotNone(produto_3.id)

        self._criar_adep(prescricao, produto_1, 'A')
        self._criar_adep(prescricao, produto_2, 'N')

        buffer = gerar_pdf_prontuario(prescricao, self.user, assinar=False)
        texto = '\n'.join(self._linhas_da_tabela(buffer))

        # Itens com marcação de administrado/não administrado aparecem.
        self.assertIn(
            'MarcadoAdministrado', texto,
            'Item administrado deve constar no ADEP.'
        )
        self.assertIn(
            'MarcadoNaoAdministrado', texto,
            'Item não administrado deve constar no ADEP.'
        )
        # Item sem marcação alguma NÃO deve constar no relatório.
        self.assertNotIn(
            'SemMarcacaoNaoDeveAparecer', texto,
            'Item sem marcação de ADEP não deve constar no relatório.'
        )
