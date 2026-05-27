"""Tests del Recolector (F3-02).

Cubre el refactor a paralelismo entre PDFs (`asyncio.gather`):

  1. `test_collector_parallelizes_pdfs` — el tiempo total no escala con
     `nº PDFs × nº campos` sino con `nº campos` (los PDFs van en paralelo
     y los campos secuenciales dentro de cada PDF).

  2. `test_collector_attributes_source_to_confirming_pdf` — cuando
     varios PDFs entran a la extracción, `source_document_id` apunta al
     PDF que efectivamente confirmó el valor del BOM, no al primero.

Ambos tests bypassean `pdfplumber` y `app.llm.complete` con monkeypatch:
el objetivo es validar la orquestación paralela y la atribución, no la
calidad del LLM ni del parsing de PDFs.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

import app.collector.agent as agent_module
from app.collector.agent import extract_fields
from app.llm import LLMResponse

# Necesario para registrar las tablas usadas por la BD del test.
from app.models import (  # noqa: F401  (registro de metadata)
    audit_log,
    chat_messages,
    documents,
    extracted_fields,
    published_dpps,
    sessions,
)
from app.models.documents import Document
from app.models.extracted_fields import ExtractedField
from app.models.sessions import WizardSession
from app.plugins.loader import Citation, Plugin, PluginField


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Session]:
    """Sesión SQLite efímera por test (no usa el TestClient HTTP)."""
    db_path = tmp_path / "collector.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _mk_plugin(field_ids: list[str]) -> Plugin:
    """Plugin sintético con N campos `string` obligatorios."""
    return Plugin(
        name="test_sector",
        regulation="Test 2024/00",
        version="0.0.1",
        fields=[
            PluginField(
                id=fid,
                type="string",
                required=True,
                citation=Citation(regulation="Test 2024/00", article="Art. 1"),
            )
            for fid in field_ids
        ],
        required_documents=[],
    )


def _mk_session_with_docs(db: Session, n_docs: int) -> tuple[str, list[Document]]:
    """Crea una sesión y N documentos asociados. Devuelve (session_id, docs)."""
    sid = f"sess-{n_docs}"
    db.add(WizardSession(id=sid))
    db.commit()

    docs: list[Document] = []
    for i in range(n_docs):
        doc = Document(
            session_id=sid,
            doc_type="datasheet",
            blob_path=f"/tmp/doc_{i}.pdf",
            sha256=f"{i:064d}",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        docs.append(doc)
    return sid, docs


async def _drain(gen) -> list[dict]:
    """Consume el AsyncIterator y devuelve los eventos SSE parseados."""
    events: list[dict] = []
    async for chunk in gen:
        # Cada chunk es "event: X\ndata: <json>\n\n".
        for line in chunk.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: ") :]))
    return events


# ════════════════════════════════════════════════════════════════════════════
# 1) Paralelismo entre PDFs
# ════════════════════════════════════════════════════════════════════════════


def test_collector_parallelizes_pdfs(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Con 3 PDFs y 2 campos, el tiempo total debe escalar como
    `nº campos × delay` (PDFs en paralelo), no como `nº PDFs × nº campos × delay`.

    Cada llamada `complete` simula 100 ms de trabajo bloqueante (`time.sleep`
    porque `complete` es síncrono y corre en `asyncio.to_thread`).
    """
    n_pdfs = 3
    sid, docs = _mk_session_with_docs(db, n_pdfs)

    # Monkeypatch: extracción de texto sin tocar disco.
    monkeypatch.setattr(
        agent_module,
        "_extract_text_from_pdf",
        lambda blob_path: f"texto del PDF {blob_path}",
    )

    call_count = 0

    def _fake_complete(prompt: str, **_kwargs) -> LLMResponse:
        nonlocal call_count
        call_count += 1
        time.sleep(0.1)  # complete es síncrono → asyncio.to_thread paraleliza
        return LLMResponse(
            content='{"value": "foo", "confidence": 0.9}',
            tokens_in=0,
            tokens_out=0,
            model="fake",
            backend="fake:fake",
        )

    monkeypatch.setattr(agent_module, "complete", _fake_complete)

    plugin = _mk_plugin(["field_a", "field_b"])

    t0 = time.perf_counter()
    asyncio.run(_drain(extract_fields(sid, db, plugin, bom={})))
    duration = time.perf_counter() - t0

    # 3 PDFs × 2 campos = 6 llamadas a complete en total.
    assert call_count == n_pdfs * len(plugin.fields), (
        f"esperaba {n_pdfs * len(plugin.fields)} llamadas a complete, " f"se hicieron {call_count}"
    )

    # Con paralelismo entre PDFs y secuencial dentro de cada PDF:
    # tiempo ≈ nº campos × delay = 2 × 0.1 = 0.2s.
    # Sin paralelismo serían 6 × 0.1 = 0.6s. Margen para overhead del runtime.
    assert duration < 0.4, (
        f"el Recolector tardó {duration:.2f}s — sin paralelismo entre PDFs "
        f"el mínimo sería ~{n_pdfs * len(plugin.fields) * 0.1:.2f}s"
    )


# ════════════════════════════════════════════════════════════════════════════
# 2) Atribución correcta de source_document_id
# ════════════════════════════════════════════════════════════════════════════


def test_collector_attributes_source_to_confirming_pdf(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Si el valor del BOM solo aparece en el tercer PDF, el campo
    `verified` resultante debe tener `source_document_id = doc_c.id`,
    NO `doc_a.id` (regresión del bug del all_text concatenado).
    """
    sid, docs = _mk_session_with_docs(db, 3)
    doc_a, doc_b, doc_c = docs

    # Marcadores únicos por PDF: cuando `complete` recibe el prompt,
    # detectamos qué PDF se le pasó y respondemos en consecuencia.
    pdf_markers = {
        doc_a.blob_path: "MARKER_A",
        doc_b.blob_path: "MARKER_B",
        doc_c.blob_path: "MARKER_C",
    }

    def _fake_extract_text(blob_path: str) -> str:
        return f"contenido del PDF con marcador {pdf_markers[blob_path]}"

    monkeypatch.setattr(agent_module, "_extract_text_from_pdf", _fake_extract_text)

    def _fake_complete(prompt: str, **_kwargs) -> LLMResponse:
        # Solo el PDF C (marcador MARKER_C) "encuentra" el valor que
        # coincide con el BOM. Los otros dos PDFs devuelven null.
        if "MARKER_C" in prompt:
            payload = {"value": "match", "confidence": 0.9}
        else:
            payload = {"value": None, "confidence": 0.0}
        return LLMResponse(
            content=json.dumps(payload),
            tokens_in=0,
            tokens_out=0,
            model="fake",
            backend="fake:fake",
        )

    monkeypatch.setattr(agent_module, "complete", _fake_complete)

    plugin = _mk_plugin(["x"])
    bom = {"x": "match"}

    asyncio.run(_drain(extract_fields(sid, db, plugin, bom=bom)))

    # Aserción dura: el campo persistido debe atribuir el PDF C.
    row = db.exec(
        select(ExtractedField).where(
            ExtractedField.session_id == sid, ExtractedField.field_id == "x"
        )
    ).first()
    assert row is not None
    assert row.provenance == "verified"
    assert row.source_document_id == doc_c.id, (
        f"se esperaba doc_c.id={doc_c.id} (PDF que confirmó), se obtuvo "
        f"{row.source_document_id} (probable regresión a primary_doc.id)"
    )
    assert row.value == "match"
