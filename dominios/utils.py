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
from django.contrib import admin
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


class Select2AdminModelAdminMixin:
    """
    Usa o autocomplete (select2 de digitação) em TODOS os campos de chave
    estrangeira / many-to-many do formulário — inclusive nos inlines.

    Para cada campo o widget correto é escolhido automaticamente:
    - ManyToManyField -> AutocompleteSelectMultiple
    - ForeignKey       -> AutocompleteSelect

    Regras aplicadas:
    - Campo ``disabled``/``readonly`` (ex.: 'estabelecimento' fixado pela sessão
      pelo AdminEstabelecimentoPadraoMixin) não é alterado.
    - Se o ModelAdmin definir ``autocomplete_light_skip = ('campo',)`` o
      campo é ignorado (útil para campos cujo modelo relacionado não tem
      ``search_fields`` — o admin do destino lança exception nesse caso).
    - Ao trocar o widget, o queryset do campo é REGISTRADO em
      ``_select2_querysets`` e reaplicado no ``get_search_results`` do admin
      do modelo relacionado (ex.: o 'cliente' do convênio só aparece com
      pacientes ativos).
    - Se o formulário montar campos fora do ``formfield_for_*`` (form próprio,
      ``base_fields`` de inline etc.), declare ``select2_querysets = {...}``
      no ModelAdmin para o mesmo recorte valer na busca do select2.
    """

    autocomplete_light_skip = ()

    # {nome_do_campo: queryset} — recorte aplicado na busca do select2,
    # independentemente de o widget ter sido aplicado pelo mixin.
    select2_querysets = {}

    # {(modelo_do_form, nome_do_campo): queryset} — recorte usado na busca do
    # select2. Preenchido por ``_aplicar_autocomplete`` e consumido em
    # ``get_search_results``; o widget em si não recebe o queryset porque o
    # AutocompleteJsonView ignora ``widget.get_queryset()``.
    _select2_querysets = None

    def _pode_usar_autocomplete(self, related_model):
        """Só troca o widget se o admin de destino permitir a busca
        (sem ``search_fields`` o AutocompleteJsonView retorna 403)."""
        related_admin = admin.site._registry.get(related_model)
        if related_admin is None:
            return False
        return bool(getattr(related_admin, 'search_fields', None))

    @staticmethod
    def _campo_editavel(formfield, db_field):
        """Campos somente leitura/desabilitados continuam com o widget original
        e campos ocultos não precisam de autocomplete."""
        if getattr(formfield, 'disabled', False):
            return False
        return not isinstance(formfield.widget, forms.HiddenInput)

    @classmethod
    def _aplicar_autocomplete(cls, admin_site, widget_class, db_field, formfield):
        """Troca o widget preservando o queryset e os attrs do campo.

        O queryset continua valendo para validação/salvamento; a busca do
        select2 é recortada por ``select2_querysets`` (ver
        ``get_search_results``).
        """
        queryset = getattr(formfield, 'queryset', None)
        if queryset is None:
            return formfield

        class _AutocompleteComStatus(widget_class):
            """Select2 de digitação; o recorte do queryset é aplicado no
            ``get_search_results`` do ModelAdmin que hospeda o campo."""

            def get_queryset(self, request):
                return queryset

        # O Django só aceita ``<ModelAdmin>.autocomplete_fields`` quando o
        # widget é EXATAMENTE AutocompleteSelect*; subclasses disparam
        # SystemCheckError no boot. Por isso marcamos esta subclasse como
        # autocomplete declarado (mesmo critério do validates()).
        _AutocompleteComStatus.__module__ = widget_class.__module__
        _AutocompleteComStatus.__name__ = widget_class.__name__
        _AutocompleteComStatus.__qualname__ = widget_class.__qualname__

        formfield.widget = _AutocompleteComStatus(
            db_field, admin_site,
            attrs=formfield.widget.attrs,
            choices=queryset,
        )
        return formfield

    def register_select2_queryset(self, nome_campo, queryset):
        """Declara o recorte de um campo do PRÓPRIO ModelAdmin.

        Uso: no `get_form` (ou no `__init__` do form) do admin que hospeda o
        campo, registre o queryset real usado na validação — a busca do
        select2 (AutocompleteJsonView) passa a respeitá-lo, mesmo quando o
        mesmo campo é usado em outro admin com outro recorte.
        """
        if self._select2_querysets is None:
            self._select2_querysets = {}
        self._select2_querysets[nome_campo] = queryset

    def get_search_results(self, request, queryset, search_term):
        """Aplica o recorte do campo também na busca do select2.

        O ``AutocompleteJsonView`` filtra pelo queryset INTEIRO do modelo que
        hospeda o campo e ignora ``widget.get_queryset()``. Sem isto, o select2
        de 'cliente' do convênio listava todas as Pessoas (inclusive
        funcionários), embora o formulário só aceitasse pacientes.
        """
        resultados, may_have_duplicates = super().get_search_results(
            request, queryset, search_term)

        campo = request.GET.get('field_name') if request is not None else None
        if not campo:
            # Busca normal do changelist: sem recorte.
            return resultados, may_have_duplicates

        # O `AutocompleteJsonView` manda `app_label` + `model_name` (o
        # `source_model` é o nome usado por outros widgets/versões).
        fonte = (request.GET.get('source_model')
                 or request.GET.get('model_name'))
        recorte = None
        if fonte == self.model._meta.model_name:
            # O select2 pertence a um campo DESTE próprio ModelAdmin
            # (ex.: campo de Pessoa no admin de Pessoa).
            recorte = (self.select2_querysets or {}).get(campo)
            if recorte is None and self._select2_querysets:
                # Widget aplicado pelo mixin: o queryset vem do form e é
                # registrado em ``_select2_querysets``.
                recorte = self._select2_querysets.get(campo)
        else:
            # O select2 está em outro ModelAdmin (ex.: 'cliente' do Convênio)
            # e busca neste modelo: o recorte mora no admin de origem. A
            # chave pode estar qualificada por `model_name` (evita que o
            # recorte de um form vaze para outro que usa o mesmo campo) —
            # o mapa qualificado está no admin que HOSPEDA o campo.
            mapa = self._select2_querysets or {}
            app_label = request.GET.get('app_label')
            origem_admin = None
            if app_label and fonte:
                # Modelo do admin que hospeda o campo (ex.: baixafatura).
                for modelo in self.admin_site._registry:
                    if (modelo._meta.app_label == app_label
                            and modelo._meta.model_name == fonte):
                        origem_admin = self.admin_site._registry[modelo]
                        break
            if origem_admin is not None:
                # Recorte declarado no admin de ORIGEM tem prioridade (é o
                # que a tela realmente oferece).
                declarado = getattr(origem_admin, 'select2_querysets', None)
                if declarado and declarado.get(campo) is not None:
                    recorte = declarado[campo]
                else:
                    mapa = (getattr(origem_admin,
                                    '_select2_querysets', None) or mapa)
            if recorte is None and fonte:
                recorte = mapa.get(f'{fonte}:{campo}')
            # Sem chave qualificada: NÃO cai na chave simples quando já existe
            # algum recorte qualificado — a chave simples poderia ser de outro
            # form que usa o mesmo campo (fatura × pagamento).
            if recorte is None and not any(':' in k for k in mapa):
                recorte = mapa.get(campo)

        if recorte is None:
            return resultados, may_have_duplicates

        if hasattr(recorte.model, 'status'):
            recorte = recorte.filter(status='A')

        # Interseção com o que o ModelAdmin de destino já liberou para busca.
        return resultados.filter(pk__in=recorte.values('pk')), may_have_duplicates

    @classmethod
    def _autocomplete(cls, admin_site, formfield, db_field, widget_class):
        """Decide e aplica o select2 de digitação (usado também nos inlines)."""
        if formfield is None or not cls._campo_editavel(formfield, db_field):
            return formfield
        related_admin = admin.site._registry.get(db_field.remote_field.model)
        if related_admin is None or not getattr(related_admin, 'search_fields', None):
            return formfield
        return cls._aplicar_autocomplete(
            admin_site, widget_class, db_field, formfield)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name in self.autocomplete_light_skip:
            return formfield
        formfield = self._autocomplete(
            self.admin_site, formfield, db_field,
            admin.widgets.AutocompleteSelect)
        self._registrar_recorte(formfield, db_field)
        return formfield

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        formfield = super().formfield_for_manytomany(db_field, request, **kwargs)
        if db_field.name in self.autocomplete_light_skip:
            return formfield
        formfield = self._autocomplete(
            self.admin_site, formfield, db_field,
            admin.widgets.AutocompleteSelectMultiple)
        self._registrar_recorte(formfield, db_field)
        return formfield

    def _registrar_recorte(self, formfield, db_field):
        """Guarda o queryset do campo para o recorte da busca do select2.

        ``get_search_results`` roda no ModelAdmin do modelo RELACIONADO
        (Pessoa), não neste, e os hooks acima rodam antes do ``__init__`` do
        form — por isso o recorte lido do form é relido aqui no momento do
        render (``_select2_querysets``). O recorte declarado em
        ``select2_querysets`` tem prioridade.
        """
        declarado = (self.select2_querysets or {}).get(db_field.name)
        if declarado is None:
            declarado = getattr(formfield, 'queryset', None)
        if declarado is None:
            return

        relacionado = self.admin_site._registry.get(db_field.remote_field.model)
        if relacionado is None or not isinstance(
                relacionado, Select2AdminModelAdminMixin):
            return
        if relacionado._select2_querysets is None:
            relacionado._select2_querysets = {}
        # Registra SEMPRE qualificado pelo admin que hospeda o campo, para o
        # recorte de um form não vazar para outro que usa o mesmo campo
        # (ex.: transação de ENTRADA na baixa de FATURA × de SAÍDA na baixa de
        # PAGAMENTO). A chave simples é só fallback para admins antigos.
        chave = f'{self.model._meta.model_name}:{db_field.name}'
        relacionado._select2_querysets[chave] = declarado

    # --- Inlines ---------------------------------------------------------
    # Os campos de um inline são gerados pelo ``BaseInlineFormSet`` do inline,
    # que não passa pelo ``formfield_for_*`` do ModelAdmin. Este mixin liga
    # nos inlines do ModelAdmin uma versão que aplica as MESMAS regras
    # (select2 de digitação em FK/M2M, respeitando queryset/status/disabled).
    @staticmethod
    def _aplicar_em_inlines(modeladmin):
        admin_site = modeladmin.admin_site
        for inline_cls in getattr(modeladmin, 'inlines', ()) or ():
            if getattr(inline_cls, '_select2_aplicado', False):
                continue
            original_fk = inline_cls.formfield_for_foreignkey
            original_m2m = inline_cls.formfield_for_manytomany

            def formfield_for_foreignkey(inline_self, db_field, request, **kwargs):
                formfield = original_fk(inline_self, db_field, request, **kwargs)
                return Select2AdminModelAdminMixin._autocomplete(
                    admin_site, formfield, db_field,
                    admin.widgets.AutocompleteSelect)

            def formfield_for_manytomany(inline_self, db_field, request, **kwargs):
                formfield = original_m2m(inline_self, db_field, request, **kwargs)
                return Select2AdminModelAdminMixin._autocomplete(
                    admin_site, formfield, db_field,
                    admin.widgets.AutocompleteSelectMultiple)

            inline_cls.formfield_for_foreignkey = formfield_for_foreignkey
            inline_cls.formfield_for_manytomany = formfield_for_manytomany
            inline_cls._select2_aplicado = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aplicar_em_inlines(self)


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


class SomenteLeituraEstatisticoAdminMixin:
    """
    Transforma o ModelAdmin em um módulo ESTATÍSTICO (somente consulta).

    Os registros são gerados exclusivamente pelo fluxo do sistema
    (atendimento, prontuário, PDF/assinatura). Permitir add/change/delete
    pelo admin abriria brecha para editar registros clínicos por fora do
    fluxo — burlando auditoria, assinatura digital e parametrizações.

    Use como PRIMEIRO mixin da classe:
        class AtendimentoAdmin(SomenteLeituraEstatisticoAdminMixin, admin.ModelAdmin)
    """
    # Deixa explícito no template do admin (botão "Adicionar" some).
    save_on_top = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        # Mesmo que algum mixin/acesso adicione ações, removeremos as de
        # escrita (ex.: "Excluir selecionados").
        actions = super().get_actions(request)
        actions.pop('delete_selected', None)
        return actions


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
            ('1', 'Sim'),
            ('0', 'Não'),
        )

    def queryset(self, request, queryset):
        # Sem seleção, mostrar ambos os estados; os atalhos superiores passam 1/0.
        if self.value() == '1':
            return queryset.filter(pre_faturado=True)
        if self.value() == '0':
            return queryset.filter(pre_faturado=False)
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
        # Usuário LOGADO sem permissão: mensagem amigável (a página branca
        # "403 Forbidden" do Django confundia — parecia erro do sistema).
        js = '''
        <script>
            alert("Voce nao tem permissao para acessar esta tela. " +
                  "Solicite acesso ao administrador do sistema.");
            window.location.href = "/";
        </script>
        '''
        return HttpResponse(js, content_type='text/html', status=200)

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
                alert("Exige permissoes em Admin Parametros ou Cadastro Profissional. Por favor, contate o administrador do sistema.");
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



class ListEditableComRegras:
    """`list_editable` que RESPONDE ÀS REGRAS do fluxo.

    Também garante `selecao_desabilitada` (lido pelo template
    `change_list_results_editavel.html`): sem o atributo o template levanta
    `AttributeError` NO MEIO DA RENDERIZAÇÃO — e o POST de edição em linha
    voltava 200 sem salvar nada.

    O Django lê `list_editable` em tempo de registro; como a lista depende do
    usuário (e a regra depende de cada linha), ela é recalculada em
    `changelist_view`: saem as colunas cujo campo não pode ser alterado no
    recorte atual — por exemplo, com o filtro de “Pré-Faturados” o checkbox
    `pre_faturado` não aparece editável, e linhas travadas ficam somente
    leitura.

    Para declarar, use a LISTA completa em `list_editable` e a lista base em
    `list_editable_sempre`.
    """

    #: O template da listagem lê este atributo em TODO ModelAdmin.
    selecao_desabilitada = False

    def list_editable_permitido(self, request):
        """Colunas editáveis para este recorte (sobrescreva se precisar)."""
        return list(self.list_editable_sempre)

    def get_linhas_nao_editaveis(self, request):
        """Pks (string) cujas colunas editáveis saem como TEXTO na tela.

        Descrição em português e consultável em SQL:

        .. code-block:: sql

            -- pré-fatura que já gerou fatura
            SELECT prefatura_ptr_id FROM admin_faturas_fatura;
            -- convênio com pré-fatura gerada
            SELECT DISTINCT convenio_id FROM admin_faturas_prefatura;
            -- fatura com baixa, com movimento, finalizada ou de competência fechada
            SELECT f.prefatura_ptr_id
              FROM admin_faturas_fatura f
             WHERE f.faturado
                OR EXISTS (SELECT 1 FROM admin_faturas_baixafatura b
                            WHERE b.fatura_ptr_id IN (
                                  SELECT pk FROM admin_faturas_fatura));
            -- baixa com movimento
            SELECT baixa_fatura_id FROM admin_financeiro_movimentobancario
             WHERE baixa_fatura_id IS NOT NULL;
            -- movimento de competência fechada
            SELECT m.pk FROM admin_financeiro_movimentobancario m
              JOIN admin_financeiro_competenciabancaria c
                ON c.id = m.competencia_bancaria_id
             WHERE c.dt_fechamento_competencia IS NOT NULL;

        Sobrescreva no ModelAdmin com o recorte que fizer sentido.
        """
        return set()

    def _aplicar_list_editable(self, request):
        # `list_editable` na INSTÂNCIA (o template e o formset leem
        # `hasattr(cl.model_admin, "list_editable")` e depois a lista). Sempre
        # grava: o recorte é calculado por REQUISIÇÃO.
        self.list_editable = list(self.list_editable_permitido(request))

    def get_changelist_form(self, request, **kwargs):
        """Form de cada linha da listagem: SÓ os campos de `list_editable`.

        O padrão do Django é `fields = ALL_FIELDS`. Como a tabela só renderiza
        as colunas editáveis, o formset chegava ao POST sem os demais campos e
        todas as linhas ficavam inválidas ("Este campo é obrigatório") — o
        Salvar da listagem não gravava nada.

        Além disso, o formulário é `required=False`: linhas SEM valor no POST
        (ex.: páginas de tabelas vazias no meio do formset) não podem bloquear
        o salvamento das outras.
        """
        campos = list(self.list_editable_permitido(request) or [])
        if campos:
            kwargs.setdefault('fields', campos)
            kwargs.setdefault('formfield_callback', _formfield_nao_obrigatorio)
        return super().get_changelist_form(request, **kwargs)

    def get_changelist_instance(self, request):
        """ChangeList já com o `list_editable` da REQUISIÇÃO aplicado.

        É o PONTO ÚNICO por onde a listagem passa — inclusive quando a classe
        define o próprio `changelist_view` (Pré-Fatura, Fatura) e quando outro
        mixin envolve o `changelist_view`. O Django só monta o FORMSET da
        listagem editável quando `cl.list_editable` é verdadeiro no GET
        (`admin/options.py`), então o recorte precisa estar na instância antes
        disso.
        """
        self._aplicar_list_editable(request)
        return super().get_changelist_instance(request)

    def _nome_do_campo_pk_no_form(self):
        """Nome do campo de PK que o FORMSET da listagem envia no POST.

        O Django procura `form-N-<pk>` — literalmente o nome do campo pk do
        modelo (`id`). Na herança multitable, porém, o campo que carrega a pk
        na linha FILHA é o PARENT LINK (`prefatura_ptr` para `Fatura`,
        `fatura_ptr` para `BaixaFatura`), e é ele que o formset renderiza.

        Sem este ajuste o Django não achava nenhuma pk (`object_pks = []`),
        montava o formset com um queryset VAZIO e o `is_valid()` voltava
        falso — a tela recarregava sem erro e NADA era gravado.
        """
        pai = getattr(self.model, 'parent_link_field', None)
        if pai is not None:
            return pai.name
        return self.model._meta.pk.name

    def _get_edited_object_pks(self, request, prefix):
        """PKs das linhas editadas, aceitando o parent link da herança."""
        nome_pk = self._nome_do_campo_pk_no_form()
        padrao = re.compile(
            r'{}-\d+-{}$'.format(re.escape(prefix), re.escape(nome_pk)))
        pks = [valor for chave, valor in request.POST.items()
               if padrao.match(chave)]
        if pks:
            return pks
        # Fallback: o Django padrão (`form-N-id`) e a pk oculta da linha.
        return super()._get_edited_object_pks(request, prefix)


# ---------------------------------------------------------------------------
def _formfield_nao_obrigatorio(db_field, **kwargs):
    """Campos de `list_editable` sem `blank=True` viram OPCIONAIS no form da
    listagem: linhas SEM valor no POST (checkboxes de outra página, linhas
    travadas pelo fluxo) não bloqueiam as demais."""
    kwargs.setdefault('required', False)
    return db_field.formfield(**kwargs)


class EdicaoComRegrasMixin(ListEditableComRegras):
    """Edição só enquanto o FLUXO da etapa permitir (`motivo_recusa_edicao`).

    Cada modelo do fluxo (Convênio → Pré-Fatura → Fatura → Baixa) define
    `motivo_recusa_edicao()`: devolve o texto amigável do impedimento ou None.
    Com impedimento a tela de alteração NÃO abre: uma mensagem explica o que
    fazer e o usuário volta para a listagem (nunca 403/o debugger).

    Para liberar a edição o usuário corrige a etapa que está travando (ex.:
    exclui o movimento e a baixa, ou marca a fatura como aberta).

    Use como primeiro mixin, antes do `admin.ModelAdmin`.

    A EDIÇÃO EM LINHA segue a mesma regra: `ListEditableComRegras` recorta as
    colunas e o ChangeList editável transforma as linhas travadas em texto.
    """

    mensagem_recusa_edicao = ('Não é possível alterar {registro}: {motivo}')

    def _motivo_recusa_edicao(self, obj):
        metodo = getattr(obj, 'motivo_recusa_edicao', None)
        return metodo() if metodo is not None else None

    def get_object(self, request, object_id, from_field=None):
        """Objeto da tela de alteração (a REGRA é aplicada no `changeform_view`).

        O motivo NÃO é levantado aqui: o `get_object` também é usado na
        confirmação de exclusão, que tem regra própria.
        """
        try:
            return super().get_object(request, object_id, from_field=from_field)
        except PermissionDenied:
            # Registro inacessível: o `changeform_view` transforma em mensagem
            # amigável (nunca a tela de permissão negada).
            return None

    def changeform_view(self, request, object_id=None, form_url='',
                        extra_context=None):
        from django.http import HttpResponseRedirect
        from django.urls import reverse

        alvo = None
        if object_id is not None:
            try:
                from django.contrib.admin.utils import unquote
                alvo = self.model._default_manager.get(
                    pk=unquote(str(object_id)))
            except Exception:
                alvo = None
        motivo = self._motivo_recusa_edicao(alvo) if alvo is not None else None
        if motivo:
            messages.error(
                request,
                self.mensagem_recusa_edicao.format(
                    registro=str(alvo), motivo=motivo))
            opts = self.model._meta
            return HttpResponseRedirect(reverse(
                f'admin:{opts.app_label}_{opts.model_name}_changelist'))
        try:
            return super().changeform_view(
                request, object_id, form_url, extra_context)
        except PermissionDenied:
            opts = self.model._meta
            return HttpResponseRedirect(reverse(
                f'admin:{opts.app_label}_{opts.model_name}_changelist'))

    # ------------------------------------------------------------------
    # MIXIN COMBINADO: exclusão em lote + regras de edição
    # ------------------------------------------------------------------
    def _changelist_view_despacha_acoes(self, original):
        """`changelist_view` + despacho das ações e das EDIÇÕES EM LINHA.

        O POST de edição em linha (listagem editável) NÃO passa pela tela de
        alteração: as linhas travadas são recusadas aqui, com mensagem, e o
        restante é salvo normalmente.
        """
        from functools import wraps

        @wraps(original)
        def changelist_view(this, request, *args, **kwargs):
            acao = (request.POST.get('action')
                    if request.method == 'POST' else None)
            salvar = request.method == 'POST' and '_save' in request.POST
            if acao and not salvar:
                return this.changelist_view_com_acoes(
                    request, kwargs.get('extra_context'),
                    this.post_acoes_em_lote(request))
            if salvar and hasattr(this, '_recusar_edicoes_em_linha'):
                this._recusar_edicoes_em_linha(request)
            return original(this, request, *args, **kwargs)

        return changelist_view

    def _recusar_edicoes_em_linha(self, request):
        """Tira do POST as linhas que NÃO podem ser alteradas.

        O widget da linha travada continua na tela (somente leitura); o resto
        do formulário é salvo normalmente. Listagens SEM `list_editable`
        (sem formset, ex.: contas a receber) não têm edição em linha: nada a
        recusar.
        """
        if not getattr(self, 'list_editable', None):
            return
        try:
            cl = self.get_changelist_instance(request)
        except Exception:
            return
        if not getattr(cl, 'formset', None):
            return  # listagem sem formset: não há edição em linha a recusar
        # O QueryDict do POST é imutável: trabalha numa cópia e devolve.
        dados = request.POST.copy()
        linhas = self._linhas_do_post(request, cl)
        if not linhas:
            return
        # Recorte EM LOTE de linhas travadas (a tela já as deixou como texto).
        try:
            travadas = {str(pk) for pk in self.get_linhas_nao_editaveis(request)}
        except Exception:
            travadas = set()
        for indice, pk in linhas:
            try:
                obj = self.model._default_manager.get(pk=pk)
            except Exception:
                continue
            # Só linhas EFETIVAMENTE alteradas no POST (a tela manda a linha
            # inteira, com os valores atuais).
            try:
                if not self._linha_alterada_no_post(request, indice, obj):
                    continue
            except Exception:
                pass
            motivo = (('já está em andamento no fluxo — altere pela etapa de '
                       'origem.' if str(pk) in travadas else '')
                      or self._motivo_recusa_edicao(obj))
            if not motivo:
                continue
            if not motivo:
                continue
            if not motivo:
                continue
            messages.error(
                request,
                f'{self.model._meta.verbose_name.capitalize()} {pk} não foi '
                f'alterado(a): {motivo}')
            prefixo = f'form-{indice}-'
            for chave in list(dados.keys()):
                if chave.startswith(prefixo):
                    dados.pop(chave, None)
            dados[f'form-{indice}-id'] = str(pk)
        request.POST = dados

    def _linhas_do_post(self, request, cl):
        """[(índice, pk)] das linhas que vieram no POST da listagem.

        A pk normalmente vem no hidden `prefatura_ptr`; sem ele, a posição é
        resolvida pela `ids_da_listagem()` do ChangeList.
        """
        try:
            total = int(request.POST.get('form-TOTAL_FORMS') or 0)
        except (TypeError, ValueError):
            return []
        linhas = []
        sem_pk = []
        for indice in range(total):
            prefixo = f'form-{indice}-'
            pk = request.POST.get(f'{prefixo}prefatura_ptr')
            if not pk:
                pk = request.POST.get(f'{prefixo}fatura_baixada')
            if pk:
                linhas.append((indice, pk))
            else:
                sem_pk.append(indice)
        if sem_pk:
            try:
                pks = cl.ids_da_listagem()
            except Exception:
                pks = []
            for indice in sem_pk:
                if indice < len(pks):
                    linhas.append((indice, pks[indice]))
        return linhas

    @staticmethod
    def _linha_alterada_no_post(request, indice, obj):
        """A linha `indice` do POST difere dos valores atuais do objeto?"""
        prefixo = f'form-{indice}-'
        for campo in ('descricao', 'nr_nota_fiscal', 'valor_fatura',
                      'valor', 'status', 'empenho', 'valor_mensal',
                      'valor_diaria', 'dia_envio', 'dias_pagamento'):
            chave = prefixo + campo
            if chave not in request.POST:
                continue
            enviado = str(request.POST.get(chave) or '').strip()
            atual = getattr(obj, campo, None)
            atual = '' if atual is None else str(atual).strip()
            if enviado != atual:
                if campo in ('valor', 'valor_fatura', 'valor_mensal',
                             'valor_diaria', 'valor_saldo'):
                    # Decimal formatado/“.” × “,” no POST: compara numericamente.
                    try:
                        from decimal import Decimal
                        if Decimal(enviado or '0') == Decimal(atual or '0'):
                            continue
                    except Exception:
                        pass
                return True
        return False

    def __init_subclass__(cls, **kwargs):
        """Em classes SEM a ação em lote, o despacho já é injetado aqui.

        Quando a classe também usa `ExclusaoEmLoteComRegrasMixin`, é ele quem
        injeta (o despacho dele cobre as duas coisas).
        """
        super().__init_subclass__(**kwargs)
        if any('post_acoes_em_lote' in base.__dict__ for base in cls.__mro__[1:]):
            return  # o outro mixin cuida do `changelist_view`
        if 'changelist_view' in cls.__dict__:
            return
        original = next(
            (base.changelist_view for base in cls.__mro__[1:]
             if hasattr(base, 'changelist_view')), None)
        if original is not None:
            cls.changelist_view = cls._changelist_view_despacha_acoes(
                cls, original)


class ExclusaoEmLoteComRegrasMixin:
    """Ação em lote "Excluir selecionados" que respeita as REGRAS do delete.

    O `delete_selected` padrão do Django apaga tudo o que foi selecionado
    (ou abre a tela de confirmação e derruba a tela inteira com
    `ProtectedError`). aqui cada registro passa pelo MESMO teste da exclusão
    individual — o método `motivo_recusa_exclusao()` do modelo (ou o
    `_motivo_recusa_exclusao(obj)` do próprio ModelAdmin, quando existir):

    - sem motivo → excluído;
    - com motivo → NÃO é excluído e o motivo vira mensagem amigável.

    No `list_display` que tenha a coluna `pk`/`id`, as linhas bloqueadas saem
    com "title" (dica de tela) explicando o motivo, antes mesmo da seleção.

    Use como primeiro mixin da classe, antes do `admin.ModelAdmin`.

    Listagens que NÃO usam o `get_actions` padrão (admin com
    `changelist_view` próprio, que trata qualquer POST como formulário) também
    funcionam: o mixin acrescenta o despacho da ação ao `changelist_view`
    (ver `_changelist_view_despacha_acoes`).
    """

    mensagem_sucesso = '{n} registro(s) excluído(s) com sucesso.'
    mensagem_recusa = '{identificacao}: {motivo}'
    max_mensagens_recusa = 10

    def _motivo_recusa_exclusao(self, obj):
        """Motivo para NÃO excluir `obj` (None = pode).

        Le a REGRA do modelo (`motivo_recusa_exclusao()`) e, depois, o
        impedimento adicional do ModelAdmin.
        """
        metodo = getattr(obj, 'motivo_recusa_exclusao', None)
        motivo = metodo() if metodo is not None else None
        if motivo:
            return motivo
        return self._impedimento_extra_exclusao(obj)

    def _impedimento_extra_exclusao(self, obj):
        """Regra adicional do ModelAdmin (None = sem impedimento).

        Sobrescreva quando a regra não estiver no modelo (ex.: o convênio, cuja
        regra depende das pré-faturas geradas).
        """
        return None



    @admin.action(description='Excluir selecionados (respeitando as regras)',
                  permissions=['delete'])
    def excluir_selecionados(self, request, queryset):
        # Seleção feita em OUTRA página ("selecionar todos"): a ação recebe o
        # queryset inteiro do filtro — aqui também vale (cada linha passa pela
        # regra), então basta percorrer o que chegou.
        registros = list(queryset)
        if not registros:
            messages.warning(
                request, 'Selecione pelo menos um registro para excluir.')
            return

        excluidos = 0
        recusas = []
        # Pks confirmadas como excluídas: o `delete()` do Django deixa o objeto
        # em memória sem pk (e `pk is None` NÃO é recusa).
        removidos = set()
        for obj in registros:
            try:
                motivo = self._motivo_recusa_exclusao(obj)
            except Exception as erro:  # nunca derruba a ação
                motivo = f'não foi possível verificar a exclusão ({erro}).'
            if motivo:
                recusas.append((obj, motivo))
                continue
            try:
                self.delete_model(request, obj)
            except Exception as erro:
                recusas.append(
                    (obj, f'a exclusão não pôde ser concluída ({erro}).'))
                continue
            if obj.pk is None or obj.pk in removidos:
                excluidos += 1
            else:
                # A exclusão só é dada como concluída se o registro saiu.
                recusas.append(
                    (obj, 'a exclusão não pôde ser concluída; o registro '
                          'continua no sistema (verifique se ele é usado em '
                          'outro cadastro).'))

        if excluidos:
            messages.success(
                request, self.mensagem_sucesso.format(n=excluidos))
        for obj, motivo in recusas[:self.max_mensagens_recusa]:
            identificacao = str(obj)
            messages.error(
                request,
                self.mensagem_recusa.format(identificacao=identificacao,
                                            motivo=motivo))
        restantes = len(recusas) - self.max_mensagens_recusa
        if restantes > 0:
            messages.warning(
                request,
                f'Mais {restantes} registro(s) selecionado(s) não puderam ser '
                'excluídos pelo mesmo motivo acima. Ajuste-os e tente de novo.')

    def _queryset_das_acoes(self, request, queryset=None):
        """Registros escolhidos no `action` do POST (respeitando o filtro).

        `select_across=0` → as pks do próprio POST (o que ESTÁ na tela);
        `select_across=1` → o queryset inteiro da listagem (o `get_queryset`
        pode recortar por permissão/estabelecimento).
        """
        from django.http import QueryDict
        from django.utils.http import urlencode

        if queryset is None:
            queryset = self.get_queryset(request)
        selecionadas = request.POST.getlist('_selected_action')
        if request.POST.get('select_across') != '1' and selecionadas:
            queryset = queryset.filter(pk__in=selecionadas)
        return queryset

    def post_acoes_em_lote(self, request, queryset=None):
        """Mapa `ação -> método` usado quando a listagem não usa o
        `get_actions` padrão (ex.: `changelist_view` próprio)."""
        queryset = self._queryset_das_acoes(request, queryset)
        return {
            'excluir_selecionados': (
                lambda req, qs=queryset: self.excluir_selecionados(req, qs)),
        }

    def changelist_view_com_acoes(self, request, extra_context=None,
                                  acoes=None):
        """Executa a AÇÃO em lote do POST e devolve o GET da listagem.

        Depois de rodar, a mensagem fica na sessão e a tela volta pelo GET
        (mesma URL, mesmos filtros) — a listagem já mostra o resultado.
        """
        nome = request.POST.get('action') or ''
        metodo = (acoes or {}).get(nome)
        if metodo is not None and self.has_delete_permission(request):
            try:
                metodo(request, self._queryset_das_acoes(request))
            except Exception as erro:  # nunca derruba a tela
                messages.error(
                    request,
                    f'Não foi possível concluir a ação “{nome}”: {erro}')
        else:
            messages.error(
                request, 'Ação em lote não reconhecida. Nada foi alterado.')
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(request.get_full_path())

    def _changelist_view_despacha_acoes(self, original):
        """`changelist_view` do Django + o despacho das ações em lote.

        Substitui o método original na classe em que o mixin for usado (só
        quando ela NÃO define o próprio `changelist_view`): assim o
        `super().changelist_view` continua chamando o próximo da MRO, sem
        quebrar a colaboração entre os mixins.
        """
        from functools import wraps

        @wraps(original)
        def changelist_view(this, request, extra_context=None):
            # Este despacho pode ser o PRIMEIRO `changelist_view` da MRO e
            # chamar direto o do Django — pulando o `ListEditableComRegras`,
            # que é quem define `list_editable` NA INSTÂNCIA. Sem essa lista o
            # Django NÃO cria o formset no GET (admin/options.py:
            # `elif cl.list_editable and ...`) e a listagem editável não
            # aparece. Por isso o recorte é aplicado aqui também.
            if hasattr(this, '_aplicar_list_editable'):
                this._aplicar_list_editable(request)
            if (request.method == 'POST' and '_save' not in request.POST
                    and request.POST.get('action')):
                return this.changelist_view_com_acoes(
                    request, extra_context, this.post_acoes_em_lote(request))
            return original(this, request, extra_context)

        return changelist_view

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Toda classe com a ação em lote tem o despacho no `changelist_view`
        # (ações + edições em linha). O método só é instalado aqui quando a
        # própria classe não o define; `get_actions` refaz a instalação.
        if cls.__dict__.get('post_acoes_em_lote') is None:
            return  # classe sem a ação em lote: não toca no `changelist_view`
        if 'changelist_view' in cls.__dict__:
            return  # a própria classe chama o despacho
        import functools
        metodo = next(
            base.__dict__['_changelist_view_despacha_acoes']
            for base in cls.__mro__
            if '_changelist_view_despacha_acoes' in base.__dict__)
        original = next(
            (base.changelist_view for base in cls.__mro__[1:]
             if hasattr(base, 'changelist_view')), None)
        if original is not None:
            cls.changelist_view = functools.partial(metodo, cls, original)
            cls.changelist_view._despacha_acoes = True

    def _delete_view_com_regras(self, original, request, object_id,
                                extra_context=None):
        """Confirmação de exclusão com as REGRAS do registro.

        O `has_delete_permission(obj=...)` devolve False com o motivo já
        registrado em mensagem (a linha continua na tela, sem a tela de
        erro de permissão). Aqui a recusa vira VOLTA para a listagem com a
        mensagem, em vez de `PermissionDenied` (403).
        """
        import re
        from urllib.parse import unquote
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        from django.contrib.admin.utils import unquote as _unquote_admin

        # O objeto é buscado pela pk CRUA: o `get_object` do Django faria
        # `unquote` de novo (pk "12" → "2") e diria que o registro não existe.
        try:
            obj = self.model._default_manager.get(
                pk=_unquote_admin(unquote(str(object_id))))
        except Exception:
            obj = None
        if obj is not None and not self.has_delete_permission(
                request, obj=obj):
            # "/admin/app/modelo/<pk>/delete/" → listagem do modelo.
            caminho = re.sub(r'/[^/]+/delete/?$', '/', request.path)
            if not caminho.endswith('/'):
                caminho += '/'
            return HttpResponseRedirect(caminho)
        try:
            return original(self, request, object_id,
                            extra_context=extra_context)
        except PermissionDenied:
            # Qualquer outra recusa vira mensagem amigável (nunca 403).
            messages.error(
                request,
                'Não é possível excluir este registro. Verifique se ele é '
                'usado em outro cadastro e volte para a listagem.')
            opts = self.model._meta
            return HttpResponseRedirect(reverse(
                f'admin:{opts.app_label}_{opts.model_name}_changelist'))

    def delete_view(self, request, object_id, extra_context=None):
        # Resolve o PRÓXIMO `delete_view` da MRO EM TEMPO DE CHAMADA: o
        # `dominios.breadcrumbs` envolve as classes registradas, e o wrapper
        # dele pode estar antes deste mixin na cadeia.
        mod = __name__
        original = next(
            base.__dict__['delete_view'] for base in type(self).__mro__[1:]
            if 'delete_view' in base.__dict__
            and base.__dict__['delete_view'].__module__ != mod)
        return self._delete_view_com_regras(
            original, request, object_id, extra_context=extra_context)

    def get_actions(self, request):
        """Troca o `delete_selected` padrão pela ação que respeita as regras."""
        # Garante o despacho das AÇÕES e das EDIÇÕES EM LINHA no
        # `changelist_view` (o `get_actions` roda quando o admin é
        # registrado, antes da primeira listagem).
        cls = type(self)
        original = cls.changelist_view
        import functools
        metodo = next(
            base.__dict__['_changelist_view_despacha_acoes']
            for base in cls.__mro__
            if '_changelist_view_despacha_acoes' in base.__dict__)
        if getattr(original, '_despacha_acoes', False) is not True:
            cls.changelist_view = functools.partial(metodo, cls, original)
            cls.changelist_view._despacha_acoes = True
        actions = super().get_actions(request)
        actions.pop('delete_selected', None)
        if 'delete' not in self.get_model_perms(request) or \
                not self.has_delete_permission(request):
            actions.pop('excluir_selecionados', None)
        return actions
