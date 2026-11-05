"""`ClassificacaoPagamento` → `ClassePagamento` (e `classificacao_pagamento`
→ `classe_pagamento`).

RENOMEAÇÃO LITERAL (sem alias, sem tabela nova): o model mantém
`db_table = 'admin_pagamentos_classificacaopagamento'`, então a tabela NÃO
muda — só as COLUNAS de FK nos três modelos do fluxo. Assim os dados
existentes (acordos, pré-pagamentos e pagamentos já gravados) continuam
apontando para a mesma linha, sem cópia e sem janela de inconsistência.

Ordem: primeiro o `db_table`/rename de colunas (são operations de schema
reversíveis), depois só o estado do model.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('admin_pagamentos', '0007_remove_classificacao_fornecedor_acordo'),
    ]

    operations = [
        # NOME DO MODEL (histórico de migrations): sem isto o estado seguinte
        # não conhece `classepagamento` e as FKs abaixo não resolvem. A TABELA
        # NÃO muda — `RenameModel` + `db_table` explícito no model fazem o
        # Django manter `admin_pagamentos_classificacaopagamento`.
        migrations.RenameModel(
            old_name='classificacaopagamento',
            new_name='classepagamento',
        ),
        migrations.AlterModelTable(
            name='classepagamento',
            table='admin_pagamentos_classificacaopagamento',
        ),
        migrations.RenameField(
            model_name='acordopagamento',
            old_name='classificacao_pagamento',
            new_name='classe_pagamento',
        ),
        migrations.RenameField(
            model_name='prepagamento',
            old_name='classificacao_pagamento',
            new_name='classe_pagamento',
        ),
        # `Pagamento` herda de `PrePagamento` (multitable): a coluna vive na
        # tabela PAI, então não há FK própria para renomear aqui.
        migrations.AlterField(
            model_name='acordopagamento',
            name='classe_pagamento',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to='admin_pagamentos.classepagamento',
                verbose_name='Classe Pagamento'),
        ),
        migrations.AlterField(
            model_name='prepagamento',
            name='classe_pagamento',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to='admin_pagamentos.classepagamento',
                verbose_name='Classe Pagamento'),
        ),
        migrations.AlterModelOptions(
            name='classepagamento',
            options={'verbose_name': 'Classe Pagamento',
                     'verbose_name_plural': '2. Classes Pagamentos'},
        ),
    ]
