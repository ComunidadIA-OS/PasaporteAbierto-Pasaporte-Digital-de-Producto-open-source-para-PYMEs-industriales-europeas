"""Tests de la source GS1 Digital Link."""

from pathlib import Path

from app.rag.ingest.sources.gs1 import parse_gs1_html
from app.rag.schema import Fragment, format_citation


def test_each_section_becomes_a_fragment(fixtures_dir: Path) -> None:
    html = (fixtures_dir / "gs1_digital_link.html").read_text(encoding="utf-8")
    fragments = list(parse_gs1_html(html))

    assert len(fragments) == 3
    articulos = sorted(f.articulo for f in fragments)
    assert articulos == ["sección 1", "sección 2", "sección 3"]
    for f in fragments:
        assert isinstance(f, Fragment)
        assert f.reglamento == "GS1 Digital Link 1.3.0"
        assert f.idioma == "en"
        assert f.sector is None


def test_section_content_includes_paragraphs(fixtures_dir: Path) -> None:
    html = (fixtures_dir / "gs1_digital_link.html").read_text(encoding="utf-8")
    fragments = list(parse_gs1_html(html))
    s2 = next(f for f in fragments if f.articulo == "sección 2")
    assert "URI Syntax" in s2.texto
    assert "primaryIdentifier" in s2.texto


def test_cita_renderable(fixtures_dir: Path) -> None:
    html = (fixtures_dir / "gs1_digital_link.html").read_text(encoding="utf-8")
    fragments = list(parse_gs1_html(html))
    cita = format_citation(fragments[0])
    assert cita == "Reglamento GS1 Digital Link 1.3.0, Art. sección 1"
