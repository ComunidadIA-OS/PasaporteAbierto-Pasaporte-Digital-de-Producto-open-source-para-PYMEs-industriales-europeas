from sqlmodel import Field, SQLModel


class ExtractedField(SQLModel, table=True):
    __tablename__ = "extracted_fields"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    field_id: str = Field(index=True)
    value: str
    source_document_id: int | None = Field(default=None, foreign_key="documents.id")
    provenance: str  # "verified" | "self_declared" | "required_pending"
    confidence: float = 0.0
