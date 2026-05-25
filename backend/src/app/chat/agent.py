"""Agente del chat lateral (F3-04).

Invariantes (CLAUDE.md):
  - El chat NUNCA escribe en el estado del wizard.
  - Toda respuesta exitosa incluye `[Reglamento X, Art. Y]`.
  - Si el RAG no devuelve fragmentos relevantes, la respuesta canónica es
    "No tengo información suficiente para responder con base normativa"
    y `citation = None`.
  - Anti-alucinación: la cita se extrae del fragmento RAG real, no del LLM.
"""

from __future__ import annotations

import contextlib
import json
import re
from dataclasses import dataclass
from typing import Any

from langfuse.decorators import langfuse_context

from app.llm import LLMBackendError, complete
from app.observability.decorators import trace_chat
from app.rag import search_corpus
from app.rag.schema import Filters, Result

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

NEGATIVE_RESPONSE = "No tengo información suficiente para responder con base normativa."

SYSTEM_PROMPT = """\
Eres un asistente experto en regulación europea de productos sostenibles (ESPR, \
Reglamento UE 2024/1781) y reglamentos sectoriales (baterías UE 2023/1542, etc.).

Tu tarea es responder preguntas del fabricante sobre requisitos normativos para su \
Pasaporte Digital de Producto (DPP).

REGLAS ESTRICTAS:
1. Responde en el mismo idioma que la pregunta del usuario.
2. Basa tu respuesta EXCLUSIVAMENTE en los fragmentos del corpus proporcionados.
3. Al final de tu respuesta, incluye SIEMPRE la cita normativa entre corchetes: \
[Reglamento X, Art. Y].
4. Si los fragmentos no contienen información relevante para la pregunta, responde \
EXACTAMENTE: "No tengo información suficiente para responder con base normativa."
5. No inventes información ni cites artículos que no aparezcan en los fragmentos.
6. Sé conciso: máximo 3-4 frases.
7. Responde en JSON estricto: {"answer": "<respuesta con cita>", "fragment_index": <int>}"""


@dataclass(frozen=True)
class ChatResult:
    answer: str
    citation_regulation: str | None
    citation_article: str | None
    citation_url: str | None
    fragments: list[Result]


@trace_chat
def answer(
    message: str,
    session_context: dict[str, Any] | None = None,
    idioma: str = "es",
) -> ChatResult:
    """Responde una pregunta del fabricante con cita normativa obligatoria.

    Pipeline lineal:
    1. RAG → fragmentos relevantes.
    2. Si vacío → negativa canónica.
    3. Prompt con fragmentos + contexto → LLM.
    4. Cita extraída del fragmento real (anti-alucinación).
    """
    # 1. Buscar fragmentos relevantes
    try:
        fragments = search_corpus(message, top_k=5, filters=Filters(idioma=idioma))
    except Exception:
        fragments = []

    # 2. Sin fragmentos → negativa canónica
    if not fragments:
        _publish_metadata(None, message)
        return ChatResult(
            answer=NEGATIVE_RESPONSE,
            citation_regulation=None,
            citation_article=None,
            citation_url=None,
            fragments=[],
        )

    # 3. Construir prompt y llamar al LLM
    prompt = _build_prompt(message, fragments, session_context)

    try:
        response = complete(prompt, system=SYSTEM_PROMPT, timeout=20.0, max_tokens=1000)
    except LLMBackendError:
        # LLM caído: devolver fragmento top-1 como respuesta mínima
        frag = fragments[0]
        fallback_answer = (
            f"{frag.texto[:200].strip()}… " f"[{frag.reglamento}, Art. {frag.articulo}]"
        )
        return ChatResult(
            answer=fallback_answer,
            citation_regulation=f"Reglamento {frag.reglamento}",
            citation_article=_render_article(frag.articulo, frag.apartado),
            citation_url=str(frag.fuente_url),
            fragments=fragments,
        )

    # 4. Parsear respuesta y extraer cita del fragmento real
    parsed = _parse_llm_json(response.content)
    if parsed is None:
        # No parseable: usar texto crudo + cita del fragmento top-1
        frag = fragments[0]
        raw_answer = response.content.strip()
        if not raw_answer:
            raw_answer = NEGATIVE_RESPONSE
        result = ChatResult(
            answer=raw_answer,
            citation_regulation=f"Reglamento {frag.reglamento}",
            citation_article=_render_article(frag.articulo, frag.apartado),
            citation_url=str(frag.fuente_url),
            fragments=fragments,
        )
        _publish_metadata(result, message)
        return result

    answer_text = str(parsed.get("answer", "")).strip()
    fragment_index = int(parsed.get("fragment_index", 0) or 0)

    # Validar que no sea la negativa
    if NEGATIVE_RESPONSE.lower() in answer_text.lower() or not answer_text:
        _publish_metadata(None, message)
        return ChatResult(
            answer=NEGATIVE_RESPONSE,
            citation_regulation=None,
            citation_article=None,
            citation_url=None,
            fragments=fragments,
        )

    # Anti-alucinación: fragment_index en rango
    if not (0 <= fragment_index < len(fragments)):
        fragment_index = 0

    frag = fragments[fragment_index]
    citation_reg = f"Reglamento {frag.reglamento}"
    citation_art = _render_article(frag.articulo, frag.apartado)

    # Asegurar que la cita aparece en la respuesta
    if f"[{frag.reglamento}" not in answer_text and "[Reglamento" not in answer_text:
        answer_text += f" [{citation_reg}, {citation_art}]"

    result = ChatResult(
        answer=answer_text,
        citation_regulation=citation_reg,
        citation_article=citation_art,
        citation_url=str(frag.fuente_url),
        fragments=fragments,
    )
    _publish_metadata(result, message)
    return result


def _build_prompt(
    message: str,
    fragments: list[Result],
    context: dict[str, Any] | None,
) -> str:
    """Construye el prompt del usuario con fragmentos RAG y contexto del wizard."""
    fragment_lines = "\n".join(
        f"[{i}] {frag.cita} — {frag.texto[:400].strip()}" for i, frag in enumerate(fragments)
    )

    context_section = ""
    if context:
        step = context.get("step", "?")
        sector = context.get("sector", "desconocido")
        context_section = f"\nContexto del wizard: paso {step}, sector {sector}.\n"

    return (
        f"Fragmentos del corpus normativo (top-{len(fragments)}):\n"
        f"{fragment_lines}\n"
        f"{context_section}\n"
        f'Pregunta del fabricante:\n"""\n{message.strip()}\n"""\n\n'
        "Responde con el JSON solicitado."
    )


def _parse_llm_json(content: str) -> dict | None:
    """Parsea JSON del LLM tolerando markdown fences."""
    text = _FENCE_RE.sub("", content.strip()).strip()
    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        text = text[start : end + 1]
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _render_article(articulo: str, apartado: str | None) -> str:
    """Renderiza referencia a artículo."""
    if articulo.lower().startswith("annex"):
        return articulo if not apartado else f"{articulo} §{apartado}"
    base = f"Art. {articulo}"
    return f"{base}.{apartado}" if apartado else base


def _publish_metadata(result: ChatResult | None, message: str) -> None:
    """Publica metadata a Langfuse."""
    with contextlib.suppress(Exception):
        metadata: dict[str, Any] = {"pregunta": message[:200]}
        if result and result.citation_regulation:
            metadata["cita"] = f"{result.citation_regulation}, {result.citation_article}"
        else:
            metadata["cita"] = "negativa canónica"
        langfuse_context.update_current_observation(metadata=metadata)
