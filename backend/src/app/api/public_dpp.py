"""Endpoint público del DPP con content negotiation.

`GET /dpp/{slug}` resuelve un DPP publicado por el prefijo URL-friendly
del `session_id` (primeros 8 chars del UUID). El backend usa `LIKE` para
no exponer el UUID completo en la URL pública.

Content negotiation por el header `Accept`:
  - `application/ld+json` → JSON-LD CIRPASS-2 Core con firma adjunta
  - `text/html` → página renderizada server-side con distinción visual
    entre campos verified y self_declared (legible para humanos y
    indexable)
  - cualquier otro → JSON-LD por defecto

Solo expone campos `access_level=public` (las otras tres secciones del
Annex XIII tienen otros canales de acceso).
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.published_dpps import PublishedDPP

router = APIRouter(prefix="/dpp", tags=["public"])

DbSession = Annotated[Session, Depends(get_session)]


def _resolve_by_slug(db: Session, slug: str) -> PublishedDPP:
    """Encuentra el DPP cuyo `session_id` empieza por `slug`.

    Valida que el slug tenga exactamente 8 caracteres (primer segmento
    del UUID4) para evitar colisiones con prefijos cortos.
    """
    if len(slug) != 8 or not slug.isalnum():
        raise HTTPException(status_code=404, detail="dpp_not_found")
    pdpp = db.exec(
        select(PublishedDPP).where(PublishedDPP.session_id.startswith(slug))  # type: ignore[attr-defined]
    ).first()
    if pdpp is None:
        raise HTTPException(status_code=404, detail="dpp_not_found")
    return pdpp


_BADGE_LABELS = {
    "verified": ("✓ verificado", "verified"),
    "self_declared": ("autodeclarado", "self_declared"),
}


def _field_value_and_provenance(raw: Any) -> tuple[str, str]:
    """Extrae (valor_renderizable, provenance) de un campo del JSON-LD.

    Soporta los dos shapes:
      - nuevo (F5-01 #2): `{"value": v, "provenance": "verified"|"self_declared"}`
      - legacy (pre-provenance): valor escalar plano

    Para DPPs legacy persistidos antes de la migración, asumimos
    `self_declared` (la opción más conservadora).
    """
    if isinstance(raw, dict) and "value" in raw:
        return str(raw["value"]), str(raw.get("provenance", "self_declared"))
    return str(raw), "self_declared"


def _render_html(pdpp: PublishedDPP) -> str:
    jsonld: dict[str, Any] = pdpp.jsonld or {}
    fields = jsonld.get("fields", {}) or {}
    rows: list[str] = []
    for k, raw in sorted(fields.items()):
        value, prov = _field_value_and_provenance(raw)
        label, css_class = _BADGE_LABELS.get(prov, ("?", "self_declared"))
        rows.append(
            f'<tr><td class="k">{_h(k)}</td>'
            f"<td>{_h(value)}</td>"
            f'<td class="p"><span class="badge {_h(css_class)}">{_h(label)}</span></td></tr>'
        )
    rows_html = "".join(rows)
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DPP · {_h(jsonld.get("sector", ""))}</title>
<meta name="description" content="Pasaporte Digital de Producto conforme a {_h(jsonld.get("regulation", ""))}.">
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; color: #222; }}
  header {{ border-bottom: 1px solid #ddd; padding-bottom: 1rem; }}
  h1 {{ font-size: 1.4rem; margin: 0; }}
  .meta {{ color: #666; font-size: 0.85rem; margin-top: 0.25rem; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 1.5rem; }}
  td {{ padding: 0.4rem 0.6rem; border-bottom: 1px solid #eee; font-size: 0.9rem; vertical-align: top; }}
  td.k {{ color: #555; font-family: ui-monospace, monospace; width: 35%; }}
  td.p {{ width: 25%; text-align: right; }}
  .badge {{ display: inline-block; padding: 0.1rem 0.5rem; border-radius: 999px; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.02em; }}
  .badge.verified {{ background: #dcfce7; color: #166534; }}
  .badge.self_declared {{ background: #ffedd5; color: #9a3412; }}
  .legend {{ display: flex; gap: 0.75rem; margin-top: 1rem; font-size: 0.75rem; color: #555; }}
  footer {{ margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #ddd; color: #888; font-size: 0.75rem; }}
  code {{ font-size: 0.75rem; word-break: break-all; }}
</style>
</head>
<body>
<header>
  <h1>Pasaporte Digital de Producto · {_h(jsonld.get("sector", ""))}</h1>
  <p class="meta">{_h(jsonld.get("regulation", ""))} · sólo campos de acceso público (Annex XIII §1).</p>
  <p class="legend">
    <span class="badge verified">✓ verificado</span><span>respaldado por documento subido</span>
    <span class="badge self_declared">autodeclarado</span><span>declaración del fabricante</span>
  </p>
</header>
<table>{rows_html}</table>
<footer>
  <p><strong>Identificador:</strong> <code>{_h(pdpp.gs1_uri)}</code></p>
  <p><strong>Firma Ed25519 (base64):</strong> <code>{_h(pdpp.signature or "—")}</code></p>
  <p><strong>Clave pública (base64):</strong> <code>{_h(pdpp.public_key or "—")}</code></p>
</footer>
</body>
</html>"""


def _h(s: object) -> str:
    """Escapado HTML mínimo para evitar XSS si entrara texto malicioso."""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


@router.get("/{slug}")
def get_public_dpp(
    slug: str,
    db: DbSession,
    accept: str = Header(default="application/ld+json"),
):
    pdpp = _resolve_by_slug(db, slug)
    # Parsear Accept correctamente: split por comas y comparar media types
    accepted_types = [t.split(";")[0].strip() for t in accept.split(",")]
    if "text/html" in accepted_types:
        return HTMLResponse(_render_html(pdpp))
    # Default: JSON-LD CIRPASS-2 Core. Headers de firma solo si el DPP está
    # firmado — un DPP `sign=false` (F5-04 CA #3) no debe sembrar headers
    # vacíos que un verificador podría confundir con una firma nula.
    headers: dict[str, str] = {}
    if pdpp.signature and pdpp.public_key:
        headers["X-Signature"] = pdpp.signature
        headers["X-Public-Key"] = pdpp.public_key
    return JSONResponse(
        content=pdpp.jsonld,
        media_type="application/ld+json",
        headers=headers,
    )
