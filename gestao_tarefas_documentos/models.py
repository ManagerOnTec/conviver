"""GESTÃO DE TAREFAS E DOCUMENTOS — modelos.

Documentos institucionais (CRM, COREN, alvará, licenças, POP...) com vigência,
renovação e validação, e tarefas (providências) ligadas opcionalmente a um
documento. Segue os padrões do ERP (auditoria us_registro/dt_registro,
estabelecimento da sessão, status A/I).
"""
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

from admin_cadastros.models import Estabelecimento
from dominios.choices import status_choices
from dominios.utils import validate_anexo_file

# Situação do documento, calculada a partir das datas (não é campo do BD).
SITUACOES = (
    ('vigente', 'Vigente'),
    ('proximo', 'Próximo do vencimento'),
    ('vencido', 'Vencido'),
    ('aguardando_renovacao', 'Aguardando renovação'),
    ('sem_vigencia', 'Sem vigência definida'),
)

# Extensões de anexo aceitas (mesma política dos anexos do projeto).
ANEXO_EXTENSOES = ['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx', 'xls', 'xlsx']

# Dias padrão para considerar "próximo do vencimento" (configurável).
DIAS_PROXIMO_VENCIMENTO_PADRAO = 30

TAREFA_STATUS = (
    ('P', 'Pendente'),
    ('A', 'Em andamento'),
    ('C', 'Concluída'),
    ('X', 'Cancelada'),
)

TAREFA_PRIORIDADE = (
    ('B', 'Baixa'),
    ('M', 'Média'),
    ('A', 'Alta'),
)

# Operações do histórico (o histórico nunca é apagado).
HISTORICO_OPERACOES = (
    ('criacao', 'Cadastro'),
    ('alteracao', 'Alteração'),
    ('validacao', 'Validação'),
    ('desvalidacao', 'Desvalidação'),
    ('renovacao', 'Renovação'),
    ('anexo', 'Substituição de anexo'),
    ('anotacao', 'Anotação'),
    ('situacao', 'Alteração de situação'),
)


class Tipo(models.Model):
    """Tipo de documento (CRM, COREN, alvará...), administrado pelo sistema."""

    descricao = models.CharField(max_length=100, verbose_name='Descrição')
    observacao = models.TextField(
        blank=True, null=True, verbose_name='Observação')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status')
    dt_registro = models.DateTimeField(
        default=timezone.now, editable=False, verbose_name='Dt.Cadastro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, editable=False,
        related_name='gtd_tipos_criados', verbose_name='Us.Cadastro')

    class Meta:
        verbose_name = 'Tipo de Documento'
        verbose_name_plural = '1. Tipos de Documento'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao

    def clean(self):
        descricao = (self.descricao or '').strip()
        if not descricao:
            raise ValidationError(
                {'descricao': 'Informe a descrição do tipo de documento.'})
        duplicado = Tipo.objects.filter(
            descricao__iexact=descricao, status='A').exclude(pk=self.pk)
        if duplicado.exists():
            raise ValidationError({
                'descricao': 'Já existe um tipo de documento ativo com esta '
                             'descrição.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Documento(models.Model):
    """Documento institucional com vigência, renovação e validação."""

    tipo = models.ForeignKey(
        Tipo, on_delete=models.PROTECT, related_name='documentos',
        verbose_name='Tipo', limit_choices_to={'status': 'A'})
    descricao_documento = models.CharField(
        max_length=200, blank=True, null=True, verbose_name='Descrição',
        help_text='Nome/resumo do documento (opcional).')
    anexo = models.FileField(
        upload_to='gestao_documentos/%Y/%m/', blank=True, null=True,
        verbose_name='Anexo',
        validators=[
            FileExtensionValidator(ANEXO_EXTENSOES), validate_anexo_file],
        help_text='PDF, JPG, JPEG, PNG, DOC, DOCX, XLS ou XLSX (até 5 MB).')
    vigencia_inicial = models.DateField(
        blank=True, null=True, verbose_name='Vigência Inicial')
    vigencia_final = models.DateField(
        blank=True, null=True, verbose_name='Vigência Final')
    inicio_renovacao = models.DateField(
        blank=True, null=True, verbose_name='Início da Renovação',
        help_text='A partir desta data o sistema avisa que a renovação '
                  'precisa começar.')
    anotacoes = models.TextField(
        blank=True, null=True, verbose_name='Anotações')
    validado = models.BooleanField(
        default=False, editable=False, verbose_name='Validado')
    dt_validacao = models.DateTimeField(
        blank=True, null=True, editable=False, verbose_name='Dt. Validação')
    us_validacao = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True,
        editable=False, related_name='gtd_documentos_validados',
        verbose_name='Us. Validação')
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT,
        verbose_name='Estabelecimento')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status')
    dt_registro = models.DateTimeField(
        default=timezone.now, editable=False, verbose_name='Dt.Cadastro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, editable=False,
        related_name='gtd_documentos_criados', verbose_name='Us.Cadastro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, editable=False, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True,
        editable=False, related_name='gtd_documentos_atualizados',
        verbose_name='Us.Atualização')

    class Meta:
        verbose_name = 'Documento'
        verbose_name_plural = '2. Documentos'
        ordering = ('-dt_registro', '-pk')

    def __str__(self):
        descricao = self.descricao_documento or self.tipo.descricao
        return (f'{self.tipo.descricao} — {descricao} '
                f'(venc. {self.vigencia_final or "sem vigência"})')

    # ------------------------------------------------------------------
    # Situação de vigência — calculada pelas datas (não por status manual).
    # ------------------------------------------------------------------
    @property
    def dias_proximo_vencimento(self):
        try:
            p = ParametrosGestaoDocumentos.objects.filter(
                estabelecimento=self.estabelecimento_id, status='A').first()
            if p and p.dias_proximo_vencimento:
                return p.dias_proximo_vencimento
        except Exception:
            pass
        return DIAS_PROXIMO_VENCIMENTO_PADRAO

    @property
    def situacao(self):
        """Chave da situação, calculada a partir das datas de hoje."""
        hoje = timezone.localdate()
        if self.status != 'A':
            return 'sem_vigencia'
        if self.inicio_renovacao and self.inicio_renovacao <= hoje:
            if not self.vigencia_final or self.vigencia_final >= hoje:
                return 'aguardando_renovacao'
        if not self.vigencia_final:
            return 'sem_vigencia'
        if self.vigencia_final < hoje:
            return 'vencido'
        if self.vigencia_final <= hoje + timezone.timedelta(
                days=self.dias_proximo_vencimento):
            return 'proximo'
        return 'vigente'

    @property
    def situacao_rotulo(self):
        return dict(SITUACOES).get(self.situacao, '—')

    @property
    def situacao_cor(self):
        """Verde vigente, amarelo próximo, vermelho vencido, cinza o resto."""
        return {
            'vigente': '#198754',
            'proximo': '#e0a800',
            'vencido': '#dc3545',
            'aguardando_renovacao': '#0d6efd',
            'sem_vigencia': '#6c757d',
        }.get(self.situacao, '#6c757d')

    def clean(self):
        erros = {}
        if not self.tipo_id:
            erros['tipo'] = 'Informe o tipo do documento.'
        elif self.tipo.status != 'A':
            erros['tipo'] = ('Este tipo de documento está inativo. '
                             'Selecione um tipo ativo.')
        if self.vigencia_inicial and self.vigencia_final and \
                self.vigencia_final < self.vigencia_inicial:
            erros['vigencia_final'] = (
                'A vigência final deve ser igual ou posterior à inicial.')
        if self.inicio_renovacao and self.vigencia_final and \
                self.inicio_renovacao > self.vigencia_final:
            erros['inicio_renovacao'] = (
                'O início da renovação deve ser anterior ou igual à vigência '
                'final.')
        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # Operações com histórico (view chama; tudo em transação)
    # ------------------------------------------------------------------
    def _historico(self, operacao, usuario, descricao):
        HistoricoDocumento.objects.create(
            documento=self, operacao=operacao, usuario=usuario,
            descricao=descricao)

    def validar(self, usuario, observacao=''):
        self.validado = True
        self.dt_validacao = timezone.now()
        self.us_validacao = usuario
        self.us_atualizacao = usuario
        self.dt_atualizacao = timezone.now()
        self.save(update_fields=[
            'validado', 'dt_validacao', 'us_validacao',
            'us_atualizacao', 'dt_atualizacao'])
        self._historico(
            'validacao', usuario,
            observacao or f'Documento validado por {usuario}.')

    def desvalidar(self, usuario, motivo):
        if not (motivo or '').strip():
            raise ValidationError({'motivo': 'Informe a justificativa da '
                                             'desvalidação.'})
        anterior = (
            f'Validado em {timezone.localtime(self.dt_validacao):%d/%m/%Y %H:%M} '
            f'por {self.us_validacao}' if self.dt_validacao else '—')
        self.validado = False
        self.dt_validacao = None
        self.us_validacao = None
        self.us_atualizacao = usuario
        self.dt_atualizacao = timezone.now()
        self.save(update_fields=[
            'validado', 'dt_validacao', 'us_validacao',
            'us_atualizacao', 'dt_atualizacao'])
        self._historico(
            'desvalidacao', usuario,
            f'{motivo.strip()} (validação anterior: {anterior})')

    def registrar_renovacao(self, usuario, vigencia_inicial, vigencia_final,
                            inicio_renovacao, anexo=None, observacao=''):
        self.vigencia_inicial = vigencia_inicial
        self.vigencia_final = vigencia_final
        self.inicio_renovacao = inicio_renovacao
        if anexo is not None:
            self.anexo = anexo
        self.us_atualizacao = usuario
        self.dt_atualizacao = timezone.now()
        self.full_clean()
        self.save()
        partes = (f'Renovado: vigência {vigencia_inicial or "—"} a '
                  f'{vigencia_final or "—"}; próxima renovação a partir de '
                  f'{inicio_renovacao or "—"}.')
        if observacao:
            partes += f' {observacao}'
        self._historico(
            'renovacao', usuario, partes)

    def registrar_anotacao(self, usuario, texto):
        if not (texto or '').strip():
            raise ValidationError(
                {'texto': 'Informe a anotação.'})
        anterior = (self.anotacoes or '').strip()
        self.anotacoes = (anterior + '\n' if anterior else '') + texto.strip()
        self.us_atualizacao = usuario
        self.dt_atualizacao = timezone.now()
        self.save(update_fields=['anotacoes', 'us_atualizacao',
                                 'dt_atualizacao'])
        self._historico(
            'anotacao', usuario, texto.strip())

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('gtd_documento_detalhe', args=[self.pk])


class Tarefa(models.Model):
    """Providência ligada (ou não) a um documento."""

    documento = models.ForeignKey(
        Documento, on_delete=models.PROTECT, blank=True, null=True,
        related_name='tarefas', verbose_name='Documento')
    titulo = models.CharField(max_length=200, verbose_name='Título')
    descricao = models.TextField(
        blank=True, null=True, verbose_name='Descrição')
    data_criacao = models.DateField(
        default=timezone.localdate, verbose_name='Dt. Criação')
    data_prazo = models.DateField(blank=True, null=True, verbose_name='Prazo')
    data_conclusao = models.DateField(
        blank=True, null=True, verbose_name='Dt. Conclusão')
    status = models.CharField(
        max_length=1, choices=TAREFA_STATUS, default='P',
        verbose_name='Situação')
    prioridade = models.CharField(
        max_length=1, choices=TAREFA_PRIORIDADE, default='M',
        verbose_name='Prioridade')
    anotacoes = models.TextField(blank=True, null=True, verbose_name='Anotações')
    usuario_responsavel = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True,
        related_name='gtd_tarefas_responsaveis', verbose_name='Responsável')
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT,
        verbose_name='Estabelecimento')
    dt_registro = models.DateTimeField(
        default=timezone.now, editable=False, verbose_name='Dt.Cadastro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, editable=False,
        related_name='gtd_tarefas_criadas', verbose_name='Us.Cadastro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, editable=False, verbose_name='Dt.Atualização')
    us_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True,
        editable=False, related_name='gtd_tarefas_atualizadas',
        verbose_name='Us.Atualização')

    class Meta:
        verbose_name = 'Tarefa'
        verbose_name_plural = '3. Tarefas'
        ordering = ('data_prazo', '-pk')

    def __str__(self):
        return self.titulo

    # ------------------------------------------------------------------
    @property
    def atrasada(self):
        return (self.data_prazo is not None
                and self.status in ('P', 'A')
                and self.data_prazo < timezone.localdate())

    @property
    def situacao_cor(self):
        if self.atrasada:
            return '#dc3545'
        return {'P': '#6c757d', 'A': '#e0a800',
                'C': '#198754', 'X': '#6c757d'}.get(self.status, '#6c757d')

    def clean(self):
        erros = {}
        if not (self.titulo or '').strip():
            erros['titulo'] = 'Informe o título da tarefa.'
        if self.data_conclusao and self.status != 'C':
            # Conclusão só faz sentido com status concluída.
            self.data_conclusao = None
        if self.status == 'C' and not self.data_conclusao:
            self.data_conclusao = timezone.localdate()
        if self.data_criacao and self.data_prazo and \
                self.data_prazo < self.data_criacao and \
                self.data_prazo < timezone.localdate() - timezone.timedelta(
                    days=365):
            erros['data_prazo'] = (
                'O prazo informado é muito anterior à data de criação; '
                'confira as datas.')
        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # Transições de situação (cada uma registra no histórico da tarefa)
    # ------------------------------------------------------------------
    def _historico(self, operacao, usuario, descricao):
        HistoricoTarefa.objects.create(
            tarefa=self, operacao=operacao, usuario=usuario,
            descricao=descricao)

    def _mudar_status(self, novo, usuario, operacao, descricao):
        self.status = novo
        if novo == 'C':
            self.data_conclusao = timezone.localdate()
        else:
            self.data_conclusao = None
        self.us_atualizacao = usuario
        self.dt_atualizacao = timezone.now()
        self.save(update_fields=['status', 'data_conclusao',
                                 'us_atualizacao', 'dt_atualizacao'])
        self._historico(operacao, usuario, descricao)
        return self

    def iniciar(self, usuario):
        return self._mudar_status(
            'A', usuario, 'alteracao', 'Tarefa iniciada.')

    def concluir(self, usuario, observacao=''):
        return self._mudar_status(
            'C', usuario,
            'alteracao',
            f'Tarefa concluída. {observacao}'.strip())

    def reabrir(self, usuario, motivo=''):
        return self._mudar_status(
            'P', usuario, 'alteracao',
            f'Tarefa reaberta. {motivo}'.strip())

    def cancelar(self, usuario, motivo=''):
        return self._mudar_status(
            'X', usuario, 'alteracao',
            f'Tarefa cancelada. {motivo}'.strip())

    def registrar_anotacao(self, usuario, texto):
        if not (texto or '').strip():
            raise ValidationError({'texto': 'Informe a anotação.'})
        anterior = (self.anotacoes or '').strip()
        self.anotacoes = (anterior + '\n' if anterior else '') + texto.strip()
        self.us_atualizacao = usuario
        self.dt_atualizacao = timezone.now()
        self.save(update_fields=['anotacoes', 'us_atualizacao',
                                 'dt_atualizacao'])
        self._historico('anotacao', usuario, texto.strip())


class HistoricoDocumento(models.Model):
    """Histórico do documento — NUNCA é apagado (PROTECT em cascata)."""

    documento = models.ForeignKey(
        Documento, on_delete=models.CASCADE, related_name='historico',
        verbose_name='Documento')
    operacao = models.CharField(
        max_length=20, choices=HISTORICO_OPERACOES, verbose_name='Operação')
    usuario = models.ForeignKey(
        User, on_delete=models.PROTECT, editable=False,
        related_name='gtd_historico_doc', verbose_name='Usuário')
    dt_operacao = models.DateTimeField(
        default=timezone.now, editable=False, verbose_name='Dt. Operação')
    descricao = models.TextField(verbose_name='Descrição')

    class Meta:
        verbose_name = 'Histórico do Documento'
        verbose_name_plural = '4. Histórico de Documentos'
        ordering = ('-dt_operacao',)

    def __str__(self):
        return (f'{self.get_operacao_display()} — '
                f'{timezone.localtime(self.dt_operacao):%d/%m/%Y %H:%M} — '
                f'{self.usuario}')


class HistoricoTarefa(models.Model):
    """Histórico da tarefa — NUNCA é apagado."""

    tarefa = models.ForeignKey(
        Tarefa, on_delete=models.CASCADE, related_name='historico',
        verbose_name='Tarefa')
    operacao = models.CharField(
        max_length=20, choices=HISTORICO_OPERACOES, verbose_name='Operação')
    usuario = models.ForeignKey(
        User, on_delete=models.PROTECT, editable=False,
        related_name='gtd_historico_tarefa', verbose_name='Usuário')
    dt_operacao = models.DateTimeField(
        default=timezone.now, editable=False, verbose_name='Dt. Operação')
    descricao = models.TextField(verbose_name='Descrição')

    class Meta:
        verbose_name = 'Histórico da Tarefa'
        verbose_name_plural = '5. Histórico de Tarefas'
        ordering = ('-dt_operacao',)

    def __str__(self):
        return (f'{self.get_operacao_display()} — '
                f'{timezone.localtime(self.dt_operacao):%d/%m/%Y %H:%M} — '
                f'{self.usuario}')


class ParametrosGestaoDocumentos(models.Model):
    """Liberação por usuário OU grupo (mesmo padrão de `ParametrosAgenda`).

    `pode(usuario, estabelecimento, acao)` é a ÚNICA fonte de liberação
    ('ver'/'editar'/'excluir'); superusuário sempre pode; sem parâmetro ativo
    → ninguém pode. Guarda também a janela de “próximo do vencimento”.
    """

    estabelecimento = models.OneToOneField(
        Estabelecimento, on_delete=models.CASCADE,
        verbose_name='Estabelecimento')
    dias_proximo_vencimento = models.PositiveIntegerField(
        default=DIAS_PROXIMO_VENCIMENTO_PADRAO,
        verbose_name='Dias de “próximo do vencimento”',
        help_text='Antes do fim da vigência, o documento entra em amarelo '
                  '(padrão: 30 dias).')
    usuarios_visualizacao = models.ManyToManyField(
        User, blank=True, related_name='gtd_visualizacao',
        verbose_name='Podem Visualizar')
    usuarios_edicao = models.ManyToManyField(
        User, blank=True, related_name='gtd_edicao',
        verbose_name='Podem Editar')
    usuarios_exclusao = models.ManyToManyField(
        User, blank=True, related_name='gtd_exclusao',
        verbose_name='Podem Excluir')
    grupos_visualizacao = models.ManyToManyField(
        'auth.Group', blank=True, related_name='gtd_grupo_visualizacao',
        verbose_name='Grupos que Podem Visualizar')
    grupos_edicao = models.ManyToManyField(
        'auth.Group', blank=True, related_name='gtd_grupo_edicao',
        verbose_name='Grupos que Podem Editar')
    grupos_exclusao = models.ManyToManyField(
        'auth.Group', blank=True, related_name='gtd_grupo_exclusao',
        verbose_name='Grupos que Podem Excluir')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A',
        verbose_name='Status')
    dt_registro = models.DateTimeField(
        default=timezone.now, editable=False, verbose_name='Dt.Cadastro')
    us_registro = models.ForeignKey(
        User, on_delete=models.PROTECT, editable=False,
        related_name='gtd_parametros_criados', verbose_name='Us.Cadastro')

    class Meta:
        verbose_name = 'Parâmetros da Gestão de Documentos'
        verbose_name_plural = '6. Parâmetros da Gestão de Documentos'

    def __str__(self):
        return f'Parâmetros da Gestão de Documentos - {self.estabelecimento}'

    @classmethod
    def pode(cls, usuario, estabelecimento, acao):
        if not usuario or not usuario.is_authenticated:
            return False
        if usuario.is_superuser:
            return True
        parametros = cls.objects.filter(
            estabelecimento=estabelecimento, status='A').first()
        if not parametros:
            return False
        campos = {
            'ver': ('usuarios_visualizacao', 'grupos_visualizacao'),
            'editar': ('usuarios_edicao', 'grupos_edicao'),
            'excluir': ('usuarios_exclusao', 'grupos_exclusao'),
        }.get(acao)
        if not campos:
            return False
        campo_usuarios, campo_grupos = campos
        if getattr(parametros, campo_usuarios).filter(pk=usuario.pk).exists():
            return True
        return usuario.groups.filter(
            pk__in=getattr(parametros, campo_grupos)
            .values_list('pk', flat=True)).exists()
