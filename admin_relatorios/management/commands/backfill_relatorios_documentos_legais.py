"""
Registra em ``Relatorio`` os Documentos Legais já gerados antes desta correção.

Até então, ``documentos_legais`` só gravava o PDF em
``DocumentoLegalInternacao.pdf_gerado`` e nunca criava a linha correspondente
em ``Relatorio``; por isso os termos não apareciam em
Admin > Relatórios gerados.

Uso:
    python manage.py backfill_relatorios_documentos_legais            # executa
    python manage.py backfill_relatorios_documentos_legais --dry-run  # só mostra
    python manage.py backfill_relatorios_documentos_legais --all      # recria inativos
"""

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from admin_relatorios.models import Relatorio
from documentos_legais.models import DocumentoLegalInternacao
from documentos_legais.services import registrar_relatorio_documento_legal


class Command(BaseCommand):
    help = 'Cria registros em Relatorio para documentos legais já gerados.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Apenas informa quantos registros seriam criados.')
        parser.add_argument(
            '--all', action='store_true',
            help='Recria mesmo quando já existe relatório ativo (historiza).')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        recriar = options['all']

        content_type = ContentType.objects.get_for_model(DocumentoLegalInternacao)

        documentos = (
            DocumentoLegalInternacao.objects
            .exclude(pdf_gerado='')
            .exclude(pdf_gerado__isnull=True)
            .select_related('atendimento', 'pessoa', 'us_registro')
            .order_by('id')
        )

        ja_com_relatorio = set(
            Relatorio.objects.filter(
                content_type=content_type, status='A',
            ).values_list('object_id', flat=True)
        )

        criados = 0
        ignorados = 0

        for documento in documentos.iterator():
            if documento.pk in ja_com_relatorio and not recriar:
                ignorados += 1
                continue

            if dry_run:
                criados += 1
                self.stdout.write(
                    f'[dry-run] criaria Relatorio doc #{documento.pk} '
                    f'({documento.codigo_documento})')
                continue

            with transaction.atomic():
                relatorio = registrar_relatorio_documento_legal(
                    documento, user=documento.us_registro)
            if relatorio:
                criados += 1

        acao = 'seriam criados' if dry_run else 'criados'
        self.stdout.write(self.style.SUCCESS(
            f'{criados} registro(s) {acao}; {ignorados} já possuíam relatório ativo.'))
