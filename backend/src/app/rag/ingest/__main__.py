"""CLI `python -m app.rag.ingest`."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Literal

import httpx

from app.rag.ingest.http_cache import CachedHttpClient
from app.rag.ingest.sources.eurlex import (
    KNOWN_DELEGATED_ACTS,
    IngestParseError,
    fetch_delegated_acts_fragments,
    fetch_regulation_fragments,
)
from app.rag.ingest.writer import write_jsonl
from app.rag.schema import Fragment, Language

logger = logging.getLogger("app.rag.ingest")


SourceFn = Callable[[CachedHttpClient, Language, bool], Iterable[Fragment]]


def _eurlex_espr(
    client: CachedHttpClient, lang: Language, force_refresh: bool
) -> Iterable[Fragment]:
    return fetch_regulation_fragments(
        client,
        celex="32024R1781",
        reglamento="UE 2024/1781",
        sector=None,
        force_refresh=force_refresh,
        languages=(lang,),
    )


def _eurlex_baterias(
    client: CachedHttpClient, lang: Language, force_refresh: bool
) -> Iterable[Fragment]:
    return fetch_regulation_fragments(
        client,
        celex="32023R1542",
        reglamento="UE 2023/1542",
        sector="batteries",
        force_refresh=force_refresh,
        languages=(lang,),
    )


def _actos_delegados(
    client: CachedHttpClient, lang: Language, force_refresh: bool
) -> Iterable[Fragment]:
    if not KNOWN_DELEGATED_ACTS:
        logger.info("No hay actos delegados ESPR registrados; se omite la source.")
        return iter(())
    return fetch_delegated_acts_fragments(client, force_refresh=force_refresh, languages=(lang,))


# El corpus RAG es exclusivamente normativo: solo texto citable como ley
# (reglamentos UE y sus actos delegados). El esquema del identificador
# (ISO/IEC 15459, GS1 Digital Link) y el vocabulario del DPP (CIRPASS-2 Core)
# NO viven aquí: los declara el plugin sectorial (`identifier_scheme`, campos)
# y los consume de forma determinista la generación del DPP y el Chat. Ver
# docs/tickets/F2.md y ARCHITECTURE.md §"Identificador único…".
SOURCES: list[tuple[str, SourceFn]] = [
    ("ue-2024-1781", _eurlex_espr),
    ("ue-2023-1542", _eurlex_baterias),
    ("actos-delegados", _actos_delegados),
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.rag.ingest",
        description="Pipeline de ingesta del corpus normativo (F2-01).",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Invalida cache HTTP y re-descarga todo.",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=None,
        help="Limita a un source concreto (slug). Repetible.",
    )
    parser.add_argument(
        "--lang",
        choices=["es", "en"],
        default=None,
        help="Limita a un idioma. Sin flag = ambos.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/corpus"),
        help="Directorio de JSONL. Default: data/corpus/",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("data/corpus/_raw"),
        help="Directorio del cache HTTP. Default: data/corpus/_raw/",
    )
    return parser


def run_ingest(
    *,
    output_dir: Path,
    cache_dir: Path,
    force_refresh: bool,
    only: list[str] | None,
    lang: Literal["es", "en"] | None,
) -> int:
    """Ejecuta el pipeline. Devuelve exit code (0/1/2)."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    languages: tuple[Language, ...] = ("es", "en") if lang is None else (lang,)
    selected = [(slug, fn) for slug, fn in SOURCES if only is None or slug in only]
    if only and not selected:
        logger.error("--only no coincide con ningún source conocido: %s", only)
        return 2

    client = CachedHttpClient(cache_dir=cache_dir)
    exit_code = 0

    try:
        for slug, fn in selected:
            for current_lang in languages:
                try:
                    fragments = list(fn(client, current_lang, force_refresh))
                except IngestParseError as exc:
                    logger.error("✗ %s.%s: regresión de parser (%s)", slug, current_lang, exc)
                    exit_code = max(exit_code, 2)
                    continue
                except (httpx.HTTPError, httpx.ConnectError) as exc:
                    logger.warning("⚠ %s.%s: red caída (%s); se salta", slug, current_lang, exc)
                    exit_code = max(exit_code, 1)
                    continue

                if not fragments:
                    logger.info(
                        "• %s.%s: sin fragments (idioma no soportado o lista vacía)",
                        slug,
                        current_lang,
                    )
                    continue

                out = output_dir / f"{slug}.{current_lang}.jsonl"
                n = write_jsonl(out, fragments)
                logger.info("✓ %s.%s: %d fragments", slug, current_lang, n)
    finally:
        client.close()

    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run_ingest(
        output_dir=args.output_dir,
        cache_dir=args.cache_dir,
        force_refresh=args.force_refresh,
        only=args.only,
        lang=args.lang,
    )


if __name__ == "__main__":
    sys.exit(main())
