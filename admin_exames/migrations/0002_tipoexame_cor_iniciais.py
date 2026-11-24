from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies = [
        ('admin_exames', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='tipoexame',
            name='cor',
            field=models.CharField(default='#FFFFFF', max_length=7, verbose_name='Cor'),
        ),
        migrations.AddField(
            model_name='tipoexame',
            name='iniciais_nome',
            field=models.BooleanField(default=False, verbose_name='Exibir iniciais do paciente no relatório'),
        ),
    ]
