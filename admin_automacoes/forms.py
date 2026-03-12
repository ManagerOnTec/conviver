from django import forms
from .models import EmailConfiguration


class EmailConfigurationAdminForm(forms.ModelForm):
    email_host_password = forms.CharField(
        widget=forms.PasswordInput(), required=False)

    class Meta:
        model = EmailConfiguration
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['email_host_password'].widget = forms.PasswordInput(
                render_value=True)
            self.fields['email_host_password'].initial = "********"
