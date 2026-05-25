"""Servicio de retrieval del corpus normativo (F2-03).

Implementa `search_corpus`, el único punto de entrada que usarán los
agentes IA (Clasificador, Recolector, Chat). Traduce los filtros
estructurados de `Filters` a una cláusula `where` de ChromaDB y devuelve
`Result` con la cita ya renderizada y lista para mostrar.

Decorado con `@observe(name="rag.search_corpus")` para que aparezca como
span de Langfuse anidado dentro del span padre del componente que llame —
auto-nesting vía contextvars, sin pasar trace_id explícito.
"""

from langfuse.decorators import observe

from app.rag.index import query as index_query
from app.rag.schema import Filters, Fragment, Result, format_citation


def _build_where(filters: Filters | None) -> dict | None:
    """Traduce `Filters` a la cláusula `where` de ChromaDB.

    - `reglamento` e `idioma` se combinan como igualdad exacta.
    - `articulos` usa `$in` para aceptar varios artículos.
    - `sector="batteries"` incluye también fragmentos transversales
      (almacenados como `sector=""` por convención del índice). Si el
      caller quiere "solo sector-específico", debe filtrar a posteriori.
    """
    if filters is None:
        return None

    clauses: list[dict] = []
    if filters.reglamento:
        clauses.append({"reglamento": filters.reglamento})
    if filters.idioma:
        clauses.append({"idioma": filters.idioma})
    if filters.articulos:
        clauses.append({"articulo": {"$in": list(filters.articulos)}})
    if filters.sector:
        clauses.append({"$or": [{"sector": filters.sector}, {"sector": ""}]})

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _to_result(fragment: Fragment, score: float) -> Result:
    """Convierte `(Fragment, score)` a `Result` con cita renderizada."""
    return Result(
        cita=format_citation(fragment),
        texto=fragment.texto,
        score=score,
        fuente_url=fragment.fuente_url,
        reglamento=fragment.reglamento,
        articulo=fragment.articulo,
        apartado=fragment.apartado,
        idioma=fragment.idioma,
    )


@observe(name="rag.search_corpus")
def search_corpus(
    query: str,
    top_k: int = 5,
    filters: Filters | None = None,
) -> list[Result]:
    """Recupera fragmentos del corpus por similitud semántica.

    Implementación de F2-03 del stub declarado en `app.rag.schema`.
    """
    where = _build_where(filters)
    hits = index_query(query, top_k=top_k, where=where)
    return [_to_result(fragment, score) for fragment, score in hits]
