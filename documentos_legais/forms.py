import base64
import uuid
from urllib.parse import unquote

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db.models import Q
from tinymce.widgets import TinyMCE

from admin_relatorios.utils import obter_dados_assinatura_certificado
from contas.models import Perfil
from dominios.text_validators import validate_evolucao_like_text
from .models import DocumentoLegalInternacao, ModeloDocumentoLegal, TipoDocumentoLegal
from .services import render_documento_html, obter_ip_cliente


EDITOR_PADRAO_DOCUMENTO = TinyMCE(
    attrs={'cols': 80, 'rows': 44},
    mce_attrs={
        'height': 900,
        'toolbar': 'undo redo | bold italic | alignleft aligncenter alignright alignjustify | bullist numlist | outdent indent',
        'menubar': False,
        'contextmenu': False,
    }
)


class TipoDocumentoLegalAdminForm(forms.ModelForm):
    class Meta:
        model = TipoDocumentoLegal
        fields = '__all__'

    def clean_nome(self):
        return self.cleaned_data['nome'].title()


class ModeloDocumentoLegalAdminForm(forms.ModelForm):
    conteudo_html = forms.CharField(widget=EDITOR_PADRAO_DOCUMENTO, validators=[validate_evolucao_like_text])

    class Meta:
        model = ModeloDocumentoLegal
        fields = '__all__'

    def clean_nome_modelo(self):
        return self.cleaned_data['nome_modelo'].title()

    def clean_titulo_documento(self):
        return self.cleaned_data['titulo_documento'].title()


class DocumentoLegalInternacaoForm(forms.ModelForm):
    assinatura_data = forms.CharField(widget=forms.HiddenInput(), required=False)
    foto_validacao_data = forms.CharField(widget=forms.HiddenInput(), required=False)
    assinar_funcionario = forms.BooleanField(
        required=False,
        initial=True,
        label='Assinar também com o certificado digital do funcionário logado',
        help_text='Quando marcado, o PDF será assinado com o certificado digital do usuário do sistema. Desmarque para gerar o termo sem a assinatura digital.',
    )

    class Meta:
        model = DocumentoLegalInternacao
        fields = [
            'tipo_documento',
            'modelo_documento',
            'responsavel_nome',
            'responsavel_cpf',
            'responsavel_documento',
            'responsavel_data_nascimento',
            'responsavel_telefone',
            'responsavel_email',
            'declaracao_aceite',
            'observacoes',
        ]
        widgets = {
            'responsavel_data_nascimento': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        self.atendimento = kwargs.pop('atendimento')
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        self.fields['tipo_documento'].queryset = TipoDocumentoLegal.objects.filter(status='A').order_by('ordem', 'nome')

        tipo_id = self.data.get('tipo_documento') or getattr(self.instance, 'tipo_documento_id', None)
        if tipo_id:
            self.fields['modelo_documento'].queryset = self._get_modelos_queryset(tipo_id)
        else:
            self.fields['modelo_documento'].queryset = ModeloDocumentoLegal.objects.none()

        self.fields['modelo_documento'].required = True
        self.fields['observacoes'].required = False
        self.fields['responsavel_telefone'].required = False
        self.fields['responsavel_email'].required = False

        self.fields['foto_validacao_data'].help_text = 'Capture uma foto pelo notebook para validar a assinatura e o atendimento.'

        if self.request and self.request.user.is_authenticated:
            perfil = getattr(self.request.user, 'perfil', None)
            if not perfil or not perfil.certificado_digital or not perfil.senha_certificado:
                self.fields['assinar_funcionario'].help_text = (
                    'Para assinar digitalmente, o usuário logado precisa ter certificado .pfx e senha cadastrados no perfil.'
                )

    def _get_modelos_queryset(self, tipo_id):
        return ModeloDocumentoLegal.objects.filter(
            tipo_documento_id=tipo_id,
            status='A',
        ).filter(
            Q(estabelecimento=self.atendimento.estabelecimento) |
            Q(estabelecimento__isnull=True)
        ).select_related('estabelecimento', 'tipo_documento').order_by('-estabelecimento_id', 'nome_modelo')

    def clean_modelo_documento(self):
        modelo = self.cleaned_data.get('modelo_documento')
        if not modelo:
            raise ValidationError('Selecione um modelo de documento.')
        if modelo.estabelecimento_id and modelo.estabelecimento_id != self.atendimento.estabelecimento_id:
            raise ValidationError('O modelo selecionado não pertence ao estabelecimento deste atendimento.')
        return modelo

    def clean(self):
        cleaned_data = super().clean()

        assinatura_data = cleaned_data.get('assinatura_data')
        if not assinatura_data and not getattr(self.instance, 'assinatura_imagem', None):
            self.add_error(None, 'Desenhe a assinatura do responsável antes de salvar o termo.')

        foto_validacao_data = cleaned_data.get('foto_validacao_data')
        if not foto_validacao_data and not any([
            getattr(self.instance, 'selfie', None),
            getattr(self.instance, 'documento_frente', None),
            getattr(self.instance, 'documento_verso', None),
        ]):
            self.add_error('foto_validacao_data', 'Capture a foto de validação pelo notebook antes de salvar o termo.')

        if not cleaned_data.get('declaracao_aceite'):
            self.add_error('declaracao_aceite', 'É obrigatório confirmar a leitura e concordância com o termo.')

        if cleaned_data.get('assinar_funcionario'):
            self._validar_assinatura_funcionario()

        modelo = cleaned_data.get('modelo_documento')
        if modelo:
            self.rendered_html = render_documento_html(
                modelo,
                self.atendimento,
                self._get_responsavel_data(cleaned_data),
            )

        return cleaned_data

    def _get_responsavel_data(self, cleaned_data):
        return {
            'responsavel_nome': cleaned_data.get('responsavel_nome', ''),
            'responsavel_cpf': cleaned_data.get('responsavel_cpf', ''),
            'responsavel_documento': cleaned_data.get('responsavel_documento', ''),
            'responsavel_data_nascimento': cleaned_data.get('responsavel_data_nascimento'),
            'responsavel_telefone': cleaned_data.get('responsavel_telefone', ''),
            'responsavel_email': cleaned_data.get('responsavel_email', ''),
        }

    def _decode_signature(self, assinatura_data):
        assinatura_data = unquote(assinatura_data or '')
        if ';base64,' not in assinatura_data:
            raise ValidationError('Formato da assinatura inválido.')
        _, encoded = assinatura_data.split(';base64,', 1)
        try:
            return base64.b64decode(encoded)
        except Exception as exc:
            raise ValidationError('Não foi possível processar a assinatura desenhada.') from exc

    def _validar_assinatura_funcionario(self):
        if not self.request or not self.request.user.is_authenticated:
            self.add_error('assinar_funcionario', 'Não foi possível identificar o usuário do sistema para a assinatura digital.')
            return

        perfil = getattr(self.request.user, 'perfil', None)
        if not perfil or not perfil.certificado_digital or not perfil.senha_certificado:
            self.add_error(
                'assinar_funcionario',
                'O usuário logado precisa ter certificado digital .pfx e senha cadastrados no perfil para assinar este documento.'
            )
            return

        try:
            with perfil.certificado_digital.open('rb') as certificado_file:
                certificado_bytes = certificado_file.read()
        except Exception:
            self.add_error('assinar_funcionario', 'Não foi possível ler o certificado digital do usuário logado.')
            return

        assinatura_info = obter_dados_assinatura_certificado(perfil.senha_certificado, certificado_bytes)
        if not assinatura_info:
            self.add_error('assinar_funcionario', 'O certificado digital do usuário logado é inválido, está vencido ou não pôde ser validado.')

    def _save_camera_capture(self, instance, data_url):
        image_bytes = self._decode_signature(data_url)
        instance.selfie.save(
            f'foto_validacao_{uuid.uuid4().hex}.png',
            ContentFile(image_bytes),
            save=False,
        )
        instance.documento_frente = None
        instance.documento_verso = None

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.atendimento = self.atendimento
        instance.pessoa = self.atendimento.pessoa
        instance.estabelecimento = self.atendimento.estabelecimento
        instance.titulo_documento = self.cleaned_data['modelo_documento'].titulo_documento
        instance.conteudo_html = getattr(self, 'rendered_html', instance.conteudo_html)
        instance.tipo_documento = self.cleaned_data['tipo_documento']
        instance.modelo_documento = self.cleaned_data['modelo_documento']

        assinatura_data = self.cleaned_data.get('assinatura_data')
        if assinatura_data:
            assinatura_bytes = self._decode_signature(assinatura_data)
            instance.assinatura_imagem.save(
                f'assinatura_{uuid.uuid4().hex}.png',
                ContentFile(assinatura_bytes),
                save=False,
            )

        foto_validacao_data = self.cleaned_data.get('foto_validacao_data')
        if foto_validacao_data:
            self._save_camera_capture(instance, foto_validacao_data)

        if self.request:
            instance.ip_assinatura = obter_ip_cliente(self.request)[:45]
            instance.user_agent = (self.request.META.get('HTTP_USER_AGENT') or '')[:500]

        if commit:
            instance.save()

        return instance
