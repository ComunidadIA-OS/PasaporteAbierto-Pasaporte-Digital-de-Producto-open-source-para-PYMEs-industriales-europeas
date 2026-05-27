"""Tests de calidad del retrieval — F2-04."""

from dataclasses import dataclass

import pytest

from app.rag import search_corpus
from app.rag.eval import DatasetEntry, load_queries, render_expected_citation
from app.rag.schema import Filters


@dataclass
class EvalSummary:
    total: int
    correct: int

    @property
    def top3_accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0


def _expected_in_results(entry: DatasetEntry, citations: list[str]) -> bool:
    expected = render_expected_citation(entry.expected_citation)
    return any(expected in c for c in citations)


@pytest.mark.parametrize("entry", load_queries(), ids=lambda e: e.id)
def test_expected_citation_in_top3(entry: DatasetEntry) -> None:
    results = search_corpus(
        entry.query,
        top_k=3,
        filters=Filters(idioma=entry.idioma),
    )
    citations = [r.cita for r in results]
    assert _expected_in_results(entry, citations), (
        f"Esperado '{render_expected_citation(entry.expected_citation)}' en top-3, "
        f"obtenido: {citations}"
    )


def test_top3_accuracy_over_80_percent() -> None:
    entries = load_queries()
    correct = 0
    for entry in entries:
        results = search_corpus(
            entry.query,
            top_k=3,
            filters=Filters(idioma=entry.idioma),
        )
        citations = [r.cita for r in results]
        if _expected_in_results(entry, citations):
            correct += 1
    summary = EvalSummary(total=len(entries), correct=correct)
    assert (
        summary.top3_accuracy >= 0.80
    ), f"Top-3 accuracy = {summary.top3_accuracy:.0%}, esperado ≥80%"
