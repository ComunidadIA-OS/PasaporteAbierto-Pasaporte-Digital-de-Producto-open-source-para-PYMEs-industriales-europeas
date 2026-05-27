"""Tests del loader de fragmentos JSONL."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.rag.chunking import load_corpus, load_fragments
from app.rag.schema import Fragment


def test_load_fragments_returns_valid_fragments(sample_fragments_path: Path) -> None:
    fragments = list(load_fragments(sample_fragments_path))
    assert len(fragments) == 10
    assert all(isinstance(f, Fragment) for f in fragments)


def test_load_fragments_preserves_idiomas(sample_fragments_path: Path) -> None:
    fragments = list(load_fragments(sample_fragments_path))
    idiomas = {f.idioma for f in fragments}
    assert idiomas == {"es", "en"}


def test_load_fragments_skips_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "with_blanks.jsonl"
    path.write_text(
        '\n{"texto":"x","reglamento":"UE 2024/1781","articulo":"7",'
        '"idioma":"es","fuente_url":"https://eur-lex.europa.eu/x"}\n\n',
        encoding="utf-8",
    )
    assert len(list(load_fragments(path))) == 1


def test_load_fragments_rejects_invalid(tmp_path: Path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text('{"texto":"sin reglamento"}\n', encoding="utf-8")
    with pytest.raises(ValidationError):
        list(load_fragments(path))


def test_load_corpus_combines_multiple_files(tmp_path: Path) -> None:
    line = (
        '{{"texto":"f{i}","reglamento":"UE 2024/1781","articulo":"7",'
        '"idioma":"es","fuente_url":"https://eur-lex.europa.eu/x"}}\n'
    )
    (tmp_path / "a.jsonl").write_text(line.format(i=1), encoding="utf-8")
    (tmp_path / "b.jsonl").write_text(line.format(i=2), encoding="utf-8")
    assert len(list(load_corpus(tmp_path))) == 2
