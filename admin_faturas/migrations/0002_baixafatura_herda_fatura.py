"""BaixaFatura passa a herdar de Fatura.

A herança é multitable: `baixafatura` ganha o parent link `fatura_ptr` (PK,
apontando para `fatura`) e os campos de Fatura/PreFatura passam a viver na
tabela herdada. Os campos que não existem em Fatura continuam na tabela da
baixa:

- `fatura_id` (antigo)  -> `fatura_baixada_id` (nova FK, a fatura baixada)
- `estabelecimento_id`  -> `estabelecimento_baixa_id`
- `us_registro_id`      -> `us_registro_baixa_id`
- `us_atualizacao_id`   -> `us_atualizacao_baixa_id`
- `id` / `status` / `dt_registro` / `dt_atualizacao` saem (viram colunas
  herdadas de `prefatura`).

IMPORTANTE (SQLite): cada AlterField de campo herdado RECRIA a tabela inteira
e recoloca `fatura_ptr_id` a partir da própria coluna antiga, que ainda está
vazia. Por isso tudo aqui é feito numa ÚNICA recriação:

1. cria a tabela nova já no formato final;
2. copia os dados preenchendo `fatura_ptr_id` e as colunas `*_baixa_id` por
   SQL, a partir das colunas antigas;
3. cria (se preciso) a linha de `prefatura`/`fatura` de onde a baixa herda,
   como cópia do estado da fatura baixada;
4. troca as tabelas e recria os índices.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

TABELA = 'admin_faturas_baixafatura'

# Colunas da tabela NOVA e de onde cada uma vem na tabela ANTIGA.
# None = preenchida depois (backfill), '' = NULL.
COLUNAS_NOVAS = [
    ('fatura_ptr_id', None),
    ('valor_baixa', 'valor_baixa'),
    ('transacao_financeira_id', 'transacao_financeira_id'),
    ('competencia_bancaria_id', 'competencia_bancaria_id'),
    ('dt_recebimento', 'dt_recebimento'),
    ('observacao', 'observacao'),
    ('fatura_baixada_id', None),
    ('estabelecimento_baixa_id', 'estabelecimento_id'),
    ('us_registro_baixa_id', 'us_registro_id'),
    ('us_atualizacao_baixa_id', 'us_atualizacao_id'),
]

INDICES = [
    ('admin_faturas_baixafatura_competencia_bancaria_id_97ea1900',
     'competencia_bancaria_id'),
    ('admin_faturas_baixafatura_transacao_financeira_id_2762b129',
     'transacao_financeira_id'),
    ('admin_faturas_baixafatura_fatura_baixada_id_a91b6693',
     'fatura_baixada_id'),
    ('admin_faturas_baixafatura_estabelecimento_baixa_id_b1e4540c',
     'estabelecimento_baixa_id'),
    ('admin_faturas_baixafatura_us_registro_baixa_id_38f58963',
     'us_registro_baixa_id'),
    ('admin_faturas_baixafatura_us_atualizacao_baixa_id_6a0c70af',
     'us_atualizacao_baixa_id'),
]

DDL_TABELA_NOVA = """
CREATE TABLE "new__admin_faturas_baixafatura" (
    "fatura_ptr_id" bigint NOT NULL PRIMARY KEY
        REFERENCES "admin_faturas_fatura" ("prefatura_ptr_id")
        DEFERRABLE INITIALLY DEFERRED,
    "valor_baixa" decimal NOT NULL,
    "transacao_financeira_id" bigint NOT NULL
        REFERENCES "admin_cadastros_financeiros_transacaofinanceira" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    "competencia_bancaria_id" bigint NULL
        REFERENCES "admin_financeiro_competenciabancaria" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    "dt_recebimento" date NOT NULL,
    "observacao" varchar(255) NULL,
    "fatura_baixada_id" bigint NOT NULL
        REFERENCES "admin_faturas_fatura" ("prefatura_ptr_id")
        DEFERRABLE INITIALLY DEFERRED,
    "estabelecimento_baixa_id" bigint NOT NULL
        REFERENCES "admin_cadastros_estabelecimento" ("id")
        DEFERRABLE INITIALLY DEFERRED,
    "us_registro_baixa_id" integer NULL
        REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
    "us_atualizacao_baixa_id" integer NULL
        REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED
)
"""

# Como as colunas da tabela nova são lidas na antiga.
ORIGEM = {
    'valor_baixa': '"valor_baixa"',
    'transacao_financeira_id': '"transacao_financeira_id"',
    'competencia_bancaria_id': '"competencia_bancaria_id"',
    'dt_recebimento': '"dt_recebimento"',
    'observacao': '"observacao"',
    # A linha herdada é criada com o MESMO id da baixa (ver baixar_copia).
    'fatura_ptr_id': '"id"',
    # fatura_baixada_id recebe o fatura_id antigo.
    'fatura_baixada_id': '"fatura_id"',
    'estabelecimento_baixa_id': '"estabelecimento_id"',
    'us_registro_baixa_id': '"us_registro_id"',
    'us_atualizacao_baixa_id': '"us_atualizacao_id"',
}


def _coluna_ou_nulo(cursor, tabela, candidatas):
    """Expressão SQL da 1ª coluna que existir em `tabela` (ou NULL).

    As colunas da fatura mudam conforme a migração em uso: numa cadeia ANTIGA
    a fatura ainda tem `id`/`fatura_id` próprios; depois da herança (e quando
    as migrações rodam de uma vez) a PK é o parent link `prefatura_ptr_id`.
    Usar a coluna errada quebra a migração, então cada passo pergunta ao banco.
    """
    cursor.execute(f'PRAGMA table_info("{tabela}")')
    existentes = {linha[1] for linha in cursor.fetchall()}
    alias = 'b' if tabela == TABELA else 'f'
    for coluna in candidatas:
        if coluna in existentes:
            return coluna, f'{alias}.{coluna}'
    return None, 'NULL'


def _fatura_pk(cursor):
    return _coluna_ou_nulo(
        cursor, 'admin_faturas_fatura', ['id', 'prefatura_ptr_id'])[0]


def _fatura_baixada(cursor):
    """Coluna da fatura baixada na tabela da baixa (nome muda na 0005)."""
    return _coluna_ou_nulo(
        cursor, TABELA, ['fatura_id', 'fatura_baixada_id'])[1]


def baixar_copia(apps, schema_editor):
    """Cria a cadeia herdada (prefatura + fatura) de cada baixa existente.

    A baixa herda de `fatura` e, portanto, a linha em `fatura`/`prefatura` com
    a mesma PK é o "retrato" da fatura no momento do recebimento. Aqui ela é
    criada como cópia do estado atual da fatura baixada.
    """
    cursor = schema_editor.connection.cursor()
    fatura_pk = _fatura_pk(cursor)
    baixa_pk = _coluna_ou_nulo(
        cursor, TABELA, ['id', 'fatura_ptr_id'])[0]
    baixada = _fatura_baixada(cursor)

    # Fatias da fatura baixada -> tabelas herdadas.
    cursor.execute("""
        INSERT INTO admin_faturas_prefatura (
            id, estabelecimento_id, dt_registro, us_registro_id,
            dt_atualizacao, us_atualizacao_id, status,
            convenio_id, cliente, nr_contrato, nr_aditivo, empenho,
            dia_envio, dias_pagamento, competencia,
            pagador_pj_id, pagador_pf_id, valor, pre_faturado, dt_vencimento
        )
        SELECT
            b.{baixa_pk}, p.estabelecimento_id, p.dt_registro, p.us_registro_id,
            p.dt_atualizacao, p.us_atualizacao_id, p.status,
            p.convenio_id, p.cliente, p.nr_contrato, p.nr_aditivo, p.empenho,
            p.dia_envio, p.dias_pagamento, p.competencia,
            p.pagador_pj_id, p.pagador_pf_id, p.valor, p.pre_faturado,
            p.dt_vencimento
        FROM admin_faturas_baixafatura b
        JOIN admin_faturas_fatura f ON f.{fatura_pk} = {baixada}
        JOIN admin_faturas_prefatura p ON p.id = f.{fatura_pk}
        WHERE NOT EXISTS (
            SELECT 1 FROM admin_faturas_prefatura x
            WHERE x.id = b.{baixa_pk}
        )
    """.format(fatura_pk=fatura_pk, baixada=baixada, baixa_pk=baixa_pk))
    cursor.execute("""
        INSERT INTO admin_faturas_fatura (
            prefatura_ptr_id, tx_retencao_nf, valor_fatura, valor_saldo,
            dt_liquidacao, descricao, nr_nota_fiscal, periodo_tratamento,
            faturado, anexo_nf
        )
        SELECT
            b.{baixa_pk}, f.tx_retencao_nf, f.valor_fatura, f.valor_saldo,
            f.dt_liquidacao, f.descricao, f.nr_nota_fiscal,
            f.periodo_tratamento, f.faturado, f.anexo_nf
        FROM admin_faturas_baixafatura b
        JOIN admin_faturas_fatura f ON f.{fatura_pk} = {baixada}
        WHERE NOT EXISTS (
            SELECT 1 FROM admin_faturas_fatura x
            WHERE x.{fatura_pk} = b.{baixa_pk}
        )
    """.format(fatura_pk=fatura_pk, baixada=baixada, baixa_pk=baixa_pk))


def herdar_fatura(apps, schema_editor):
    """Recria `baixafatura` no formato herdado preservando os dados."""
    conexao = schema_editor.connection

    baixar_copia(apps, schema_editor)

    with conexao.cursor() as cursor:
        # A tabela antiga pode NÃO ter todas as colunas previstas (ex.: uma
        # migração futura removeu uma delas). As ausentes ficam NULL.
        cursor.execute(f'PRAGMA table_info("{TABELA}")')
        existentes = {linha[1] for linha in cursor.fetchall()}

        cursor.execute(DDL_TABELA_NOVA)
        colunas = ', '.join(f'"{nome}"' for nome, _ in COLUNAS_NOVAS)
        # Colunas que, no estado atual, já foram renomeadas/removidas: o valor
        # é lido da coluna que faz o papel dela hoje (ver `_coluna_ou_nulo`).
        atuais = {
            'fatura_ptr_id': ['id', 'fatura_ptr_id'],
            'fatura_baixada_id': ['fatura_id', 'fatura_baixada_id'],
            'estabelecimento_baixa_id': ['estabelecimento_id',
                                         'estabelecimento_baixa_id'],
            'us_registro_baixa_id': ['us_registro_id', 'us_registro_baixa_id'],
            'us_atualizacao_baixa_id': ['us_atualizacao_id',
                                        'us_atualizacao_baixa_id'],
        }
        origens = ', '.join(
            f'"{_coluna_ou_nulo(cursor, TABELA, atuais[nome])[0]}"'
            if nome in atuais else
            (f'"{origem}"' if origem in existentes else 'NULL')
            for nome, origem in COLUNAS_NOVAS)
        cursor.execute(
            f'INSERT INTO "new__admin_faturas_baixafatura" ({colunas}) '
            f'SELECT {origens} FROM "{TABELA}"'
        )
        cursor.execute(f'DROP TABLE "{TABELA}"')
        cursor.execute(
            f'ALTER TABLE "new__admin_faturas_baixafatura" '
            f'RENAME TO "{TABELA}"'
        )
        for nome, coluna in INDICES:
            cursor.execute(
                f'CREATE INDEX "{nome}" ON "{TABELA}" ("{coluna}")')


def reverter_heranca(apps, schema_editor):
    """Recria `baixafatura` no formato antigo (sem a herança)."""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE "new__admin_faturas_baixafatura" (
                "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                "fatura_id" bigint NOT NULL
                    REFERENCES "admin_faturas_fatura" ("prefatura_ptr_id")
                    DEFERRABLE INITIALLY DEFERRED,
                "valor_baixa" decimal NOT NULL,
                "transacao_financeira_id" bigint NOT NULL
                    REFERENCES "admin_cadastros_financeiros_transacaofinanceira" ("id")
                    DEFERRABLE INITIALLY DEFERRED,
                "competencia_bancaria_id" bigint NULL
                    REFERENCES "admin_financeiro_competenciabancaria" ("id")
                    DEFERRABLE INITIALLY DEFERRED,
                "dt_recebimento" date NOT NULL,
                "observacao" varchar(255) NULL,
                "estabelecimento_id" bigint NOT NULL
                    REFERENCES "admin_cadastros_estabelecimento" ("id")
                    DEFERRABLE INITIALLY DEFERRED,
                "dt_registro" datetime NULL,
                "us_registro_id" integer NULL
                    REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
                "dt_atualizacao" datetime NULL,
                "us_atualizacao_id" integer NULL
                    REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
                "status" varchar(1) NOT NULL
            )
        """)
        cursor.execute("""
            INSERT INTO "new__admin_faturas_baixafatura" (
                "id", "fatura_id", "valor_baixa", "transacao_financeira_id",
                "competencia_bancaria_id", "dt_recebimento", "observacao",
                "estabelecimento_id", "dt_registro", "us_registro_id",
                "dt_atualizacao", "us_atualizacao_id", "status"
            )
            SELECT
                b.fatura_ptr_id, b.fatura_baixada_id, b.valor_baixa,
                b.transacao_financeira_id, b.competencia_bancaria_id,
                b.dt_recebimento, b.observacao, b.estabelecimento_baixa_id,
                p.dt_registro, b.us_registro_baixa_id, p.dt_atualizacao,
                b.us_atualizacao_baixa_id, p.status
            FROM "admin_faturas_baixafatura" b
            LEFT JOIN "admin_faturas_prefatura" p ON p.id = b.fatura_ptr_id
        """)
        cursor.execute(f'DROP TABLE "{TABELA}"')
        cursor.execute(
            f'ALTER TABLE "new__admin_faturas_baixafatura" '
            f'RENAME TO "{TABELA}"')
        for nome, coluna in [
            ('admin_faturas_baixafatura_fatura_id_bdf082cd', 'fatura_id'),
            ('admin_faturas_baixafatura_competencia_bancaria_id_97ea1900',
             'competencia_bancaria_id'),
            ('admin_faturas_baixafatura_estabelecimento_id_f3e66e52',
             'estabelecimento_id'),
            ('admin_faturas_baixafatura_transacao_financeira_id_2762b129',
             'transacao_financeira_id'),
            ('admin_faturas_baixafatura_us_atualizacao_id_d48f7b02',
             'us_atualizacao_id'),
            ('admin_faturas_baixafatura_us_registro_id_0298d75a',
             'us_registro_id'),
        ]:
            cursor.execute(f'CREATE INDEX "{nome}" ON "{TABELA}" ("{coluna}")')


class Migration(migrations.Migration):

    dependencies = [
        ('admin_financeiro', '0001_initial'),
        ('admin_cadastros', '0001_initial'),
        ('admin_cadastros_financeiros', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('admin_faturas', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='baixafatura',
                    name='fatura_ptr',
                    field=models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True, primary_key=True, serialize=False,
                        to='admin_faturas.fatura'),
                ),
                migrations.RemoveField(model_name='baixafatura', name='id'),
                migrations.RemoveField(model_name='baixafatura', name='status'),
                migrations.RemoveField(
                    model_name='baixafatura', name='dt_registro'),
                migrations.RemoveField(
                    model_name='baixafatura', name='dt_atualizacao'),
                migrations.RemoveField(
                    model_name='baixafatura', name='fatura'),
                migrations.RemoveField(
                    model_name='baixafatura', name='estabelecimento'),
                migrations.RemoveField(
                    model_name='baixafatura', name='us_registro'),
                migrations.RemoveField(
                    model_name='baixafatura', name='us_atualizacao'),
                migrations.AddField(
                    model_name='baixafatura',
                    name='fatura_baixada',
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='baixas', to='admin_faturas.fatura',
                        verbose_name='Fatura',
                        help_text='Fatura que está sendo baixada.'),
                ),
                migrations.AddField(
                    model_name='baixafatura',
                    name='estabelecimento_baixa',
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='estab_baixa_fatura',
                        to='admin_cadastros.estabelecimento',
                        verbose_name='Estabelecimento'),
                ),
                migrations.AddField(
                    model_name='baixafatura',
                    name='us_registro_baixa',
                    field=models.ForeignKey(
                        null=True, on_delete=django.db.models.deletion.PROTECT,
                        related_name='baixa_fat_criado_por',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Us.Registro'),
                ),
                migrations.AddField(
                    model_name='baixafatura',
                    name='us_atualizacao_baixa',
                    field=models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='baixa_fat_atualizado_por',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Us.Atualização'),
                ),
                migrations.AlterField(
                    model_name='baixafatura',
                    name='competencia_bancaria',
                    field=models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to='admin_financeiro.competenciabancaria',
                        verbose_name='Competência Bancária'),
                ),
                migrations.AlterField(
                    model_name='baixafatura',
                    name='dt_recebimento',
                    field=models.DateField(verbose_name='Data de Recebimento'),
                ),
                migrations.AlterField(
                    model_name='baixafatura',
                    name='observacao',
                    field=models.CharField(
                        blank=True, max_length=255, null=True,
                        verbose_name='Observação'),
                ),
                migrations.AlterField(
                    model_name='baixafatura',
                    name='transacao_financeira',
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to='admin_cadastros_financeiros.transacaofinanceira',
                        verbose_name='Transação Financeira'),
                ),
                migrations.AlterField(
                    model_name='baixafatura',
                    name='valor_baixa',
                    field=models.DecimalField(
                        decimal_places=2, max_digits=10,
                        verbose_name='Valor da Baixa'),
                ),
            ],
            database_operations=[
                migrations.RunPython(herdar_fatura, reverter_heranca),
            ],
        ),
    ]
