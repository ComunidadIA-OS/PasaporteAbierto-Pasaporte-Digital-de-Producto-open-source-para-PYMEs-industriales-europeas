"""Tests de scripts/rag_quality_badge.py."""

import json
from pathlib import Path

from scripts.rag_quality_badge import (
    BADGE_END,
    BADGE_START,
    build_badge_markdown,
    summarize_pytest_report,
    update_readme,
)


def test_summarize_all_xfailed(tmp_path: Path) -> None:
    report = {
        "tests": [
            {"outcome": "xfailed"},
            {"outcome": "xfailed"},
            {"outcome": "xfailed"},
        ]
    }
    report_path = tmp_path / "rag.json"
    report_path.write_text(json.dumps(report))

    summary = summarize_pytest_report(report_path)
    assert summary.total == 3
    assert summary.passed == 0
    assert summary.xfailed == 3
    assert summary.status == "pending"


def test_summarize_mixed(tmp_path: Path) -> None:
    report = {
        "tests": [
            {"outcome": "passed"},
            {"outcome": "passed"},
            {"outcome": "passed"},
            {"outcome": "xfailed"},
        ]
    }
    report_path = tmp_path / "rag.json"
    report_path.write_text(json.dumps(report))

    summary = summarize_pytest_report(report_path)
    assert summary.total == 4
    assert summary.passed == 3
    assert summary.failed == 0
    assert summary.status == "warn"  # 75% < 80%


def test_summarize_all_passed(tmp_path: Path) -> None:
    report = {"tests": [{"outcome": "passed"} for _ in range(10)]}
    report_path = tmp_path / "rag.json"
    report_path.write_text(json.dumps(report))

    summary = summarize_pytest_report(report_path)
    assert summary.status == "ok"
    assert summary.accuracy_percent == 100


def test_build_badge_pending() -> None:
    md = build_badge_markdown(status="pending", percent=None)
    assert "pendiente" in md.lower()
    assert "F2--03" in md


def test_build_badge_ok() -> None:
    md = build_badge_markdown(status="ok", percent=87)
    assert "87" in md
    assert "brightgreen" in md or "green" in md


def test_update_readme_replaces_between_markers(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        f"Hola\n{BADGE_START}\nbadge viejo\n{BADGE_END}\nResto\n",
        encoding="utf-8",
    )

    update_readme(readme, new_badge_markdown="badge nuevo")

    contenido = readme.read_text(encoding="utf-8")
    assert "badge viejo" not in contenido
    assert "badge nuevo" in contenido
    assert "Hola" in contenido and "Resto" in contenido


def test_update_readme_idempotent(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        f"{BADGE_START}\nbadge\n{BADGE_END}\n",
        encoding="utf-8",
    )

    update_readme(readme, new_badge_markdown="badge")
    first = readme.read_text(encoding="utf-8")
    update_readme(readme, new_badge_markdown="badge")
    second = readme.read_text(encoding="utf-8")

    assert first == second
