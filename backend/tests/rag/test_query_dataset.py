"""Tests del dataset de queries F2-04. Corren siempre, NO xfail."""

from collections import Counter

from app.rag.eval import DatasetEntry, load_queries


def test_dataset_loads_and_validates() -> None:
    entries = load_queries()
    assert len(entries) >= 20, "F2-04 exige ≥20 queries"
    assert len(entries) <= 30, "F2-04 exige ≤30 queries"
    for e in entries:
        assert isinstance(e, DatasetEntry)


def test_dataset_no_duplicate_ids() -> None:
    entries = load_queries()
    ids = [e.id for e in entries]
    duplicates = [k for k, c in Counter(ids).items() if c > 1]
    assert not duplicates, f"IDs duplicados: {duplicates}"


def test_dataset_distribution_by_reglamento() -> None:
    entries = load_queries()
    by_reg = Counter(e.expected_citation.reglamento for e in entries)
    assert by_reg["UE 2024/1781"] >= 8, "≥8 queries sobre ESPR"
    assert by_reg["UE 2023/1542"] >= 8, "≥8 queries sobre baterías"
    assert by_reg["CIRPASS-2 Core"] >= 2, "≥2 sobre CIRPASS-2"
    assert by_reg["GS1 Digital Link 1.3.0"] >= 2, "≥2 sobre GS1"
    assert by_reg["ISO/IEC 15459"] >= 2, "≥2 sobre ISO 15459"


def test_dataset_batteries_covers_art77_or_annex_xiii() -> None:
    entries = load_queries()
    art77_or_annex = [
        e
        for e in entries
        if e.expected_citation.reglamento == "UE 2023/1542"
        and e.expected_citation.articulo in {"77", "Annex XIII"}
    ]
    assert len(art77_or_annex) >= 3, "≥3 queries sobre Art. 77 o Annex XIII de baterías"


def test_dataset_language_balance() -> None:
    entries = load_queries()
    by_lang = Counter(e.idioma for e in entries)
    total = len(entries)
    assert by_lang["es"] / total >= 0.40, "≥40% queries en castellano"
    assert by_lang["en"] / total >= 0.40, "≥40% queries en inglés"
