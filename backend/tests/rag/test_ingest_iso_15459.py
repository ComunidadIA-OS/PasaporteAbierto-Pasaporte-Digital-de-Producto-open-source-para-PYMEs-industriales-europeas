"""Tests de la source ISO/IEC 15459-1..6 (fragmentos-stub)."""

from app.rag.ingest.sources.iso_15459 import fetch_fragments
from app.rag.schema import Fragment


def test_six_parts_each_language() -> None:
    fragments_es = list(fetch_fragments(idioma="es"))
    fragments_en = list(fetch_fragments(idioma="en"))

    assert len(fragments_es) == 6
    assert len(fragments_en) == 6
    for f in fragments_es + fragments_en:
        assert isinstance(f, Fragment)
        assert f.reglamento == "ISO/IEC 15459"
        assert f.articulo.startswith("Part")
        assert "ISO" in f.texto
        assert "licencia" in f.texto.lower() or "license" in f.texto.lower()
        assert str(f.fuente_url).startswith("https://www.iso.org/")


def test_articulo_is_part_n() -> None:
    fragments = list(fetch_fragments(idioma="en"))
    articulos = sorted(f.articulo for f in fragments)
    assert articulos == ["Part 1", "Part 2", "Part 3", "Part 4", "Part 5", "Part 6"]


def test_sector_is_none() -> None:
    for f in fetch_fragments(idioma="es"):
        assert f.sector is None, "ISO 15459 es transversal, no sector-específica"


def test_format_citation_is_renderable() -> None:
    from app.rag.schema import format_citation

    fragments = list(fetch_fragments(idioma="es"))
    cita = format_citation(fragments[0])
    assert cita.startswith("Reglamento ISO/IEC 15459, Art. Part ")
