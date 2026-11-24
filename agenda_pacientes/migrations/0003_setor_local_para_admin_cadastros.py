# Refatoração da hierarquia dos locais da agenda.
#
# ANTES (agenda_pacientes):  Unidade → Setor → Local
# DEPOIS (admin_cadastros):  Estabelecimento → Setor → Local
#
# - `Unidade` foi removida; o `estabelecimento` passou a ficar direto no
#   `Setor`.
# - `Setor` e `Local` agora são modelos de `admin_cadastros`
#   (“10. Setores” / “11. Locais”).
#
# Os dados existentes são **copiados** para as novas tabelas antes de as
# antigas serem removidas (mesmo id), e as FKs (`AgendaPaciente.local`,
# `TipoAgendamento.local`) são reconciliadas depois da troca.
#
# Por que `SeparateDatabaseAndState`: o SQLite não aceita `AlterField` que
# troca uma FK para tabela recém-criada na mesma migração (“Pending trigger
# events”) nem `RemoveField` num campo que participa de uma `UniqueConstraint`
# (`ordering`/`unique`). O schema é montado de forma explícita e o *state* do
# Django é sincronizado separadamente.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def copiar_cadastros(apps, schema_editor):
    """Copia Unidade/Setor/Local antigos para Estabelecimento → Setor → Local."""
    db = schema_editor.connection.alias
    Unidade = apps.get_model('agenda_pacientes', 'Unidade')
    SetorOld = apps.get_model('agenda_pacientes', 'Setor')
    LocalOld = apps.get_model('agenda_pacientes', 'Local')
    Setor = apps.get_model('admin_cadastros', 'Setor')
    Local = apps.get_model('admin_cadastros', 'Local')

    for setor_old in SetorOld.objects.using(db).select_related('unidade'):
        Setor.objects.using(db).create(
            id=setor_old.pk,
            estabelecimento_id=setor_old.unidade.estabelecimento_id,
            nome=setor_old.nome,
            status=setor_old.status,
            dt_registro=setor_old.dt_registro,
            us_registro_id=setor_old.us_registro_id,
            dt_atualizacao=setor_old.dt_atualizacao,
            us_atualizacao_id=setor_old.us_atualizacao_id,
        )

    # A Unidade não tem representação na nova estrutura: preservamos o nome
    # em um Setor quando ele ainda não existir com o mesmo nome (assim um
    # local que ficou órfão — sem setor — continua referenciável).
    for unidade in Unidade.objects.using(db).all():
        existe = Setor.objects.using(db).filter(
            estabelecimento_id=unidade.estabelecimento_id,
            nome__iexact=unidade.nome).filter(status='A').exists()
        if not existe:
            Setor.objects.using(db).create(
                estabelecimento_id=unidade.estabelecimento_id,
                nome=unidade.nome[:100],
                status=unidade.status,
                dt_registro=unidade.dt_registro,
                us_registro_id=unidade.us_registro_id,
                dt_atualizacao=unidade.dt_atualizacao,
                us_atualizacao_id=unidade.us_atualizacao_id,
            )

    for local_old in LocalOld.objects.using(db).all():
        Local.objects.using(db).create(
            id=local_old.pk,
            setor_id=local_old.setor_id,
            nome=local_old.nome,
            online=local_old.online,
            meio_online=local_old.meio_online,
            link_online=local_old.link_online,
            status=local_old.status,
            dt_registro=local_old.dt_registro,
            us_registro_id=local_old.us_registro_id,
            dt_atualizacao=local_old.dt_atualizacao,
            us_atualizacao_id=local_old.us_atualizacao_id,
        )


def reconciliar_fks(apps, schema_editor):
    """Reaponta `AgendaPaciente.local`/`TipoAgendamento.local` para os ids copiados.

    Os ids dos locais foram preservados; a reconciliação garante o vínculo
    mesmo se o banco tiver reconstruído as tabelas (SQLite `ATOMIC`/remake).
    """
    db = schema_editor.connection.alias
    Local = apps.get_model('admin_cadastros', 'Local')
    Agenda = apps.get_model('agenda_pacientes', 'AgendaPaciente')
    Tipo = apps.get_model('agenda_pacientes', 'TipoAgendamento')

    ids = set(Local.objects.using(db).values_list('pk', flat=True))
    Agenda.objects.using(db).exclude(
        local_id__in=ids).update(local_id=None)
    Tipo.objects.using(db).exclude(
        local_id__in=ids).update(local_id=None)


def nada(apps, schema_editor):
    """Reversão não recria Unidade: os dados ficaram em admin_cadastros."""


class Migration(migrations.Migration):

    dependencies = [
        ('admin_cadastros', '0010_setor_local_and_more'),
        ('agenda_pacientes', '0002_tipoagendamento_cor_and_more'),
    ]

    operations = [
        # 1) Copia os cadastros antigos para as novas tabelas.
        migrations.RunPython(copiar_cadastros, nada),

        # 2) Esvazia as FKs antes de trocar os campos (evita depender da
        #    reconciliação logo após a troca de tabela).
        migrations.RunPython(reconciliar_fks, nada),

        # 3) Schema: remove as FKs antigas...
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='agendapaciente',
                    name='local',
                    field=models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to='admin_cadastros.local', verbose_name='Local'),
                ),
                migrations.AlterField(
                    model_name='tipoagendamento',
                    name='local',
                    field=models.ForeignKey(
                        blank=True,
                        help_text='Local sugerido ao criar um agendamento deste tipo.',
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to='admin_cadastros.local', verbose_name='Local Padrão'),
                ),
                migrations.DeleteModel(name='Local'),
                migrations.DeleteModel(name='Setor'),
                migrations.DeleteModel(name='Unidade'),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=[
                        # `DROP TABLE` também remove os índices/FKs da tabela.
                        'DROP TABLE IF EXISTS "agenda_pacientes_local";',
                        'DROP TABLE IF EXISTS "agenda_pacientes_setor";',
                        'DROP TABLE IF EXISTS "agenda_pacientes_unidade";',
                    ],
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),

        # 4) Numeração do menu do app (1 parâmetros, 2 tipos, 3 agendas).
        migrations.AlterModelOptions(
            name='parametrosagenda',
            options={'verbose_name': 'Parâmetros da Agenda',
                     'verbose_name_plural': '1. Parâmetros da Agenda'},
        ),
        migrations.AlterModelOptions(
            name='tipoagendamento',
            options={'ordering': ('descricao',), 'verbose_name': 'Tipo de Agendamento',
                     'verbose_name_plural': '2. Tipos de Agendamento'},
        ),
        migrations.AlterModelOptions(
            name='agendapaciente',
            options={'ordering': ('data_hora', 'pk'), 'verbose_name': 'Agenda de Paciente',
                     'verbose_name_plural': '3. Agendas de Pacientes'},
        ),
    ]
