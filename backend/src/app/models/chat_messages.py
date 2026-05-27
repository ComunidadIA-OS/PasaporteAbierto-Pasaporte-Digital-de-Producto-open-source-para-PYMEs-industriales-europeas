from datetime import datetime

from sqlmodel import JSON, Column, Field, SQLModel

from app.time_utils import utcnow


class ChatMessage(SQLModel, table=True):
    """Histórico del chat lateral por sesión (F3-04 criterio 3).

    Canal independiente del estado del wizard: el chat NUNCA escribe en
    `sessions.progress` ni `extracted_fields` (invariante de CLAUDE.md), pero
    sí persiste su propio histórico en esta tabla para permitir reanudación.
    """

    __tablename__ = "chat_messages"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    role: str  # "user" | "assistant"
    content: str
    citation: dict | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow, index=True)
