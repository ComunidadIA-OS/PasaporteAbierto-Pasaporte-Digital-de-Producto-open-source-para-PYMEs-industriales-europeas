from datetime import datetime

from sqlmodel import JSON, Column, Field, SQLModel

from app.time_utils import utcnow


class WizardSession(SQLModel, table=True):
    __tablename__ = "sessions"

    id: str = Field(primary_key=True)
    progress: dict = Field(default_factory=dict, sa_column=Column(JSON))
    sector: str | None = None
    plugin: str | None = None
    classification_confidence: float | None = None
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: datetime = Field(default_factory=utcnow)
