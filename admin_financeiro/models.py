from django.db import models
from django.db.models import Sum
from decimal import Decimal
from django.utils import timezone
from django.conf import settings
from admin_pagamentos.models import Pagamento, User
from admin_cadastros_financeiros.models import Conta, TransacaoFinanceira
from django.core.exceptions import ValidationError
from admin_cadastros.models import Estabelecimento
from dominios.choices import status_choices

class ControleBancario(models.Model):

    conta = models.ForeignKey(Conta, on_delete=models.PROTECT)
    us_registro = models.ForeignKey(
        User, related_name='uscontbanc_registro', on_delete=models.PROTECT)
    dt_registro = models.DateTimeField(default=timezone.now, editable=False)
    us_atualizacao = models.ForeignKey(
        User, related_name='uscontbanc_atualizacao', on_delete=models.PROTECT, blank=True, null=True)
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None,  verbose_name='Dt.Atualização')
    estabelecimento = models.ForeignKey(Estabelecimento, on_delete=models.PROTECT)

    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status')

    def __str__(self):
        return f"{self.conta}"

    class Meta:
        verbose_name = 'Controle Bancário'
        verbose_name_plural = '1. Controles Bancários'



class CompetenciaBancaria(models.Model):
    controle_bancario = models.ForeignKey(ControleBancario, on_delete=models.PROTECT)
    descricao = models.CharField(max_length=100, help_text='Utilize uma descrição, como exemplo = JANEIRO/2024')
    dt_abertura_competencia = models.DateField()
    dt_fechamento_competencia = models.DateField(blank=True, null=True)
    saldo_inicial = models.DecimalField(max_digits=12, decimal_places=2)
    saldo_anterior = models.DecimalField(max_digits=12, decimal_places=2)
    saldo_atual = models.DecimalField(max_digits=12, decimal_places=2)
    observacao = models.CharField(max_length=100, blank=True, null=True)

    us_registro = models.ForeignKey(
        User, related_name='ussaldo_registro', on_delete=models.PROTECT)
    dt_registro = models.DateTimeField(default=timezone.now, editable=False)
    us_atualizacao = models.ForeignKey(
        User, related_name='ussaldo_atualizacao', on_delete=models.PROTECT, blank=True, null=True)
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None,  verbose_name='Dt.Atualização')
    estabelecimento = models.ForeignKey(Estabelecimento, on_delete=models.PROTECT)

    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status')
    
    # ------------------------------------------------------------------
    # SALDOS: recalculados a partir dos MOVIMENTOS BANCÁRIOS da competência
    # (entradas − saídas) sempre que um movimento é salvo/excluído.
    # ------------------------------------------------------------------
    def recalcular_saldos(self):
        """saldo_atual = saldo_anterior + Σ entradas − Σ saídas."""
        agg = self.movimentobancario_set.aggregate(
            entradas=Sum('valor_entrada'), saidas=Sum('valor_saida'))
        self.saldo_atual = (self.saldo_anterior or 0) \
            + (agg['entradas'] or 0) - (agg['saidas'] or 0)
        self.save(update_fields=['saldo_atual'])

    @property
    def total_entradas(self):
        return self.movimentobancario_set.aggregate(
            s=Sum('valor_entrada'))['s'] or 0

    @property
    def total_saidas(self):
        return self.movimentobancario_set.aggregate(
            s=Sum('valor_saida'))['s'] or 0

    @property
    def pode_fechar(self):
        """Pode fechar? Existe conciliação FINALIZADA e sem divergência."""
        conc = getattr(self, 'conciliacao', None)
        return bool(conc and conc.finalizada
                    and abs(conc.divergencia) < Decimal('0.01'))

    # ------------------------------------------------------------------
    # CONTROLE DE PERÍODO e SALDO HERDADO
    # ------------------------------------------------------------------
    @property
    def fechada(self):
        return self.dt_fechamento_competencia is not None

    def validar_periodo(self, dt):
        """`dt` pertence ao período da competência? (abertura..hoje/fechamento)"""
        if dt is None:
            return True
        if self.dt_abertura_competencia and dt < self.dt_abertura_competencia:
            return False
        limite = self.dt_fechamento_competencia or timezone.localdate()
        return dt <= limite

    def anexar_saldo_anterior(self):
        """Herda o saldo da última competência FECHADA do mesmo banco.

        Evita digitar o saldo anterior manualmente e o erro de "saldo
        inicial" divergente do extrato. Retorna um aviso quando o valor
        informado no formulário difere do herdado.
        """
        anterior = CompetenciaBancaria.objects.filter(
            controle_bancario_id=self.controle_bancario_id,
            dt_fechamento_competencia__isnull=False,
        ).exclude(pk=self.pk).order_by('-dt_fechamento_competencia').first()
        if anterior is None:
            return None
        if self.saldo_anterior in (None, 0):
            self.saldo_anterior = anterior.saldo_atual
            return None
        if abs((self.saldo_anterior or 0) - (anterior.saldo_atual or 0)) \
                >= Decimal('0.01'):
            return ('O saldo anterior informado (R$ %s) difere do saldo final '
                    'da competência anterior "%s" (R$ %s).'
                    % (self.saldo_anterior, anterior.descricao,
                       anterior.saldo_atual))
        return None

    def fechar(self, user, dt_fechamento=None):
        """Fecha a competência (dt_fechamento) — exige conciliação ok."""
        conc = getattr(self, 'conciliacao', None)
        if conc:
            conc.refresh_from_db()  # validações anteriores podem ter alterado
            if not conc.finalizada or abs(conc.divergencia) >= Decimal('0.01'):
                raise ValueError(
                    'Conciliação bancária pendente ou com divergência de '
                    f'R$ {conc.divergencia}: importe o extrato e conclua a '
                    'conciliação antes de fechar.')
        else:
            raise ValueError(
                'Nenhum extrato importado/conciliado para esta competência: '
                'importe o extrato e conclua a conciliação antes de fechar.')
        self.dt_fechamento_competencia = dt_fechamento or timezone.localdate()
        self.us_atualizacao = user
        self.dt_atualizacao = timezone.now()
        self.save(update_fields=['dt_fechamento_competencia',
                                 'us_atualizacao', 'dt_atualizacao'])

    class Meta:
        verbose_name = 'Competência Bancária'
        verbose_name_plural = '2. Competências Bancárias'


    def __str__(self):
        abertura_formatada = self.dt_abertura_competencia.strftime('%d/%m/%Y')
        if self.dt_fechamento_competencia:
            fechamento_formatado = self.dt_fechamento_competencia.strftime('%d/%m/%Y')
            return f"{self.controle_bancario} - Competência Bancária - {self.descricao} - Abertura: {abertura_formatada} - Fechamento: {fechamento_formatado} - {self.estabelecimento}"
        else:
            return f"{self.controle_bancario} - Competência Bancária - {self.descricao} - Abertura: {abertura_formatada} - Fechamento: Em aberto - {self.estabelecimento}"


#########################################################################
#########################################################################
class MovimentoBancario(models.Model):

    competencia_bancaria = models.ForeignKey(CompetenciaBancaria, on_delete=models.PROTECT, verbose_name='Competência (Aberta)')


    transacao_financeira = models.ForeignKey(
        TransacaoFinanceira, on_delete=models.PROTECT, verbose_name='Transação Financeira')
    
    valor_entrada = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Valor E', blank=True, null=True)
    
    valor_saida = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Valor S', blank=True, null=True)

    # Origem/descrição livre do movimento. Em lançamentos de BAIXA é
    # preenchido automaticamente (baixa/fatura/empacotadas); em lançamentos
    # MANUAIS o usuário descreve — e o admin prefixa "Lançamento manual".
    # Pode ser NEGATIVO em casos de AJUSTE (estorno/correção): aqui não há
    # restrição de sinal — a regra de não-negatividade vale para o SALDO DA
    # FATURA (validador da baixa), não para o movimento bancário.
    observacao = models.CharField(
        max_length=255, blank=True, null=True, verbose_name='Observação',
        help_text='Descrição livre. Em ajustes, indique o motivo (o valor '
                  'pode ser negativo em casos de ajuste/estorno).')

    # Data em que o valor ENTROU/SAIU efetivamente no banco (pode divergir
    # do registro): base da conciliação com o extrato.
    dt_movimento = models.DateField(
        default=timezone.localdate, verbose_name='Dt. Movimento')

    # Par de uma TRANSFERÊNCIA CAIXA ⇄ BANCO (depósito/saque): o movimento do
    # caixa e o do banco compartilham o mesmo ID de transferência.
    transferencia_id = models.CharField(
        max_length=36, blank=True, null=True, editable=False,
        verbose_name='ID da transferência', db_index=True)

    # SAQUE lançado a partir do BANCO: informa de qual CAIXA entra o dinheiro
    # (a entrada no caixa é gerada automaticamente).
    competencia_caixa = models.ForeignKey(
        'admin_tesouraria.CompetenciaCaixa', on_delete=models.PROTECT,
        blank=True, null=True, related_name='movimentos_banco_saque',
        verbose_name='Caixa de destino (saque)',
        help_text='Saque: o dinheiro sai do banco e entra neste caixa '
                  '(competência de caixa aberta).')
    
 
    us_registro = models.ForeignKey(
        User, related_name='movimento_registro', on_delete=models.PROTECT)
    dt_registro = models.DateTimeField(default=timezone.now, editable=False)
    us_atualizacao = models.ForeignKey(
        User, related_name='movimento_atualizacao', on_delete=models.PROTECT, blank=True, null=True)
    dt_atualizacao = models.DateTimeField(
        blank=True, null=True, default=None,  verbose_name='Dt.Atualização')
    estabelecimento = models.ForeignKey(Estabelecimento, on_delete=models.PROTECT)

    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status')

    # Baixa de origem deste movimento (quando a entrada vem de uma baixa de
    # fatura): mostra a baixa, a fatura dela e as baixas empacotadas.
    baixa_fatura = models.ForeignKey(
        'admin_faturas.BaixaFatura', on_delete=models.PROTECT, blank=True,
        null=True, related_name='movimentos_bancarios',
        verbose_name='Baixa de Fatura')

    # Baixa de PAGAMENTO que gerou a saída (contas a pagar).
    baixa_pagamento = models.ForeignKey(
        'admin_pagamentos.BaixaPagamento', on_delete=models.PROTECT,
        blank=True, null=True, related_name='movimentos_bancarios',
        verbose_name='Baixa de Pagamento')

    # ORIGEM: descrição de onde veio o valor. Em movimentos de baixa é
    # preenchido automaticamente (baixa/fatura/empacotadas); em lançamentos
    # MANUAIS o usuário escreve — e o sistema prefixa "Lançamento manual".
    origem = models.CharField(
        max_length=255, blank=True, null=True, verbose_name='Origem')

    class Meta:
        verbose_name = "Movimento Bancário"
        verbose_name_plural = "3. Movimentos Bancários"

    # Exibição da ORIGEM do valor: a baixa + fatura dela + baixas empacotadas
    # (movimentos automáticos) ou a observação do usuário (lançamento manual,
    # que o admin prefixa com "Lançamento manual").
    def baixa_origem_display(self):
        if self.baixa_fatura_id is None:
            # Lançamento MANUAL: mostra a observação do usuário.
            return self.observacao or '-'
        def _fatura_pk(b):
            # O alias em memória pode estar vazio (instância carregada do
            # banco): o `do_bd` lê o M2M.
            f = b.fatura_baixada_do_bd()
            return f.pk if f else None
        b = self.baixa_fatura
        partes = [f'Baixa #{b.pk} (fatura {_fatura_pk(b) or "?"})']
        empacotadas = list(b.baixas_empacotadas.all())
        if empacotadas:
            partes.append('empacotadas: ' + ', '.join(
                f'#{o.pk} (fatura {_fatura_pk(o) or "?"})'
                for o in empacotadas))
        return ' '.join(partes)
    baixa_origem_display.short_description = 'Origem (Baixa / Fatura)'

    # ------------------------------------------------------------------
    # STATUS DA CONCILIAÇÃO do movimento (exibido na listagem)
    # ------------------------------------------------------------------
    def situacao_conciliacao(self):
        """'Conciliado' / 'Divergente' / 'Ignorado' / 'Pendente'.

        Vem da LINHA DO EXTRATO que aponta para este movimento (M2M reverso
        `linhas_extrato`). Sem linha vinculada: 'Não conciliado'."""
        linha = self.linhas_extrato.first()
        if linha is None:
            return 'Não conciliado'
        return {'C': 'Conciliado', 'I': 'Ignorado',
                'P': 'Pendente'}.get(linha.status, 'Pendente')

    @property
    def conciliado(self):
        return self.situacao_conciliacao() == 'Conciliado'

    def _validar_competencia(self):
        """Competência obrigatória, ABERTA e com a data DENTRO do período."""
        from django.core.exceptions import ValidationError
        comp = self.competencia_bancaria
        if comp is None:
            raise ValidationError(
                {'competencia_bancaria':
                 'Competência bancária é obrigatória.'})
        if comp.dt_fechamento_competencia:
            raise ValidationError(
                {'competencia_bancaria':
                 f'A competência "{comp.descricao}" está FECHADA em '
                 f'{comp.dt_fechamento_competencia:%d/%m/%Y}: não é possível '
                 'lançar nem alterar movimentos dela. Abra uma nova '
                 'competência para o banco.'})
        if not comp.validar_periodo(self.dt_movimento):
            raise ValidationError(
                {'dt_movimento':
                 f'A data {self.dt_movimento:%d/%m/%Y} está fora do período '
                 f'da competência "{comp.descricao}" (aberta em '
                 f'{comp.dt_abertura_competencia:%d/%m/%Y}).'})

        # TRANSFERÊNCIA pelo lado do BANCO:
        #  - saque: exige o CAIXA de destino (entrada gerada nele);
        #  - depósito lançado no banco (entrada): não usa o campo de caixa.
        transacao = self.transacao_financeira
        movimento_transacao = (getattr(transacao, 'movimento', '') or '').lower()
        if self.competencia_caixa_id:
            caixa = self.competencia_caixa
            if caixa.dt_fechamento:
                raise ValidationError(
                    {'competencia_caixa':
                     f'O caixa "{caixa}" está FECHADO: a entrada do saque '
                     'não pode ser lançada nele.'})
            if not caixa.validar_periodo(self.dt_movimento):
                raise ValidationError(
                    {'competencia_caixa':
                     'A data do saque está fora do período da competência de '
                     'caixa escolhida.'})
        if movimento_transacao == 'saque' and not self.competencia_caixa_id:
            raise ValidationError(
                {'competencia_caixa':
                 'Saque do banco: informe o CAIXA que recebe o dinheiro '
                 '(competência de caixa aberta). A entrada no caixa é gerada '
                 'automaticamente.'})
        if movimento_transacao == 'deposito' and (self.valor_saida or 0) > 0:
            raise ValidationError(
                {'valor_saida':
                 'Depósito em banco é ENTRADA no banco (o dinheiro sai do '
                 'caixa).'})

    def save(self, *args, **kwargs):
        # Atribui o estabelecimento com base na competência bancária
        if self.competencia_bancaria:
            self.estabelecimento = self.competencia_bancaria.estabelecimento
        else:
            raise ValueError('Competência bancária é obrigatória.')
        if self.dt_movimento is None:
            self.dt_movimento = timezone.localdate()
        # `_automatico` = este lançamento é o PAR criado pelo caixa (depósito
        # ou saque do outro lado): não gera de volta, senão vira loop.
        automatico = bool(kwargs.pop('_automatico', False))
        self._validar_competencia()
        super().save(*args, **kwargs)
        # SALDOS da competência alimentados pelos movimentos (entradas − saídas).
        self.competencia_bancaria.recalcular_saldos()
        # SAQUE lançado no BANCO: gera a ENTRADA no caixa escolhido.
        if self.competencia_caixa_id and not automatico:
            _sincronizar_caixa_do_saque(self)

    def delete(self, *args, **kwargs):
        competencia = self.competencia_bancaria
        # Apaga o par CAIXA do saque (se houver) e recompõe o saldo dele.
        if self.transferencia_id:
            try:
                from admin_tesouraria.models import MovimentoCaixa
                pares = list(MovimentoCaixa.objects.filter(
                    transferencia_id=self.transferencia_id))
                competencias_caixa = {p.competencia_caixa for p in pares}
                for par in pares:
                    # O `delete()` do modelo recalcula o saldo do caixa.
                    par.delete()
                for comp_caixa in competencias_caixa:
                    comp_caixa.recalcular_saldos()
            except Exception:
                pass
        super().delete(*args, **kwargs)
        competencia.recalcular_saldos()

    def __str__(self):
        return f"{self.transacao_financeira} Entrada: {self.valor_entrada} Saída: {self.valor_saida}"


def _sincronizar_caixa_do_saque(movimento_banco):
    """SAQUE lançado no BANCO → cria/atualiza a ENTRADA no caixa.

    O banco é a origem do dinheiro: a saída já está nele; aqui é gerada a
    ENTRADA na competência de caixa informada, com o mesmo
    `transferencia_id` (excluir um apaga o outro).
    """
    from uuid import uuid4
    from admin_tesouraria.models import CompetenciaCaixa, MovimentoCaixa

    caixa = movimento_banco.competencia_caixa
    if caixa is None:
        return
    if not movimento_banco.transferencia_id:
        movimento_banco.transferencia_id = str(uuid4())
        MovimentoBancario.objects.filter(pk=movimento_banco.pk).update(
            transferencia_id=movimento_banco.transferencia_id)
    valor = (movimento_banco.valor_saida or movimento_banco.valor_entrada or 0)
    descricao = (f'Saque do banco ({movimento_banco.competencia_bancaria.descricao})')
    existente = MovimentoCaixa.objects.filter(
        transferencia_id=movimento_banco.transferencia_id).first()
    dados = dict(
        competencia_caixa=caixa,
        dt_movimento=movimento_banco.dt_movimento,
        tipo='E',
        origem='saque_banco',
        valor_entrada=valor,
        valor_saida=None,
        transacao_financeira=movimento_banco.transacao_financeira,
        competencia_bancaria=movimento_banco.competencia_bancaria,
        observacao=descricao[:250],
        us_registro_id=movimento_banco.us_registro_id,
        estabelecimento_id=caixa.estabelecimento_id,
        status='A',
        transferencia_id=movimento_banco.transferencia_id,
    )
    if existente is not None:
        for campo, val in dados.items():
            setattr(existente, campo, val)
        existente.save(_automatico=True)
    else:
        MovimentoCaixa(**dados).save(_automatico=True)
    caixa.recalcular_saldos()


# ===========================================================================
# CONCILIAÇÃO BANCÁRIA — importação de extrato (OFX/PDF), conferência e
# fechamento da competência.
# ===========================================================================
class ExtratoImportado(models.Model):
    """Arquivo de extrato importado (OFX ou PDF) vinculado a uma
    competência bancária — guarda o arquivo e metadados da importação."""

    ARQUIVO_CHOICES = [('ofx', 'OFX'), ('pdf', 'PDF')]

    competencia_bancaria = models.ForeignKey(
        CompetenciaBancaria, on_delete=models.PROTECT,
        related_name='extratos', verbose_name='Competência Bancária')
    arquivo = models.FileField(
        upload_to='extratos/%Y/%m/', verbose_name='Arquivo do extrato')
    tipo = models.CharField(max_length=3, choices=ARQUIVO_CHOICES)
    dt_inicio = models.DateField(null=True, blank=True,
                                 verbose_name='Início do período')
    dt_fim = models.DateField(null=True, blank=True,
                              verbose_name='Fim do período')
    saldo_final_extrato = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        verbose_name='Saldo final do extrato')
    dt_registro = models.DateTimeField(default=timezone.now, editable=False)
    us_registro = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='extratos_importados')

    class Meta:
        verbose_name = 'Extrato Importado'
        verbose_name_plural = '1. Extratos Importados'

    def __str__(self):
        return f'{self.get_tipo_display()} – {self.dt_inicio} a {self.dt_fim}'


class LinhaExtrato(models.Model):
    """Uma transação do extrato importado, aguardando conciliação."""

    STATUS = [
        ('P', 'Pendente'),
        ('C', 'Conciliada'),
        ('I', 'Ignorada'),
    ]

    extrato = models.ForeignKey(
        ExtratoImportado, on_delete=models.CASCADE, related_name='linhas')
    dt_lancamento = models.DateField(verbose_name='Data')
    valor = models.DecimalField(
        max_digits=14, decimal_places=2,
        help_text='Positivo = crédito; negativo = débito.')
    descricao = models.CharField(max_length=255)
    documento = models.CharField(max_length=60, blank=True, null=True,
                                 verbose_name='Documento/Checknum')
    fitid = models.CharField(max_length=80, blank=True, null=True,
                             verbose_name='ID único (OFX)')
    status = models.CharField(max_length=1, choices=STATUS, default='P')
    movimento_bancario = models.ForeignKey(
        MovimentoBancario, on_delete=models.SET_NULL,
        blank=True, null=True, related_name='linhas_extrato',
        verbose_name='Movimento conciliado')

    class Meta:
        verbose_name = 'Linha de Extrato'
        verbose_name_plural = '2. Linhas de Extrato'
        ordering = ['dt_lancamento', 'pk']
        unique_together = [('extrato', 'fitid')]

    def __str__(self):
        return f'{self.dt_lancamento} {self.valor:+.2f} {self.descricao[:40]}'


class ConciliacaoBancaria(models.Model):
    """Conciliação de uma competência: fecha quando TODAS as linhas dos
    extratos da competência estão conciliadas/ignoradas e o saldo confere."""

    competencia_bancaria = models.OneToOneField(
        CompetenciaBancaria, on_delete=models.PROTECT,
        related_name='conciliacao')
    dt_conciliacao = models.DateTimeField(default=timezone.now,
                                          editable=False)
    saldo_informado = models.DecimalField(
        max_digits=14, decimal_places=2, verbose_name='Saldo do extrato')
    saldo_calculado = models.DecimalField(
        max_digits=14, decimal_places=2, verbose_name='Saldo calculado',
        help_text='Saldo da competência (anterior + entradas − saídas).')
    divergencia = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        verbose_name='Divergência')
    finalizada = models.BooleanField(default=False)
    us_registro = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='conciliacoes')

    class Meta:
        verbose_name = 'Conciliação Bancária'
        # Item 4 do menu do Financeiro (depois de competências e movimentos).
        verbose_name_plural = '4. Conciliação Bancária'

    def __str__(self):
        return (f'Conciliação {self.competencia_bancaria} – '
                f'{"Finalizada" if self.finalizada else "Em andamento"}')


