from datetime import datetime

from sqlmodel import JSON, Column, Field, SQLModel


class AuditLogEntry(SQLModel, table=True):
    __tablename__ = "audit_log"

    id: int | None = Field(default=None, primary_key=True, index=True)
    prev_hash: str | None = None  # null sólo en la primera entrada
    content_hash: str
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    operation: str  # classify | override | verify | publish | sign
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
