"""Tests de la source CIRPASS-2 Core Ontology."""

from pathlib import Path

from app.rag.ingest.sources.cirpass import parse_cirpass_jsonld
from app.rag.schema import Fragment, format_citation


def test_each_class_becomes_a_fragment(fixtures_dir: Path) -> None:
    payload = (fixtures_dir / "cirpass_core.jsonld").read_text(encoding="utf-8")
    fragments = list(parse_cirpass_jsonld(payload))

    assert len(fragments) == 3
    labels = {f.articulo for f in fragments}
    assert labels == {"Product", "Material", "ConformityDocument"}
    for f in fragments:
        assert isinstance(f, Fragment)
        assert f.reglamento == "CIRPASS-2 Core"
        assert f.idioma == "en"
        assert f.sector is None
        assert f.apartado is None
        assert f.texto, "texto no vacío (label + comment)"


def test_cita_renderable(fixtures_dir: Path) -> None:
    payload = (fixtures_dir / "cirpass_core.jsonld").read_text(encoding="utf-8")
    fragments = list(parse_cirpass_jsonld(payload))
    cita = format_citation(fragments[0])
    assert cita.startswith("Reglamento CIRPASS-2 Core, Art. ")


def test_skips_entries_without_label_or_comment() -> None:
    payload = """
    {
      "@graph": [
        {"@id": "x", "label": "Foo"},
        {"@id": "y", "label": "Bar", "comment": "valid"}
      ]
    }
    """
    fragments = list(parse_cirpass_jsonld(payload))
    assert len(fragments) == 1
    assert fragments[0].articulo == "Bar"
