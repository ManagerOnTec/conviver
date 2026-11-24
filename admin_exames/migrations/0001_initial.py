from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('admin_cadastros', '0009_empresa_tipo'),
        ('admin_cadastros_assistenciais', '0001_initial'),
    ]
    operations = [
        migrations.CreateModel(
            name='TipoExame',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', models.CharField(max_length=120, unique=True, verbose_name='Tipo de Exame')),
                ('dt_registro', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Dt. Registro')),
                ('dt_atualizacao', models.DateTimeField(blank=True, null=True, verbose_name='Dt. Atualização')),
                ('status', models.CharField(choices=[('A', 'Ativo'), ('I', 'Inativo')], default='A', max_length=1)),
                ('us_atualizacao', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='tipo_exame_atualizado_por', to=settings.AUTH_USER_MODEL)),
                ('us_registro', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='tipo_exame_criado_por', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Tipo de Exame', 'verbose_name_plural': '1. Tipos de Exames', 'ordering': ('descricao',)},
        ),
        migrations.CreateModel(
            name='ParametrosExames',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('observacoes', models.CharField(blank=True, max_length=255, null=True, verbose_name='Observações')),
                ('dt_registro', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Dt. Registro')),
                ('dt_atualizacao', models.DateTimeField(blank=True, null=True, verbose_name='Dt. Atualização')),
                ('status', models.CharField(choices=[('A', 'Ativo'), ('I', 'Inativo')], default='A', max_length=1)),
                ('estabelecimento', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='admin_cadastros.estabelecimento')),
                ('profissao', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='admin_cadastros_assistenciais.profissao', verbose_name='Profissão liberada')),
                ('profissional', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='parametros_exames_profissional', to=settings.AUTH_USER_MODEL, verbose_name='Profissional liberado')),
                ('tipo_exame_padrao', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='parametros_padrao_exames', to='admin_exames.tipoexame', verbose_name='Tipo de Exame Padrão')),
                ('tipos_exame', models.ManyToManyField(to='admin_exames.tipoexame', verbose_name='Tipos de Exames liberados')),
                ('us_atualizacao', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='parametros_exames_atualizado_por', to=settings.AUTH_USER_MODEL)),
                ('us_registro', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='parametros_exames_criado_por', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Parâmetro de Exames', 'verbose_name_plural': '2. Parâmetros de Exames', 'ordering': ('-pk',)},
        ),
    ]
