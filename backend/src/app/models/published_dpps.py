from datetime import datetime

from sqlmodel import JSON, Column, Field, SQLModel


class PublishedDPP(SQLModel, table=True):
    __tablename__ = "published_dpps"

    gs1_uri: str = Field(primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    jsonld: dict = Field(sa_column=Column(JSON))
    signature: str | None = None  # base64 Ed25519
    public_key: str | None = None
    published_at: datetime = Field(default_factory=datetime.utcnow)
