from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies = [
        ('admin_relatorios', '0009_tipo_exame_personalizado'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gerenciadorrelatoriopersonalizado',
            name='relatorio',
            field=models.CharField(
                max_length=50,
                choices=[
                    ('evolucao', 'Evolução'), ('exame', 'Exame'),
                    ('prescricao', 'Prescrição'), ('adep', 'ADEP'),
                    ('sae', 'SAE'), ('sinais_vitais', 'Sinais Vitais'),
                    ('perdas_ganhos', 'Perdas e Ganhos'),
                    ('plano_cuidados', 'Plano de Cuidados'),
                    ('diagnostico', 'Diagnóstico'), ('oficios', 'Ofício'),
                    ('orcamentos', 'Orçamento'), ('atas', 'Ata'),
                    ('documentos_legais', 'Documentos Legais'),
                ],
            ),
        ),
    ]
