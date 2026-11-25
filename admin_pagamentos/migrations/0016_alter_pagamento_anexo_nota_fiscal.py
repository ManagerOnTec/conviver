from django.core.validators import FileExtensionValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_pagamentos', '0015_acordopagamento_data_fim_obrigatoria'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pagamento',
            name='anexo_nota_fiscal',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to='pagamentos/notas_fiscais/',
                validators=[
                    FileExtensionValidator(
                        allowed_extensions=[
                            'pdf', 'xml', 'jpg', 'jpeg', 'png', 'peg',
                        ],
                    ),
                ],
                verbose_name='Anexo Nota Fiscal',
            ),
        ),
    ]
