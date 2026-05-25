"""Tests de calidad del retrieval — F2-04.

Estos tests llaman al stub `search_corpus()` definido en
`app.rag.schema`. Hasta que F2-03 implemente la versión real, el
stub lanza `NotImplementedError` → cada test cae como `xfail`.

Cuando F2-03 mergee a develop y entre a esta rama, los tests pasarán
automáticamente y aparecerán como `XPASS`. En ese momento se retira
la marca `xfail` en un PR puente.

Por qué `strict=False`: queremos que CI siga verde cuando los tests
pasen (XPASS) sin que el equipo tenga que rebotar al test runner.
"""

from dataclasses import dataclass

import pytest

from app.rag.eval import DatasetEntry, load_queries, render_expected_citation
from app.rag.schema import Filters, search_corpus

XFAIL_REASON = (
    "Requiere F2-03 (search_corpus implementado). " "Retirar marca al mergear F2-03 a develop."
)


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


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
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


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
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
