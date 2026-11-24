from django.db import migrations, models


def preencher_fim_recorrencia(apps, schema_editor):
    AcordoPagamento = apps.get_model('admin_pagamentos', 'AcordoPagamento')
    # Acordos antigos sem data final recebem a data inicial como fim, evitando
    # que a alteração para campo obrigatório falhe e sem criar recorrências
    # futuras por suposição.
    for acordo in AcordoPagamento.objects.filter(data_fim__isnull=True).iterator():
        AcordoPagamento.objects.filter(pk=acordo.pk).update(
            data_fim=acordo.data_inicio)


class Migration(migrations.Migration):

    dependencies = [
        ('admin_pagamentos', '0014_acordopagamento_estabelecimento'),
    ]

    operations = [
        migrations.RunPython(preencher_fim_recorrencia, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='acordopagamento',
            name='data_fim',
            field=models.DateField(
                help_text='Data final obrigatória para geração das previsões.',
                verbose_name='Fim da Recorrência',
            ),
        ),
    ]
