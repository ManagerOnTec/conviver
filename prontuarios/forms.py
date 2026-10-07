from .models import Prescricao, CadastroProfissional
from django.utils.timezone import now, make_aware, is_naive, get_current_timezone
from .models import Prescricao
from admin_prescricoes.models import ParametrosPrescricao
from admin_cadastros_assistenciais.models import CadastroProfissional
from datetime import datetime, time, timedelta
from datetime import time
from django.db.models import Q
from django.utils.timezone import now, localtime, make_aware, is_naive, get_current_timezone
from datetime import timedelta
from admin_evolucoes.models import TipoEvolucao
from .models import Adep, Diagnostico, Psicoterapia
from django.core.validators import MinLengthValidator
from django.forms import TextInput, inlineformset_factory
from django.forms.utils import ErrorList
from django.core.exceptions import NON_FIELD_ERRORS
from django.core.exceptions import ValidationError
from admin_cadastros_assistenciais.models import CID, CadastroProfissional
from admin_estoques.models import Produto
from admin_prescricoes.forms import BaseModelPrescricaoForm
from admin_prescricoes.models import InicioPlanoTerapeutico, IntervaloHoras, ParametrosPrescricao
from .models import SAE, PerdasGanhos, PlanoCuidados, Prescricao, ProdutoPrescricao, SinaisVitais, PassagemPlantao
from admin_logs.models import ProntuarioAcessos
from django.contrib.auth.models import User
from dominios.widgets import DateTimePickerInput
from crispy_forms.layout import Submit
from crispy_forms.helper import FormHelper
from django.forms.widgets import DateInput, DateTimeInput
from django_select2.views import AutoResponseView
from django_select2.forms import ModelSelect2Widget
from django_select2.forms import Select2Widget
from dominios.utils import FilterByStatusMixin, NoneToEmptyMixin, validar_whats, validar_telefone
from admin_cadastros.widgets import TabelaCampoWidget
from . models import Atendimento
from contas import models
from datetime import datetime, timedelta
from admin_cadastros.models import Pessoa, TipoAtendimento
from django.db import IntegrityError
from django.urls import reverse, reverse_lazy
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.contrib import messages
from django import forms
from prontuarios.models import Evolucao, MAX_EVOLUCAO_TEXT_LENGTH, validate_evolucao_texto
from unidecode import unidecode
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.utils.text import capfirst
from dominios.utils import FilterByStatusMixin
from atendimentos.models import Atendimento
from django.forms import HiddenInput
from django.contrib import messages
from admin_sae.models import Aspecto, AspectoAnalisado, Evidencia, DiagnosticoEnfermagem, FatorRelacionado, Intervencao
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from tinymce.widgets import TinyMCE
from django.core.validators import MaxLengthValidator
from django_select2.forms import Select2MultipleWidget
from dominios.utils import validar_tamanho_ata
from django.db.models import Q


class EvolucaoCreateForm(FilterByStatusMixin, forms.ModelForm):

    evolucao = forms.CharField(
        widget=TinyMCE(
            attrs={'cols': 80, 'rows': 44},
            mce_attrs={'height': 900,
                       'toolbar': 'undo redo | bold italic | alignleft aligncenter alignright alignjustify | outdent indent',
                       'menubar': False,
                       'contextmenu': False}),
        validators=[
            validate_evolucao_texto,
        ],
    )

    class Meta:
        model = Evolucao
        # Liste aqui todos os campos necessários para a evolução, exceto 'atendimento'
        exclude = ['pessoa', 'atendimento', 'created_by', 'relatorio',
                   'estabelecimento', 'us_registro', 'dt_registro', 'dt_atualizacao', 'us_atualizacao']

        widgets = {
            'atendimento': HiddenInput(),
            'status': HiddenInput(),
        }

    def __init__(self, *args, **kwargs):

        atendimento = kwargs.pop('atendimento', None)
        user = kwargs.pop('user', None)
        estabelecimento = kwargs.pop('estabelecimento', None)

        super().__init__(*args, **kwargs)

        self.instance.created_by = user

        if not self.instance.pk:
            self.fields['status'].widget.attrs['style'] = 'display:none;'

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Atribui o usuário que está criando a evolução
        # instance.created_by = self.initial.get('user')

        if commit:
            instance.save()
        return instance


class EvolucaoDetailForm(forms.ModelForm):

    evolucao = forms.CharField(
        widget=TinyMCE(
            attrs={'cols': 80, 'rows': 44, },
            mce_attrs={
                'height': 900,
                'toolbar': 'undo redo | bold italic | alignleft aligncenter alignright alignjustify | outdent indent',
                'menubar': False,
                'contextmenu': False,
            }
        )
    )

    class Meta:
        model = Evolucao
        exclude = ('pessoa', 'atendimento')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields:
            self.fields[field].widget.attrs['disabled'] = True


class EvolucaoUpdateForm(forms.ModelForm):

    evolucao = forms.CharField(
        widget=TinyMCE(
            attrs={'cols': 80, 'rows': 44, },
            mce_attrs={
                'height': 900,
                'toolbar': 'undo redo | bold italic | alignleft aligncenter alignright alignjustify | outdent indent',
                'menubar': False,
                'contextmenu': False,
            }
        ),
        validators=[
            validate_evolucao_texto,
        ],
    )

    class Meta:
        model = Evolucao
        exclude = ('dt_registro', 'dt_atualizacao',
                   'us_registro', 'us_atualizacao', 'estabelecimento',)
        widgets = {
            'atendimento': forms.HiddenInput(),  # Campo atendimento como input oculto
            # Campo evolucao com atributos personalizados
        }


class PsicoterapiaCreateForm(FilterByStatusMixin, forms.ModelForm):

    psicoterapia = forms.CharField(
        widget=TinyMCE(
            attrs={'cols': 80, 'rows': 44, },
            mce_attrs={'height': 900,
                       'toolbar': 'undo redo | bold italic | alignleft aligncenter alignright alignjustify | outdent indent',
                       'menubar': False,
                       'contextmenu': False}),
        # Adiciona o validador de tamanho máximo aqui
        validators=[MaxLengthValidator(20000)]
    )

    class Meta:
        model = Psicoterapia
        # Liste aqui todos os campos necessários para a evolução, exceto 'atendimento'
        exclude = ['pessoa', 'atendimento', 'created_by',
                   'estabelecimento', 'us_registro', 'dt_registro', 'dt_atualizacao', 'us_atualizacao',]

        widgets = {
            'atendimento': HiddenInput(),
            'status': HiddenInput(),
        }

    def __init__(self, *args, **kwargs):

        atendimento = kwargs.pop('atendimento', None)
        user = kwargs.pop('user', None)
        estabelecimento = kwargs.pop('estabelecimento', None)
        status = 'A'

        super().__init__(*args, **kwargs)

        self.instance.created_by = user

        if not self.instance.pk:
            self.fields['status'].widget.attrs['style'] = 'display:none;'

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Atribui o usuário que está criando a psicoterapia
        if commit:
            instance.save()
        return instance


class PsicoterapiaDetailForm(forms.ModelForm):

    psicoterapia = forms.CharField(
        widget=TinyMCE(
            attrs={'cols': 80, 'rows': 44, },
            mce_attrs={
                'height': 900,
                'toolbar': 'undo redo | bold italic | alignleft aligncenter alignright alignjustify | outdent indent',
                'menubar': False,
                'contextmenu': False,
            }
        )
    )

    class Meta:
        model = Psicoterapia
        exclude = ('pessoa', 'atendimento')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields:
            self.fields[field].widget.attrs['disabled'] = True


class PsicoterapiaUpdateForm(forms.ModelForm):

    psicoterapia = forms.CharField(
        widget=TinyMCE(
            attrs={'cols': 80, 'rows': 44, },
            mce_attrs={
                'height': 900,
                'toolbar': 'undo redo | bold italic | alignleft aligncenter alignright alignjustify | outdent indent',
                'menubar': False,
                'contextmenu': False,
            }
        ),
        # Adiciona o validador de tamanho máximo aqui
        validators=[MaxLengthValidator(20000)]
    )

    class Meta:
        model = Psicoterapia
        exclude = ('dt_registro', 'dt_atualizacao',
                   'us_registro', 'us_atualizacao', 'estabelecimento',)

    def __init__(self, *args, **kwargs):
        super(PsicoterapiaUpdateForm, self).__init__(*args, **kwargs)
        # Desabilita a edição do campo atendimento
        self.fields['atendimento'].disabled = True
        # Renderiza como um campo oculto
        self.fields['atendimento'].widget = forms.HiddenInput()
        self.user = kwargs.pop('user', None)

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Atribui o usuário que está criando a evolução
        # instance.created_by = self.initial.get('user')

        if commit:
            instance.save()
        return instance


class SinaisVitaisCreateForm(FilterByStatusMixin, forms.ModelForm):
    class Meta:
        model = SinaisVitais
        exclude = ['pessoa', 'atendimento', 'created_by',
                   'estabelecimento', 'us_registro', 'dt_registro', 'dt_atualizacao', 'us_atualizacao', ]

        widgets = {
            'atendimento': HiddenInput(),
            'temperatura': forms.NumberInput(attrs={'placeholder': 'Graus Celsius (ex: 36.5)'}),
            'pressao_arterial': forms.TextInput(attrs={'placeholder': 'Pressão arterial (ex: 120/80)'}),
            'frequencia_cardiaca': forms.NumberInput(attrs={'placeholder': 'Batimentos por minuto (ex: 60)'}),
            'frequencia_respiratoria': forms.NumberInput(attrs={'placeholder': 'Respirações por minuto (ex: 12)'}),
            'saturacao_oxigenio': forms.NumberInput(attrs={'placeholder': 'Porcentagem (ex: 98)'}),
            'controle_glicemia': forms.NumberInput(attrs={'placeholder': 'mg/dL (ex: 120)'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.atendimento = kwargs.pop('atendimento', None)
        self.estabelecimento = kwargs.pop(
            'estabelecimento', None)  # Adicionando esta linha
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.instance.created_by = self.user

        if not self.instance.pk:
            self.fields['status'].widget.attrs['style'] = 'display:none;'

    def clean(self):
        cleaned_data = super().clean()
        pressao_arterial = cleaned_data.get('pressao_arterial')

        # Verifica se pelo menos um dos campos é preenchido
        if not any(cleaned_data.get(field) for field in [
            'temperatura',
            'pressao_arterial',
            'frequencia_cardiaca',
            'frequencia_respiratoria',
            'saturacao_oxigenio',
            'controle_glicemia'
        ]):
            raise forms.ValidationError(
                "Pelo menos um dos campos deve ser preenchido.")

        # Verificador de pressão arterial
        if pressao_arterial:
            partes = pressao_arterial.split('/')
            if len(partes) != 2 or not partes[0].isdigit() or not partes[1].isdigit():
                self.add_error(
                    'pressao_arterial', 'Pressão arterial deve conter um número antes e depois da barra. Ex: 120/80')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Atribui o usuário que está criando SV
        instance.created_by = self.initial.get('user')

        if commit:
            instance.save()
        return instance


class SinaisVitaisDetailForm(forms.ModelForm):

    class Meta:
        model = SinaisVitais
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields:
            self.fields[field].widget.attrs['disabled'] = True


class SinaisVitaisUpdateForm(forms.ModelForm):
    class Meta:
        model = SinaisVitais
        exclude = ('dt_registro', 'dt_atualizacao',
                   'us_registro', 'us_atualizacao', 'estabelecimento')
        widgets = {
            'atendimento': forms.HiddenInput(),
            'temperatura': forms.NumberInput(attrs={'placeholder': 'Graus Celsius (ex: 36.5)'}),
            'pressao_arterial': forms.TextInput(attrs={'placeholder': 'Pressão arterial (ex: 120/80)'}),
            'frequencia_cardiaca': forms.NumberInput(attrs={'placeholder': 'Batimentos por minuto (ex: 60)'}),
            'frequencia_respiratoria': forms.NumberInput(attrs={'placeholder': 'Respirações por minuto (ex: 12)'}),
            'saturacao_oxigenio': forms.NumberInput(attrs={'placeholder': 'Porcentagem (ex: 98)'}),
            'controle_glicemia': forms.NumberInput(attrs={'placeholder': 'mg/dL (ex: 120)'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.atendimento = kwargs.pop('atendimento', None)
        self.estabelecimento = kwargs.pop('estabelecimento', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.instance.created_by = self.user

    def clean(self):
        cleaned_data = super().clean()
        pressao_arterial = cleaned_data.get('pressao_arterial')

        # Verifica se pelo menos um dos campos é preenchido
        if not any(cleaned_data.get(field) for field in [
            'temperatura',
            'pressao_arterial',
            'frequencia_cardiaca',
            'frequencia_respiratoria',
            'saturacao_oxigenio',
            'controle_glicemia'
        ]):
            raise forms.ValidationError(
                "Pelo menos um dos campos deve ser preenchido.")

        # Verificador de pressão arterial
        if pressao_arterial:
            partes = pressao_arterial.split('/')
            if len(partes) != 2 or not partes[0].isdigit() or not partes[1].isdigit():
                self.add_error(
                    'pressao_arterial', 'Pressão arterial deve conter um número antes e depois da barra. Ex: 120/80')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Atribui o usuário que está criando SV
        instance.created_by = self.initial.get('user')

        if commit:
            instance.save()
        return instance


class SinaisVitaisListForm(FilterByStatusMixin, forms.ModelForm):
    class Meta:
        model = SinaisVitais
        fields = '__all__'


class PerdasGanhosCreateForm(FilterByStatusMixin, forms.ModelForm):
    class Meta:
        model = PerdasGanhos
        exclude = ['atendimento', 'created_by',
                   'estabelecimento', 'us_registro', 'dt_registro', 'dt_atualizacao', 'us_atualizacao', ]

        widgets = {
            'atendimento': HiddenInput(),
            'altura': forms.NumberInput(attrs={'placeholder': 'Altura em CM (ex: 180)'}),
            'peso': forms.NumberInput(attrs={'placeholder': 'Peso em kg (ex: 70)'}),
        }

    def __init__(self, *args, **kwargs):

        self.request = kwargs.pop('request', None)
        atendimento = kwargs.pop('atendimento', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.instance.created_by = user

        if not self.instance.pk:
            self.fields['status'].widget.attrs['style'] = 'display:none;'

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Atribui o usuário que está criando SV
        instance.created_by = self.initial.get('user')

        if commit:
            instance.save()
        return instance


class PerdasGanhosDetailForm(forms.ModelForm):

    class Meta:
        model = PerdasGanhos
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields:
            self.fields[field].widget.attrs['disabled'] = True


class PerdasGanhosUpdateForm(forms.ModelForm):
    class Meta:
        model = PerdasGanhos
        exclude = ('dt_registro', 'dt_atualizacao',
                   'us_registro', 'us_atualizacao', 'estabelecimento')
        widgets = {
            'atendimento': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        atendimento = kwargs.pop('atendimento', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.instance.created_by = user

        if not self.instance.pk:
            self.fields['status'].widget.attrs['style'] = 'display:none;'

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Atribui o usuário que está criando SV
        instance.created_by = self.initial.get('user')

        if commit:
            instance.save()
        return instance


class PlanoCuidadosCreateForm(FilterByStatusMixin, forms.ModelForm):
    class Meta:
        model = PlanoCuidados
        exclude = ['atendimento', 'created_by',
                   'estabelecimento', 'us_registro', 'dt_registro', 'dt_atualizacao', 'us_atualizacao']

        widgets = {
            'atendimento': HiddenInput(),
            'status': HiddenInput(),
        }

    def __init__(self, *args, **kwargs):

        self.request = kwargs.pop('request', None)
        atendimento = kwargs.pop('atendimento', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.instance.created_by = user

        if not self.instance.pk:
            self.fields['status'].widget.attrs['style'] = 'display:none;'

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Atribui o usuário que está criando SV
        instance.created_by = self.initial.get('user')

        if commit:
            instance.save()
        return instance


class PlanoCuidadosDetailForm(forms.ModelForm):

    class Meta:
        model = PlanoCuidados
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields:
            self.fields[field].widget.attrs['disabled'] = True


class PlanoCuidadosUpdateForm(forms.ModelForm):
    class Meta:
        model = PlanoCuidados
        exclude = ('dt_registro', 'dt_atualizacao',
                   'us_registro', 'us_atualizacao', 'estabelecimento')
        widgets = {
            'atendimento': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        atendimento = kwargs.pop('atendimento', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.instance.created_by = user

        if not self.instance.pk:
            self.fields['status'].widget.attrs['style'] = 'display:none;'

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Atribui o usuário que está criando SV
        instance.created_by = self.initial.get('user')

        if commit:
            instance.save()
        return instance


class SAECreateForm(FilterByStatusMixin, forms.ModelForm):
    class Meta:
        model = SAE
        exclude = ['atendimento', 'created_by',
                   'estabelecimento', 'us_registro', 'dt_registro', 'dt_atualizacao', 'us_atualizacao',]

        widgets = {
            'atendimento': HiddenInput(),
            'status': HiddenInput(),
        }

    def __init__(self, *args, **kwargs):

        self.request = kwargs.pop('request', None)
        atendimento = kwargs.pop('atendimento', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.instance.created_by = user

        if not self.instance.pk:
            self.fields['status'].widget.attrs['style'] = 'display:none;'

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Atribui o usuário que está criando SV
        instance.created_by = self.initial.get('user')

        if commit:
            instance.save()
        return instance


class SAEDetailForm(forms.ModelForm):

    class Meta:
        model = SAE
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields:
            self.fields[field].widget.attrs['disabled'] = True


class SAEUpdateForm(forms.ModelForm):
    class Meta:
        model = SAE
        fields = ['us_registro', 'aspecto', 'aspecto_analisado', 'evidencia', 'diagnostico_enfermagem',
                  'fator_relacionado', 'intervencao', 'anotacao', 'status', 'atendimento', 'estabelecimento',]
        widgets = {
            'atendimento': forms.HiddenInput(),
            'estabelecimento': forms.HiddenInput(),
            'us_registro': forms.TextInput(attrs={'readonly': 'readonly'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        atendimento = kwargs.pop('atendimento', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.instance.created_by = user

        if not self.instance.pk:
            self.fields['status'].widget.attrs['style'] = 'display:none;'

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Atribui o usuário que está criando SV
        instance.created_by = self.initial.get('user')

        if commit:
            instance.save()
        return instance

#######################################################################


class ProdutoPrescricaoForm(FilterByStatusMixin, forms.ModelForm):
    class Meta:
        model = ProdutoPrescricao
        fields = [
            'produto',
            'intervalo_horas',
            'dt_inicio',
            'hora_inicio_produto',
            'dt_final',
            'se_necessario',
            'dose_unica',
            'observacao',
            'status',
        ]
        widgets = {
            'dt_inicio': forms.HiddenInput(),
            'status': forms.HiddenInput(),
            'dt_final': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.estabelecimento_id = None
        if self.request and hasattr(self.request, 'session'):
            self.estabelecimento_id = self.request.session.get(
                'estabelecimento_id')
        atendimento = kwargs.pop('atendimento', None)
        self.user = kwargs.pop('user', None)
        super(ProdutoPrescricaoForm, self).__init__(*args, **kwargs)
        # Define o queryset para o campo 'produto'
        pode_ser_prescrito_qs = Produto.objects.filter(
            pode_ser_prescrito=True, status='A')
        grupo_pode_ser_prescrito_qs = Produto.objects.filter(
            grupo__pode_ser_prescrito=True, status='A')
        self.fields['produto'].queryset = pode_ser_prescrito_qs | grupo_pode_ser_prescrito_qs
        # Inicializa o campo 'intervalo_horas' com o valor padrão, se existir
        default_intervalo = IntervaloHoras.objects.filter(
            padrao=True, status='A').first()
        if default_intervalo:
            self.fields['intervalo_horas'].initial = default_intervalo
        # Inicializa o campo 'hora_inicio_produto' com o padrão do plano, igual à prescrição,
        # permitindo que o usuário altere manualmente, se necessário.
        default_inicio = InicioPlanoTerapeutico.objects.filter(
            padrao=True, status='A').first()
        if default_inicio:
            self.fields['hora_inicio_produto'].initial = default_inicio

    def clean(self):
        cleaned_data = super().clean()

        dt_inicio = cleaned_data.get('dt_inicio')
        hora_inicio_produto = cleaned_data.get('hora_inicio_produto')
        dt_final = cleaned_data.get('dt_final')
        us_registro = self.user

        us_profissao = CadastroProfissional.objects.filter(
            profissional=us_registro, status='A').first()
        estab = self.estabelecimento_id

        if us_profissao:
            usuario_liberado = ParametrosPrescricao.objects.filter(
                Q(profissional=us_registro, estabelecimento_id=estab, status='A') |
                Q(profissao=us_profissao.profissao,
                  estabelecimento_id=estab, status='A')
            ).first()

            retroativo = usuario_liberado.permite_prescricao_retroativa if usuario_liberado else False
            dias = usuario_liberado.dias if usuario_liberado else None

            if usuario_liberado:
                if dt_inicio and hora_inicio_produto:
                    dt_hora_inicio = datetime.combine(
                        dt_inicio, hora_inicio_produto.hora_inicio)

                # 🔹 Verifica se a hora de início do produto é menor que a hora atual
                    if make_aware(dt_hora_inicio) < timezone.now():
                        if retroativo:
                            return cleaned_data
                        else:
                            raise ValidationError(
                                f'Os campos de data e hora não podem ser menores que a data e hora atual')
                            return messages.error(self, 'Erro')

                    # Verifica a diferença de dias entre dt_inicio e dt_final
                        if dias:
                            diferenca = (
                                dt_final - make_aware(dt_hora_inicio)).days

                            if diferenca:
                                # Bloqueia se dt_final for menor que dt_inicio
                                if dt_final < make_aware(dt_hora_inicio):
                                    raise ValidationError(
                                        'A data final não pode ser menor que a inicial.')
                                    return messages.error(self, 'Erro')

                                # Bloqueia se a diferença for maior que os dias permitidos
                                if diferenca > dias:
                                    raise ValidationError(
                                        f'A data final não pode ser superior a {dias} dias, conforme definido no parâmetro')
                                    return messages.error(self, 'Erro')

            else:
                raise ValidationError('Profissional sem permissão!')
                return messages.error(self, 'Erro')

        return cleaned_data

    def clean_hora_inicio_produto(self):
        # Recupera o valor do campo 'hora_inicio_produto' (FK para InicioPlanoTerapeutico)
        hora_inicio_produto = self.cleaned_data.get('hora_inicio_produto')
        try:
            # Tenta obter a prescrição associada (também FK para InicioPlanoTerapeutico)
            prescricao = self.instance.prescricao
        except ObjectDoesNotExist:
            prescricao = None

        # Se houver prescrição, compara os valores do campo 'hora_inicio'
        # Presume-se que o modelo InicioPlanoTerapeutico possua o campo 'hora_inicio'
        if prescricao and hora_inicio_produto.hora_inicio < prescricao.hora_inicio.hora_inicio:
            # Adiciona mensagem de erro ao campo sem lançar exceção
            self.add_error(
                'hora_inicio_produto', "A hora de início do produto não pode ser menor que a hora de início da prescrição.")
        return hora_inicio_produto

    def save(self, commit=True):
        instance = super(ProdutoPrescricaoForm, self).save(commit=False)

        try:
            presc_date = instance.prescricao.dt_inicio
            intervalo = instance.intervalo_horas.intervalo_horas if instance.intervalo_horas else 24
        except ObjectDoesNotExist:
            presc_date = None
            intervalo = 24
            if self.request:
                messages.warning(
                    self.request, 'Não foi possível definir dt_inicio por falta de prescrição.')

        if presc_date:
            if instance.pk is None:  # Primeiro dia, aplica hora_inicio_produto
                dt_hora_inicio = datetime.combine(
                    presc_date, self.cleaned_data['hora_inicio_produto'].hora_inicio)
                dt_hora_inicio = make_aware(dt_hora_inicio)
                instance.dt_inicio = dt_hora_inicio
            else:
                # Para os dias seguintes, usa o intervalo para definir a nova data/hora
                instance.dt_inicio = instance.dt_inicio + \
                    timedelta(hours=intervalo)

        if commit:
            instance.save()
        return instance


class ProdutoPrescricaoUpForm(FilterByStatusMixin, forms.ModelForm):
    class Meta:
        model = ProdutoPrescricao
        fields = [
            'produto',
            'intervalo_horas',
            'dt_inicio',
            'hora_inicio_produto',
            'dt_final',
            'se_necessario',
            'dose_unica',
            'observacao',
            'status',
        ]
        widgets = {
            'dt_inicio': forms.HiddenInput(),
            'status': forms.HiddenInput(),
            'dt_final': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.estabelecimento_id = None
        if self.request and hasattr(self.request, 'session'):
            self.estabelecimento_id = self.request.session.get(
                'estabelecimento_id')
        atendimento = kwargs.pop('atendimento', None)
        self.user = kwargs.pop('user', None)
        super(ProdutoPrescricaoUpForm, self).__init__(*args, **kwargs)
        # Define o queryset para o campo 'produto'
        pode_ser_prescrito_qs = Produto.objects.filter(
            pode_ser_prescrito=True, status='A')
        grupo_pode_ser_prescrito_qs = Produto.objects.filter(
            grupo__pode_ser_prescrito=True, status='A')
        self.fields['produto'].queryset = pode_ser_prescrito_qs | grupo_pode_ser_prescrito_qs
        # Inicializa o campo 'intervalo_horas' com o valor padrão, se existir
        default_intervalo = IntervaloHoras.objects.filter(
            padrao=True, status='A').first()
        if default_intervalo:
            self.fields['intervalo_horas'].initial = default_intervalo
        # Inicializa o campo 'hora_inicio_produto' com o padrão do plano, igual à prescrição,
        # permitindo que o usuário altere manualmente, se necessário.
        default_inicio = InicioPlanoTerapeutico.objects.filter(
            padrao=True, status='A').first()
        if default_inicio:
            self.fields['hora_inicio_produto'].initial = default_inicio

    def clean(self):
        cleaned_data = super().clean()

        dt_inicio = cleaned_data.get('dt_inicio')
        hora_inicio_produto = cleaned_data.get('hora_inicio_produto')
        dt_final = cleaned_data.get('dt_final')
        us_registro = self.user

        us_profissao = CadastroProfissional.objects.filter(
            profissional=us_registro, status='A').first()
        estab = self.estabelecimento_id

        if us_profissao:
            usuario_liberado = ParametrosPrescricao.objects.filter(
                Q(profissional=us_registro, estabelecimento_id=estab, status='A') |
                Q(profissao=us_profissao.profissao,
                  estabelecimento_id=estab, status='A')
            ).first()

            retroativo = usuario_liberado.permite_prescricao_retroativa if usuario_liberado else False
            dias = usuario_liberado.dias if usuario_liberado else None

            if usuario_liberado:
                if dt_inicio and hora_inicio_produto:
                    dt_hora_inicio = datetime.combine(
                        dt_inicio, hora_inicio_produto.hora_inicio)

                # 🔹 Verifica se a hora de início do produto é menor que a hora atual
                    if make_aware(dt_hora_inicio) < timezone.now():
                        if retroativo:
                            return cleaned_data
                        else:
                            raise ValidationError(
                                f'Os campos de data e hora não podem ser menores que a data e hora atual')
                            return messages.error(self, 'Erro')

                    # Verifica a diferença de dias entre dt_inicio e dt_final
                        if dias:
                            diferenca = (
                                dt_final - make_aware(dt_hora_inicio)).days

                            if diferenca:
                                # Bloqueia se dt_final for menor que dt_inicio
                                if dt_final < make_aware(dt_hora_inicio):
                                    raise ValidationError(
                                        'A data final não pode ser menor que a inicial.')
                                    return messages.error(self, 'Erro')

                                # Bloqueia se a diferença for maior que os dias permitidos
                                if diferenca > dias:
                                    raise ValidationError(
                                        f'A data final não pode ser superior a {dias} dias, conforme definido no parâmetro')
                                    return messages.error(self, 'Erro')

            else:
                raise ValidationError('Profissional sem permissão!')
                return messages.error(self, 'Erro')

        return cleaned_data

    def clean_hora_inicio_produto(self):
        # Recupera o valor do campo 'hora_inicio_produto' (FK para InicioPlanoTerapeutico)
        hora_inicio_produto = self.cleaned_data.get('hora_inicio_produto')
        try:
            # Tenta obter a prescrição associada (também FK para InicioPlanoTerapeutico)
            prescricao = self.instance.prescricao
        except ObjectDoesNotExist:
            prescricao = None

        # Se houver prescrição, compara os valores do campo 'hora_inicio'
        # Presume-se que o modelo InicioPlanoTerapeutico possua o campo 'hora_inicio'
        if prescricao and hora_inicio_produto.hora_inicio < prescricao.hora_inicio.hora_inicio:
            # Adiciona mensagem de erro ao campo sem lançar exceção
            self.add_error(
                'hora_inicio_produto', "A hora de início do produto não pode ser menor que a hora de início da prescrição.")
        return hora_inicio_produto

    def save(self, commit=True):
        instance = super(ProdutoPrescricaoUpForm, self).save(commit=False)

        try:
            presc_date = instance.prescricao.dt_inicio
            intervalo = instance.intervalo_horas.intervalo_horas if instance.intervalo_horas else 24
        except ObjectDoesNotExist:
            presc_date = None
            intervalo = 24
            if self.request:
                messages.warning(
                    self.request, 'Não foi possível definir dt_inicio por falta de prescrição.')

        if presc_date:
            if instance.pk is None:  # Primeiro dia, aplica hora_inicio_produto
                dt_hora_inicio = datetime.combine(
                    presc_date, self.cleaned_data['hora_inicio_produto'].hora_inicio)
                dt_hora_inicio = make_aware(dt_hora_inicio)
                instance.dt_inicio = dt_hora_inicio
            else:
                # Para os dias seguintes, usa o intervalo para definir a nova data/hora
                instance.dt_inicio = instance.dt_inicio + \
                    timedelta(hours=intervalo)

        if commit:
            instance.save()
        return instance


###########################################################################


class AdepForm(forms.ModelForm):
    class Meta:
        model = Adep
        fields = '__all__'


# Inicio prescricao


class PrescricaoForm(forms.ModelForm):
    class Meta:
        model = Prescricao
        exclude = [
            'created_by', 'prescricao_anterior', 'dt_suspensao', 'us_suspensao',
            'us_registro', 'us_prescricao_inicial', 'dt_registro', 'dt_atualizacao',
            'us_atualizacao'
        ]
        widgets = {
            'atendimento': forms.HiddenInput(),
            'status': forms.HiddenInput(),
            'fase': forms.HiddenInput(),
            'relatorio': forms.HiddenInput(),
            'estabelecimento': forms.HiddenInput(),
            'prescricao_anterior': forms.HiddenInput(),
            'dt_inicio': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'},
                format='%Y-%m-%dT%H:%M'
            ),
            'dt_final': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'},
                format='%Y-%m-%dT%H:%M'
            ),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.estabelecimento_id = None
        if self.request and hasattr(self.request, 'session'):
            self.estabelecimento_id = self.request.session.get(
                'estabelecimento_id')

        self.user = kwargs.pop('user', None)
        self.atendimento = kwargs.pop('atendimento', None)

        super().__init__(*args, **kwargs)

        self.instance.created_by = self.user
        self.instance.atendimento = self.atendimento

        # Para novo registro, define valores padrão
        if not self.instance.pk:
            self.fields['status'].widget.attrs['style'] = 'display:none;'
            if not self.initial.get('dt_inicio'):
                hoje_meia_noite = localtime(now()).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                # Garante que seja timezone-aware e converte para UTC-3
                if is_naive(hoje_meia_noite):
                    hoje_meia_noite = make_aware(
                        hoje_meia_noite, timezone=get_current_timezone())
                self.fields['dt_inicio'].initial = hoje_meia_noite
                self.instance.dt_inicio = hoje_meia_noite

        # Atualiza `dt_final` com um valor padrão baseado em `dt_inicio`
        if self.instance.dt_inicio:
            next_day = self.instance.dt_inicio + timedelta(days=1)
            dt_final_default = next_day.replace(
                hour=23, minute=59, second=59, microsecond=0)
            self.fields['dt_final'].initial = dt_final_default

    def clean(self):
        cleaned_data = super().clean()
        dt_inicio = cleaned_data.get('dt_inicio')
        dt_final = cleaned_data.get('dt_final')

        if dt_inicio and is_naive(dt_inicio):
            dt_inicio = make_aware(dt_inicio, timezone=get_current_timezone())
        cleaned_data['dt_inicio'] = dt_inicio

        # 🚨 Busca parâmetros para verificar permissões
        profissional = CadastroProfissional.objects.filter(
            profissional=self.user, status='A').first()
        if not profissional:
            raise ValidationError(
                "Ação não permitida, verifique parâmetros da prescrição!.")

        parametros = ParametrosPrescricao.objects.filter(
            Q(profissional=self.user, estabelecimento=self.estabelecimento_id, status='A') |
            Q(profissao=profissional.profissao,
              estabelecimento=self.estabelecimento_id, status='A')
        ).first()

        if not parametros:
            raise ValidationError("Parâmetros da prescrição não encontrados.")

        # 🚨 BLOQUEIO DE PRESCRIÇÃO RETROATIVA
        if dt_inicio and dt_inicio < now():
            if not parametros.permite_prescricao_retroativa:
                raise ValidationError(
                    "Não é permitido prescrição com data retroativa.")

        # 🚨 VALIDAÇÃO DE `DT_FINAL`
        if dt_inicio and dt_final:
            # Verifica se `dt_final` é menor que `dt_inicio`
            if dt_final < dt_inicio:
                raise ValidationError(
                    "A data final não pode ser menor que a data de início.")

            # Limite máximo permitido baseado no campo 'dias' do parâmetro
            limite_dt_final = dt_inicio + timedelta(days=parametros.dias)
            if dt_final > limite_dt_final:
                raise ValidationError(
                    f"Data final não pode ser superior a {parametros.dias} dia(s) a partir da Data de Início."
                )

        return cleaned_data


# fim prescricao


# inicio diagnostico


class DiagnosticoCreateForm(FilterByStatusMixin, forms.ModelForm):

    class Meta:
        model = Diagnostico
        # Liste aqui todos os campos necessários para a evolução, exceto 'atendimento'
        exclude = ['pessoa', 'atendimento', 'created_by',
                   'estabelecimento', 'us_registro', 'dt_registro', 'dt_atualizacao', 'us_atualizacao']

        widgets = {
            'atendimento': HiddenInput(),
            'status': HiddenInput(),
        }

    def __init__(self, *args, **kwargs):

        atendimento = kwargs.pop('atendimento', None)
        user = kwargs.pop('user', None)
        estabelecimento = kwargs.pop('estabelecimento', None)

        super().__init__(*args, **kwargs)

        self.instance.created_by = user

        self.fields['diagnostico'] = forms.ModelMultipleChoiceField(
            queryset=CID.objects.all(),
            widget=Select2MultipleWidget(attrs={'data-width': '100%'}),
            required=False,
            label='CID - Diagnósticos dos encaminhamentos'
        )

        if not self.instance.pk:
            self.fields['status'].widget.attrs['style'] = 'display:none;'

    def clean_diagnostico(self):
        diagnostico = self.cleaned_data.get('diagnostico')
        if diagnostico and len(diagnostico) > 20:
            raise forms.ValidationError(
                "Você não pode selecionar mais de 20 diagnósticos.")
        if not diagnostico:
            raise ValidationError('Este campo é obrigatório.')
        return diagnostico

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Atribui o usuário que está criando a evolução
        instance.created_by = self.initial.get('user')

        if commit:
            instance.save()
        return instance


class DiagnosticoDetailForm(forms.ModelForm):

    class Meta:
        model = Diagnostico
        exclude = ('atendimento',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields:
            self.fields[field].widget.attrs['disabled'] = True


class DiagnosticoUpdateForm(forms.ModelForm):

    class Meta:
        model = Diagnostico
        exclude = ('dt_registro', 'dt_atualizacao',
                   'us_registro', 'us_atualizacao', 'estabelecimento',)
        widgets = {
            'atendimento': forms.HiddenInput(),  # Campo atendimento como input oculto
            # Campo evolucao com atributos personalizados
        }

    def __init__(self, *args, **kwargs):
        super(DiagnosticoUpdateForm, self).__init__(*args, **kwargs)
        # Desabilita a edição do campo atendimento
        self.fields['atendimento'].disabled = True
        # Renderiza como um campo oculto
        self.fields['atendimento'].widget = forms.HiddenInput()
        self.user = kwargs.pop('user', None)
        self.fields['diagnostico'] = forms.ModelMultipleChoiceField(
            queryset=CID.objects.all(),
            required=False,
            label='CID - Diagnósticos dos encaminhamentos',
            widget=Select2MultipleWidget(attrs={'data-width': '100%'})
        )

    def clean_diagnostico(self):
        diagnostico = self.cleaned_data.get('diagnostico')
        if diagnostico and len(diagnostico) > 20:
            raise forms.ValidationError(
                "Você não pode selecionar mais de 20 diagnósticos.")
        if not diagnostico:
            raise ValidationError('Este campo é obrigatório.')
        return diagnostico

# fim diagnostico


### INICIO PASSAGEM PLANTAO ####


class PassagemPlantaoCreateForm(FilterByStatusMixin, forms.ModelForm):
    passagem_plantao = forms.CharField(
        widget=TinyMCE(
            # Esses valores são apenas exemplos e podem ser ajustados conforme necessário
            attrs={'cols': 80, 'rows': 44},
            mce_attrs={
                'height': 900,  # Define a altura do editor TinyMCE para 700px
                'toolbar': 'undo redo | bold italic | alignleft aligncenter alignright alignjustify | outdent indent',
                'menubar': False,
                'contextmenu': False,
            }
        ),
        # Adiciona o validador de tamanho máximo aqui
        validators=[MaxLengthValidator(25000)]
    )

    class Meta:
        model = PassagemPlantao
        # Liste aqui todos os campos necessários para a evolução, exceto 'atendimento'
        exclude = ['created_by', 'estabelecimento', 'us_registro',
                   'dt_registro', 'dt_atualizacao', 'us_atualizacao', ]

        widgets = {
            'atendimento': HiddenInput(),
            'status': HiddenInput(),
        }

    def __init__(self, *args, **kwargs):

        user = kwargs.pop('user', None)
        estabelecimento = kwargs.pop('estabelecimento', None)
        status = 'A'

        super().__init__(*args, **kwargs)

        self.instance.created_by = user

        if not self.instance.pk:
            self.fields['status'].widget.attrs['style'] = 'display:none;'

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Atribui o usuário que está criando a evolução

        if commit:
            instance.save()
        return instance


class PassagemPlantaoDetailForm(forms.ModelForm):
    passagem_plantao = forms.CharField(
        widget=TinyMCE(
            # Esses valores são apenas exemplos e podem ser ajustados conforme necessário
            attrs={'cols': 80, 'rows': 44},
            mce_attrs={
                'height': 900,  # Define a altura do editor TinyMCE para 700px
                'toolbar': 'undo redo | bold italic | alignleft aligncenter alignright alignjustify | outdent indent',
                'menubar': False,
                'contextmenu': False,
            }
        )
    )

    class Meta:
        model = PassagemPlantao
        fields = '__all__'

    def __init__(self, *args, **kwargs):

        super(PassagemPlantaoDetailForm, self).__init__(*args, **kwargs)

        for field in self.fields:
            self.fields[field].widget.attrs['disabled'] = True


### FIM PASSAGEM PLANTAO ###
