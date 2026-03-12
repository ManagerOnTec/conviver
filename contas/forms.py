from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms
from django.contrib.auth.models import User
from .models import Perfil
from admin_cadastros.models import Pessoa, Estabelecimento
from django.contrib.admin.widgets import FilteredSelectMultiple
from unidecode import unidecode
from django.contrib.admin.widgets import AutocompleteSelect
from django.contrib import admin
from dominios.utils import HiddenPasswordInput


class PerfilForm(forms.ModelForm):
    senha_certificado = forms.CharField(
        widget=forms.PasswordInput(), required=False)

    estabelecimento = forms.ModelMultipleChoiceField(
        queryset=Estabelecimento.objects.all(),
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
            classificacao_pessoa='funcionario'
        )

        if self.instance.pk:
            self.fields['dt_desligamento'].widget.attrs['readonly'] = True
            self.fields['senha_certificado'].widget = forms.PasswordInput(
                render_value=True
            )
            self.fields['senha_certificado'].initial = "********"

    def clean_pessoa(self):
        pessoa = self.cleaned_data.get('pessoa')

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
