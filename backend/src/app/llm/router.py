from dataclasses import dataclass

import litellm

from app.config import settings


@dataclass(frozen=True)
class ParsedBackend:
    provider: str  # ollama | anthropic | openai | ...
    model: str  # qwen2.5:14b | claude-opus-4 | gpt-4o | ...
    raw: str


@dataclass(frozen=True)
class LLMResponse:
    content: str
    tokens_in: int
    tokens_out: int
    model: str
    backend: str


class LLMBackendError(RuntimeError):
    """Fallo del backend de LLM con mensaje sanitizado.

    OWASP LLM07 (System Prompt Leakage): el mensaje exterior identifica el
    backend (`self.backend`) pero NO contiene el contenido del prompt ni el
    mensaje crudo de la excepción original. El detalle completo queda
    accesible via `__cause__` (preservado por `raise ... from exc`) para
    depuración en entorno controlado (Langfuse, tracebacks).
    """

    def __init__(self, message: str, *, backend: str) -> None:
        super().__init__(message)
        self.backend = backend


def parse_backend(value: str) -> ParsedBackend:
    """Convierte 'provider:model[:variant]' en ParsedBackend.

    Acepta:
      ollama:qwen2.5:14b   -> provider=ollama, model=qwen2.5:14b
      anthropic:claude-... -> provider=anthropic, model=claude-...
    """
    if ":" not in value:
        raise ValueError(f"MODEL_BACKEND inválido: '{value}'. Formato esperado provider:model")
    provider, model = value.split(":", 1)
    if not provider or not model:
        raise ValueError(f"MODEL_BACKEND inválido: '{value}'")
    return ParsedBackend(provider=provider, model=model, raw=value)


def _to_litellm_model(parsed: ParsedBackend) -> str:
    """LiteLLM usa 'provider/model' como identificador unificado."""
    if parsed.provider == "ollama":
        return f"ollama/{parsed.model}"
    if parsed.provider == "anthropic":
        return f"anthropic/{parsed.model}"
    if parsed.provider == "openai":
        return parsed.model  # LiteLLM acepta el modelo openai directo
    # Fallback: cualquier otro provider se delega a LiteLLM con la sintaxis
    # genérica `provider/model`. Si LiteLLM no soporta ese provider, levantará
    # su propio error en `litellm.completion`, que el wrapper envuelve en
    # `LLMBackendError` con mensaje sanitizado (OWASP LLM07).
    return f"{parsed.provider}/{parsed.model}"


# Defaults OWASP LLM10 (Unbounded Consumption) — conservadores; los callers
# pueden overridear cuando la tarea lo justifique (Recolector con PDFs largos,
# Clasificador con corpus extenso, etc.).
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_TOKENS = 2000


def complete(
    prompt: str,
    *,
    system: str | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_tokens: int | None = DEFAULT_MAX_TOKENS,
    **opts,
) -> LLMResponse:
    """Wrapper único de LLM para todo el sistema. Lee MODEL_BACKEND del entorno.

    OWASP LLM01 (Prompt Injection): `system` y `prompt` van como mensajes
    separados (role=system y role=user) a litellm; nunca se concatenan en una
    sola cadena. Los callers deben usar `system=` para instrucciones del
    sistema; `prompt` queda exclusivamente para input de usuario.

    OWASP LLM10 (Unbounded Consumption): defaults conservadores de timeout y
    max_tokens. Override explícito por argumento cuando la tarea lo justifique.

    OWASP LLM07 (System Prompt Leakage): si el backend falla, levanta
    LLMBackendError con mensaje genérico (NO contiene el prompt ni el detalle
    de la excepción original). El detalle queda en `__cause__` para
    depuración interna.
    """
    parsed = parse_backend(settings.model_backend)
    model_id = _to_litellm_model(parsed)
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        response = litellm.completion(
            model=model_id,
            messages=messages,
            timeout=timeout,
            max_tokens=max_tokens,
            **opts,
        )
        # Parsing dentro del try: un payload malformado del backend (choices
        # vacíos, content=None por content-filter, usage con None en lugar de
        # omitido) se envuelve en LLMBackendError igual que un fallo de red.
        # Preserva la invariante OWASP LLM07: un error de infra nunca llega
        # al caller con detalles sin sanitizar. El `or 0` defiende del caso
        # en que el backend popule el campo con None en lugar de omitirlo
        # (int(None) levantaría TypeError).
        content = response["choices"][0]["message"]["content"]
        usage = response.get("usage") or {}
        tokens_in = int(usage.get("prompt_tokens") or 0)
        tokens_out = int(usage.get("completion_tokens") or 0)
        model = response.get("model") or model_id
    except Exception as exc:
        # OWASP LLM07: mensaje sanitizado al exterior; detalle en __cause__.
        raise LLMBackendError(
            f"Backend {parsed.raw} ({parsed.provider}) falló — ver __cause__ para detalle.",
            backend=parsed.raw,
        ) from exc

    return LLMResponse(
        content=content,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        model=model,
        backend=parsed.raw,
    )
