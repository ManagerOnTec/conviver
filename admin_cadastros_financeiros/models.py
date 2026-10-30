from django.db import models
from dominios.choices import status_choices
from admin_cadastros.models import Estabelecimento


class Banco(models.Model):
    numero_banco = models.CharField(max_length=10, unique=True)
    descricao_banco = models.CharField(max_length=100)
    observacao = models.CharField(max_length=100, blank=True, null=True)
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT, 
        help_text="Estabelecimento associado a este banco"
    )
    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status'
    )

    def __str__(self):
        return f"{self.numero_banco} - {self.descricao_banco}"

    class Meta:
        verbose_name = "Banco"
        verbose_name_plural = "1. Bancos"


class Agencia(models.Model):
    banco = models.ForeignKey(
        Banco, on_delete=models.PROTECT, related_name='agencias')
    numero_agencia = models.CharField(max_length=10)
    descricao_agencia = models.CharField(max_length=100, blank=True, null=True)
    observacao = models.CharField(max_length=100, blank=True, null=True)
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT, 
        help_text="Estabelecimento associado a esta agência"
    )
    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status'
    )

    def __str__(self):
        return f"Agência {self.numero_agencia} - {self.banco.descricao_banco}"

    class Meta:
        verbose_name = "Agência"
        verbose_name_plural = "2. Agências"


class Conta(models.Model):
    numero_conta = models.CharField(
        max_length=20, help_text='Informe com o digito e sem caracteres especiais')
    observacao = models.CharField(max_length=100, blank=True, null=True)
    agencia = models.ForeignKey(
        Agencia, on_delete=models.PROTECT, related_name='contas')
    padrao = models.BooleanField(
        blank=True, null=True, default=False, help_text='Movimentação financeira padrão do estabelecimento'
    )
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT, 
        help_text="Estabelecimento associado a esta conta"
    )
    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status'
    )

    def __str__(self):
        return f"Conta: {self.numero_conta} - Agência: {self.agencia.numero_agencia} - {self.agencia.banco.descricao_banco}"

    class Meta:
        verbose_name = "Conta"
        verbose_name_plural = "3. Contas"


class TransacaoFinanceira(models.Model):
    TIPO_CHOICES = [
        ('entrada', 'Entrada'),
        ('saida', 'Saída'),
        # TRANSFERÊNCIAS: o tipo diz o SENTIDO do dinheiro entre caixa e banco.
        ('deposito_bancario', 'Depósito Bancário'),
        ('saque_bancario', 'Saque Bancário'),
        ('nenhum', 'Não Movimenta'),
    ]

    MOVIMENTO_CHOICES = [
        ('caixa', 'Movimenta Caixa'),
        ('banco', 'Movimenta Banco'),
        # TRANSFERÊNCIAS entre caixa e banco: geram DOIS lançamentos.
        # O nome do movimento é o SENTIDO do dinheiro: depósito sai do CAIXA e
        # entra no BANCO; saque sai do BANCO e entra no CAIXA.
        ('deposito', 'Depósito Bancário (Caixa → Banco)'),
        ('saque', 'Saque Bancário (Banco → Caixa)'),
        ('nenhum', 'Não Movimenta'),
    ]

    transacao_financeira = models.CharField(max_length=80)
    tipo = models.CharField(max_length=17, choices=TIPO_CHOICES)
    movimento = models.CharField(max_length=9, choices=MOVIMENTO_CHOICES)
    estabelecimento = models.ForeignKey(
        Estabelecimento, on_delete=models.PROTECT,
        help_text="Estabelecimento associado a esta transação"
    )
    status = models.CharField(
        max_length=1, choices=status_choices, default='A', verbose_name='Status'
    )

    def __str__(self):
        return f"{self.transacao_financeira} / {self.tipo} / {self.movimento}"

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # TRANSFERÊNCIAS: o sistema gera AUTOMATICAMENTE o lançamento do outro
    # lado. O `tipo` digitado vale para o lado do MOVIMENTO escolhido.
    # ------------------------------------------------------------------
    # Onde o lançamento digitado acontece e qual é o lado automático:
    LADO_TIPADO = {
        'deposito': 'caixa',   # depósito: digita-se a SAÍDA do caixa
        'saque': 'banco',      # saque:   digita-se a SAÍDA do banco
    }
    LADO_AUTOMATICO = {
        'deposito': 'banco',   # ... e entra no banco (automático)
        'saque': 'caixa',      # ... e entra no caixa (automático)
    }
    # Tipo do lado AUTOMÁTICO (sempre o oposto: sai de um, entra no outro).
    TIPO_AUTOMATICO = {
        'deposito': 'entrada',
        'saque': 'entrada',
    }

    # Os DOIS sentidos em que a transferência pode ser registrada: começando
    # pelo caixa (depósito) ou pelo banco (saque). O `tipo` próprio da
    # transferência diz o sentido — e é ele que define os dois lançamentos.
    TIPO_ESPERADO = {
        'deposito': 'deposito_bancario',
        'saque': 'saque_bancario',
    }

    @property
    def tipo_esperado(self):
        """Tipo que a transação DEVE ter conforme o movimento.

        **Depósito Bancário** (caixa → banco): sai do caixa, entra no banco.
        **Saque Bancário** (banco → caixa): sai do banco, entra no caixa.
        O lançamento digitado é a SAÍDA do lado de origem; a ENTRADA no outro
        lado é criada automaticamente.
        """
        return self.TIPO_ESPERADO.get(self.movimento)

    @property
    def tipo_lancamento(self):
        """'entrada' / 'saida' do lado onde o lançamento é DIGITADO.

        - `saque_bancario`  → lança no BANCO como **saída** (sai do banco e
          entra no caixa);
        - `deposito_bancario` → lança no CAIXA como **saída** (sai do caixa e
          entra no banco).

        Como o lançamento digitado é SEMPRE a saída do lado de origem, o valor
        é `saida` nos dois casos. Os demais tipos devolvem o próprio `tipo`.
        """
        if self.tipo in ('deposito_bancario', 'saque_bancario'):
            return 'saida'
        return self.tipo

    @property
    def e_transferencia(self):
        return self.tipo in ('deposito_bancario', 'saque_bancario')

    def clean(self):
        from django.core.exceptions import ValidationError
        esperado = self.tipo_esperado
        if esperado and self.tipo != esperado:
            sentido = ('o dinheiro sai do CAIXA e entra no BANCO'
                       if self.movimento == 'deposito'
                       else 'o dinheiro sai do BANCO e entra no CAIXA')
            raise ValidationError({
                'tipo':
                    f'Para “{self.get_movimento_display()}” o tipo deve ser '
                    f'“{dict(self.TIPO_CHOICES)[esperado]}” — {sentido}. '
                    'O lançamento do outro lado é gerado automaticamente.'})
        if self.movimento == 'nenhum' and self.tipo != 'nenhum':
            raise ValidationError({
                'tipo': 'Transação que não movimenta deve ter tipo '
                        '“Não Movimenta”.'})
        if self.movimento in ('caixa', 'banco') and self.tipo == 'nenhum':
            raise ValidationError({
                'tipo': 'Escolha Entrada ou Saída para transação que '
                        'movimenta caixa/banco.'})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Transação Financeira"
        verbose_name_plural = "7. Transações Financeiras"
