"""Forms da Gestão de Tarefas e Documentos."""
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import (
    ANEXO_EXTENSOES, Documento, Tarefa, Tipo,
)


class TipoForm(forms.ModelForm):
    class Meta:
        model = Tipo
        fields = ['descricao', 'observacao', 'status']

    def clean_descricao(self):
        descricao = (self.cleaned_data.get('descricao') or '').strip()
        if not descricao:
            raise ValidationError(
                'Informe a descrição do tipo de documento.')
        return descricao


class DocumentoForm(forms.ModelForm):
    class Meta:
        model = Documento
        fields = ['tipo', 'descricao_documento', 'anexo', 'vigencia_inicial',
                  'vigencia_final', 'inicio_renovacao', 'anotacoes', 'status']
        widgets = {
            'vigencia_inicial': forms.DateInput(
                attrs={'type': 'date'}, format='%Y-%m-%d'),
            'vigencia_final': forms.DateInput(
                attrs={'type': 'date'}, format='%Y-%m-%d'),
            'inicio_renovacao': forms.DateInput(
                attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def clean_anexo(self):
        anexo = self.cleaned_data.get('anexo')
        if not anexo:
            return anexo
        extensao = (anexo.name.rsplit('.', 1)[-1] or '').lower()
        if extensao not in ANEXO_EXTENSOES:
            raise ValidationError(
                'Extensão não permitida. Envie: ' +
                ', '.join(ANEXO_EXTENSOES).upper() + '.')
        return anexo

    def clean(self):
        dados = super().clean()
        vig_inicial = dados.get('vigencia_inicial')
        vig_final = dados.get('vigencia_final')
        inicio_renov = dados.get('inicio_renovacao')
        if vig_inicial and vig_final and vig_final < vig_inicial:
            self.add_error(
                'vigencia_final',
                'A vigência final deve ser igual ou posterior à inicial.')
        if inicio_renov and vig_final and inicio_renov > vig_final:
            self.add_error(
                'inicio_renovacao',
                'O início da renovação deve ser anterior ou igual à vigência '
                'final.')
        return dados


class DocumentoFiltroForm(forms.Form):
    """Filtros do menu lateral da listagem (padrão da Agenda)."""

    SITUACOES_FILTRO = (
        ('', 'Todas'),
        ('vigente', 'Vigentes'),
        ('proximo', 'Próximos do vencimento'),
        ('vencido', 'Vencidos'),
        ('aguardando_renovacao', 'Aguardando renovação'),
        ('sem_vigencia', 'Sem vigência definida'),
    )

    q = forms.CharField(
        label='Busca', required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Descrição, anotações, tipo...'}),
    )
    tipo = forms.ModelChoiceField(
        label='Tipo', required=False,
        queryset=Tipo.objects.none(), empty_label='Todos')
    situacao = forms.ChoiceField(
        label='Situação', required=False, choices=SITUACOES_FILTRO)
    data_inicio = forms.DateField(
        label='Vigência final (de)', required=False,
        widget=forms.DateInput(attrs={'type': 'date'}))
    data_fim = forms.DateField(
        label='Vigência final (até)', required=False,
        widget=forms.DateInput(attrs={'type': 'date'}))

    def __init__(self, *args, tipos=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tipos is not None:
            self.fields['tipo'].queryset = tipos


class RenovacaoForm(forms.Form):
    """Modal “Registrar renovação”: novas vigências + anexo opcional."""

    vigencia_inicial = forms.DateField(
        label='Nova vigência inicial', required=False,
        widget=forms.DateInput(attrs={'type': 'date'}))
    vigencia_final = forms.DateField(
        label='Nova vigência final', required=False,
        widget=forms.DateInput(attrs={'type': 'date'}))
    inicio_renovacao = forms.DateField(
        label='Início da próxima renovação', required=False,
        widget=forms.DateInput(attrs={'type': 'date'}))
    anexo = forms.FileField(
        label='Novo anexo (opcional)', required=False)
    observacao = forms.CharField(
        label='Observação', required=False,
        widget=forms.Textarea(attrs={'rows': 2}))

    def clean(self):
        dados = super().clean()
        vig_inicial = dados.get('vigencia_inicial')
        vig_final = dados.get('vigencia_final')
        inicio_renov = dados.get('inicio_renovacao')
        if not vig_final:
            self.add_error('vigencia_final',
                           'Informe a nova vigência final.')
        if vig_inicial and vig_final and vig_final < vig_inicial:
            self.add_error(
                'vigencia_final',
                'A vigência final deve ser igual ou posterior à inicial.')
        if inicio_renov and vig_final and inicio_renov > vig_final:
            self.add_error(
                'inicio_renovacao',
                'O início da renovação deve ser anterior ou igual à vigência '
                'final.')
        anexo = dados.get('anexo')
        if anexo:
            extensao = (anexo.name.rsplit('.', 1)[-1] or '').lower()
            if extensao not in ANEXO_EXTENSOES:
                self.add_error(
                    'anexo', 'Extensão não permitida. Envie: ' +
                    ', '.join(ANEXO_EXTENSOES).upper() + '.')
        return dados


class AnotacaoForm(forms.Form):
    texto = forms.CharField(
        label='Anotação', widget=forms.Textarea(attrs={'rows': 4}))

    def clean_texto(self):
        texto = (self.cleaned_data.get('texto') or '').strip()
        if not texto:
            raise ValidationError('Informe a anotação.')
        return texto


class DesvalidacaoForm(forms.Form):
    motivo = forms.CharField(
        label='Justificativa', widget=forms.Textarea(attrs={'rows': 3}))

    def clean_motivo(self):
        motivo = (self.cleaned_data.get('motivo') or '').strip()
        if not motivo:
            raise ValidationError('Informe a justificativa da desvalidação.')
        return motivo


class TarefaForm(forms.ModelForm):
    class Meta:
        model = Tarefa
        fields = ['titulo', 'documento', 'descricao', 'data_criacao',
                  'data_prazo', 'prioridade', 'usuario_responsavel',
                  'anotacoes']
        widgets = {
            'data_criacao': forms.DateInput(
                attrs={'type': 'date'}, format='%Y-%m-%d'),
            'data_prazo': forms.DateInput(
                attrs={'type': 'date'}, format='%Y-%m-%d'),
            'descricao': forms.Textarea(attrs={'rows': 3}),
            'anotacoes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['documento'].queryset = Documento.objects.filter(
            status='A').order_by('-pk')
        self.fields['documento'].empty_label = 'Sem documento vinculado'
        if not self.instance.pk:
            self.initial.setdefault('data_criacao', timezone.localdate())

    def clean_titulo(self):
        titulo = (self.cleaned_data.get('titulo') or '').strip()
        if not titulo:
            raise ValidationError('Informe o título da tarefa.')
        return titulo


class TarefaFiltroForm(forms.Form):
    SITUACOES_FILTRO = (
        ('', 'Todas'),
        ('P', 'Pendentes'),
        ('A', 'Em andamento'),
        ('C', 'Concluídas'),
        ('atrasadas', 'Atrasadas'),
        ('X', 'Canceladas'),
    )

    q = forms.CharField(
        label='Busca', required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Título, documento...'}))
    documento = forms.ModelChoiceField(
        label='Documento', required=False,
        queryset=Documento.objects.none(), empty_label='Todos')
    situacao = forms.ChoiceField(
        label='Situação', required=False, choices=SITUACOES_FILTRO)
    prioridade = forms.ChoiceField(
        label='Prioridade', required=False,
        choices=(('', 'Todas'), ('B', 'Baixa'), ('M', 'Média'), ('A', 'Alta')))

    def __init__(self, *args, documentos=None, **kwargs):
        super().__init__(*args, **kwargs)
        if documentos is not None:
            self.fields['documento'].queryset = documentos
