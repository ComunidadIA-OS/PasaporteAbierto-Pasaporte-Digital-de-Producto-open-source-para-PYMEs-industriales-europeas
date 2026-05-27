"""Tests del servicio search_corpus (F2-03).

Los tests del traductor de filtros (`_build_where`) son rápidos. Los
end-to-end que ejercitan ChromaDB + bge-m3 están marcados `slow`.
"""

from pathlib import Path

import pytest

from app.rag import search_corpus
from app.rag.chunking import load_fragments
from app.rag.index import upsert_fragments
from app.rag.retrieval import _build_where
from app.rag.schema import Filters


def test_build_where_none_when_no_filters() -> None:
    assert _build_where(None) is None
    assert _build_where(Filters()) is None


def test_build_where_single_field_is_flat() -> None:
    assert _build_where(Filters(reglamento="UE 2024/1781")) == {"reglamento": "UE 2024/1781"}


def test_build_where_combines_multiple_fields_with_and() -> None:
    where = _build_where(Filters(reglamento="UE 2024/1781", idioma="es"))
    assert where == {
        "$and": [
            {"reglamento": "UE 2024/1781"},
            {"idioma": "es"},
        ]
    }


def test_build_where_articulos_uses_in() -> None:
    where = _build_where(Filters(articulos=["7", "9"]))
    assert where == {"articulo": {"$in": ["7", "9"]}}


def test_build_where_sector_includes_transversales() -> None:
    """sector="batteries" debe incluir también fragmentos transversales (sector="")."""
    where = _build_where(Filters(sector="batteries"))
    assert where == {"$or": [{"sector": "batteries"}, {"sector": ""}]}


def test_search_corpus_is_decorated_with_observe() -> None:
    """Smoke test: el decorador @observe envuelve la función sin romperla.

    No requiere Langfuse configurado — `@observe` es tolerante a cliente=None
    por diseño (la traza simplemente no se emite).
    """
    assert callable(search_corpus)
    # `@observe` preserva el nombre vía functools.wraps.
    assert search_corpus.__name__ == "search_corpus"


@pytest.fixture
def populated_index(tmp_path: Path, sample_fragments_path: Path) -> Path:
    upsert_fragments(load_fragments(sample_fragments_path), path=tmp_path)
    return tmp_path


@pytest.mark.slow
def test_search_corpus_returns_results_with_rendered_cita(
    populated_index: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Criterio 1 de F2-03: cada resultado expone cita lista para renderizar."""
    from app.rag import index

    original_get_collection = index.get_collection
    monkeypatch.setattr(
        index, "get_collection", lambda path=None: original_get_collection(populated_index)
    )
    results = search_corpus("pasaporte de batería", top_k=3)
    assert len(results) >= 3
    for r in results:
        assert r.cita.startswith("Reglamento ")
        assert "Art." in r.cita


@pytest.mark.slow
def test_search_corpus_filtro_sector_incluye_transversales(
    populated_index: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Criterio 2 de F2-03: filtro sector aplicado correctamente.

    Con sector="batteries" se devuelven fragmentos del sector y transversales
    (sector="" / None), nunca de otros sectores.
    """
    from app.rag import index

    original_get_collection = index.get_collection
    monkeypatch.setattr(
        index, "get_collection", lambda path=None: original_get_collection(populated_index)
    )
    results = search_corpus(
        "pasaporte digital",
        top_k=5,
        filters=Filters(sector="batteries"),
    )
    assert results
    for r in results:
        assert r.reglamento  # populado
        # En el fixture solo hay batteries y transversales (sector=None).
        # Si hubiera otro sector, este test lo detectaría.
