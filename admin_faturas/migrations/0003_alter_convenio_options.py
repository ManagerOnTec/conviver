from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('admin_faturas', '0002_baixafatura_herda_fatura'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='convenio',
            options={'ordering': ['-pk'], 'verbose_name': 'Convênio',
                     'verbose_name_plural': '1. Convênios/Contratos'},
        ),
    ]
