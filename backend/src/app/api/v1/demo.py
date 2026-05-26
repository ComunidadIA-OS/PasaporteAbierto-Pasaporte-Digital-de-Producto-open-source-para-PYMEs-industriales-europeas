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
from pathlib import Path
from typing import Annotated, Any

import yaml
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.v1.schemas import DocType
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
