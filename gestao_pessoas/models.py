"""GESTÃO DE PESSOAS — modelos.

Funcionários = pessoas já cadastradas (classificação `funcionario` em
`Pessoa.classificacao_pessoa` — nada de duplicar dados pessoais). Módulo
acompanha: documentação funcional, ASO, ficha de registro, cartão-ponto,
exames periódicos, cursos obrigatórios e férias. Segue os padrões do ERP.
"""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

from admin_cadastros.models import Estabelecimento, Pessoa
from dominios.choices import status_choices
from dominios.utils import validate_anexo_file

ANEXO_EXTENSOES = ['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx', 'xls', 'xlsx']

FUNCIONARIO_SITUACAO = (
    ('A', 'Ativo'),
    ('F', 'Afastado'),
    ('D', 'Desligado'),
)

ASO_TIPO_EXAME = (
    ('admissional', 'Admissional'),
    ('periodico', 'Periódico'),
    ('retorno_trabalho', 'Retorno ao trabalho'),
    ('mudanca_riscos', 'Mudança de riscos ocupacionais'),
    ('demissional', 'Demissional'),
)

ASO_STATUS = (
    ('N', 'Não agendado'),
    ('AG', 'Agendado'),
    ('R', 'Realizado'),
    ('C', 'Cancelado'),
)

EXAME_STATUS = ASO_STATUS

FERIAS_STATUS = (
    ('P', 'Pendente'),
    ('G', 'Programada'),
    ('E', 'Em andamento'),
    ('C', 'Concluída'),
    ('X', 'Cancelada'),
)

CURSO_FUNCIONARIO_STATUS = (
    ('P', 'Pendente'),
    ('R', 'Realizado'),
    ('V', 'Vencido'),
    ('C', 'Cancelado'),
)

# Operações do histórico (nunca apagado).
HISTORICO_OPERACOES = (
    ('criacao', 'Cadastro'),
    ('alteracao', 'Alteração'),
    ('documento', 'Documento'),
    ('aso_agendamento', 'ASO — agendamento'),
    ('aso_realizacao', 'ASO — realização'),
    ('ficha', 'Ficha de registro'),
    ('cartao', 'Cartão-ponto'),
    ('periodico_agendamento', 'Periódico — agendamento'),
    ('periodico_realizacao', 'Periódico — realização'),
    ('curso', 'Curso'),
    ('ferias', 'Férias'),
    ('situacao', 'Alteração de situação'),
)


def _validar_anexo(anexo):
    """Extensão + tamanho (mesma política do ERP)."""
    if not anexo:
        return anexo
    extensao = (anexo.name.rsplit('.', 1)[-1] or '').lower()
    if extensao not in ANEXO_EXTENSOES:
        raise ValidationError(
            {'anexo': 'Extensão não permitida. Envie: ' +
                      ', '.join(ANEXO_EXTENSOES).upper() + '.'})
    validate_anexo_file(anexo)
    return anexo


class HistoricoFuncionario(models.Model):
    """Histórico do funcionário — nunca é apagado."""

    funcionario = models.ForeignKey(
        'Funcionario', on_delete=models.CASCADE, related_name='historico',
        verbose_name='Funcionário')
    operacao = models.CharField(
        max_length=25, choices=HISTORICO_OPERACOES, verbose_name='Operação')
    usuario = models.ForeignKey(
        User, on_delete=models.PROTECT, editable=False,
        related_name='gp_historico', verbose_name='Usuário')
    dt_operacao = models.DateTimeField(
        default=timezone.now, editable=False, verbose_name='Dt. Operação')
    descricao = models.TextField(verbose_name='Descrição')

    class Meta:
        verbose_name = 'Histórico do Funcionário'
        verbose_name_plural = '8. Histórico de Funcionários'
        ordering = ('-dt_operacao',)

    def __str__(self):
        return (f'{self.get_operacao_display()} — '
                f'{timezone.localtime(self.dt_operacao):%d/%m/%Y %H:%M} — '
                f'{self.usuario}')


class Funcionario(models.Model):
    """Relação funcional de uma PESSOA já cadastrada (classificação
    `funcionario`). Sem duplicar nome/CPF/telefone — tudo em `Pessoa`."""

    pessoa = models.OneToOneField(
        Pessoa, on_delete=models.PROTECT, related_name='funcionario',
        verbose_name='Pessoa', limit_choices_to={'classificacao_pessoa': 'funcionario'})
    data_admissao = models.DateField(verbose_name='Dt. Admissão')
    status_funcionario = models.CharField(
        max_length=1, choices=FUNCIONARIO_SITUACAO, default='A',
        verbose_name='Situação Funcional')
    anotacoes = models.TextField(blank=True, null=True, verbose_name='Anotações')
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT,
        verbose_name='Estabelecimento')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status')
    dt_cadastro = models.DateTimeField(
        default=timezone.now, editable=False, verbose_name='Dt.Cadastro')
    usuario_cadastro = models.ForeignKey(
        User, on_delete=models.PROTECT, editable=False,
        related_name='gp_funcionarios_criados', verbose_name='Us.Cadastro')
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, editable=False, verbose_name='Dt.Atualização')
    usuario_atualizacao = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True,
        editable=False, related_name='gp_funcionarios_atualizados',
        verbose_name='Us.Atualização')

    class Meta:
        verbose_name = 'Funcionário'
        verbose_name_plural = '1. Funcionários'
        ordering = ('pessoa__nome',)

    def __str__(self):
        return self.pessoa.nome

    @property
    def nome(self):
        return self.pessoa.nome

    # ------------------------------------------------------------------
    # Resumo por coluna da listagem (usados nas views/templates)
    # ------------------------------------------------------------------
    @property
    def documentos_qtde(self):
        return self.documentos.count()

    @property
    def aso_atual(self):
        return self.asos.filter(status__in=('AG', 'R')).order_by(
            '-pk').first()

    @property
    def aso_situacao_rotulo(self):
        aso = self.aso_atual
        if aso is None:
            return 'Não agendado'
        return (f'{aso.get_status_display()}'
                + (f' em {aso.data_agendamento:%d/%m/%Y}'
                   if aso.status == 'AG' and aso.data_agendamento else '')
                + (f' em {aso.data_realizacao:%d/%m/%Y}'
                   if aso.status == 'R' and aso.data_realizacao else ''))

    @property
    def ficha_registro(self):
        return self.fichas_registro.order_by('-pk').first()

    @property
    def cartao_ponto(self):
        return self.cartoes_ponto.order_by('-pk').first()

    @property
    def exame_periodico_atual(self):
        return self.exames_periodicos.filter(
            status__in=('AG', 'R')).order_by('-pk').first()

    @property
    def periodico_situacao_rotulo(self):
        exame = self.exame_periodico_atual
        if exame is None:
            return 'Não agendado'
        return (f'{exame.get_status_display()}'
                + (f' em {exame.data_agendamento:%d/%m/%Y}'
                   if exame.status == 'AG' and exame.data_agendamento else '')
                + (f' em {exame.data_realizacao:%d/%m/%Y}'
                   if exame.status == 'R' and exame.data_realizacao else ''))

    @property
    def cursos_pendentes_qtde(self):
        return self.cursos_funcionario.filter(status='P').count()

    @property
    def cursos_concluidos_qtde(self):
        return self.cursos_funcionario.filter(status='R').count()

    @property
    def cursos_vencidos_qtde(self):
        hoje = timezone.localdate()
        return self.cursos_funcionario.filter(
            status='R', data_validade__lt=hoje).count()

    @property
    def ferias_atual(self):
        return self.ferias.filter(
            status__in=('P', 'G', 'E')).order_by('-pk').first()

    @property
    def ferias_saldo_dias(self):
        ferias = self.ferias_atual
        if ferias is None:
            return None
        return (ferias.dias_direito or 0) - (ferias.dias_gozados or 0)

    # ------------------------------------------------------------------
    # Listas em HTML seguro (escapado) para os modais informativos
    # ------------------------------------------------------------------
    def _html_lista(self, linhas):
        from django.utils.html import escape
        if not linhas:
            return '<p class="text-muted">Nenhum registro.</p>'
        return '<ul class="list-group">' + ''.join(
            f'<li class="list-group-item">{escape(linha)}</li>'
            for linha in linhas) + '</ul>'

    @property
    def documentos_html(self):
        return self._html_lista(
            f'{d.tipo_documento} — dt. '
            f'{d.data_documento:%d/%m/%Y} — '
            + (f'<a href="{d.anexo.url}" target="_blank">{d.descricao or "abrir"}</a>'
               if d.anexo else 'sem anexo')
            for d in self.documentos_lista)

    @property
    def aso_html(self):
        return self._html_lista(
            f'{a.get_tipo_exame_display()} — {a.get_status_display()}'
            + (f' agend. {a.data_agendamento:%d/%m/%Y}'
               if a.data_agendamento else '')
            + (f' realiz. {a.data_realizacao:%d/%m/%Y}'
               if a.data_realizacao else '')
            + (f' válid. {a.data_validade:%d/%m/%Y}'
               if a.data_validade else '')
            + (f' — <a href="{a.anexo.url}" target="_blank">ver ASO</a>'
               if a.anexo else '')
            for a in self.aso_lista)

    @property
    def periodico_html(self):
        return self._html_lista(
            f'{e.get_status_display()}'
            + (f' agend. {e.data_agendamento:%d/%m/%Y}'
               if e.data_agendamento else '')
            + (f' realiz. {e.data_realizacao:%d/%m/%Y}'
               if e.data_realizacao else '')
            + (f' próximo {e.data_proximo_exame:%d/%m/%Y}'
               if e.data_proximo_exame else '')
            + (f' — <a href="{e.anexo.url}" target="_blank">ver resultado</a>'
               if e.anexo else '')
            for e in self.periodico_lista)

    @property
    def ferias_html(self):
        return self._html_lista(
            f'{f.get_status_display()} — aquisitivo '
            f'{f.periodo_aquisitivo_inicio:%d/%m/%Y} a '
            f'{f.periodo_aquisitivo_final:%d/%m/%Y}'
            + (f'; concessivo {f.periodo_concessivo_inicio:%d/%m/%Y} a '
               f'{f.periodo_concessivo_final:%d/%m/%Y}'
               if f.periodo_concessivo_final else '')
            + f'; gozados {f.dias_gozados}/{f.dias_direito}'
            + (f'; férias {f.data_inicio_ferias:%d/%m/%Y} a '
               f'{f.data_final_ferias:%d/%m/%Y}'
               if f.data_final_ferias else '')
            for f in self.ferias_lista)

    # ------------------------------------------------------------------
    def clean(self):
        erros = {}
        if not self.pessoa_id:
            erros['pessoa'] = 'Informe a pessoa do funcionário.'
        elif self.pessoa.classificacao_pessoa != 'funcionario':
            erros['pessoa'] = (
                'A pessoa precisa estar classificada como FUNCIONÁRIO no '
                'cadastro de Pessoas.')
        if self.data_admissao and self.data_admissao > timezone.localdate():
            erros['data_admissao'] = (
                'A data de admissão não pode ser futura.')
        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.full_clean()
        nova = self._state.adding
        retorno = super().save(*args, **kwargs)
        if nova:
            # Histórico de criação (a view pode acrescentar mais detalhes).
            self._historico(
                'criacao', self.usuario_cadastro,
                f'Funcionário cadastrado (admissão '
                f'{self.data_admissao:%d/%m/%Y}).')
        return retorno

    def _historico(self, operacao, usuario, descricao):
        HistoricoFuncionario.objects.create(
            funcionario=self, operacao=operacao, usuario=usuario,
            descricao=descricao)


class DocumentoFuncionario(models.Model):
    """Documento funcional (ficha, certidões, contratos...)."""

    funcionario = models.ForeignKey(
        Funcionario, on_delete=models.CASCADE, related_name='documentos',
        verbose_name='Funcionário')
    tipo_documento = models.CharField(
        max_length=100, verbose_name='Tipo de Documento')
    anexo = models.FileField(
        upload_to='gestao_pessoas/documentos/%Y/%m/', verbose_name='Anexo',
        validators=[FileExtensionValidator(ANEXO_EXTENSOES),
                    validate_anexo_file])
    data_documento = models.DateField(
        verbose_name='Dt. do Documento')
    descricao = models.CharField(
        max_length=200, blank=True, null=True, verbose_name='Descrição')
    anotacoes = models.TextField(blank=True, null=True, verbose_name='Anotações')
    dt_cadastro = models.DateTimeField(
        default=timezone.now, editable=False, verbose_name='Dt.Cadastro')
    usuario_cadastro = models.ForeignKey(
        User, on_delete=models.PROTECT, editable=False,
        related_name='gp_documentos', verbose_name='Us.Cadastro')

    class Meta:
        verbose_name = 'Documento do Funcionário'
        verbose_name_plural = '2. Documentos do Funcionário'
        ordering = ('-dt_cadastro',)

    def __str__(self):
        return f'{self.tipo_documento} — {self.funcionario}'

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class ASO(models.Model):
    """Atestado de Saúde Ocupacional (admissional, periódico, etc.).

    O histórico nunca é apagado: registrar um novo ASO NÃO apaga os
    anteriores (apenas os marca como encerrados implicitamente pela
    listagem, que mostra o mais recente).
    """

    funcionario = models.ForeignKey(
        Funcionario, on_delete=models.CASCADE, related_name='asos',
        verbose_name='Funcionário')
    tipo_exame = models.CharField(
        max_length=20, choices=ASO_TIPO_EXAME, default='periodico',
        verbose_name='Tipo de Exame')
    data_agendamento = models.DateField(
        blank=True, null=True, verbose_name='Dt. Agendamento')
    data_realizacao = models.DateField(
        blank=True, null=True, verbose_name='Dt. Realização')
    data_validade = models.DateField(
        blank=True, null=True, verbose_name='Dt. Validade',
        help_text='Quando aplicável ao tipo de exame.')
    anexo = models.FileField(
        upload_to='gestao_pessoas/aso/%Y/%m/', blank=True, null=True,
        verbose_name='Anexo (ASO)',
        validators=[FileExtensionValidator(ANEXO_EXTENSOES),
                    validate_anexo_file])
    observacoes = models.TextField(
        blank=True, null=True, verbose_name='Observações')
    status = models.CharField(
        max_length=2, choices=ASO_STATUS, default='N', verbose_name='Situação')
    dt_cadastro = models.DateTimeField(
        default=timezone.now, editable=False, verbose_name='Dt.Cadastro')
    usuario_cadastro = models.ForeignKey(
        User, on_delete=models.PROTECT, editable=False,
        related_name='gp_asos', verbose_name='Us.Cadastro')

    class Meta:
        verbose_name = 'ASO'
        verbose_name_plural = '3. ASOs'
        ordering = ('-data_agendamento', '-pk')

    def __str__(self):
        return (f'ASO {self.get_tipo_exame_display()} — {self.funcionario} '
                f'({self.get_status_display()})')

    def clean(self):
        erros = {}
        if self.status == 'AG' and not self.data_agendamento:
            erros['data_agendamento'] = (
                'Informe a data do agendamento.')
        if self.status == 'R' and not self.data_realizacao:
            erros['data_realizacao'] = (
                'Informe a data de realização do exame.')
        if self.data_realizacao and self.data_agendamento and \
                self.data_realizacao < self.data_agendamento:
            erros['data_realizacao'] = (
                'A realização não pode ser anterior ao agendamento.')
        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class FichaRegistro(models.Model):
    """Ficha de registro do funcionário (uma ativa por funcionário)."""

    funcionario = models.ForeignKey(
        Funcionario, on_delete=models.CASCADE, related_name='fichas_registro',
        verbose_name='Funcionário')
    anexo = models.FileField(
        upload_to='gestao_pessoas/fichas/%Y/%m/', blank=True, null=True,
        verbose_name='Anexo (Ficha)',
        validators=[FileExtensionValidator(ANEXO_EXTENSOES),
                    validate_anexo_file])
    data_registro = models.DateField(
        blank=True, null=True, verbose_name='Dt. do Registro')
    observacoes = models.TextField(
        blank=True, null=True, verbose_name='Observações')
    dt_cadastro = models.DateTimeField(
        default=timezone.now, editable=False, verbose_name='Dt.Cadastro')
    usuario_cadastro = models.ForeignKey(
        User, on_delete=models.PROTECT, editable=False,
        related_name='gp_fichas', verbose_name='Us.Cadastro')

    class Meta:
        verbose_name = 'Ficha de Registro'
        verbose_name_plural = '4. Fichas de Registro'
        ordering = ('-dt_cadastro',)

    def __str__(self):
        return f'Ficha de registro — {self.funcionario}'


class CartaoPonto(models.Model):
    """Cartão-ponto do funcionário."""

    funcionario = models.ForeignKey(
        Funcionario, on_delete=models.CASCADE, related_name='cartoes_ponto',
        verbose_name='Funcionário')
    numero_cartao = models.CharField(
        max_length=50, verbose_name='Nº do Cartão')
    data_inicio_vigencia = models.DateField(
        blank=True, null=True, verbose_name='Dt. Início da Vigência')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A',
        verbose_name='Status')
    observacoes = models.TextField(
        blank=True, null=True, verbose_name='Observações')

    class Meta:
        verbose_name = 'Cartão-Ponto'
        verbose_name_plural = '5. Cartões-Ponto'
        ordering = ('-pk',)

    def __str__(self):
        return f'Cartão {self.numero_cartao} — {self.funcionario}'

    def clean(self):
        if not (self.numero_cartao or '').strip():
            raise ValidationError(
                {'numero_cartao': 'Informe o número do cartão-ponto.'})
        duplicado = CartaoPonto.objects.filter(
            numero_cartao__iexact=self.numero_cartao, status='A') \
            .exclude(pk=self.pk)
        if duplicado.exists():
            raise ValidationError({
                'numero_cartao': 'Já existe um cartão-ponto ATIVO com este '
                                 'número.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class ExamePeriodico(models.Model):
    """Exame periódico (controle independente dos demais ASOs)."""

    funcionario = models.ForeignKey(
        Funcionario, on_delete=models.CASCADE,
        related_name='exames_periodicos', verbose_name='Funcionário')
    data_agendamento = models.DateField(
        blank=True, null=True, verbose_name='Dt. Agendamento')
    data_realizacao = models.DateField(
        blank=True, null=True, verbose_name='Dt. Realização')
    data_proximo_exame = models.DateField(
        blank=True, null=True, verbose_name='Dt. do Próximo Exame')
    anexo = models.FileField(
        upload_to='gestao_pessoas/periodicos/%Y/%m/', blank=True, null=True,
        verbose_name='Anexo (Resultado/ASO)',
        validators=[FileExtensionValidator(ANEXO_EXTENSOES),
                    validate_anexo_file])
    status = models.CharField(
        max_length=2, choices=EXAME_STATUS, default='N', verbose_name='Situação')
    observacoes = models.TextField(
        blank=True, null=True, verbose_name='Observações')
    dt_cadastro = models.DateTimeField(
        default=timezone.now, editable=False, verbose_name='Dt.Cadastro')
    usuario_cadastro = models.ForeignKey(
        User, on_delete=models.PROTECT, editable=False,
        related_name='gp_periodicos', verbose_name='Us.Cadastro')

    class Meta:
        verbose_name = 'Exame Periódico'
        verbose_name_plural = '6. Exames Periódicos'
        ordering = ('-data_agendamento', '-pk')

    def __str__(self):
        return f'Periódico — {self.funcionario} ({self.get_status_display()})'

    def clean(self):
        erros = {}
        if self.status == 'AG' and not self.data_agendamento:
            erros['data_agendamento'] = 'Informe a data do agendamento.'
        if self.status == 'R' and not self.data_realizacao:
            erros['data_realizacao'] = 'Informe a data de realização.'
        if self.data_realizacao and self.data_agendamento and \
                self.data_realizacao < self.data_agendamento:
            erros['data_realizacao'] = (
                'A realização não pode ser anterior ao agendamento.')
        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Curso(models.Model):
    """Curso obrigatório/treinamento (NR-32, brigada...), cadastrável."""

    nome = models.CharField(max_length=150, verbose_name='Nome')
    descricao = models.TextField(
        blank=True, null=True, verbose_name='Descrição')
    carga_horaria = models.PositiveIntegerField(
        verbose_name='Carga horária (h)')
    validade_meses = models.PositiveIntegerField(
        blank=True, null=True, verbose_name='Validade (meses)',
        help_text='Vazio = certificado sem vencimento.')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status')

    class Meta:
        verbose_name = 'Curso Obrigatório'
        verbose_name_plural = '7. Cursos Obrigatórios'
        ordering = ('nome',)

    def __str__(self):
        return self.nome

    def clean(self):
        if not (self.nome or '').strip():
            raise ValidationError({'nome': 'Informe o nome do curso.'})
        duplicado = Curso.objects.filter(
            nome__iexact=self.nome, status='A').exclude(pk=self.pk)
        if duplicado.exists():
            raise ValidationError(
                {'nome': 'Já existe um curso ativo com este nome.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class CursoFuncionario(models.Model):
    """Cursos obrigatórios do funcionário (realizados e pendentes)."""

    funcionario = models.ForeignKey(
        Funcionario, on_delete=models.CASCADE,
        related_name='cursos_funcionario', verbose_name='Funcionário')
    curso = models.ForeignKey(
        Curso, on_delete=models.PROTECT, related_name='realizacoes',
        verbose_name='Curso', limit_choices_to={'status': 'A'})
    data_realizacao = models.DateField(
        blank=True, null=True, verbose_name='Dt. Realização')
    data_validade = models.DateField(
        blank=True, null=True, verbose_name='Dt. Validade')
    anexo_certificado = models.FileField(
        upload_to='gestao_pessoas/certificados/%Y/%m/', blank=True, null=True,
        verbose_name='Certificado',
        validators=[FileExtensionValidator(ANEXO_EXTENSOES),
                    validate_anexo_file])
    status = models.CharField(
        max_length=1, choices=CURSO_FUNCIONARIO_STATUS, default='P',
        verbose_name='Situação')
    observacoes = models.TextField(
        blank=True, null=True, verbose_name='Observações')

    class Meta:
        verbose_name = 'Curso do Funcionário'
        verbose_name_plural = 'Cursos do Funcionário'
        ordering = ('data_validade', '-pk')
        constraints = [
            models.UniqueConstraint(
                fields=('funcionario', 'curso', 'data_realizacao'),
                name='curso_unico_por_data'),
        ]

    def __str__(self):
        return f'{self.curso} — {self.funcionario}'

    @property
    def vencido(self):
        return (self.status == 'R' and self.data_validade is not None
                and self.data_validade < timezone.localdate())

    @property
    def proximo_vencimento(self):
        return (self.status == 'R' and self.data_validade is not None
                and self.data_validade >= timezone.localdate()
                and self.data_validade <= timezone.localdate()
                + timezone.timedelta(days=30))

    def clean(self):
        erros = {}
        if not self.curso_id:
            erros['curso'] = 'Informe o curso.'
        if self.status == 'R' and not self.data_realizacao:
            erros['data_realizacao'] = (
                'Informe a data de realização do curso.')
        if self.status == 'R' and self.curso_id and self.curso.validade_meses \
                and self.data_realizacao and not self.data_validade:
            self.data_validade = self.data_realizacao + timezone.timedelta(
                days=30 * self.curso.validade_meses)
        if self.data_realizacao and self.data_validade and \
                self.data_validade < self.data_realizacao:
            erros['data_validade'] = (
                'A validade deve ser posterior à realização.')
        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Ferias(models.Model):
    """Períodos aquisitivos/concessivos e férias programadas/gozadas."""

    funcionario = models.ForeignKey(
        Funcionario, on_delete=models.CASCADE, related_name='ferias',
        verbose_name='Funcionário')
    periodo_aquisitivo_inicio = models.DateField(
        verbose_name='Período aquisitivo — início')
    periodo_aquisitivo_final = models.DateField(
        verbose_name='Período aquisitivo — final')
    periodo_concessivo_inicio = models.DateField(
        blank=True, null=True, verbose_name='Período concessivo — início')
    periodo_concessivo_final = models.DateField(
        blank=True, null=True, verbose_name='Período concessivo — final')
    dias_direito = models.PositiveIntegerField(
        default=30, verbose_name='Dias de direito')
    dias_gozados = models.PositiveIntegerField(
        default=0, verbose_name='Dias gozados')
    data_inicio_ferias = models.DateField(
        blank=True, null=True, verbose_name='Início das férias')
    data_final_ferias = models.DateField(
        blank=True, null=True, verbose_name='Final das férias')
    status = models.CharField(
        max_length=1, choices=FERIAS_STATUS, default='P',
        verbose_name='Situação')
    observacoes = models.TextField(
        blank=True, null=True, verbose_name='Observações')
    dt_cadastro = models.DateTimeField(
        default=timezone.now, editable=False, verbose_name='Dt.Cadastro')
    usuario_cadastro = models.ForeignKey(
        User, on_delete=models.PROTECT, editable=False,
        related_name='gp_ferias', verbose_name='Us.Cadastro')

    class Meta:
        verbose_name = 'Férias'
        verbose_name_plural = 'Férias'
        ordering = ('-periodo_aquisitivo_inicio',)

    def __str__(self):
        return (f'Férias {self.periodo_aquisitivo_inicio:%d/%m/%Y} — '
                f'{self.funcionario} ({self.get_status_display()})')

    @property
    def saldo_dias(self):
        return (self.dias_direito or 0) - (self.dias_gozados or 0)

    @property
    def concessivo_vencendo(self):
        """Período concessivo termina em ≤ 30 dias (alerta)."""
        return (self.periodo_concessivo_final is not None
                and self.status in ('P', 'G')
                and self.periodo_concessivo_final <= timezone.localdate()
                + timezone.timedelta(days=30))

    @property
    def concessivo_vencido(self):
        return (self.periodo_concessivo_final is not None
                and self.status in ('P', 'G')
                and self.periodo_concessivo_final < timezone.localdate())

    def clean(self):
        erros = {}
        if self.periodo_aquisitivo_final < self.periodo_aquisitivo_inicio:
            erros['periodo_aquisitivo_final'] = (
                'O fim do período aquisitivo deve ser posterior ao início.')
        if self.periodo_concessivo_inicio and self.periodo_concessivo_final \
                and self.periodo_concessivo_final < \
                self.periodo_concessivo_inicio:
            erros['periodo_concessivo_final'] = (
                'O fim do período concessivo deve ser posterior ao início.')
        if self.dias_gozados > self.dias_direito:
            erros['dias_gozados'] = (
                f'Os dias gozados ({self.dias_gozados}) não podem ultrapassar '
                f'os dias de direito ({self.dias_direito}).')
        if self.data_inicio_ferias and self.data_final_ferias and \
                self.data_final_ferias < self.data_inicio_ferias:
            erros['data_final_ferias'] = (
                'O final das férias deve ser posterior ao início.')
        if self.data_inicio_ferias and self.data_final_ferias:
            dias_ferias = (self.data_final_ferias - self.data_inicio_ferias
                           ).days + 1
            if dias_ferias > self.dias_direito:
                erros['data_final_ferias'] = (
                    f'As férias somam {dias_ferias} dias, mais que os '
                    f'{self.dias_direito} de direito.')
        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class ParametrosGestaoPessoas(models.Model):
    """Liberação por usuário OU grupo (mesmo padrão de `ParametrosAgenda`).

    `pode(usuario, estabelecimento, acao)` é a ÚNICA fonte
    ('ver'/'editar'/'excluir'); superusuário sempre pode; sem parâmetro ativo
    → ninguém pode.
    """

    estabelecimento = models.OneToOneField(
        Estabelecimento, on_delete=models.CASCADE,
        verbose_name='Estabelecimento')
    usuarios_visualizacao = models.ManyToManyField(
        User, blank=True, related_name='gp_visualizacao',
        verbose_name='Podem Visualizar')
    usuarios_edicao = models.ManyToManyField(
        User, blank=True, related_name='gp_edicao', verbose_name='Podem Editar')
    usuarios_exclusao = models.ManyToManyField(
        User, blank=True, related_name='gp_exclusao', verbose_name='Podem Excluir')
    grupos_visualizacao = models.ManyToManyField(
        'auth.Group', blank=True, related_name='gp_grupo_visualizacao',
        verbose_name='Grupos que Podem Visualizar')
    grupos_edicao = models.ManyToManyField(
        'auth.Group', blank=True, related_name='gp_grupo_edicao',
        verbose_name='Grupos que Podem Editar')
    grupos_exclusao = models.ManyToManyField(
        'auth.Group', blank=True, related_name='gp_grupo_exclusao',
        verbose_name='Grupos que Podem Excluir')
    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status')
    dt_cadastro = models.DateTimeField(
        default=timezone.now, editable=False, verbose_name='Dt.Cadastro')
    usuario_cadastro = models.ForeignKey(
        User, on_delete=models.PROTECT, editable=False,
        related_name='gp_parametros_criados', verbose_name='Us.Cadastro')

    class Meta:
        verbose_name = 'Parâmetros da Gestão de Pessoas'
        verbose_name_plural = '9. Parâmetros da Gestão de Pessoas'

    def __str__(self):
        return f'Parâmetros da Gestão de Pessoas - {self.estabelecimento}'

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
