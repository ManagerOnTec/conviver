"""`Empresa.tipo` — o PAPEL da empresa no sistema.

A mesma tabela `Empresa` atende três vínculos diferentes:

    fornecedor      → `Fornecedor.empresa`        (fluxo de SAÍDA)
    convenio        → `AcordoFaturamento.pagador_pj` (fluxo de ENTRADA)
    estabelecimento → `Estabelecimento.empresa`   (a própria unidade)

O campo entra com `default='convenio'` (valor neutro e o mais numeroso), e
depois o BACKFILL corrige as empresas já cadastradas deduzindo o papel pelos
vínculos existentes — sem isso, o `clean()` novo recusaria a edição de
registros antigos ("empresa é do tipo convênio" numa unidade, por exemplo).

Ordem do backfill (o mais específico primeiro):

1. empresas que já são ESTABELECIMENTO;
2. empresas que já são FORNECEDOR;
3. as demais ficam como CONVÊNIO (default).
"""
from django.db import migrations, models


def classificar_empresas(apps, schema_editor):
    Empresa = apps.get_model('admin_cadastros', 'Empresa')
    Estabelecimento = apps.get_model('admin_cadastros', 'Estabelecimento')

    # 1) ESTABELECIMENTO — vínculo direto e inequívoco.
    ids_estab = list(
        Estabelecimento.objects.filter(empresa__isnull=False)
        .values_list('empresa_id', flat=True).distinct())
    if ids_estab:
        Empresa.objects.filter(pk__in=ids_estab).update(tipo='estabelecimento')

    # 2) FORNECEDOR — depende do app de pagamentos existir.
    try:
        Fornecedor = apps.get_model('admin_pagamentos', 'Fornecedor')
        ids_forn = list(
            Fornecedor.objects.filter(empresa__isnull=False)
            .values_list('empresa_id', flat=True).distinct())
        if ids_forn:
            Empresa.objects.filter(pk__in=ids_forn).exclude(
                tipo='estabelecimento').update(tipo='fornecedor')
    except LookupError:
        pass  # app não instalado nesta migração

    # 3) CONVÊNIO — quem sobrou (é o default do campo).


def nada(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        # `admin_cadastros` tem só a inicial neste repositório; o backfill
        # consulta `admin_pagamentos` em `apps.get_model` e trata a ausência
        # com `LookupError`, então não precisa de dependência cruzada (que
        # criaria ciclo: pagamentos → cadastros).
        ('admin_cadastros', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='empresa',
            name='tipo',
            field=models.CharField(
                choices=[('fornecedor', 'Fornecedor'),
                         ('convenio', 'Convênio'),
                         ('estabelecimento', 'Estabelecimento')],
                db_index=True,
                default='convenio',
                help_text='Define onde esta empresa pode ser usada: '
                          'fornecedor, convênio (pagador) ou estabelecimento.',
                max_length=20,
                verbose_name='Tipo'),
        ),
        migrations.RunPython(classificar_empresas, nada),
    ]
