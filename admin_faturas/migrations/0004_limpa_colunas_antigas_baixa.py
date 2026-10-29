"""Migração de estado vazia.

A recriação de `baixafatura` (com a remoção das colunas antigas) é feita numa
única passada na migração 0002 — no SQLite, cada AlterField/RemoveField de
campo herdado recria a tabela e apagaria o backfill das colunas novas. Esta
migração é mantida apenas para preservar a cadeia já registrada.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('admin_faturas', '0003_alter_convenio_options'),
    ]

    operations = []
