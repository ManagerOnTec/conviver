"""Liga a FK `BaixaFatura.competencia_bancaria` (não pôde entrar no
`0001_initial` por causa da dependência circular com `admin_financeiro`)."""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_faturas', '0001_initial'),
        ('admin_financeiro', '0010_movimentobancario_competencia_caixa'),
    ]

    operations = [
        migrations.AddField(
            model_name='baixafatura',
            name='competencia_bancaria',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to='admin_financeiro.competenciabancaria',
                verbose_name='Competência Bancária'),
        ),
    ]
