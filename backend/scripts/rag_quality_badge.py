"""Genera el badge de calidad RAG y lo inserta en el README raíz.

Uso:
    cd backend && uv run pytest tests/rag/test_retrieval_quality.py \
        --json-report --json-report-file=/tmp/rag.json
    cd backend && uv run python -m scripts.rag_quality_badge \
        --report /tmp/rag.json --readme ../README.md
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

BADGE_START = "<!-- RAG_QUALITY_BADGE:START -->"
BADGE_END = "<!-- RAG_QUALITY_BADGE:END -->"

Status = Literal["pending", "ok", "warn", "fail"]


@dataclass
class Summary:
    total: int
    passed: int
    failed: int
    xfailed: int
    xpassed: int

    @property
    def accuracy_percent(self) -> int:
        return round(100 * self.passed / self.total) if self.total else 0

    @property
    def status(self) -> Status:
        if self.failed:
            return "fail"
        if self.passed == 0 and self.xfailed > 0:
            return "pending"
        if self.accuracy_percent >= 80:
            return "ok"
        return "warn"


def summarize_pytest_report(report_path: Path) -> Summary:
    data = json.loads(report_path.read_text(encoding="utf-8"))
    tests = data.get("tests", [])
    counts = {"passed": 0, "failed": 0, "xfailed": 0, "xpassed": 0}
    for t in tests:
        outcome = t.get("outcome", "")
        if outcome in counts:
            counts[outcome] += 1
    return Summary(total=len(tests), **counts)


def build_badge_markdown(*, status: Status, percent: int | None) -> str:
    if status == "pending":
        return (
            "![RAG quality](https://img.shields.io/badge/RAG_quality-pendiente_(F2--03)-lightgrey)"
        )
    if status == "fail":
        return "![RAG quality](https://img.shields.io/badge/RAG_quality-failing-red)"
    color = "brightgreen" if status == "ok" else "yellow"
    return f"![RAG quality](https://img.shields.io/badge/RAG_quality-{percent}%25_top--3-{color})"


def update_readme(readme_path: Path, *, new_badge_markdown: str) -> None:
    text = readme_path.read_text(encoding="utf-8")
    if BADGE_START not in text or BADGE_END not in text:
        raise SystemExit(
            f"README sin marcadores {BADGE_START} / {BADGE_END}. "
            "Insertarlos manualmente una vez antes de invocar este script."
        )
    pre, rest = text.split(BADGE_START, 1)
    _, post = rest.split(BADGE_END, 1)
    new_text = f"{pre}{BADGE_START}\n{new_badge_markdown}\n{BADGE_END}{post}"
    if new_text != text:
        readme_path.write_text(new_text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Genera el badge RAG e inserta en README.")
    parser.add_argument("--report", type=Path, required=True, help="Ruta al pytest-json-report.")
    parser.add_argument("--readme", type=Path, required=True, help="README a actualizar.")
    args = parser.parse_args(argv)

    summary = summarize_pytest_report(args.report)
    percent = summary.accuracy_percent if summary.status in {"ok", "warn"} else None
    badge = build_badge_markdown(status=summary.status, percent=percent)
    update_readme(args.readme, new_badge_markdown=badge)
    print(f"RAG quality badge: status={summary.status} percent={percent} → {args.readme}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
