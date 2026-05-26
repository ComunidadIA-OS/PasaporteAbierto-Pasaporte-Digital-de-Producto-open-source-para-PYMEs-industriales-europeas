"""Router del wizard de 7 pasos.

Todos los endpoints están implementados (F3-F5). Endpoints expuestos:

  - POST   /sessions                                   (paso 1, crear sesión)
  - GET    /sessions/{id}                              (reanudar sesión)
  - PATCH  /sessions/{id}                              (autosave de progreso)
  - POST   /sessions/{id}/classify                     (paso 2, Clasificador)
  - POST   /sessions/{id}/classify/override            (override manual)
  - PUT    /sessions/{id}/bom                          (paso 3, BOM)
  - GET    /sessions/{id}/documents                    (paso 4, listar requeridos)
  - POST   /sessions/{id}/documents                    (paso 4, subir PDF)
  - GET    /sessions/{id}/documents/{doc_id}/excerpt   (fragmento PDF fuente)
  - POST   /sessions/{id}/extract                      (paso 5, Recolector SSE)
  - GET    /sessions/{id}/verify                       (paso 6, Verificador)
  - POST   /sessions/{id}/dpp                          (paso 7, generar y publicar)
  - GET    /sessions/{id}/dpp/qr.png                   (QR PNG del DPP)
  - GET    /sessions/{id}/dpp/qr.svg                   (QR SVG del DPP)

Los schemas Pydantic en `app.api.v1.schemas` actúan como contrato
congelado entre backend y frontend: cambiar el shape de respuesta
exige ticket explícito y migración del cliente.
"""

import hashlib
import json
import uuid
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile
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
    DocType,
    DocumentExcerptResponse,
    DocumentsListResponse,
    DppPublishRequest,
    DppResponse,
    FieldValue,
    MissingField,
    RequiredDocumentSpec,
    SessionState,
    UpdateProgressRequest,
    UploadDocumentResponse,
    UploadedDocument,
    VerifyResponse,
    VerifyWarning,
)
from app.audit import append_entry as append_audit
from app.classifier import classify as run_classifier
from app.db.session import get_session
from app.dpp import (
    build_gs1_uri,
    build_jsonld,
    canonical_payload,
    filter_public_fields,
    generate_qr_png,
    generate_qr_svg,
    get_or_create_keypair,
    public_dpp_url,
    sign_payload,
)
from app.models.documents import Document
from app.models.extracted_fields import ExtractedField
from app.models.published_dpps import PublishedDPP
from app.models.sessions import WizardSession
from app.plugins.conditions import evaluate_when
from app.plugins.loader import Plugin, PluginField, load_all_plugins
from app.time_utils import utcnow
from app.verifier import verify_session as run_verifier

# Resolver del directorio de plugins. Centralizado en config.py para soportar
# tanto el layout del host como el del contenedor.
from app.config import settings  # noqa: E402

_PLUGINS_DIR: Path = settings.plugins_dir

DbSession = Annotated[Session, Depends(get_session)]

router = APIRouter(prefix="/sessions", tags=["wizard"])


def _to_session_state(row: WizardSession, db: Session | None = None) -> SessionState:
    """Construye el `SessionState` completo desde BD.

    Pasar `db` permite rellenar `extracted_fields` con lo realmente persistido y
    construir la `classification_citation` desde `progress["classification_citation"]`
    (persistido por `classify_session`). Si `db` es None, ambos vienen vacíos —
    sólo conviene en pruebas o cuando el caller ya tiene los datos.
    """
    progress: dict[str, Any] = row.progress or {}

    citation: Citation | None = None
    raw_citation = progress.get("classification_citation")
    if isinstance(raw_citation, dict) and raw_citation.get("regulation"):
        citation = Citation(
            regulation=str(raw_citation.get("regulation", "")),
            article=str(raw_citation.get("article", "")),
            url=raw_citation.get("url"),
        )

    extracted: list[FieldValue] = []
    if db is not None:
        rows = db.exec(select(ExtractedField).where(ExtractedField.session_id == row.id)).all()
        for ef in rows:
            extracted.append(
                FieldValue(
                    field_id=ef.field_id,
                    value=ef.value,
                    provenance=ef.provenance,  # type: ignore[arg-type]
                    confidence=ef.confidence,
                    source_document_id=ef.source_document_id,
                )
            )

    return SessionState(
        session_id=row.id,
        current_step=progress.get("step", 1),
        description=progress.get("description"),
        sector=row.sector,
        plugin=row.plugin,
        classification_confidence=row.classification_confidence,
        classification_citation=citation,
        bom=progress.get("bom", {}),
        extracted_fields=extracted,
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
    return _to_session_state(_get_or_404(db, session_id), db)


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
    return _to_session_state(row, db)


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
    progress: dict[str, Any] = dict(row.progress or {})
    description = progress.get("description")
    if not description:
        raise HTTPException(status_code=400, detail="session_has_no_description")

    result = run_classifier(description)

    row.sector = result.sector
    row.plugin = result.plugin
    row.classification_confidence = result.confidence

    # Persistir la cita en `progress` para que _to_session_state pueda
    # reconstruirla en futuros GET /sessions/{id} (no hay columna dedicada).
    if result.sector != "unknown":
        progress["classification_citation"] = {
            "regulation": result.citation_regulation,
            "article": result.citation_article,
            "url": result.citation_url,
        }
    else:
        progress.pop("classification_citation", None)
    row.progress = progress

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


@router.post("/{session_id}/classify/override", response_model=SessionState)
def classify_override(
    session_id: str,
    body: ClassifyOverrideRequest,
    db: DbSession,
) -> SessionState:
    """Override manual del sector clasificado (F4-02).

    Reemplaza `sessions.sector` y `sessions.plugin` con los del body y
    registra una entrada en `audit_log` con `operation="classify_override"`,
    el motivo del fabricante y los valores antes/después. La confianza
    pasa a 1.0 (decisión humana explícita).
    """
    row = _get_or_404(db, session_id)
    previous = {"sector": row.sector, "plugin": row.plugin}

    row.sector = body.sector
    row.plugin = body.plugin
    row.classification_confidence = 1.0
    row.updated_at = utcnow()
    db.add(row)

    # Borrar la cita persistida: el override es decisión humana, no del clasificador
    # automático con cita normativa del RAG.
    progress_override: dict[str, Any] = dict(row.progress or {})
    if progress_override.pop("classification_citation", None) is not None:
        row.progress = progress_override

    append_audit(
        db,
        operation="classify_override",
        payload={
            "session_id": session_id,
            "previous": previous,
            "new": {"sector": body.sector, "plugin": body.plugin},
            "reason": body.reason,
        },
    )
    db.commit()
    db.refresh(row)
    return _to_session_state(row, db)


def _validate_field_value(field: PluginField, value: Any) -> str | None:
    """Devuelve mensaje de error si el valor no encaja en el tipo del campo, else None."""
    if value is None:
        return None  # ausencia se controla aparte (required check)
    ftype = field.type
    if ftype == "string":
        if not isinstance(value, str):
            return "se esperaba string"
    elif ftype == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            return "se esperaba integer"
    elif ftype == "number":
        if isinstance(value, bool) or not isinstance(value, int | float):
            return "se esperaba number"
    elif ftype == "boolean":
        if not isinstance(value, bool):
            return "se esperaba boolean"
    elif ftype == "enum":
        if not isinstance(value, str):
            return "se esperaba string (enum)"
        allowed = field.enum_values or []
        if value not in allowed:
            return f"valor fuera del enum permitido ({', '.join(allowed)})"
    elif ftype == "repeater" and not isinstance(value, list):
        return "se esperaba lista (repeater)"
    return None


def _resolve_plugin(name: str | None) -> Plugin:
    """Carga el plugin asociado a la sesión; 400 si no hay sector o 404 si falta YAML."""
    if not name:
        raise HTTPException(status_code=400, detail="session_has_no_plugin")
    plugins = load_all_plugins(_PLUGINS_DIR)
    plugin = plugins.get(name)
    if plugin is None:
        raise HTTPException(status_code=404, detail=f"plugin_not_found: {name}")
    return plugin


@router.put("/{session_id}/bom", response_model=BomResponse)
def put_bom(
    session_id: str,
    body: BomRequest,
    db: DbSession,
) -> BomResponse:
    """Guarda el BOM del paso 3 con `provenance='self_declared'`.

    Validaciones:
      - Cada `field_id` debe existir en el plugin de la sesión.
      - Cada valor debe encajar en el tipo declarado en el plugin.
      - `required` faltantes se reportan en `errors` pero NO bloquean el save
        (save parcial permitido — el chequeo "puede avanzar" lo hace F3-03).

    Persiste en `extracted_fields` con upsert por (session_id, field_id) y
    `provenance='self_declared'`. F3-02 (Recolector) hace UPDATE sobre los
    mismos registros si verifica con PDFs.
    """
    row = _get_or_404(db, session_id)
    plugin = _resolve_plugin(row.plugin)
    field_map: dict[str, PluginField] = {f.id: f for f in plugin.fields}

    errors: list[dict[str, str]] = []
    valid_inputs: dict[str, Any] = {}

    for fid, value in body.fields.items():
        field = field_map.get(fid)
        if field is None:
            errors.append({"field_id": fid, "message": "campo no definido en el plugin"})
            continue
        err = _validate_field_value(field, value)
        if err:
            errors.append({"field_id": fid, "message": err})
            continue
        valid_inputs[fid] = value

    # Required faltantes (no rompen el save, solo se reportan).
    # Si el usuario envió el campo pero con tipo inválido, el error de tipo
    # ya está reportado; no duplicamos "requerido — falta valor".
    submitted = set(body.fields.keys())
    for f in plugin.fields:
        if not f.required or f.id in submitted:
            continue
        already = db.exec(
            select(ExtractedField).where(
                ExtractedField.session_id == session_id,
                ExtractedField.field_id == f.id,
            )
        ).first()
        if already is None:
            errors.append({"field_id": f.id, "message": "requerido — falta valor"})

    # Upsert de los valores válidos.
    for fid, value in valid_inputs.items():
        existing = db.exec(
            select(ExtractedField).where(
                ExtractedField.session_id == session_id,
                ExtractedField.field_id == fid,
            )
        ).first()
        serialized = json.dumps(value) if isinstance(value, dict | list | bool) else str(value)
        if existing is not None:
            existing.value = serialized
            existing.provenance = "self_declared"
            existing.confidence = 1.0
            existing.source_document_id = None
            db.add(existing)
        else:
            db.add(
                ExtractedField(
                    session_id=session_id,
                    field_id=fid,
                    value=serialized,
                    provenance="self_declared",
                    confidence=1.0,
                    source_document_id=None,
                )
            )

    # Reflejar BOM válido en progress (para reanudación rápida sin re-leer).
    progress: dict[str, Any] = dict(row.progress or {})
    progress["bom"] = {**progress.get("bom", {}), **valid_inputs}
    row.progress = progress
    row.updated_at = utcnow()
    db.add(row)
    db.commit()

    return BomResponse(
        accepted=not any(e["message"] != "requerido — falta valor" for e in errors),
        errors=[{"field_id": e["field_id"], "message": e["message"]} for e in errors],
    )


_UPLOADS_DIR: Path = Path(__file__).resolve().parents[5] / "backend" / "data" / "uploads"
_MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB


@router.get("/{session_id}/documents", response_model=DocumentsListResponse)
def list_documents(session_id: str, db: DbSession) -> DocumentsListResponse:
    """Listado de documentos requeridos y subidos (F4-04).

    Deriva la lista de documentos requeridos del plugin + BOM (condiciones
    `when`). Nunca hardcodeado en frontend.
    """
    row = _get_or_404(db, session_id)
    plugin = _resolve_plugin(row.plugin)
    bom = _bom_from_extracted(db, session_id, plugin)

    # Documentos ya subidos
    uploaded_rows = db.exec(select(Document).where(Document.session_id == session_id)).all()
    uploaded_types = {d.doc_type for d in uploaded_rows}

    # Documentos requeridos según plugin + condiciones when. La cita normativa
    # del documento viene del propio plugin YAML (campo opcional `citation` en
    # required_documents). Si el plugin no la declara, la API devuelve
    # `citation=null` antes que inventar una referencia regulatoria genérica.
    required: list[RequiredDocumentSpec] = []
    for rd in plugin.required_documents:
        if not evaluate_when(rd.when, bom):
            continue
        doc_citation: Citation | None = None
        if rd.citation is not None:
            doc_citation = Citation(
                regulation=f"Reglamento {rd.citation.regulation}",
                article=rd.citation.article,
            )
        required.append(
            RequiredDocumentSpec(
                doc_type=rd.type,
                mandatory=rd.mandatory,
                citation=doc_citation,
                uploaded=rd.type in uploaded_types,
            )
        )

    return DocumentsListResponse(
        required=required,
        uploaded=[
            UploadedDocument(
                id=d.id,  # type: ignore[arg-type]
                doc_type=d.doc_type,
                sha256=d.sha256,
                uploaded_at=d.uploaded_at,
            )
            for d in uploaded_rows
        ],
    )


@router.post("/{session_id}/documents", response_model=UploadDocumentResponse)
async def upload_document(
    session_id: str,
    file: UploadFile,
    db: DbSession,
    doc_type: DocType = Query(
        ..., description="Tipo de documento: datasheet, certificate, lca, sds, ce_declaration"
    ),
) -> UploadDocumentResponse:
    """Subida de documentos con deduplicación por (sesión, sha256, doc_type) (F4-04).

    - Límite de 10 MB por fichero.
    - `doc_type` validado contra el Literal `DocType` (422 antes de tocar disco).
    - Dedupe incluye `doc_type`: el mismo PDF puede subirse como tipos distintos
      (p. ej. el fabricante quiere clasificar el mismo informe como `datasheet`
      y `certificate`) sin que la segunda subida devuelva el primero.
    - Guarda el blob en `backend/data/uploads/{session_id}/`.
    """
    _get_or_404(db, session_id)

    # Leer contenido y validar tamaño
    content = await file.read()
    if len(content) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"file_too_large: máximo {_MAX_FILE_SIZE // (1024 * 1024)} MB",
        )

    # Calcular SHA-256
    file_hash = hashlib.sha256(content).hexdigest()

    # Deduplicar por (session, sha256, doc_type) — incluir doc_type evita que el
    # mismo PDF subido como "datasheet" devuelva la fila al subirlo después como
    # "certificate", bloqueando el segundo doc_type silenciosamente.
    existing = db.exec(
        select(Document).where(
            Document.session_id == session_id,
            Document.sha256 == file_hash,
            Document.doc_type == doc_type,
        )
    ).first()
    if existing:
        return UploadDocumentResponse(
            document=UploadedDocument(
                id=existing.id,  # type: ignore[arg-type]
                doc_type=existing.doc_type,
                sha256=existing.sha256,
                uploaded_at=existing.uploaded_at,
            ),
            deduplicated=True,
        )

    # Guardar blob en disco
    session_dir = _UPLOADS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    blob_path = session_dir / f"{file_hash}.pdf"
    blob_path.write_bytes(content)

    # Persistir en BD
    doc = Document(
        session_id=session_id,
        doc_type=doc_type,
        blob_path=str(blob_path),
        sha256=file_hash,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return UploadDocumentResponse(
        document=UploadedDocument(
            id=doc.id,  # type: ignore[arg-type]
            doc_type=doc.doc_type,
            sha256=doc.sha256,
            uploaded_at=doc.uploaded_at,
        ),
        deduplicated=False,
    )


# Longitud del fragmento devuelto en el endpoint de excerpt. ~200 chars antes
# y después del match suelen bastar para que el fabricante reconozca el dato
# en su PDF y verifique visualmente la extracción del Recolector.
_EXCERPT_CONTEXT_CHARS: int = 200


def _find_excerpt_in_pdf(blob_path: str, value: str) -> tuple[str, bool, int | None]:
    """Busca `value` (case-insensitive) en el texto del PDF y devuelve contexto.

    Retorna (excerpt, match_found, page_number_o_None). Si el valor no
    aparece literal en ninguna página, devuelve los primeros 500 chars del
    PDF como contexto general con match_found=False. pdfplumber se importa
    perezosamente porque es pesado y solo lo necesita este endpoint.
    """
    import pdfplumber

    needle = value.strip().lower()
    if not needle:
        return "", False, None

    with pdfplumber.open(blob_path) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            haystack = text.lower()
            pos = haystack.find(needle)
            if pos == -1:
                continue
            start = max(0, pos - _EXCERPT_CONTEXT_CHARS)
            end = min(len(text), pos + len(needle) + _EXCERPT_CONTEXT_CHARS)
            prefix = "…" if start > 0 else ""
            suffix = "…" if end < len(text) else ""
            return f"{prefix}{text[start:end].strip()}{suffix}", True, page_idx

        # No encontrado: devolver un primer pantallazo del PDF como contexto.
        first_page_text = (pdf.pages[0].extract_text() or "").strip()
        snippet = first_page_text[:500]
        if len(first_page_text) > 500:
            snippet += "…"
        return snippet, False, None


@router.get(
    "/{session_id}/documents/{doc_id}/excerpt",
    response_model=DocumentExcerptResponse,
)
def get_document_excerpt(
    session_id: str,
    doc_id: int,
    field_id: str,
    db: DbSession,
) -> DocumentExcerptResponse:
    """Devuelve un fragmento del PDF que respalda un campo extraído (F4-05 #2).

    Permite al fabricante verificar visualmente la procedencia del valor
    extraído por el Recolector. Si el valor aparece literal en el PDF, se
    devuelve con ~200 chars de contexto antes/después y el número de página;
    si no aparece (campos numéricos formateados de forma distinta, valores
    self_declared no presentes en PDF), se devuelve un pantallazo del inicio
    con `match_found=False`.

    Errores:
      - 404 si la sesión, el documento o el campo no existen.
      - 409 si el documento no pertenece a esta sesión (evita filtración de
        contenido entre sesiones).
    """
    _get_or_404(db, session_id)

    doc = db.exec(select(Document).where(Document.id == doc_id)).first()
    if doc is None:
        raise HTTPException(status_code=404, detail="document_not_found")
    if doc.session_id != session_id:
        # No filtramos blobs entre sesiones aunque el id sea adivinable.
        raise HTTPException(status_code=409, detail="document_not_in_session")

    ef = db.exec(
        select(ExtractedField).where(
            ExtractedField.session_id == session_id,
            ExtractedField.field_id == field_id,
        )
    ).first()
    if ef is None:
        raise HTTPException(status_code=404, detail="field_not_found")

    try:
        excerpt, match_found, page = _find_excerpt_in_pdf(doc.blob_path, ef.value)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="document_blob_missing") from None
    except Exception as e:
        # pdfplumber fallando no debe tumbar el endpoint: devolvemos 422 con motivo.
        raise HTTPException(status_code=422, detail=f"pdf_read_error: {type(e).__name__}") from e

    return DocumentExcerptResponse(
        document_id=doc_id,
        field_id=field_id,
        value=ef.value,
        excerpt=excerpt,
        match_found=match_found,
        page_number=page,
    )


@router.get("/{session_id}/verify", response_model=VerifyResponse)
def verify(session_id: str, db: DbSession) -> VerifyResponse:
    """Verificador determinista (F3-03). Valida estado de sesión contra plugin.

    GET porque es idempotente: no escribe BD ni audit_log. El audit log de
    "verify pasó / falló" se escribe en F4-06 al publicar (allí sí hay
    decisión, no antes).
    """
    row = _get_or_404(db, session_id)
    plugin = _resolve_plugin(row.plugin)
    result = run_verifier(db, row, plugin)
    return VerifyResponse(
        completeness=result.completeness,
        missing_fields=[
            MissingField(
                field_id=m.field_id,
                citation=Citation(
                    regulation=m.citation_regulation,
                    article=m.citation_article,
                ),
                reason=m.reason,
            )
            for m in result.missing_fields
        ],
        warnings=[
            VerifyWarning(rule_id=w.rule_id, field_id=w.field_id, message=w.message)
            for w in result.warnings
        ],
        can_publish=result.can_publish,
    )


def _bom_from_extracted(db: Session, session_id: str, plugin: Plugin) -> dict[str, Any]:
    """Recupera todos los `extracted_fields` de la sesión deserializados."""
    bom, _ = _bom_and_provenance_from_extracted(db, session_id, plugin)
    return bom


def _bom_and_provenance_from_extracted(
    db: Session, session_id: str, plugin: Plugin
) -> tuple[dict[str, Any], dict[str, str]]:
    """Como `_bom_from_extracted` pero también devuelve provenance por campo.

    Provenance refleja el origen del valor en `extracted_fields.provenance`
    (`verified` si lo extrajo el Recolector contra un PDF, `self_declared`
    si lo escribió el fabricante a mano). `required_pending` se filtra:
    no hay valor que mostrar todavía.
    """
    rows = db.exec(select(ExtractedField).where(ExtractedField.session_id == session_id)).all()
    field_map = {f.id: f for f in plugin.fields}
    bom: dict[str, Any] = {}
    prov: dict[str, str] = {}
    for r in rows:
        f = field_map.get(r.field_id)
        if f is None or r.provenance == "required_pending":
            continue
        v: Any = r.value
        if f.type == "boolean":
            v = r.value.lower() in ("true", "1", "yes")
        elif f.type == "integer":
            try:
                v = int(r.value)
            except ValueError:
                continue
        elif f.type == "number":
            try:
                v = float(r.value)
            except ValueError:
                continue
        elif f.type == "repeater":
            try:
                v = json.loads(r.value)
                if not isinstance(v, list):
                    continue
            except json.JSONDecodeError:
                continue
        bom[r.field_id] = v
        prov[r.field_id] = r.provenance
    return bom, prov


@router.post("/{session_id}/dpp", response_model=DppResponse)
def generate_dpp(
    session_id: str,
    db: DbSession,
    body: DppPublishRequest | None = None,
) -> DppResponse:
    """Genera y publica el DPP (paso 7). Firma Ed25519 opcional (F5-04 CA #3).

    - 409 si `verify` indica que no se puede publicar (required pendientes).
    - 409 si la sesión ya tiene un DPP publicado (idempotencia: no re-publicamos).
    - Persiste JSON-LD en `published_dpps`. Si `sign=True` (default), adjunta
      firma Ed25519 + clave pública en la misma fila; si `sign=False`, ambas
      quedan NULL y la respuesta indica `signed=false`.
    - Escribe entry en `audit_log` con `operation='publish'` y hash del JSON-LD.
    """
    row = _get_or_404(db, session_id)
    plugin = _resolve_plugin(row.plugin)

    verify_result = run_verifier(db, row, plugin)
    if not verify_result.can_publish:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "cannot_publish",
                "completeness": verify_result.completeness,
                "missing_count": len(verify_result.missing_fields),
            },
        )

    existing = db.exec(select(PublishedDPP).where(PublishedDPP.session_id == session_id)).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="dpp_already_published")

    bom, provenance = _bom_and_provenance_from_extracted(db, session_id, plugin)
    public_fields = filter_public_fields(plugin, bom)
    public_provenance = filter_public_fields(plugin, provenance)

    gs1_uri = build_gs1_uri(plugin, session_id)
    jsonld = build_jsonld(plugin, gs1_uri, public_fields, public_provenance)

    sign_dpp = body.sign if body is not None else True
    signature_b64: str | None = None
    public_key_b64: str | None = None
    if sign_dpp:
        key = get_or_create_keypair()
        signed = sign_payload(key, canonical_payload(jsonld))
        signature_b64 = signed.signature_b64
        public_key_b64 = signed.public_key_b64

    db.add(
        PublishedDPP(
            gs1_uri=gs1_uri,
            session_id=session_id,
            jsonld=jsonld,
            signature=signature_b64,
            public_key=public_key_b64,
        )
    )
    append_audit(
        db,
        operation="publish",
        payload={
            "session_id": session_id,
            "gs1_uri": gs1_uri,
            "jsonld_sha256": hashlib.sha256(canonical_payload(jsonld)).hexdigest(),
            "public_fields_count": len(public_fields),
            "signed": sign_dpp,
        },
    )
    db.commit()

    slug = session_id.split("-", 1)[0]
    public_url = public_dpp_url(slug)
    return DppResponse(
        gs1_uri=gs1_uri,
        public_url=public_url,
        qr_png_url=f"/api/v1/sessions/{session_id}/dpp/qr.png",
        qr_svg_url=f"/api/v1/sessions/{session_id}/dpp/qr.svg",
        signed=sign_dpp,
        jsonld_url=public_url,
    )


def _published_or_404(db: Session, session_id: str) -> PublishedDPP:
    pdpp = db.exec(select(PublishedDPP).where(PublishedDPP.session_id == session_id)).first()
    if pdpp is None:
        raise HTTPException(status_code=404, detail="dpp_not_published")
    return pdpp


def _public_url_for(pdpp: PublishedDPP) -> str:
    """Reconstruye la URL pública absoluta del DPP para impresión en QR."""
    slug = pdpp.session_id.split("-", 1)[0]
    return public_dpp_url(slug)


@router.get("/{session_id}/dpp/qr.png")
def dpp_qr_png(session_id: str, db: DbSession) -> Response:
    pdpp = _published_or_404(db, session_id)
    return Response(content=generate_qr_png(_public_url_for(pdpp)), media_type="image/png")


@router.get("/{session_id}/dpp/qr.svg")
def dpp_qr_svg(session_id: str, db: DbSession) -> Response:
    pdpp = _published_or_404(db, session_id)
    return Response(content=generate_qr_svg(_public_url_for(pdpp)), media_type="image/svg+xml")


@router.post("/{session_id}/extract")
async def extract(session_id: str, db: DbSession) -> StreamingResponse:
    """Ejecuta el Recolector de PDFs (F3-02).

    Pipeline híbrido: pdfplumber + LLM. Emite eventos SSE campo a campo
    para que el frontend muestre progreso en tiempo real. No dialoga con
    el usuario: escribe en extracted_fields y devuelve control al wizard.
    """
    from app.collector import extract_fields as run_collector

    row = _get_or_404(db, session_id)
    plugin = _resolve_plugin(row.plugin)
    bom = _bom_from_extracted(db, session_id, plugin)

    return StreamingResponse(
        run_collector(session_id, db, plugin, bom),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
