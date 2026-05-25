"""Fragmentos-stub de ISO/IEC 15459-1..6 (sin red).

Estas normas son de pago: no se redistribuye texto. Cada fragmento
contiene un abstract público del ISO Online Browsing Platform (≤200
palabras, uso legítimo) más una nota explícita de que el texto
completo está bajo licencia ISO. Cumple su función en el RAG: que
la cita normativa aparezca cuando el chat necesite referenciar el
Art. 77.3 del Reg. UE 2023/1542.
"""

from collections.abc import Iterable

from pydantic import HttpUrl

from app.rag.schema import Fragment, Language

_PARTS_EN: dict[str, tuple[str, str]] = {
    "Part 1": (
        "https://www.iso.org/standard/54779.html",
        "ISO/IEC 15459-1:2014 — Information technology — Automatic identification "
        "and data capture techniques — Unique identification — Part 1: Individual "
        "transport units. Specifies a unique, non-significant string of characters "
        "for the identification of transport units. Texto completo bajo licencia ISO.",
    ),
    "Part 2": (
        "https://www.iso.org/standard/54780.html",
        "ISO/IEC 15459-2:2015 — Unique identification — Part 2: Registration "
        "procedures. Specifies the registration procedures required to ensure "
        "that unique identifiers issued by different agencies do not collide. "
        "Texto completo bajo licencia ISO.",
    ),
    "Part 3": (
        "https://www.iso.org/standard/54781.html",
        "ISO/IEC 15459-3:2014 — Unique identification — Part 3: Common rules. "
        "Common rules for the construction of unique identifiers, applicable to "
        "the other parts of the standard. Texto completo bajo licencia ISO.",
    ),
    "Part 4": (
        "https://www.iso.org/standard/54782.html",
        "ISO/IEC 15459-4:2014 — Unique identification — Part 4: Individual "
        "products and product packages. Specifies a unique identifier for "
        "individual products and product packages. Texto completo bajo licencia ISO.",
    ),
    "Part 5": (
        "https://www.iso.org/standard/54783.html",
        "ISO/IEC 15459-5:2014 — Unique identification — Part 5: Individual "
        "returnable transport items (RTIs). Specifies a unique identifier for "
        "returnable transport items. Texto completo bajo licencia ISO.",
    ),
    "Part 6": (
        "https://www.iso.org/standard/54784.html",
        "ISO/IEC 15459-6:2014 — Unique identification — Part 6: Groupings. "
        "Specifies a unique identifier for groupings (logistic groupings of "
        "items). Texto completo bajo licencia ISO.",
    ),
}

_PARTS_ES: dict[str, tuple[str, str]] = {
    "Part 1": (
        "https://www.iso.org/standard/54779.html",
        "ISO/IEC 15459-1:2014 — Tecnologías de la información — Identificación "
        "automática y captura de datos — Identificación única — Parte 1: "
        "Unidades de transporte individuales. Especifica una cadena única no "
        "significativa para identificar unidades de transporte. Texto completo "
        "bajo licencia ISO.",
    ),
    "Part 2": (
        "https://www.iso.org/standard/54780.html",
        "ISO/IEC 15459-2:2015 — Identificación única — Parte 2: Procedimientos "
        "de registro. Especifica los procedimientos de registro necesarios para "
        "garantizar que los identificadores únicos emitidos por agencias distintas "
        "no colisionen. Texto completo bajo licencia ISO.",
    ),
    "Part 3": (
        "https://www.iso.org/standard/54781.html",
        "ISO/IEC 15459-3:2014 — Identificación única — Parte 3: Reglas comunes. "
        "Reglas comunes para la construcción de identificadores únicos, "
        "aplicables al resto de partes de la norma. Texto completo bajo licencia ISO.",
    ),
    "Part 4": (
        "https://www.iso.org/standard/54782.html",
        "ISO/IEC 15459-4:2014 — Identificación única — Parte 4: Productos "
        "individuales y embalajes de productos. Especifica un identificador "
        "único para productos individuales y sus embalajes. Texto completo "
        "bajo licencia ISO.",
    ),
    "Part 5": (
        "https://www.iso.org/standard/54783.html",
        "ISO/IEC 15459-5:2014 — Identificación única — Parte 5: Unidades de "
        "transporte retornables individuales (RTIs). Especifica un identificador "
        "único para unidades de transporte retornables. Texto completo bajo licencia ISO.",
    ),
    "Part 6": (
        "https://www.iso.org/standard/54784.html",
        "ISO/IEC 15459-6:2014 — Identificación única — Parte 6: Agrupaciones. "
        "Especifica un identificador único para agrupaciones logísticas de "
        "ítems. Texto completo bajo licencia ISO.",
    ),
}


def fetch_fragments(idioma: Language) -> Iterable[Fragment]:
    """Devuelve 6 fragmentos-stub (uno por parte) en el idioma pedido."""
    parts: dict[str, tuple[str, str]] = _PARTS_ES if idioma == "es" else _PARTS_EN
    for parte, (url, texto) in parts.items():
        yield Fragment(
            texto=texto,
            reglamento="ISO/IEC 15459",
            articulo=parte,
            apartado=None,
            idioma=idioma,
            fuente_url=HttpUrl(url),
            sector=None,
        )
