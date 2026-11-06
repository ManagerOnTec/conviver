from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms
from django.contrib.auth.models import User
from .models import Perfil
from admin_cadastros.models import Pessoa, Estabelecimento
from django.contrib.admin.widgets import FilteredSelectMultiple
from unidecode import unidecode
from django.contrib.admin.widgets import AutocompleteSelect
from django.urls import reverse
from django.contrib import admin
from dominios.utils import HiddenPasswordInput


class PerfilForm(forms.ModelForm):
    senha_certificado = forms.CharField(
        widget=forms.PasswordInput(), required=False)

    estabelecimento = forms.ModelMultipleChoiceField(
        queryset=Estabelecimento.objects.filter(status='A'),
        widget=FilteredSelectMultiple('Estabelecimento', is_stacked=False)
    )

    class Meta:
        model = Perfil
        fields = ('pessoa', 'estabelecimento', 'estabelecimento_padrao',
                  'dt_admissao', 'dt_desligamento', 'certificado_digital', 'validade_certificado', 'senha_certificado')

    def clean_certificado_digital(self):
        certificado = self.cleaned_data.get('certificado_digital')
        if certificado:
            extensao = certificado.name.rsplit('.', 1)[-1].lower()
            if extensao != 'pfx':
                raise forms.ValidationError(
                    "Apenas arquivos .pfx são aceitos para o certificado digital.")
        return certificado

    def clean(self):
        cleaned_data = super().clean()
        estabelecimento_padrao = cleaned_data.get('estabelecimento_padrao')
        estabelecimentos_liberados = cleaned_data.get('estabelecimento', None)

        # Validação: O estabelecimento_padrao deve estar entre os estabelecimentos liberados
        if estabelecimento_padrao and estabelecimentos_liberados:
            if estabelecimento_padrao not in estabelecimentos_liberados:
                raise forms.ValidationError(
                    "O estabelecimento padrão selecionado deve estar entre os estabelecimentos liberados."
                )

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Limita apenas pessoas com classificação FUNCIONARIO
        self.fields['pessoa'].queryset = Pessoa.objects.filter(
            classificacao_pessoa='funcionario', status='A'
        )

        if self.instance.pk:
            self.fields['dt_desligamento'].widget.attrs['readonly'] = True
            self.fields['senha_certificado'].widget = forms.PasswordInput(
                render_value=True
            )
            self.fields['senha_certificado'].initial = "********"

    def clean_pessoa(self):
        pessoa = self.cleaned_data.get('pessoa')

        # Defesa adicional à filtragem do queryset: mantém a instância Pessoa
        # validada no campo e rejeita qualquer classificação diferente.
        if pessoa and pessoa.classificacao_pessoa != 'funcionario':
            raise ValidationError(
                "A pessoa vinculada ao perfil deve ser da classificação FUNCIONÁRIO."
            )

        return pessoa



class CustomUserCreationForm(UserCreationForm):

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        default_password = "abc123++"  # Substitua pela senha padrão desejada
        self.fields['email'].required = True
        self.fields['password1'].widget.attrs.update({
            'value': default_password,
            'readonly': True
        })
        self.fields['password2'].widget.attrs.update({
            'value': default_password,
            'readonly': True
        })

    def clean_username(self):
        username = self.cleaned_data['username']
        username = unidecode(username.lower())
        return username

    def clean(self):
        super().clean()
        if 'groups' in self.cleaned_data and len(self.cleaned_data['groups']) == 0:
            self.add_error(
                'groups', 'Pelo menos um grupo deve ser selecionado.')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Email já existe.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        default_password = "abc123++"  # Substitua pela senha padrão desejada
        user.set_password(default_password)
        if commit:
            user.save()
        return user  # Adicione esta linha


class CustomUserChangeForm(UserChangeForm):

    class Meta:
        model = User
        fields = ('username', 'email',)

    def clean_username(self):
        username = self.cleaned_data['username']
        username = unidecode(username.lower())
        return username

# ----------------------------------------------------------------------------
# Widget "select + botão adicionar" para os FKs do Perfil no admin do Usuário.
# O RelatedFieldWidgetWrapper dependia de CSS que o tema do projeto escondia;
# aqui o "+" é desenhado pelo próprio template do widget, com a URL de popup
# do admin do modelo relacionado. O clique usa `showAddAnotherPopup`
# (RelatedObjectLookups.js do admin), que abre o popup e, ao salvar, atualiza
# o select automaticamente (mesmo mecanismo nativo do Django Admin).
# ----------------------------------------------------------------------------
class SelectComAdicionarMixin:
    """Calcula a URL de popup de cadastro do modelo relacionado."""

    def get_context(self, name, value, attrs):
        ctx = super().get_context(name, value, attrs)
        modelo = getattr(self, '_modelo_relacionado', None)
        if modelo is not None:
            meta = modelo._meta
            # variável PRÓPRIA do template (attrs com hífen não são acessíveis
            # via dot no template Django)
            ctx['widget']['add_url'] = reverse(
                'admin:%s_%s_add' % (meta.app_label, meta.model_name))
        return ctx


class SelectComAdicionar(SelectComAdicionarMixin, forms.Select):
    template_name = 'contas/widgets/select_add.html'


class SelectMultiploComAdicionar(SelectComAdicionarMixin, forms.SelectMultiple):
    template_name = 'contas/widgets/select_add.html'


def _aplicar_select_com_adicionar(form):
    """Troca o widget dos FKs do Perfil pelo select com botão “+”."""
    # Somente registros ATIVOS aparecem como opção (inativos saem da lista).
    qs_pessoa = Pessoa.objects.filter(
        classificacao_pessoa='funcionario', status='A')
    qs_estab = Estabelecimento.objects.filter(status='A')

    form.fields['pessoa'].queryset = qs_pessoa
    form.fields['estabelecimento_padrao'].queryset = qs_estab
    form.fields['estabelecimento'].queryset = qs_estab

    # ESTABELECIMENTO(S) e PADRÃO + PESSOA: MESMO PADRÃO DO CLIENTE EM
    # ACORDOFATURAMENTO — widgets nativos do admin (AutocompleteSelect*),
    # que o admin do Django inicializa sozinho (ordem correta de jQuery e
    # select2 garantida pelo admin), com digitação/busca e “+” do wrapper.
    from django.contrib import admin as djadmin
    from django.contrib.admin.widgets import (AutocompleteSelect,
                                              AutocompleteSelectMultiple,
                                              RelatedFieldWidgetWrapper)

    campo_estab = Perfil._meta.get_field('estabelecimento')
    campo_estab_padrao = Perfil._meta.get_field('estabelecimento_padrao')
    campo_pessoa = Perfil._meta.get_field('pessoa')

    # ATENÇÃO: o AutocompleteSelect* lê self.choices.field e
    # self.choices.queryset (ModelChoiceIterator do campo). Atribuir o widget
    # diretamente ao field o desconecta do iterator; por isso o widget é
    # criado a partir do FORMFIELD do campo (que já vem com iterator e
    # queryset “ só ativos”), e depois envolto no wrapper do “+”.
    def _autocomplete_com_mais(formfield, db_field):
        # O primeiro argumento do AutocompleteSelect é o CAMPO DE ORIGEM
        # (ManyToManyField/ForeignKey), não o remote_field. Se passar
        # remote_field, o HTML envia app_label=admin_cadastros,
        # model_name=estabelecimento, field_name=perfil; esse campo reverso
        # é um ManyToManyRel e o endpoint levanta AttributeError.
        widget = (AutocompleteSelectMultiple(db_field, djadmin.site)
                  if db_field.many_to_many
                  else AutocompleteSelect(db_field, djadmin.site))
        # Herda as choices do formfield (iterator/queryset ativo).
        widget.choices = formfield.choices
        return RelatedFieldWidgetWrapper(
            widget, db_field.remote_field, djadmin.site)

    form.fields['estabelecimento'].widget = _autocomplete_com_mais(
        form.fields['estabelecimento'], campo_estab)
    form.fields['estabelecimento_padrao'].widget = _autocomplete_com_mais(
        form.fields['estabelecimento_padrao'], campo_estab_padrao)
    form.fields['pessoa'].widget = _autocomplete_com_mais(
        form.fields['pessoa'], campo_pessoa)


class PerfilInlineForm(PerfilForm):
    """Form do inline: autocomplete nativo do admin + “+” nos FKs."""

    class Meta(PerfilForm.Meta):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _aplicar_select_com_adicionar(self)
