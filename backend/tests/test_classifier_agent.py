"""Tests del agente Clasificador (F3-01).

Mockea `search_corpus` y `complete` para correr rápido. La calidad real
contra LLM + corpus se valida en un test de integración aparte (no aquí).
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from app.classifier import classify
from app.classifier.agent import CONFIDENCE_THRESHOLD
from app.llm import LLMBackendError, LLMResponse
from app.rag.schema import Result


def _result(reglamento: str, articulo: str, apartado: str | None = None) -> Result:
    """Construye un Result válido para tests."""
    return Result(
        cita=f"Reglamento {reglamento}, Art. {articulo}",
        texto=(
            "Los productores facilitarán a los consumidores información clara sobre "
            "la batería, su composición y desempeño."
        ),
        score=0.9,
        fuente_url="https://eur-lex.europa.eu/eli/reg/2023/1542",
        reglamento=reglamento,
        articulo=articulo,
        apartado=apartado,
        idioma="es",
    )


def _llm_json(payload: dict[str, Any]) -> LLMResponse:
    return LLMResponse(
        content=json.dumps(payload),
        tokens_in=10,
        tokens_out=20,
        model="ollama/qwen2.5:14b",
        backend="ollama:qwen2.5:14b",
    )


def _patch_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    fragments: list[Result],
    llm_response: LLMResponse | Exception,
) -> None:
    monkeypatch.setattr("app.classifier.agent.search_corpus", lambda *a, **kw: fragments)

    def _complete(prompt: str, **kw: Any) -> LLMResponse:
        if isinstance(llm_response, Exception):
            raise llm_response
        return llm_response

    monkeypatch.setattr("app.classifier.agent.complete", _complete)


# ─── golden + confianza ──────────────────────────────────────────────────────


def test_classifies_batteries_with_high_confidence(monkeypatch: pytest.MonkeyPatch) -> None:
    fragments = [_result("UE 2023/1542", "77", "1")]
    _patch_dependencies(
        monkeypatch,
        fragments=fragments,
        llm_response=_llm_json(
            {
                "sector": "batteries",
                "confidence": 0.92,
                "fragment_index": 0,
                "reasoning": "Producto descrito como batería Li-ion industrial.",
            }
        ),
    )

    result = classify("Batería industrial recargable Li-ion 5 kWh para almacenamiento residencial")

    assert result.sector == "batteries"
    assert result.plugin == "batteries"
    assert result.confidence == pytest.approx(0.92)
    assert result.requires_review is False
    assert result.citation_regulation == "Reglamento UE 2023/1542"
    assert result.citation_article == "Art. 77.1"
    assert result.citation_url is not None


def test_low_confidence_triggers_review(monkeypatch: pytest.MonkeyPatch) -> None:
    fragments = [_result("UE 2023/1542", "77")]
    _patch_dependencies(
        monkeypatch,
        fragments=fragments,
        llm_response=_llm_json(
            {"sector": "batteries", "confidence": 0.5, "fragment_index": 0, "reasoning": "x"}
        ),
    )

    result = classify("dispositivo con celdas electroquímicas")

    assert result.sector == "batteries"
    assert result.confidence == 0.5
    assert result.confidence < CONFIDENCE_THRESHOLD
    assert result.requires_review is True


# ─── anti-alucinación y robustez ─────────────────────────────────────────────


def test_unknown_sector_is_forced_to_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    """Si el LLM devuelve un sector no instalado, no inventamos cita."""
    fragments = [_result("UE 2024/1781", "1")]
    _patch_dependencies(
        monkeypatch,
        fragments=fragments,
        llm_response=_llm_json(
            {"sector": "aircraft", "confidence": 0.95, "fragment_index": 0, "reasoning": "x"}
        ),
    )

    result = classify("turbina de avión")

    assert result.sector == "unknown"
    assert result.plugin == "unknown"
    assert result.confidence == 0.0
    assert result.requires_review is True
    assert result.citation_regulation == "N/A"


def test_invalid_json_from_llm_degrades_to_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    fragments = [_result("UE 2023/1542", "77")]
    _patch_dependencies(
        monkeypatch,
        fragments=fragments,
        llm_response=LLMResponse(
            content="no soy json", tokens_in=1, tokens_out=1, model="x", backend="y"
        ),
    )

    result = classify("descripción cualquiera con suficiente longitud para pasar validación")
    assert result.sector == "unknown"
    assert result.requires_review is True


def test_json_inside_markdown_fences_is_still_parsed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Los LLMs a veces envuelven el JSON en ```json ... ```. Tolerar."""
    fragments = [_result("UE 2023/1542", "77")]
    content = (
        '```json\n{"sector":"batteries","confidence":0.88,"fragment_index":0,"reasoning":"r"}\n```'
    )
    _patch_dependencies(
        monkeypatch,
        fragments=fragments,
        llm_response=LLMResponse(
            content=content, tokens_in=1, tokens_out=1, model="x", backend="y"
        ),
    )

    result = classify("Batería de litio para vehículo eléctrico ligero")
    assert result.sector == "batteries"
    assert result.confidence == pytest.approx(0.88)


def test_llm_backend_error_degrades_to_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    fragments = [_result("UE 2023/1542", "77")]
    _patch_dependencies(
        monkeypatch,
        fragments=fragments,
        llm_response=LLMBackendError("backend caído", backend="ollama:qwen2.5:14b"),
    )

    result = classify("batería industrial")
    assert result.sector == "unknown"
    assert result.requires_review is True


def test_out_of_range_fragment_index_falls_back_to_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fragments = [_result("UE 2023/1542", "77"), _result("UE 2024/1781", "1")]
    _patch_dependencies(
        monkeypatch,
        fragments=fragments,
        llm_response=_llm_json(
            {"sector": "batteries", "confidence": 0.9, "fragment_index": 99, "reasoning": "x"}
        ),
    )

    result = classify("Batería industrial Li-ion 5 kWh")
    # Cae al fragmento 0 (más relevante) en lugar de inventar cita.
    assert result.citation_article == "Art. 77"


def test_no_fragments_caps_confidence_and_forces_review(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Si el RAG no devuelve nada, no hay cita real → confianza degradada."""
    _patch_dependencies(
        monkeypatch,
        fragments=[],
        llm_response=_llm_json(
            {"sector": "batteries", "confidence": 0.95, "fragment_index": 0, "reasoning": "x"}
        ),
    )

    result = classify("Batería industrial Li-ion")
    assert result.sector == "batteries"
    assert result.confidence <= 0.6
    assert result.requires_review is True
    assert result.citation_article == "N/A"


def test_rag_exception_does_not_propagate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Si ChromaDB no está disponible, degradar sin romper la API."""

    def _raise(*a: Any, **kw: Any) -> list[Result]:
        raise RuntimeError("chroma down")

    monkeypatch.setattr("app.classifier.agent.search_corpus", _raise)
    monkeypatch.setattr(
        "app.classifier.agent.complete",
        lambda *a, **kw: _llm_json(
            {"sector": "batteries", "confidence": 0.9, "fragment_index": 0, "reasoning": "x"}
        ),
    )

    result = classify("Batería industrial")
    # Sin fragmentos, confianza capada.
    assert result.requires_review is True


def test_annex_article_rendering(monkeypatch: pytest.MonkeyPatch) -> None:
    """'Annex XIII' con apartado '1.k' debe renderizar 'Annex XIII §1.k'."""
    fragments = [_result("UE 2023/1542", "Annex XIII", "1.k")]
    _patch_dependencies(
        monkeypatch,
        fragments=fragments,
        llm_response=_llm_json(
            {"sector": "batteries", "confidence": 0.9, "fragment_index": 0, "reasoning": "x"}
        ),
    )

    result = classify("Batería industrial Li-ion")
    assert result.citation_article == "Annex XIII §1.k"
