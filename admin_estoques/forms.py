from django.core.exceptions import ValidationError
from django import forms
from admin_cadastros.forms import BaseModelForm
from dominios.utils import FilterByStatusMixin
from .models import Categoria, Grupo, Classe, SubClasse, TipoProduto, Produto


class TipoProdutoForm(FilterByStatusMixin, BaseModelForm):
    class Meta(BaseModelForm.Meta):
        model = TipoProduto
        fields = '__all__'

    def clean_descricao(self):
        return self.cleaned_data['descricao'].title()


class GrupoForm(FilterByStatusMixin, BaseModelForm):
    class Meta(BaseModelForm.Meta):
        model = Grupo
        fields = '__all__'

    def clean_descricao(self):
        return self.cleaned_data['descricao'].title()


class ClasseForm(FilterByStatusMixin, BaseModelForm):
    class Meta(BaseModelForm.Meta):
        model = Classe
        fields = '__all__'

    def clean_descricao(self):
        return self.cleaned_data['descricao'].title()


class SubClasseForm(FilterByStatusMixin, BaseModelForm):
    class Meta(BaseModelForm.Meta):
        model = SubClasse
        fields = '__all__'

    def clean_descricao(self):
        return self.cleaned_data['descricao'].title()


class CategoriaForm(FilterByStatusMixin, BaseModelForm):
    class Meta(BaseModelForm.Meta):
        model = Categoria
        fields = '__all__'

    def clean_descricao(self):
        return self.cleaned_data['descricao'].title()


class UnidadeMedidaForm(FilterByStatusMixin, BaseModelForm):
    class Meta(BaseModelForm.Meta):
        model = Categoria
        fields = '__all__'

    def clean_unidade_medida(self):
        return self.cleaned_data['unidade_medida'].upper()

    def clean_descricao(self):
        return self.cleaned_data['descricao'].title()


class ProdutoForm(FilterByStatusMixin, BaseModelForm):
    class Meta(BaseModelForm.Meta):
        model = Produto
        fields = '__all__'

    def clean_descricao(self):
        return self.cleaned_data['descricao'].title()

    def clean_subclasse(self):
        subclasse = self.cleaned_data.get('subclasse')
        classe = self.cleaned_data.get('classe')

        if subclasse and classe and subclasse.classe != classe:
            raise ValidationError(
                "A subclasse selecionada não pertence à classe selecionada.")

        return subclasse

    def clean(self):
        cleaned_data = super().clean()

        principio_ativo = cleaned_data.get('principio_ativo')
        produto_referencia = cleaned_data.get('produto_referencia')

        if (principio_ativo and not produto_referencia) or (produto_referencia and not principio_ativo):
            raise ValidationError(
                "Se o principio ativo for marcado, um produto de referência deve ser vinculado. Isto significa que este cadastro é do princípio ativo e deve ter o cadastro do produto de referência vinculado, já o produto referência não deve marcar o campo princípio ativo e não deve ser vinculado outro produto nele. A melhor forma de se cadatrar produtos é ter o produto referência cadastrado primeiro e depois cadastrar os princípio ativo, marcar o campo principio ativo, e vincular o produto de referência.")

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super(ProdutoForm, self).__init__(*args, **kwargs)

        # Esconda o campo 'status' se for um novo objeto (ou seja, se este for um form de criação)
        if self.instance._state.adding:
            self.fields['status'].widget = forms.HiddenInput()

        # Defina a queryset inicial do campo 'subclasse'
        self.fields['subclasse'].queryset = SubClasse.objects.filter(
            status='A')
