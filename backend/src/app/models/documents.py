from datetime import datetime

from sqlmodel import Field, SQLModel


class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    doc_type: str  # datasheet | certificate | lca | sds | ce_declaration
    blob_path: str
    sha256: str = Field(index=True)
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
