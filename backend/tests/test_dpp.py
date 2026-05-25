"""Tests unidad del módulo app.dpp."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.dpp import (
    build_gs1_uri,
    build_jsonld,
    canonical_payload,
    filter_public_fields,
    generate_qr_png,
    generate_qr_svg,
    sign_payload,
    verify_payload,
)
from app.plugins.loader import load_plugin

BATTERIES = Path(__file__).resolve().parents[2] / "plugins" / "batteries.yaml"


@pytest.fixture
def plugin():
    return load_plugin(BATTERIES)


def test_gs1_uri_batteries_uses_iso15459(plugin) -> None:
    """Reg. UE 2023/1542 Art. 77.3 obliga a ISO/IEC 15459 para baterías."""
    uri = build_gs1_uri(plugin, "abc12345-def6-7890-1234-567890abcdef")
    assert uri.startswith("urn:iso15459:")
    assert "batteries" in uri
    assert uri.endswith("abc12345")


def test_gs1_uri_fallback_to_gs1_digital_link(plugin) -> None:
    """Si cambiásemos el identifier_scheme a gs1, usar Digital Link."""
    fake = plugin.model_copy(update={"identifier_scheme": "gs1_digital_link"})
    uri = build_gs1_uri(fake, "abc12345-rest")
    assert uri.startswith("https://id.gs1.org/01/")
    assert uri.endswith("abc12345")


def test_filter_public_fields_drops_non_public(plugin) -> None:
    """El JSON-LD público no debe contener campos de Sección 2/3/4."""
    # Buscar un campo public y uno no-public en el plugin para verificar.
    public_id = next(f.id for f in plugin.fields if f.access_level == "public")
    non_public_id = next(
        (f.id for f in plugin.fields if f.access_level != "public"), None
    )

    bom = {public_id: "X", "made_up_field": "Y"}
    if non_public_id:
        bom[non_public_id] = "Z"

    out = filter_public_fields(plugin, bom)
    assert public_id in out
    assert "made_up_field" not in out
    if non_public_id:
        assert non_public_id not in out


def test_jsonld_contains_minimum_required_fields(plugin) -> None:
    uri = build_gs1_uri(plugin, "abc12345")
    jsonld = build_jsonld(plugin, uri, {"battery_mass_kg": 25.5}, {"battery_mass_kg": "verified"})
    assert jsonld["@id"] == uri
    assert jsonld["@type"] == "DigitalProductPassport"
    assert jsonld["sector"] == "batteries"
    assert jsonld["regulation"] == "EU 2023/1542"
    assert jsonld["fields"]["battery_mass_kg"]["value"] == 25.5
    assert jsonld["fields"]["battery_mass_kg"]["provenance"] == "verified"


def test_jsonld_default_provenance_is_self_declared(plugin) -> None:
    """Si no se pasa provenance para un campo, asumimos self_declared (conservador)."""
    uri = build_gs1_uri(plugin, "abc12345")
    jsonld = build_jsonld(plugin, uri, {"battery_mass_kg": 25.5})
    assert jsonld["fields"]["battery_mass_kg"]["provenance"] == "self_declared"


def test_jsonld_context_declares_value_and_provenance(plugin) -> None:
    """El @context debe declarar los términos `value` y `provenance` para que
    consumidores JSON-LD puedan expandirlos al namespace local del DPP."""
    uri = build_gs1_uri(plugin, "abc12345")
    jsonld = build_jsonld(plugin, uri, {"battery_mass_kg": 25.5}, {"battery_mass_kg": "verified"})
    assert "value" in jsonld["@context"]
    assert "provenance" in jsonld["@context"]


def test_sign_then_verify_roundtrip() -> None:
    from nacl.signing import SigningKey

    key = SigningKey.generate()
    payload = canonical_payload({"foo": "bar", "n": 1})
    signed = sign_payload(key, payload)
    assert verify_payload(signed.public_key_b64, payload, signed.signature_b64) is True


def test_verify_fails_on_tampered_payload() -> None:
    from nacl.signing import SigningKey

    key = SigningKey.generate()
    payload = canonical_payload({"foo": "bar"})
    signed = sign_payload(key, payload)
    tampered = canonical_payload({"foo": "evil"})
    assert verify_payload(signed.public_key_b64, tampered, signed.signature_b64) is False


def test_canonical_payload_is_deterministic() -> None:
    """Mismo dict en distinto orden → mismos bytes."""
    a = canonical_payload({"x": 1, "y": 2})
    b = canonical_payload({"y": 2, "x": 1})
    assert a == b


def test_qr_png_has_png_header() -> None:
    data = generate_qr_png("urn:iso15459:batteries:abc12345")
    assert data[:4] == b"\x89PNG"


def test_qr_svg_has_xml_header() -> None:
    data = generate_qr_svg("urn:iso15459:batteries:abc12345")
    assert data.startswith(b"<?xml")
    assert b"<svg" in data


def test_generate_dpp_under_2s_for_50_materials_bom(plugin) -> None:
    """F5-01 CA #3 — la generación del JSON-LD debe ser <2s con un BOM
    de hasta 50 materiales. Medimos `build_jsonld` (paso determinista) sobre
    un repeater `critical_raw_materials` poblado con 50 entradas.
    """
    import time

    materials = [
        {"name": f"material_{i}", "share_pct": 0.5, "source": "EU"}
        for i in range(50)
    ]
    public_fields = {
        "battery_mass_kg": 25.5,
        "critical_raw_materials": materials,
    }
    provenance = dict.fromkeys(public_fields, "self_declared")
    uri = build_gs1_uri(plugin, "abc12345")

    t0 = time.perf_counter()
    jsonld = build_jsonld(plugin, uri, public_fields, provenance)
    elapsed = time.perf_counter() - t0

    assert elapsed < 2.0, f"generación tardó {elapsed:.3f}s (>2s)"
    assert len(jsonld["fields"]["critical_raw_materials"]["value"]) == 50
