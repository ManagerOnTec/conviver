from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.contrib.sessions.models import Session
from django.utils import timezone


def _sessoes_do_usuario(user, excluir_key=None):
    """Sessões ativas (não expiradas) autenticadas para o usuário."""
    alvo = str(user.pk)
    ativas = Session.objects.filter(expire_date__gte=timezone.now())

    for session in ativas.iterator():
        try:
            data = session.get_decoded()
        except Exception:
            # Sessão corrompida: não deve impedir o login.
            continue
        if data.get('_auth_user_id') != alvo:
            continue
        if excluir_key and session.session_key == excluir_key:
            continue
        yield session


@receiver(user_logged_in)
def remove_other_sessions(sender, request, user, **kwargs):
    """
    Ao logar, remove todas as outras sessões do mesmo usuário.
    Mantém apenas a sessão atual.

    Sessões órfãs (cookie já descartado, mas registro ainda não expirado no
    banco) também são removidas — sem isso o admin acumulava várias linhas
    para o mesmo usuário em "Log - Sessões - Usuários Logados".
    """
    current_session_key = getattr(request.session, 'session_key', None)

    for session in list(_sessoes_do_usuario(user, excluir_key=current_session_key)):
        session.delete()


@receiver(user_logged_out)
def remove_session_on_logout(sender, request, user, **kwargs):
    """
    Garante que o registro da sessão seja removido no logout.

    ``auth.logout()`` já apaga a sessão, mas quando a chave é rotacionada
    antes do logout o registro antigo pode permanecer listado.
    """
    if request is None or user is None:
        return
    for session in list(_sessoes_do_usuario(user)):
        session.delete()