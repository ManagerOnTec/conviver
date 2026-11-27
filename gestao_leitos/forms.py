"""Forms da Gestão de Leitos."""
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from django_select2.forms import ModelSelect2Widget

from admin_cadastros.models import Ala, Local, Leito, Setor
from atendimentos.models import Atendimento

from .models import GESTAO_STATUS, GestaoLeito


def _atendimentos_sem_leito(estabelecimento):
    """Atendimentos ativos SEM ALTA e SEM ocupação de leito ativa."""
    ocupados = GestaoLeito.objects.filter(
        dt_saida__isnull=True).values('atendimento_id')
    return Atendimento.objects.filter(
        estabelecimento=estabelecimento, status='A',
        dt_alta__isnull=True,
    ).exclude(pk__in=ocupados).order_by('-pk')


class LeitoMapaFiltroForm(forms.Form):
    """Filtros do menul do mapa de leitos (padrão da Agenda)."""

    SITUACOES_FILTRO = (
        ('', 'Todas'),
        ('O', 'Ocupados'),
        ('L', 'Livres'),
        ('B', 'Bloqueados'),
        ('H', 'Higienização'),
    )

    q = forms.CharField(
        label='Busca', required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Leito, paciente, CPF...'}))
    ala = forms.ModelChoiceField(
        label='Ala', required=False, queryset=Ala.objects.none(),
        empty_label='Todas')
    setor = forms.ModelChoiceField(
        label='Setor', required=False, queryset=None, empty_label='Todos')
    local = forms.ModelChoiceField(
        label='Local', required=False, queryset=None, empty_label='Todos')
    situacao = forms.ChoiceField(
        label='Situação', required=False, choices=SITUACOES_FILTRO)
    status = forms.ChoiceField(
        label='Status', required=False,
        choices=(('', 'Todos'), ('A', 'Ativos'), ('I', 'Inativos')))

    def __init__(self, *args, estabelecimento=None, **kwargs):
        super().__init__(*args, **kwargs)
        if estabelecimento is not None:
            self.fields['ala'].queryset = Ala.objects.filter(
                estabelecimento=estabelecimento, status='A')
            self.fields['setor'].queryset = Setor.objects.filter(
                    estabelecimento=estabelecimento, status='A')
            self.fields['local'].queryset = Local.objects.filter(
                setor__estabelecimento=estabelecimento, status='A')


class AtendimentoSelect2Widget(ModelSelect2Widget):
    """LOOKUP digitado (padrão do projeto): busca o paciente/exame do
    atendimento ativo, sem alta e sem leito, do estabelecimento da sessão.
    """

    model = Atendimento
    search_fields = [
        'pessoa__nome__icontains', 'pessoa__cpf__icontains', 'id__icontains',
    ]

    def filter_queryset(self, request, term, queryset=None, **dependent_fields):
        estabelecimento_id = request.session.get('estabelecimento_id')
        if not request.user.is_authenticated or not estabelecimento_id:
            return self.get_queryset().none()
        return _atendimentos_sem_leito(estabelecimento_id).filter(
            Q(pessoa__nome__icontains=term)
            | Q(pessoa__cpf__icontains=term)
            | Q(id__icontains=term)).select_related('pessoa')[:50]

    def label_from_instance(self, atendimento):
        pessoa = atendimento.pessoa
        cpf = pessoa.cpf or ''
        return (f'#{atendimento.pk} — {pessoa.nome}'
                + (f' (CPF {cpf})' if cpf else ''))


class LeitoSelect2Widget(ModelSelect2Widget):
    """LOOKUP digitado dos leitos LIVRES do estabelecimento da sessão
    (sempre exibindo leito + local / setor / ala no rótulo)."""

    model = Leito
    search_fields = [
        'leito__icontains', 'local__nome__icontains',
        'local__setor__nome__icontains', 'local__setor__ala__nome__icontains',
    ]

    def filter_queryset(self, request, term, queryset=None, **dependent_fields):
        estabelecimento_id = request.session.get('estabelecimento_id')
        if not request.user.is_authenticated or not estabelecimento_id:
            return self.get_queryset().none()
        return Leito.objects.filter(
            status='A', ocupado=False,
            local__setor__estabelecimento_id=estabelecimento_id,
            local__setor__ala__internacao=True,
        ).filter(
            Q(leito__icontains=term)
            | Q(local__nome__icontains=term)
            | Q(local__setor__nome__icontains=term)
            | Q(local__setor__ala__nome__icontains=term),
        ).select_related('local', 'local__setor', 'local__setor__ala')[:50]

    def label_from_instance(self, leito):
        local = leito.local
        return (f'{leito.leito} — {local.nome}'
                + (f' / {local.setor.nome}' if local.setor_id else '')
                + (f' / {local.setor.ala.nome}'
                   if local.setor_id and local.setor.ala_id else ''))


class OcuparLeitoForm(forms.Form):
    """Modal “Registrar Ocupação”: leito LIVRE e atendimento SEM leito, ambos
    digitáveis (django_select2), sempre do estabelecimento da sessão."""

    leito = forms.ModelChoiceField(
        label='Leito (livre)', queryset=Leito.objects.none(),
        widget=LeitoSelect2Widget(
            attrs={
                'data-minimum-input-length': 0,
                'data-placeholder': 'Digite leito, local, setor ou ala...',
                'data-theme': 'default',
                'data-language': 'pt-BR',
                'data-width': '100%',
            }))
    atendimento = forms.ModelChoiceField(
        label='Atendimento (paciente)',
        queryset=Atendimento.objects.none(),
        widget=AtendimentoSelect2Widget(
            attrs={
                'data-minimum-input-length': 0,
                'data-placeholder': 'Digite nome, CPF ou nº do atendimento...',
                'data-theme': 'default',
                'data-language': 'pt-BR',
                'data-width': '100%',
            }))
    dt_entrada = forms.DateTimeField(
        label='Data/hora de entrada',
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))
    observacoes = forms.CharField(
        label='Observações', required=False,
        widget=forms.Textarea(attrs={'rows': 2}))

    def __init__(self, *args, estabelecimento=None, **kwargs):
        super().__init__(*args, **kwargs)
        if estabelecimento is not None:
            # Validação do POST precisa de queryset real (o select2 valida
            # contra ele); o recorte continua server-side.
            self.fields['atendimento'].queryset = _atendimentos_sem_leito(
                estabelecimento)
            self.fields['leito'].queryset = Leito.objects.filter(
                status='A', ocupado=False,
                local__setor__estabelecimento=estabelecimento,
                local__setor__ala__internacao=True)
        if not self.is_bound:
            self.initial.setdefault(
                'dt_entrada', timezone.localtime().strftime('%Y-%m-%dT%H:%M'))

    def clean_atendimento(self):
        atendimento = self.cleaned_data.get('atendimento')
        if atendimento is None:
            raise ValidationError('Selecione o atendimento.')
        if atendimento.dt_alta:
            raise ValidationError(
                'Este atendimento já teve ALTA: não pode ocupar leito.')
        if GestaoLeito.objects.filter(
                atendimento=atendimento, dt_saida__isnull=True).exists():
            raise ValidationError(
                'Este atendimento já está em outro leito (use Trocar leito).')
        return atendimento


class SaidaLeitoForm(forms.Form):
    dt_saida = forms.DateTimeField(
        label='Data/hora de saída',
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))
    observacoes = forms.CharField(
        label='Motivo/observações', required=False,
        widget=forms.Textarea(attrs={'rows': 2}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.initial.setdefault(
                'dt_saida', timezone.localtime().strftime('%Y-%m-%dT%H:%M'))


class TransferenciaLeitoForm(forms.Form):
    leito_destino = forms.ModelChoiceField(
        label='Leito de destino', queryset=Leito.objects.none(),
        widget=LeitoSelect2Widget(
            attrs={
                'data-minimum-input-length': 0,
                'data-placeholder': 'Digite leito, local, setor ou ala...',
                'data-theme': 'default',
                'data-language': 'pt-BR',
                'data-width': '100%',
            }))
    observacoes = forms.CharField(
        label='Observações', required=False,
        widget=forms.Textarea(attrs={'rows': 2}))

    def __init__(self, *args, leito_atual=None, estabelecimento=None,
                 **kwargs):
        super().__init__(*args, **kwargs)
        # Validação do POST precisa de queryset real (recorte server-side).
        self.fields['leito_destino'].queryset = Leito.objects.filter(
            status='A', ocupado=False,
            local__setor__estabelecimento=estabelecimento,
            local__setor__ala__internacao=True,
        ).exclude(pk=leito_atual.pk if leito_atual else None)
        self.leito_atual = leito_atual


class StatusLeitoForm(forms.Form):
    situacao = forms.ChoiceField(label='Nova situação', choices=GESTAO_STATUS)
    observacoes = forms.CharField(
        label='Motivo', required=False,
        widget=forms.Textarea(attrs={'rows': 2}))


class OcupacaoForm(forms.ModelForm):
    """Form da TELA de registrar/editar ocupação (selects digitáveis)."""

    class Meta:
        model = GestaoLeito
        fields = ['leito', 'atendimento', 'dt_entrada', 'situacao',
                  'observacoes']
        widgets = {
            'leito': LeitoSelect2Widget(
                attrs={
                    'data-minimum-input-length': 0,
                    'data-placeholder': 'Digite leito, local, setor ou ala...',
                    'data-theme': 'default',
                    'data-language': 'pt-BR',
                    'data-width': '100%',
                }),
            'atendimento': AtendimentoSelect2Widget(
                attrs={
                    'data-minimum-input-length': 0,
                    'data-placeholder': 'Digite nome, CPF ou nº do atendimento...',
                    'data-theme': 'default',
                    'data-language': 'pt-BR',
                    'data-width': '100%',
                }),
            'dt_entrada': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}),
            'observacoes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, estabelecimento=None, **kwargs):
        super().__init__(*args, **kwargs)
        if estabelecimento is not None:
            # Validação do POST contra querysets reais (recorte server-side).
            self.fields['atendimento'].queryset = _atendimentos_sem_leito(
                estabelecimento)
            self.fields['leito'].queryset = Leito.objects.filter(
                status='A', ocupado=False,
                local__setor__estabelecimento=estabelecimento,
                local__setor__ala__internacao=True)
        # Pré-seleção (ex.: ?atendimento= do modal “Pacientes sem Leitos”):
        # o objeto inicial precisa estar no queryset para o select2
        # renderizar a opção selecionada.
        for campo, modelo in (('atendimento', Atendimento),
                              ('leito', Leito)):
            selecionado = self.initial.get(campo) or self.initial.get(
                f'{campo}_id')
            if selecionado:
                self.fields[campo].queryset = \
                    self.fields[campo].queryset | \
                    modelo.objects.filter(pk=getattr(selecionado, 'pk',
                                                     selecionado))

    def clean(self):
        dados = super().clean()
        situacao = dados.get('situacao')
        atendimento = dados.get('atendimento')
        # Atendimento OBRIGATÓRIO apenas em OCUPADO; nas demais situações o
        # leito é operado sem paciente (limpa o campo).
        if situacao == 'O' and not atendimento:
            self.add_error(
                'atendimento',
                'Para ocupar o leito, selecione o atendimento do paciente.')
        elif situacao in ('L', 'B', 'H'):
            dados['atendimento'] = None
            self.cleaned_data['atendimento'] = None
        return dados
