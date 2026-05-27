"""Source EUR-Lex: parser HTML + descarga para reglamentos UE.

Cubre Reg. UE 2024/1781 (ESPR), Reg. UE 2023/1542 (baterías) y actos
delegados publicados. Cada apartado dentro de cada artículo se modela
como un Fragment independiente. Los anexos se modelan como
`articulo="Annex N"`.

Selectores HTML basados en la estructura semántica de EUR-Lex:
- `p.oj-ti-art`     marca "Artículo N" / "Article N"
- `p.oj-sti-art`    subtítulo del artículo (no se persiste)
- `p.oj-normal`     párrafos numerados (apartados)
- `div.eli-main-title` cabecera del documento (no se persiste)
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup
from pydantic import HttpUrl

from app.rag.ingest.http_cache import CachedHttpClient
from app.rag.schema import Fragment, Language


class IngestParseError(RuntimeError):
    """Se levantó porque el HTML no contiene la estructura esperada."""


# Reconoce "Artículo 7", "Article 7", "Artículo 77 bis"
_ARTICLE_RE = re.compile(
    r"^(?:Artículo|Article)\s+([0-9]+(?:\s*bis|\s*ter|\s*quater)?)$", re.IGNORECASE
)
# Reconoce "ANEXO XIII", "ANNEX XIII", "ANEXO 1"
_ANNEX_RE = re.compile(r"^(?:ANEXO|ANNEX)\s+([IVXLCDM0-9]+)\s*$", re.IGNORECASE)
# Reconoce inicio de apartado: "1.", "12.", "1.a)", etc.
_PARAGRAPH_NUM_RE = re.compile(r"^\s*([0-9]+(?:\.[a-z0-9]+)*)\s*\.\s*(.*)$", re.DOTALL)


def parse_eurlex_html(
    html: str,
    *,
    reglamento: str,
    idioma: Language,
    fuente_url: HttpUrl,
    sector: str | None,
) -> Iterable[Fragment]:
    """Parsea HTML EUR-Lex en stream de Fragments por (artículo, apartado).

    Levanta `IngestParseError` si en >10 KB no encuentra ningún artículo
    o anexo (regresión: EUR-Lex cambió la estructura).
    """
    soup = BeautifulSoup(html, "lxml")

    current_articulo: str | None = None
    found_any = False

    for tag in soup.find_all("p"):
        classes = tag.get("class") or []
        text = tag.get_text(" ", strip=True)

        if "oj-ti-art" in classes:
            art = _match_article(text)
            annex = _match_annex(text)
            current_articulo = art or annex
            if current_articulo:
                found_any = True
            continue

        if current_articulo is None:
            continue

        if "oj-normal" in classes:
            apartado, contenido = _split_paragraph(text)
            if not contenido.strip():
                continue
            yield Fragment(
                texto=contenido.strip(),
                reglamento=reglamento,
                articulo=current_articulo,
                apartado=apartado,
                idioma=idioma,
                fuente_url=fuente_url,
                sector=sector,
            )

    if not found_any and len(html) > 10_000:
        raise IngestParseError(
            f"HTML >10KB sin artículos detectados (URL {fuente_url}). "
            "Probable cambio de estructura en EUR-Lex."
        )


def _match_article(text: str) -> str | None:
    m = _ARTICLE_RE.match(text.strip())
    if not m:
        return None
    return re.sub(r"\s+", " ", m.group(1)).strip()


def _match_annex(text: str) -> str | None:
    m = _ANNEX_RE.match(text.strip())
    if not m:
        return None
    return f"Annex {m.group(1)}"


def _split_paragraph(text: str) -> tuple[str | None, str]:
    """Extrae nº de apartado del inicio del párrafo, si existe."""
    m = _PARAGRAPH_NUM_RE.match(text)
    if not m:
        return None, text
    return m.group(1), m.group(2)


# ──────────────────────────────────────────────────────────────────────
# Fetcher de alto nivel (se completa en T6/T7)
# ──────────────────────────────────────────────────────────────────────

_EURLEX_BASE = "https://eur-lex.europa.eu/legal-content/{lang_upper}/TXT/HTML/?uri=CELEX:{celex}"


def build_eurlex_url(celex: str, idioma: Language) -> HttpUrl:
    return HttpUrl(_EURLEX_BASE.format(lang_upper=idioma.upper(), celex=celex))


def fetch_regulation_fragments(
    client: CachedHttpClient,
    *,
    celex: str,
    reglamento: str,
    sector: str | None,
    force_refresh: bool = False,
    languages: tuple[Language, ...] = ("es", "en"),
) -> Iterable[Fragment]:
    """Descarga y parsea un reglamento EUR-Lex en los idiomas pedidos."""
    for idioma in languages:
        url = build_eurlex_url(celex, idioma)
        html = client.get_text(
            str(url),
            cache_key=f"{celex}.{idioma}.html",
            force_refresh=force_refresh,
        )
        yield from parse_eurlex_html(
            html,
            reglamento=reglamento,
            idioma=idioma,
            fuente_url=url,
            sector=sector,
        )


def load_local_html(fixture_path: Path) -> str:
    """Helper para tests/local: lee un HTML del disco."""
    return fixture_path.read_text(encoding="utf-8")


# ──────────────────────────────────────────────────────────────────────
# Actos delegados ESPR publicados a la fecha
#
# Lista declarativa. Se rellena tras consultar EUR-Lex con el filtro
# tipo=delegReg + DD_YEAR=>=2024 + dominio="legal-acts". En caso de
# que no exista todavía ningún acto delegado ESPR publicado (estado
# real durante el desarrollo de F2-01 puede ser que la lista esté
# vacía), KNOWN_DELEGATED_ACTS = [] es respuesta válida y el CLI se
# salta este source con un INFO log.
# ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class DelegatedAct:
    """Acto delegado ESPR registrado para ingesta."""

    celex: str  # ej. "32024R0567"
    reglamento: str  # ej. "UE 2024/567"
    sector: str | None  # ej. "textile" o None si transversal

    @property
    def slug(self) -> str:
        return f"actos-delegados-{self.celex.lower()}"


# Rellenar con el resultado de la consulta del Step 1. Si está vacío,
# dejar la lista vacía explícitamente.
KNOWN_DELEGATED_ACTS: list[DelegatedAct] = []


def fetch_delegated_acts_fragments(
    client: CachedHttpClient,
    *,
    force_refresh: bool = False,
    languages: tuple[Language, ...] = ("es", "en"),
) -> Iterable[Fragment]:
    """Itera sobre los actos delegados registrados y los parsea."""
    for act in KNOWN_DELEGATED_ACTS:
        yield from fetch_regulation_fragments(
            client,
            celex=act.celex,
            reglamento=act.reglamento,
            sector=act.sector,
            force_refresh=force_refresh,
            languages=languages,
        )
