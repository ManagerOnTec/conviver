from django.db import IntegrityError
from admin_cadastros.models import Pessoa, PessoaCampos, TipoAtendimento
from datetime import datetime
from django.contrib import messages
from django import forms
from contas import models
from . models import Oficios
from unidecode import unidecode
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.utils.text import capfirst
from admin_cadastros.widgets import TabelaCampoWidget
from dominios.utils import FilterByStatusMixin, validar_whats, validar_telefone
from django_select2.forms import Select2Widget
from django_select2.forms import ModelSelect2Widget
from django_select2.views import AutoResponseView
from django.forms.widgets import DateInput, DateTimeInput
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from dominios.widgets import DateTimePickerInput
from django.core.validators import FileExtensionValidator
from django_select2.forms import Select2MultipleWidget
from admin_cadastros_assistenciais.models import CID
from tinymce.widgets import TinyMCE
from django.core.validators import MaxLengthValidator
from dominios.text_validators import validate_evolucao_like_text


class OficiosCreateForm(FilterByStatusMixin, forms.ModelForm):

    oficio = forms.CharField(
        widget=TinyMCE(
            attrs={'cols': 80, 'rows': 44},
            mce_attrs={'height': 900,
                       'toolbar': 'undo redo | bold italic | alignleft aligncenter alignright alignjustify | outdent indent',
                       'menubar': False,
                       'contextmenu': False}
        ),
        validators=[
            validate_evolucao_like_text
        ]
    )

    class Meta:
        model = Oficios
        exclude = ('dt_registro', 'dt_atualizacao',
                   'us_registro', 'us_atualizacao', 'status', 'estabelecimento',)


class OficiosDetailForm(forms.ModelForm):
    class Meta:
        model = Oficios
        exclude = ('pessoa',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields:
            self.fields[field].widget.attrs['disabled'] = True

###############################################################################


class OficiosUpdateForm(FilterByStatusMixin, forms.ModelForm):

    oficio = forms.CharField(
        widget=TinyMCE(
            attrs={'cols': 80, 'rows': 44},
            mce_attrs={'height': 900,
                       'toolbar': 'undo redo | bold italic | alignleft aligncenter alignright alignjustify | outdent indent',
                       'menubar': False,
                       'contextmenu': False}
        ),
        validators=[
            validate_evolucao_like_text
        ]
    )

    class Meta:
        model = Oficios
        exclude = ('dt_registro', 'dt_atualizacao', 'us_registro',
                   'us_atualizacao', 'estabelecimento',)
