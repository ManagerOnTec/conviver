import base64
from datetime import datetime, timedelta
from io import BytesIO
import zipfile

import PyPDF2
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

from admin_cadastros.models import Estabelecimento, Pessoa, Empresa, TipoAtendimento
from admin_evolucoes.models import TipoEvolucao
from admin_relatorios.models import GerenciadorRelatorioGeral
from admin_relatorios.models import Relatorio
from admin_relatorios.rel_paragrafos import genParagrafosRel
from atendimentos.models import Atendimento
from atas.models import Atas
from contas.models import Perfil
from oficios.models import Oficios
from orcamentos.models import Orcamentos
from prontuarios.forms import EvolucaoCreateForm, EvolucaoUpdateForm
from prontuarios.models import Evolucao, MAX_EVOLUCAO_TEXT_LENGTH, validate_evolucao_texto
from prontuarios.relatorios import gerar_pdf_prontuario
from prontuarios.views import EvolucaoCreateView, download_filtered_pdfs
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
