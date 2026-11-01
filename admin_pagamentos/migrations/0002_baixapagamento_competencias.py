"""Liga as FKs de COMPETÊNCIA na baixa de pagamento.

Não cabem no `0001_initial` por causa da dependência circular
(`admin_financeiro` referencia `admin_pagamentos` e vice-versa).
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_pagamentos', '0001_initial'),
        ('admin_financeiro', '0010_movimentobancario_competencia_caixa'),
        ('admin_tesouraria', '0002_alter_movimentocaixa_tipo'),
    ]

    operations = [
        migrations.AddField(
            model_name='baixapagamento',
            name='competencia_bancaria',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to='admin_financeiro.competenciabancaria',
                verbose_name='Competência Bancária'),
        ),
        migrations.AddField(
            model_name='baixapagamento',
            name='competencia_caixa',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to='admin_tesouraria.competenciacaixa',
                verbose_name='Competência de Caixa'),
        ),
    ]
