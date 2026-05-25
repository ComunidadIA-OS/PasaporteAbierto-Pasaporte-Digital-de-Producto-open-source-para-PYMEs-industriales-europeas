"""Tests del parser EUR-Lex."""

from pathlib import Path

from pydantic import HttpUrl

from app.rag.ingest.sources.eurlex import parse_eurlex_html
from app.rag.schema import Fragment, format_citation


def _read(fixtures_dir: Path, name: str) -> str:
    return (fixtures_dir / name).read_text(encoding="utf-8")


def test_parse_espr_es_produces_articles(fixtures_dir: Path) -> None:
    html = _read(fixtures_dir, "eurlex_ue-2024-1781_es.html")
    fragments = list(
        parse_eurlex_html(
            html,
            reglamento="UE 2024/1781",
            idioma="es",
            fuente_url=HttpUrl(
                "https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:32024R1781"
            ),
            sector=None,
        )
    )

    # 3 artículos x apartados (2+3+1 = 6 apartados)
    assert len(fragments) == 6
    for f in fragments:
        assert isinstance(f, Fragment)
        assert f.reglamento == "UE 2024/1781"
        assert f.idioma == "es"
        assert f.sector is None
        assert f.articulo in {"1", "7", "9"}

    # Art. 7.3 (criterio de cita correcta)
    art_7_3 = next(f for f in fragments if f.articulo == "7" and f.apartado == "3")
    assert "actualizada" in art_7_3.texto.lower()
    assert format_citation(art_7_3) == "Reglamento UE 2024/1781, Art. 7.3"


def test_parse_espr_en_produces_articles(fixtures_dir: Path) -> None:
    html = _read(fixtures_dir, "eurlex_ue-2024-1781_en.html")
    fragments = list(
        parse_eurlex_html(
            html,
            reglamento="UE 2024/1781",
            idioma="en",
            fuente_url=HttpUrl(
                "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32024R1781"
            ),
            sector=None,
        )
    )
    assert len(fragments) == 6
    art_7_3 = next(f for f in fragments if f.articulo == "7" and f.apartado == "3")
    assert "up-to-date" in art_7_3.texto.lower() or "accurate" in art_7_3.texto.lower()


def test_parse_empty_html_raises(fixtures_dir: Path) -> None:
    import pytest

    from app.rag.ingest.sources.eurlex import IngestParseError

    big_html = "<html><body>" + ("<p>nope</p>" * 1000) + "</body></html>"  # >10 KB sin artículos
    with pytest.raises(IngestParseError):
        list(
            parse_eurlex_html(
                big_html,
                reglamento="UE 2024/1781",
                idioma="es",
                fuente_url=HttpUrl(
                    "https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:32024R1781"
                ),
                sector=None,
            )
        )


def test_parse_baterias_extracts_art77(fixtures_dir: Path) -> None:
    html = _read(fixtures_dir, "eurlex_ue-2023-1542_es.html")
    fragments = list(
        parse_eurlex_html(
            html,
            reglamento="UE 2023/1542",
            idioma="es",
            fuente_url=HttpUrl(
                "https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:32023R1542"
            ),
            sector="batteries",
        )
    )

    art77 = [f for f in fragments if f.articulo == "77"]
    assert len(art77) == 3, "Art. 77 tiene 3 apartados en la fixture"

    art77_3 = next(f for f in art77 if f.apartado == "3")
    assert (
        "ISO/IEC 15459" in art77_3.texto
    ), "Art. 77.3 debe citar ISO/IEC 15459 (cumplimiento Art. 77.3 del Reg.)"
    assert format_citation(art77_3) == "Reglamento UE 2023/1542, Art. 77.3"


def test_parse_baterias_extracts_annex_xiii(fixtures_dir: Path) -> None:
    html = _read(fixtures_dir, "eurlex_ue-2023-1542_es.html")
    fragments = list(
        parse_eurlex_html(
            html,
            reglamento="UE 2023/1542",
            idioma="es",
            fuente_url=HttpUrl(
                "https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:32023R1542"
            ),
            sector="batteries",
        )
    )
    annex = [f for f in fragments if f.articulo == "Annex XIII"]
    assert len(annex) == 2, "Annex XIII tiene 2 apartados en la fixture"
    assert format_citation(annex[0]) == "Reglamento UE 2023/1542, Art. Annex XIII.1"


def test_baterias_fragments_tagged_with_sector(fixtures_dir: Path) -> None:
    html = _read(fixtures_dir, "eurlex_ue-2023-1542_es.html")
    fragments = list(
        parse_eurlex_html(
            html,
            reglamento="UE 2023/1542",
            idioma="es",
            fuente_url=HttpUrl(
                "https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:32023R1542"
            ),
            sector="batteries",
        )
    )
    assert all(f.sector == "batteries" for f in fragments)


def test_espr_fragments_have_no_sector(fixtures_dir: Path) -> None:
    html = _read(fixtures_dir, "eurlex_ue-2024-1781_es.html")
    fragments = list(
        parse_eurlex_html(
            html,
            reglamento="UE 2024/1781",
            idioma="es",
            fuente_url=HttpUrl(
                "https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:32024R1781"
            ),
            sector=None,
        )
    )
    assert all(f.sector is None for f in fragments)


def test_parse_baterias_en_uses_annex_keyword(fixtures_dir: Path) -> None:
    html = _read(fixtures_dir, "eurlex_ue-2023-1542_en.html")
    fragments = list(
        parse_eurlex_html(
            html,
            reglamento="UE 2023/1542",
            idioma="en",
            fuente_url=HttpUrl(
                "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32023R1542"
            ),
            sector="batteries",
        )
    )
    annex = [f for f in fragments if f.articulo == "Annex XIII"]
    assert len(annex) == 2


def test_known_delegated_acts_have_well_formed_celex() -> None:
    import re

    from app.rag.ingest.sources.eurlex import KNOWN_DELEGATED_ACTS

    for act in KNOWN_DELEGATED_ACTS:
        assert re.match(r"^[0-9]{5}[A-Z][0-9]{4}$", act.celex), f"CELEX inválido: {act.celex}"
        assert act.reglamento
        assert act.slug.startswith("actos-delegados-")
        assert act.sector is None or isinstance(act.sector, str)


def test_known_delegated_acts_slug_uses_celex_lowercase() -> None:
    from app.rag.ingest.sources.eurlex import KNOWN_DELEGATED_ACTS

    for act in KNOWN_DELEGATED_ACTS:
        assert act.slug == f"actos-delegados-{act.celex.lower()}"
