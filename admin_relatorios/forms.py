from tinymce.widgets import TinyMCE
from django import forms
from django.utils import timezone
from django.forms import TextInput, inlineformset_factory
from admin_evolucoes.models import TipoEvolucao, TextoPadrao
from django.core.validators import MinLengthValidator
from dominios.utils import FilterByStatusMixin
from .models import GerenciadorRelatorioPersonalizado, GerenciadorRelatorioGeral
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from dominios.text_validators import validate_evolucao_like_text
from django import forms
from .models import TextoDocumentoPadrao


EDITOR_PADRAO_EVOLUCAO = TinyMCE(
    attrs={'cols': 80, 'rows': 44},
    mce_attrs={
        'height': 900,
        'toolbar': 'undo redo | bold italic | alignleft aligncenter alignright alignjustify | outdent indent',
        'menubar': False,
        'contextmenu': False,
    }
)


class GerenciadorRelatorioGeralForm(FilterByStatusMixin, forms.ModelForm):

    class Meta:
        model = GerenciadorRelatorioGeral

        exclude = ('us_registro', 'us_atualizacao',
                   'dt_registro', 'dt_atualizacao')

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super(GerenciadorRelatorioGeralForm, self).__init__(*args, **kwargs)

        if self.instance._state.adding:
            self.fields['status'].widget = forms.HiddenInput()

    def clean_dados_header(self):
        return self.cleaned_data['dados_header'].title()

    def clean_dados_right_header(self):
        return self.cleaned_data['dados_right_header'].title()

    def clean_dados_footer(self):
        return self.cleaned_data['dados_footer'].title()


class GerenciadorRelatorioPersonalizadoForm(FilterByStatusMixin, forms.ModelForm):

    class Meta:
        model = GerenciadorRelatorioPersonalizado

        exclude = ('us_registro', 'us_atualizacao',
                   'dt_registro', 'dt_atualizacao')

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super(GerenciadorRelatorioPersonalizadoForm,
              self).__init__(*args, **kwargs)

        if self.instance._state.adding:
            self.fields['status'].widget = forms.HiddenInput()

    def clean_dados_header(self):
        dados_header = self.cleaned_data.get('dados_header')
        return dados_header.title() if dados_header else None

    def clean_dados_right_header(self):
        dados_right_header = self.cleaned_data.get('dados_right_header')
        return dados_right_header.title() if dados_right_header else None

    def clean_dados_footer(self):
        dados_footer = self.cleaned_data.get('dados_footer')
        return dados_footer.title() if dados_footer else None

    def clean(self):
        cleaned_data = super().clean()
        relatorio = cleaned_data.get("relatorio")
        tipo_evolucao = cleaned_data.get("tipo_evolucao")
        tipo_documento_legal = cleaned_data.get("tipo_documento_legal")

        # Se 'relatorio' for 'evolucao', então 'tipo_evolucao' é obrigatório
        if relatorio == "evolucao" and not tipo_evolucao:
            self.add_error(
                'tipo_evolucao', "O campo Tipo Evolução é obrigatório quando Relatório é Evolução.")

        if relatorio == "documentos_legais" and not tipo_documento_legal:
            self.add_error(
                'tipo_documento_legal',
                "O campo Tipo de Documento Legal é obrigatório quando Relatório é Documentos Legais.")

        if relatorio != "evolucao":
            cleaned_data['tipo_evolucao'] = None

        if relatorio != "documentos_legais":
            cleaned_data['tipo_documento_legal'] = None

        return cleaned_data


class TextoDocumentoPadraoForm(forms.ModelForm):
    texto = forms.CharField(
        widget=EDITOR_PADRAO_EVOLUCAO,
        validators=[validate_evolucao_like_text],
        label='Textos Padronizados'
    )

    class Meta:
        model = TextoDocumentoPadrao
        fields = '__all__'
