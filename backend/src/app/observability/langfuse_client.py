"""Cliente Langfuse + auto-integración con LiteLLM.

Mejor práctica oficial de Langfuse v2 verificada en docs (2026-05-24): el SDK
inicializa el cliente HTTP de forma perezosa (no abre conexiones hasta emitir
la primera traza), así que envolver `Langfuse(...)` en try/except no aporta
valor — un fallo solo aparecería en la primera llamada real, no aquí. La
degradación graceful viene de devolver `None` cuando faltan credenciales.

`init_observability()` se llama explícitamente desde `app.main` al boot de
FastAPI; el módulo NO tiene side effects al import para mantener la suite
de tests aislada y permitir reemplazar la configuración antes del arranque
(reemplaza el side-effect-at-import que existía en una iteración anterior
de T8 — patrón identificado en code review como riesgo de test pollution).
"""

from functools import lru_cache

import litellm
from langfuse import Langfuse

from app.config import settings


@lru_cache(maxsize=1)
def get_client() -> Langfuse | None:
    """Devuelve un cliente Langfuse si hay credenciales, si no None.

    Sin claves en `.env`, la app sigue arrancando sin telemetría. Los
    decoradores `@observe` de Langfuse v2 son tolerantes a cliente=None
    por diseño (se convierten en no-ops silenciosos), así que los callers
    de los decoradores semánticos no necesitan verificar nada.

    NOTA para tests: el resultado se cachea con `@lru_cache(maxsize=1)`. Si
    un test muta `settings.langfuse_public_key` o `langfuse_secret_key` con
    monkeypatch, debe invocar `get_client.cache_clear()` antes de volver a
    llamar `get_client()`, o seguirá recibiendo el resultado cacheado de la
    ejecución previa.
    """
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return None
    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )


def configure_litellm_callbacks(client: Langfuse | None) -> None:
    """Habilita el auto-tracing de LiteLLM hacia Langfuse.

    Con cliente Langfuse activo, cada llamada a `litellm.completion()` emite
    automáticamente un span `generation` a Langfuse con `model`,
    `tokens_in/out`, `cost`, `latency`, `prompt`, `response` — sin escribir
    código de tracing en el wrapper T7. Combinado con `@trace_classifier`
    en F3, el span del clasificador se convierte en padre del span
    `generation` automático de LiteLLM = árbol de observabilidad perfecto.

    Idempotente: llamadas repetidas no duplican "langfuse" en los callbacks.
    Sin cliente, es no-op.
    """
    if client is None:
        return
    if "langfuse" not in litellm.success_callback:
        litellm.success_callback.append("langfuse")
    if "langfuse" not in litellm.failure_callback:
        litellm.failure_callback.append("langfuse")


def init_observability() -> None:
    """Inicializa la observabilidad del proyecto.

    Punto de entrada explícito invocado desde `app.main` al boot de FastAPI.
    Obtiene el cliente Langfuse (None si no hay credenciales) y configura
    los callbacks automáticos de LiteLLM. Idempotente — llamadas repetidas
    no duplican estado.

    Se prefiere esta función explícita a un side effect al import del módulo:
    permite que `tests/` importe `langfuse_client` sin mutar el estado global
    de `litellm.success_callback` / `litellm.failure_callback`, y deja la
    decisión de "cuándo arrancar observability" en manos del orquestador
    (app.main), no del orden de imports.
    """
    configure_litellm_callbacks(get_client())
