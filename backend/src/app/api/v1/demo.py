"""Endpoints de demo precargada (gated por settings.demo_mode).

Sirven dos cosas:

1. `GET /api/v1/demo/sample/{sector}` — devuelve description + bom_fields que
   el frontend puede inyectar en los inputs del wizard (botones "Cargar
   ejemplo" en pasos 1 y 3).
2. `POST /api/v1/demo/sessions/{sid}/seed-documents` — genera al vuelo los
   PDFs sintéticos descritos en el config y los inserta como `Document` de
   la sesión. Reutiliza la misma deduplicación por SHA-256 que el upload
   normal.

Ambos endpoints leen los datos demo desde el YAML compartido en
`scripts/e2e_demo/config.yaml` (mismo origen que el runner E2E `run.py`),
para que un solo cambio en ese fichero se refleje en CLI y UI.

Si `DEMO_MODE=false` (default), los endpoints devuelven 404.
"""

from __future__ import annotations

import hashlib
import io
import json
import uuid
from pathlib import Path
from typing import Annotated, Any

import yaml
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.v1.schemas import DocType
from app.auth.deps import CurrentUser
from app.config import settings
from app.db.session import get_session
from app.models.documents import Document

router = APIRouter(prefix="/demo", tags=["demo"])

DbSession = Annotated[Session, Depends(get_session)]


# ─── localización del YAML compartido ─────────────────────────────────────────


def _discover_demo_config() -> Path | None:
    """Busca `scripts/e2e_demo/config.yaml` ascendiendo desde este módulo.

    Layout host: `<repo>/scripts/e2e_demo/config.yaml`.
    Layout container: `/app/scripts/e2e_demo/config.yaml` (montado por
    docker-compose; ver `docker-compose.yml`).
    """
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        candidate = parent / "scripts" / "e2e_demo" / "config.yaml"
        if candidate.is_file():
            return candidate
    return None


def _load_demo_config() -> dict[str, Any]:
    path = _discover_demo_config()
    if path is None:
        raise HTTPException(
            status_code=503,
            detail="demo_config_not_found: scripts/e2e_demo/config.yaml no está montado",
        )
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _require_demo_mode() -> None:
    if not settings.demo_mode:
        # 404 (no 403) para que el endpoint sea invisible en producción.
        raise HTTPException(status_code=404, detail="not_found")


# ─── GET /demo/sample/{sector} ────────────────────────────────────────────────


class DemoSampleResponse(BaseModel):
    sector: str
    description: str
    bom_fields: dict[str, Any]
    documents: list[dict[str, Any]]


@router.get("/sample/{sector}", response_model=DemoSampleResponse)
def get_sample(sector: str) -> DemoSampleResponse:
    """Devuelve los datos demo para `sector`. Sólo `batteries` por ahora."""
    _require_demo_mode()
    if sector != "batteries":
        raise HTTPException(status_code=404, detail=f"sin demo para sector={sector}")
    cfg = _load_demo_config()
    return DemoSampleResponse(
        sector=sector,
        description=cfg["description"],
        bom_fields=cfg["bom"]["fields"],
        documents=[
            {"doc_type": d["doc_type"], "title": d["title"], "embeds_count": len(d["embeds"])}
            for d in cfg.get("documents", [])
        ],
    )


# ─── POST /demo/sessions/{sid}/seed-documents ─────────────────────────────────


class SeededDoc(BaseModel):
    id: int
    doc_type: DocType
    sha256: str
    deduplicated: bool
    bytes: int


class SeedDocumentsResponse(BaseModel):
    seeded: list[SeededDoc]


def _build_pdf(title: str, embeds: list[str]) -> bytes:
    """Genera un PDF mínimo en memoria con un título y los bullets en `embeds`.

    Reportlab se importa perezosamente: solo lo necesita este endpoint, y
    si demo_mode=false no llegamos a esta función.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    flow: list[Any] = [
        Paragraph(f"<b>{title}</b>", styles["Title"]),
        Spacer(1, 12),
        Paragraph(
            "Documento sintético generado por el modo demo de PasaporteAbierto. "
            "No tiene validez legal — alimenta al Recolector con campos "
            "textuales reconocibles para mostrar el flujo end-to-end.",
            styles["Italic"],
        ),
        Spacer(1, 18),
    ]
    for line in embeds:
        flow.append(Paragraph(f"• {line}", styles["BodyText"]))
        flow.append(Spacer(1, 6))
    doc.build(flow)
    return buf.getvalue()


_UPLOADS_DIR: Path = Path(__file__).resolve().parents[5] / "backend" / "data" / "uploads"


@router.post("/sessions/{session_id}/seed-documents", response_model=SeedDocumentsResponse)
def seed_documents(session_id: str, db: DbSession) -> SeedDocumentsResponse:
    """Genera los PDFs sintéticos del config y los inserta en la sesión.

    Idempotente vía la dedup (session, sha256, doc_type) heredada del
    upload normal: re-ejecutar el endpoint no duplica documentos.
    """
    _require_demo_mode()

    # Validar que la sesión existe.
    from app.models.sessions import WizardSession  # import perezoso para evitar ciclos

    session_row = db.get(WizardSession, session_id)
    if session_row is None:
        raise HTTPException(status_code=404, detail="session_not_found")

    cfg = _load_demo_config()
    specs = cfg.get("documents", [])
    if not specs:
        raise HTTPException(status_code=503, detail="demo_config_sin_documentos")

    seeded: list[SeededDoc] = []
    session_dir = _UPLOADS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    for spec in specs:
        doc_type: DocType = spec["doc_type"]
        pdf_bytes = _build_pdf(spec["title"], spec["embeds"])
        file_hash = hashlib.sha256(pdf_bytes).hexdigest()

        # Dedup por (sesión, sha256, doc_type) — mismo criterio que upload normal.
        existing = db.exec(
            select(Document).where(
                Document.session_id == session_id,
                Document.sha256 == file_hash,
                Document.doc_type == doc_type,
            )
        ).first()
        if existing:
            seeded.append(
                SeededDoc(
                    id=existing.id,  # type: ignore[arg-type]
                    doc_type=existing.doc_type,
                    sha256=existing.sha256,
                    deduplicated=True,
                    bytes=len(pdf_bytes),
                )
            )
            continue

        blob_path = session_dir / f"{file_hash}.pdf"
        blob_path.write_bytes(pdf_bytes)
        doc = Document(
            session_id=session_id,
            doc_type=doc_type,
            blob_path=str(blob_path),
            sha256=file_hash,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        seeded.append(
            SeededDoc(
                id=doc.id,  # type: ignore[arg-type]
                doc_type=doc.doc_type,
                sha256=doc.sha256,
                deduplicated=False,
                bytes=len(pdf_bytes),
            )
        )

    return SeedDocumentsResponse(seeded=seeded)


# ─── POST /demo/seed-dashboard ────────────────────────────────────────────────
#
# Siembra un lote de DPP del usuario actual (unos en curso, otros publicados)
# para poder ver el dashboard poblado SIN ejecutar los pasos IA (clasificar /
# extraer necesitan LLM). Los finalizados se publican con la misma lógica
# determinista del paso 7 (build_jsonld + firma Ed25519), solo que los campos
# se autocompletan en vez de extraerse de PDFs. Gated por demo_mode + login.


class SeedDashboardResponse(BaseModel):
    created_in_progress: int
    created_published: int
    total_user_sessions: int


# Descripciones de ejemplo (variadas) para que el dashboard no se vea repetido.
_DEMO_DESCRIPTIONS_IN_PROGRESS = [
    "Batería LiFePO4 10 kWh para autoconsumo solar residencial, montaje en pared.",
    "Pack de baterías de tracción Li-ion 48 V para carretilla elevadora industrial.",
    "Módulo de almacenamiento estacionario 5 kWh con BMS integrado y refrigeración pasiva.",
]
_DEMO_DESCRIPTIONS_PUBLISHED = [
    "Batería industrial recargable Li-ion 5 kWh para almacenamiento residencial fijo interior.",
    "Sistema de baterías modular 15 kWh para microrred comercial, química NMC.",
]


def _serialize_value(value: Any) -> str:
    """Mismo criterio de serialización que el wizard (put_bom)."""
    return json.dumps(value) if isinstance(value, dict | list | bool) else str(value)


def _demo_value_for(field: Any) -> Any:
    """Valor de ejemplo plausible según el tipo del campo del plugin."""
    ftype = field.type
    if ftype == "enum":
        return (field.enum_values or ["n/a"])[0]
    if ftype == "integer":
        return 1200
    if ftype == "number":
        return 5.0
    if ftype == "boolean":
        return True
    if ftype == "repeater":
        return []
    return f"DEMO-{field.id}"


def _seed_published_dpp(db: Session, plugin: Any, user_id: str, description: str) -> None:
    """Crea una sesión y la publica de forma determinista (sin pasos IA)."""
    from app.audit import append_entry as append_audit
    from app.dpp import (
        build_gs1_uri,
        build_jsonld,
        canonical_payload,
        filter_public_fields,
        get_or_create_keypair,
        sign_payload,
    )
    from app.models.extracted_fields import ExtractedField
    from app.models.published_dpps import PublishedDPP
    from app.models.sessions import WizardSession

    session_id = str(uuid.uuid4())
    db.add(
        WizardSession(
            id=session_id,
            user_id=user_id,
            sector="batteries",
            plugin="batteries",
            classification_confidence=0.95,
            progress={"step": 7, "description": description},
        )
    )

    bom: dict[str, Any] = {}
    provenance: dict[str, str] = {}
    for i, f in enumerate(plugin.fields):
        if not f.required:
            continue
        value = _demo_value_for(f)
        bom[f.id] = value
        # Alterna verified/self_declared para que el DPP muestre variedad de procedencia.
        prov = "verified" if i % 2 == 0 else "self_declared"
        provenance[f.id] = prov
        db.add(
            ExtractedField(
                session_id=session_id,
                field_id=f.id,
                value=_serialize_value(value),
                provenance=prov,
                confidence=1.0,
            )
        )

    public_fields = filter_public_fields(plugin, bom)
    public_provenance = filter_public_fields(plugin, provenance)
    gs1_uri = build_gs1_uri(plugin, session_id)
    jsonld = build_jsonld(plugin, gs1_uri, public_fields, public_provenance)
    signed = sign_payload(get_or_create_keypair(), canonical_payload(jsonld))
    db.add(
        PublishedDPP(
            gs1_uri=gs1_uri,
            session_id=session_id,
            jsonld=jsonld,
            signature=signed.signature_b64,
            public_key=signed.public_key_b64,
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
            "signed": True,
            "demo_seed": True,
        },
    )
    db.commit()


def _seed_in_progress(db: Session, plugin: Any, user_id: str, description: str, step: int) -> None:
    """Crea una sesión en curso (con algunos campos y, opcionalmente, chat)."""
    from app.models.chat_messages import ChatMessage
    from app.models.extracted_fields import ExtractedField
    from app.models.sessions import WizardSession

    session_id = str(uuid.uuid4())
    classified = step >= 3
    db.add(
        WizardSession(
            id=session_id,
            user_id=user_id,
            sector="batteries" if classified else None,
            plugin="batteries" if classified else None,
            classification_confidence=0.91 if classified else None,
            progress={"step": step, "description": description},
        )
    )
    # A partir del paso 3 ya hay algunos campos autodeclarados.
    if classified:
        for i, f in enumerate(plugin.fields):
            if not f.required or i % 3 != 0:  # solo un subconjunto → "en curso"
                continue
            db.add(
                ExtractedField(
                    session_id=session_id,
                    field_id=f.id,
                    value=_serialize_value(_demo_value_for(f)),
                    provenance="self_declared",
                    confidence=1.0,
                )
            )
    # Una sesión en curso con conversación, para el badge "con chat".
    if step >= 5:
        db.add(
            ChatMessage(
                session_id=session_id,
                role="user",
                content="¿Qué exige el Art. 77 sobre el identificador único?",
            )
        )
        db.add(
            ChatMessage(
                session_id=session_id,
                role="assistant",
                content="El pasaporte usa un identificador único ISO/IEC 15459 [Reglamento UE 2023/1542, Art. 77.3].",
                citation={"regulation": "UE 2023/1542", "article": "77.3", "url": None},
            )
        )
    db.commit()


@router.post("/seed-dashboard", response_model=SeedDashboardResponse)
def seed_dashboard(db: DbSession, user: CurrentUser) -> SeedDashboardResponse:
    """Siembra DPP de ejemplo (en curso + publicados) para el usuario actual.

    Pensado para probar el dashboard sin Ollama: los publicados se generan con
    la lógica determinista del paso 7. Idempotencia: cada llamada añade un lote
    nuevo (el usuario controla cuántas veces lo pulsa).
    """
    _require_demo_mode()

    from app.models.sessions import WizardSession
    from app.plugins.loader import load_all_plugins

    plugins = load_all_plugins(settings.plugins_dir)
    plugin = plugins.get("batteries")
    if plugin is None:
        raise HTTPException(status_code=503, detail="plugin_batteries_no_disponible")

    steps = [1, 3, 5]
    for desc, step in zip(_DEMO_DESCRIPTIONS_IN_PROGRESS, steps, strict=True):
        _seed_in_progress(db, plugin, user.id, desc, step)
    for desc in _DEMO_DESCRIPTIONS_PUBLISHED:
        _seed_published_dpp(db, plugin, user.id, desc)

    total = len(db.exec(select(WizardSession).where(WizardSession.user_id == user.id)).all())
    return SeedDashboardResponse(
        created_in_progress=len(_DEMO_DESCRIPTIONS_IN_PROGRESS),
        created_published=len(_DEMO_DESCRIPTIONS_PUBLISHED),
        total_user_sessions=total,
    )
