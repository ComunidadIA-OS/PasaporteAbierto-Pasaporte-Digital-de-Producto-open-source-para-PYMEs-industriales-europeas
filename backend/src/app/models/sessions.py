from datetime import datetime

from sqlmodel import JSON, Column, Field, SQLModel

from app.time_utils import utcnow


class WizardSession(SQLModel, table=True):
    __tablename__ = "sessions"

    id: str = Field(primary_key=True)
    # Dueño de la sesión. Nullable a propósito: las filas sembradas (seed/demo)
    # o creadas antes del login quedan sin dueño y siguen siendo legibles; las
    # creadas vía API con sesión iniciada llevan `user_id` y solo las ve su
    # dueño (ver `_get_owned_or_404` en el router del wizard). Sin esto el ID
    # opaco bastaba para acceder a cualquier DPP — ver ADR-0004.
    user_id: str | None = Field(default=None, foreign_key="users.id", index=True)
    progress: dict = Field(default_factory=dict, sa_column=Column(JSON))
    sector: str | None = None
    plugin: str | None = None
    classification_confidence: float | None = None
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: datetime = Field(default_factory=utcnow)
