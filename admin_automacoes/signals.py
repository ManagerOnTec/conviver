from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.contrib.sessions.models import Session
from django.utils import timezone


@receiver(user_logged_in)
def remove_other_sessions(sender, request, user, **kwargs):
    """
    Ao logar, remove todas as outras sessões do mesmo usuário.
    Mantém apenas a sessão atual.
    """

    current_session_key = request.session.session_key

    sessions = Session.objects.filter(
        expire_date__gte=timezone.now()
    )

    for session in sessions:
        data = session.get_decoded()
        if data.get('_auth_user_id') == str(user.id):
            if session.session_key != current_session_key:
                session.delete()