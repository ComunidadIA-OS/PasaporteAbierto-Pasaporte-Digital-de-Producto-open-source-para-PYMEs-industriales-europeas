"""Contrato compartido del módulo RAG (F2).

Este fichero es la frontera entre las ramas de trabajo de F2:

- F2-01 (ingesta) produce objetos `Fragment` y los persiste en
  `backend/data/corpus/{reglamento_slug}.{idioma}.jsonl`.
- F2-02 (chunking + embeddings) los lee y los indexa en ChromaDB.
- F2-03 (retrieval) implementa `search_corpus()`.
- F2-04 (tests) consume `search_corpus()` desde `backend/tests/rag/`.

Cambiar este fichero implica coordinar las 4 ramas. Hacerlo en PR aparte.
"""

from typing import Literal

from pydantic import BaseModel, HttpUrl

Language = Literal["es", "en"]


class Fragment(BaseModel):
    """Unidad mínima de texto legal con metadatos suficientes para citar.

    Producto de F2-01, entrada de F2-02.
    """

    texto: str
    reglamento: str  # "UE 2024/1781" | "UE 2023/1542" | ...
    articulo: str  # "7" | "77" | "Annex XIII" — string para admitir anexos y "bis"
    apartado: str | None = None  # "3" | "3.a" | None si el artículo no tiene apartados
    idioma: Language
    fuente_url: HttpUrl  # URL canónica en EUR-Lex u otra fuente oficial
    sector: str | None = None  # "batteries" si es sector-específico; None si transversal


class Filters(BaseModel):
    """Filtros opcionales para `search_corpus`.

    - `sector="batteries"` incluye fragmentos del sector + transversales (sector=None).
      Para "solo sector-específico", el caller filtra a posteriori.
    - `articulos` hace match exacto sobre `Fragment.articulo`.
    """

    reglamento: str | None = None
    sector: str | None = None
    articulos: list[str] | None = None
    idioma: Language | None = None


class Result(BaseModel):
    """Resultado individual de `search_corpus`.

    `cita` viene ya renderizada lista para mostrar al usuario; los campos
    crudos (`reglamento`, `articulo`, `apartado`) se exponen por si el caller
    necesita filtrar o agrupar.
    """

    cita: str  # "Reglamento UE 2024/1781, Art. 7.3"
    texto: str
    score: float  # similitud 0..1
    fuente_url: HttpUrl
    reglamento: str
    articulo: str
    apartado: str | None
    idioma: Language


def format_citation(fragment: Fragment) -> str:
    """Renderiza la cita canónica de un fragmento.

    Función pura compartida para garantizar que F2-01 (al persistir) y F2-03
    (al devolver resultados) producen exactamente la misma cadena.
    """
    base = f"Reglamento {fragment.reglamento}, Art. {fragment.articulo}"
    return f"{base}.{fragment.apartado}" if fragment.apartado else base


def search_corpus(
    query: str,
    top_k: int = 5,
    filters: Filters | None = None,
) -> list[Result]:
    """Recupera fragmentos del corpus por similitud semántica.

    Implementación pendiente — la entrega F2-03 sustituye este stub.
    F2-04 puede importar la firma desde ya para escribir tests.
    """
    raise NotImplementedError("Implementación pendiente — ver ticket F2-03.")
