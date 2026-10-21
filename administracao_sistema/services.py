"""
Serviços do módulo Administração do Sistema.

- Duração de sessão (Configuração de Sessões)
- Quantidade de usuários simultâneos
"""

from django.contrib.sessions.models import Session
from django.utils import timezone


def sessoes_ativas_por_usuario():
    """
    Retorna ``{user_id: quantidade_de_sessoes}`` para sessões não expiradas.

    Sessões corrompidas ou sem autenticação são ignoradas.
    """
    contagem = {}
    for session in Session.objects.filter(expire_date__gte=timezone.now()) \
            .iterator():
        try:
            user_id = session.get_decoded().get('_auth_user_id')
        except Exception:
            continue
        if user_id:
            contagem[user_id] = contagem.get(user_id, 0) + 1
    return contagem


def usuarios_autenticados_distintos(excluir_user_id=None):
    """Conjunto de IDs de usuários com pelo menos uma sessão ativa."""
    ids = set(sessoes_ativas_por_usuario().keys())
    if excluir_user_id is not None:
        ids.discard(str(excluir_user_id))
    return ids


def limite_usuarios_simultaneos():
    """Valor configurado, ou None se não configurado."""
    from administracao_sistema.models import QtdUsuariosSimultaneos

    try:
        config = QtdUsuariosSimultaneos.objects.first()
    except Exception:
        return None
    if not config or not config.max_usuarios_simultaneos:
        return None
    return int(config.max_usuarios_simultaneos)


def pode_iniciar_sessao(user):
    """
    Verifica se ``user`` pode iniciar uma nova sessão.

    Regras:
    - ``admin`` nunca é bloqueado.
    - Se o usuário já possui sessão ativa, ele não consome vaga nova.
    - Caso contrário, exige ``usuarios_ativos < limite``.

    Retorna (permitido, limite, usuarios_ativos).
    """
    limite = limite_usuarios_simultaneos()
    if limite is None:
        return True, None, 0

    ativos = usuarios_autenticados_distintos()

    if getattr(user, 'username', None) == 'admin':
        return True, limite, len(ativos)

    if str(user.pk) in ativos:
        return True, limite, len(ativos)

    return len(ativos) < limite, limite, len(ativos)


def duracao_sessao_configurada():
    """
    Duração da sessão em segundos, ou None se não configurada.

    O admin descreve ``duracao_sessao`` como SEGUNDOS (ex.: 3600 = 1 hora).
    """
    from administracao_sistema.models_parametros import ConfiguracaoSessao

    try:
        config = ConfiguracaoSessao.objects.first()
    except Exception:
        return None
    if not config or not config.duracao_sessao:
        return None
    return int(config.duracao_sessao)
