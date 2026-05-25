"""Generación y firma del DPP (paso 7 + endpoint público).

Pipeline determinista:
  - `build_gs1_uri(plugin, session_id)` → identificador único según
    `plugin.identifier_scheme` (ISO/IEC 15459 obligatorio para baterías
    por Art. 77.3 de Reg. UE 2023/1542; GS1 Digital Link default).
  - `build_jsonld(plugin, session, fields)` → JSON-LD CIRPASS-2 Core con
    solo campos `access_level=public` (las otras 3 secciones del Annex
    XIII tienen access control aparte).
  - `sign_payload(key, payload)` → firma Ed25519 (PyNaCl) → (sig, pub).
  - `generate_qr_png/svg(uri)` → QR con `segno`.

Clave del fabricante: una `SigningKey` Ed25519 persistida en
`backend/data/keys/manufacturer.ed25519` (generada al primer uso, 0600).
En producción real cada fabricante tendría su HSM/keychain — aquí es
suficiente para el hackathon y para que la verificación funcione.
"""

from __future__ import annotations

import base64
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import segno
from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey

from app.plugins.loader import Plugin

# `backend/src/app/dpp/__init__.py` → parents[3] = backend/
KEYS_DIR: Path = Path(__file__).resolve().parents[3] / "data" / "keys"
KEY_FILE: Path = KEYS_DIR / "manufacturer.ed25519"


# ─── claves ──────────────────────────────────────────────────────────────────


def get_or_create_keypair() -> SigningKey:
    """Devuelve la clave de firma del fabricante, generándola si no existe.

    La semilla (32 bytes) se persiste con permisos 0600. Eso permite que
    el endpoint público verifique firmas pasadas tras un restart.
    """
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    if KEY_FILE.exists():
        return SigningKey(KEY_FILE.read_bytes())
    key = SigningKey.generate()
    KEY_FILE.write_bytes(bytes(key))
    KEY_FILE.chmod(0o600)
    return key


# ─── identificador y JSON-LD ─────────────────────────────────────────────────


def build_gs1_uri(plugin: Plugin, session_id: str) -> str:
    """Construye el `gs1_uri` (key de `published_dpps`) según el plugin.

    - Para baterías (identifier_scheme=iso_iec_15459) usamos un URN
      compacto siguiendo la convención de ISO/IEC 15459.
    - Para el resto, fallback a GS1 Digital Link (https://id.gs1.org/...).
    """
    short = session_id.split("-", 1)[0]
    if plugin.identifier_scheme == "iso_iec_15459":
        return f"urn:iso15459:{plugin.name}:{short}"
    return f"https://id.gs1.org/01/09506000134352/21/{short}"


def filter_public_fields(plugin: Plugin, all_fields: dict[str, Any]) -> dict[str, Any]:
    """Devuelve solo los campos con `access_level=public` (Annex XIII Sección 1)."""
    public_ids = {f.id for f in plugin.fields if f.access_level == "public"}
    return {fid: v for fid, v in all_fields.items() if fid in public_ids}


def build_jsonld(plugin: Plugin, gs1_uri: str, public_fields: dict[str, Any]) -> dict:
    """Construye el documento JSON-LD del DPP con sólo campos público."""
    return {
        "@context": {
            "@vocab": "https://cirpass.eu/dpp/v1/",
            "dpp": "https://cirpass.eu/dpp/v1/",
            "regulation": "https://cirpass.eu/dpp/v1/regulation",
            "sector": "https://cirpass.eu/dpp/v1/sector",
        },
        "@type": "DigitalProductPassport",
        "@id": gs1_uri,
        "sector": plugin.name,
        "regulation": plugin.regulation,
        "identifier_scheme": plugin.identifier_scheme,
        "fields": public_fields,
    }


def canonical_payload(jsonld: dict) -> bytes:
    """Bytes deterministas del JSON-LD para firmar/verificar."""
    return json.dumps(jsonld, sort_keys=True, separators=(",", ":"), default=str).encode()


# ─── firma Ed25519 ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SignedPayload:
    signature_b64: str
    public_key_b64: str


def sign_payload(key: SigningKey, payload: bytes) -> SignedPayload:
    sig = key.sign(payload).signature
    return SignedPayload(
        signature_b64=base64.b64encode(sig).decode(),
        public_key_b64=base64.b64encode(bytes(key.verify_key)).decode(),
    )


def verify_payload(public_key_b64: str, payload: bytes, signature_b64: str) -> bool:
    """Verifica que la firma del payload es válida bajo la clave pública dada."""
    try:
        vk = VerifyKey(base64.b64decode(public_key_b64))
        vk.verify(payload, base64.b64decode(signature_b64))
        return True
    except (BadSignatureError, ValueError):
        return False


# ─── QR ──────────────────────────────────────────────────────────────────────


def generate_qr_png(uri: str, scale: int = 5) -> bytes:
    """QR PNG con corrección H (alta) — apto para impresión sobre producto."""
    buf = io.BytesIO()
    segno.make(uri, error="h").save(buf, kind="png", scale=scale)
    return buf.getvalue()


def generate_qr_svg(uri: str, scale: int = 5) -> bytes:
    buf = io.BytesIO()
    segno.make(uri, error="h").save(buf, kind="svg", scale=scale)
    return buf.getvalue()


__all__ = [
    "SignedPayload",
    "build_gs1_uri",
    "build_jsonld",
    "canonical_payload",
    "filter_public_fields",
    "generate_qr_png",
    "generate_qr_svg",
    "get_or_create_keypair",
    "sign_payload",
    "verify_payload",
]
