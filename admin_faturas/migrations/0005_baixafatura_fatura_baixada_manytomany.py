"""`BaixaFatura.fatura_baixada` passa de FK para ManyToMany.

Uma fatura pode ter VÁRIAS baixas (recebimentos parciais); cada baixa continua
apontando para UMA fatura (a lista do M2M tem um item).

O que muda no banco:
- a tabela intermediária do M2M (`admin_faturas_baixafatura_fatura_baixada`) é
  criada e RECEBE uma linha por baixa, com a fatura que já estava em
  `baixafatura.fatura_baixada_id`;
- a coluna `fatura_baixada_id` é removida (o vínculo passa a morar na tabela
  intermediária).

SQLite: cada operação de esquema RECRIA a tabela `baixafatura` a partir do
estado dos MODELOS (não do banco) — por isso o SQL é montado à mão aqui, em
vez de `AddField`/`RemoveField`, senão o Django já procuraria a coluna nova
(`fatura_baixada_id`) numa tabela que ainda não a tem (ou perderia o backfill).
"""
from django.db import connections, migrations, models
from django.db.migrations.loader import MigrationLoader

DEFAULT_DB_ALIAS = 'default'

TABELA = 'admin_faturas_baixafatura'
TABELA_INTERMEDIARIA = 'admin_faturas_baixafatura_fatura_baixada'
COLUNA_ANTIGA = 'fatura_baixada_id'
COLUNA_PAI = 'fatura_ptr_id'


def _pk_fatura_colunas(conexao, tabela):
    """Colunas da PK de `tabela` (ramo do banco usado nesta migração)."""
    with conexao.cursor() as cursor:
        if conexao.vendor == 'sqlite':
            cursor.execute(f'PRAGMA table_info("{tabela}")')
            return [linha[1] for linha in cursor.fetchall() if linha[5]]
    with conexao.cursor() as cursor:
        cursor.execute(f'SHOW KEYS FROM "{tabela}" WHERE Key_name = \'PRIMARY\'')
        return [linha[4] for linha in cursor.fetchall()]





def _tabela_m2m(apps, at_end=True):
    """Modelo `through` do M2M, lido do estado escolhido.

    O `apps` que o RunPython recebe é o estado ANTERIOR da migração (a FK),
    por isso, ao aplicar, o estado usado é o FINAL (esta migração). Na
    reversão é o contrário: o estado final da reversão é o anterior.
    """
    estado = MigrationLoader(
        connections[DEFAULT_DB_ALIAS]).project_state(at_end=at_end)
    BaixaFatura = estado.apps.get_model('admin_faturas', 'BaixaFatura')
    return BaixaFatura._meta.get_field('fatura_baixada').remote_field.through


def migrar_fk_para_m2m(apps, schema_editor):
    conexao = schema_editor.connection

    # 1) Tabela intermediária do M2M (schema do modelo), criada ANTES de
    #    mexer na tabela da baixa.
    schema_editor.create_model(_tabela_m2m(apps))

    # 2) Cada baixa existente passa a apontar para a fatura que já tinha.
    #    As colunas são as REAIS da tabela criada (o `through` é o modelo
    #    modelado no estado da migração, e os nomes podem ter prefixo).
    with conexao.cursor() as cursor:
        cursor.execute(f'PRAGMA table_info("{TABELA_INTERMEDIARIA}")')
        colunas_through = [linha[1] for linha in cursor.fetchall()]
    origem_id = next(c for c in colunas_through if c.endswith('_id'))
    destino_id = next(c for c in colunas_through
                      if c.endswith('_id') and c != origem_id)
    with conexao.cursor() as cursor:
        cursor.execute(
            f'INSERT INTO "{TABELA_INTERMEDIARIA}" ("{origem_id}", '
            f'"{destino_id}") SELECT "{COLUNA_PAI}", "{COLUNA_ANTIGA}" '
            f'FROM "{TABELA}" WHERE "{COLUNA_ANTIGA}" IS NOT NULL')

    # 3) Destino no formato novo: a coluna da FK antiga sai (o vínculo agora
    #    mora na tabela intermediária). No SQLite, a FK some junto, porque a
    #    recriação usa só as colunas — nada é perdido, a cópia é feita antes.
    with conexao.cursor() as cursor:
        if conexao.vendor == 'sqlite':
            _recriar_tabela_sqlite(cursor, com_coluna_fatura=False)
        else:
            cursor.execute(f'ALTER TABLE "{TABELA}" DROP COLUMN "{COLUNA_ANTIGA}"')


def _recriar_tabela_sqlite(cursor, com_coluna_fatura):
    """Recria `baixafatura` no SQLite preservando os dados e os índices."""
    cursor.execute(f'PRAGMA table_info("{TABELA}")')
    colunas = cursor.fetchall()
    cursor.execute(
        "SELECT name, sql FROM sqlite_master "
        f"WHERE type = 'index' AND tbl_name = '{TABELA}' AND sql IS NOT NULL")
    indices = cursor.fetchall()

    existentes = [c[1] for c in colunas]
    definir = {c[1]: c[2] for c in colunas}
    if com_coluna_fatura and COLUNA_ANTIGA not in definir:
        # Reversão: a coluna da FK volta a existir (com os dados recolocados
        # logo depois, a partir da tabela intermediária).
        definir[COLUNA_ANTIGA] = 'bigint NULL'
    manter = [c for c in existentes
              if com_coluna_fatura or c != COLUNA_ANTIGA]
    if com_coluna_fatura and COLUNA_ANTIGA not in manter:
        manter.append(COLUNA_ANTIGA)
    # A cópia pega só as colunas que JÁ existem na tabela atual.
    dados = [c for c in manter if c in existentes]
    definicoes = []
    for coluna in manter:
        tipo = definir[coluna]
        if coluna == COLUNA_PAI:
            tipo = 'INTEGER' if 'INT' in tipo.upper() else 'bigint'
            definicoes.append(f'"{coluna}" {tipo} NOT NULL PRIMARY KEY')
        else:
            definicoes.append(f'"{coluna}" {tipo}')

    cursor.execute(f'DROP TABLE IF EXISTS "{TABELA}__novo"')
    cursor.execute(
        f'CREATE TABLE "{TABELA}__novo" ({", ".join(definicoes)})')
    lista = ', '.join(f'"{c}"' for c in dados)
    origem = ', '.join(f'"{c}"' for c in dados)
    cursor.execute(
        f'INSERT INTO "{TABELA}__novo" ({lista}) '
        f'SELECT {origem} FROM "{TABELA}"')
    for nome, sql in indices:
        nome_novo = nome.replace(TABELA, f'{TABELA}__novo')
        sql_novo = (sql.replace(f'"{nome}"', f'"{nome_novo}"')
                       .replace(f'"{TABELA}"', f'"{TABELA}__novo"')
                       .replace(f'ON {TABELA} ', f'ON "{TABELA}__novo" '))
        # Índice de coluna removida (ex.: a própria FK antiga) não é recriado.
        if f'"{COLUNA_ANTIGA}"' in sql_novo and not com_coluna_fatura:
            continue
        cursor.execute(sql_novo)
    cursor.execute(f'DROP TABLE "{TABELA}"')
    cursor.execute(f'ALTER TABLE "{TABELA}__novo" RENAME TO "{TABELA}"')


def reverter_m2m_para_fk(apps, schema_editor):
    """Volta a FK: a fatura de cada baixa sai da tabela intermediária."""
    conexao = schema_editor.connection
    pk_baixa = _pk_fatura_colunas(conexao, TABELA)[0]
    pk_fatura = _pk_fatura_colunas(conexao, 'admin_faturas_fatura')[0]

    with conexao.cursor() as cursor:
        cursor.execute(f'PRAGMA table_info("{TABELA_INTERMEDIARIA}")')
        colunas_through = [linha[1] for linha in cursor.fetchall()]
        cursor.execute(
            f'SELECT "{colunas_through[1]}", "{colunas_through[2]}" '
            f'FROM "{TABELA_INTERMEDIARIA}" ORDER BY "{colunas_through[2]}"')
        faturas = {}
        for baixa_id, fatura_id in cursor.fetchall():
            faturas.setdefault(baixa_id, fatura_id)
        if conexao.vendor == 'sqlite':
            # Recoloca a coluna: o estado do `through` na reversão ainda é o
            # desta migração, então a recriação tem de ser manual.
            _recriar_tabela_sqlite(cursor, com_coluna_fatura=True)
        else:
            cursor.execute(
                f'ALTER TABLE "{TABELA}" ADD COLUMN "{COLUNA_ANTIGA}" bigint '
                f'NULL REFERENCES "admin_faturas_fatura" ("{pk_fatura}")')
        for baixa_id, fatura_id in faturas.items():
            cursor.execute(
                f'UPDATE "{TABELA}" SET "{COLUNA_ANTIGA}" = %s '
                f'WHERE "{pk_baixa}" = %s', [fatura_id, baixa_id])

    schema_editor.delete_model(_tabela_m2m(apps, at_end=False))


class Migration(migrations.Migration):

    dependencies = [
        ('admin_faturas', '0004_limpa_colunas_antigas_baixa'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(migrar_fk_para_m2m, reverter_m2m_para_fk),
            ],
            state_operations=[
                migrations.RemoveField(
                    model_name='baixafatura',
                    name='fatura_baixada',
                ),
                migrations.AddField(
                    model_name='baixafatura',
                    name='fatura_baixada',
                    field=models.ManyToManyField(
                        help_text='Fatura que está sendo baixada.',
                        related_name='baixas', to='admin_faturas.fatura',
                        verbose_name='Fatura'),
                ),
            ],
        ),
    ]
