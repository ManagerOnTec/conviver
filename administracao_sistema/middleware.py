"""
Middleware de duração de sessão.

``ConfiguracaoSessaoMiddleware`` aplica a duração definida em
Administração do Sistema > Configurações de Sessões.

Comportamento: **sessão deslizante** — cada request autenticado renova a
expiração para ``duracao_sessao`` segundos. O usuário só é deslogado após ficar
``duracao_sessao`` segundos SEM interagir.

Problemas corrigidos:
- A duração é recarregada periodicamente, refletindo alterações no admin sem
  reiniciar o processo.
- ``session.modified = True`` força o SAVE. Com
  ``SESSION_SAVE_EVERY_REQUEST = False``, apenas chamar ``set_expiry`` não
  grava nada no banco e a sessão continuava com o SESSION_COOKIE_AGE do
  settings (era por isso que configurar 5s não derrubava a sessão).
- Sem "margem" fixa maior que a duração: funciona com valores pequenos.
"""

import time
from datetime import timedelta

from django.utils import timezone

from administracao_sistema.services import duracao_sessao_configurada

# Tempo (segundos) de cache da configuração em memória.
CACHE_CONFIG_SEGUNDOS = 5


class ConfiguracaoSessaoMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response
        self._duracao = None
        self._cache_em = 0.0

    def _duracao_configurada(self):
        agora = time.monotonic()
        if self._duracao is None or agora - self._cache_em > CACHE_CONFIG_SEGUNDOS:
            self._duracao = duracao_sessao_configurada()
            self._cache_em = agora
        return self._duracao

    def __call__(self, request):
        if request.user.is_authenticated:
            self._aplicar_duracao(request)
        return self.get_response(request)

    def _aplicar_duracao(self, request):
        duracao = self._duracao_configurada()
        if duracao is None:
            return

        session = request.session
        expira_em = (session.get_expiry_date() - timezone.now()).total_seconds()

        # Regra: o tempo é SEMPRE contado desde a última ação (request).
        # A expiração é reiniciada em todo request autenticado.
        #
        # Importante: usamos um datetime ABSOLUTO, e não segundos. Quando
        # `_session_expiry` já está gravado como int, o Django reutiliza esse
        # int no próximo `get_expiry_age` e a expiração nunca é recalculada
        # (era por isso que a sessão caía mesmo com requests frequentes).
        nova_expiracao = timezone.now() + timedelta(seconds=duracao)

        if expira_em <= 0 or abs(expira_em - duracao) >= 1:
            session.set_expiry(nova_expiracao)
            # Sem isto o Django não grava (SESSION_SAVE_EVERY_REQUEST=False)
            # e a nova expiração se perde.
            session.modified = True
