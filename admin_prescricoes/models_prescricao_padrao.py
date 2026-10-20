"""
Modelos de PRESCRIÇÃO PADRÃO (templates de prescrição).

Este módulo vive em `admin_prescricoes` (administração de prescrição) e é separado de
`models.py` apenas para manter a funcionalidade isolada — assim, junto com
`forms_prescricao_padrao.py`, `views_prescricao_padrao.py` e
`admin_prescricao_padrao.py`, pode ser removido por completo pelo rollback sem tocar
na lógica já existente de prescrição do paciente.

Conceito
--------
`PrescricaoPadrao` é o cabeçalho do modelo (nome, descrição, liberação por profissional
ou profissão) e `ProdutoPrescricaoPadrao` são os itens do modelo — os mesmos campos de um
item de `ProdutoPrescricao` (produto, intervalo, horário de início, se necessário, dose
única, observação), porém SEM vínculo com atendimento/prescrição do paciente.

Ao cadastrar uma prescrição no prontuário, o profissional abre um modal (ver
static/js/prescricao_padrao_modal.js) que lista os modelos que ele pode usar, de acordo
com `ParametrosPrescricao` (profissional ou profissão), e os itens são inseridos no
formset da prescrição que está sendo criada.

Para remover esta funcionalidade por completo use:
    bash .rollback/2026-10-20_prescricao_padrao/rollback.sh
"""
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from admin_cadastros.models import Estabelecimento
from admin_cadastros_assistenciais.models import Profissao
from admin_estoques.models import Produto
from dominios.choices import status_choices

from .models import InicioPlanoTerapeutico, IntervaloHoras


class BaseModelPrescricaoPadrao(models.Model):
    """Base com auditoria + status, no mesmo formato de admin_prescricoes.BaseModelPrescricao."""

    dt_registro = models.DateTimeField(
        default=timezone.now, verbose_name='Dt.Registro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='%(class)s_registro_padrao',
        verbose_name='Us.Registro', null=True, blank=True)
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='%(class)s_atualizacao_padrao',
        null=True, blank=True, verbose_name='Us.Atualização')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A')

    class Meta:
        abstract = True
        ordering = ['-pk']


class PrescricaoPadrao(BaseModelPrescricaoPadrao):
    """Cabeçalho do modelo de prescrição (o "receituário padrão" do paciente/setor)."""

    descricao = models.CharField(
        max_length=120, verbose_name='Descrição',
        help_text='Ex.: Prescrição padrão — Hipertensão / Pós-operatório / Idoso.')
    observacao = models.CharField(
        max_length=255, blank=True, null=True, verbose_name='Observação',
        help_text='Texto livre exibido no modal para orientar o profissional.')

    profissional = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, blank=True,
        related_name='prescricoes_padrao', verbose_name='Profissional liberado',
        help_text='Se preenchido, apenas este profissional pode usar o modelo.')
    profissao = models.ForeignKey(
        Profissao, on_delete=models.PROTECT, null=True, blank=True,
        related_name='prescricoes_padrao', verbose_name='Profissão liberada',
        help_text='Se preenchido, qualquer profissional desta profissão pode usar o modelo.')

    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT, verbose_name='Estabelecimento')

    class Meta(BaseModelPrescricaoPadrao.Meta):
        verbose_name = 'Prescrição Padrão'
        verbose_name_plural = '5. Prescrições Padrão'

    def __str__(self):
        return self.descricao

    @property
    def liberacao_resumida(self):
        if self.profissional_id:
            return f'Profissional: {self.profissional}'
        if self.profissao_id:
            return f'Profissão: {self.profissao}'
        return 'Todos os profissionais com parâmetro de prescrição'

    def pode_ser_usada_por(self, user, estabelecimento_id=None):
        """Regra de liberação do modelo (independente de ParametrosPrescricao).

        - modelo sem profissional/profissão: qualquer profissional com parâmetro de prescrição;
        - modelo com profissional: somente ele (ou superusuário);
        - modelo com profissão: qualquer profissional daquela profissão.
        """
        if self.status != 'A':
            return False
        if estabelecimento_id and str(self.estabelecimento_id) != str(estabelecimento_id):
            return False
        if not self.profissional_id and not self.profissao_id:
            return True
        if getattr(user, 'is_superuser', False):
            return True
        if self.profissional_id and self.profissional_id == user.id:
            return True
        if self.profissao_id:
            from admin_cadastros_assistenciais.models import CadastroProfissional
            return CadastroProfissional.objects.filter(
                profissional=user, profissao_id=self.profissao_id, status='A').exists()
        return False


class ProdutoPrescricaoPadrao(BaseModelPrescricaoPadrao):
    """Item do modelo de prescrição — espelha os campos de ProdutoPrescricao."""

    prescricao_padrao = models.ForeignKey(
        PrescricaoPadrao, related_name='produtos', on_delete=models.CASCADE,
        verbose_name='Prescrição Padrão')
    produto = models.ForeignKey(
        Produto, on_delete=models.PROTECT, verbose_name='Produto')
    intervalo_horas = models.ForeignKey(
        IntervaloHoras, on_delete=models.PROTECT, verbose_name='Intervalos')
    se_necessario = models.BooleanField(
        default=False, verbose_name='Se necessário?')
    dose_unica = models.BooleanField(
        default=False, verbose_name='Dose Única?',
        help_text='Marque se o medicamento for administrado apenas uma vez.')
    observacao = models.CharField(
        blank=True, null=True, max_length=11, verbose_name='Observações gerais')
    hora_inicio_produto = models.ForeignKey(
        InicioPlanoTerapeutico, on_delete=models.PROTECT, verbose_name='Hora de Início',
        related_name='hora_inicio_produto_padrao')
    ordem = models.PositiveIntegerField(
        default=0, verbose_name='Ordem', help_text='Ordem de exibição/inserção do item.')

    class Meta(BaseModelPrescricaoPadrao.Meta):
        verbose_name = 'Produto da Prescrição Padrão'
        verbose_name_plural = 'Produtos da Prescrição Padrão'
        ordering = ['ordem', 'pk']

    def __str__(self):
        return f'{self.produto.descricao} ({self.prescricao_padrao.descricao})'


class PrescricaoPadraoUtilizacao(models.Model):
    """Auditoria: registra quando um profissional inseriu um modelo de prescrição.

    A prescrição em si continua sendo gravada nas tabelas existentes (Prescricao /
    ProdutoPrescricao); este registro serve apenas para rastreabilidade do modelo
    utilizado, sem interferir na lógica de prescrição.
    """

    prescricao_padrao = models.ForeignKey(
        PrescricaoPadrao, on_delete=models.PROTECT, verbose_name='Prescrição Padrão',
        related_name='utilizacoes')
    prescricao = models.ForeignKey(
        'prontuarios.Prescricao', on_delete=models.CASCADE, verbose_name='Prescrição',
        related_name='prescricoes_padrao_utilizadas')
    atendimento = models.ForeignKey(
        'atendimentos.Atendimento', on_delete=models.PROTECT, verbose_name='Atendimento')
    profissional = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, blank=True, verbose_name='Profissional')
    dt_registro = models.DateTimeField(
        default=timezone.now, verbose_name='Dt.Registro')

    class Meta:
        verbose_name = 'Utilização de Prescrição Padrão'
        verbose_name_plural = 'Utilizações de Prescrição Padrão'
        ordering = ['-pk']
        constraints = [
            models.UniqueConstraint(
                fields=['prescricao_padrao', 'prescricao'],
                name='unique_prescricao_padrao_por_prescricao'),
        ]

    def __str__(self):
        return f'{self.prescricao_padrao} -> Prescrição {self.prescricao_id}'


def registrar_uso_prescricao_padrao(prescricao, post_data, prefix, user):
    """Cria os registros de auditoria a partir dos itens marcados pelo modal.

    O modal envia, para cada item inserido, um hidden
    ``<prefix>-<index>-item_padrao_id`` com o id do `ProdutoPrescricaoPadrao`.
    """
    ids = set()
    for chave in (post_data or {}).keys():
        if not chave.endswith('-item_padrao_id'):
            continue
        if prefix and not chave.startswith(f'{prefix}-'):
            continue
        valor = post_data.get(chave)
        if not valor:
            continue
        try:
            ids.add(int(valor))
        except (TypeError, ValueError):
            continue

    if not ids or prescricao is None or not prescricao.pk:
        return []

    ids_padroes = set(
        ProdutoPrescricaoPadrao.objects.filter(id__in=ids)
        .values_list('prescricao_padrao_id', flat=True)
    )
    utilizacoes = []
    for padrao_id in ids_padroes:
        utilizacao, _ = PrescricaoPadraoUtilizacao.objects.get_or_create(
            prescricao_padrao_id=padrao_id,
            prescricao=prescricao,
            defaults={
                'atendimento': prescricao.atendimento,
                'profissional': user if getattr(user, 'pk', None) else None,
            },
        )
        utilizacoes.append(utilizacao)
    return utilizacoes
