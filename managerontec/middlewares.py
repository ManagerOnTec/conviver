# middlewares.py

from django.contrib import messages
from administracao_sistema.models import QtdUsuariosSimultaneos
from django.http import HttpResponse
from django.contrib.sessions.models import Session
from datetime import datetime
from django.urls import resolve
from administracao_sistema.models_logs import ProntuarioAcessos
from django.http import Http404
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.contrib.auth import get_user
from administracao_sistema.models_parametros import ConfiguracaoSessao
from django.utils.deprecation import MiddlewareMixin
from django.urls import reverse

class RegistroAcessoMiddleware(LoginRequiredMixin):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            if request.path.startswith('/prontuarios/prontuario_detalhe/'):
                us_acesso = request.user
                dt_acesso = timezone.make_aware(datetime.now())
                item_prontuario = 'prontuario'
                motivo_acesso = 'log prontuario'
                pk = resolve(request.path).kwargs.get('pk')
                prontuario = ProntuarioAcessos(
                    atendimento_id=pk,
                    us_acesso=us_acesso,
                    dt_acesso=dt_acesso,
                    motivo_acesso=motivo_acesso,
                    item_prontuario=item_prontuario,
                )
                if request.user.is_authenticated:
                    prontuario.save()

            if request.path.startswith('/prontuarios/evolucao_listar/'):
                us_acesso = request.user
                dt_acesso = timezone.make_aware(datetime.now())
                item_prontuario = 'evolucao'
                motivo_acesso = 'log evolucao'
                atendimento_id = resolve(
                    request.path).kwargs.get('atendimento_id')
                prontuario = ProntuarioAcessos(
                    atendimento_id=atendimento_id,
                    us_acesso=us_acesso,
                    dt_acesso=dt_acesso,
                    motivo_acesso=motivo_acesso,
                    item_prontuario=item_prontuario,
                )
                if request.user.is_authenticated:
                    prontuario.save()

            if request.path.startswith('/prontuarios/diagnostico_listar/'):
                us_acesso = request.user
                dt_acesso = timezone.make_aware(datetime.now())
                item_prontuario = 'diagnostico'
                motivo_acesso = 'log diagnostico'
                atendimento_id = resolve(
                    request.path).kwargs.get('atendimento_id')
                prontuario = ProntuarioAcessos(
                    atendimento_id=atendimento_id,
                    us_acesso=us_acesso,
                    dt_acesso=dt_acesso,
                    motivo_acesso=motivo_acesso,
                    item_prontuario=item_prontuario,
                )
                if request.user.is_authenticated:
                    prontuario.save()

            if request.path.startswith('/prontuarios/psicoterapia_listar/'):
                us_acesso = request.user
                dt_acesso = timezone.make_aware(datetime.now())
                item_prontuario = 'psicoterapia'
                motivo_acesso = 'log psicoterapia'
                atendimento_id = resolve(
                    request.path).kwargs.get('atendimento_id')
                prontuario = ProntuarioAcessos(
                    atendimento_id=atendimento_id,
                    us_acesso=us_acesso,
                    dt_acesso=dt_acesso,
                    motivo_acesso=motivo_acesso,
                    item_prontuario=item_prontuario,
                )
                if request.user.is_authenticated:
                    prontuario.save()

            if request.path.startswith('/prontuarios/prescicao_listar/'):
                us_acesso = request.user
                dt_acesso = timezone.make_aware(datetime.now())
                item_prontuario = 'prescricao'
                motivo_acesso = 'log prescricao'
                atendimento_id = resolve(
                    request.path).kwargs.get('atendimento_id')
                prontuario = ProntuarioAcessos(
                    atendimento_id=atendimento_id,
                    us_acesso=us_acesso,
                    dt_acesso=dt_acesso,
                    motivo_acesso=motivo_acesso,
                    item_prontuario=item_prontuario,
                )
                if request.user.is_authenticated:
                    prontuario.save()

            if request.path.startswith('/prontuarios/sinais_vitais_listar/'):
                us_acesso = request.user
                dt_acesso = timezone.make_aware(datetime.now())
                item_prontuario = 'sinais vitais'
                motivo_acesso = 'log sinais vitais'
                atendimento_id = resolve(
                    request.path).kwargs.get('atendimento_id')
                prontuario = ProntuarioAcessos(
                    atendimento_id=atendimento_id,
                    us_acesso=us_acesso,
                    dt_acesso=dt_acesso,
                    motivo_acesso=motivo_acesso,
                    item_prontuario=item_prontuario,
                )
                if request.user.is_authenticated:
                    prontuario.save()

            if request.path.startswith('/prontuarios/sae_listar/'):
                us_acesso = request.user
                dt_acesso = timezone.make_aware(datetime.now())
                item_prontuario = 'sae'
                motivo_acesso = 'log sae'
                atendimento_id = resolve(
                    request.path).kwargs.get('atendimento_id')
                prontuario = ProntuarioAcessos(
                    atendimento_id=atendimento_id,
                    us_acesso=us_acesso,
                    dt_acesso=dt_acesso,
                    motivo_acesso=motivo_acesso,
                    item_prontuario=item_prontuario,
                )
                if request.user.is_authenticated:
                    prontuario.save()

            if request.path.startswith('/prontuarios/plano_cuidados_listar/'):
                us_acesso = request.user
                dt_acesso = timezone.make_aware(datetime.now())
                item_prontuario = 'plano de cuidados'
                motivo_acesso = 'log plano de cuidados'
                atendimento_id = resolve(
                    request.path).kwargs.get('atendimento_id')
                prontuario = ProntuarioAcessos(
                    atendimento_id=atendimento_id,
                    us_acesso=us_acesso,
                    dt_acesso=dt_acesso,
                    motivo_acesso=motivo_acesso,
                    item_prontuario=item_prontuario,
                )
                if request.user.is_authenticated:
                    prontuario.save()

            if request.path.startswith('/prontuarios/perdas_ganhos_listar/'):
                us_acesso = request.user
                dt_acesso = timezone.make_aware(datetime.now())
                item_prontuario = 'perdas e ganhos'
                motivo_acesso = 'log perdas e ganhos'
                atendimento_id = resolve(
                    request.path).kwargs.get('atendimento_id')
                prontuario = ProntuarioAcessos(
                    atendimento_id=atendimento_id,
                    us_acesso=us_acesso,
                    dt_acesso=dt_acesso,
                    motivo_acesso=motivo_acesso,
                    item_prontuario=item_prontuario,
                )
                if request.user.is_authenticated:
                    prontuario.save()

            if request.path.startswith('/prontuarios/adep_listar/'):
                us_acesso = request.user
                dt_acesso = timezone.make_aware(datetime.now())
                item_prontuario = 'adep'
                motivo_acesso = 'log adep'
                atendimento_id = resolve(
                    request.path).kwargs.get('atendimento_id')
                prontuario = ProntuarioAcessos(
                    atendimento_id=atendimento_id,
                    us_acesso=us_acesso,
                    dt_acesso=dt_acesso,
                    motivo_acesso=motivo_acesso,
                    item_prontuario=item_prontuario,
                )
                if request.user.is_authenticated:
                    prontuario.save()

        response = self.get_response(request)
        return response




## CONTROLE DE ACESSO


class LimitUserLoginsMiddleware:
    """
    Verifica o limite de USUÁRIOS simultâneos a cada request autenticado.

    A contagem é feita por usuário distinto (não por sessão) e o bloqueio de
    NOVOS logins é aplicado na view de login (``contas.views.login``), onde se
    sabe que a sessão ainda não existia. Aqui só se marca o request para que
    telas possam exibir o estado (``request.limite_usuarios``).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)

        # admin sempre tem acesso, inclusive à área administrativa.
        if user is not None and user.is_authenticated and user.username == 'admin':
            request.limite_usuarios = None
            return self.get_response(request)

        from administracao_sistema.services import (
            limite_usuarios_simultaneos, usuarios_autenticados_distintos)

        limite = limite_usuarios_simultaneos()
        if limite is not None:
            request.limite_usuarios = {
                'limite': limite,
                'ativos': len(usuarios_autenticados_distintos()),
            }

        return self.get_response(request)
