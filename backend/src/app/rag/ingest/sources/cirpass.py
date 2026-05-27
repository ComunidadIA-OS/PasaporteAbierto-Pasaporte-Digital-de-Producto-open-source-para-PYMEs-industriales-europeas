"""Source CIRPASS-2 Core Ontology.

La ontología se publica en JSON-LD (rdfs:label + rdfs:comment por clase).
Cada clase con label + comment se convierte en un Fragment cuyo
`articulo` es el label de la clase. No hay versión es oficial: solo en.

URL canónica: https://cirpass.eu/ontology/core (placeholder hasta
confirmar URL exacta en el plan).
"""

import json
from collections.abc import Iterable

from pydantic import HttpUrl

from app.rag.ingest.http_cache import CachedHttpClient
from app.rag.schema import Fragment

_CANONICAL_URL = "https://cirpass.eu/ontology/core"


def parse_cirpass_jsonld(payload: str) -> Iterable[Fragment]:
    """Parsea el JSON-LD de CIRPASS-2 Core y emite Fragments por clase."""
    data = json.loads(payload)
    graph = data.get("@graph", [])
    for entry in graph:
        label = entry.get("label")
        comment = entry.get("comment")
        if not label or not comment:
            continue
        yield Fragment(
            texto=f"{label}: {comment}",
            reglamento="CIRPASS-2 Core",
            articulo=str(label),
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
    """Descarga el JSON-LD canónico y emite Fragments."""
    payload = client.get_text(
        _CANONICAL_URL,
        cache_key="cirpass-2-core.jsonld",
        force_refresh=force_refresh,
    )
    yield from parse_cirpass_jsonld(payload)
