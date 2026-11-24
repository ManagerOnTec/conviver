from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django_select2.forms import ModelSelect2Widget, Select2Widget
from django.utils import timezone

from atendimentos.models import Atendimento

from admin_cadastros.models import Local
from .models import AgendaPaciente, TipoAgendamento


class ExameSolicitadoSelect2Widget(ModelSelect2Widget):
    search_fields = (
        'tipo_exame__descricao__icontains',
        'solicitacao__icontains',
        'atendimento__pessoa__nome__icontains',
    )

    def label_from_instance(self, exame):
        solicitacao = ' '.join((exame.solicitacao or '').split())
        if len(solicitacao) > 100:
            solicitacao = f'{solicitacao[:97]}...'
        registrado_em = timezone.localtime(
            exame.dt_registro).strftime('%d/%m/%Y %H:%M')
        paciente = exame.atendimento.pessoa.nome
        return (
            f'{exame.tipo_exame} | {registrado_em} | {paciente} | '
            f'{solicitacao or "Sem detalhes da solicitação"}')

    def filter_queryset(self, request, term, queryset=None, **dependent_fields):
        atendimento_id = dependent_fields.get('atendimento_id')
        estabelecimento_id = request.session.get('estabelecimento_id')
        if not request.user.is_authenticated or not atendimento_id \
                or not estabelecimento_id:
            return self.get_queryset().none()

        queryset = queryset or self.get_queryset()
        queryset = queryset.filter(
            atendimento_id=atendimento_id,
            estabelecimento_id=estabelecimento_id,
            status='A',
            resultados__isnull=True,
        ).select_related('tipo_exame', 'atendimento__pessoa').distinct()
        return super().filter_queryset(
            request, term, queryset=queryset, **dependent_fields)


def _locais_compativeis(estabelecimento_id, externo=None, atual=None):
    locais = Local.objects.filter(status='A')
    if estabelecimento_id:
        locais = locais.filter(
            Q(setor__estabelecimento_id=estabelecimento_id)
            | Q(setor__isnull=True, online='S'))
    if externo is True:
        locais = locais.filter(
            Q(setor__ala__internacao=False)
            | Q(setor__isnull=True, online='S'))
    elif externo is False:
        locais = locais.filter(setor__ala__internacao=True)
    if atual:
        locais = Local.objects.filter(Q(pk=atual) | Q(pk__in=locais))
    return locais.select_related('setor__ala').order_by('nome')


class TipoAgendamentoForm(forms.ModelForm):
    """Cadastro de tipos de agendamento (admin)."""

    class Meta:
        model = TipoAgendamento
        fields = '__all__'

    def clean_descricao(self):
        descricao = (self.cleaned_data.get('descricao') or '').strip()
        if not descricao:
            raise ValidationError(
                'Informe a descrição do tipo de agendamento.')
        return descricao


class AgendaPacienteForm(forms.ModelForm):
    """Agendamento POR ATENDIMENTO (sem campo pessoa).

    Quando o tipo é do tipo exame, exige o `exame` solicitado do atendimento
    (não executado). Tipo não-exame não aceita exame vinculado.
    """

    class Meta:
        model = AgendaPaciente
        fields = [
            'atendimento', 'tipo', 'exame', 'local', 'data_hora',
            'responsavel', 'observacao', 'link_videochamada',
            'link_whatsapp', 'efetuado', 'dt_efetuado',
            'observacao_execucao', 'status',
        ]
        widgets = {
            'data_hora': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'dt_efetuado': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'observacao': forms.Textarea(attrs={'rows': 3}),
            'observacao_execucao': forms.Textarea(attrs={'rows': 3}),
            'exame': ExameSolicitadoSelect2Widget(
                dependent_fields={'atendimento': 'atendimento_id'},
                attrs={'data-placeholder': 'Pesquise por exame ou solicitação'}),
            'local': Select2Widget(
                attrs={'data-placeholder': 'Selecione um local'}),
        }

    def __init__(self, *args, **kwargs):
        estabelecimento_id = kwargs.pop('estabelecimento_id', None)
        super().__init__(*args, **kwargs)
        estabelecimento_id = estabelecimento_id or \
            self.instance.estabelecimento_id or \
            self.initial.get('estabelecimento_id')

        if 'atendimento' in self.fields and estabelecimento_id:
            self.fields['atendimento'].queryset = Atendimento.objects.filter(
                estabelecimento_id=estabelecimento_id)

        if 'tipo' in self.fields:
            tipo_atual = self.instance.tipo_id if self.instance.pk else None
            tipos = TipoAgendamento.objects.filter(status='A')
            if tipo_atual:
                tipos = TipoAgendamento.objects.filter(
                    Q(status='A') | Q(pk=tipo_atual))
            self.fields['tipo'].queryset = tipos.order_by('descricao')

        if 'local' in self.fields:
            tipo_id = self.data.get('tipo') if self.is_bound else None
            if not tipo_id:
                tipo_inicial = (
                    self.instance.tipo_id if self.instance.pk
                    else self.initial.get('tipo'))
                tipo_id = getattr(tipo_inicial, 'pk', tipo_inicial)
            try:
                tipo = TipoAgendamento.objects.filter(
                    pk=int(tipo_id), status='A').first()
            except (TypeError, ValueError):
                tipo = None

            local_atual = self.instance.local_id if self.instance.pk else None
            self.fields['local'].queryset = _locais_compativeis(
                estabelecimento_id,
                externo=tipo.externo if tipo else None,
                atual=local_atual)

        for campo in ('data_hora', 'dt_efetuado'):
            if self.fields.get(campo):
                self.fields[campo].input_formats = ['%Y-%m-%dT%H:%M']

        # A consulta AJAX exige o atendimento escolhido e a sessão recorta
        # todos os resultados pelo estabelecimento ativo.
        if 'exame' in self.fields:
            from prontuarios.models import Exame
            exames = Exame.objects.filter(
                status='A', resultados__isnull=True)
            if estabelecimento_id:
                exames = exames.filter(
                    estabelecimento_id=estabelecimento_id)
            atual = self.instance.exame_id if self.instance.pk else None
            if atual:
                exames = Exame.objects.filter(Q(pk=atual) | Q(pk__in=exames))
            self.fields['exame'].queryset = exames.select_related(
                'tipo_exame', 'atendimento__pessoa').distinct()

    def clean(self):
        dados = super().clean()
        tipo = dados.get('tipo')
        local = dados.get('local')
        link_video = dados.get('link_videochamada')
        link_whats = dados.get('link_whatsapp')
        exame = dados.get('exame')
        atendimento = dados.get('atendimento')

        # Sempre validar o TIPO.
        if not tipo:
            raise ValidationError(
                {'tipo': 'Informe o tipo de agendamento.'})
        if tipo.status != 'A':
            raise ValidationError(
                {'tipo': 'Este tipo de agendamento está inativo. Selecione um '
                         'tipo ativo.'})

        # A dependência é uma configuração explícita do tipo, não inferida
        # pelo texto da descrição.
        if tipo.exige_exame_solicitado:
            if not exame:
                raise ValidationError({
                    'exame': 'Para este tipo de agendamento, selecione o '
                             'exame solicitado do atendimento.',
                })
            if atendimento and exame.atendimento_id != atendimento.pk:
                raise ValidationError({
                    'exame': 'Este exame não pertence ao atendimento '
                             'informado.',
                })
            exame_original = (
                self.instance.exame_id if self.instance.pk else None)
            if exame.pk != exame_original and \
                    exame.resultados.filter(status='A').exists():
                raise ValidationError({
                    'exame': 'Este exame já foi executado e não pode ser '
                             'agendado novamente.',
                })
            # Atendimento herdados do exame (garante o vínculo).
            if not atendimento:
                dados['atendimento'] = exame.atendimento
                self.instance.atendimento = exame.atendimento
        elif exame:
            raise ValidationError({
                'exame': 'Somente tipos de agendamento que exigem exame podem '
                         'estar vinculados a um exame.',
            })

        if tipo.exige_local_online == 'S' and (
                not local or local.online != 'S'):
            raise ValidationError({
                'local': 'Este tipo de agendamento exige um local online ativo.'
            })
        if local and local.online == 'S' and not (
                link_video or link_whats or local.link_online):
            raise ValidationError({
                'link_videochamada': 'Este local é online: informe o link da '
                                     'videochamada ou do WhatsApp.'
            })
        if tipo.local_id and not local:
            dados['local'] = tipo.local
            self.instance.local = tipo.local
        return dados


class AgendaExameModalForm(forms.ModelForm):
    """Campos mínimos para marcar um único agendamento a partir do exame."""

    class Meta:
        model = AgendaPaciente
        fields = (
            'tipo', 'data_hora', 'local', 'observacao',
            'link_videochamada', 'link_whatsapp',
        )
        widgets = {
            'data_hora': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'),
            'observacao': forms.Textarea(attrs={'rows': 2}),
            'local': Select2Widget(
                attrs={'data-placeholder': 'Selecione um local'}),
        }

    def __init__(
        self, *args, atendimento, exame, estabelecimento_id, responsavel=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.instance.atendimento = atendimento
        self.instance.exame = exame
        self.instance.estabelecimento_id = estabelecimento_id
        self.instance.responsavel = responsavel

        self.fields['tipo'].queryset = TipoAgendamento.objects.filter(
            status='A', exige_exame_solicitado=True).order_by('descricao')
        tipo_id = self.data.get('tipo') if self.is_bound else None
        if not tipo_id:
            tipo_id = getattr(self.initial.get('tipo'), 'pk', None)
        try:
            tipo = self.fields['tipo'].queryset.filter(
                pk=int(tipo_id)).first()
        except (TypeError, ValueError):
            tipo = None

        self.fields['local'].queryset = _locais_compativeis(
            estabelecimento_id,
            externo=tipo.externo if tipo else None)
        self.fields['data_hora'].input_formats = ['%Y-%m-%dT%H:%M']

    def clean(self):
        dados = super().clean()
        tipo = dados.get('tipo')
        exame = self.instance.exame
        if tipo and not tipo.exige_exame_solicitado:
            self.add_error(
                'tipo',
                'Selecione um tipo de agendamento que exija exame solicitado.')
        if exame and AgendaPaciente.objects.filter(
                exame=exame, status='A').exclude(pk=self.instance.pk).exists():
            raise ValidationError(
                'Este exame já possui um agendamento ativo. Consulte a data e '
                'o local na lista de exames.')
        return dados
