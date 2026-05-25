"""Schemas Pydantic v2 de la API pública del wizard (PR-0 conjunto).

Estos schemas son el **contrato congelado** entre backend y frontend. Cambiarlos
requiere PR conjunto entre Persona A y Persona B (ver docs/tickets/REPARTO.md).

Cubre los 8 endpoints del wizard:
  - POST   /sessions                              (paso 1)
  - GET    /sessions/{id}                         (reanudación)
  - POST   /sessions/{id}/classify                (paso 2 — F3-01)
  - PUT    /sessions/{id}/bom                     (paso 3)
  - GET    /sessions/{id}/documents               (paso 4)
  - POST   /sessions/{id}/documents               (paso 4)
  - POST   /sessions/{id}/extract                 (paso 5 SSE — F3-02)
  - GET    /sessions/{id}/verify                  (paso 6 — F3-03)
  - POST   /sessions/{id}/dpp                     (paso 7 — F5)
  - POST   /chat                                  (chat lateral — F3-04)
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Provenance = Literal["verified", "self_declared", "required_pending"]
AccessLevel = Literal["public", "legitimate_interest", "authorities_only", "individual"]
DocType = Literal["datasheet", "certificate", "lca", "sds", "ce_declaration"]


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Citation(_Base):
    """Cita normativa concreta (reglamento + artículo o anexo)."""

    regulation: str
    article: str
    url: str | None = None


# --- POST /sessions ---------------------------------------------------------


class CreateSessionRequest(_Base):
    description: str = Field(
        min_length=20,
        max_length=2000,
        description="Paso 1 — texto libre del fabricante",
    )


class CreateSessionResponse(_Base):
    session_id: str
    created_at: datetime


# --- GET /plugins -----------------------------------------------------------


class PluginSummary(_Base):
    """Resumen de un plugin sectorial. Usado por F4-02 (override) y F4-03 (BOM)."""

    name: str
    regulation: str
    description: str


class PluginsListResponse(_Base):
    plugins: list[PluginSummary]


# --- PATCH /sessions/{id} (F4-01 autosave) ----------------------------------


class UpdateProgressRequest(_Base):
    """Mutación parcial del estado de la sesión (autosave del wizard).

    Todos los campos son opcionales; los presentes se mergean con el estado
    existente. `bom` hace shallow-merge (no reemplaza claves no incluidas).
    """

    step: int | None = Field(default=None, ge=1, le=7)
    description: str | None = Field(default=None, min_length=20, max_length=2000)
    bom: dict[str, Any] | None = None


# --- GET /sessions/{id} -----------------------------------------------------


class FieldValue(_Base):
    """Campo extraído o autodeclarado, con su provenance y trazabilidad."""

    field_id: str
    value: Any
    provenance: Provenance
    confidence: float
    source_document_id: int | None = None


class SessionState(_Base):
    """Estado completo de la sesión, suficiente para reanudar el wizard."""

    session_id: str
    current_step: int = Field(ge=1, le=7)
    description: str | None = None
    sector: str | None = None
    plugin: str | None = None
    classification_confidence: float | None = None
    classification_citation: Citation | None = None
    bom: dict[str, Any] = Field(default_factory=dict)
    extracted_fields: list[FieldValue] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# --- POST /sessions/{id}/classify (F3-01) -----------------------------------


class ClassifyResponse(_Base):
    sector: str  # id del plugin o "unknown"
    plugin: str  # = sector cuando es conocido, "unknown" si no
    confidence: float = Field(ge=0.0, le=1.0)
    citation: Citation | None = Field(
        default=None,
        description="None solo si sector='unknown' o el RAG no devolvió fragmentos. Cuando la clasificación es exitosa la cita es obligatoria (invariante de F3-01).",
    )
    requires_review: bool = Field(
        description="True si confidence < 0.7 (umbral fijo del wizard)",
    )


class ClassifyOverrideRequest(_Base):
    """Override manual del sector (paso 2). Queda registrado en audit_log."""

    sector: str
    plugin: str
    reason: str = Field(min_length=10)


# --- PUT /sessions/{id}/bom -------------------------------------------------


class BomRequest(_Base):
    fields: dict[str, Any] = Field(description="Campos del BOM según schema del plugin")


class BomValidationError(_Base):
    field_id: str
    message: str


class BomResponse(_Base):
    accepted: bool
    errors: list[BomValidationError] = Field(default_factory=list)


# --- GET / POST /sessions/{id}/documents ------------------------------------


class RequiredDocumentSpec(_Base):
    """Documento requerido derivado del plugin + BOM (no hardcoded)."""

    doc_type: DocType
    mandatory: bool
    citation: Citation | None = None
    uploaded: bool


class UploadedDocument(_Base):
    id: int
    doc_type: DocType
    sha256: str
    uploaded_at: datetime


class DocumentsListResponse(_Base):
    required: list[RequiredDocumentSpec]
    uploaded: list[UploadedDocument]


class UploadDocumentResponse(_Base):
    """Multipart POST devuelve el documento creado (o el existente si dedupe por hash)."""

    document: UploadedDocument
    deduplicated: bool = Field(
        description="True si el sha256 ya existía y se devolvió el documento original",
    )


class DocumentExcerptResponse(_Base):
    """Fragmento del PDF que respalda un campo extraído (F4-05 criterio 2).

    `excerpt` contiene texto crudo con `…` indicando truncación; el frontend
    lo renderiza como pre-formatted. `match_found=False` cuando el valor no
    aparece literal en el PDF: se devuelve el inicio del documento como
    contexto general en vez de un fragmento concreto.
    """

    document_id: int
    field_id: str
    value: str
    excerpt: str
    match_found: bool
    page_number: int | None = None


# --- POST /sessions/{id}/extract (F3-02 SSE) --------------------------------


# Eventos SSE emitidos por el Recolector. El frontend los recibe como
# `event: <type>\ndata: <json>\n\n`. El JSON del campo `data` está tipado
# como una de estas clases según el `event`.

ExtractEvent = Literal["progress", "field_extracted", "done", "error"]


class ExtractProgress(_Base):
    event: Literal["progress"] = "progress"
    processed: int
    total: int
    current_document: str | None = None


class ExtractFieldExtracted(_Base):
    event: Literal["field_extracted"] = "field_extracted"
    field: FieldValue


class ExtractDone(_Base):
    event: Literal["done"] = "done"
    fields_total: int
    fields_verified: int
    fields_self_declared: int
    fields_pending: int


class ExtractError(_Base):
    event: Literal["error"] = "error"
    message: str
    document_id: int | None = None


# --- GET /sessions/{id}/verify (F3-03) --------------------------------------


class MissingField(_Base):
    field_id: str
    citation: Citation | None = None
    reason: str  # "required_pending" | "validation_failed"


class VerifyWarning(_Base):
    field_id: str | None = None
    message: str
    rule_id: str | None = None


class VerifyResponse(_Base):
    completeness: float = Field(ge=0.0, le=1.0)
    missing_fields: list[MissingField] = Field(default_factory=list)
    warnings: list[VerifyWarning] = Field(default_factory=list)
    can_publish: bool = Field(
        description="False si hay required_pending crítico — bloquea el paso 7",
    )


# --- POST /sessions/{id}/dpp (paso 7) ---------------------------------------


class DppResponse(_Base):
    gs1_uri: str
    public_url: str
    qr_png_url: str
    qr_svg_url: str
    signed: bool
    jsonld_url: str


# --- POST /chat (F3-04) -----------------------------------------------------


class ChatRequest(_Base):
    session_id: str
    message: str = Field(min_length=1)


class ChatFragment(_Base):
    """Fragmento del RAG usado para componer la respuesta. Mostrarlo es opcional."""

    cita: str  # ya renderizada: "Reglamento UE 2024/1781, Art. 7"
    texto: str
    score: float


class ChatResponse(_Base):
    """Respuesta del chat. Si `citation is None`, `answer` es la negativa estándar."""

    answer: str
    citation: Citation | None = None
    fragments: list[ChatFragment] = Field(default_factory=list)


class ChatHistoryMessage(_Base):
    """Mensaje persistido del histórico del chat (F3-04 criterio 3)."""

    role: Literal["user", "assistant"]
    content: str
    citation: Citation | None = None
    created_at: datetime


class ChatHistoryResponse(_Base):
    """Histórico completo del chat para una sesión, ordenado cronológicamente."""

    messages: list[ChatHistoryMessage] = Field(default_factory=list)
