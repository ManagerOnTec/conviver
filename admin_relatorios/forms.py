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
from dominios.utils import validar_tamanho_ata
from django import forms
from .models import TextoDocumentoPadrao


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

        # Se 'relatorio' for 'evolucao', então 'tipo_evolucao' é obrigatório
        if relatorio == "evolucao" and not tipo_evolucao:
            self.add_error(
                'tipo_evolucao', "O campo Tipo Evolução é obrigatório quando Relatório é Evolução.")

        return cleaned_data


class TextoDocumentoPadraoForm(forms.ModelForm):
    texto = forms.CharField(
        widget=TinyMCE(attrs={'cols': 80, 'rows': 30}),
        validators=[validar_tamanho_ata],
        label='Textos Padronizados'
    )

    class Meta:
        model = TextoDocumentoPadrao
        fields = '__all__'
