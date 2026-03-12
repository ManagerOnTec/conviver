from django.contrib.auth import get_user_model
from django.utils.encoding import force_str
from django.template.loader import render_to_string
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from dominios.utils import obter_permissoes_por_usuario
from django.shortcuts import render
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.shortcuts import redirect, render
from django.views.generic import TemplateView
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from logging import INFO, DEBUG
from logging import basicConfig
from logging import info, debug
from admin_automacoes. models import EmailConfiguration
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from admin_cadastros.models import Estabelecimento
from django.http import JsonResponse

basicConfig(
    level=INFO,
    filename='logs.log',
    filemode='a',
    format='%(levelname)s:%(asctime)s:%(message)s'
)


def home(request):
    context = {
        'mostrar_rodape': False,
        'mostrar_nav': True,
        'titulo': 'ManagerONTEC',
        'title': 'home',

    }
    return render(request, 'contas/home.html', context)


def login(request):

    context = {
        'mostrar_rodape': False,
        'mostrar_nav': True,
        'titulo': 'ManagerONTEC',
        'title': 'login',

    }

    if request.user.is_authenticated:
        # Se o usuário já estiver logado, faça logout e redirecione para a página de login novamente
        return redirect('logout')
    elif request.method == 'POST':
        usuario = request.POST['usuario']
        senha = request.POST['senha']
        user = auth.authenticate(request, username=usuario, password=senha)

        if not user:
            messages.error(request, 'Usuário ou senha inválidos!')
            return render(request, 'contas/login.html', context)

        # Verificar se a senha foi alterada

        if user.username == 'admin':
            auth.login(request, user)
            return redirect('/admin')

        try:
            perfil = user.perfil
            senha_alterada = perfil.senha_alterada
        except:
            messages.warning(
                request, 'Perfil de usuário não liberado, contate o administrador do sistema!')
            return redirect('logout')

        auth.login(request, user)
        if not senha_alterada:
            return redirect('alterar')
        else:
            return redirect('select_estabelecimento')
    else:
        return render(request, 'contas/login.html', context)


@login_required(login_url='login')
def alterar(request):

    # Se o usuário não está autenticado, redirecione para a página de login
    if not request.user.is_authenticated:
        messages.warning(
            request, "Sua sessão expirou. Por favor, faça login novamente.")
        # substitua 'login' com sua URL de login
        return HttpResponseRedirect(reverse('login'))

    estabelecimento_id = request.session.get("estabelecimento_id")
    # Restante do seu código...

    if estabelecimento_id:
        estabelecimento = Estabelecimento.objects.get(pk=estabelecimento_id)
    else:
        estabelecimento = None

    context = {
        'mostrar_rodape': False,
        'mostrar_nav': True,
        'titulo': 'Alteração de Senha',
        'title': 'alterar',
        'estabelecimento': estabelecimento,
    }

    if request.method != 'POST':
        return render(request, 'contas/alterar.html', context)

    if request.method == 'POST':
        usuario = request.POST.get('usuario')
        senha_atual = request.POST.get('senha_atual')
        novasenha = request.POST.get('novasenha')
        confirmasenha = request.POST.get('confirmasenha')
        user = User.objects.get(username=usuario)

        if not user.check_password(senha_atual):
            messages.error(request, 'Senha atual incorreta.')
            return render(request, 'contas/alterar.html', context)

        if novasenha != confirmasenha or not novasenha:
            messages.error(request, 'Por favor corriga as senhas!')
            return render(request, 'contas/alterar.html', context)
        elif novasenha != '' and novasenha is not None:
            try:
                validate_password(novasenha, user=user)
            except ValidationError as e:
                messages.error(request, ', '.join(e))
                return render(request, 'contas/alterar.html', context)
            messages.success(
                request, 'Senha alterada com sucesso, faça seu login!')
            user.set_password(novasenha)
        user.save()
        perfil = user.perfil
        perfil.senha_alterada = True
        perfil.save()
        auth.login(request, user)
        return redirect('logout')


@login_required(login_url='login')
def logout(request):
    auth.logout(request)
    messages.warning(request, 'Usuário Deslogado!')
    return redirect('login')


@login_required(login_url='login')
def select_estabelecimento(request):

    # Se o usuário não está autenticado, redirecione para a página de login
    if not request.user.is_authenticated:
        messages.warning(
            request, "Sua sessão expirou. Por favor, faça login novamente.")
        # substitua 'login' com sua URL de login
        return HttpResponseRedirect(reverse('login'))

    permissoes = obter_permissoes_por_usuario(request.user.id)

    context = {
        'mostrar_rodape': False,
        'mostrar_nav': True,
        'titulo': 'Estabelecimento(s)',
        'title': 'select_estabelecimento',
        'permissoes': permissoes,
    }

    if request.method == "POST":
        estabelecimento_id = request.POST.get("estabelecimento")
        try:
            estabelecimento = Estabelecimento.objects.get(id=estabelecimento_id)
            request.session["estabelecimento_id"] = estabelecimento.id
            # Redirecionar para a página inicial ou dashboard do usuário
            return redirect("cadastros_index")
        except Estabelecimento.DoesNotExist:
            messages.error(request, "Estabelecimento não encontrado.")
            return redirect("select_estabelecimento")

    try:
        estabelecimento = request.user.perfil.estabelecimento.all()
        if not estabelecimento.exists():
            raise ObjectDoesNotExist

    except ObjectDoesNotExist:
        # Renderizar um template diferente ou mostrar uma mensagem de erro
        # return render(request, "contas/sem_estabelecimento.html")
        messages.warning(
            request, "Você não possui nenhum estabelecimento liberado. Contate o administrador do sistema e solicite liberação de acesso ao estabelecimento desejado")
        return redirect("logout")

    return render(request, "contas/select_estabelecimento.html", {"estabelecimento": estabelecimento, **context})


def esqueci(request):
    context = {
        'mostrar_rodape': False,
        'mostrar_nav': True,
        'titulo': 'Recuperação de Senha',
        'title': 'esqueci',
    }

    if request.method == 'POST':
        email = request.POST['email']

        if not email:
            messages.error(request, 'E-mail inválido.')
            return render(request, 'contas/esqueci.html', context)
        else:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                messages.warning(request, 'E-mail não encontrado.')
                return render(request, 'contas/esqueci.html', context)

            try:
                config = EmailConfiguration.objects.get(
                    regra='redefinicao de senha')
            except EmailConfiguration.DoesNotExist:
                messages.warning(
                    request, 'Recuperar por e-mail desabilitado. Contate o administrador do sistema para criar regra de reruperação por e-mail com o seguinte nome "redefinicao de senha" ou para alterar sua senha no módulo de Administração e Cadastros.')
                return render(request, 'contas/esqueci.html', context)

            from django.core.mail import get_connection, EmailMessage

            try:
                connection = get_connection(
                    backend=config.email_backend,
                    host=config.email_host,
                    port=config.email_port,
                    username=config.email_host_user,
                    password=config.email_host_password,
                    use_tls=config.email_use_tls
                )

                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)

                mail_subject = 'Redefinição de senha'
                message = render_to_string('contas/resetar_senha_email.html', {
                    'user': user,
                    'domain': get_current_site(request).domain,
                    'uid': uid,
                    'token': token,
                })

                email_message = EmailMessage(
                    mail_subject,
                    '',
                    config.email_host_user,
                    [user.email],
                    connection=connection
                )
                # Aqui está a adição para tratar o corpo como HTML
                email_message.content_subtype = 'html'
                email_message.body = message
                email_message.send()

                messages.success(request, 'E-mail enviado com sucesso!')
                return redirect('login')

            except Exception as e:
                messages.error(
                    request, f'Falha no envio do e-mail. Error: {e}')
                return render(request, 'contas/esqueci.html', context)

    # Se não for um POST, apenas renderizar a página normalmente
    return render(request, 'contas/esqueci.html', context)


def password_reset_confirm(request, uidb64=None, token=None):
    UserModel = get_user_model()
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = UserModel._default_manager.get(pk=uid)
    except (TypeError, ValueError, OverflowError, UserModel.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            new_password = request.POST.get('novasenha')
            password_confirm = request.POST.get('confirmasenha')
            if new_password == password_confirm:
                try:
                    validate_password(new_password, user=user)
                except ValidationError as e:
                    messages.error(request, ', '.join(e))
                    return render(request, 'contas/resetar_senha.html', {'uidb64': uidb64, 'token': token})
                user.set_password(new_password)
                user.save()
                messages.success(request, "Senha redefinida com sucesso!")
                # replace 'login' with the name of your login view
                return redirect('login')
            else:
                messages.error(request, "As senhas não correspondem!")
        return render(request, 'contas/resetar_senha.html', {'uidb64': uidb64, 'token': token})
    else:
        messages.error(request, "O link de redefinição de senha é inválido!")
        # replace 'password_reset' with the name of your password reset view
        return redirect('password_reset')
