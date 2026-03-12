from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _
from django.contrib import admin, auth
from django.forms import BaseInlineFormSet, SelectMultiple
from dominios.utils import IsActiveFilter
from . import models
from django.conf import settings
import os
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.contrib.auth.models import User
from .models import Pessoa, Estabelecimento, Perfil
from .forms import CustomUserChangeForm, CustomUserCreationForm, PerfilForm
from django.core.exceptions import ValidationError
from admin_cadastros.models import Pessoa

from django.contrib.auth.admin import GroupAdmin
from django.contrib.auth.models import Group
from django.contrib import messages


class PerfilInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        # Verifica se há pelo menos um Perfil criado
        has_perfil = False
        for form in self.forms:
            if form.cleaned_data.get('user'):
                has_perfil = True
                break

        if not has_perfil:
            raise ValidationError(
                'Por favor, preencha todos os campos obrigatórios do perfil.')


class PerfilInline(admin.StackedInline):
    model = Perfil
    form = PerfilForm
    formset = PerfilInlineFormSet
    can_delete = False
    verbose_name = 'Perfil'
    verbose_name_plural = 'Perfis'
    ordering = ['-pk',]

    def has_delete_permission(self, request, obj=None):
        return False

    # 🔒 FILTRA SOMENTE FUNCIONÁRIOS NO PERFIL
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)

        # altera queryset do campo pessoa no form base
        formset.form.base_fields['pessoa'].queryset = Pessoa.objects.filter(
            classificacao_pessoa='funcionario'
        )

        return formset

class UserAdmin(DefaultUserAdmin):
    inlines = [PerfilInline]
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    # Personalize conforme necessário
    list_display = ('id', 'username', 'perfil_pessoa', 'email', 'is_active', 'is_staff',
                    'is_superuser', 'estabelecimentos_perfil', 'perfil_estabelecimento_padrao', 'grupos_perfil', )

    list_filter = (IsActiveFilter, 'is_staff', 'is_superuser', 'groups',)

    list_editable = ('is_active', 'is_staff', 'is_superuser', 'email',)

    list_display_links = ('id', 'username', 'perfil_pessoa',)

    ordering = ['-pk',]

    search_fields = ('id', 'username', 'email', 'perfil__pessoa__nome',)

    list_per_page = 11

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.username != 'admin':
            return queryset.exclude(username='admin')  # excluir usuário admin
        return queryset

    # METODO PARA VER SENHA DO CERTIFICADO
    def perfil_senha_certificado(self, obj):
        return obj.perfil.senha_certificado
    perfil_senha_certificado.short_description = 'Senha Certificado'

    def perfil_pessoa(self, obj):
        return obj.perfil.pessoa.nome
    perfil_pessoa.short_description = 'Pessoa.Nome'

    # Função personalizada para exibir o "Estabelecimento Padrão"

    def perfil_estabelecimento_padrao(self, obj):
        # Verifica se o usuário tem um perfil associado e se o estabelecimento_padrao está definido
        return obj.perfil.estabelecimento_padrao if hasattr(obj, 'perfil') else None
    perfil_estabelecimento_padrao.short_description = 'Estabelecimento Padrão'

    def grupos_perfil(self, obj):
        return ", ".join([g.name for g in obj.groups.all()])
    grupos_perfil.short_description = 'Grupos'

    def estabelecimentos_perfil(self, obj):
        return ", " .join([g.estabelecimento for g in obj.perfil.estabelecimento.all()])
    estabelecimentos_perfil.short_description = 'Estabelecimentos'

    default_password = "abc123++"  # Substitua pela senha padrão desejada
    help_text = f'Recomendamos uso do primeiro nome.sobrenome para usuario. A senha padrão para novos usuários é: {default_password}, ela sera alterada no primeiro acesso!'

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'email'),
            'description': help_text,
        }),
        (('Permissões'), {'fields': ('is_active', 'is_staff',
         'is_superuser', 'groups', 'user_permissions')}),
    )

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (('E-mail'), {'fields': ('email',)}),
        (('Permissões'), {'fields': ('is_active', 'is_staff',
         'is_superuser', 'groups', 'user_permissions')}),

    )


class PreventGroupDeletionMixin:
    def delete_model(self, request, obj):
        if obj.user_set.exists():
            messages.error(
                request, 'Este grupo não pode ser excluído pois está relacionado a outros objetos.')
        else:
            super().delete_model(request, obj)


class CustomGroupAdmin(PreventGroupDeletionMixin, GroupAdmin):
    def has_delete_permission(self, request, obj=None):
        # Permitir exclusão apenas se não houver usuários associados
        if obj and obj.user_set.exists():
            messages.error(
                request, 'Este grupo não pode ser excluído pois está relacionado a usuários.')
            return False
        return super().has_delete_permission(request, obj)


admin.site.unregister(Group)
admin.site.register(Group, CustomGroupAdmin)
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
User._meta.verbose_name_plural = "2. Usuários"
Group._meta.verbose_name_plural = "1. Grupos"
