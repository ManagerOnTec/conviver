from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

import documentos_legais.models
import dominios.text_validators


def criar_tipos_padrao(apps, schema_editor):
    TipoDocumentoLegal = apps.get_model('documentos_legais', 'TipoDocumentoLegal')
    tipos = [
        ('termo-internacao', 'Termo De Internação', 1),
        ('termo-alta-pedido', 'Termo De Alta A Pedido', 2),
        ('termo-entrega-pertences', 'Termo De Entrega De Pertences', 3),
        ('termo-responsabilidade-saida', 'Termo De Responsabilidade De Saída', 4),
    ]
    for slug, nome, ordem in tipos:
        TipoDocumentoLegal.objects.get_or_create(
            slug=slug,
            defaults={
                'nome': nome,
                'ordem': ordem,
                'padrao_sistema': True,
                'status': 'A',
            },
        )


def remover_tipos_padrao(apps, schema_editor):
    TipoDocumentoLegal = apps.get_model('documentos_legais', 'TipoDocumentoLegal')
    TipoDocumentoLegal.objects.filter(padrao_sistema=True).delete()


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('admin_cadastros', '0001_initial'),
        ('atendimentos', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TipoDocumentoLegal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=150, unique=True, verbose_name='Tipo de Termo')),
                ('slug', models.SlugField(max_length=160, unique=True, verbose_name='Identificador')),
                ('descricao', models.CharField(blank=True, max_length=255, null=True, verbose_name='Descrição')),
                ('ordem', models.PositiveIntegerField(default=0, verbose_name='Ordem')),
                ('padrao_sistema', models.BooleanField(default=False, verbose_name='Padrão do Sistema')),
                ('status', models.CharField(choices=[('A', 'Ativo'), ('I', 'Inativo')], default='A', max_length=1)),
                ('dt_registro', models.DateTimeField(default=django.utils.timezone.now, null=True, verbose_name='Dt.Registro')),
                ('dt_atualizacao', models.DateTimeField(blank=True, default=None, null=True, verbose_name='Dt.Atualização')),
                ('us_atualizacao', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='tipo_documento_legal_atualizado_por', to=settings.AUTH_USER_MODEL, verbose_name='Us.Atualização')),
                ('us_registro', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='tipo_documento_legal_criado_por', to=settings.AUTH_USER_MODEL, verbose_name='Us.Registro')),
            ],
            options={'verbose_name': 'Tipo de Documento Legal', 'verbose_name_plural': '1. Tipos de Documentos Legais', 'ordering': ['ordem', 'nome']},
        ),
        migrations.CreateModel(
            name='ModeloDocumentoLegal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome_modelo', models.CharField(max_length=150, verbose_name='Nome do Modelo')),
                ('titulo_documento', models.CharField(max_length=255, verbose_name='Título do Documento')),
                ('conteudo_html', models.TextField(help_text='Placeholders disponíveis: {{ paciente_nome }}, {{ paciente_cpf }}, {{ paciente_dt_nascimento }}, {{ atendimento_id }}, {{ responsavel_nome }}, {{ responsavel_cpf }}, {{ responsavel_documento }}, {{ responsavel_data_nascimento }}, {{ responsavel_telefone }}, {{ responsavel_email }}, {{ data_documento }}, {{ estabelecimento_nome }}.', validators=[dominios.text_validators.validate_evolucao_like_text], verbose_name='Conteúdo do Termo')),
                ('status', models.CharField(choices=[('A', 'Ativo'), ('I', 'Inativo')], default='A', max_length=1)),
                ('dt_registro', models.DateTimeField(default=django.utils.timezone.now, null=True, verbose_name='Dt.Registro')),
                ('dt_atualizacao', models.DateTimeField(blank=True, default=None, null=True, verbose_name='Dt.Atualização')),
                ('estabelecimento', models.ForeignKey(blank=True, help_text='Deixe em branco para um modelo global do sistema.', null=True, on_delete=django.db.models.deletion.PROTECT, to='admin_cadastros.estabelecimento', verbose_name='Estabelecimento')),
                ('tipo_documento', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='modelos', to='documentos_legais.tipodocumentolegal', verbose_name='Tipo de Termo')),
                ('us_atualizacao', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='modelo_documento_legal_atualizado_por', to=settings.AUTH_USER_MODEL, verbose_name='Us.Atualização')),
                ('us_registro', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='modelo_documento_legal_criado_por', to=settings.AUTH_USER_MODEL, verbose_name='Us.Registro')),
            ],
            options={'verbose_name': 'Modelo de Documento Legal', 'verbose_name_plural': '2. Modelos de Documentos Legais', 'ordering': ['tipo_documento__ordem', 'nome_modelo']},
        ),
        migrations.CreateModel(
            name='DocumentoLegalInternacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo_documento', models.CharField(editable=False, max_length=32, unique=True, verbose_name='Código')),
                ('titulo_documento', models.CharField(max_length=255, verbose_name='Título do Documento')),
                ('conteudo_html', models.TextField(validators=[dominios.text_validators.validate_evolucao_like_text], verbose_name='Conteúdo Congelado')),
                ('responsavel_nome', models.CharField(max_length=255, verbose_name='Responsável')),
                ('responsavel_cpf', models.CharField(max_length=18, verbose_name='CPF do Responsável')),
                ('responsavel_documento', models.CharField(max_length=50, verbose_name='Documento de Identificação')),
                ('responsavel_data_nascimento', models.DateField(verbose_name='Data de Nascimento do Responsável')),
                ('responsavel_telefone', models.CharField(blank=True, max_length=20, null=True, verbose_name='Telefone')),
                ('responsavel_email', models.EmailField(blank=True, max_length=254, null=True, verbose_name='E-mail')),
                ('declaracao_aceite', models.BooleanField(default=False, verbose_name='Li e concordo com o termo')),
                ('assinatura_imagem', models.ImageField(blank=True, null=True, upload_to=documentos_legais.models.assinatura_upload_path, verbose_name='Assinatura Desenhada')),
                ('documento_frente', models.ImageField(blank=True, null=True, upload_to=documentos_legais.models.documento_frente_upload_path, validators=[django.core.validators.FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])], verbose_name='Documento Frente')),
                ('documento_verso', models.ImageField(blank=True, null=True, upload_to=documentos_legais.models.documento_verso_upload_path, validators=[django.core.validators.FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])], verbose_name='Documento Verso')),
                ('selfie', models.ImageField(blank=True, null=True, upload_to=documentos_legais.models.selfie_upload_path, validators=[django.core.validators.FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])], verbose_name='Selfie')),
                ('pdf_gerado', models.FileField(blank=True, null=True, upload_to=documentos_legais.models.pdf_upload_path, verbose_name='PDF Gerado')),
                ('hash_pdf', models.CharField(blank=True, max_length=64, null=True, verbose_name='Hash SHA-256')),
                ('dt_assinatura', models.DateTimeField(blank=True, null=True, verbose_name='Dt.Assinatura')),
                ('ip_assinatura', models.CharField(blank=True, max_length=45, null=True, verbose_name='IP')),
                ('user_agent', models.CharField(blank=True, max_length=500, null=True, verbose_name='User Agent')),
                ('observacoes', models.CharField(blank=True, max_length=255, null=True, verbose_name='Observações')),
                ('status', models.CharField(choices=[('A', 'Ativo'), ('I', 'Inativo')], default='A', max_length=1)),
                ('dt_registro', models.DateTimeField(default=django.utils.timezone.now, null=True, verbose_name='Dt.Registro')),
                ('dt_atualizacao', models.DateTimeField(blank=True, default=None, null=True, verbose_name='Dt.Atualização')),
                ('atendimento', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='documentos_legais', to='atendimentos.atendimento', verbose_name='Atendimento')),
                ('estabelecimento', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='documentos_legais', to='admin_cadastros.estabelecimento', verbose_name='Estabelecimento')),
                ('modelo_documento', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='documentos_gerados', to='documentos_legais.modelodocumentolegal', verbose_name='Modelo Aplicado')),
                ('pessoa', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='documentos_legais', to='admin_cadastros.pessoa', verbose_name='Paciente')),
                ('tipo_documento', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='documentos_gerados', to='documentos_legais.tipodocumentolegal', verbose_name='Tipo de Termo')),
                ('us_atualizacao', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='documento_legal_atualizado_por', to=settings.AUTH_USER_MODEL, verbose_name='Us.Atualização')),
                ('us_registro', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='documento_legal_criado_por', to=settings.AUTH_USER_MODEL, verbose_name='Us.Registro')),
            ],
            options={'verbose_name': 'Documento Legal de Internação', 'verbose_name_plural': '3. Documentos Legais de Internação', 'ordering': ['-dt_registro', '-id']},
        ),
        migrations.RunPython(criar_tipos_padrao, remover_tipos_padrao),
    ]
