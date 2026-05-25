"""Endpoints del wizard de 7 pasos (PR-0).

Estado:
  - POST /sessions y GET /sessions/{id} están **implementados** contra SQLite
    (persistencia real). Son la mínima base que F4-01 amplía.
  - Los demás endpoints son **stubs deterministas** marcados con header
    `X-Stub: true`. Devuelven datos fijos representativos para que el
    frontend pueda maquetar y B/A puedan trabajar sin esperar al otro.

Cada stub queda etiquetado con el ticket que lo reemplazará. Sustituir el
stub por la implementación real **no debe** cambiar el schema de salida
(ver `schemas.py`).
"""

import asyncio
import json
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from app.api.v1.schemas import (
    BomRequest,
    BomResponse,
    Citation,
    ClassifyOverrideRequest,
    ClassifyResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    DocumentsListResponse,
    DppResponse,
    ExtractDone,
    ExtractFieldExtracted,
    ExtractProgress,
    FieldValue,
    MissingField,
    RequiredDocumentSpec,
    SessionState,
    UpdateProgressRequest,
    VerifyResponse,
    VerifyWarning,
)
from app.classifier import classify as run_classifier
from app.db.session import get_session
from app.models.sessions import WizardSession
from app.time_utils import utcnow

DbSession = Annotated[Session, Depends(get_session)]

router = APIRouter(prefix="/sessions", tags=["wizard"])


def _stub(response: Response) -> None:
    """Marca la respuesta como stub para que el frontend lo detecte."""
    response.headers["X-Stub"] = "true"


# ---------------------------------------------------------------------------
# Implementados de verdad (mínimo necesario para que F4-01 trabaje contra BD)
# ---------------------------------------------------------------------------


def _to_session_state(row: WizardSession) -> SessionState:
    progress: dict[str, Any] = row.progress or {}
    return SessionState(
        session_id=row.id,
        current_step=progress.get("step", 1),
        description=progress.get("description"),
        sector=row.sector,
        plugin=row.plugin,
        classification_confidence=row.classification_confidence,
        classification_citation=None,
        bom=progress.get("bom", {}),
        extracted_fields=[],
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _get_or_404(db: Session, session_id: str) -> WizardSession:
    row = db.exec(select(WizardSession).where(WizardSession.id == session_id)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="session_not_found")
    return row


@router.post("", response_model=CreateSessionResponse, status_code=201)
def create_session(
    body: CreateSessionRequest,
    db: DbSession,
) -> CreateSessionResponse:
    """Crea sesión persistente con la descripción del paso 1."""
    session_id = str(uuid.uuid4())
    row = WizardSession(
        id=session_id,
        progress={"step": 1, "description": body.description},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return CreateSessionResponse(session_id=row.id, created_at=row.created_at)


@router.get("/{session_id}", response_model=SessionState)
def get_session_state(
    session_id: str,
    db: DbSession,
) -> SessionState:
    """Reanuda una sesión existente."""
    return _to_session_state(_get_or_404(db, session_id))


@router.patch("/{session_id}", response_model=SessionState)
def update_progress(
    session_id: str,
    body: UpdateProgressRequest,
    db: DbSession,
) -> SessionState:
    """Autosave del wizard. Mergea campos del body en `sessions.progress`.

    Reglas:
      - `step` reemplaza el actual (no se puede saltar a step > current+1 desde
        cliente; eso lo enforza el frontend, pero el backend NO bloquea
        retroceder ni avanzar — la regla de "no saltar hacia adelante" es UX,
        no de seguridad).
      - `bom` hace shallow-merge: claves no enviadas se mantienen.
      - `description` reemplaza la descripción del paso 1.

    `extracted_fields`, `sector`, `plugin` y `classification_confidence` se
    actualizan por endpoints específicos (classify, extract). NO se aceptan
    por aquí.
    """
    row = _get_or_404(db, session_id)
    progress: dict[str, Any] = dict(row.progress or {})

    if body.step is not None:
        progress["step"] = body.step
    if body.description is not None:
        progress["description"] = body.description
    if body.bom is not None:
        existing_bom: dict[str, Any] = dict(progress.get("bom", {}))
        existing_bom.update(body.bom)
        progress["bom"] = existing_bom

    row.progress = progress
    row.updated_at = utcnow()
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_session_state(row)


# ---------------------------------------------------------------------------
# Stubs — Persona A los reemplaza en F3-01 / F4-03 / F3-03 / F4-06
# ---------------------------------------------------------------------------


@router.post("/{session_id}/classify", response_model=ClassifyResponse)
def classify_session(
    session_id: str,
    db: DbSession,
) -> ClassifyResponse:
    """Clasifica la sesión usando el agente Clasificador (F3-01).

    Persiste `sector`, `plugin` y `classification_confidence` en `sessions`.
    Si el clasificador devuelve `unknown` o confianza baja, igualmente
    persiste lo devuelto (`requires_review=True` lo indica al frontend).
    """
    row = _get_or_404(db, session_id)
    progress: dict[str, Any] = row.progress or {}
    description = progress.get("description")
    if not description:
        raise HTTPException(status_code=400, detail="session_has_no_description")

    result = run_classifier(description)

    row.sector = result.sector
    row.plugin = result.plugin
    row.classification_confidence = result.confidence
    row.updated_at = utcnow()
    db.add(row)
    db.commit()

    citation = (
        Citation(
            regulation=result.citation_regulation,
            article=result.citation_article,
            url=result.citation_url,
        )
        if result.sector != "unknown"
        else None
    )
    return ClassifyResponse(
        sector=result.sector,
        plugin=result.plugin,
        confidence=result.confidence,
        citation=citation,
        requires_review=result.requires_review,
    )


@router.post("/{session_id}/classify/override", status_code=204)
def classify_override_stub(
    session_id: str,
    body: ClassifyOverrideRequest,
    response: Response,
) -> Response:
    """STUB de F3-01 (override manual). En real escribirá audit_log."""
    _stub(response)
    return Response(status_code=204, headers={"X-Stub": "true"})


@router.put("/{session_id}/bom", response_model=BomResponse)
def put_bom_stub(
    session_id: str,
    body: BomRequest,
    response: Response,
) -> BomResponse:
    """STUB de F4-03. Acepta cualquier dict sin validar contra plugin."""
    _stub(response)
    return BomResponse(accepted=True, errors=[])


@router.get("/{session_id}/documents", response_model=DocumentsListResponse)
def list_documents_stub(session_id: str, response: Response) -> DocumentsListResponse:
    """STUB de F4-04. Devuelve 3 docs requeridos típicos de baterías."""
    _stub(response)
    return DocumentsListResponse(
        required=[
            RequiredDocumentSpec(
                doc_type="datasheet",
                mandatory=True,
                citation=Citation(regulation="Reglamento UE 2023/1542", article="Annex XIII §1"),
                uploaded=False,
            ),
            RequiredDocumentSpec(
                doc_type="certificate",
                mandatory=True,
                citation=Citation(regulation="Reglamento UE 2023/1542", article="Art. 7"),
                uploaded=False,
            ),
            RequiredDocumentSpec(
                doc_type="lca",
                mandatory=False,
                citation=Citation(regulation="Reglamento UE 2023/1542", article="Annex II"),
                uploaded=False,
            ),
        ],
        uploaded=[],
    )


@router.get("/{session_id}/verify", response_model=VerifyResponse)
def verify_stub(session_id: str, response: Response) -> VerifyResponse:
    """STUB de F3-03. Devuelve completitud 0.8 con 2 faltantes."""
    _stub(response)
    return VerifyResponse(
        completeness=0.8,
        missing_fields=[
            MissingField(
                field_id="state_of_health",
                citation=Citation(regulation="Reglamento UE 2023/1542", article="Annex XIII §1.k"),
                reason="required_pending",
            ),
            MissingField(
                field_id="recycled_content",
                citation=Citation(regulation="Reglamento UE 2023/1542", article="Art. 8"),
                reason="required_pending",
            ),
        ],
        warnings=[
            VerifyWarning(
                field_id=None,
                message="Faltan 2 campos obligatorios para publicar el DPP.",
                rule_id=None,
            ),
        ],
        can_publish=False,
    )


@router.post("/{session_id}/dpp", response_model=DppResponse)
def generate_dpp_stub(session_id: str, response: Response) -> DppResponse:
    """STUB de F5 / paso 7. Devuelve URLs fake del DPP publicado."""
    _stub(response)
    gs1_uri = f"https://id.gs1.org/01/09506000134352/21/{session_id[:8]}"
    return DppResponse(
        gs1_uri=gs1_uri,
        public_url=f"http://localhost:3000/dpp/{session_id[:8]}",
        qr_png_url=f"/api/v1/sessions/{session_id}/dpp/qr.png",
        qr_svg_url=f"/api/v1/sessions/{session_id}/dpp/qr.svg",
        signed=False,
        jsonld_url=f"/api/v1/sessions/{session_id}/dpp/jsonld",
    )


# ---------------------------------------------------------------------------
# Stub SSE — Persona B reemplaza en F3-02
# ---------------------------------------------------------------------------


async def _fake_recolector_stream(session_id: str):
    """Emula la secuencia de eventos que emitirá el Recolector real."""
    fake_fields = [
        FieldValue(
            field_id="capacity_nominal",
            value="5000",
            provenance="verified",
            confidence=0.95,
            source_document_id=1,
        ),
        FieldValue(
            field_id="cycle_life",
            value="1000",
            provenance="verified",
            confidence=0.90,
            source_document_id=1,
        ),
        FieldValue(
            field_id="cobalt_content",
            value="12%",
            provenance="self_declared",
            confidence=0.60,
            source_document_id=None,
        ),
        FieldValue(
            field_id="state_of_health",
            value="",
            provenance="required_pending",
            confidence=0.0,
            source_document_id=None,
        ),
    ]

    total = len(fake_fields)
    yield _sse(ExtractProgress(processed=0, total=total, current_document="datasheet.pdf"))
    await asyncio.sleep(0.2)
    for i, field in enumerate(fake_fields, start=1):
        yield _sse(ExtractFieldExtracted(field=field))
        await asyncio.sleep(0.3)
        yield _sse(ExtractProgress(processed=i, total=total, current_document="datasheet.pdf"))
    yield _sse(
        ExtractDone(
            fields_total=total,
            fields_verified=sum(1 for f in fake_fields if f.provenance == "verified"),
            fields_self_declared=sum(1 for f in fake_fields if f.provenance == "self_declared"),
            fields_pending=sum(1 for f in fake_fields if f.provenance == "required_pending"),
        )
    )


def _sse(event: ExtractProgress | ExtractFieldExtracted | ExtractDone) -> str:
    payload = event.model_dump(mode="json")
    return f"event: {payload['event']}\ndata: {json.dumps(payload)}\n\n"


@router.post("/{session_id}/extract")
async def extract_stub(session_id: str) -> StreamingResponse:
    """STUB de F3-02. SSE con 4 campos fake (verified/self_declared/required_pending)."""
    return StreamingResponse(
        _fake_recolector_stream(session_id),
        media_type="text/event-stream",
        headers={"X-Stub": "true", "Cache-Control": "no-cache"},
    )
