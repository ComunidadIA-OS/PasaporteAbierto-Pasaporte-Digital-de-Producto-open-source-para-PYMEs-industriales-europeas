"""API pública del wrapper de LLM. Los callers usan `from app.llm import ...`."""

from app.llm.router import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_TIMEOUT_SECONDS,
    LLMBackendError,
    LLMResponse,
    ParsedBackend,
    complete,
    parse_backend,
)

__all__ = [
    "DEFAULT_MAX_TOKENS",
    "DEFAULT_TIMEOUT_SECONDS",
    "LLMBackendError",
    "LLMResponse",
    "ParsedBackend",
    "complete",
    "parse_backend",
]
