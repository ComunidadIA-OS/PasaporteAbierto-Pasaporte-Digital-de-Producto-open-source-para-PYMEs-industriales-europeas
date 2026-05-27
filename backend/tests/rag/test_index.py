"""Tests del índice ChromaDB.

Marcados como `slow` porque dependen del modelo bge-m3. Cubren los tres
criterios de aceptación de F2-02:

1. Query devuelve ≥3 fragmentos relevantes en <500 ms (tras warmup).
2. Reindexar es idempotente: dos upserts no duplican.
3. Funciona en ES y EN sobre el mismo índice.
"""

import time
from pathlib import Path

import pytest

from app.rag.chunking import load_fragments
from app.rag.index import get_collection, query, upsert_fragments


@pytest.fixture
def populated_index(tmp_path: Path, sample_fragments_path: Path) -> Path:
    """Crea un índice temporal poblado con los 10 fragmentos de muestra."""
    upsert_fragments(load_fragments(sample_fragments_path), path=tmp_path)
    return tmp_path


@pytest.mark.slow
def test_upsert_is_idempotent(tmp_path: Path, sample_fragments_path: Path) -> None:
    """Criterio 2: reindexar dos veces no duplica."""
    upsert_fragments(load_fragments(sample_fragments_path), path=tmp_path)
    first_count = get_collection(tmp_path).count()

    upsert_fragments(load_fragments(sample_fragments_path), path=tmp_path)
    second_count = get_collection(tmp_path).count()

    assert first_count == second_count == 10


@pytest.mark.slow
def test_query_latency_under_500ms(populated_index: Path) -> None:
    """Criterio 1: ≥3 resultados en <500 ms (medido tras warmup)."""
    query("pasaporte de batería", top_k=3, path=populated_index)  # warmup

    start = time.perf_counter()
    results = query("identificador único", top_k=3, path=populated_index)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert len(results) >= 3
    assert elapsed_ms < 500, f"Latencia {elapsed_ms:.0f}ms supera 500ms"


@pytest.mark.slow
def test_query_works_in_es_and_en(populated_index: Path) -> None:
    """Criterio 3: queries en ES y EN sobre el mismo índice devuelven resultados."""
    results_es = query("pasaporte de producto", top_k=3, path=populated_index)
    results_en = query("digital product passport", top_k=3, path=populated_index)

    assert len(results_es) >= 3
    assert len(results_en) >= 3


@pytest.mark.slow
def test_query_returns_score_in_unit_range(populated_index: Path) -> None:
    """Score = 1 - distancia coseno, debe caer cerca de [0, 1]."""
    results = query("battery passport", top_k=3, path=populated_index)
    for _, score in results:
        assert -0.1 <= score <= 1.1, f"Score fuera de rango: {score}"


@pytest.mark.slow
def test_query_with_where_filter(populated_index: Path) -> None:
    """El parámetro `where` se propaga a ChromaDB y filtra metadata."""
    results = query(
        "pasaporte",
        top_k=5,
        where={"idioma": "en"},
        path=populated_index,
    )
    assert results
    for fragment, _ in results:
        assert fragment.idioma == "en"
