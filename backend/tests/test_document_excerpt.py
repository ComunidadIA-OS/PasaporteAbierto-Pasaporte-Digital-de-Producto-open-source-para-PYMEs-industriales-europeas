"""Tests del endpoint GET /sessions/{id}/documents/{doc_id}/excerpt (F4-05 #2).

Verifica:
  - Match exitoso devuelve fragmento con contexto + número de página.
  - Match fallido devuelve pantallazo del inicio con match_found=False.
  - 404 si sesión/documento/campo no existe.
  - 409 si el documento no pertenece a la sesión.

No usa PDFs reales: monkeypatchea pdfplumber.open con un stub que devuelve
texto controlado por test.
"""

from __future__ import annotations

from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from app.api.v1 import wizard as wizard_module
from app.db.session import get_session
from app.models.documents import Document
from app.models.extracted_fields import ExtractedField


class _FakePage:
    def __init__(self, text: str) -> None:
        self._text = text

    def extract_text(self) -> str:
        return self._text


class _FakePdf:
    def __init__(self, pages_text: list[str]) -> None:
        self.pages = [_FakePage(t) for t in pages_text]

    def __enter__(self) -> "_FakePdf":
        return self

    def __exit__(self, *args: object) -> None:
        return None


@pytest.fixture
def _stub_pdfplumber(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Devuelve una lista mutable de páginas; tests añaden el texto que esperan leer."""
    pages: list[list[str]] = [["página 1: contenido por defecto"]]

    @contextmanager
    def _fake_open(_blob_path: str):
        yield _FakePdf(pages[0])

    import pdfplumber

    monkeypatch.setattr(pdfplumber, "open", _fake_open)
    return pages


def _session_with_doc_and_field(
    client: TestClient, value: str, set_pages: list[list[str]], page_text: str
) -> tuple[str, int]:
    r = client.post(
        "/api/v1/sessions",
        json={"description": "Producto de prueba para excerpt en PDF fuente del Recolector."},
    )
    sid: str = r.json()["session_id"]

    # Insertar Document y ExtractedField directamente vía la sesión de BD del test.
    db_gen = client.app.dependency_overrides[get_session]()
    db = next(db_gen)
    doc_id: int
    try:
        doc = Document(
            session_id=sid,
            doc_type="datasheet",
            blob_path="/tmp/fake-not-used.pdf",
            sha256="0" * 64,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        # Capturar id ANTES de cerrar la sesión para evitar DetachedInstanceError.
        doc_id = doc.id  # type: ignore[assignment]
        ef = ExtractedField(
            session_id=sid,
            field_id="rated_capacity_ah",
            value=value,
            provenance="verified",
            confidence=0.95,
            source_document_id=doc_id,
        )
        db.add(ef)
        db.commit()
    finally:
        db.close()

    set_pages[0] = [page_text]
    return sid, doc_id


def test_excerpt_match_found_returns_context_and_page(
    client: TestClient, _stub_pdfplumber: list[list[str]]
) -> None:
    page_text = (
        "Pre-context que debería aparecer antes del valor. " * 5
        + "Capacidad nominal: 100 Ah a 25°C. "
        + "Post-context que aparece después. " * 5
    )
    sid, doc_id = _session_with_doc_and_field(client, "100", _stub_pdfplumber, page_text)

    r = client.get(
        f"/api/v1/sessions/{sid}/documents/{doc_id}/excerpt?field_id=rated_capacity_ah"
    )
    assert r.status_code == 200
    body = r.json()
    assert body["match_found"] is True
    assert body["page_number"] == 1
    assert body["value"] == "100"
    assert "100" in body["excerpt"]
    assert "Capacidad nominal" in body["excerpt"]


def test_excerpt_match_not_found_returns_first_page_snippet(
    client: TestClient, _stub_pdfplumber: list[list[str]]
) -> None:
    page_text = "Documento sin el valor buscado. Solo texto genérico aquí."
    sid, doc_id = _session_with_doc_and_field(
        client, "valor_inventado_no_presente", _stub_pdfplumber, page_text
    )

    r = client.get(
        f"/api/v1/sessions/{sid}/documents/{doc_id}/excerpt?field_id=rated_capacity_ah"
    )
    assert r.status_code == 200
    body = r.json()
    assert body["match_found"] is False
    assert body["page_number"] is None
    assert "Documento sin el valor buscado" in body["excerpt"]


def test_excerpt_404_on_unknown_document(
    client: TestClient, _stub_pdfplumber: list[list[str]]
) -> None:
    r = client.post(
        "/api/v1/sessions",
        json={"description": "Sesión sin documentos para forzar 404 del endpoint excerpt."},
    )
    sid = r.json()["session_id"]

    r = client.get(
        f"/api/v1/sessions/{sid}/documents/99999/excerpt?field_id=anything"
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "document_not_found"


def test_excerpt_409_when_document_belongs_to_other_session(
    client: TestClient, _stub_pdfplumber: list[list[str]]
) -> None:
    # Sesión A con un documento
    sid_a, doc_id = _session_with_doc_and_field(
        client, "100", _stub_pdfplumber, "Texto que sí contiene 100 Ah."
    )

    # Sesión B intenta acceder al documento de A → 409
    r = client.post(
        "/api/v1/sessions",
        json={"description": "Segunda sesión que no debería ver el documento de A."},
    )
    sid_b = r.json()["session_id"]

    r = client.get(
        f"/api/v1/sessions/{sid_b}/documents/{doc_id}/excerpt?field_id=rated_capacity_ah"
    )
    assert r.status_code == 409
    assert r.json()["detail"] == "document_not_in_session"
