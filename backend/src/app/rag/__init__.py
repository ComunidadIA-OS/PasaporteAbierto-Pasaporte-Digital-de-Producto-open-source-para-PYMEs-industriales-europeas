"""Módulo RAG: ingesta del corpus normativo, indexado y retrieval.

Contrato compartido entre los tickets F2-01 a F2-04. Las implementaciones
viven en módulos separados; este paquete solo expone los tipos y la firma
de `search_corpus` para que F2-01 y F2-02/03/04 puedan trabajar en paralelo.
"""

from app.rag.retrieval import search_corpus
from app.rag.schema import (
    Filters,
    Fragment,
    Language,
    Result,
    format_citation,
)

__all__ = [
    "Filters",
    "Fragment",
    "Language",
    "Result",
    "format_citation",
    "search_corpus",
]
