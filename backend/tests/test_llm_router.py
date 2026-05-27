from unittest.mock import patch

import pytest

from app.config import settings
from app.llm.router import LLMBackendError, LLMResponse, complete, parse_backend

# ═══ Tests funcionales ═══


def test_parse_backend_ollama():
    backend = parse_backend("ollama:qwen2.5:14b")
    assert backend.provider == "ollama"
    assert backend.model == "qwen2.5:14b"


def test_parse_backend_anthropic():
    backend = parse_backend("anthropic:claude-opus-4")
    assert backend.provider == "anthropic"
    assert backend.model == "claude-opus-4"


def test_parse_backend_rejects_malformed():
    with pytest.raises(ValueError):
        parse_backend("just-a-string")


def test_complete_returns_typed_response(monkeypatch):
    # NOTE: Settings es un singleton de pydantic-settings instanciado a nivel
    # módulo; monkeypatch.setenv no afecta al singleton ya creado. Usar
    # monkeypatch.setattr sobre el objeto settings, igual que test_health.py.
    monkeypatch.setattr(settings, "model_backend", "ollama:qwen2.5:14b")

    fake_response = {
        "choices": [{"message": {"content": "respuesta del modelo"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
        "model": "ollama/qwen2.5:14b",
    }

    with patch("app.llm.router.litellm.completion", return_value=fake_response) as mocked:
        result = complete("hola mundo")

    assert isinstance(result, LLMResponse)
    assert result.content == "respuesta del modelo"
    assert result.tokens_in == 10
    assert result.tokens_out == 4
    assert result.model == "ollama/qwen2.5:14b"
    assert result.backend == "ollama:qwen2.5:14b"
    mocked.assert_called_once()


def test_complete_raises_typed_error_on_backend_failure(monkeypatch):
    monkeypatch.setattr(settings, "model_backend", "ollama:qwen2.5:14b")

    with (
        patch("app.llm.router.litellm.completion", side_effect=RuntimeError("ollama down")),
        pytest.raises(LLMBackendError) as exc,
    ):
        complete("hola")

    assert exc.value.backend == "ollama:qwen2.5:14b"
    # El backend identifica el origen del fallo; el detalle del exc original
    # queda en __cause__ (preservado por raise ... from exc) — accesible para
    # depuración interna pero no expuesto en el mensaje del error.
    assert exc.value.__cause__ is not None


# ═══ Defensas OWASP ═══


def test_complete_passes_system_message_when_provided(monkeypatch):
    """OWASP LLM01 (Prompt Injection): separar system de user evita injection
    por concatenación. El parámetro `system=` debe traducirse en un mensaje
    con role=system distinto del role=user.
    """
    monkeypatch.setattr(settings, "model_backend", "ollama:qwen2.5:14b")

    fake_response = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 6},
        "model": "ollama/qwen2.5:14b",
    }

    with patch("app.llm.router.litellm.completion", return_value=fake_response) as mocked:
        complete("¿qué es ESPR?", system="Eres asistente normativo. Cita siempre.")

    call_kwargs = mocked.call_args.kwargs
    messages = call_kwargs["messages"]
    assert messages[0] == {"role": "system", "content": "Eres asistente normativo. Cita siempre."}
    assert messages[1] == {"role": "user", "content": "¿qué es ESPR?"}


def test_complete_passes_timeout_and_max_tokens(monkeypatch):
    """OWASP LLM10 (Unbounded Consumption): los overrides explícitos de
    timeout y max_tokens deben propagarse a litellm.completion.
    """
    monkeypatch.setattr(settings, "model_backend", "ollama:qwen2.5:14b")

    fake_response = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        "model": "ollama/qwen2.5:14b",
    }

    with patch("app.llm.router.litellm.completion", return_value=fake_response) as mocked:
        complete("test", timeout=10.0, max_tokens=500)

    call_kwargs = mocked.call_args.kwargs
    assert call_kwargs["timeout"] == 10.0
    assert call_kwargs["max_tokens"] == 500


def test_complete_uses_safe_defaults_for_timeout_and_max_tokens(monkeypatch):
    """OWASP LLM10: si no se pasan, defaults conservadores (timeout=30.0,
    max_tokens=2000) — mitigan DoS por llamadas que se cuelgan y respuestas
    sin tope con APIs comerciales.
    """
    monkeypatch.setattr(settings, "model_backend", "ollama:qwen2.5:14b")

    fake_response = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        "model": "ollama/qwen2.5:14b",
    }

    with patch("app.llm.router.litellm.completion", return_value=fake_response) as mocked:
        complete("test")

    call_kwargs = mocked.call_args.kwargs
    assert call_kwargs["timeout"] == 30.0
    assert call_kwargs["max_tokens"] == 2000


def test_llm_backend_error_does_not_echo_prompt(monkeypatch):
    """OWASP LLM07 (System Prompt Leakage): el mensaje exterior de
    LLMBackendError NO debe contener el prompt ni el mensaje crudo de la
    excepción original de LiteLLM (que algunos backends populan con eco del
    request body). El detalle queda accesible via __cause__ para depuración.
    """
    monkeypatch.setattr(settings, "model_backend", "ollama:qwen2.5:14b")

    secret_prompt = "SYSTEM_PROMPT_SECRETO_QUE_NO_DEBE_FILTRARSE"
    backend_exception_with_echo = RuntimeError(f"Bad request: messages=[{secret_prompt}]")

    with (
        patch("app.llm.router.litellm.completion", side_effect=backend_exception_with_echo),
        pytest.raises(LLMBackendError) as exc,
    ):
        complete(secret_prompt)

    # El mensaje exterior identifica el backend pero NO contiene el prompt
    assert secret_prompt not in str(exc.value)
    # El detalle completo sigue accesible via __cause__ para Langfuse/tracebacks
    assert exc.value.__cause__ is backend_exception_with_echo


# ═══ Tests de robustez añadidos en code review ═══


@pytest.mark.parametrize(
    "raw, expected_litellm_id",
    [
        ("ollama:qwen2.5:14b", "ollama/qwen2.5:14b"),
        ("anthropic:claude-opus-4", "anthropic/claude-opus-4"),
        ("openai:gpt-4o", "gpt-4o"),
        ("groq:llama3-70b", "groq/llama3-70b"),
    ],
)
def test_to_litellm_model_mapping(raw, expected_litellm_id):
    """El mapping a identificador LiteLLM es consistente por provider.
    Cubre los 4 caminos de `_to_litellm_model`: ollama, anthropic, openai
    (directo, sin prefijo) y fallback genérico para providers desconocidos.
    """
    from app.llm.router import _to_litellm_model

    parsed = parse_backend(raw)
    assert _to_litellm_model(parsed) == expected_litellm_id


def test_complete_without_system_sends_only_user_message(monkeypatch):
    """OWASP LLM01: si el caller no pasa `system`, solo se envía un mensaje
    user (lista de 1 elemento) — no se inyecta un system prompt vacío ni se
    concatena con el prompt.
    """
    monkeypatch.setattr(settings, "model_backend", "ollama:qwen2.5:14b")

    fake_response = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        "model": "ollama/qwen2.5:14b",
    }

    with patch("app.llm.router.litellm.completion", return_value=fake_response) as mocked:
        complete("solo input de usuario")

    messages = mocked.call_args.kwargs["messages"]
    assert len(messages) == 1
    assert messages[0] == {"role": "user", "content": "solo input de usuario"}


def test_complete_handles_null_usage_tokens(monkeypatch):
    """Resilience: algunos backends populan usage con None en lugar de omitir
    el campo (típico en respuestas streaming/partial). `int(None)` rompería;
    el wrapper convierte None → 0 de forma silenciosa.
    """
    monkeypatch.setattr(settings, "model_backend", "ollama:qwen2.5:14b")

    fake_response = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None},
        "model": "ollama/qwen2.5:14b",
    }

    with patch("app.llm.router.litellm.completion", return_value=fake_response):
        result = complete("test")

    assert result.tokens_in == 0
    assert result.tokens_out == 0


def test_complete_wraps_malformed_response_in_llm_backend_error(monkeypatch):
    """OWASP LLM07 reforzado: si el backend devuelve un payload malformado
    (choices vacíos, content=None por content-filter, etc.) el wrapper
    envuelve el KeyError/IndexError/TypeError en LLMBackendError sanitizado.
    Sin esto, el caller recibiría un traceback de infra fuera del envoltorio
    OWASP-compliant.
    """
    monkeypatch.setattr(settings, "model_backend", "ollama:qwen2.5:14b")

    # Payload sin 'choices' (típico content-filter block o respuesta truncada)
    malformed_response = {"model": "ollama/qwen2.5:14b"}

    with (
        patch("app.llm.router.litellm.completion", return_value=malformed_response),
        pytest.raises(LLMBackendError) as exc,
    ):
        complete("test")

    assert exc.value.backend == "ollama:qwen2.5:14b"
    # El detalle (KeyError) queda en __cause__, accesible para depuración
    assert exc.value.__cause__ is not None
