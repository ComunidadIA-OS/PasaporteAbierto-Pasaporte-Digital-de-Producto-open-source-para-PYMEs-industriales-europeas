"""Tests del endpoint POST /sessions/{id}/dpp + endpoint público /dpp/{slug}."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import select

from app.db.session import get_session
from app.dpp import canonical_payload, verify_payload
from app.models.audit_log import AuditLogEntry
from app.models.extracted_fields import ExtractedField
from app.plugins.loader import load_plugin

DESCRIPTION = "Batería industrial recargable Li-ion 5 kWh para almacenamiento residencial"
BATTERIES = Path(__file__).resolve().parents[2] / "plugins" / "batteries.yaml"


def _fill_all_required(client: TestClient, session_id: str) -> None:
    """Rellena directamente en BD todos los required del plugin de baterías
    con valores fake aceptados por el verifier. Hacerlo via PUT requeriría
    enviar 47 campos correctos en un solo request; en BD es más simple."""
    plugin = load_plugin(BATTERIES)
    db = next(client.app.dependency_overrides[get_session]())  # type: ignore[arg-type]
    try:
        for field in plugin.fields:
            if not field.required:
                continue
            if field.type == "enum":
                value = (field.enum_values or ["x"])[0]
            elif field.type == "number":
                value = "10.0"
            elif field.type == "integer":
                value = "1"
            elif field.type == "boolean":
                value = "true"
            elif field.type == "repeater":
                value = json.dumps(["item1"])
            else:
                value = "fake-value"
            db.add(
                ExtractedField(
                    session_id=session_id,
                    field_id=field.id,
                    value=value,
                    provenance="self_declared",
                    confidence=1.0,
                )
            )
        db.commit()
    finally:
        db.close()


def _classified_session(client: TestClient) -> str:
    sid = client.post("/api/v1/sessions", json={"description": DESCRIPTION}).json()["session_id"]
    client.post(
        f"/api/v1/sessions/{sid}/classify/override",
        json={"sector": "batteries", "plugin": "batteries", "reason": "test setup"},
    )
    return sid


# ─── POST /dpp ───────────────────────────────────────────────────────────────


def test_publish_blocked_without_can_publish(client: TestClient) -> None:
    sid = _classified_session(client)
    # Sin BOM → can_publish=False → 409
    r = client.post(f"/api/v1/sessions/{sid}/dpp")
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert detail["error"] == "cannot_publish"
    assert detail["missing_count"] > 0


def test_publish_happy_path_writes_dpp_and_audit(client: TestClient) -> None:
    sid = _classified_session(client)
    _fill_all_required(client, sid)

    r = client.post(f"/api/v1/sessions/{sid}/dpp")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["gs1_uri"].startswith("urn:iso15459:batteries:")
    assert body["signed"] is True
    # public_url es absoluta (default DPP_PUBLIC_BASE_URL=http://localhost:8000)
    # — debe ser navegable, no un URN sin esquema HTTP, porque es lo que
    # imprimimos en el QR del producto.
    assert body["public_url"].startswith("http")
    assert "/dpp/" in body["public_url"]
    assert body["jsonld_url"] == body["public_url"]
    assert body["qr_png_url"].endswith(".png")
    assert body["qr_svg_url"].endswith(".svg")

    db = next(client.app.dependency_overrides[get_session]())  # type: ignore[arg-type]
    try:
        # Audit log tiene entry de publish.
        audit_entries = db.exec(
            select(AuditLogEntry).where(AuditLogEntry.operation == "publish")
        ).all()
        assert len(audit_entries) == 1
        payload = audit_entries[0].payload or {}
        assert payload["gs1_uri"] == body["gs1_uri"]
        assert "jsonld_sha256" in payload
    finally:
        db.close()


def test_publish_is_idempotent_blocks_re_publication(client: TestClient) -> None:
    sid = _classified_session(client)
    _fill_all_required(client, sid)

    first = client.post(f"/api/v1/sessions/{sid}/dpp")
    assert first.status_code == 200

    again = client.post(f"/api/v1/sessions/{sid}/dpp")
    assert again.status_code == 409
    assert again.json()["detail"] == "dpp_already_published"


def test_publish_jsonld_only_contains_public_fields(client: TestClient) -> None:
    """El JSON-LD persistido no debe incluir campos de Sección 2/3/4."""
    sid = _classified_session(client)
    _fill_all_required(client, sid)
    client.post(f"/api/v1/sessions/{sid}/dpp")

    plugin = load_plugin(BATTERIES)
    non_public_ids = {f.id for f in plugin.fields if f.access_level != "public"}

    # Leer el JSON-LD del endpoint público.
    slug = sid.split("-", 1)[0]
    r = client.get(f"/dpp/{slug}", headers={"Accept": "application/ld+json"})
    assert r.status_code == 200
    fields = r.json()["fields"]
    for fid in fields:
        assert fid not in non_public_ids


def test_publish_signature_verifies_correctly(client: TestClient) -> None:
    """Roundtrip: la firma persistida valida contra el JSON-LD persistido."""
    sid = _classified_session(client)
    _fill_all_required(client, sid)
    client.post(f"/api/v1/sessions/{sid}/dpp")

    slug = sid.split("-", 1)[0]
    r = client.get(f"/dpp/{slug}", headers={"Accept": "application/ld+json"})
    assert r.status_code == 200
    jsonld = r.json()
    sig = r.headers["X-Signature"]
    pub = r.headers["X-Public-Key"]

    assert verify_payload(pub, canonical_payload(jsonld), sig) is True


# ─── /api/v1/sessions/{id}/dpp/qr.{png,svg} ──────────────────────────────────


def test_qr_png_endpoint_returns_image(client: TestClient) -> None:
    sid = _classified_session(client)
    _fill_all_required(client, sid)
    client.post(f"/api/v1/sessions/{sid}/dpp")

    r = client.get(f"/api/v1/sessions/{sid}/dpp/qr.png")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content[:4] == b"\x89PNG"


def test_qr_svg_endpoint_returns_svg(client: TestClient) -> None:
    sid = _classified_session(client)
    _fill_all_required(client, sid)
    client.post(f"/api/v1/sessions/{sid}/dpp")

    r = client.get(f"/api/v1/sessions/{sid}/dpp/qr.svg")
    assert r.status_code == 200
    assert "svg" in r.headers["content-type"]
    assert b"<svg" in r.content


def test_qr_returns_404_before_publish(client: TestClient) -> None:
    sid = _classified_session(client)
    r = client.get(f"/api/v1/sessions/{sid}/dpp/qr.png")
    assert r.status_code == 404


# ─── GET /sessions/{id}/dpp (rehidratación al reentrar en un finalizado) ─────


def test_get_dpp_returns_same_contract_as_post(client: TestClient) -> None:
    """Tras publicar, GET /dpp devuelve exactamente el mismo body que el POST.
    Es lo que permite al frontend rehidratar QR + URL pública al reentrar en un
    DPP finalizado sin re-publicar (POST sería 409)."""
    sid = _classified_session(client)
    _fill_all_required(client, sid)
    posted = client.post(f"/api/v1/sessions/{sid}/dpp")
    assert posted.status_code == 200

    r = client.get(f"/api/v1/sessions/{sid}/dpp")
    assert r.status_code == 200, r.text
    assert r.json() == posted.json()


def test_get_dpp_404_before_publish(client: TestClient) -> None:
    """Sin DPP publicado todavía → 404 (el frontend se queda en borrador)."""
    sid = _classified_session(client)
    _fill_all_required(client, sid)
    r = client.get(f"/api/v1/sessions/{sid}/dpp")
    assert r.status_code == 404


def test_get_dpp_infers_unsigned_from_row(client: TestClient) -> None:
    """`signed` se infiere de si la fila guardó firma: un DPP publicado con
    sign=False se rehidrata como signed=False."""
    sid = _classified_session(client)
    _fill_all_required(client, sid)
    client.post(f"/api/v1/sessions/{sid}/dpp", json={"sign": False})

    r = client.get(f"/api/v1/sessions/{sid}/dpp")
    assert r.status_code == 200
    assert r.json()["signed"] is False


# ─── GET /dpp/{slug} (público) ───────────────────────────────────────────────


def test_public_dpp_returns_jsonld_by_default(client: TestClient) -> None:
    sid = _classified_session(client)
    _fill_all_required(client, sid)
    client.post(f"/api/v1/sessions/{sid}/dpp")

    slug = sid.split("-", 1)[0]
    r = client.get(f"/dpp/{slug}")  # sin Accept explícito
    assert r.status_code == 200
    assert "application/ld+json" in r.headers["content-type"]
    body = r.json()
    assert body["@type"] == "DigitalProductPassport"
    assert "X-Signature" in r.headers


def test_public_dpp_returns_html_when_requested(client: TestClient) -> None:
    sid = _classified_session(client)
    _fill_all_required(client, sid)
    client.post(f"/api/v1/sessions/{sid}/dpp")

    slug = sid.split("-", 1)[0]
    r = client.get(f"/dpp/{slug}", headers={"Accept": "text/html"})
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert b"<!doctype html>" in r.content
    assert b"Pasaporte Digital de Producto" in r.content


def test_public_dpp_404_for_unknown_slug(client: TestClient) -> None:
    r = client.get("/dpp/no-existe-este-slug-x")
    assert r.status_code == 404


# ─── F5-03 CA #1/#2 · content negotiation con q-values (RFC 7231 §5.3.2) ─────


def test_prefers_html_unit_cases() -> None:
    """Unit tests del helper `_prefers_html`: cubrimos los edge cases del
    parseo RFC 7231 sin levantar la app (rápidos y deterministas)."""
    from app.api.public_dpp import _prefers_html

    # Solo JSON-LD → JSON-LD (False).
    assert _prefers_html("application/ld+json") is False
    # Solo HTML → HTML (True).
    assert _prefers_html("text/html") is True
    # Wildcard puro → JSON-LD (default seguro, no asumimos preferencia humana).
    assert _prefers_html("*/*") is False
    # Header de navegador típico (Firefox/Chrome) → HTML.
    assert (
        _prefers_html(
            "text/html,application/xhtml+xml,application/xml;q=0.9," "image/webp,*/*;q=0.8"
        )
        is True
    )
    # Bug fix: HTML degradado a q=0.5 mientras JSON-LD pide q=1.0 → JSON-LD.
    assert _prefers_html("text/html;q=0.5, application/ld+json;q=1.0") is False
    # Empate explícito q=1.0/q=1.0 → gana JSON-LD (FUNCIONAL §5: canónico
    # para máquinas; auditores/agregadores son el caso de uso por defecto).
    assert _prefers_html("application/ld+json;q=1.0, text/html;q=1.0") is False
    # q=0 significa "no acepto este tipo" → JSON-LD aunque text/html aparezca.
    assert _prefers_html("text/html;q=0") is False
    # Header vacío → JSON-LD (default seguro para curl/máquinas).
    assert _prefers_html("") is False
    # Espacios extras y mayúsculas en `Q=` deben tolerarse.
    assert _prefers_html("text/html ; Q=0.9 , application/ld+json ; q=0.5") is True
    # Media-range malformado en q (no parseable) → q=1.0 según RFC 7231.
    assert _prefers_html("text/html;q=notanumber") is True


def test_public_dpp_respects_q_values_prefers_jsonld(client: TestClient) -> None:
    """F5-03 CA #1: un cliente con `text/html;q=0.5, application/ld+json;q=1.0`
    debe recibir JSON-LD. Antes del fix, recibía HTML porque el parseo
    descartaba los q-values."""
    sid = _classified_session(client)
    _fill_all_required(client, sid)
    client.post(f"/api/v1/sessions/{sid}/dpp")

    slug = sid.split("-", 1)[0]
    r = client.get(
        f"/dpp/{slug}",
        headers={"Accept": "text/html;q=0.5, application/ld+json;q=1.0"},
    )
    assert r.status_code == 200
    assert "application/ld+json" in r.headers["content-type"]
    assert r.json()["@type"] == "DigitalProductPassport"


def test_public_dpp_browser_accept_header_returns_html(client: TestClient) -> None:
    """F5-03 CA #2: el header Accept típico de Firefox/Chrome (text/html con
    q implícito 1.0) debe recibir la página HTML."""
    sid = _classified_session(client)
    _fill_all_required(client, sid)
    client.post(f"/api/v1/sessions/{sid}/dpp")

    slug = sid.split("-", 1)[0]
    r = client.get(
        f"/dpp/{slug}",
        headers={
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9," "image/webp,*/*;q=0.8"
            )
        },
    )
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert b"<!doctype html>" in r.content


def test_public_dpp_html_q_zero_falls_back_to_jsonld(client: TestClient) -> None:
    """`text/html;q=0` significa "no acepto HTML" → JSON-LD."""
    sid = _classified_session(client)
    _fill_all_required(client, sid)
    client.post(f"/api/v1/sessions/{sid}/dpp")

    slug = sid.split("-", 1)[0]
    r = client.get(f"/dpp/{slug}", headers={"Accept": "text/html;q=0"})
    assert r.status_code == 200
    assert "application/ld+json" in r.headers["content-type"]


def test_public_dpp_wildcard_accept_returns_jsonld(client: TestClient) -> None:
    """`Accept: */*` (curl sin -H, agregadores) → JSON-LD canónico."""
    sid = _classified_session(client)
    _fill_all_required(client, sid)
    client.post(f"/api/v1/sessions/{sid}/dpp")

    slug = sid.split("-", 1)[0]
    r = client.get(f"/dpp/{slug}", headers={"Accept": "*/*"})
    assert r.status_code == 200
    assert "application/ld+json" in r.headers["content-type"]


# ─── F5-01 #2 + F5-03 #3 · provenance + badge HTML ───────────────────────────


def _mark_one_field_verified(client: TestClient, session_id: str) -> str:
    """Mutar un campo del BOM a provenance=verified para tener mezcla."""
    plugin = load_plugin(BATTERIES)
    public_required = next(f for f in plugin.fields if f.required and f.access_level == "public")
    db = next(client.app.dependency_overrides[get_session]())  # type: ignore[arg-type]
    try:
        row = db.exec(
            select(ExtractedField).where(
                ExtractedField.session_id == session_id,
                ExtractedField.field_id == public_required.id,
            )
        ).one()
        row.provenance = "verified"
        db.add(row)
        db.commit()
    finally:
        db.close()
    return public_required.id


def test_public_dpp_jsonld_exposes_provenance_per_field(client: TestClient) -> None:
    """F5-01 CA #2: cada campo del JSON-LD público expone su provenance."""
    sid = _classified_session(client)
    _fill_all_required(client, sid)
    verified_id = _mark_one_field_verified(client, sid)
    client.post(f"/api/v1/sessions/{sid}/dpp")

    slug = sid.split("-", 1)[0]
    r = client.get(f"/dpp/{slug}", headers={"Accept": "application/ld+json"})
    assert r.status_code == 200
    fields = r.json()["fields"]
    assert isinstance(fields, dict) and fields, "JSON-LD debe tener campos públicos"
    for _fid, payload in fields.items():
        assert isinstance(payload, dict)
        assert "value" in payload
        assert payload["provenance"] in {"verified", "self_declared"}
    assert fields[verified_id]["provenance"] == "verified"


# ─── F5-04 #3 · firma opt-in por sesión ──────────────────────────────────────


def test_publish_unsigned_when_sign_false(client: TestClient) -> None:
    """`sign=False` → JSON-LD persistido sin firma; respuesta `signed=False`."""
    sid = _classified_session(client)
    _fill_all_required(client, sid)

    r = client.post(f"/api/v1/sessions/{sid}/dpp", json={"sign": False})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["signed"] is False

    slug = sid.split("-", 1)[0]
    pub = client.get(f"/dpp/{slug}", headers={"Accept": "application/ld+json"})
    assert pub.status_code == 200
    # Sin firma: no se inyectan headers vacíos que confundan al verificador.
    assert "X-Signature" not in pub.headers
    assert "X-Public-Key" not in pub.headers


def test_publish_signed_by_default(client: TestClient) -> None:
    """Sin body → firma activa por defecto (compat con clientes anteriores)."""
    sid = _classified_session(client)
    _fill_all_required(client, sid)

    r = client.post(f"/api/v1/sessions/{sid}/dpp")
    assert r.status_code == 200
    assert r.json()["signed"] is True


def test_audit_log_records_signed_flag(client: TestClient) -> None:
    """El audit log refleja si la publicación se firmó (trazabilidad)."""
    sid = _classified_session(client)
    _fill_all_required(client, sid)
    client.post(f"/api/v1/sessions/{sid}/dpp", json={"sign": False})

    db = next(client.app.dependency_overrides[get_session]())  # type: ignore[arg-type]
    try:
        entry = db.exec(select(AuditLogEntry).where(AuditLogEntry.operation == "publish")).one()
        assert (entry.payload or {}).get("signed") is False
    finally:
        db.close()


def test_public_dpp_html_renders_verified_and_self_declared_badges(client: TestClient) -> None:
    """F5-03 CA #3: la página HTML diferencia visualmente verified vs self_declared."""
    sid = _classified_session(client)
    _fill_all_required(client, sid)
    _mark_one_field_verified(client, sid)
    client.post(f"/api/v1/sessions/{sid}/dpp")

    slug = sid.split("-", 1)[0]
    r = client.get(f"/dpp/{slug}", headers={"Accept": "text/html"})
    assert r.status_code == 200
    body = r.content.decode()
    # Ambos badges deben aparecer porque mezclamos provenance.
    assert 'class="badge verified"' in body
    assert 'class="badge self_declared"' in body
