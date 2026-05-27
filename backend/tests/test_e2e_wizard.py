"""Test E2E del flujo completo del wizard de baterías (FUNCIONAL §10 #7).

Recorre los 7 pasos del wizard + verificación pública del DPP + audit chain.
Mockea Clasificador (LLM + RAG) para no depender de Ollama/Anthropic ni del
corpus indexado. Recolector no se invoca con PDF: se monta una sesión sin
documentos, así fases 1 y 2 del Recolector quedan vacías y la fase 3 cae al
caso "solo BOM → self_declared".

Tickets cubiertos:
    F3-01 clasificador, F3-02 recolector, F3-03 verificador,
    F4-01..03 wizard step orchestration y BOM, F4-06 generación DPP,
    F5-01..04 provenance / JSON-LD / firma / audit hash chain.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

import app.dpp as dpp_module
from app.db.session import get_session
from app.llm.router import LLMResponse
from app.main import app
from app.models import (  # noqa: F401  (registrar metadata)
    audit_log,
    auth,
    chat_messages,
    documents,
    extracted_fields,
    published_dpps,
    sessions,
)
from app.plugins.loader import Plugin, PluginField, load_all_plugins
from app.rag.schema import Result
from tests.conftest import authenticate

# `backend/tests/test_e2e_wizard.py` → parents[2] = repo root
REPO_ROOT: Path = Path(__file__).resolve().parents[2]
PLUGINS_DIR: Path = REPO_ROOT / "plugins"

DESCRIPTION: str = (
    "Batería industrial recargable Li-ion 5 kWh para almacenamiento residencial "
    "de excedentes solares, instalación fija interior."
)


# ─── fixtures locales ────────────────────────────────────────────────────────


@pytest.fixture
def e2e_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """TestClient con BD SQLite efímera y clave Ed25519 redirigida a tmp_path.

    El override de `KEYS_DIR` / `KEY_FILE` evita que el test toque la clave
    persistida en `backend/data/keys/manufacturer.ed25519` (que es la del
    fabricante real, no debería mutarse desde tests).
    """
    db_path = tmp_path / "e2e.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    def _override_get_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    # Aislar la clave Ed25519 en tmp_path — el test no debe tocar la del repo.
    keys_dir = tmp_path / "keys"
    monkeypatch.setattr(dpp_module, "KEYS_DIR", keys_dir)
    monkeypatch.setattr(dpp_module, "KEY_FILE", keys_dir / "manufacturer.ed25519")

    # Defensividad: si en un futuro alguien dispara el Recolector con docs,
    # no queremos llamadas LLM reales. El happy path no usa PDFs así que
    # `complete` no debería invocarse — si se invoca, falla ruidosamente.
    def _no_llm_in_collector(*_args: Any, **_kwargs: Any) -> LLMResponse:
        pytest.fail(
            "El Recolector no debería llamar al LLM sin PDFs subidos. "
            "Si esta aserción salta, algo en el pipeline disparó LLM en vacío."
        )

    monkeypatch.setattr("app.collector.agent.complete", _no_llm_in_collector)

    app.dependency_overrides[get_session] = _override_get_session
    try:
        test_client = TestClient(app)
        # El wizard exige login desde ADR-0004; autenticamos para recorrer E2E.
        authenticate(test_client)
        yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def batteries_plugin() -> Plugin:
    """Carga el plugin de baterías desde el YAML real del repo."""
    plugins = load_all_plugins(PLUGINS_DIR)
    assert "batteries" in plugins, "el plugin batteries debe estar instalado"
    return plugins["batteries"]


@pytest.fixture
def mock_classifier(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mockea el LLM + RAG del Clasificador para no depender de Ollama/Chroma.

    Sin esto:
      - `search_corpus` levanta o devuelve [] → confidence se capa a ≤0.6
        y `requires_review=True`, rompiendo la aserción del paso 2.
      - `complete` intenta hablar con el backend LLM configurado, que en CI
        no existe.
    """
    fake_fragment = Result(
        cita="Reglamento UE 2023/1542, Art. 77.3",
        texto=(
            "El pasaporte de batería se hará accesible mediante un identificador "
            "único conforme a la norma ISO/IEC 15459."
        ),
        score=0.9,
        fuente_url=("https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX%3A32023R1542"),
        reglamento="UE 2023/1542",
        articulo="77",
        apartado="3",
        idioma="es",
    )

    monkeypatch.setattr(
        "app.classifier.agent.search_corpus",
        lambda *_args, **_kwargs: [fake_fragment],
    )

    def _fake_complete(*_args: Any, **_kwargs: Any) -> LLMResponse:
        payload = {
            "sector": "batteries",
            "confidence": 0.9,
            "fragment_index": 0,
            "reasoning": "test e2e",
        }
        return LLMResponse(
            content=json.dumps(payload),
            tokens_in=10,
            tokens_out=20,
            model="fake",
            backend="fake:fake",
        )

    monkeypatch.setattr("app.classifier.agent.complete", _fake_complete)


# ─── helpers ─────────────────────────────────────────────────────────────────


def _value_for_required_field(field: PluginField) -> Any:
    """Genera un valor válido por tipo, aceptable por `_validate_field_value`."""
    if field.type == "string":
        return f"valor-{field.id}"
    if field.type == "enum":
        allowed = field.enum_values or []
        assert allowed, f"campo enum {field.id} sin enum_values"
        return allowed[0]
    if field.type == "number":
        return 1.0
    if field.type == "integer":
        return 1
    if field.type == "boolean":
        return True
    if field.type == "repeater":
        # `[]` es una lista válida y el verifier la considera presente
        # (`json.loads("[]") == []`, isinstance(list) → True).
        return []
    raise AssertionError(f"tipo desconocido para {field.id}: {field.type}")


def _bom_payload_for(plugin: Plugin) -> dict[str, Any]:
    """Construye el payload completo con TODOS los `required=True` del plugin."""
    return {f.id: _value_for_required_field(f) for f in plugin.fields if f.required}


def _drain_sse(content: bytes) -> list[dict[str, Any]]:
    """Parsea los eventos SSE de la respuesta del /extract."""
    events: list[dict[str, Any]] = []
    for line in content.decode().splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: ") :]))
    return events


# ─── Test 1: happy path completo ─────────────────────────────────────────────


def test_full_wizard_flow_batteries(
    e2e_client: TestClient,
    batteries_plugin: Plugin,
    mock_classifier: None,
) -> None:
    """Recorre los 7 pasos del wizard + endpoint público + audit chain.

    Cubre FUNCIONAL §10 criterio 7 (tests E2E del flujo completo).
    """
    client = e2e_client

    # ── Paso 1: crear sesión ────────────────────────────────────────────────
    r = client.post("/api/v1/sessions", json={"description": DESCRIPTION})
    assert r.status_code == 201, r.text
    sid: str = r.json()["session_id"]
    # UUID v4 → 36 chars con guiones, no vacío.
    assert isinstance(sid, str) and len(sid) == 36 and sid.count("-") == 4

    # ── Paso 2: clasificación ───────────────────────────────────────────────
    r = client.post(f"/api/v1/sessions/{sid}/classify")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["sector"] == "batteries"
    assert body["confidence"] >= 0.7
    assert body["requires_review"] is False
    assert body["citation"] is not None
    assert "2023/1542" in body["citation"]["regulation"]

    # ── Paso 3: BOM con todos los required del plugin ───────────────────────
    bom_payload = _bom_payload_for(batteries_plugin)
    # Sanidad mínima: el plugin de baterías declara ≥25 campos required.
    assert len(bom_payload) >= 25, (
        f"el plugin batteries debe tener ≥25 required, se han generado " f"{len(bom_payload)}"
    )
    r = client.put(f"/api/v1/sessions/{sid}/bom", json={"fields": bom_payload})
    assert r.status_code == 200, r.text
    bom_body = r.json()
    assert bom_body["accepted"] is True, f"errores del PUT BOM: {bom_body['errors']}"
    assert bom_body["errors"] == [], (
        f"PUT con todos los required no debería emitir errores: " f"{bom_body['errors']}"
    )

    # ── Paso 4: documentos (skip) ───────────────────────────────────────────
    # El test no sube PDFs: el BOM completo basta para que el Verificador
    # apruebe (verifier solo valida campos required, no required_documents).

    # ── Paso 5: extracción (Recolector sobre 0 PDFs) ───────────────────────
    r = client.post(f"/api/v1/sessions/{sid}/extract")
    assert r.status_code == 200, r.text
    events = _drain_sse(r.content)
    # Evento inicial de progreso (processed=0) y evento final `done`.
    assert any(
        e.get("event") == "progress" and e.get("processed") == 0 for e in events
    ), f"no se emitió progreso inicial: {events[:3]}"
    done_events = [e for e in events if e.get("event") == "done"]
    assert len(done_events) == 1, f"se esperaba un único `done`, got {done_events}"
    done = done_events[0]
    # Sin PDFs, ningún campo puede ser `verified`; todos los que tenían BOM
    # caen a `self_declared` (caso 3 del agregador). Los `required` sin BOM
    # serían `required_pending`, pero hemos rellenado TODOS los required.
    assert (
        done["fields_verified"] == 0
    ), f"sin PDFs no puede haber verified; got {done['fields_verified']}"
    assert done["fields_self_declared"] >= len(bom_payload), (
        f"todos los required del BOM deben quedar self_declared; "
        f"got {done['fields_self_declared']} self_declared con "
        f"{len(bom_payload)} required enviados"
    )

    # ── Paso 6: verificación → can_publish=True ────────────────────────────
    r = client.get(f"/api/v1/sessions/{sid}/verify")
    assert r.status_code == 200, r.text
    verify_body = r.json()
    assert (
        verify_body["can_publish"] is True
    ), f"no se puede publicar: missing={verify_body['missing_fields']}"
    assert verify_body["completeness"] == 1.0
    assert verify_body["missing_fields"] == []

    # ── Paso 7: generación y publicación del DPP ───────────────────────────
    r = client.post(f"/api/v1/sessions/{sid}/dpp")
    assert r.status_code == 200, r.text
    dpp_body = r.json()
    gs1_uri: str = dpp_body["gs1_uri"]
    assert gs1_uri.startswith(
        "urn:iso15459:batteries:"
    ), f"para baterías esperamos identifier_scheme=iso_iec_15459; got {gs1_uri}"
    assert dpp_body["public_url"].startswith("http")
    assert dpp_body["qr_png_url"].endswith(".png")
    assert dpp_body["qr_svg_url"].endswith(".svg")
    assert dpp_body["signed"] is True

    # ── Verificación pública: JSON-LD ──────────────────────────────────────
    slug = sid.split("-", 1)[0]
    r = client.get(f"/dpp/{slug}", headers={"Accept": "application/ld+json"})
    assert r.status_code == 200, r.text
    jsonld = r.json()
    assert jsonld["@id"] == gs1_uri
    assert jsonld["sector"] == "batteries"
    assert jsonld["fields"], "el DPP público no puede tener `fields` vacío"

    # ── Verificación pública: HTML con badges de provenance ────────────────
    r = client.get(f"/dpp/{slug}", headers={"Accept": "text/html"})
    assert r.status_code == 200
    html_body = r.content.decode()
    assert ("self_declared" in html_body) or (
        "verified" in html_body
    ), "la página HTML debería mostrar al menos un badge de provenance"

    # ── Audit chain: verificable end-to-end ────────────────────────────────
    r = client.get("/api/v1/audit/verify")
    assert r.status_code == 200, r.text
    audit_body = r.json()
    assert audit_body["ok"] is True
    # Publish escribe una entry; classify (sin override) no escribe audit.
    assert (
        audit_body["total_rows"] >= 1
    ), f"se esperaba al menos la entry de publish; got {audit_body}"

    # ── QR endpoints ────────────────────────────────────────────────────────
    r_png = client.get(f"/api/v1/sessions/{sid}/dpp/qr.png")
    assert r_png.status_code == 200
    assert r_png.headers["content-type"] == "image/png"
    assert len(r_png.content) > 0
    assert r_png.content[:4] == b"\x89PNG"

    r_svg = client.get(f"/api/v1/sessions/{sid}/dpp/qr.svg")
    assert r_svg.status_code == 200
    assert "svg" in r_svg.headers["content-type"]
    assert len(r_svg.content) > 0
    assert b"<svg" in r_svg.content


# ─── Test 2: regresión del bloqueo de publicación con BOM incompleto ─────────


def test_cannot_publish_with_incomplete_bom(
    e2e_client: TestClient,
    batteries_plugin: Plugin,
    mock_classifier: None,
) -> None:
    """Si faltan required, verify bloquea y POST /dpp devuelve 409.

    Regresión de la invariante CLAUDE.md: "No se puede emitir un DPP parcial
    conforme. Si falta cualquier campo obligatorio del plugin, la publicación
    queda bloqueada en el paso 6 (Verificador)."
    """
    client = e2e_client

    # Crear + clasificar.
    sid = client.post("/api/v1/sessions", json={"description": DESCRIPTION}).json()["session_id"]
    r = client.post(f"/api/v1/sessions/{sid}/classify")
    assert r.status_code == 200, r.text
    assert r.json()["sector"] == "batteries"

    # PUT BOM con solo 5 required (de los 28 del plugin).
    required_ids = [f for f in batteries_plugin.fields if f.required][:5]
    assert len(required_ids) == 5
    partial = {f.id: _value_for_required_field(f) for f in required_ids}
    r = client.put(f"/api/v1/sessions/{sid}/bom", json={"fields": partial})
    assert r.status_code == 200, r.text

    # Verify dice que NO se puede publicar.
    r = client.get(f"/api/v1/sessions/{sid}/verify")
    assert r.status_code == 200, r.text
    verify_body = r.json()
    assert verify_body["can_publish"] is False
    assert len(verify_body["missing_fields"]) > 0

    # POST /dpp → 409 con error "cannot_publish".
    r = client.post(f"/api/v1/sessions/{sid}/dpp")
    assert r.status_code == 409, r.text
    detail = r.json()["detail"]
    assert detail["error"] == "cannot_publish"
    assert detail["missing_count"] > 0
