from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('admin_relatorios', '0002_gerenciadorrelatoriopersonalizado_tipo_documento_legal_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='relatorio',
            options={'verbose_name': 'Relatório Gerado', 'verbose_name_plural': '4. Relatórios Gerados'},
        ),
        migrations.AddField(
            model_name='relatorio',
            name='dt_registro',
            field=models.DateTimeField(default=django.utils.timezone.now, null=True, verbose_name='Dt.Registro'),
        ),
        migrations.AddField(
            model_name='relatorio',
            name='us_registro',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='relatorio_criado_por', to=settings.AUTH_USER_MODEL, verbose_name='Us.Registro'),
        ),
    ]
