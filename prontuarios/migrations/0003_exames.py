from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion
import django.utils.timezone
import dominios.utils
class Migration(migrations.Migration):
    dependencies = [
        ('admin_exames', '0002_tipoexame_cor_iniciais'),
        ('atendimentos', '0001_initial'),
        ('admin_cadastros', '0009_empresa_tipo'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('prontuarios', '0002_alter_evolucao_evolucao'),
    ]
    operations = [
        migrations.CreateModel(
            name='Exame',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('solicitacao', models.TextField(blank=True, verbose_name='Solicitação / Indicação')),
                ('anexo_exame', models.FileField(blank=True, null=True, upload_to='anexos/exames/%Y/%m/', validators=[django.core.validators.FileExtensionValidator(['pdf', 'png', 'jpg', 'jpeg']), dominios.utils.validate_anexo_file], verbose_name='Laudo / Anexo')),
                ('dt_registro', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Dt. Registro')),
                ('dt_atualizacao', models.DateTimeField(blank=True, default=None, null=True, verbose_name='Dt. Atualização')),
                ('status', models.CharField(choices=[('A', 'Ativo'), ('I', 'Inativo')], default='A', max_length=1)),
                ('assinar', models.BooleanField(default=True, verbose_name='Assinar relatório')),
                ('atendimento', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='atendimentos.atendimento')),
                ('estabelecimento', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='admin_cadastros.estabelecimento')),
                ('tipo_exame', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='admin_exames.tipoexame', verbose_name='Tipo de Exame')),
                ('us_atualizacao', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='exame_atualizado_por', to=settings.AUTH_USER_MODEL, verbose_name='Us. Atualização')),
                ('us_registro', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='exame_criado_por', to=settings.AUTH_USER_MODEL, verbose_name='Us. Registro')),
            ],
            options={'verbose_name': 'Exame', 'verbose_name_plural': 'Exames', 'ordering': ('-dt_registro', '-pk')},
            bases=(models.Model, __import__('admin_relatorios.utils', fromlist=['RelatorioMixin']).RelatorioMixin),
        ),
        migrations.CreateModel(
            name='ResultadoExame',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_resultado', models.DateField(verbose_name='Data do Resultado')),
                ('anotacoes', models.TextField(blank=True, verbose_name='Anotações')),
                ('anexo_1', models.FileField(blank=True, null=True, upload_to='anexos/exames/%Y/%m/', validators=[django.core.validators.FileExtensionValidator(['pdf', 'png', 'jpg', 'jpeg']), dominios.utils.validate_anexo_file], verbose_name='Anexo 1')),
                ('anexo_2', models.FileField(blank=True, null=True, upload_to='anexos/exames/%Y/%m/', validators=[django.core.validators.FileExtensionValidator(['pdf', 'png', 'jpg', 'jpeg']), dominios.utils.validate_anexo_file], verbose_name='Anexo 2')),
                ('anexo_3', models.FileField(blank=True, null=True, upload_to='anexos/exames/%Y/%m/', validators=[django.core.validators.FileExtensionValidator(['pdf', 'png', 'jpg', 'jpeg']), dominios.utils.validate_anexo_file], verbose_name='Anexo 3')),
                ('dt_registro', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Dt. Registro')),
                ('dt_atualizacao', models.DateTimeField(blank=True, default=None, null=True, verbose_name='Dt. Atualização')),
                ('status', models.CharField(choices=[('A', 'Ativo'), ('I', 'Inativo')], default='A', max_length=1)),
                ('exame', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='resultados', to='prontuarios.exame')),
                ('us_atualizacao', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='resultado_exame_atualizado_por', to=settings.AUTH_USER_MODEL)),
                ('us_registro', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='resultado_exame_criado_por', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Resultado de Exame', 'verbose_name_plural': 'Resultados de Exames', 'ordering': ('-data_resultado', '-pk')},
        ),
    ]
