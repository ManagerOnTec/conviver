# middlewares.py

from django.contrib import messages
from admin_automacoes.models import QtdUsuariosSimultaneos
from django.http import HttpResponse
from django.contrib.sessions.models import Session
from datetime import datetime
from django.urls import resolve
from admin_logs.models import ProntuarioAcessos
from django.http import Http404
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.contrib.auth import get_user
from admin_parametros.models import ConfiguracaoSessao
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

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # 🔓 Libera admin
        if request.path.startswith('/admin/'):
            return self.get_response(request)

        user = get_user(request)

        # 🔓 Libera usuário admin
        if user.is_authenticated and user.username == 'admin':
            return self.get_response(request)

        if user.is_authenticated:
            try:
                config = QtdUsuariosSimultaneos.objects.first()
                max_logged_in_users = config.max_usuarios_simultaneos if config and config.max_usuarios_simultaneos else 10
            except Exception:
                max_logged_in_users = 10

            try:
                active_sessions = Session.objects.filter(
                    expire_date__gte=timezone.now()
                )
                current_logged_in_users = active_sessions.count()
            except Exception:
                current_logged_in_users = 0

            if current_logged_in_users > max_logged_in_users:

                login_url = reverse('login')
                admin_url = reverse('admin:login')

                return HttpResponse(f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<title>Limite de Usuários</title>
<style>
    body {{
        margin: 0;
        padding: 0;
        height: 100vh;
        background: linear-gradient(135deg, #000000, #1a1a1a);
        display: flex;
        justify-content: center;
        align-items: center;
        font-family: Arial, Helvetica, sans-serif;
        color: #ffffff;
    }}

    .card {{
        background: #111;
        padding: 40px;
        border-radius: 12px;
        box-shadow: 0 0 25px rgba(0,0,0,0.8);
        width: 420px;
        text-align: center;
        border: 1px solid #333;
    }}

    h2 {{
        margin-bottom: 20px;
        font-weight: 600;
    }}

    p {{
        font-size: 14px;
        color: #ccc;
    }}

    .stats {{
        margin: 20px 0;
        font-size: 13px;
        color: #888;
    }}

    .btn {{
        display: inline-block;
        padding: 10px 18px;
        margin: 10px 5px;
        text-decoration: none;
        border-radius: 6px;
        font-size: 14px;
        transition: 0.3s;
    }}

    .btn-admin {{
        background: #ff4d4d;
        color: #fff;
    }}

    .btn-admin:hover {{
        background: #e60000;
    }}

    .btn-login {{
        background: #2e86ff;
        color: #fff;
    }}

    .btn-login:hover {{
        background: #1a5ed9;
    }}

    hr {{
        border: none;
        border-top: 1px solid #333;
        margin: 25px 0;
    }}
</style>
</head>
<body>
    <div class="card">
        <h2>Limite de Usuários Atingido</h2>

        <div class="stats">
            Máximo permitido: {max_logged_in_users}<br>
            Usuários ativos: {current_logged_in_users}
        </div>

        <hr>

        <p>Entre em contato com o administrador do sistema.</p>

        <a href="{admin_url}" class="btn btn-admin">
            Área Administrativa
        </a>

        <a href="{login_url}" class="btn btn-login">
            Tentar Login Novamente
        </a>
    </div>
</body>
</html>
""", status=403)

        return self.get_response(request)