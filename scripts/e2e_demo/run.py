#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "httpx>=0.27",
#   "pyyaml>=6.0",
#   "reportlab>=4.0",
# ]
# ///
"""
E2E demo runner del wizard de PasaporteAbierto.

Recorre los 7 pasos del pipeline contra una instancia REAL del stack
(`make up` en docker), inyectando datos desde `config.yaml` y generando
PDFs sintéticos como certificación de producto.

Uso:
    uv run scripts/e2e_demo/run.py
    uv run scripts/e2e_demo/run.py --config otro_config.yaml --no-docs

Salida: cada paso imprime su resultado. Si algo falla, sale con código != 0
y muestra el cuerpo del error.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import httpx
import yaml
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


# ─── helpers de presentación ──────────────────────────────────────────────────

CYAN, GREEN, YELLOW, RED, RESET = "\033[36m", "\033[32m", "\033[33m", "\033[31m", "\033[0m"


def step(n: int | str, title: str) -> None:
    print(f"\n{CYAN}━━━ Paso {n}: {title}{RESET}")


def ok(msg: str) -> None:
    print(f"  {GREEN}✓{RESET} {msg}")


def info(msg: str) -> None:
    print(f"    {msg}")


def warn(msg: str) -> None:
    print(f"  {YELLOW}⚠{RESET} {msg}")


def die(msg: str, resp: httpx.Response | None = None) -> None:
    print(f"  {RED}✗ {msg}{RESET}", file=sys.stderr)
    if resp is not None:
        print(f"    HTTP {resp.status_code}", file=sys.stderr)
        try:
            print(f"    body: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}", file=sys.stderr)
        except Exception:
            print(f"    body: {resp.text[:500]}", file=sys.stderr)
    sys.exit(1)


# ─── generación de PDFs sintéticos ────────────────────────────────────────────


def build_pdf(path: Path, title: str, embeds: list[str]) -> None:
    """Genera un PDF mínimo con un title y bullets en `embeds`.

    Los strings de `embeds` quedan literales en el texto para que el
    Recolector (paso 5, LLM) pueda extraerlos y marcar `verified`.
    """
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    styles = getSampleStyleSheet()
    flow: list[Any] = [
        Paragraph(f"<b>{title}</b>", styles["Title"]),
        Spacer(1, 12),
        Paragraph(
            "Documento sintético generado por el harness E2E de PasaporteAbierto. "
            "No tiene validez legal. Su único propósito es alimentar el Recolector "
            "del wizard con campos textuales reconocibles.",
            styles["Italic"],
        ),
        Spacer(1, 18),
    ]
    for line in embeds:
        flow.append(Paragraph(f"• {line}", styles["BodyText"]))
        flow.append(Spacer(1, 6))
    doc.build(flow)


# ─── pasos del pipeline ───────────────────────────────────────────────────────


def create_session(client: httpx.Client, description: str) -> str:
    step(1, "POST /sessions (descripción)")
    r = client.post("/api/v1/sessions", json={"description": description})
    if r.status_code != 201:
        die("no se pudo crear la sesión", r)
    sid = r.json()["session_id"]
    ok(f"sesión creada: {sid}")
    return sid


def classify(client: httpx.Client, sid: str) -> str:
    step(2, "POST /classify (IA — Clasificador)")
    r = client.post(f"/api/v1/sessions/{sid}/classify", timeout=120.0)
    if r.status_code != 200:
        die("clasificación falló", r)
    body = r.json()
    sector = body["sector"]
    conf = body["confidence"]
    review = body["requires_review"]
    cit = body.get("citation") or {}
    ok(f"sector={sector}  confidence={conf:.2f}  requires_review={review}")
    if cit:
        info(f"cita: [{cit.get('regulation')}, {cit.get('article')}]")
    if review:
        warn("requires_review=True — el clasificador no está seguro, pero seguimos")
    return sector


def put_bom(client: httpx.Client, sid: str, fields: dict[str, Any]) -> None:
    step(3, "PUT /bom (campos del plugin)")
    r = client.put(f"/api/v1/sessions/{sid}/bom", json={"fields": fields})
    if r.status_code != 200:
        die("PUT BOM falló", r)
    body = r.json()
    if not body["accepted"] or body["errors"]:
        die(f"BOM rechazado. Errores: {body['errors']}")
    ok(f"BOM aceptado — {len(fields)} campos enviados")


def upload_documents(
    client: httpx.Client, sid: str, doc_specs: list[dict[str, Any]], tmpdir: Path
) -> list[int]:
    step(4, "POST /documents (PDFs sintéticos)")
    doc_ids: list[int] = []
    for spec in doc_specs:
        doc_type = spec["doc_type"]
        pdf_path = tmpdir / f"{doc_type}.pdf"
        build_pdf(pdf_path, spec["title"], spec["embeds"])
        with pdf_path.open("rb") as f:
            r = client.post(
                f"/api/v1/sessions/{sid}/documents",
                params={"doc_type": doc_type},
                files={"file": (pdf_path.name, f, "application/pdf")},
                timeout=30.0,
            )
        if r.status_code != 200:
            die(f"subida de {doc_type} falló", r)
        body = r.json()
        doc_ids.append(body["document"]["id"])
        marker = " (dedup)" if body.get("deduplicated") else ""
        ok(f"{doc_type:14s} → id={body['document']['id']}{marker}  {pdf_path.stat().st_size} bytes")
    return doc_ids


def extract(client: httpx.Client, sid: str) -> dict[str, Any]:
    step(5, "POST /extract (IA — Recolector, SSE)")
    final: dict[str, Any] = {}
    # Timeout generoso: el Recolector procesa N docs con N llamadas al LLM.
    with client.stream(
        "POST", f"/api/v1/sessions/{sid}/extract", timeout=httpx.Timeout(600.0)
    ) as r:
        if r.status_code != 200:
            # Para errores, leemos el cuerpo completo antes de salir.
            r.read()
            die("extract falló", r)
        for raw_line in r.iter_lines():
            if not raw_line or not raw_line.startswith("data: "):
                continue
            evt = json.loads(raw_line[len("data: ") :])
            ev_type = evt.get("event")
            if ev_type == "progress":
                processed = evt.get("processed", "?")
                total = evt.get("total", "?")
                info(f"progress {processed}/{total} — {evt.get('current_document', '')}")
            elif ev_type == "done":
                final = evt
                ok(
                    f"done — verified={evt.get('fields_verified', 0)}  "
                    f"self_declared={evt.get('fields_self_declared', 0)}  "
                    f"pending={evt.get('fields_required_pending', 0)}"
                )
            elif ev_type == "error":
                die(f"evento error en SSE: {evt}")
    if not final:
        die("SSE terminó sin evento 'done'")
    return final


def verify(client: httpx.Client, sid: str) -> dict[str, Any]:
    step(6, "GET /verify")
    r = client.get(f"/api/v1/sessions/{sid}/verify")
    if r.status_code != 200:
        die("verify falló", r)
    body = r.json()
    completeness = body.get("completeness", 0)
    missing = body.get("missing_fields", [])
    warnings = body.get("warnings", [])
    if body["can_publish"]:
        ok(f"can_publish=True  completeness={completeness:.0%}")
    else:
        warn(f"can_publish=False  completeness={completeness:.0%}  missing={len(missing)}")
        for m in missing[:10]:
            info(f"  · falta: {m}")
        if len(missing) > 10:
            info(f"  · …y {len(missing) - 10} más")
    if warnings:
        info(f"warnings: {len(warnings)}")
        for w in warnings[:5]:
            info(f"  · {w}")
    return body


def publish_dpp(client: httpx.Client, sid: str) -> dict[str, Any]:
    step(7, "POST /dpp (generación + firma + QR)")
    r = client.post(f"/api/v1/sessions/{sid}/dpp")
    if r.status_code != 200:
        die("publish falló", r)
    body = r.json()
    ok(f"gs1_uri = {body['gs1_uri']}")
    info(f"public_url = {body['public_url']}")
    info(f"qr_png     = {body['qr_png_url']}")
    info(f"qr_svg     = {body['qr_svg_url']}")
    info(f"signed     = {body['signed']}")
    return body


def check_public(client: httpx.Client, sid: str, gs1_uri: str) -> None:
    step("8a", "GET /dpp/{slug} (JSON-LD)")
    slug = sid.split("-", 1)[0]
    r = client.get(f"/dpp/{slug}", headers={"Accept": "application/ld+json"})
    if r.status_code != 200:
        die("DPP público (JSON-LD) falló", r)
    jsonld = r.json()
    if jsonld.get("@id") != gs1_uri:
        die(f"@id no coincide: esperado {gs1_uri}, got {jsonld.get('@id')}")
    n_fields = len(jsonld.get("fields", []) or jsonld.get("fields", {}))
    ok(f"@id ok — sector={jsonld.get('sector')}  fields_publicos={n_fields}")

    step("8b", "GET /dpp/{slug} (HTML)")
    r = client.get(f"/dpp/{slug}", headers={"Accept": "text/html"})
    if r.status_code != 200:
        die("DPP público (HTML) falló", r)
    html = r.text
    badges = [b for b in ("verified", "self_declared", "required_pending") if b in html]
    ok(f"HTML renderizado  badges_presentes={badges}")


def audit_check(client: httpx.Client) -> None:
    step("9", "GET /audit/verify (hash chain)")
    r = client.get("/api/v1/audit/verify")
    if r.status_code != 200:
        die("audit verify falló", r)
    body = r.json()
    if not body.get("ok"):
        die(f"audit chain ROTA — {body}")
    ok(f"chain ok — total_rows={body.get('total_rows', '?')}")


# ─── main ─────────────────────────────────────────────────────────────────────


def _open_browser(url: str) -> None:
    """Intenta abrir `url` en el navegador del sistema (macOS/Linux/WSL).

    No es fatal si falla — solo imprime un warning.
    """
    for cmd in (["open"], ["xdg-open"], ["wslview"]):
        if shutil.which(cmd[0]):
            try:
                subprocess.Popen([*cmd, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except OSError:
                continue
    warn(f"no pude abrir el navegador automáticamente — visita {url} a mano")


def main() -> None:
    parser = argparse.ArgumentParser(description="E2E demo del wizard de PasaporteAbierto")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent / "config.yaml",
        help="Ruta al YAML de config",
    )
    parser.add_argument(
        "--no-docs",
        action="store_true",
        help="Saltar paso 4 (no generar ni subir PDFs)",
    )
    parser.add_argument(
        "--stop-at",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Ejecuta solo pasos 1..N vía API y termina imprimiendo el link al "
            "wizard del frontend, para que continúes manualmente desde la UI. "
            "Útiles: 1 (solo sesión), 2 (+clasificar), 3 (+BOM), 4 (+docs), "
            "5 (+extract). Sin este flag, recorre los 7 pasos completos."
        ),
    )
    parser.add_argument(
        "--open-browser",
        action="store_true",
        help="Con --stop-at, abre el navegador en la URL del wizard al terminar.",
    )
    parser.add_argument(
        "--frontend-base",
        default="http://localhost:3000",
        help="Base URL del frontend para construir el link del wizard.",
    )
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    api_base = cfg["api_base"].rstrip("/")
    frontend_base = args.frontend_base.rstrip("/")

    stop_at = args.stop_at if args.stop_at is not None else 99  # 99 = full E2E
    if args.stop_at is not None and not 1 <= args.stop_at <= 7:
        die(f"--stop-at debe estar entre 1 y 7, no {args.stop_at}")

    print(f"{CYAN}E2E demo wizard PasaporteAbierto{RESET}")
    print(f"  api_base      = {api_base}")
    print(f"  frontend_base = {frontend_base}")
    print(f"  config        = {args.config}")
    print(f"  modo          = {'full E2E' if args.stop_at is None else f'demo (stop-at={args.stop_at})'}")
    print(f"  documentos    = {'SKIP' if args.no_docs else len(cfg.get('documents', []))}")

    with httpx.Client(base_url=api_base, timeout=30.0) as client:
        # Sanity: backend vivo.
        try:
            r = client.get("/api/v1/health")
            r.raise_for_status()
        except httpx.HTTPError as e:
            die(f"backend no responde en {api_base}: {e}")

        sid = create_session(client, cfg["description"])
        if stop_at >= 2:
            classify(client, sid)
        if stop_at >= 3:
            put_bom(client, sid, cfg["bom"]["fields"])
        if stop_at >= 4 and not args.no_docs:
            with tempfile.TemporaryDirectory(prefix="dpp_e2e_") as tmp:
                upload_documents(client, sid, cfg["documents"], Path(tmp))
        elif stop_at >= 4 and args.no_docs:
            warn("--no-docs activo: saltando paso 4")
        if stop_at >= 5:
            extract(client, sid)
        if stop_at >= 6:
            verify_body = verify(client, sid)
            if not verify_body["can_publish"]:
                die("verify bloquea la publicación; revisa missing_fields arriba")
        if stop_at >= 7:
            dpp = publish_dpp(client, sid)
            check_public(client, sid, dpp["gs1_uri"])
            audit_check(client)
            print(f"\n{GREEN}━━━ E2E completado con éxito{RESET}")
            print(f"  Sesión: {sid}")
            print(f"  Abre:   {dpp['public_url']}")
            return

    # Modo demo (--stop-at < 7): imprimimos el link al frontend.
    wizard_url = f"{frontend_base}/wizard/{sid}"
    print(f"\n{GREEN}━━━ Sesión lista para continuar manualmente en la UI{RESET}")
    print(f"  Sesión:        {sid}")
    print(f"  Wizard (UI):   {CYAN}{wizard_url}{RESET}")
    print(f"  Estado:        pasos 1..{stop_at} hechos vía API; continúa desde {stop_at + 1}")
    if args.open_browser:
        _open_browser(wizard_url)


if __name__ == "__main__":
    main()
