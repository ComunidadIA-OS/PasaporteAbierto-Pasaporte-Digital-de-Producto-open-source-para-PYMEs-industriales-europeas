"""Source GS1 Digital Link spec 1.3.

Estructura HTML: <h2>N. Título</h2> seguidos de <p>...</p> hasta el
próximo <h2>. Cada sección numerada se convierte en un Fragment con
articulo="sección N", texto = título + concatenación de párrafos.
"""

import re
from collections.abc import Iterable

from bs4 import BeautifulSoup
from pydantic import HttpUrl

from app.rag.ingest.http_cache import CachedHttpClient
from app.rag.schema import Fragment

_CANONICAL_URL = "https://www.gs1.org/standards/gs1-digital-link"
_SECTION_RE = re.compile(r"^\s*([0-9]+)\.\s+(.+?)\s*$")


def parse_gs1_html(html: str) -> Iterable[Fragment]:
    """Parsea HTML de GS1 Digital Link y emite Fragments por sección."""
    soup = BeautifulSoup(html, "lxml")
    sections: list[tuple[str, str, list[str]]] = []  # (numero, titulo, parrafos)
    current: tuple[str, str, list[str]] | None = None

    for tag in soup.find_all(["h2", "p"]):
        if tag.name == "h2":
            text = tag.get_text(" ", strip=True)
            m = _SECTION_RE.match(text)
            if not m:
                current = None
                continue
            if current is not None:
                sections.append(current)
            current = (m.group(1), m.group(2), [])
        elif tag.name == "p" and current is not None:
            current[2].append(tag.get_text(" ", strip=True))

    if current is not None:
        sections.append(current)

    for numero, titulo, parrafos in sections:
        cuerpo = " ".join(p for p in parrafos if p)
        yield Fragment(
            texto=f"{titulo}. {cuerpo}".strip(),
            reglamento="GS1 Digital Link 1.3.0",
            articulo=f"sección {numero}",
            apartado=None,
            idioma="en",
            fuente_url=HttpUrl(_CANONICAL_URL),
            sector=None,
        )


def fetch_fragments(
    client: CachedHttpClient,
    *,
    force_refresh: bool = False,
) -> Iterable[Fragment]:
    payload = client.get_text(
        _CANONICAL_URL,
        cache_key="gs1-digital-link.html",
        force_refresh=force_refresh,
    )
    yield from parse_gs1_html(payload)
