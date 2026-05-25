"""Evaluación del RAG: dataset de queries y métricas (F2-04)."""

from app.rag.eval.dataset import (
    DatasetEntry,
    ExpectedCitation,
    load_queries,
    render_expected_citation,
)

__all__ = [
    "DatasetEntry",
    "ExpectedCitation",
    "load_queries",
    "render_expected_citation",
]
