"""`AcordoPagamento.estabelecimento` vira CAMPO (FK), não mais `property`.

Antes o estabelecimento era derivado do fornecedor (`property`), então o
acordo não podia ser recortado por estabelecimento no filtro padrão
(`EstabelecimentoFilterAdminMixin`) nem fixado no formulário
(`AdminEstabelecimentoPadraoMixin`).

Agora é uma FK própria, preenchida com o estabelecimento da SESSÃO/perfil (o
mesmo que as demais etapas do fluxo usam). O backfill resolve os acordos já
existentes na seguinte ordem:

1. o estabelecimento ligado à EMPRESA do fornecedor (relação
   `estabelecimento_set`);
2. o estabelecimento da PESSOA do fornecedor;
3. o primeiro estabelecimento ativo do sistema (último recurso, para nunca
   deixar o acordo sem vínculo).

A FK fica `null=True` no schema (linha antiga sem como resolver não quebra a
migração), mas o form SEMPRE carrega o padrão da sessão nos novos registros.
"""
from django.db import migrations, models
import django.db.models.deletion


def preencher_estabelecimento(apps, schema_editor):
    AcordoPagamento = apps.get_model('admin_pagamentos', 'AcordoPagamento')
    Estabelecimento = apps.get_model('admin_cadastros', 'Estabelecimento')

    padrao = Estabelecimento.objects.filter(status='A').first() \
        or Estabelecimento.objects.first()

    for acordo in AcordoPagamento.objects.filter(
            estabelecimento__isnull=True).iterator():
        estabelecimento = None
        fornecedor = acordo.fornecedor if acordo.fornecedor_id else None
        if fornecedor is not None:
            empresa = (fornecedor.empresa
                       if getattr(fornecedor, 'empresa_id', None) else None)
            if empresa is not None and hasattr(empresa, 'estabelecimento_set'):
                estabelecimento = empresa.estabelecimento_set.first()
            if estabelecimento is None:
                estabelecimento = padrao
        if estabelecimento is not None:
            AcordoPagamento.objects.filter(pk=acordo.pk).update(
                estabelecimento_id=estabelecimento.pk)


def nada(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('admin_pagamentos', '0013_alter_classepagamento_descricao'),
        ('admin_cadastros', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='acordopagamento',
            name='estabelecimento',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to='admin_cadastros.estabelecimento',
                verbose_name='Estabelecimento'),
        ),
        migrations.RunPython(preencher_estabelecimento, nada),
    ]
