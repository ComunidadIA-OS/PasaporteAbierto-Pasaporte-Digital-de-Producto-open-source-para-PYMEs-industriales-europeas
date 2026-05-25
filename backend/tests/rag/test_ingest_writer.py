"""Tests del writer JSONL idempotente."""

from pathlib import Path

import pytest
from pydantic import HttpUrl

from app.rag.ingest.writer import write_jsonl
from app.rag.schema import Fragment


def _sample_fragments() -> list[Fragment]:
    return [
        Fragment(
            texto="Texto del artículo 7 apartado 1.",
            reglamento="UE 2024/1781",
            articulo="7",
            apartado="1",
            idioma="es",
            fuente_url=HttpUrl("https://eur-lex.europa.eu/eli/reg/2024/1781/oj"),
            sector=None,
        ),
        Fragment(
            texto="Texto del artículo 7 apartado 2.",
            reglamento="UE 2024/1781",
            articulo="7",
            apartado="2",
            idioma="es",
            fuente_url=HttpUrl("https://eur-lex.europa.eu/eli/reg/2024/1781/oj"),
            sector=None,
        ),
    ]


def test_atomic_write_idempotent(tmp_path: Path) -> None:
    out = tmp_path / "ue-2024-1781.es.jsonl"
    fragments = _sample_fragments()

    write_jsonl(out, fragments)
    first = out.read_bytes()

    write_jsonl(out, fragments)
    second = out.read_bytes()

    assert first == second, "Escribir dos veces el mismo input debe ser byte-a-byte idéntico"
    assert out.read_text().splitlines(keepends=False) != [""]
    assert len(out.read_text().splitlines()) == 2


def test_atomic_write_survives_crash(tmp_path: Path, monkeypatch) -> None:
    out = tmp_path / "ue-2024-1781.es.jsonl"
    write_jsonl(out, _sample_fragments())
    original = out.read_bytes()

    def boom(_src, _dst):
        raise OSError("simulated crash mid-write")

    monkeypatch.setattr("app.rag.ingest.writer.os.replace", boom)

    with pytest.raises(OSError, match="simulated crash"):
        write_jsonl(out, _sample_fragments())

    assert out.read_bytes() == original, "fichero previo debe sobrevivir cuando os.replace falla"
    # El tmp queda en disco; al re-ejecutar la operación normal se sobrescribe.


def test_write_empty_produces_empty_file(tmp_path: Path) -> None:
    out = tmp_path / "empty.es.jsonl"
    n = write_jsonl(out, [])
    assert n == 0
    assert out.exists()
    assert out.read_bytes() == b""
