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


# Iconos SVG inline (la página la sirve el backend, no el bundle Next con
# Material Symbols; SVG inline mantiene el lenguaje de diseño sin CDN ni
# caracteres-icono, y funciona en despliegues self-hosted sin red externa).
_SVG_CHECK = (
    '<svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">'
    '<path fill="currentColor" d="M13.5 4.2a.9.9 0 0 1 0 1.27l-6 6a.9.9 0 0 1-1.27 0'
    'L2.5 7.74A.9.9 0 1 1 3.77 6.47l2.6 2.6 5.36-5.37a.9.9 0 0 1 1.27 0z"/></svg>'
)
_SVG_DECLARED = (
    '<svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">'
    '<path fill="currentColor" d="M11.7 1.4a1 1 0 0 1 1.4 0l1.5 1.5a1 1 0 0 1 0 1.4'
    'l-8 8a1 1 0 0 1-.44.26l-3 .8a.6.6 0 0 1-.73-.74l.8-3a1 1 0 0 1 .26-.43l8-8zM11 '
    '3.3 12.7 5 14 3.7 12.3 2 11 3.3z"/></svg>'
)
_SVG_EMBLEM = (
    '<svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true">'
    '<path fill="currentColor" d="M12 1.5 3.5 5v6.2c0 5 3.6 9.4 8.5 10.8 4.9-1.4 8.5'
    '-5.8 8.5-10.8V5L12 1.5z"/><path fill="#fff" d="M10.7 14.6 7.9 11.8l1.2-1.2 1.6 '
    '1.6 4.1-4.1 1.2 1.2-5.3 5.3z"/></svg>'
)
_SVG_LOCK = (
    '<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">'
    '<path fill="currentColor" d="M8 1a3 3 0 0 0-3 3v2H4.2A1.2 1.2 0 0 0 3 7.2v6.6A1.2 '
    '1.2 0 0 0 4.2 15h7.6A1.2 1.2 0 0 0 13 13.8V7.2A1.2 1.2 0 0 0 11.8 6H11V4a3 3 0 0 '
    '0-3-3zm1.5 5h-3V4a1.5 1.5 0 0 1 3 0v2z"/></svg>'
)

# (etiqueta, clase CSS, icono SVG) por estado de provenance.
_BADGE_META = {
    "verified": ("Verificado", "verified", _SVG_CHECK),
    "self_declared": ("Autodeclarado", "self_declared", _SVG_DECLARED),
}

_CSS = """
:root{
  --eu-blue:#003399; --green:#00b14f;
  --ink:#1a2230; --muted:#5b6573; --faint:#9aa3b2;
  --line:#e6e9f0; --bg:#eef1f6; --card:#fff;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);line-height:1.5;
  font-family:"IBM Plex Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
  -webkit-font-smoothing:antialiased;}
.topband{height:4px;background:var(--eu-blue)}
.wrap{max-width:860px;margin:0 auto;padding:32px 20px 56px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden}
.head{padding:28px 32px;border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:center;gap:11px;color:var(--eu-blue)}
.brand .emblem{flex:none;line-height:0}
.brand .kicker{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:11px;
  letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
h1{font-size:24px;line-height:1.2;letter-spacing:-.018em;margin:14px 0 0;font-weight:600}
h1 .sector{color:var(--eu-blue);text-transform:capitalize}
.meta{color:var(--muted);font-size:13.5px;margin:8px 0 0}
.legend{display:flex;flex-wrap:wrap;gap:18px;margin-top:18px}
.legend .row{display:inline-flex;align-items:center;gap:7px;font-size:12.5px;color:var(--muted)}
.badge{display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border-radius:999px;
  font-size:11px;font-weight:600;letter-spacing:.02em;text-transform:uppercase;white-space:nowrap}
.badge svg{flex:none}
.badge.verified{background:#e3f6ea;color:#00723a}
.badge.self_declared{background:#eceff3;color:#566072}
table{width:100%;border-collapse:collapse}
tbody tr{border-bottom:1px solid var(--line)}
tbody tr:last-child{border-bottom:0}
td{padding:13px 16px;font-size:14px;vertical-align:top}
td.k{width:34%;color:var(--muted);font-size:12.5px;word-break:break-word;
  font-family:"IBM Plex Mono",ui-monospace,monospace}
td.v{color:var(--ink);word-break:break-word}
td.v a{color:var(--eu-blue);text-decoration:none;border-bottom:1px solid #b9c7ec}
td.v a:hover{border-bottom-color:var(--eu-blue)}
td.p{width:1%;text-align:right;white-space:nowrap}
.vlist{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:4px}
.vlist li{padding-left:13px;position:relative}
.vlist li::before{content:"";position:absolute;left:0;top:8px;width:5px;height:5px;
  border-radius:50%;background:var(--eu-blue);opacity:.5}
.muted{color:var(--faint)}
.verify{padding:22px 32px;background:#fafbfd;border-top:1px solid var(--line)}
.verify h2{display:flex;align-items:center;gap:8px;margin:0 0 14px;font-size:13px;
  text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:600}
.verify h2 svg{color:var(--green)}
.kv{margin:0 0 10px}.kv:last-child{margin:0}
.kv .lbl{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.06em;
  color:var(--faint);margin-bottom:3px}
.kv code{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:12px;
  color:var(--ink);word-break:break-all}
.foot{margin-top:18px;text-align:center;color:var(--faint);font-size:11.5px}
@media(max-width:560px){
  .head,.verify{padding-left:18px;padding-right:18px}
  td{padding:11px 10px}td.k{width:42%}h1{font-size:20px}
}
"""


def _badge(prov: str) -> str:
    label, css_class, icon = _BADGE_META.get(prov, ("Desconocido", "self_declared", _SVG_DECLARED))
    return f'<span class="badge {css_class}">{icon}{_h(label)}</span>'


def _field_value_and_provenance(raw: Any) -> tuple[Any, str]:
    """Extrae (valor, provenance) de un campo del JSON-LD.

    Soporta los dos shapes:
      - nuevo (F5-01 #2): `{"value": v, "provenance": "verified"|"self_declared"}`
      - legacy (pre-provenance): valor escalar plano

    Devuelve el valor sin convertir a `str` para que `_format_value` pueda
    renderizar listas/objetos de forma legible. Para DPPs legacy asumimos
    `self_declared` (la opción más conservadora).
    """
    if isinstance(raw, dict) and "value" in raw:
        return raw["value"], str(raw.get("provenance", "self_declared"))
    return raw, "self_declared"


def _format_value(value: Any) -> str:
    """Renderiza el valor de un campo como HTML legible y escapado.

    Los repeaters (materiales críticos, sustancias peligrosas) llegan como
    lista de objetos: se muestran como una línea por elemento en vez del
    `repr` de Python (`[{'name': ...}]`) que se veía antes. Las URLs se
    vuelven enlaces.
    """
    if isinstance(value, list):
        if not value:
            return '<span class="muted">—</span>'
        items: list[str] = []
        for it in value:
            if isinstance(it, dict):
                parts = [_h(v) for v in it.values() if v not in (None, "")]
                items.append(" · ".join(parts) if parts else "—")
            else:
                items.append(_h(it))
        return '<ul class="vlist">' + "".join(f"<li>{x}</li>" for x in items) + "</ul>"
    if isinstance(value, dict):
        parts = [_h(v) for v in value.values() if v not in (None, "")]
        return " · ".join(parts) if parts else '<span class="muted">—</span>'
    text = str(value)
    if text.startswith(("http://", "https://")):
        return f'<a href="{_h(text)}" target="_blank" rel="noreferrer">{_h(text)}</a>'
    return _h(text)


def _render_html(pdpp: PublishedDPP) -> str:
    jsonld: dict[str, Any] = pdpp.jsonld or {}
    fields = jsonld.get("fields", {}) or {}
    sector = _h(jsonld.get("sector", ""))
    regulation = _h(jsonld.get("regulation", ""))
    rows: list[str] = []
    for k, raw in sorted(fields.items()):
        value, prov = _field_value_and_provenance(raw)
        rows.append(
            f'<tr><td class="k">{_h(k)}</td>'
            f'<td class="v">{_format_value(value)}</td>'
            f'<td class="p">{_badge(prov)}</td></tr>'
        )
    rows_html = "".join(rows)
    return (
        "<!doctype html>\n"
        '<html lang="es"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>DPP · {sector}</title>"
        f'<meta name="description" content="Pasaporte Digital de Producto conforme a {regulation}.">'
        f"<style>{_CSS}</style></head><body>"
        '<div class="topband"></div>'
        '<div class="wrap"><div class="card">'
        '<header class="head">'
        f'<div class="brand"><span class="emblem">{_SVG_EMBLEM}</span>'
        '<span class="kicker">Pasaporte Digital de Producto</span></div>'
        f'<h1>Pasaporte Digital de Producto · <span class="sector">{sector}</span></h1>'
        f'<p class="meta">{regulation} · sólo campos de acceso público (Annex XIII §1).</p>'
        '<div class="legend">'
        f'<span class="row">{_badge("verified")} respaldado por documento subido</span>'
        f'<span class="row">{_badge("self_declared")} declaración del fabricante</span>'
        "</div></header>"
        f"<table><tbody>{rows_html}</tbody></table>"
        '<section class="verify">'
        f"<h2>{_SVG_LOCK} Verificación criptográfica</h2>"
        f'<div class="kv"><span class="lbl">Identificador</span><code>{_h(pdpp.gs1_uri)}</code></div>'
        '<div class="kv"><span class="lbl">Firma Ed25519 (base64)</span>'
        f"<code>{_h(pdpp.signature or '—')}</code></div>"
        '<div class="kv"><span class="lbl">Clave pública (base64)</span>'
        f"<code>{_h(pdpp.public_key or '—')}</code></div>"
        "</section></div>"
        '<p class="foot">Generado por PasaporteAbierto · '
        "DPP conforme al Reglamento UE 2024/1781 (ESPR)</p>"
        "</div></body></html>"
    )


def _h(s: object) -> str:
    """Escapado HTML mínimo para evitar XSS si entrara texto malicioso."""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _parse_accept(accept: str) -> list[tuple[str, float]]:
    """Parsea el header Accept devolviendo `(media_type, q_value)` por entrada.

    Sigue RFC 7231 §5.3.2: cada media-range se separa por coma; los parámetros
    se separan por `;`. El parámetro `q` (default 1.0) define la preferencia.
    Media-ranges malformados o con `q` no parseable se mantienen con q=1.0
    (interpretación tolerante recomendada por el propio RFC). Entradas con
    `media_type` vacío se descartan.
    """
    parsed: list[tuple[str, float]] = []
    for raw in accept.split(","):
        parts = [p.strip() for p in raw.split(";") if p.strip()]
        if not parts:
            continue
        media_type = parts[0].lower()
        if not media_type:
            continue
        q = 1.0
        for param in parts[1:]:
            if param.lower().startswith("q="):
                try:
                    q = float(param[2:].strip())
                except ValueError:
                    q = 1.0
                break
        parsed.append((media_type, q))
    return parsed


def _prefers_html(accept: str) -> bool:
    """Decide si el cliente prefiere text/html sobre application/ld+json.

    Parsea el header Accept respetando q-values (RFC 7231 §5.3.2). Devuelve
    True solo si text/html tiene q > 0 y su q es ≥ que el de application/ld+json
    (default 0 si ld+json no aparece). En empate gana JSON-LD por ser el
    formato canónico para máquinas (FUNCIONAL §5).
    """
    html_q = 0.0
    jsonld_q = 0.0
    html_seen = False
    for media_type, q in _parse_accept(accept):
        if media_type == "text/html":
            html_seen = True
            # Si aparece múltiples veces, nos quedamos con la mayor preferencia.
            if q > html_q:
                html_q = q
        elif media_type == "application/ld+json":
            if q > jsonld_q:
                jsonld_q = q
    if not html_seen or html_q <= 0.0:
        return False
    # Empate → JSON-LD (default seguro para auditores/agregadores, FUNCIONAL §5).
    return html_q > jsonld_q


@router.get("/{slug}")
def get_public_dpp(
    slug: str,
    db: DbSession,
    accept: str = Header(default="application/ld+json"),
):
    pdpp = _resolve_by_slug(db, slug)
    if _prefers_html(accept):
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
