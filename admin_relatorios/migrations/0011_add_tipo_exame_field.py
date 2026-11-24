from django.db import migrations, models
import django.db.models.deletion
class Migration(migrations.Migration):
    dependencies = [
        ('admin_exames', '0002_tipoexame_cor_iniciais'),
        ('admin_relatorios', '0010_tipo_exame_report_choice'),
    ]

    operations = [
        migrations.AddField(
            model_name='gerenciadorrelatoriopersonalizado',
            name='tipo_exame',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='admin_exames.tipoexame', verbose_name='Tipo de Exame'),
        ),
    ]
