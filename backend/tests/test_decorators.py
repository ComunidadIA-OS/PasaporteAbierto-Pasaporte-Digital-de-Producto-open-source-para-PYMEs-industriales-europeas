from unittest.mock import MagicMock

import litellm
import pytest

from app.observability.decorators import trace_chat, trace_classifier, trace_collector
from app.observability.langfuse_client import configure_litellm_callbacks, get_client

# ═══ Tests de wrappers semánticos sobre @observe ═══


def test_trace_classifier_wraps_function_call():
    """Aplicar @trace_classifier no rompe la función decorada."""

    @trace_classifier
    def fake_classify(description: str) -> dict:
        return {"sector": "batteries", "confidence": 0.91}

    result = fake_classify("batería para EV")
    assert result == {"sector": "batteries", "confidence": 0.91}


def test_trace_collector_wraps_function_call():
    @trace_collector
    def fake_collect(pdf_path: str) -> dict:
        return {"fields_extracted": 12}

    assert fake_collect("doc.pdf") == {"fields_extracted": 12}


def test_trace_chat_wraps_function_call():
    @trace_chat
    def fake_chat(q: str) -> dict:
        return {"answer": "x", "cita_normativa": "EU 2024/1781 Art. 7"}

    assert fake_chat("¿qué exige el ESPR?") == {
        "answer": "x",
        "cita_normativa": "EU 2024/1781 Art. 7",
    }


def test_decorators_propagate_exceptions():
    """Las excepciones de la función decorada llegan al caller intactas
    (no las traga ni las enmascara — solo @observe captura su propia
    excepción interna si Langfuse falla).
    """

    @trace_classifier
    def broken(x):
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        broken("x")


# ═══ Tests de auto-integración LiteLLM ═══


def test_configure_litellm_callbacks_enables_when_client_present(monkeypatch):
    """Con cliente Langfuse activo, litellm.success_callback contiene 'langfuse'.
    Habilita el auto-tracing de cada complete() del wrapper T7 sin código extra.
    """
    fake_client = MagicMock()
    monkeypatch.setattr(litellm, "success_callback", [])
    monkeypatch.setattr(litellm, "failure_callback", [])

    configure_litellm_callbacks(fake_client)

    assert "langfuse" in litellm.success_callback
    assert "langfuse" in litellm.failure_callback


def test_configure_litellm_callbacks_skips_when_no_client(monkeypatch):
    """Sin cliente Langfuse, no se modifica el callback de LiteLLM
    (la app arranca degradadamente sin telemetría).
    """
    monkeypatch.setattr(litellm, "success_callback", [])
    monkeypatch.setattr(litellm, "failure_callback", [])

    configure_litellm_callbacks(None)

    assert "langfuse" not in litellm.success_callback
    assert "langfuse" not in litellm.failure_callback


def test_configure_litellm_callbacks_is_idempotent(monkeypatch):
    """Llamar dos veces no duplica 'langfuse' en los callbacks
    (la app puede invocarlo en boot y en re-config sin efectos extraños).
    """
    fake_client = MagicMock()
    monkeypatch.setattr(litellm, "success_callback", [])
    monkeypatch.setattr(litellm, "failure_callback", [])

    configure_litellm_callbacks(fake_client)
    configure_litellm_callbacks(fake_client)

    assert litellm.success_callback.count("langfuse") == 1
    assert litellm.failure_callback.count("langfuse") == 1


# ═══ Tests de get_client (degradación graceful) ═══


def test_get_client_returns_none_without_credentials(monkeypatch):
    """Sin LANGFUSE_PUBLIC_KEY/SECRET_KEY, get_client devuelve None silenciosamente
    para que la app arranque sin telemetría.
    """
    from app.config import settings

    monkeypatch.setattr(settings, "langfuse_public_key", "")
    monkeypatch.setattr(settings, "langfuse_secret_key", "")
    get_client.cache_clear()

    assert get_client() is None


def test_get_client_returns_none_with_only_secret_key(monkeypatch):
    """El guard `and` exige AMBAS claves. Sin public_key, get_client devuelve None
    aunque secret_key esté presente.
    """
    from app.config import settings

    monkeypatch.setattr(settings, "langfuse_public_key", "")
    monkeypatch.setattr(settings, "langfuse_secret_key", "sk-secret-only")
    get_client.cache_clear()

    assert get_client() is None


def test_get_client_returns_none_with_only_public_key(monkeypatch):
    """Simétrico: sin secret_key, get_client devuelve None aunque public_key
    esté presente.
    """
    from app.config import settings

    monkeypatch.setattr(settings, "langfuse_public_key", "pk-public-only")
    monkeypatch.setattr(settings, "langfuse_secret_key", "")
    get_client.cache_clear()

    assert get_client() is None


# ═══ Tests del punto de entrada init_observability ═══


def test_init_observability_configures_callbacks_with_client(monkeypatch):
    """init_observability() obtiene el cliente y configura los callbacks de
    LiteLLM. Cuando hay un cliente Langfuse activo, los callbacks de litellm
    contienen 'langfuse' tras la invocación.
    """
    from app.observability import langfuse_client as lc

    fake_client = MagicMock()
    monkeypatch.setattr(lc, "get_client", lambda: fake_client)
    monkeypatch.setattr(litellm, "success_callback", [])
    monkeypatch.setattr(litellm, "failure_callback", [])

    lc.init_observability()

    assert "langfuse" in litellm.success_callback
    assert "langfuse" in litellm.failure_callback


def test_init_observability_is_noop_without_client(monkeypatch):
    """init_observability() es no-op si get_client devuelve None — la app
    arranca sin telemetría y sin mutar litellm.
    """
    from app.observability import langfuse_client as lc

    monkeypatch.setattr(lc, "get_client", lambda: None)
    monkeypatch.setattr(litellm, "success_callback", [])
    monkeypatch.setattr(litellm, "failure_callback", [])

    lc.init_observability()

    assert "langfuse" not in litellm.success_callback
    assert "langfuse" not in litellm.failure_callback
