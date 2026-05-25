"""Endpoint del chat lateral (F3-04).

Invariantes (CLAUDE.md):
  - El chat NUNCA escribe en el estado del wizard.
  - Si el RAG no devuelve fragmentos relevantes, la respuesta canónica es
    "No tengo información suficiente para responder con base normativa"
    y `citation = None`.
  - Toda respuesta exitosa incluye `[Reglamento X, Art. Y]` y un objeto
    `Citation` poblado.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.v1.schemas import ChatFragment, ChatRequest, ChatResponse, Citation
from app.chat import answer as chat_answer
from app.db.session import get_session
from app.models.sessions import WizardSession

router = APIRouter(prefix="/chat", tags=["chat"])

DbSession = Annotated[Session, Depends(get_session)]


@router.post("", response_model=ChatResponse)
def chat(body: ChatRequest, db: DbSession) -> ChatResponse:
    """Chat lateral con cita normativa obligatoria (F3-04).

    Cada respuesta exitosa incluye cita. Si el RAG no encuentra fragmentos
    relevantes, devuelve la negativa canónica con citation=None.
    El chat nunca escribe en el estado del wizard.
    """
    # Obtener contexto del wizard (paso actual, sector, etc.)
    context: dict[str, Any] | None = None
    row = db.exec(select(WizardSession).where(WizardSession.id == body.session_id)).first()
    if row:
        progress = row.progress or {}
        context = {
            "step": progress.get("step", 1),
            "sector": row.sector,
            "plugin": row.plugin,
        }

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
