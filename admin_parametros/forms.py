from django import forms
from .models import ConfiguracaoSessao


class ConfiguracaoSessaoForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoSessao
        fields = ['duracao_sessao',]

    def clean_duracao_sessao(self):
        duracao_sessao = self.cleaned_data['duracao_sessao']
        if duracao_sessao < 600:
            raise forms.ValidationError(
                'O tempo de duração da sessão deve ser de pelo menos 600 micro segundos.')
        return duracao_sessao
