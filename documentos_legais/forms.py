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
    foto_documento_data = forms.CharField(widget=forms.HiddenInput(), required=False)
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

        self.exige_assinatura_responsavel = True
        self.exige_assinatura_atendente = True
        self._aplicar_exigencias_do_modelo()

    def _get_modelo_selecionado(self):
        """Retorna o modelo escolhido, considerando POST/GET ou edição."""
        modelo_id = self.data.get('modelo_documento') or getattr(self.instance, 'modelo_documento_id', None)
        if not modelo_id:
            if getattr(self.instance, 'modelo_documento_id', None):
                return self.instance.modelo_documento
            return None
        return ModeloDocumentoLegal.objects.filter(pk=modelo_id).first()

    def _definir_exigencia_responsavel(self, forcar_nao_obrigatorio=False):
        """Define obrigatoriedade dos dados do responsável conforme o modelo.

        Quando o modelo exige a assinatura do responsável, nome/CPF/documento/nascimento
        são obrigatórios. Caso contrário, todos ficam opcionais e podem ser omitidos.

        Com forcar_nao_obrigatorio=True (nenhum modelo escolhido ainda, ex.: GET inicial),
        os campos ficam opcionais.
        """
        obrigatorio = False if forcar_nao_obrigatorio else self._exige_assinatura_responsavel()
        campos_responsavel = [
            'responsavel_nome',
            'responsavel_cpf',
            'responsavel_documento',
            'responsavel_data_nascimento',
        ]
        for nome_campo in campos_responsavel:
            self.fields[nome_campo].required = obrigatorio

    def _aplicar_exigencias_do_modelo(self):
        """Ajusta obrigatoriedade e opções conforme as exigências do modelo.

        - Sem assinatura do responsável: dados do responsável, assinatura desenhada e
          fotos deixam de ser obrigatórios e o valor do campo é ignorado no salvamento.
        - Sem assinatura do atendente: a opção de assinatura digital do funcionário é
          desmarcada e forçada para falso.
        """
        modelo = self._get_modelo_selecionado()
        if modelo is None:
            # Sem modelo selecionado ainda (ex.: GET inicial, onde as opções de modelo
            # chegam via AJAX), não marcamos os campos do responsável como obrigatórios
            # para não exibir "obrigatório" indevidamente. O JS/clean ajustam depois,
            # conforme o modelo escolhido.
            self._definir_exigencia_responsavel(forcar_nao_obrigatorio=True)
            return

        self.exige_assinatura_responsavel = modelo.exige_assinatura_responsavel
        self.exige_assinatura_atendente = modelo.exige_assinatura_atendente

        if not self.exige_assinatura_atendente:
            # Desmarca e desabilita a assinatura do funcionário quando o modelo não a exige.
            self.fields['assinar_funcionario'].initial = False
            self.fields['assinar_funcionario'].disabled = True
            if self.data.get('modelo_documento'):
                self.data = self.data.copy()
                self.data.pop('assinar_funcionario', None)

        self._definir_exigencia_responsavel()

    def _exige_assinatura_responsavel(self):
        return self.exige_assinatura_responsavel

    def _exige_assinatura_atendente(self):
        return self.exige_assinatura_atendente


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

        # Reaplica as exigências do modelo (cobre POST onde o __init__ pode ter sido
        # chamado antes do modelo estar disponível).
        self._aplicar_exigencias_do_modelo()

        if self._exige_assinatura_responsavel():
            assinatura_data = cleaned_data.get('assinatura_data')
            if not assinatura_data and not getattr(self.instance, 'assinatura_imagem', None):
                self.add_error(None, 'Desenhe a assinatura do responsável antes de salvar o termo.')

            foto_validacao_data = cleaned_data.get('foto_validacao_data')
            foto_documento_data = cleaned_data.get('foto_documento_data')
            if not foto_validacao_data and not getattr(self.instance, 'selfie', None):
                self.add_error('foto_validacao_data', 'Capture a foto do responsável pelo notebook antes de salvar o termo.')
            if not foto_documento_data and not getattr(self.instance, 'foto_documento', None):
                self.add_error('foto_documento_data', 'Capture a foto do documento do responsável antes de salvar o termo.')
        else:
            # Modelo não exige assinatura do responsável: ignora assinatura/fotos.
            cleaned_data['assinatura_data'] = ''
            cleaned_data['foto_validacao_data'] = ''
            cleaned_data['foto_documento_data'] = ''

        if not cleaned_data.get('declaracao_aceite'):
            self.add_error('declaracao_aceite', 'É obrigatório confirmar a leitura e concordância com o termo.')

        if self._exige_assinatura_atendente() and cleaned_data.get('assinar_funcionario'):
            self._validar_assinatura_funcionario()
        else:
            # Sem exigência do atendente, a assinatura digital do funcionário é descartada.
            cleaned_data['assinar_funcionario'] = False

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

    def _save_camera_capture(self, instance, data_url, field_name='selfie', prefix='foto_validacao'):
        image_bytes = self._decode_signature(data_url)
        field = getattr(instance, field_name)
        field.save(
            f'{prefix}_{uuid.uuid4().hex}.png',
            ContentFile(image_bytes),
            save=False,
        )

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.atendimento = self.atendimento
        instance.pessoa = self.atendimento.pessoa
        instance.estabelecimento = self.atendimento.estabelecimento
        instance.titulo_documento = self.cleaned_data['modelo_documento'].titulo_documento
        instance.conteudo_html = getattr(self, 'rendered_html', instance.conteudo_html)
        instance.tipo_documento = self.cleaned_data['tipo_documento']
        instance.modelo_documento = self.cleaned_data['modelo_documento']

        if self._exige_assinatura_responsavel():
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
                self._save_camera_capture(instance, foto_validacao_data, 'selfie', 'foto_validacao')

            foto_documento_data = self.cleaned_data.get('foto_documento_data')
            if foto_documento_data:
                self._save_camera_capture(instance, foto_documento_data, 'foto_documento', 'foto_documento')
        else:
            # Não exige assinatura do responsável: garante que nada seja anexado e que
            # os dados do responsável não sejam gravados (o PDF não os exibe nesse caso).
            instance.assinatura_imagem = None
            instance.selfie = None
            instance.foto_documento = None
            instance.responsavel_nome = None
            instance.responsavel_cpf = None
            instance.responsavel_documento = None
            instance.responsavel_data_nascimento = None

        if self.request:
            instance.ip_assinatura = obter_ip_cliente(self.request)[:45]
            instance.user_agent = (self.request.META.get('HTTP_USER_AGENT') or '')[:500]

        if commit:
            instance.save()

        return instance
