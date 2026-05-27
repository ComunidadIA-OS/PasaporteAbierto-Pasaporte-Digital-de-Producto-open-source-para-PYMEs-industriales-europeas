"""Source EUR-Lex: parser HTML + descarga para reglamentos UE.

Cubre Reg. UE 2024/1781 (ESPR), Reg. UE 2023/1542 (baterías) y actos
delegados publicados. Cada apartado dentro de cada artículo se modela
como un Fragment independiente (la unidad natural de cita). Los anexos
se modelan como `articulo="Annex N"`.

**Descarga vía Cellar (Oficina de Publicaciones).** El endpoint público
`eur-lex.europa.eu/legal-content/.../HTML/` aplica anti-scraping y
responde `202 Accepted` con cuerpo vacío a clientes no-navegador, por lo
que la ingesta producía 0 fragmentos. La fuente fiable es el repositorio
Cellar con content-negotiation: `publications.europa.eu/resource/celex/{celex}`
+ cabecera `Accept: application/xhtml+xml` y `Accept-Language`. El HTML
servido tiene la misma estructura semántica del Diario Oficial. La cita
(`fuente_url`) sigue apuntando a la página amigable de EUR-Lex.

Selectores HTML basados en la estructura semántica del Diario Oficial:
- `p.oj-ti-art`     marca "Artículo N" / "Article N"
- `p.oj-doc-ti`     marca títulos de anexo "ANEXO N" / "ANNEX N" (y el
                    título del reglamento, que se ignora al no casar)
- `p.oj-sti-art`    subtítulo del artículo (no se persiste)
- `p.oj-normal`     párrafos (apartados numerados y elementos de lista)
- `p.oj-ti-grseq-1` subtítulos de sección/anexo numerados (apartados de anexo)
- `div.eli-main-title` cabecera del documento (no se persiste)

Chunking por estructura legal (F2-02): los elementos de lista ("a)",
"i)"…) que EUR-Lex publica como párrafos sueltos se agrupan dentro de su
apartado, de modo que cada fragmento es un apartado completo y citable
("Reglamento X, Art. Y.Z") en vez de un marcador huérfano.
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

# Clases <p> cuyo texto forma parte del cuerpo de un artículo o anexo. Los
# subtítulos `oj-ti-grseq-1` se incluyen porque en los anexos numeran los
# apartados ("1.   INFORMACIÓN DE ACCESO PÚBLICO…"); las notas, firmas y
# tablas quedan fuera a propósito.
_CONTENT_CLASSES = frozenset({"oj-normal", "oj-ti-grseq-1"})
# Clases que pueden contener un título de artículo o de anexo.
_HEADING_CLASSES = frozenset({"oj-ti-art", "oj-doc-ti"})
# Subtítulo del artículo (su epígrafe oficial, p. ej. "Pasaporte digital del
# producto"). No es un fragmento propio, pero se antepone como contexto al
# texto de cada apartado para que el chunk sea auto-descriptivo y la
# similitud semántica reconozca de qué artículo trata (mejora el retrieval).
_SUBTITLE_CLASS = "oj-sti-art"


def parse_eurlex_html(
    html: str,
    *,
    reglamento: str,
    idioma: Language,
    fuente_url: HttpUrl,
    sector: str | None,
) -> Iterable[Fragment]:
    """Parsea HTML EUR-Lex en Fragments agrupados por (artículo, apartado).

    Recorre los `<p>` en orden documental manteniendo el artículo/anexo
    actual y acumulando el texto de cada apartado: los elementos de lista
    que EUR-Lex publica como párrafos sueltos ("a)", "i)"…) se concatenan
    dentro del apartado al que pertenecen, de forma que el fragmento
    resultante es la unidad de cita completa y no un marcador huérfano.

    Levanta `IngestParseError` si en >10 KB no encuentra ningún artículo
    o anexo (regresión: EUR-Lex cambió la estructura).
    """
    soup = BeautifulSoup(html, "lxml")

    fragments: list[Fragment] = []
    current_articulo: str | None = None
    current_apartado: str | None = None
    current_subtitulo: str | None = None
    buffer: list[str] = []
    found_any = False

    def flush() -> None:
        nonlocal buffer
        if current_articulo is not None and buffer:
            body = re.sub(r"\s+", " ", " ".join(buffer)).strip()
            if body:
                # Antepone el epígrafe del artículo como contexto del chunk.
                texto = f"{current_subtitulo}. {body}" if current_subtitulo else body
                fragments.append(
                    Fragment(
                        texto=texto,
                        reglamento=reglamento,
                        articulo=current_articulo,
                        apartado=current_apartado,
                        idioma=idioma,
                        fuente_url=fuente_url,
                        sector=sector,
                    )
                )
        buffer = []

    for tag in soup.find_all("p"):
        classes = set(tag.get("class") or [])
        # Normaliza el espacio duro (\xa0) que EUR-Lex usa entre "Artículo" y
        # el número, para que las regex y el texto final sean limpios.
        text = re.sub(r"\s+", " ", tag.get_text(" ", strip=True).replace("\xa0", " ")).strip()
        if not text:
            continue

        if classes & _HEADING_CLASSES:
            heading = _match_article(text) or _match_annex(text)
            if heading:
                flush()
                current_articulo = heading
                current_apartado = None
                current_subtitulo = None
                found_any = True
            # Un `oj-doc-ti` que no casa (p. ej. el título del reglamento) no
            # cambia el estado: se ignora sin tocar el artículo en curso.
            continue

        if current_articulo is None:
            continue
        if _SUBTITLE_CLASS in classes:
            # Epígrafe del artículo: se guarda como contexto, no como fragmento.
            if current_subtitulo is None:
                current_subtitulo = text
            continue
        if not (classes & _CONTENT_CLASSES):
            continue  # notas, firmas, tablas…

        apartado, contenido = _split_paragraph(text)
        if apartado is not None:
            # Comienza un apartado numerado nuevo: cierra el anterior.
            flush()
            current_apartado = apartado
            if contenido.strip():
                buffer.append(contenido.strip())
        else:
            # Elemento de lista o continuación: se acumula en el apartado actual.
            buffer.append(text)

    flush()

    if not found_any and len(html) > 10_000:
        raise IngestParseError(
            f"HTML >10KB sin artículos detectados (URL {fuente_url}). "
            "Probable cambio de estructura en EUR-Lex."
        )

    return fragments


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

# Página amigable de EUR-Lex: se usa como `fuente_url` de la cita (la que
# verá el usuario), no para descargar.
_EURLEX_BASE = "https://eur-lex.europa.eu/legal-content/{lang_upper}/TXT/HTML/?uri=CELEX:{celex}"
# Repositorio Cellar de la Oficina de Publicaciones: descarga fiable con
# content-negotiation (Accept + Accept-Language), sin anti-scraping.
_CELLAR_BASE = "http://publications.europa.eu/resource/celex/{celex}"


def build_eurlex_url(celex: str, idioma: Language) -> HttpUrl:
    """URL canónica y legible de EUR-Lex para mostrar en la cita."""
    return HttpUrl(_EURLEX_BASE.format(lang_upper=idioma.upper(), celex=celex))


def build_cellar_url(celex: str) -> str:
    """URL del repositorio Cellar desde la que se descarga el documento."""
    return _CELLAR_BASE.format(celex=celex)


def _cellar_headers(idioma: Language) -> dict[str, str]:
    """Cabeceras de content-negotiation: XHTML del DO en el idioma pedido."""
    return {"Accept": "application/xhtml+xml", "Accept-Language": idioma}


def fetch_regulation_fragments(
    client: CachedHttpClient,
    *,
    celex: str,
    reglamento: str,
    sector: str | None,
    force_refresh: bool = False,
    languages: tuple[Language, ...] = ("es", "en"),
) -> Iterable[Fragment]:
    """Descarga (vía Cellar) y parsea un reglamento EUR-Lex en los idiomas pedidos."""
    for idioma in languages:
        html = client.get_text(
            build_cellar_url(celex),
            cache_key=f"{celex}.{idioma}.html",
            force_refresh=force_refresh,
            headers=_cellar_headers(idioma),
        )
        yield from parse_eurlex_html(
            html,
            reglamento=reglamento,
            idioma=idioma,
            fuente_url=build_eurlex_url(celex, idioma),
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
