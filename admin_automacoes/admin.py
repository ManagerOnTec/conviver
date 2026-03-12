from .models import EmailConfiguration, QtdUsuariosSimultaneos
from .forms import EmailConfigurationAdminForm, forms
from django.contrib import admin
from cryptography.fernet import Fernet
from django.conf import settings
from cryptography.fernet import InvalidToken
import logging
from django.contrib import admin
from django.utils import timezone
from django.contrib import messages
from .models import ActiveSession

class EmailConfigurationAdmin(admin.ModelAdmin):
    form = EmailConfigurationAdminForm

    list_display = ('id', 'regra',
                    'email_host', 'email_host_user', 'email_port',)
    list_display_links = ('id', 'regra', 'email_host',
                          'email_port', 'email_host_user',)
    list_filter = ('regra',)

    def has_add_permission(self, request):
        return request.user.username == 'admin'

    def has_change_permission(self, request, obj=None):
        return request.user.username == 'admin'

    def has_delete_permission(self, request, obj=None):
        return request.user.username == 'admin'

    def has_view_permission(self, request, obj=None):
        return request.user.username == 'admin'


class QtdUsuariosSimultaneosAdmin(admin.ModelAdmin):

    list_display = ('id', 'max_usuarios_simultaneos',)
    list_display_links = ('id', 'max_usuarios_simultaneos')

    def has_add_permission(self, request):
        return request.user.username == 'admin'

    def has_change_permission(self, request, obj=None):
        return request.user.username == 'admin'

    def has_delete_permission(self, request, obj=None):
        return request.user.username == 'admin'

    def has_view_permission(self, request, obj=None):
        return request.user.username == 'admin'




@admin.register(ActiveSession)
class ActiveSessionAdmin(admin.ModelAdmin):

    list_display = (
        'session_key',
        'get_username',
        'get_email',
        'expire_date',
        'is_valid',
    )

    readonly_fields = (
        'session_key',
        'get_username',
        'get_email',
        'expire_date',
    )

    ordering = ('-expire_date',)

    actions = ['force_logout']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(expire_date__gte=timezone.now())

    def is_valid(self, obj):
        return obj.expire_date >= timezone.now()
    is_valid.boolean = True
    is_valid.short_description = "Sessão Ativa"

    def force_logout(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(
            request,
            f'{count} sessão(ões) encerrada(s) com sucesso.',
            messages.SUCCESS
        )

    force_logout.short_description = "Encerrar sessão (Forçar logout)"

    def has_add_permission(self, request):
        return False


admin.site.register(EmailConfiguration, EmailConfigurationAdmin)
admin.site.register(QtdUsuariosSimultaneos, QtdUsuariosSimultaneosAdmin)
