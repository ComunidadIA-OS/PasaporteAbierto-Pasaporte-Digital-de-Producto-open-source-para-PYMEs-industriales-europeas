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
from app.plugins.loader import Plugin, PluginField, RequiredDocument
from app.rag import search_corpus
from app.rag.schema import Filters, Result

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

NEGATIVE_RESPONSE = "No tengo información suficiente para responder con base normativa."

SYSTEM_PROMPT = """\
Eres un asistente experto en regulación europea de productos sostenibles (ESPR, \
Reglamento UE 2024/1781) y reglamentos sectoriales (baterías UE 2023/1542, etc.).

Acompañas al fabricante a lo largo del wizard de generación del Pasaporte Digital de \
Producto (DPP). Puedes responder CINCO tipos de mensajes:

  A. Normativas — basadas en los fragmentos del corpus normativo proporcionados.
  B. Sobre un CAMPO concreto del plugin sectorial cargado — basadas en los \
metadatos del plugin (cada campo tiene su propia cita validada contra el \
reglamento sectorial).
  C. Sobre un DOCUMENTO requerido por el plugin (datasheet, certificate, lca, \
sds, ce_declaration) — basadas en `required_documents` del plugin.
  D. De contexto del wizard — en qué paso está el usuario, qué clasificación \
recibió, qué plugin está activo. Se responden con el contexto provisto.
  E. De cortesía conversacional — saludos ("hola"), agradecimientos ("gracias", \
"entiendo", "perfecto"), despedidas, confirmaciones cortas. Responde con UNA frase \
amable y, si procede, invita a seguir preguntando sobre el DPP. Sin cita.

Cuando el usuario use referencias deícticas ("ese valor", "lo anterior", "ese \
campo", "ese documento"), resuélvelas usando el histórico de la conversación.

REGLAS ESTRICTAS:
1. Responde en el mismo idioma que la pregunta del usuario.
2. Para preguntas normativas (A), basa tu respuesta EXCLUSIVAMENTE en los fragmentos.
3. Para preguntas sobre un campo del plugin (B), basa tu respuesta en los metadatos
   del plugin. Indica el id del campo y para qué sirve, usando su cita. Si te
   preguntan por «valores aceptados», «rango», «formato» o «reglas de validación»
   del campo: úsa `type`, `enum_values` y `validation` del campo. Si el campo
   solo tiene `type` (sin enum ni validation), responde explícitamente que es
   un valor del tipo indicado sin restricciones adicionales en el plugin. Si la
   pregunta involucra a varios campos, consulta `cross_validations` del plugin.
4. Para preguntas sobre un documento requerido (C), basa tu respuesta en
   `required_documents` del plugin. Indica el tipo de documento exactamente como
   aparece en el plugin (datasheet, certificate, lca, sds, ce_declaration). Solo
   uses esta ruta si el documento del plugin tiene cita; si no, usa la ruta A.
5. Para preguntas de contexto del wizard (D), responde con el paso/sector/plugin
   proporcionados. No necesitas cita normativa (no es respuesta regulatoria).
6. Para cortesía conversacional (E), una frase breve sin cita. No la uses para
   preguntas reales; solo para mensajes que claramente no piden información.
7. Para A, B y C, incluye SIEMPRE al final de la respuesta la cita normativa
   entre corchetes: [Reglamento X, Art. Y].
8. Si no tienes información suficiente para responder UNA PREGUNTA REAL (A/B/C),
   responde EXACTAMENTE: "No tengo información suficiente para responder con
   base normativa." NUNCA uses esa negativa para saludos o agradecimientos —
   en ese caso usa ruta E.
9. No inventes información, citas, artículos, ids de campo ni tipos de documento.
10. Sé conciso: máximo 3-4 frases.
11. Responde en JSON estricto:
    {
      "answer": "<respuesta>",
      "source": "rag" | "plugin_field" | "plugin_document" | "wizard_context" | "smalltalk" | "none",
      "fragment_index": <int o null>,         // sólo si source == "rag"
      "field_id": "<id exacto>" | null,       // sólo si source == "plugin_field"
      "document_type": "<tipo exacto>" | null // sólo si source == "plugin_document"
    }"""


@dataclass(frozen=True)
class ChatResult:
    answer: str
    citation_regulation: str | None
    citation_article: str | None
    citation_url: str | None
    fragments: list[Result]


# Regex para detectar citas inline tipo "[Reglamento UE 2023/1542" o "[UE 2023/1542".
# Capturamos el identificador del reglamento (lo que va tras "Reglamento " o tras "[").
_INLINE_CITE_RE = re.compile(r"\[\s*(?:Reglamento\s+)?([^,\]]+?)\s*(?:,|\])", re.IGNORECASE)


def _negative_result(fragments: list[Result]) -> ChatResult:
    """Resultado canónico de "no se puede responder con base normativa"."""
    return ChatResult(
        answer=NEGATIVE_RESPONSE,
        citation_regulation=None,
        citation_article=None,
        citation_url=None,
        fragments=fragments,
    )


def _select_fragment_by_citations(
    answer_text: str,
    fragments: list[Result],
    fallback_index: int,
) -> int | None:
    """Alinea el `fragment_index` con la cita inline real del cuerpo.

    Anti-alucinación, pero menos agresivo que descartar la respuesta entera:

    - Sin cita inline en el cuerpo → usa `fallback_index` (lo eligió el LLM).
    - Con cita(s) inline que coincide(n) con algún fragmento del top-k → devuelve
      el índice del primer fragmento que case. Esto cubre el caso típico de
      "huella de carbono", donde el RAG devuelve fragmentos de varios reglamentos
      (ESPR 2024/1781 y UE 2023/1542) y el LLM cita uno mientras eligió otro en
      `fragment_index`; antes descartábamos la respuesta, ahora la realineamos.
    - Con cita(s) inline pero NINGUNA coincide con ningún fragmento del top-k →
      `None`. Eso sí es alucinación real (el LLM inventó un reglamento que no
      está en el material recuperado) → el caller devuelve la negativa canónica.
    """
    mentions = _INLINE_CITE_RE.findall(answer_text)
    if not mentions:
        return fallback_index
    for mention in mentions:
        normalized = mention.strip().lower()
        for i, frag in enumerate(fragments):
            if frag.reglamento.strip().lower() in normalized:
                return i
    return None


@trace_chat
def answer(
    message: str,
    session_context: dict[str, Any] | None = None,
    idioma: str = "es",
) -> ChatResult:
    """Responde una pregunta del fabricante con cita normativa obligatoria
    cuando aplica, o información de contexto del wizard cuando no aplica.

    Cinco rutas posibles según el `source` que el LLM identifique:
      - `rag`             → respuesta normativa basada en fragmentos del corpus.
                            Cita extraída del fragmento real (anti-alucinación).
      - `plugin_field`    → respuesta sobre un campo concreto del plugin sectorial.
                            Cita desde el YAML del plugin (validado en arranque
                            contra `_schema.yaml`), no del LLM.
      - `plugin_document` → respuesta sobre un documento requerido del plugin
                            (datasheet, lca, certificate, ...). Cita desde el
                            YAML; solo aplica si el documento tiene `citation`.
      - `wizard_context`  → respuesta sobre el estado del wizard (paso, sector,
                            plugin activo). Sin cita: no es regulación.
      - `smalltalk`       → cortesía conversacional (saludos, gracias,
                            despedidas). Sin cita. Solo para mensajes que
                            claramente no piden información.
      - `none`            → negativa canónica.

    El chat sigue sin escribir en el estado del wizard (CLAUDE.md §invariantes).
    """
    sector: str | None = None
    plugin_def: Plugin | None = None
    history: list[dict[str, Any]] = []
    if session_context:
        raw_sector = session_context.get("sector")
        if isinstance(raw_sector, str) and raw_sector and raw_sector != "unknown":
            sector = raw_sector
        candidate = session_context.get("plugin_def")
        if isinstance(candidate, Plugin):
            plugin_def = candidate
        raw_history = session_context.get("history")
        if isinstance(raw_history, list):
            history = [
                m for m in raw_history
                if isinstance(m, dict) and m.get("role") and m.get("content")
            ]

    try:
        fragments = search_corpus(
            message,
            top_k=5,
            filters=Filters(idioma=idioma, sector=sector),
        )
    except Exception:
        fragments = []

    # Sin material en absoluto (ni RAG, ni plugin, ni contexto) → negativa.
    # Si hay plugin o contexto, seguimos: el LLM puede responder ruta B o C.
    if not fragments and plugin_def is None and not session_context:
        _publish_metadata(None, message)
        return _negative_result([])

    prompt = _build_prompt(message, fragments, plugin_def, session_context, history)

    try:
        response = complete(prompt, system=SYSTEM_PROMPT, timeout=20.0, max_tokens=1000)
    except LLMBackendError:
        # LLM caído: si hay fragmentos, devolver top-1; si no, negativa.
        if fragments:
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
        _publish_metadata(None, message)
        return _negative_result(fragments)

    parsed = _parse_llm_json(response.content)
    if parsed is None:
        _publish_metadata(None, message)
        return _negative_result(fragments)

    answer_text = str(parsed.get("answer", "")).strip()
    source = str(parsed.get("source", "")).lower()

    if not answer_text or NEGATIVE_RESPONSE.lower() in answer_text.lower():
        _publish_metadata(None, message)
        return _negative_result(fragments)

    # Ruta B: campo del plugin. Cita siempre desde el YAML del plugin.
    if source == "plugin_field" and plugin_def is not None:
        field = _find_plugin_field(plugin_def, parsed.get("field_id"))
        if field is None:
            _publish_metadata(None, message)
            return _negative_result(fragments)
        citation_reg = f"Reglamento {field.citation.regulation}"
        citation_art = field.citation.article
        if field.citation.regulation not in answer_text:
            answer_text = f"{answer_text} [{citation_reg}, {citation_art}]"
        result = ChatResult(
            answer=answer_text,
            citation_regulation=citation_reg,
            citation_article=citation_art,
            citation_url=None,
            fragments=fragments,
        )
        _publish_metadata(result, message)
        return result

    # Ruta C: documento requerido por el plugin. Cita desde el YAML del plugin.
    if source == "plugin_document" and plugin_def is not None:
        doc = _find_plugin_document(plugin_def, parsed.get("document_type"))
        if doc is None or doc.citation is None:
            _publish_metadata(None, message)
            return _negative_result(fragments)
        citation_reg = f"Reglamento {doc.citation.regulation}"
        citation_art = doc.citation.article
        if doc.citation.regulation not in answer_text:
            answer_text = f"{answer_text} [{citation_reg}, {citation_art}]"
        result = ChatResult(
            answer=answer_text,
            citation_regulation=citation_reg,
            citation_article=citation_art,
            citation_url=None,
            fragments=fragments,
        )
        _publish_metadata(result, message)
        return result

    # Ruta E: cortesía conversacional (saludos, gracias, despedidas). Sin cita.
    if source == "smalltalk":
        result = ChatResult(
            answer=answer_text,
            citation_regulation=None,
            citation_article=None,
            citation_url=None,
            fragments=[],
        )
        _publish_metadata(result, message)
        return result

    # Ruta D: contexto del wizard. Sin cita normativa (no es regulación).
    if source == "wizard_context":
        result = ChatResult(
            answer=answer_text,
            citation_regulation=None,
            citation_article=None,
            citation_url=None,
            fragments=[],
        )
        _publish_metadata(result, message)
        return result

    # Ruta A: respuesta normativa basada en RAG.
    if source == "rag" and fragments:
        fragment_index = int(parsed.get("fragment_index", 0) or 0)
        if not (0 <= fragment_index < len(fragments)):
            fragment_index = 0
        chosen = _select_fragment_by_citations(answer_text, fragments, fragment_index)
        if chosen is None:
            _publish_metadata(None, message)
            return _negative_result(fragments)
        fragment_index = chosen
        frag = fragments[fragment_index]
        citation_reg = f"Reglamento {frag.reglamento}"
        citation_art = _render_article(frag.articulo, frag.apartado)
        if f"[{frag.reglamento}" not in answer_text:
            answer_text = f"{answer_text} [{citation_reg}, {citation_art}]"
        result = ChatResult(
            answer=answer_text,
            citation_regulation=citation_reg,
            citation_article=citation_art,
            citation_url=str(frag.fuente_url),
            fragments=fragments,
        )
        _publish_metadata(result, message)
        return result

    # source == "none", desconocido, o combinación inválida (p. ej. rag sin fragmentos).
    _publish_metadata(None, message)
    return _negative_result(fragments)


def _build_prompt(
    message: str,
    fragments: list[Result],
    plugin: Plugin | None,
    context: dict[str, Any] | None,
    history: list[dict[str, Any]] | None = None,
) -> str:
    """Construye el prompt con cuatro bloques de contexto: histórico de la
    conversación, fragmentos RAG, plugin sectorial activo (campos + sus citas
    YAML) y estado del wizard.

    El LLM elige qué bloque usar mediante el campo `source` del JSON. El caller
    inyecta la cita de la fuente correspondiente (RAG real o YAML del plugin),
    nunca confía en la cita generada por el LLM.
    """
    sections: list[str] = []

    if history:
        # Truncamos cada mensaje a 300 caracteres para que 5 turnos sigan siendo
        # ~3 KB. El LLM solo necesita la referencia, no el cuerpo completo.
        history_lines = "\n".join(
            f"{m.get('role', '?')}: {str(m.get('content', ''))[:300]}"
            for m in history
        )
        sections.append(
            "Histórico reciente de la conversación (más antiguo primero, "
            "úsalo para resolver referencias deícticas tipo «ese valor», «lo "
            "anterior», pero NO inventes información que no esté ahí):\n"
            f"{history_lines}"
        )

    if fragments:
        fragment_lines = "\n".join(
            f"[{i}] {frag.cita} — {frag.texto[:400].strip()}"
            for i, frag in enumerate(fragments)
        )
        sections.append(
            f"Fragmentos del corpus normativo (top-{len(fragments)}):\n{fragment_lines}"
        )
    else:
        sections.append("Fragmentos del corpus normativo: ninguno relevante para esta pregunta.")

    if plugin is not None:
        field_lines = "\n".join(_render_plugin_field(f) for f in plugin.fields)
        doc_lines = "\n".join(
            (
                f"- {d.type} (mandatory={d.mandatory}"
                f"{', when=' + d.when if d.when else ''}) → "
                + (
                    f"[Reglamento {d.citation.regulation}, {d.citation.article}]"
                    if d.citation
                    else "(sin cita YAML; si te preguntan por este doc, usa la ruta A=rag)"
                )
            )
            for d in plugin.required_documents
        )
        xval_lines = (
            "\n".join(
                f"- {cv.id}: {cv.rule}"
                + (f"  // {cv.message}" if cv.message else "")
                for cv in plugin.cross_validations
            )
            if plugin.cross_validations
            else "(ninguna)"
        )
        sections.append(
            f"Plugin sectorial cargado: «{plugin.name}» — {plugin.regulation}.\n"
            f"{plugin.description}\n"
            f"Campos del plugin (id, tipo, obligatoriedad, valores aceptados, cita):\n"
            f"{field_lines}\n\n"
            f"Documentos requeridos por el plugin (tipo, obligatoriedad, cita):\n{doc_lines}\n\n"
            f"Reglas cruzadas del plugin (relacionan varios campos):\n{xval_lines}"
        )

    if context:
        step = context.get("step", "?")
        sector = context.get("sector") or "sin clasificar"
        plugin_name = context.get("plugin") or "sin plugin"
        sections.append(
            f"Contexto del wizard: paso {step} de 7, "
            f"sector clasificado «{sector}», plugin activo «{plugin_name}»."
        )

    sections.append(
        f'Pregunta del fabricante:\n"""\n{message.strip()}\n"""\n\n'
        "Identifica primero el tipo de pregunta (normativa, sobre un campo del "
        "plugin, o sobre el estado del wizard) y responde con el JSON solicitado, "
        "rellenando `source`, `fragment_index` o `field_id` según corresponda."
    )

    return "\n\n".join(sections)


def _render_plugin_field(f: PluginField) -> str:
    """Renderiza un campo del plugin para el prompt con toda la info necesaria
    para responder preguntas tipo «qué valores acepta» o «hay alguna regla»."""
    parts = [f"type={f.type}", f"req={f.required}", f"access={f.access_level}"]
    if f.enum_values:
        parts.append(f"enum={f.enum_values}")
    if f.validation:
        parts.append(f"validation=`{f.validation}`")
    meta = ", ".join(parts)
    return (
        f"- {f.id} ({meta}) → "
        f"[Reglamento {f.citation.regulation}, {f.citation.article}]"
    )


def _find_plugin_field(plugin: Plugin, field_id: Any) -> PluginField | None:
    """Busca un campo del plugin por id exacto. Devuelve None si no existe o si
    el id no es una cadena (el LLM podría devolver null o un objeto)."""
    if not isinstance(field_id, str) or not field_id:
        return None
    for f in plugin.fields:
        if f.id == field_id:
            return f
    return None


def _find_plugin_document(plugin: Plugin, doc_type: Any) -> RequiredDocument | None:
    """Busca un documento requerido del plugin por tipo exacto. Devuelve None si
    no existe, si el tipo no es cadena, o si el documento no tiene cita YAML
    (esos casos los responde la ruta `rag`, no `plugin_document`)."""
    if not isinstance(doc_type, str) or not doc_type:
        return None
    for d in plugin.required_documents:
        if d.type == doc_type and d.citation is not None:
            return d
    return None


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
