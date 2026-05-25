"""Generación y firma del DPP (paso 7 + endpoint público).

Pipeline determinista:
  - `build_gs1_uri(plugin, session_id)` → identificador único según
    `plugin.identifier_scheme` (ISO/IEC 15459 obligatorio para baterías
    por Art. 77.3 de Reg. UE 2023/1542; GS1 Digital Link default).
  - `build_jsonld(plugin, session, fields)` → JSON-LD con vocabulario local
    (perfil interno hasta que CIRPASS publique su `@context` oficial). Solo
    campos `access_level=public`; las otras tres secciones del Annex XIII
    tienen otros canales de acceso.
  - `sign_payload(key, payload)` → firma Ed25519 (PyNaCl) → (sig, pub).
  - `generate_qr_png/svg(url)` → QR que apunta al endpoint público local.

Clave del fabricante: una `SigningKey` Ed25519 persistida en
`backend/data/keys/manufacturer.ed25519` (generada al primer uso, 0600).
En producción real cada fabricante tendría su HSM/keychain — aquí es
suficiente para el hackathon y para que la verificación funcione.
"""

from __future__ import annotations

import base64
import contextlib
import io
import json
import os
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

# Namespace local del vocabulario JSON-LD (URN: no se resuelve por HTTP, así
# evitamos prometer un context público que no existe — ver decisión del review).
_DPP_NAMESPACE: str = "urn:pasaporte-abierto:dpp:v1#"


# ─── claves ──────────────────────────────────────────────────────────────────


def get_or_create_keypair() -> SigningKey:
    """Devuelve la clave de firma del fabricante, generándola si no existe.

    Atomicidad: usa `O_CREAT | O_EXCL` para que sólo un proceso/hilo gane la
    creación inicial; cualquier otro que llegue tras el fallo `FileExistsError`
    reusa la clave persistida. Esto evita el race anterior donde dos requests
    concurrentes generaban claves distintas y la última escrita invalidaba
    firmas previas.
    """
    if KEY_FILE.exists():
        return SigningKey(KEY_FILE.read_bytes())
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        # O_EXCL es atómico a nivel filesystem (POSIX y Windows).
        fd = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return SigningKey(KEY_FILE.read_bytes())
    try:
        key = SigningKey.generate()
        os.write(fd, bytes(key))
    finally:
        os.close(fd)
    # chmod tras cerrar el fd: solo aplica en POSIX (Windows lo ignora silenciosamente).
    if os.name != "nt":
        with contextlib.suppress(OSError):
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


def build_jsonld(
    plugin: Plugin,
    gs1_uri: str,
    public_fields: dict[str, Any],
    provenance: dict[str, str] | None = None,
) -> dict:
    """Construye el documento JSON-LD del DPP con sólo campos públicos.

    Cada campo se emite como un sub-objeto `{value, provenance}` para
    cumplir F5-01 CA #2 — el consumidor distingue datos verificados contra
    PDF (`verified`) de los auto-declarados por el fabricante (`self_declared`).
    Si `provenance` no se proporciona o falta una entrada para un `field_id`,
    se asume `self_declared` (la opción más conservadora: el fabricante
    afirma el dato sin respaldo documental).

    El `@context` declara un vocabulario propio bajo un namespace URN local. NO
    pretende ser CIRPASS-2 Core hasta que el consorcio publique su context
    oficial — un URN es válido como identificador en JSON-LD sin necesidad de
    resolver por HTTP, y evita prometer una URL externa inexistente.
    """
    prov_map: dict[str, str] = provenance or {}
    fields_with_prov: dict[str, dict[str, Any]] = {
        fid: {
            "value": v,
            "provenance": prov_map.get(fid, "self_declared"),
        }
        for fid, v in public_fields.items()
    }
    return {
        "@context": {
            "@version": 1.1,
            "dpp": _DPP_NAMESPACE,
            "DigitalProductPassport": "dpp:DigitalProductPassport",
            "sector": "dpp:sector",
            "regulation": "dpp:regulation",
            "identifier_scheme": "dpp:identifierScheme",
            "fields": "dpp:fields",
            "value": "dpp:value",
            "provenance": "dpp:provenance",
        },
        "@type": "DigitalProductPassport",
        "@id": gs1_uri,
        "sector": plugin.name,
        "regulation": plugin.regulation,
        "identifier_scheme": plugin.identifier_scheme,
        "fields": fields_with_prov,
    }


def canonical_payload(jsonld: dict) -> bytes:
    """Bytes deterministas del JSON-LD para firmar/verificar.

    Sin `default=str`: cualquier tipo no serializable lanza `TypeError` antes
    de firmar. Eso impide producir firmas que un verificador externo no pueda
    reproducir tras deserializar el JSON-LD recibido por HTTP.
    """
    return json.dumps(jsonld, sort_keys=True, separators=(",", ":")).encode()


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


# ─── QR y URL pública ────────────────────────────────────────────────────────


def public_dpp_url(slug: str) -> str:
    """URL pública absoluta del DPP para imprimir en el QR.

    Se construye a partir de `DPP_PUBLIC_BASE_URL` (env). Por defecto apunta al
    backend local; en producción el operador la configura al dominio expuesto.
    El QR del producto debe resolver a `GET /dpp/{slug}` del propio backend,
    no al identificador `gs1_uri` (URN sin resolución HTTP o redirector externo).
    """
    base = os.environ.get("DPP_PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
    return f"{base}/dpp/{slug}"


def generate_qr_png(url: str, scale: int = 5) -> bytes:
    """QR PNG con corrección H (alta) — apto para impresión sobre producto.

    `url` debe ser la URL pública absoluta del DPP (`public_dpp_url(slug)`),
    no el `gs1_uri` (que sería un URN no navegable o un redirect externo).
    """
    buf = io.BytesIO()
    segno.make(url, error="h").save(buf, kind="png", scale=scale)
    return buf.getvalue()


def generate_qr_svg(url: str, scale: int = 5) -> bytes:
    buf = io.BytesIO()
    segno.make(url, error="h").save(buf, kind="svg", scale=scale)
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
    "public_dpp_url",
    "sign_payload",
    "verify_payload",
]
