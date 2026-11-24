from django.db import migrations, models


def preencher_anotacoes_nulas(apps, schema_editor):
    AgendaPaciente = apps.get_model('agenda_pacientes', 'AgendaPaciente')
    banco = schema_editor.connection.alias
    AgendaPaciente.objects.using(banco).filter(
        observacao__isnull=True,
    ).update(observacao='')
    AgendaPaciente.objects.using(banco).filter(
        observacao_execucao__isnull=True,
    ).update(observacao_execucao='')


class Migration(migrations.Migration):

    dependencies = [
        ('agenda_pacientes', '0005_tipoagendamento_exige_exame_solicitado_and_more'),
    ]

    operations = [
        migrations.RunPython(
            preencher_anotacoes_nulas,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='agendapaciente',
            name='observacao',
            field=models.TextField(
                error_messages={
                    'blank': 'Informe a anotação da agenda.',
                    'null': 'Informe a anotação da agenda.',
                },
                help_text='Obrigatória; anotação do agendamento (modal de '
                          'agendamento do exame).',
                verbose_name='Anotação',
            ),
        ),
        migrations.AlterField(
            model_name='agendapaciente',
            name='observacao_execucao',
            field=models.TextField(
                blank=True,
                help_text='Obrigatória quando o agendamento estiver efetuado.',
                verbose_name='Anotação da Execução',
            ),
        ),
    ]
