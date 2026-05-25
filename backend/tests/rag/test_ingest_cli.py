"""Tests del CLI `python -m app.rag.ingest`."""

from pathlib import Path

from pydantic import HttpUrl

from app.rag.ingest.__main__ import build_parser, run_ingest
from app.rag.schema import Fragment


def _sample_fragment(reglamento: str, idioma: str) -> Fragment:
    return Fragment(
        texto=f"texto {reglamento} {idioma}",
        reglamento=reglamento,
        articulo="1",
        apartado="1",
        idioma=idioma,
        fuente_url=HttpUrl("https://eur-lex.europa.eu/"),
        sector=None,
    )


def test_parser_accepts_known_flags() -> None:
    parser = build_parser()
    args = parser.parse_args(["--force-refresh", "--only", "ue-2024-1781", "--lang", "es"])
    assert args.force_refresh is True
    assert args.only == ["ue-2024-1781"]
    assert args.lang == "es"


def test_parser_only_is_repeatable() -> None:
    parser = build_parser()
    args = parser.parse_args(["--only", "ue-2024-1781", "--only", "iso-15459"])
    assert args.only == ["ue-2024-1781", "iso-15459"]


def test_run_ingest_writes_jsonl_per_source(tmp_path: Path, monkeypatch) -> None:
    # Monkeypatch las sources para no tocar la red.
    def fake_eurlex_espr(*_a, **_kw):
        return iter([_sample_fragment("UE 2024/1781", "es")])

    def fake_eurlex_baterias(*_a, **_kw):
        return iter([_sample_fragment("UE 2023/1542", "es")])

    def fake_iso(idioma):
        return iter([_sample_fragment("ISO/IEC 15459", idioma)])

    monkeypatch.setattr(
        "app.rag.ingest.__main__.SOURCES",
        [
            ("ue-2024-1781", lambda client, lang, force_refresh: fake_eurlex_espr()),
            ("ue-2023-1542", lambda client, lang, force_refresh: fake_eurlex_baterias()),
            ("iso-15459", lambda client, lang, force_refresh: fake_iso(lang)),
        ],
    )

    exit_code = run_ingest(
        output_dir=tmp_path,
        cache_dir=tmp_path / "_raw",
        force_refresh=False,
        only=None,
        lang=None,
    )

    assert exit_code == 0
    assert (tmp_path / "ue-2024-1781.es.jsonl").exists()
    assert (tmp_path / "ue-2023-1542.es.jsonl").exists()
    assert (tmp_path / "iso-15459.es.jsonl").exists()
    assert (tmp_path / "iso-15459.en.jsonl").exists()


def test_run_ingest_filters_by_only(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.rag.ingest.__main__.SOURCES",
        [
            (
                "ue-2024-1781",
                lambda client, lang, force_refresh: iter([_sample_fragment("UE 2024/1781", "es")]),
            ),
            (
                "iso-15459",
                lambda client, lang, force_refresh: iter([_sample_fragment("ISO/IEC 15459", lang)]),
            ),
        ],
    )

    exit_code = run_ingest(
        output_dir=tmp_path,
        cache_dir=tmp_path / "_raw",
        force_refresh=False,
        only=["iso-15459"],
        lang="en",
    )
    assert exit_code == 0
    assert (tmp_path / "iso-15459.en.jsonl").exists()
    assert not (tmp_path / "ue-2024-1781.es.jsonl").exists()
    assert not (tmp_path / "iso-15459.es.jsonl").exists()


def test_run_ingest_returns_1_on_network_failure(tmp_path: Path, monkeypatch) -> None:
    import httpx

    def boom(*_a, **_kw):
        raise httpx.ConnectError("network down")

    monkeypatch.setattr(
        "app.rag.ingest.__main__.SOURCES",
        [
            ("ue-2024-1781", boom),
            (
                "iso-15459",
                lambda client, lang, force_refresh: iter([_sample_fragment("ISO/IEC 15459", lang)]),
            ),
        ],
    )

    exit_code = run_ingest(
        output_dir=tmp_path,
        cache_dir=tmp_path / "_raw",
        force_refresh=False,
        only=None,
        lang="es",
    )
    assert exit_code == 1  # red caída en una source pero el resto continuó
    assert (tmp_path / "iso-15459.es.jsonl").exists()


def test_run_ingest_returns_2_on_parser_error(tmp_path: Path, monkeypatch) -> None:
    from app.rag.ingest.sources.eurlex import IngestParseError

    def boom(*_a, **_kw):
        raise IngestParseError("EUR-Lex changed structure")

    monkeypatch.setattr(
        "app.rag.ingest.__main__.SOURCES",
        [("ue-2024-1781", boom)],
    )

    exit_code = run_ingest(
        output_dir=tmp_path,
        cache_dir=tmp_path / "_raw",
        force_refresh=False,
        only=None,
        lang="es",
    )
    assert exit_code == 2
