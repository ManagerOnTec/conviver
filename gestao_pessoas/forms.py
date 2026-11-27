"""Forms da Gestão de Pessoas."""
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from admin_cadastros.models import Pessoa

from .models import (
    ANEXO_EXTENSOES, ASO_TIPO_EXAME, ASO, CartaoPonto, Curso,
    CursoFuncionario, DocumentoFuncionario, EXAME_STATUS, ExamePeriodico,
    Ferias, FichaRegistro, Funcionario,
)


class DocumentoFuncionarioForm(forms.ModelForm):
    """Modal “Anexar documento”: arquivo + descrição + data."""

    class Meta:
        model = DocumentoFuncionario
        fields = ['tipo_documento', 'anexo', 'data_documento', 'descricao',
                  'anotacoes']
        widgets = {
            'data_documento': forms.DateInput(
                attrs={'type': 'date'}, format='%Y-%m-%d'),
            'anotacoes': forms.Textarea(attrs={'rows': 2}),
        }

    def clean(self):
        dados = super().clean()
        if not (dados.get('tipo_documento') or '').strip():
            self.add_error('tipo_documento', 'Informe o tipo do documento.')
        if not dados.get('anexo'):
            self.add_error('anexo', 'Selecione o arquivo do documento.')
        if not dados.get('data_documento'):
            self.add_error('data_documento', 'Informe a data do documento.')
        return dados


class AsoAgendarForm(forms.Form):
    """Modal “Agendar ASO”: data do agendamento + tipo."""

    tipo_exame = forms.ChoiceField(
        label='Tipo de exame', choices=ASO_TIPO_EXAME,
        initial='periodico')
    data_agendamento = forms.DateField(
        label='Data do agendamento',
        widget=forms.DateInput(attrs={'type': 'date'}))


class AsoRegistrarForm(forms.Form):
    """Modal “Registrar ASO”: realização, validade e anexo."""

    data_realizacao = forms.DateField(
        label='Data de realização', widget=forms.DateInput(
            attrs={'type': 'date'}))
    data_validade = forms.DateField(
        label='Validade (opcional)', required=False,
        widget=forms.DateInput(attrs={'type': 'date'}))
    anexo = forms.FileField(
        label='Anexo do ASO (opcional)', required=False)
    observacoes = forms.CharField(
        label='Observações', required=False,
        widget=forms.Textarea(attrs={'rows': 2}))

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


class FichaRegistroForm(forms.Form):
    """Modal “Ficha de registro”: anexo + data."""

    anexo = forms.FileField(label='Arquivo da ficha')
    data_registro = forms.DateField(
        label='Data do registro', widget=forms.DateInput(
            attrs={'type': 'date'}))
    observacoes = forms.CharField(
        label='Observações', required=False,
        widget=forms.Textarea(attrs={'rows': 2}))

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


class CartaoPontoForm(forms.ModelForm):
    class Meta:
        model = CartaoPonto
        fields = ['numero_cartao', 'data_inicio_vigencia', 'observacoes']
        widgets = {
            'data_inicio_vigencia': forms.DateInput(
                attrs={'type': 'date'}, format='%Y-%m-%d'),
            'observacoes': forms.Textarea(attrs={'rows': 2}),
        }


class PeriodicoAgendarForm(forms.Form):
    data_agendamento = forms.DateField(
        label='Data do agendamento', widget=forms.DateInput(
            attrs={'type': 'date'}))
    observacoes = forms.CharField(
        label='Observações', required=False,
        widget=forms.Textarea(attrs={'rows': 2}))


class PeriodicoRegistrarForm(forms.Form):
    data_realizacao = forms.DateField(
        label='Data de realização', widget=forms.DateInput(
            attrs={'type': 'date'}))
    data_proximo_exame = forms.DateField(
        label='Data do próximo exame', required=False,
        widget=forms.DateInput(attrs={'type': 'date'}))
    anexo = forms.FileField(
        label='Anexo (resultado/ASO)', required=False)
    observacoes = forms.CharField(
        label='Observações', required=False,
        widget=forms.Textarea(attrs={'rows': 2}))

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


class CursoForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = ['nome', 'descricao', 'carga_horaria', 'validade_meses',
                  'status']


class CursoFuncionarioForm(forms.ModelForm):
    """Registrar realização de curso (certificado opcional)."""

    class Meta:
        model = CursoFuncionario
        fields = ['curso', 'data_realizacao', 'data_validade',
                  'anexo_certificado', 'status', 'observacoes']
        widgets = {
            'data_realizacao': forms.DateInput(
                attrs={'type': 'date'}, format='%Y-%m-%d'),
            'data_validade': forms.DateInput(
                attrs={'type': 'date'}, format='%Y-%m-%d'),
            'observacoes': forms.Textarea(attrs={'rows': 2}),
        }


class FeriasForm(forms.ModelForm):
    """Período aquisitivo/concessivo + programação."""

    class Meta:
        model = Ferias
        fields = [
            'periodo_aquisitivo_inicio', 'periodo_aquisitivo_final',
            'periodo_concessivo_inicio', 'periodo_concessivo_final',
            'dias_direito', 'dias_gozados', 'data_inicio_ferias',
            'data_final_ferias', 'status', 'observacoes']
        widgets = {campo: forms.DateInput(
            attrs={'type': 'date'}, format='%Y-%m-%d')
            for campo in ('periodo_aquisitivo_inicio',
                          'periodo_aquisitivo_final',
                          'periodo_concessivo_inicio',
                          'periodo_concessivo_final',
                          'data_inicio_ferias', 'data_final_ferias')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Campos com default/derivados: o modal de aquisitivo/programar não
        # os envia — não são obrigatórios no POST.
        self.fields['dias_gozados'].required = False
        self.fields['status'].required = False

    def clean(self):
        dados = super().clean()
        gozados = dados.get('dias_gozados') or 0
        direito = dados.get('dias_direito') or 0
        if gozados > direito:
            self.add_error(
                'dias_gozados',
                f'Os dias gozados ({gozados}) não podem ultrapassar os dias '
                f'de direito ({direito}).')
        return dados


class FuncionarioForm(forms.ModelForm):
    """Cadastro do funcionário: campo `pessoa` (pré-carregável via
    ?pessoa= do modal de pendentes), estabelecimento FORA do form (a view
    grava o da sessão) e datas com o seletor de calendário."""

    class Meta:
        model = Funcionario
        fields = ['pessoa', 'data_admissao', 'status_funcionario',
                  'anotacoes']
        widgets = {
            'pessoa': forms.Select(attrs={'class': 'form-select',
                                          'data-width': '100%'}),
            'data_admissao': forms.DateInput(
                attrs={'type': 'date'}, format='%Y-%m-%d'),
            'anotacoes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, pessoa_pre_carga=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Só pessoas do tipo funcionário ativas (recorte do estabelecimento
        # não se aplica à pessoa; a vinculação é a própria linha criada).
        self.fields['pessoa'].queryset = Pessoa.objects.filter(
            status='A', classificacao_pessoa='funcionario').order_by('nome')
        # PRÉ-CARGA: pessoa clicada no modal “Funcionários sem Registro”.
        if pessoa_pre_carga is not None:
            self.fields['pessoa'].initial = pessoa_pre_carga
            self.fields['pessoa'].queryset = (
                self.fields['pessoa'].queryset |
                Pessoa.objects.filter(pk=pessoa_pre_carga.pk))
        if not self.instance.pk:
            self.initial.setdefault('data_admissao', timezone.localdate())


class FuncionarioFiltroForm(forms.Form):
    """Filtros do menu lateral da listagem de funcionários.

    Mesmo padrão do `AgendaPacienteFiltroForm` (crispy no menul, compacto).
    """

    q = forms.CharField(
        label='Busca', required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Nome ou CPF...'}),
    )
    situacao = forms.ChoiceField(
        label='Situação', required=False,
        choices=(('', 'Todas'), ('A', 'Ativos'), ('F', 'Afastados'),
                 ('D', 'Desligados')),
    )
    admissao_inicio = forms.DateField(
        label='Admissão (de)', required=False,
        widget=forms.DateInput(attrs={'type': 'date'}))
    admissao_fim = forms.DateField(
        label='Admissão (até)', required=False,
        widget=forms.DateInput(attrs={'type': 'date'}))
    sem_aso_agendado = forms.BooleanField(
        label='Sem ASO agendado/realizado', required=False)
    sem_ficha = forms.BooleanField(
        label='Ficha de registro pendente', required=False)
    sem_periodico = forms.BooleanField(
        label='Periódico pendente', required=False)
    cursos_vencidos = forms.BooleanField(
        label='Cursos vencidos', required=False)
    ferias_pendentes = forms.BooleanField(
        label='Férias pendentes/programadas', required=False)
