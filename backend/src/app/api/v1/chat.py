"""Endpoint del chat lateral (F3-04).

Invariantes (CLAUDE.md):
  - El chat NUNCA escribe en el estado del wizard (`sessions.progress`,
    `extracted_fields`, `documents` están off-limits).
  - El histórico del chat persiste en su PROPIA tabla (`chat_messages`),
    canal independiente del wizard. Persistirlo aquí permite reanudar
    la conversación tras refresh (F3-04 criterio 3) sin violar la
    invariante de "el chat no escribe en el estado del wizard".
  - Si el RAG no devuelve fragmentos relevantes, la respuesta canónica es
    "No tengo información suficiente para responder con base normativa"
    y `citation = None`.
  - Toda respuesta exitosa incluye `[Reglamento X, Art. Y]` y un objeto
    `Citation` poblado.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.v1.schemas import (
    ChatFragment,
    ChatHistoryMessage,
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    Citation,
)
from app.chat import answer as chat_answer
from app.config import settings
from app.db.session import get_session
from app.models.chat_messages import ChatMessage
from app.models.sessions import WizardSession
from app.plugins.loader import load_all_plugins

router = APIRouter(prefix="/chat", tags=["chat"])

DbSession = Annotated[Session, Depends(get_session)]


def _citation_to_dict(citation: Citation | None) -> dict[str, Any] | None:
    if citation is None:
        return None
    return {
        "regulation": citation.regulation,
        "article": citation.article,
        "url": citation.url,
    }


def _citation_from_dict(raw: Any) -> Citation | None:
    if not isinstance(raw, dict) or not raw.get("regulation"):
        return None
    return Citation(
        regulation=str(raw.get("regulation", "")),
        article=str(raw.get("article", "")),
        url=raw.get("url"),
    )


@router.post("", response_model=ChatResponse)
def chat(body: ChatRequest, db: DbSession) -> ChatResponse:
    """Chat lateral con cita normativa obligatoria (F3-04).

    Cada respuesta exitosa incluye cita. Si el RAG no encuentra fragmentos
    relevantes, devuelve la negativa canónica con citation=None. El histórico
    (usuario + respuesta) se persiste en `chat_messages` para reanudación;
    NO se toca el estado del wizard.
    """
    # Obtener contexto del wizard (paso actual, sector, etc.)
    context: dict[str, Any] | None = None
    row = db.exec(select(WizardSession).where(WizardSession.id == body.session_id)).first()
    if row is None:
        # No persistimos histórico si la sesión no existe — evita filas huérfanas
        # y devuelve 404 al cliente.
        raise HTTPException(status_code=404, detail="session_not_found")

    progress = row.progress or {}
    context: dict[str, Any] = {
        "step": progress.get("step", 1),
        "sector": row.sector,
        "plugin": row.plugin,
    }

    # Si la sesión ya está clasificada, cargamos la definición completa del plugin
    # para que el chat pueda explicar campos concretos (p. ej. "qué es
    # battery_passport_unique_id") usando la cita normativa del propio YAML.
    # Un fallo de carga no bloquea el chat: simplemente no podrá responder
    # preguntas sobre campos hasta que el plugin vuelva a ser cargable.
    if row.plugin:
        try:
            plugins = load_all_plugins(settings.plugins_dir)
            plugin_def = plugins.get(row.plugin)
            if plugin_def is not None:
                context["plugin_def"] = plugin_def
        except Exception:
            pass

    # Cargamos los últimos turnos persistidos para que el LLM pueda resolver
    # referencias deícticas ("ese valor", "lo anterior"). Limitamos a 10 mensajes
    # (~5 turnos) para no inflar el prompt. Se leen ANTES de persistir la pregunta
    # nueva, así no aparece duplicada.
    recent = db.exec(
        select(ChatMessage)
        .where(ChatMessage.session_id == body.session_id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(10)
    ).all()
    context["history"] = [
        {"role": m.role, "content": m.content} for m in reversed(recent)
    ]

    # Determinar idioma del contexto
    idioma = "es"  # Default; podría inferirse de la sesión

    result = chat_answer(body.message, session_context=context, idioma=idioma)

    citation = None
    if result.citation_regulation:
        citation = Citation(
            regulation=result.citation_regulation,
            article=result.citation_article or "",
            url=result.citation_url,
        )

    # Persistir histórico (canal independiente del estado del wizard).
    # Una sola transacción para que user+assistant queden encadenados o nada.
    db.add(
        ChatMessage(
            session_id=body.session_id,
            role="user",
            content=body.message,
            citation=None,
        )
    )
    db.add(
        ChatMessage(
            session_id=body.session_id,
            role="assistant",
            content=result.answer,
            citation=_citation_to_dict(citation),
        )
    )
    db.commit()

    return ChatResponse(
        answer=result.answer,
        citation=citation,
        fragments=[
            ChatFragment(
                cita=f.cita,
                texto=f.texto[:500],
                score=f.score,
            )
            for f in result.fragments[:3]
        ],
    )


# El historial vive bajo /sessions/{id}/chat por simetría con el resto del
# wizard, no bajo /chat/sessions/{id}. Se registra desde aquí para mantener
# el módulo del chat agrupado.
history_router = APIRouter(prefix="/sessions", tags=["chat"])


@history_router.get("/{session_id}/chat", response_model=ChatHistoryResponse)
def get_chat_history(session_id: str, db: DbSession) -> ChatHistoryResponse:
    """Devuelve el histórico del chat persistido por sesión (F3-04 criterio 3).

    Orden estable por `created_at` ascendente + `id` ascendente para empates
    de timestamp (utcnow() puede repetir microsegundos bajo carga).
    """
    # Verifica que la sesión existe (404 explícito en vez de devolver lista vacía).
    row = db.exec(select(WizardSession).where(WizardSession.id == session_id)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="session_not_found")

    rows = db.exec(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at, ChatMessage.id)
    ).all()

    return ChatHistoryResponse(
        messages=[
            ChatHistoryMessage(
                role=r.role,  # type: ignore[arg-type]
                content=r.content,
                citation=_citation_from_dict(r.citation),
                created_at=r.created_at,
            )
            for r in rows
        ]
    )
