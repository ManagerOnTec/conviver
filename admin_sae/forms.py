from django import forms
from .models import BaseModel, Aspecto, AspectoAnalisado, Evidencia, DiagnosticoEnfermagem, FatorRelacionado, Intervencao, ParametrosSAE
from dominios.utils import FilterByStatusMixin
from admin_cadastros.forms import BaseModelForm


class AspectoForm(FilterByStatusMixin, BaseModelForm):
    class Meta(BaseModelForm.Meta):
        model = Aspecto
        fields = '__all__'

    def clean_descricao(self):
        return self.cleaned_data['descricao'].title()


class AspectoAnalisadoForm(FilterByStatusMixin, BaseModelForm):
    class Meta(BaseModelForm.Meta):
        model = AspectoAnalisado
        fields = ['descricao', 'aspecto', 'dt_registro',
                  'us_registro', 'dt_atualizacao', 'us_atualizacao', 'status']

    def clean_descricao(self):
        return self.cleaned_data['descricao'].title()


class EvidenciaForm(FilterByStatusMixin, BaseModelForm):
    class Meta(BaseModelForm.Meta):
        model = Evidencia

        fields = ['descricao', 'aspecto_analisado', 'dt_registro',
                  'us_registro', 'dt_atualizacao', 'us_atualizacao', 'status']

    def clean_descricao(self):
        return self.cleaned_data['descricao'].title()


class DiagnosticoEnfermagemForm(FilterByStatusMixin, BaseModelForm):
    class Meta(BaseModelForm.Meta):
        model = DiagnosticoEnfermagem

        fields = ['descricao', 'evidencia', 'dt_registro',
                  'us_registro', 'dt_atualizacao', 'us_atualizacao', 'status']

    def clean_descricao(self):
        return self.cleaned_data['descricao'].title()


class FatorRelacionadoForm(FilterByStatusMixin, BaseModelForm):
    class Meta(BaseModelForm.Meta):
        model = FatorRelacionado

        fields = ['descricao', 'diagnostico_enfermagem', 'dt_registro',
                  'us_registro', 'dt_atualizacao', 'us_atualizacao', 'status']

    def clean_descricao(self):
        return self.cleaned_data['descricao'].title()


class IntervencaoForm(FilterByStatusMixin, BaseModelForm):
    class Meta(BaseModelForm.Meta):
        model = Intervencao

        fields = ['descricao', 'fator_relacionado', 'dt_registro',
                  'us_registro', 'dt_atualizacao', 'us_atualizacao', 'status']

    def clean_descricao(self):
        return self.cleaned_data['descricao'].title()


class ParametrosSAEForm(FilterByStatusMixin, BaseModelForm):
    class Meta(BaseModelForm.Meta):
        model = ParametrosSAE

        fields = ['profissao', 'profissional',  'estabelecimento', 'status', 'dt_registro',
                  'us_registro', 'dt_atualizacao', 'us_atualizacao']

    def clean(self):
        cleaned_data = super().clean()

        profissao = cleaned_data.get('profissao')
        profissional = cleaned_data.get('profissional')

        if not profissao and not profissional:
            raise forms.ValidationError(
                "Deve ser definida uma profissão ou usuário.",
                code='invalid',
            )
