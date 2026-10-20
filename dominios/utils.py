from django.utils import timezone
from django.http import HttpResponse, HttpResponseRedirect
from admin_cadastros_assistenciais.models import CadastroProfissional
from reportlab.lib.pagesizes import A4
from django.conf import settings
from django.urls import reverse
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import models
from django.db import connection
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.core.exceptions import ValidationError
from datetime import datetime
from django import template
import re
from django import forms
from django.contrib.auth.models import Group
from django.db.models import Q
from admin_cadastros.models import Estabelecimento
from django.contrib.admin import SimpleListFilter
from admin_cadastros_assistenciais.models import CadastroProfissional
from admin_evolucoes.models import ParametrosEvolucao
from admin_adep.models import ParametrosAdep
from admin_prescricoes.models import ParametrosPrescricao
from admin_sae.models import ParametrosSAE
from admin_perdas_ganhos.models import ParametrosPerdasGanhos
from admin_plano_cuidados.models import ParametrosPlanoCuidados
from admin_sinais_vitais.models import ParametrosSinaisVitais
from django.forms import PasswordInput
from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken
import logging
from django.http import HttpResponse
import datetime
from cryptography.hazmat import backends
from cryptography import x509
import os
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import pkcs12
# from endesive.pdf import cms
# from endesive import pdf
from datetime import date
import xlwt
from django.core.exceptions import ValidationError
from django.utils.html import strip_tags


def validar_tamanho_ata(value):
    # Remove todas as tags HTML para contar caracteres
    texto_limpo = strip_tags(value)
    tamanho = len(texto_limpo)

    # Conta as quebras de linha, parágrafos e itens de lista
    linhas = (
        value.count('<p>') +  # Conta parágrafos
        value.count('<br>') +  # Conta quebras de linha <br>
        value.count('<br/>') +  # Conta quebras de linha <br/>
        value.count('\n') +  # Conta quebras de linha \n
        value.count('<li>')  # Conta itens de lista
    )

    # Adiciona 1 para a última linha (se não terminar com uma quebra)
    if not value.strip().endswith(('\n', '<br>', '<br/>', '</p>', '</li>')):
        linhas += 1

    if tamanho > 8000:
        raise ValidationError(
            f"O campo deve conter no máximo 4000 caracteres. Atual: {tamanho}.")

    if linhas > 25:
        raise ValidationError(
            f"O campo deve conter no máximo 25 linhas. Atual: {linhas}.")


class HiddenPasswordInput(PasswordInput):
    def get_context(self, name, value, attrs):
        # Substitua o valor por asteriscos antes de renderizar
        value = "********"
        return super().get_context(name, value, attrs)


# METODO PARA CRIPTOGRAFAR E DESCRIPTOGRAFAR CAMPOS, USADO EM SENHAS E EVOLUCOES CRIPTOGRAFADAS
class EncryptedCharField(models.CharField):
    def from_db_value(self, value, expression, connection):
        if value is not None:
            cipher_suite = Fernet(settings.FERNET_KEY)
            try:
                return cipher_suite.decrypt(value.encode()).decode()
            except InvalidToken:
                logging.error("Erro ao descriptografar o valor.")
                return None  # Ou lidar com o erro de forma adequada
        return value

    def get_prep_value(self, value):
        if value is not None:
            cipher_suite = Fernet(settings.FERNET_KEY)
            return cipher_suite.encrypt(value.encode()).decode()
        return value


class EncryptedTextField(models.TextField):
    def from_db_value(self, value, expression, connection):
        if value is not None:
            cipher_suite = Fernet(settings.FERNET_KEY)
            try:
                return cipher_suite.decrypt(value.encode()).decode()
            except InvalidToken:
                logging.error("Erro ao descriptografar o valor.")
                return None  # Ou lidar com o erro de forma adequada
        return value

    def get_prep_value(self, value):
        if value is not None:
            cipher_suite = Fernet(settings.FERNET_KEY)
            return cipher_suite.encrypt(value.encode()).decode()
        return value


def in_group(user, group_name):
    try:
        group = Group.objects.get(name=group_name)
    except Group.DoesNotExist:
        return False

    return group in user.groups.all()

# OBTER USUARIO LOGADO


def get_current_user(request):
    if request and request.user.is_authenticated:
        return request.user
    return None


# FILTRAR APENAS ATIVOS NOS FORMS TEMPLATES CUSTOMIZADOS
class FilterByStatusMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field, forms.ModelChoiceField) and hasattr(field.queryset.model, 'status'):
                if field.queryset.query:
                    # O queryset já foi definido, então filtramos ele
                    field.queryset = field.queryset.filter(status='A')
                else:
                    # O queryset ainda não foi definido, então adicionamos o filtro para que ele seja aplicado mais tarde
                    field.queryset.query.add_q(Q(status='A'))

# CRIAR OBJETOS NOS ADMIN SOMENTE COM STATUS A


class FilterAdminByStatusMixin:
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if hasattr(field.queryset.model, 'status'):
            field.queryset = field.queryset.filter(status='A')
        return field


# LISTAR NO ADMIN OBJETOS A E SE NECESSARIO ALTERAR PARA STATUS I
class StatusFilterAdminMixin(SimpleListFilter):
    title = 'Status (Ativo)'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return (
            ('A', 'Ativo'),
            ('I', 'Inativo'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'A':
            return queryset.filter(status='A')
        elif self.value() == 'I':
            return queryset.filter(status='I')
        else:
            return queryset.filter(status='A')


class PreFaturadoFilterAdminMixin(SimpleListFilter):
    title = 'Pré Faturado (Não)'
    parameter_name = 'pre_faturado'

    def lookups(self, request, model_admin):
        return (
            ('True', 'Sim'),
            ('False', 'Não'),
        )

    def queryset(self, request, queryset):
        # Definindo como padrão os objetos não faturados
        if self.value() is None or self.value() == 'False':
            return queryset.filter(pre_faturado=False)
        elif self.value() == 'True':
            return queryset.filter(pre_faturado=True)
        return queryset
# LISTAR USERS ATIVOS NO ADMIN E SE NECESSARIO ALTERAR PARA STATUS I


class FaturadoFilterAdminMixin(SimpleListFilter):
    title = 'Faturado'
    parameter_name = 'pre_faturado'

    def lookups(self, request, model_admin):
        return (
            ('True', 'Sim'),
            ('False', 'Não'),
        )

    def queryset(self, request, queryset):
        # Definindo como padrão os objetos não faturados
        if self.value() is None or self.value() == 'False':
            return queryset.filter(faturado=False)
        elif self.value() == 'True':
            return queryset.filter(faturado=True)
        return queryset
# LISTAR USERS ATIVOS NO ADMIN E SE NECESSARIO ALTERAR PARA STATUS I


class IsActiveFilter(SimpleListFilter):
    title = ('Status')
    parameter_name = 'is_active'

    def lookups(self, request, model_admin):
        return (
            (True, ('Ativo')),
            (False, ('Inativo')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'True':
            return queryset.filter(is_active=True)
        elif self.value() == 'False':
            return queryset.filter(is_active=False)
        else:
            return queryset.filter(is_active=True)


# VALIDAR WHATSAPP
def validar_whats(numero):
    padrao = re.compile(r'^\+?[1-9]\d{12}$')  # regex para validar número
    return padrao.match(numero) is not None

# VALIDAR TELEFONE


def validar_telefone(numero):
    padrao = re.compile(r'^\+?[1-9]\d{8,12}$')  # regex para validar número
    return padrao.match(numero) is not None


# CALCULAR IDADE
register = template.Library()


@register.filter
def calcular_idade(dt_nascimento):
    if dt_nascimento:
        hoje = date.today()
        idade = hoje.year - dt_nascimento.year
        if hoje.month < dt_nascimento.month or (hoje.month == dt_nascimento.month and hoje.day < dt_nascimento.day):
            idade -= 1
        return idade
    else:
        return None

# VALIDAR ANEXO COM 5MB


def validate_anexo_file(value):
    if value:
        max_file_size = 5 * 1024 * 1024  # 5 MB
        if value.size > max_file_size:
            raise ValidationError(
                f'O arquivo excede o tamanho máximo permitido de {max_file_size // (5 * 1024 * 1024)} MB.')


class AccessDenied(Exception):
    pass


# FILTRAR ESTABELECIMENTOS DO USUSARIO NAS VIEWS
class FilterObjectsByEstabelecimentoMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        estabelecimento_id = self.request.session.get("estabelecimento_id")

        if estabelecimento_id:
            estabelecimento = Estabelecimento.objects.get(
                pk=estabelecimento_id)
            queryset = queryset.filter(estabelecimento=estabelecimento)
        else:
            queryset = queryset.none()

        return queryset


# VERIFICA PERMISSOES POR GRUPO OU USUARIO, SE NAO TIVER PERMISSAO RETORNA PARA A PAGINA ANTERIOR

class CustomPermissionRequiredMixin(UserPassesTestMixin, PermissionRequiredMixin):
    raise_exception = True

    def test_func(self):
        return self.request.user.is_authenticated

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            js = '''
            <script>
                alert("Sua sessao expirou. Clique OK para fazer o login novamente.");
                window.location.href = "/login/"; 
            </script>
            '''
            return HttpResponse(js, content_type='text/html')
        else:
            raise PermissionDenied

    def dispatch(self, request, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return HttpResponseRedirect(reverse('logout'))

        if not self.test_func():
            return self.handle_no_permission()
        try:
            return super().dispatch(request, *args, **kwargs)
        except PermissionDenied:
            js = '''
            <script>
                alert("Solicite permissao ao administrador do sistema.");
                window.history.back();
            </script>
            '''
            return HttpResponse(js, content_type='text/html')


# OBTER PERMISSOES POR USUARIO
def obter_permissoes_por_usuario(user_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT g.name, p.codename
            FROM auth_user u
            JOIN auth_user_groups ug ON u.id = ug.user_id
            JOIN auth_group g ON ug.group_id = g.id
            JOIN auth_group_permissions gp ON g.id = gp.group_id
            JOIN auth_permission p ON gp.permission_id = p.id
            WHERE u.id = %s
        """, [user_id])
        resultado = cursor.fetchall()
        grupos = {}
        for grupo, permissao in resultado:
            if grupo not in grupos:
                grupos[grupo] = [permissao]
            else:
                grupos[grupo].append(permissao)
        return grupos

# VERIFICAR SE USUARIO É CRIADOR DO REGISTRO E CASO NAO SEJA NEGA ACESSO


class UserIsCreatorMixin():
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()

        if self.object.us_registro != request.user:
            js = '''
            <script>
                alert("Somente o profissional que realizou o registro pode atualizar!");
                window.history.back();
            </script>
            '''
            return HttpResponse(js, content_type='text/html')

        return super().dispatch(request, *args, **kwargs)


class NoneToEmptyMixin:
    def preprocess_fields(self):
        # Percorre todos os campos do formulário
        for field_name, field in self.fields.items():
            # Verifica se o campo tem valor None
            if self.initial.get(field_name) is None:
                self.initial[field_name] = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.preprocess_fields()


# TODO: APOS TESTES EXCLUIR
"""
# verifica cadastro profissional nos modelos de parametros
def parametros_prontuarios(user, estabelecimento, modelo_parametros):
    print(
        f"Função - User: {user}, Estabelecimento: {estabelecimento}, Modelo: {modelo_parametros}")

    cadastro_profissional = False
    # Obter o objeto CadastroProfissional relacionado ao usuário logado

    has_permission = False

    cadastro_profissional = CadastroProfissional.objects.get(
        profissional=user, status='A'
    )

    if cadastro_profissional:

        has_permission = modelo_parametros.objects.filter(
            Q(profissao=cadastro_profissional.profissao, estabelecimento=estabelecimento, status='A') |
            Q(profissional=user, estabelecimento=estabelecimento, status='A')
        ).exists()

    else:
        has_permission = False

    print(f"Função - Has Permission: {has_permission}")

    return has_permission


# mixin na cbv para passar o modelo para parametros_prontuarios ver permissao de criar e editar

# TODO: INICIALIZADAS VARIAVEIS, TESTA, OU TIRAR OU VER O DO COMENTARIO
class ParametrosProntuariosMixin:
    modelo_parametros = None  # Defina isso na sua view

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Sua sessão expirou!')
            return HttpResponseRedirect(reverse('logout'))
        user = request.user
        # Substitua pela forma correta de obter o estabelecimento da sessão
        estabelecimento = request.session.get('estabelecimento_id')

        print(
            f"Mixin - User: {user}, Estabelecimento: {estabelecimento}, Modelo: {self.modelo_parametros}")

        has_permission = False
        # Verificar permissão usando a função genérica
        has_permission = parametros_prontuarios(
            user, estabelecimento, self.modelo_parametros)

        if has_permission is not True:
            js = '''
            <script>
                alert("Voce nao tem permissao para criar registros, contate o administrador do sistema!");
                window.history.back();
            </script>
            '''
            return HttpResponse(js, content_type='text/html')

        return super().dispatch(request, *args, **kwargs)


"""


def parametros_prontuarios(user, estabelecimento, modelo_parametros):
    try:
        cadastro_profissional = CadastroProfissional.objects.get(
            profissional=user, status='A'
        )
    except CadastroProfissional.DoesNotExist:
        return False, "Usuario nao possui um cadastro profissional ativo."

    has_permission = modelo_parametros.objects.filter(
        Q(profissao=cadastro_profissional.profissao, estabelecimento=estabelecimento, status='A') |
        Q(profissional=user, estabelecimento=estabelecimento, status='A')
    ).exists()

    if has_permission:
        return True, ""
    else:
        return False, "Usuario nao tem permissao para este recurso."


class ParametrosProntuariosMixin:
    modelo_parametros = None  # Deve ser definido na view que herda este mixin

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Sua sessão expirou!')
            return HttpResponseRedirect(reverse('logout'))

        user = request.user
        estabelecimento = request.session.get('estabelecimento_id')

        # Verificação adicional para garantir que modelo_parametros não é None
        if self.modelo_parametros is None:
            js = '''
            <script>
                alert("Permissoes em Admin Parametros, para Passagem de Plantoes nao definido. Por favor, contate o administrador do sistema.");
                window.history.back();
            </script>
            '''
            return HttpResponse(js, content_type='text/html')

        has_permission, message = parametros_prontuarios(
            user, estabelecimento, self.modelo_parametros)

        if not has_permission:
            js = f'''
            <script>
                alert("{message}");
                window.history.back();
            </script>
            '''
            return HttpResponse(js, content_type='text/html')

        return super().dispatch(request, *args, **kwargs)


def chain_form_init(form, form_init):
    """
    Encadeia um novo ``form.__init__`` ao que já estiver definido no form.

    Os mixins de admin (ex.: ``AdminEstabelecimentoPadraoMixin``) substituem
    ``form.__init__`` em ``get_form``. Se um ModelAdmin sobrescrever o
    ``__init__`` diretamente, a lógica do mixin é descartada silenciosamente.
    Use esta função para preservar as duas camadas.
    """
    previous_init = form.__init__

    def chained_init(form_instance, *args, **kwargs):
        previous_init(form_instance, *args, **kwargs)
        form_init(form_instance, *args, **kwargs)

    form.__init__ = chained_init
    return form


class AdminEstabelecimentoPadraoMixin:
    """
    Vincula o campo 'estabelecimento' ao estabelecimento ATIVO NA SESSÃO do
    usuário (chave 'estabelecimento_id', definida em select_estabelecimento).

    Regras:
    - Sessão ativa e liberada para o perfil: o valor é fixado (campo
      desabilitado), com a sessão prevalecendo sobre qualquer POST.
    - Sessão ativa mas NÃO liberada para o perfil: bloqueia com PermissionDenied
      (em vez de silenciosamente cair em outro estabelecimento).
    - Sem sessão (ex.: login direto no /admin ou superuser): usa o
      'estabelecimento_padrao' do perfil, como fallback.
    - Só quem não tem perfil (superuser puro) continua escolhendo livremente.
    """

    @staticmethod
    def _estabelecimento_da_sessao(request, perfil):
        """
        Resolve o estabelecimento ativo. Retorna (estabelecimento, liberado).
        'liberado' indica se o estabelecimento pode ser usado pelo perfil.
        """
        estabelecimento = None
        estabelecimento_id = request.session.get('estabelecimento_id')

        if estabelecimento_id:
            estabelecimento = Estabelecimento.objects.filter(
                pk=estabelecimento_id).first()

        if estabelecimento is None and perfil:
            # Sem sessão: cai para o padrão do perfil.
            estabelecimento = perfil.estabelecimento_padrao

        if estabelecimento is None:
            return None, False

        if not perfil:
            return estabelecimento, True

        liberado = perfil.estabelecimento.filter(pk=estabelecimento.pk).exists()
        return estabelecimento, liberado

    def get_form(self, request, obj=None, **kwargs):
        """
        Fixa o campo 'estabelecimento' no estabelecimento da sessão (ou no
        padrão do perfil quando não há sessão) e impede a troca pelo usuário.
        """
        form = super().get_form(request, obj, **kwargs)

        perfil = getattr(request.user, 'perfil', None)
        estabelecimento, liberado = self._estabelecimento_da_sessao(
            request, perfil)

        # Sessão apontando para estabelecimento não liberado: bloqueia.
        if perfil and estabelecimento and not liberado:
            raise PermissionDenied(
                'O estabelecimento selecionado na sessão não está liberado '
                'para o seu perfil. Contate o administrador do sistema.')

        campo = form.base_fields.get('estabelecimento')
        if campo is None:
            # Campo readonly/removido neste ModelAdmin: a vinculação é feita
            # no save_model.
            return form

        if perfil is not None:
            liberados = perfil.estabelecimento.all()
            campo.queryset = liberados.filter(pk=estabelecimento.pk) \
                if estabelecimento else liberados

            if not estabelecimento:
                campo.queryset = Estabelecimento.objects.none()
                campo.disabled = True

                def form_init(form_instance, *args, **kwargs):
                    form_instance.add_error(
                        None,
                        'Nenhum estabelecimento ativo na sessão. Selecione um '
                        'estabelecimento antes de continuar.',
                    )

                chain_form_init(form, form_init)
                return form

            # Fixa o valor: o usuário não escolhe estabelecimento.
            campo.initial = estabelecimento
            campo.disabled = True

            def form_init(form_instance, *args, **kwargs):
                # Garante o valor da sessão mesmo em edição (campo desabilitado
                # não é enviado pelo navegador).
                form_instance.fields['estabelecimento'].initial = estabelecimento
                form_instance.instance.estabelecimento = estabelecimento
                try:
                    form_instance.initial['estabelecimento'] = estabelecimento
                except Exception:
                    pass

            chain_form_init(form, form_init)

        return form

    def save_model(self, request, obj, form, change):
        """
        Garante o estabelecimento da sessão no objeto salvo e impede que o
        usuário salve para um estabelecimento não liberado para o perfil.
        """
        perfil = getattr(request.user, 'perfil', None)
        estabelecimento, liberado = self._estabelecimento_da_sessao(
            request, perfil)

        if perfil and estabelecimento and not liberado:
            raise PermissionDenied(
                'O estabelecimento selecionado na sessão não está liberado '
                'para o seu perfil. Contate o administrador do sistema.')

        if estabelecimento is not None:
            # A sessão prevalece sobre qualquer valor vindo do POST.
            obj.estabelecimento = estabelecimento

        if perfil:
            liberados = perfil.estabelecimento.all()
            if obj.estabelecimento and obj.estabelecimento not in liberados:
                raise PermissionDenied(
                    'Você não tem permissão para salvar este objeto para este estabelecimento.')

        super().save_model(request, obj, form, change)


class AdminSaveModelAuditMixin:
    """
    Mixin para salvar os campos de auditoria como 'us_registro', 'dt_registro',
    'us_atualizacao', e 'dt_atualizacao' nos ModelAdmins.
    """

    def save_model(self, request, obj, form, change):
        """
        Define os campos de auditoria: 'us_registro' e 'dt_registro' ao criar
        e 'us_atualizacao' e 'dt_atualizacao' ao atualizar.
        """
        if not change:
            # Primeira vez que o objeto está sendo salvo
            obj.us_registro = request.user
            obj.dt_registro = timezone.now()
        else:
            # Se o objeto já existe (edição)
            obj.us_atualizacao = request.user
            obj.dt_atualizacao = timezone.now()

        # Chama o método padrão de save_model para continuar o processo
        super().save_model(request, obj, form, change)


class ExportToXLSMixin:
    """
    Exportador corporativo avançado para Excel (.xlsx) e CSV (UTF-8 com BOM).
    Utiliza openpyxl para gerar planilhas estilizadas com cabeçalho institucional,
    auto-ajuste de colunas, formatação de datas e linhas zebradas.
    Mantém compatibilidade com xlwt como fallback.
    """

    def export_as_xls(self, request, queryset):
        """Exporta queryset para arquivo Excel moderno (.xlsx) estilizado."""
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]
        verbose_names = [field.verbose_name.title() if hasattr(field, 'verbose_name') else field.name for field in meta.fields]

        try:
            import io
            import datetime as dt_mod
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = str(meta.verbose_name_plural)[:31]

            # Estilos
            fill_header = PatternFill(start_color="1B3A57", end_color="1B3A57", fill_type="solid")
            font_header = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
            font_normal = Font(name="Calibri", size=9)
            border_thin = Border(
                left=Side(style='thin', color='E0E0E0'),
                right=Side(style='thin', color='E0E0E0'),
                top=Side(style='thin', color='E0E0E0'),
                bottom=Side(style='thin', color='E0E0E0')
            )
            fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

            # Cabeçalho
            ws.row_dimensions[1].height = 24
            for col_num, v_name in enumerate(verbose_names, start=1):
                cell = ws.cell(row=1, column=col_num, value=str(v_name))
                cell.font = font_header
                cell.fill = fill_header
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = border_thin

            # Dados
            for row_num, obj in enumerate(queryset, start=2):
                ws.row_dimensions[row_num].height = 19
                is_even = (row_num % 2 == 0)

                for col_num, field_name in enumerate(field_names, start=1):
                    val = getattr(obj, field_name, '')
                    # Formata datas e relações
                    if isinstance(val, (dt_mod.datetime, dt_mod.date)):
                        val_str = val.strftime('%d/%m/%Y %H:%M') if isinstance(val, dt_mod.datetime) else val.strftime('%d/%m/%Y')
                    elif hasattr(val, '__str__') and not isinstance(val, (str, int, float, bool)):
                        val_str = str(val)
                    else:
                        val_str = str(val) if val is not None else ''

                    cell = ws.cell(row=row_num, column=col_num, value=val_str)
                    cell.font = font_normal
                    cell.border = border_thin
                    if is_even:
                        cell.fill = fill_zebra
                    cell.alignment = Alignment(vertical="center")

            # Largura automática das colunas
            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = max(max_len + 3, 11)

            buffer = io.BytesIO()
            wb.save(buffer)
            buffer.seek(0)

            response = HttpResponse(
                buffer.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{meta.verbose_name_plural}.xlsx"'
            return response

        except Exception as e:
            # Fallback seguro para xlwt se openpyxl falhar
            response = HttpResponse(content_type='application/ms-excel')
            response['Content-Disposition'] = f'attachment; filename="{meta.verbose_name_plural}.xls"'
            wb = xlwt.Workbook(encoding='utf-8')
            ws = wb.add_sheet(str(meta.verbose_name_plural)[:31])

            for col_num, field_name in enumerate(field_names):
                ws.write(0, col_num, field_name)

            for row_num, obj in enumerate(queryset, start=1):
                for col_num, field_name in enumerate(field_names):
                    value = getattr(obj, field_name)
                    ws.write(row_num, col_num, str(value))

            wb.save(response)
            return response

    export_as_xls.short_description = "📊 Exportar Selecionados para Excel (XLSX Formatado)"

    def export_as_csv(self, request, queryset):
        """Exporta queryset para CSV com codificação UTF-8 e BOM (compatível com Excel)."""
        import csv
        import datetime as dt_mod
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]
        verbose_names = [field.verbose_name.title() if hasattr(field, 'verbose_name') else field.name for field in meta.fields]

        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="{meta.verbose_name_plural}.csv"'

        writer = csv.writer(response, delimiter=';')
        writer.writerow(verbose_names)

        for obj in queryset:
            row = []
            for field_name in field_names:
                val = getattr(obj, field_name, '')
                if isinstance(val, dt_mod.datetime):
                    val = val.strftime('%d/%m/%Y %H:%M')
                elif isinstance(val, dt_mod.date):
                    val = val.strftime('%d/%m/%Y')
                elif hasattr(val, '__str__') and not isinstance(val, (str, int, float, bool)):
                    val = str(val)
                row.append(str(val) if val is not None else '')
            writer.writerow(row)

        return response

    export_as_csv.short_description = "📄 Exportar Selecionados para CSV (UTF-8)"

