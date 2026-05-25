# F2-01 + F2-04 · Corpus ingest + RAG tests — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar el pipeline reproducible `python -m app.rag.ingest` que descarga y parsea el corpus normativo europeo a JSONL de `Fragment`s, y la suite de calidad RAG F2-04 (dataset + tests xfail + badge), todo coordinado con el contrato compartido `backend/src/app/rag/schema.py`.

**Architecture:** Adaptadores por fuente bajo `backend/src/app/rag/ingest/sources/` (uno por origen: EUR-Lex, CIRPASS-2, GS1, ISO/IEC 15459). Cada source devuelve `Iterable[Fragment]`. El CLI los junta y los persiste atómicamente a `backend/data/corpus/{slug}.{lang}.jsonl`. Tests sobre fixtures HTML locales (sin red en CI). F2-04 escribe contra la firma del stub `search_corpus()` con `xfail(strict=False)` hasta que F2-03 aterrice.

**Tech Stack:** Python 3.11, httpx (ya en el proyecto), beautifulsoup4+lxml (nuevas), pydantic v2 (ya), pyyaml (ya), pytest (ya), pytest-json-report (nueva dev).

**Spec relacionado:** `docs/superpowers/specs/2026-05-25-f2-01-04-corpus-ingesta-tests.md`

**Contrato compartido (ya existe, no se toca):** `backend/src/app/rag/schema.py` con `Fragment`, `Filters`, `Result`, `Language`, `format_citation()`, stub `search_corpus()`.

---

## File Structure

### Crear

```
backend/
├── src/app/rag/ingest/
│   ├── __init__.py                       # T1
│   ├── __main__.py                       # T10 (CLI)
│   ├── writer.py                         # T2
│   ├── http_cache.py                     # T3
│   └── sources/
│       ├── __init__.py                   # T1 (registry)
│       ├── eurlex.py                     # T5, T6, T7
│       ├── cirpass.py                    # T8
│       ├── gs1.py                        # T9
│       └── iso_15459.py                  # T4
├── tests/rag/
│   ├── __init__.py                       # T1
│   ├── conftest.py                       # T1 (fixtures dir resolver)
│   ├── fixtures/
│   │   ├── eurlex_ue-2024-1781_es.html   # T5
│   │   ├── eurlex_ue-2024-1781_en.html   # T5
│   │   ├── eurlex_ue-2023-1542_es.html   # T6 (incluye Art. 77 + Annex XIII)
│   │   ├── eurlex_ue-2023-1542_en.html   # T6
│   │   ├── cirpass_core.jsonld           # T8
│   │   └── gs1_digital_link.html         # T9
│   ├── queries.yaml                      # T11 (dataset F2-04)
│   ├── test_ingest_writer.py             # T2
│   ├── test_ingest_http_cache.py         # T3
│   ├── test_ingest_iso_15459.py          # T4
│   ├── test_ingest_eurlex.py             # T5, T6, T7
│   ├── test_ingest_cirpass.py            # T8
│   ├── test_ingest_gs1.py                # T9
│   ├── test_ingest_cli.py                # T10
│   ├── test_query_dataset.py             # T12
│   └── test_retrieval_quality.py         # T13
├── scripts/
│   └── rag_quality_badge.py              # T14
└── (sin commitear)
    └── data/corpus/
        ├── _raw/...
        └── *.jsonl
```

### Modificar

- `backend/pyproject.toml` — añadir `beautifulsoup4`, `lxml`, `pytest-json-report`. (T1)
- `backend/.gitignore` — añadir `data/corpus/`. (T1)
- `README.md` (raíz) — insertar marcadores HTML del badge RAG. (T14)
- `Makefile` (raíz) — añadir target `make ingest`. (T10)

---

## Mapa tickets ↔ tareas

| Ticket | Tareas |
|---|---|
| F2-01 criterio 1 (`python -m ingest` desde cero) | T1, T2, T3, T10 |
| F2-01 criterio 2 (cita "Reglamento X, Art. Y" lista) | T2, T4, T5, T6, T8, T9 |
| F2-01 criterio 3 (corpus es + en) | T5, T6, T7, T10 |
| F2-04 criterio 1 (≥80% top-3) | T13 (xfail hasta F2-03) |
| F2-04 criterio 2 (`pytest tests/rag/` <60s) | T4, T12, T13 (xfail evita lentitud) |
| F2-04 criterio 3 (badge en README) | T14 |
| Cierre | T15 |

---

## Task 1: Setup — dependencias, .gitignore, módulo skeleton, conftest

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/.gitignore`
- Create: `backend/src/app/rag/ingest/__init__.py`
- Create: `backend/src/app/rag/ingest/sources/__init__.py`
- Create: `backend/tests/rag/__init__.py`
- Create: `backend/tests/rag/conftest.py`
- Create: `backend/tests/rag/fixtures/` (directorio vacío)

- [ ] **Step 1: Añadir deps a `backend/pyproject.toml`**

Editar `backend/pyproject.toml`. Reemplazar el array `dependencies` y `[dependency-groups].dev` por:

```toml
dependencies = [
    "fastapi==0.115.*",
    "uvicorn[standard]==0.32.*",
    "pydantic==2.*",
    "pydantic-settings==2.*",
    "sqlmodel==0.0.22",
    "alembic==1.13.*",
    "pyyaml==6.*",
    "litellm==1.52.*",
    "langfuse==2.*",
    "httpx==0.27.*",
    "beautifulsoup4==4.12.*",
    "lxml==5.*",
]

[dependency-groups]
dev = [
    "pytest==8.*",
    "pytest-asyncio==0.24.*",
    "ruff==0.7.*",
    "pytest-cov==5.*",
    "pytest-json-report==1.5.*",
]
```

- [ ] **Step 2: Resolver lockfile**

Run: `cd backend && uv sync`
Expected: `Resolved N packages`, instala beautifulsoup4, lxml, pytest-json-report.

- [ ] **Step 3: Verificar instalación**

Run: `cd backend && uv run python -c "import bs4, lxml; print(bs4.__version__, lxml.__version__)"`
Expected: imprime dos versiones (4.12.x y 5.x.x).

- [ ] **Step 4: Añadir `data/corpus/` a `.gitignore`**

Append a `backend/.gitignore`:

```
data/corpus/
```

- [ ] **Step 5: Crear `backend/src/app/rag/ingest/__init__.py`**

```python
"""Pipeline de ingesta del corpus normativo (F2-01).

Punto de entrada: `python -m app.rag.ingest`.
"""
```

- [ ] **Step 6: Crear `backend/src/app/rag/ingest/sources/__init__.py`**

```python
"""Adaptadores por fuente del corpus.

Cada módulo expone una función `fetch_fragments()` que devuelve
`Iterable[Fragment]`. Añadir un origen nuevo = un fichero nuevo aquí.
"""
```

- [ ] **Step 7: Crear `backend/tests/rag/__init__.py`** (fichero vacío)

```python
```

- [ ] **Step 8: Crear `backend/tests/rag/conftest.py`**

```python
"""Fixtures compartidos de tests RAG."""

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Directorio con fixtures HTML/JSON-LD reales recortados."""
    return Path(__file__).parent / "fixtures"
```

- [ ] **Step 9: Crear directorio de fixtures**

Run: `mkdir -p backend/tests/rag/fixtures`
Expected: directorio existe.

- [ ] **Step 10: Verificar que la suite existente sigue verde**

Run: `cd backend && uv run pytest -q`
Expected: todos los tests previos pasan; los nuevos directorios `tests/rag/` no tienen tests aún (pytest no falla).

- [ ] **Step 11: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock backend/.gitignore \
        backend/src/app/rag/ingest/ backend/tests/rag/__init__.py \
        backend/tests/rag/conftest.py
git commit -m "$(cat <<'EOF'
chore(rag): scaffold módulo de ingesta y suite tests/rag (F2-01)

Añade beautifulsoup4 + lxml para parsing HTML EUR-Lex y
pytest-json-report para el badge de calidad RAG. Crea el árbol
vacío `app/rag/ingest/{,sources}` y `tests/rag/{,fixtures}`.

data/corpus/ ignorado: el corpus es regenerable con
`python -m app.rag.ingest`, no es código fuente.
EOF
)"
```

---

## Task 2: `writer.py` — escritura atómica JSONL idempotente (TDD)

**Files:**
- Create: `backend/src/app/rag/ingest/writer.py`
- Test: `backend/tests/rag/test_ingest_writer.py`

- [ ] **Step 1: Escribir test `test_atomic_write_idempotent`**

Crear `backend/tests/rag/test_ingest_writer.py`:

```python
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
```

- [ ] **Step 2: Run test, verificar fallo**

Run: `cd backend && uv run pytest tests/rag/test_ingest_writer.py::test_atomic_write_idempotent -v`
Expected: `ModuleNotFoundError: No module named 'app.rag.ingest.writer'` o equivalente.

- [ ] **Step 3: Implementar `writer.py`**

Crear `backend/src/app/rag/ingest/writer.py`:

```python
"""Escritura atómica de JSONL de Fragments.

Una línea = un Fragment serializado con `model_dump_json()`. Escritura
atómica con `os.replace`: si la operación falla a medias, el fichero
previo (si existía) queda intacto.
"""

import os
from collections.abc import Iterable
from pathlib import Path

from app.rag.schema import Fragment


def write_jsonl(path: Path, fragments: Iterable[Fragment]) -> int:
    """Escribe `fragments` como JSONL en `path` de forma atómica.

    Devuelve el número de fragments escritos. El destino se crea si no
    existe; los directorios padre también.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    count = 0
    with tmp.open("w", encoding="utf-8") as fh:
        for fragment in fragments:
            fh.write(fragment.model_dump_json())
            fh.write("\n")
            count += 1
    os.replace(tmp, path)
    return count
```

- [ ] **Step 4: Run test, verificar pass**

Run: `cd backend && uv run pytest tests/rag/test_ingest_writer.py -v`
Expected: PASS.

- [ ] **Step 5: Añadir test `test_atomic_write_survives_crash`**

Append a `backend/tests/rag/test_ingest_writer.py`:

```python
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
```

- [ ] **Step 6: Run test, verificar pass**

Run: `cd backend && uv run pytest tests/rag/test_ingest_writer.py -v`
Expected: 2 passed.

- [ ] **Step 7: Añadir test `test_write_empty_produces_empty_file`**

Append:

```python
def test_write_empty_produces_empty_file(tmp_path: Path) -> None:
    out = tmp_path / "empty.es.jsonl"
    n = write_jsonl(out, [])
    assert n == 0
    assert out.exists()
    assert out.read_bytes() == b""
```

- [ ] **Step 8: Run test, verificar pass**

Run: `cd backend && uv run pytest tests/rag/test_ingest_writer.py -v`
Expected: 3 passed.

- [ ] **Step 9: Lint**

Run: `cd backend && uv run ruff check src/app/rag/ingest/writer.py tests/rag/test_ingest_writer.py && uv run ruff format src/app/rag/ingest/writer.py tests/rag/test_ingest_writer.py`
Expected: All checks passed. Formato sin cambios o aplicado.

- [ ] **Step 10: Commit**

```bash
git add backend/src/app/rag/ingest/writer.py backend/tests/rag/test_ingest_writer.py
git commit -m "$(cat <<'EOF'
feat(rag): writer JSONL atómico e idempotente (F2-01)

Escribe Fragments a `data/corpus/{slug}.{lang}.jsonl` con tmp +
os.replace. Si la operación falla a medias, el fichero previo
sobrevive. Reescribir el mismo input produce bytes idénticos.
EOF
)"
```

---

## Task 3: `http_cache.py` — cache HTTP con `--force-refresh` (TDD)

**Files:**
- Create: `backend/src/app/rag/ingest/http_cache.py`
- Test: `backend/tests/rag/test_ingest_http_cache.py`

- [ ] **Step 1: Escribir test `test_cache_hits_on_second_call`**

Crear `backend/tests/rag/test_ingest_http_cache.py`:

```python
"""Tests del cache HTTP del ingestor."""

from pathlib import Path

import httpx
import pytest

from app.rag.ingest.http_cache import CachedHttpClient


def test_cache_hits_on_second_call(tmp_path: Path) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, text="<html>hola</html>")

    transport = httpx.MockTransport(handler)
    client = CachedHttpClient(cache_dir=tmp_path, transport=transport, min_size=10)

    body1 = client.get_text("https://example.com/foo.html", cache_key="foo")
    body2 = client.get_text("https://example.com/foo.html", cache_key="foo")

    assert body1 == body2 == "<html>hola</html>"
    assert calls["n"] == 1, "segunda llamada debe ir a cache"
    assert (tmp_path / "foo").exists()


def test_force_refresh_bypasses_cache(tmp_path: Path) -> None:
    bodies = iter(["<html>v1</html>", "<html>v2</html>"])
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, text=next(bodies))

    transport = httpx.MockTransport(handler)
    client = CachedHttpClient(cache_dir=tmp_path, transport=transport, min_size=10)

    first = client.get_text("https://example.com/foo.html", cache_key="foo")
    second = client.get_text("https://example.com/foo.html", cache_key="foo", force_refresh=True)

    assert first == "<html>v1</html>"
    assert second == "<html>v2</html>"
    assert calls["n"] == 2


def test_retries_then_succeeds(tmp_path: Path) -> None:
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise httpx.ConnectError("flaky")
        return httpx.Response(200, text="ok")

    transport = httpx.MockTransport(handler)
    client = CachedHttpClient(cache_dir=tmp_path, transport=transport)
    body = client.get_text("https://example.com/foo.html", cache_key="foo")
    assert body == "ok"
    assert attempts["n"] == 3


def test_raises_after_max_retries(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("always down")

    transport = httpx.MockTransport(handler)
    client = CachedHttpClient(cache_dir=tmp_path, transport=transport)
    with pytest.raises(httpx.ConnectError):
        client.get_text("https://example.com/foo.html", cache_key="foo")


def test_corrupted_cache_is_redownloaded(tmp_path: Path) -> None:
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, text="<html>" + "x" * 5000 + "</html>")

    transport = httpx.MockTransport(handler)
    client = CachedHttpClient(cache_dir=tmp_path, transport=transport, min_size=100)

    (tmp_path / "foo").write_text("tiny")  # cache "corrupta": < min_size
    body = client.get_text("https://example.com/foo.html", cache_key="foo")

    assert calls["n"] == 1, "cache truncada debe descartarse y re-descargar"
    assert len(body) > 100
```

- [ ] **Step 2: Run tests, verificar fallo**

Run: `cd backend && uv run pytest tests/rag/test_ingest_http_cache.py -v`
Expected: ImportError de `app.rag.ingest.http_cache`.

- [ ] **Step 3: Implementar `http_cache.py`**

Crear `backend/src/app/rag/ingest/http_cache.py`:

```python
"""Cache HTTP en disco para descargas del corpus.

Política: GET texto, cache en disco bajo `cache_dir/<cache_key>`, validar
tamaño mínimo (descarta cache corrupta truncada). Reintentos con backoff
exponencial en errores de red.
"""

import time
from pathlib import Path

import httpx

DEFAULT_HEADERS = {
    "User-Agent": "PasaporteAbierto-corpus-ingest/0.1 (+https://github.com/ComunidadIA-OS/PasaporteAbierto-Pasaporte-Digital-de-Producto-open-source-para-PYMEs-industriales-europeas)",
    "Accept-Language": "es;q=1.0, en;q=0.9",
}


class CachedHttpClient:
    """Cliente httpx con cache en disco y reintentos."""

    def __init__(
        self,
        cache_dir: Path,
        *,
        transport: httpx.BaseTransport | None = None,
        max_retries: int = 3,
        backoff_base_seconds: float = 1.0,
        timeout_seconds: float = 30.0,
        min_size: int = 1024,
    ) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._client = httpx.Client(
            transport=transport,
            timeout=timeout_seconds,
            headers=DEFAULT_HEADERS,
            follow_redirects=True,
        )
        self.max_retries = max_retries
        self.backoff_base_seconds = backoff_base_seconds
        self.min_size = min_size

    def get_text(self, url: str, *, cache_key: str, force_refresh: bool = False) -> str:
        cache_path = self.cache_dir / cache_key
        if not force_refresh and cache_path.exists():
            data = cache_path.read_text(encoding="utf-8")
            if len(data) >= self.min_size:
                return data
            # cache corrupta o truncada: descartar
            cache_path.unlink()

        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = self._client.get(url)
                response.raise_for_status()
                body = response.text
                cache_path.write_text(body, encoding="utf-8")
                return body
            except (httpx.HTTPError, httpx.ConnectError) as exc:
                last_error = exc
                if attempt < self.max_retries - 1:
                    time.sleep(self.backoff_base_seconds * (2**attempt))
        assert last_error is not None
        raise last_error

    def close(self) -> None:
        self._client.close()
```

- [ ] **Step 4: Run tests, verificar pass**

Run: `cd backend && uv run pytest tests/rag/test_ingest_http_cache.py -v`
Expected: 5 passed.

- [ ] **Step 5: Lint**

Run: `cd backend && uv run ruff check src/app/rag/ingest/http_cache.py tests/rag/test_ingest_http_cache.py && uv run ruff format src/app/rag/ingest/http_cache.py tests/rag/test_ingest_http_cache.py`
Expected: All checks passed.

- [ ] **Step 6: Commit**

```bash
git add backend/src/app/rag/ingest/http_cache.py backend/tests/rag/test_ingest_http_cache.py
git commit -m "$(cat <<'EOF'
feat(rag): cache HTTP en disco con reintentos para ingest (F2-01)

httpx.Client con timeout 30s, 3 reintentos con backoff exponencial
(1s/2s/4s) en ConnectError. Cache invalida entradas <1KB
(detecta truncados). --force-refresh bypass del cache.
EOF
)"
```

---

## Task 4: `iso_15459.py` — fragmentos-stub sin red (TDD)

**Files:**
- Create: `backend/src/app/rag/ingest/sources/iso_15459.py`
- Test: `backend/tests/rag/test_ingest_iso_15459.py`

- [ ] **Step 1: Escribir test `test_six_parts_each_language`**

Crear `backend/tests/rag/test_ingest_iso_15459.py`:

```python
"""Tests de la source ISO/IEC 15459-1..6 (fragmentos-stub)."""

from app.rag.ingest.sources.iso_15459 import fetch_fragments
from app.rag.schema import Fragment


def test_six_parts_each_language() -> None:
    fragments_es = list(fetch_fragments(idioma="es"))
    fragments_en = list(fetch_fragments(idioma="en"))

    assert len(fragments_es) == 6
    assert len(fragments_en) == 6
    for f in fragments_es + fragments_en:
        assert isinstance(f, Fragment)
        assert f.reglamento == "ISO/IEC 15459"
        assert f.articulo.startswith("Part")
        assert "ISO" in f.texto
        assert "licencia" in f.texto.lower() or "license" in f.texto.lower()
        assert str(f.fuente_url).startswith("https://www.iso.org/")


def test_articulo_is_part_n() -> None:
    fragments = list(fetch_fragments(idioma="en"))
    articulos = sorted(f.articulo for f in fragments)
    assert articulos == ["Part 1", "Part 2", "Part 3", "Part 4", "Part 5", "Part 6"]


def test_sector_is_none() -> None:
    for f in fetch_fragments(idioma="es"):
        assert f.sector is None, "ISO 15459 es transversal, no sector-específica"


def test_format_citation_is_renderable() -> None:
    from app.rag.schema import format_citation

    fragments = list(fetch_fragments(idioma="es"))
    cita = format_citation(fragments[0])
    assert cita.startswith("Reglamento ISO/IEC 15459, Art. Part ")
```

- [ ] **Step 2: Run test, verificar fallo**

Run: `cd backend && uv run pytest tests/rag/test_ingest_iso_15459.py -v`
Expected: ImportError.

- [ ] **Step 3: Implementar `iso_15459.py`**

Crear `backend/src/app/rag/ingest/sources/iso_15459.py`:

```python
"""Fragmentos-stub de ISO/IEC 15459-1..6 (sin red).

Estas normas son de pago: no se redistribuye texto. Cada fragmento
contiene un abstract público del ISO Online Browsing Platform (≤200
palabras, uso legítimo) más una nota explícita de que el texto
completo está bajo licencia ISO. Cumple su función en el RAG: que
la cita normativa aparezca cuando el chat necesite referenciar el
Art. 77.3 del Reg. UE 2023/1542.
"""

from collections.abc import Iterable
from typing import Literal

from pydantic import HttpUrl

from app.rag.schema import Fragment, Language


_PARTS_EN: dict[str, tuple[str, str]] = {
    "Part 1": (
        "https://www.iso.org/standard/54779.html",
        "ISO/IEC 15459-1:2014 — Information technology — Automatic identification "
        "and data capture techniques — Unique identification — Part 1: Individual "
        "transport units. Specifies a unique, non-significant string of characters "
        "for the identification of transport units. Texto completo bajo licencia ISO.",
    ),
    "Part 2": (
        "https://www.iso.org/standard/54780.html",
        "ISO/IEC 15459-2:2015 — Unique identification — Part 2: Registration "
        "procedures. Specifies the registration procedures required to ensure "
        "that unique identifiers issued by different agencies do not collide. "
        "Texto completo bajo licencia ISO.",
    ),
    "Part 3": (
        "https://www.iso.org/standard/54781.html",
        "ISO/IEC 15459-3:2014 — Unique identification — Part 3: Common rules. "
        "Common rules for the construction of unique identifiers, applicable to "
        "the other parts of the standard. Texto completo bajo licencia ISO.",
    ),
    "Part 4": (
        "https://www.iso.org/standard/54782.html",
        "ISO/IEC 15459-4:2014 — Unique identification — Part 4: Individual "
        "products and product packages. Specifies a unique identifier for "
        "individual products and product packages. Texto completo bajo licencia ISO.",
    ),
    "Part 5": (
        "https://www.iso.org/standard/54783.html",
        "ISO/IEC 15459-5:2014 — Unique identification — Part 5: Individual "
        "returnable transport items (RTIs). Specifies a unique identifier for "
        "returnable transport items. Texto completo bajo licencia ISO.",
    ),
    "Part 6": (
        "https://www.iso.org/standard/54784.html",
        "ISO/IEC 15459-6:2014 — Unique identification — Part 6: Groupings. "
        "Specifies a unique identifier for groupings (logistic groupings of "
        "items). Texto completo bajo licencia ISO.",
    ),
}

_PARTS_ES: dict[str, tuple[str, str]] = {
    "Part 1": (
        "https://www.iso.org/standard/54779.html",
        "ISO/IEC 15459-1:2014 — Tecnologías de la información — Identificación "
        "automática y captura de datos — Identificación única — Parte 1: "
        "Unidades de transporte individuales. Especifica una cadena única no "
        "significativa para identificar unidades de transporte. Texto completo "
        "bajo licencia ISO.",
    ),
    "Part 2": (
        "https://www.iso.org/standard/54780.html",
        "ISO/IEC 15459-2:2015 — Identificación única — Parte 2: Procedimientos "
        "de registro. Especifica los procedimientos de registro necesarios para "
        "garantizar que los identificadores únicos emitidos por agencias distintas "
        "no colisionen. Texto completo bajo licencia ISO.",
    ),
    "Part 3": (
        "https://www.iso.org/standard/54781.html",
        "ISO/IEC 15459-3:2014 — Identificación única — Parte 3: Reglas comunes. "
        "Reglas comunes para la construcción de identificadores únicos, "
        "aplicables al resto de partes de la norma. Texto completo bajo licencia ISO.",
    ),
    "Part 4": (
        "https://www.iso.org/standard/54782.html",
        "ISO/IEC 15459-4:2014 — Identificación única — Parte 4: Productos "
        "individuales y embalajes de productos. Especifica un identificador "
        "único para productos individuales y sus embalajes. Texto completo "
        "bajo licencia ISO.",
    ),
    "Part 5": (
        "https://www.iso.org/standard/54783.html",
        "ISO/IEC 15459-5:2014 — Identificación única — Parte 5: Unidades de "
        "transporte retornables individuales (RTIs). Especifica un identificador "
        "único para unidades de transporte retornables. Texto completo bajo licencia ISO.",
    ),
    "Part 6": (
        "https://www.iso.org/standard/54784.html",
        "ISO/IEC 15459-6:2014 — Identificación única — Parte 6: Agrupaciones. "
        "Especifica un identificador único para agrupaciones logísticas de "
        "ítems. Texto completo bajo licencia ISO.",
    ),
}


def fetch_fragments(idioma: Language) -> Iterable[Fragment]:
    """Devuelve 6 fragmentos-stub (uno por parte) en el idioma pedido."""
    parts: dict[str, tuple[str, str]] = _PARTS_ES if idioma == "es" else _PARTS_EN
    for parte, (url, texto) in parts.items():
        yield Fragment(
            texto=texto,
            reglamento="ISO/IEC 15459",
            articulo=parte,
            apartado=None,
            idioma=idioma,
            fuente_url=HttpUrl(url),
            sector=None,
        )
```

- [ ] **Step 4: Run tests, verificar pass**

Run: `cd backend && uv run pytest tests/rag/test_ingest_iso_15459.py -v`
Expected: 4 passed.

- [ ] **Step 5: Lint**

Run: `cd backend && uv run ruff check src/app/rag/ingest/sources/iso_15459.py tests/rag/test_ingest_iso_15459.py && uv run ruff format src/app/rag/ingest/sources/iso_15459.py tests/rag/test_ingest_iso_15459.py`
Expected: All checks passed.

- [ ] **Step 6: Commit**

```bash
git add backend/src/app/rag/ingest/sources/iso_15459.py backend/tests/rag/test_ingest_iso_15459.py
git commit -m "$(cat <<'EOF'
feat(rag): source ISO/IEC 15459-1..6 fragmentos-stub (F2-01)

6 fragments en es + 6 en en con abstract público + URL canónica ISO
OBP. No redistribuye texto bajo licencia ISO. Permite que el chat
cite la norma cuando el Art. 77.3 del Reg. 2023/1542 lo exija.
EOF
)"
```

---

## Task 5: `eurlex.py` — parser HTML para Reg. UE 2024/1781 (ESPR) (TDD)

**Files:**
- Create: `backend/tests/rag/fixtures/eurlex_ue-2024-1781_es.html`
- Create: `backend/tests/rag/fixtures/eurlex_ue-2024-1781_en.html`
- Create: `backend/src/app/rag/ingest/sources/eurlex.py`
- Test: `backend/tests/rag/test_ingest_eurlex.py`

- [ ] **Step 1: Crear fixture HTML mínima ESPR (es)**

Crear `backend/tests/rag/fixtures/eurlex_ue-2024-1781_es.html`. Este fixture es un recorte realista (no necesita ser el HTML completo, solo suficiente para que el parser encuentre selectores reales de EUR-Lex). Estructura:

```html
<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><title>Reglamento (UE) 2024/1781</title></head>
<body>
  <div class="eli-main-title">
    <p class="oj-doc-ti">REGLAMENTO (UE) 2024/1781 DEL PARLAMENTO EUROPEO Y DEL CONSEJO</p>
    <p class="oj-hd-ti">por el que se establece un marco para fijar requisitos de diseño ecológico</p>
  </div>

  <p class="oj-ti-art" id="d1e1234">Artículo 1</p>
  <p class="oj-sti-art">Objeto y ámbito de aplicación</p>
  <p class="oj-normal">1. El presente Reglamento establece un marco para fijar requisitos de diseño ecológico aplicables a los productos comercializados o puestos en servicio en la Unión.</p>
  <p class="oj-normal">2. El presente Reglamento se aplica a todos los productos físicos comercializados o puestos en servicio.</p>

  <p class="oj-ti-art" id="d1e2345">Artículo 7</p>
  <p class="oj-sti-art">Pasaporte digital de producto</p>
  <p class="oj-normal">1. Los productos comercializados o puestos en servicio dispondrán de un pasaporte digital de producto.</p>
  <p class="oj-normal">2. El pasaporte digital de producto cumplirá los requisitos esenciales establecidos en el artículo 9.</p>
  <p class="oj-normal">3. La información incluida en el pasaporte digital de producto será exacta, completa y estará actualizada.</p>

  <p class="oj-ti-art" id="d1e3456">Artículo 9</p>
  <p class="oj-sti-art">Requisitos esenciales del pasaporte digital de producto</p>
  <p class="oj-normal">1. El pasaporte digital de producto estará conectado, a través de un soporte de datos, con un identificador único de producto.</p>
</body>
</html>
```

- [ ] **Step 2: Crear fixture HTML mínima ESPR (en)**

Crear `backend/tests/rag/fixtures/eurlex_ue-2024-1781_en.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Regulation (EU) 2024/1781</title></head>
<body>
  <div class="eli-main-title">
    <p class="oj-doc-ti">REGULATION (EU) 2024/1781 OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL</p>
    <p class="oj-hd-ti">establishing a framework for the setting of ecodesign requirements</p>
  </div>

  <p class="oj-ti-art" id="d1e1234">Article 1</p>
  <p class="oj-sti-art">Subject matter and scope</p>
  <p class="oj-normal">1. This Regulation establishes a framework for setting ecodesign requirements applicable to products placed on the market or put into service in the Union.</p>
  <p class="oj-normal">2. This Regulation applies to all physical goods placed on the market or put into service.</p>

  <p class="oj-ti-art" id="d1e2345">Article 7</p>
  <p class="oj-sti-art">Digital product passport</p>
  <p class="oj-normal">1. Products placed on the market or put into service shall have a digital product passport.</p>
  <p class="oj-normal">2. The digital product passport shall meet the essential requirements set out in Article 9.</p>
  <p class="oj-normal">3. The information included in the digital product passport shall be accurate, complete, and up-to-date.</p>

  <p class="oj-ti-art" id="d1e3456">Article 9</p>
  <p class="oj-sti-art">Essential requirements for the digital product passport</p>
  <p class="oj-normal">1. The digital product passport shall be connected, through a data carrier, with a unique product identifier.</p>
</body>
</html>
```

- [ ] **Step 3: Escribir test `test_parse_espr_es_produces_articles`**

Crear `backend/tests/rag/test_ingest_eurlex.py`:

```python
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

    big_html = "<html><body>" + ("<p>nope</p>" * 200) + "</body></html>"  # >10 KB sin artículos
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
```

- [ ] **Step 4: Run tests, verificar fallo**

Run: `cd backend && uv run pytest tests/rag/test_ingest_eurlex.py -v`
Expected: ImportError.

- [ ] **Step 5: Implementar parser en `eurlex.py`**

Crear `backend/src/app/rag/ingest/sources/eurlex.py`:

```python
"""Source EUR-Lex: parser HTML + descarga para reglamentos UE.

Cubre Reg. UE 2024/1781 (ESPR), Reg. UE 2023/1542 (baterías) y actos
delegados publicados. Cada apartado dentro de cada artículo se modela
como un Fragment independiente. Los anexos se modelan como
`articulo="Annex N"`.

Selectores HTML basados en la estructura semántica de EUR-Lex:
- `p.oj-ti-art`     marca "Artículo N" / "Article N"
- `p.oj-sti-art`    subtítulo del artículo (no se persiste)
- `p.oj-normal`     párrafos numerados (apartados)
- `div.eli-main-title` cabecera del documento (no se persiste)
"""

import re
from collections.abc import Iterable
from pathlib import Path

from bs4 import BeautifulSoup
from pydantic import HttpUrl

from app.rag.ingest.http_cache import CachedHttpClient
from app.rag.schema import Fragment, Language


class IngestParseError(RuntimeError):
    """Se levantó porque el HTML no contiene la estructura esperada."""


# Reconoce "Artículo 7", "Article 7", "Artículo 77 bis"
_ARTICLE_RE = re.compile(r"^(?:Artículo|Article)\s+([0-9]+(?:\s*bis|\s*ter|\s*quater)?)$", re.IGNORECASE)
# Reconoce "ANEXO XIII", "ANNEX XIII", "ANEXO 1"
_ANNEX_RE = re.compile(r"^(?:ANEXO|ANNEX)\s+([IVXLCDM0-9]+)\s*$", re.IGNORECASE)
# Reconoce inicio de apartado: "1.", "12.", "1.a)", etc.
_PARAGRAPH_NUM_RE = re.compile(r"^\s*([0-9]+(?:\.[a-z0-9]+)*)\s*\.\s*(.*)$", re.DOTALL)


def parse_eurlex_html(
    html: str,
    *,
    reglamento: str,
    idioma: Language,
    fuente_url: HttpUrl,
    sector: str | None,
) -> Iterable[Fragment]:
    """Parsea HTML EUR-Lex en stream de Fragments por (artículo, apartado).

    Levanta `IngestParseError` si en >10 KB no encuentra ningún artículo
    o anexo (regresión: EUR-Lex cambió la estructura).
    """
    soup = BeautifulSoup(html, "lxml")

    current_articulo: str | None = None
    found_any = False

    for tag in soup.find_all("p"):
        classes = tag.get("class") or []
        text = tag.get_text(" ", strip=True)

        if "oj-ti-art" in classes:
            art = _match_article(text)
            annex = _match_annex(text)
            current_articulo = art or annex
            if current_articulo:
                found_any = True
            continue

        if current_articulo is None:
            continue

        if "oj-normal" in classes:
            apartado, contenido = _split_paragraph(text)
            if not contenido.strip():
                continue
            yield Fragment(
                texto=contenido.strip(),
                reglamento=reglamento,
                articulo=current_articulo,
                apartado=apartado,
                idioma=idioma,
                fuente_url=fuente_url,
                sector=sector,
            )

    if not found_any and len(html) > 10_000:
        raise IngestParseError(
            f"HTML >10KB sin artículos detectados (URL {fuente_url}). "
            "Probable cambio de estructura en EUR-Lex."
        )


def _match_article(text: str) -> str | None:
    m = _ARTICLE_RE.match(text.strip())
    if not m:
        return None
    return re.sub(r"\s+", " ", m.group(1)).strip()


def _match_annex(text: str) -> str | None:
    m = _ANNEX_RE.match(text.strip())
    if not m:
        return None
    return f"Annex {m.group(1)}"


def _split_paragraph(text: str) -> tuple[str | None, str]:
    """Extrae nº de apartado del inicio del párrafo, si existe."""
    m = _PARAGRAPH_NUM_RE.match(text)
    if not m:
        return None, text
    return m.group(1), m.group(2)


# ──────────────────────────────────────────────────────────────────────
# Fetcher de alto nivel (se completa en T6/T7)
# ──────────────────────────────────────────────────────────────────────

_EURLEX_BASE = "https://eur-lex.europa.eu/legal-content/{lang_upper}/TXT/HTML/?uri=CELEX:{celex}"


def build_eurlex_url(celex: str, idioma: Language) -> HttpUrl:
    return HttpUrl(_EURLEX_BASE.format(lang_upper=idioma.upper(), celex=celex))


def fetch_regulation_fragments(
    client: CachedHttpClient,
    *,
    celex: str,
    reglamento: str,
    sector: str | None,
    force_refresh: bool = False,
    languages: tuple[Language, ...] = ("es", "en"),
) -> Iterable[Fragment]:
    """Descarga y parsea un reglamento EUR-Lex en los idiomas pedidos."""
    for idioma in languages:
        url = build_eurlex_url(celex, idioma)
        html = client.get_text(
            str(url),
            cache_key=f"{celex}.{idioma}.html",
            force_refresh=force_refresh,
        )
        yield from parse_eurlex_html(
            html,
            reglamento=reglamento,
            idioma=idioma,
            fuente_url=url,
            sector=sector,
        )


def load_local_html(fixture_path: Path) -> str:
    """Helper para tests/local: lee un HTML del disco."""
    return fixture_path.read_text(encoding="utf-8")
```

- [ ] **Step 6: Run tests, verificar pass**

Run: `cd backend && uv run pytest tests/rag/test_ingest_eurlex.py -v`
Expected: 3 passed.

- [ ] **Step 7: Lint**

Run: `cd backend && uv run ruff check src/app/rag/ingest/sources/eurlex.py tests/rag/test_ingest_eurlex.py && uv run ruff format src/app/rag/ingest/sources/eurlex.py tests/rag/test_ingest_eurlex.py`
Expected: All checks passed.

- [ ] **Step 8: Commit**

```bash
git add backend/src/app/rag/ingest/sources/eurlex.py \
        backend/tests/rag/test_ingest_eurlex.py \
        backend/tests/rag/fixtures/eurlex_ue-2024-1781_es.html \
        backend/tests/rag/fixtures/eurlex_ue-2024-1781_en.html
git commit -m "$(cat <<'EOF'
feat(rag): parser EUR-Lex para Reg. UE 2024/1781 ESPR (F2-01)

parse_eurlex_html(html, reglamento, idioma, fuente_url, sector)
emite un Fragment por (artículo, apartado). Selectores OJ:
oj-ti-art, oj-normal. Reconoce "Artículo N" / "Article N" y
"ANEXO X" / "ANNEX X". Si HTML >10KB no devuelve artículos
levanta IngestParseError (regresión).

Tests usan fixture HTML local recortada con la estructura
semántica real de EUR-Lex (clases oj-*). Sin red en CI.
EOF
)"
```

---

## Task 6: `eurlex.py` — Reg. UE 2023/1542 (baterías) + Annex XIII + sector=batteries (TDD)

**Files:**
- Create: `backend/tests/rag/fixtures/eurlex_ue-2023-1542_es.html`
- Create: `backend/tests/rag/fixtures/eurlex_ue-2023-1542_en.html`
- Modify: `backend/tests/rag/test_ingest_eurlex.py`

- [ ] **Step 1: Crear fixture HTML del Reg. 2023/1542 (es)**

Crear `backend/tests/rag/fixtures/eurlex_ue-2023-1542_es.html`. Incluye Art. 77 (Pasaporte de batería) + Annex XIII (Información que debe incluirse en el pasaporte para baterías):

```html
<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><title>Reglamento (UE) 2023/1542</title></head>
<body>
  <div class="eli-main-title">
    <p class="oj-doc-ti">REGLAMENTO (UE) 2023/1542 DEL PARLAMENTO EUROPEO Y DEL CONSEJO</p>
    <p class="oj-hd-ti">relativo a las pilas y baterías y a sus residuos</p>
  </div>

  <p class="oj-ti-art" id="d1e10000">Artículo 1</p>
  <p class="oj-sti-art">Objeto</p>
  <p class="oj-normal">1. El presente Reglamento establece requisitos de sostenibilidad, seguridad, etiquetado, marcado e información para la comercialización de pilas y baterías en la Unión.</p>

  <p class="oj-ti-art" id="d1e77000">Artículo 77</p>
  <p class="oj-sti-art">Pasaporte de batería</p>
  <p class="oj-normal">1. A partir del 18 de febrero de 2027, cada batería para LMT, batería industrial con una capacidad superior a 2 kWh y batería de vehículo eléctrico que se introduzca en el mercado o se ponga en servicio dispondrá de un registro electrónico ("pasaporte de batería").</p>
  <p class="oj-normal">2. El pasaporte de batería contendrá la información establecida en el anexo XIII.</p>
  <p class="oj-normal">3. El pasaporte de batería estará vinculado de manera única mediante un identificador único que el operador económico que introduzca la batería en el mercado asignará en forma de código QR e imprimirá o grabará en la batería conforme a las normas ISO/IEC 15459-1:2014, ISO/IEC 15459-2:2015, ISO/IEC 15459-3:2014, ISO/IEC 15459-4:2014, ISO/IEC 15459-5:2014 e ISO/IEC 15459-6:2014, o equivalentes.</p>

  <p class="oj-ti-art" id="d1eannex13">ANEXO XIII</p>
  <p class="oj-sti-art">Información que debe incluirse en el pasaporte de batería</p>
  <p class="oj-normal">1. Información accesible al público sobre el modelo de batería: fabricante, modelo, año de fabricación, peso, capacidad.</p>
  <p class="oj-normal">2. Información accesible únicamente a las personas con un interés legítimo y a la Comisión: composición detallada, despiece físico.</p>
</body>
</html>
```

- [ ] **Step 2: Crear fixture en inglés**

Crear `backend/tests/rag/fixtures/eurlex_ue-2023-1542_en.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Regulation (EU) 2023/1542</title></head>
<body>
  <div class="eli-main-title">
    <p class="oj-doc-ti">REGULATION (EU) 2023/1542 OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL</p>
    <p class="oj-hd-ti">concerning batteries and waste batteries</p>
  </div>

  <p class="oj-ti-art" id="d1e10000">Article 1</p>
  <p class="oj-sti-art">Subject matter</p>
  <p class="oj-normal">1. This Regulation establishes requirements on sustainability, safety, labelling, marking and information for the placing on the market of batteries in the Union.</p>

  <p class="oj-ti-art" id="d1e77000">Article 77</p>
  <p class="oj-sti-art">Battery passport</p>
  <p class="oj-normal">1. From 18 February 2027, each LMT battery, industrial battery with a capacity greater than 2 kWh, and electric vehicle battery placed on the market or put into service shall have an electronic record ("battery passport").</p>
  <p class="oj-normal">2. The battery passport shall contain the information set out in Annex XIII.</p>
  <p class="oj-normal">3. The battery passport shall be uniquely identified through a unique identifier which the economic operator placing the battery on the market shall assign in the form of a QR code and print or engrave on the battery in accordance with ISO/IEC 15459-1:2014, ISO/IEC 15459-2:2015, ISO/IEC 15459-3:2014, ISO/IEC 15459-4:2014, ISO/IEC 15459-5:2014 and ISO/IEC 15459-6:2014, or equivalent.</p>

  <p class="oj-ti-art" id="d1eannex13">ANNEX XIII</p>
  <p class="oj-sti-art">Information to be included in the battery passport</p>
  <p class="oj-normal">1. Information accessible to the public about the battery model: manufacturer, model, year of manufacture, weight, capacity.</p>
  <p class="oj-normal">2. Information accessible only to persons with a legitimate interest and to the Commission: detailed composition, physical breakdown.</p>
</body>
</html>
```

- [ ] **Step 3: Añadir tests del Reg. 2023/1542 + Annex XIII + sector**

Append a `backend/tests/rag/test_ingest_eurlex.py`:

```python
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
    assert "ISO/IEC 15459" in art77_3.texto, "Art. 77.3 debe citar ISO/IEC 15459 (cumplimiento Art. 77.3 del Reg.)"
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
```

- [ ] **Step 4: Run tests, verificar pass**

Run: `cd backend && uv run pytest tests/rag/test_ingest_eurlex.py -v`
Expected: 8 passed. (3 anteriores + 5 nuevos)

- [ ] **Step 5: Lint**

Run: `cd backend && uv run ruff check tests/rag/test_ingest_eurlex.py && uv run ruff format tests/rag/test_ingest_eurlex.py`
Expected: All checks passed.

- [ ] **Step 6: Commit**

```bash
git add backend/tests/rag/fixtures/eurlex_ue-2023-1542_es.html \
        backend/tests/rag/fixtures/eurlex_ue-2023-1542_en.html \
        backend/tests/rag/test_ingest_eurlex.py
git commit -m "$(cat <<'EOF'
feat(rag): cobertura Art. 77 + Annex XIII Reg. UE 2023/1542 (F2-01)

Añade fixtures es+en del Reg. baterías con los tres puntos críticos:
Art. 77 (pasaporte de batería), Art. 77.3 (referencia ISO/IEC
15459-1..6 — cumplimiento del esquema obligatorio del identificador
único) y Annex XIII (información incluida en el pasaporte de
batería). Tests verifican que sector="batteries" se etiqueta y que
ESPR (sector=None) no.
EOF
)"
```

---

## Task 7: `eurlex.py` — actos delegados publicados (TDD)

**Files:**
- Modify: `backend/src/app/rag/ingest/sources/eurlex.py`
- Modify: `backend/tests/rag/test_ingest_eurlex.py`

- [ ] **Step 1: Investigar actos delegados ESPR publicados a 2026-05-25**

Run: `curl -s 'https://eur-lex.europa.eu/search.html?DD_YEAR=2024,2025,2026&qid=1&DTS_DOM=ALL&type=advanced&CASE_LAW_SUMMARY=false&CASE_LAW_JURIS=false&DTS_SUBDOM=LEGAL_ACTS&DB_TYPE_OF_ACT=delegReg&excConsLeg=true&DD_FROM_DATE_FILTER=01012024' -H "Accept: text/html" | grep -oE 'CELEX:[0-9]{5}[A-Z][0-9]{4}' | sort -u | head -20`

Documenta los CELEX encontrados (si los hay). Si la lista está vacía, registrar `KNOWN_DELEGATED_ACTS = []` y dejar la fuente desactivada con un comentario explicativo. **Si hay actos**, capturar para cada uno: CELEX, título corto, sector (`None` si transversal, o `"textile"` / `"electronics"` / etc.), idiomas oficiales (siempre es+en al mínimo).

- [ ] **Step 2: Escribir test del registry**

Append a `backend/tests/rag/test_ingest_eurlex.py`:

```python
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
```

- [ ] **Step 3: Run tests, verificar fallo**

Run: `cd backend && uv run pytest tests/rag/test_ingest_eurlex.py -v`
Expected: `ImportError: cannot import name 'KNOWN_DELEGATED_ACTS'`.

- [ ] **Step 4: Añadir registry de actos delegados a `eurlex.py`**

Append a `backend/src/app/rag/ingest/sources/eurlex.py`:

```python
# ──────────────────────────────────────────────────────────────────────
# Actos delegados ESPR publicados a la fecha
#
# Lista declarativa. Se rellena tras consultar EUR-Lex con el filtro
# tipo=delegReg + DD_YEAR=>=2024 + dominio="legal-acts". En caso de
# que no exista todavía ningún acto delegado ESPR publicado (estado
# real durante el desarrollo de F2-01 puede ser que la lista esté
# vacía), KNOWN_DELEGATED_ACTS = [] es respuesta válida y el CLI se
# salta este source con un INFO log.
# ──────────────────────────────────────────────────────────────────────

from dataclasses import dataclass


@dataclass(frozen=True)
class DelegatedAct:
    """Acto delegado ESPR registrado para ingesta."""

    celex: str               # ej. "32024R0567"
    reglamento: str          # ej. "UE 2024/567"
    sector: str | None       # ej. "textile" o None si transversal

    @property
    def slug(self) -> str:
        return f"actos-delegados-{self.celex.lower()}"


# Rellenar con el resultado de la consulta del Step 1. Si está vacío,
# dejar la lista vacía explícitamente.
KNOWN_DELEGATED_ACTS: list[DelegatedAct] = []


def fetch_delegated_acts_fragments(
    client: CachedHttpClient,
    *,
    force_refresh: bool = False,
    languages: tuple[Language, ...] = ("es", "en"),
) -> Iterable[Fragment]:
    """Itera sobre los actos delegados registrados y los parsea."""
    for act in KNOWN_DELEGATED_ACTS:
        yield from fetch_regulation_fragments(
            client,
            celex=act.celex,
            reglamento=act.reglamento,
            sector=act.sector,
            force_refresh=force_refresh,
            languages=languages,
        )
```

- [ ] **Step 5: Run tests, verificar pass**

Run: `cd backend && uv run pytest tests/rag/test_ingest_eurlex.py -v`
Expected: 10 passed (2 nuevos sobre los 8 anteriores). Si `KNOWN_DELEGATED_ACTS` está vacío los tests siguen pasando porque iteran sobre cero elementos.

- [ ] **Step 6: Lint**

Run: `cd backend && uv run ruff check src/app/rag/ingest/sources/eurlex.py tests/rag/test_ingest_eurlex.py && uv run ruff format src/app/rag/ingest/sources/eurlex.py tests/rag/test_ingest_eurlex.py`
Expected: All checks passed.

- [ ] **Step 7: Commit**

```bash
git add backend/src/app/rag/ingest/sources/eurlex.py backend/tests/rag/test_ingest_eurlex.py
git commit -m "$(cat <<'EOF'
feat(rag): registry declarativo de actos delegados ESPR (F2-01)

DelegatedAct frozen dataclass + lista KNOWN_DELEGATED_ACTS rellena
con el resultado de la consulta EUR-Lex el 2026-05-25. Slug
"actos-delegados-{celex-en-minúsculas}" para los JSONL.

Si no hay actos delegados ESPR publicados todavía (estado actual
de EUR-Lex), la lista vacía es comportamiento válido: el CLI los
salta sin error y el resto del corpus se ingiere normalmente.
EOF
)"
```

---

## Task 8: `cirpass.py` — CIRPASS-2 Core Ontology desde JSON-LD (TDD)

**Files:**
- Create: `backend/tests/rag/fixtures/cirpass_core.jsonld`
- Create: `backend/src/app/rag/ingest/sources/cirpass.py`
- Create: `backend/tests/rag/test_ingest_cirpass.py`

- [ ] **Step 1: Crear fixture mínima `cirpass_core.jsonld`**

Crear `backend/tests/rag/fixtures/cirpass_core.jsonld`. La estructura JSON-LD de la ontología CIRPASS-2 (referenciada en `docs/ARCHITECTURE.md`) usa `@graph` con clases SKOS-like. Fixture realista:

```json
{
  "@context": {
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "label": "rdfs:label",
    "comment": "rdfs:comment"
  },
  "@graph": [
    {
      "@id": "https://cirpass.eu/ontology/core#Product",
      "@type": "owl:Class",
      "label": "Product",
      "comment": "A physical good placed on the market, subject to the Digital Product Passport requirements set out in Regulation (EU) 2024/1781."
    },
    {
      "@id": "https://cirpass.eu/ontology/core#Material",
      "@type": "owl:Class",
      "label": "Material",
      "comment": "A substance or mixture of substances that constitutes a Product or one of its Components."
    },
    {
      "@id": "https://cirpass.eu/ontology/core#ConformityDocument",
      "@type": "owl:Class",
      "label": "ConformityDocument",
      "comment": "A document attesting that a Product complies with one or more applicable regulations or standards."
    }
  ]
}
```

- [ ] **Step 2: Escribir tests**

Crear `backend/tests/rag/test_ingest_cirpass.py`:

```python
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
```

- [ ] **Step 3: Run tests, verificar fallo**

Run: `cd backend && uv run pytest tests/rag/test_ingest_cirpass.py -v`
Expected: ImportError.

- [ ] **Step 4: Implementar `cirpass.py`**

Crear `backend/src/app/rag/ingest/sources/cirpass.py`:

```python
"""Source CIRPASS-2 Core Ontology.

La ontología se publica en JSON-LD (rdfs:label + rdfs:comment por clase).
Cada clase con label + comment se convierte en un Fragment cuyo
`articulo` es el label de la clase. No hay versión es oficial: solo en.

URL canónica: https://cirpass.eu/ontology/core (placeholder hasta
confirmar URL exacta en el plan).
"""

import json
from collections.abc import Iterable

from pydantic import HttpUrl

from app.rag.ingest.http_cache import CachedHttpClient
from app.rag.schema import Fragment

_CANONICAL_URL = "https://cirpass.eu/ontology/core"


def parse_cirpass_jsonld(payload: str) -> Iterable[Fragment]:
    """Parsea el JSON-LD de CIRPASS-2 Core y emite Fragments por clase."""
    data = json.loads(payload)
    graph = data.get("@graph", [])
    for entry in graph:
        label = entry.get("label")
        comment = entry.get("comment")
        if not label or not comment:
            continue
        yield Fragment(
            texto=f"{label}: {comment}",
            reglamento="CIRPASS-2 Core",
            articulo=str(label),
            apartado=None,
            idioma="en",
            fuente_url=HttpUrl(_CANONICAL_URL),
            sector=None,
        )


def fetch_fragments(
    client: CachedHttpClient,
    *,
    force_refresh: bool = False,
) -> Iterable[Fragment]:
    """Descarga el JSON-LD canónico y emite Fragments."""
    payload = client.get_text(
        _CANONICAL_URL,
        cache_key="cirpass-2-core.jsonld",
        force_refresh=force_refresh,
    )
    yield from parse_cirpass_jsonld(payload)
```

- [ ] **Step 5: Run tests, verificar pass**

Run: `cd backend && uv run pytest tests/rag/test_ingest_cirpass.py -v`
Expected: 3 passed.

- [ ] **Step 6: Lint**

Run: `cd backend && uv run ruff check src/app/rag/ingest/sources/cirpass.py tests/rag/test_ingest_cirpass.py && uv run ruff format src/app/rag/ingest/sources/cirpass.py tests/rag/test_ingest_cirpass.py`
Expected: All checks passed.

- [ ] **Step 7: Commit**

```bash
git add backend/src/app/rag/ingest/sources/cirpass.py \
        backend/tests/rag/test_ingest_cirpass.py \
        backend/tests/rag/fixtures/cirpass_core.jsonld
git commit -m "$(cat <<'EOF'
feat(rag): source CIRPASS-2 Core Ontology JSON-LD (F2-01)

Una clase con label+comment → un Fragment. articulo=label,
reglamento="CIRPASS-2 Core", apartado=None, sector=None, idioma=en
(no hay versión es oficial). Entradas sin label o comment se
saltan. Fragment.texto = "label: comment" para retrieval rico.
EOF
)"
```

---

## Task 9: `gs1.py` — GS1 Digital Link spec HTML (TDD)

**Files:**
- Create: `backend/tests/rag/fixtures/gs1_digital_link.html`
- Create: `backend/src/app/rag/ingest/sources/gs1.py`
- Create: `backend/tests/rag/test_ingest_gs1.py`

- [ ] **Step 1: Crear fixture mínima `gs1_digital_link.html`**

Crear `backend/tests/rag/fixtures/gs1_digital_link.html`. La spec GS1 Digital Link 1.3 usa estructura HTML con secciones numeradas (`<h2>1. Introduction</h2>`):

```html
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>GS1 Digital Link 1.3.0</title></head>
<body>
  <h1>GS1 Digital Link Standard</h1>
  <h2 id="s1">1. Introduction</h2>
  <p>GS1 Digital Link enables connections between physical objects and digital information.</p>
  <p>The standard extends the role of GS1 identifiers by enabling them to function as web URIs.</p>

  <h2 id="s2">2. URI Syntax</h2>
  <p>The base URI follows the pattern /{primaryIdentifier}/{value}.</p>
  <p>Primary identifiers include GTIN, GLN, SSCC, and others defined in section 3.</p>

  <h2 id="s3">3. Identifier Mappings</h2>
  <p>This section defines how GS1 Application Identifiers map to URI path components.</p>
</body>
</html>
```

- [ ] **Step 2: Escribir tests**

Crear `backend/tests/rag/test_ingest_gs1.py`:

```python
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
```

- [ ] **Step 3: Run tests, verificar fallo**

Run: `cd backend && uv run pytest tests/rag/test_ingest_gs1.py -v`
Expected: ImportError.

- [ ] **Step 4: Implementar `gs1.py`**

Crear `backend/src/app/rag/ingest/sources/gs1.py`:

```python
"""Source GS1 Digital Link spec 1.3.

Estructura HTML: <h2>N. Título</h2> seguidos de <p>...</p> hasta el
próximo <h2>. Cada sección numerada se convierte en un Fragment con
articulo="sección N", texto = título + concatenación de párrafos.
"""

import re
from collections.abc import Iterable

from bs4 import BeautifulSoup
from pydantic import HttpUrl

from app.rag.ingest.http_cache import CachedHttpClient
from app.rag.schema import Fragment

_CANONICAL_URL = "https://www.gs1.org/standards/gs1-digital-link"
_SECTION_RE = re.compile(r"^\s*([0-9]+)\.\s+(.+?)\s*$")


def parse_gs1_html(html: str) -> Iterable[Fragment]:
    """Parsea HTML de GS1 Digital Link y emite Fragments por sección."""
    soup = BeautifulSoup(html, "lxml")
    sections: list[tuple[str, str, list[str]]] = []  # (numero, titulo, parrafos)
    current: tuple[str, str, list[str]] | None = None

    for tag in soup.find_all(["h2", "p"]):
        if tag.name == "h2":
            text = tag.get_text(" ", strip=True)
            m = _SECTION_RE.match(text)
            if not m:
                current = None
                continue
            if current is not None:
                sections.append(current)
            current = (m.group(1), m.group(2), [])
        elif tag.name == "p" and current is not None:
            current[2].append(tag.get_text(" ", strip=True))

    if current is not None:
        sections.append(current)

    for numero, titulo, parrafos in sections:
        cuerpo = " ".join(p for p in parrafos if p)
        yield Fragment(
            texto=f"{titulo}. {cuerpo}".strip(),
            reglamento="GS1 Digital Link 1.3.0",
            articulo=f"sección {numero}",
            apartado=None,
            idioma="en",
            fuente_url=HttpUrl(_CANONICAL_URL),
            sector=None,
        )


def fetch_fragments(
    client: CachedHttpClient,
    *,
    force_refresh: bool = False,
) -> Iterable[Fragment]:
    payload = client.get_text(
        _CANONICAL_URL,
        cache_key="gs1-digital-link.html",
        force_refresh=force_refresh,
    )
    yield from parse_gs1_html(payload)
```

- [ ] **Step 5: Run tests, verificar pass**

Run: `cd backend && uv run pytest tests/rag/test_ingest_gs1.py -v`
Expected: 3 passed.

- [ ] **Step 6: Lint**

Run: `cd backend && uv run ruff check src/app/rag/ingest/sources/gs1.py tests/rag/test_ingest_gs1.py && uv run ruff format src/app/rag/ingest/sources/gs1.py tests/rag/test_ingest_gs1.py`
Expected: All checks passed.

- [ ] **Step 7: Commit**

```bash
git add backend/src/app/rag/ingest/sources/gs1.py \
        backend/tests/rag/test_ingest_gs1.py \
        backend/tests/rag/fixtures/gs1_digital_link.html
git commit -m "$(cat <<'EOF'
feat(rag): source GS1 Digital Link spec (F2-01)

<h2>N. Título</h2> + <p>...</p> → Fragment con articulo="sección N",
texto = título + párrafos concatenados. Una sección puede contener
varios <p>; todos se unen. Idioma=en (no hay versión es oficial).
EOF
)"
```

---

## Task 10: CLI `python -m app.rag.ingest` (TDD)

**Files:**
- Create: `backend/src/app/rag/ingest/__main__.py`
- Create: `backend/tests/rag/test_ingest_cli.py`
- Modify: `Makefile` (raíz)

- [ ] **Step 1: Escribir test del CLI (happy path con sources mockeadas)**

Crear `backend/tests/rag/test_ingest_cli.py`:

```python
"""Tests del CLI `python -m app.rag.ingest`."""

from pathlib import Path

import pytest
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
            ("iso-15459",    lambda client, lang, force_refresh: fake_iso(lang)),
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
            ("ue-2024-1781", lambda client, lang, force_refresh: iter([_sample_fragment("UE 2024/1781", "es")])),
            ("iso-15459",    lambda client, lang, force_refresh: iter([_sample_fragment("ISO/IEC 15459", lang)])),
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
            ("iso-15459",    lambda client, lang, force_refresh: iter([_sample_fragment("ISO/IEC 15459", lang)])),
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
```

- [ ] **Step 2: Run tests, verificar fallo**

Run: `cd backend && uv run pytest tests/rag/test_ingest_cli.py -v`
Expected: ImportError.

- [ ] **Step 3: Implementar `__main__.py`**

Crear `backend/src/app/rag/ingest/__main__.py`:

```python
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
from app.rag.ingest.sources import cirpass, gs1, iso_15459
from app.rag.ingest.writer import write_jsonl
from app.rag.schema import Fragment, Language

logger = logging.getLogger("app.rag.ingest")


SourceFn = Callable[[CachedHttpClient, Language, bool], Iterable[Fragment]]


def _eurlex_espr(client: CachedHttpClient, lang: Language, force_refresh: bool) -> Iterable[Fragment]:
    return fetch_regulation_fragments(
        client,
        celex="32024R1781",
        reglamento="UE 2024/1781",
        sector=None,
        force_refresh=force_refresh,
        languages=(lang,),
    )


def _eurlex_baterias(client: CachedHttpClient, lang: Language, force_refresh: bool) -> Iterable[Fragment]:
    return fetch_regulation_fragments(
        client,
        celex="32023R1542",
        reglamento="UE 2023/1542",
        sector="batteries",
        force_refresh=force_refresh,
        languages=(lang,),
    )


def _actos_delegados(client: CachedHttpClient, lang: Language, force_refresh: bool) -> Iterable[Fragment]:
    if not KNOWN_DELEGATED_ACTS:
        logger.info("No hay actos delegados ESPR registrados; se omite la source.")
        return iter(())
    return fetch_delegated_acts_fragments(client, force_refresh=force_refresh, languages=(lang,))


def _cirpass(client: CachedHttpClient, lang: Language, force_refresh: bool) -> Iterable[Fragment]:
    if lang != "en":
        return iter(())  # CIRPASS-2 solo tiene versión en
    return cirpass.fetch_fragments(client, force_refresh=force_refresh)


def _gs1(client: CachedHttpClient, lang: Language, force_refresh: bool) -> Iterable[Fragment]:
    if lang != "en":
        return iter(())  # GS1 solo en
    return gs1.fetch_fragments(client, force_refresh=force_refresh)


def _iso_15459(_client: CachedHttpClient, lang: Language, _force_refresh: bool) -> Iterable[Fragment]:
    return iso_15459.fetch_fragments(idioma=lang)


SOURCES: list[tuple[str, SourceFn]] = [
    ("ue-2024-1781",      _eurlex_espr),
    ("ue-2023-1542",      _eurlex_baterias),
    ("actos-delegados",   _actos_delegados),
    ("cirpass-2-core",    _cirpass),
    ("gs1-digital-link",  _gs1),
    ("iso-15459",         _iso_15459),
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
                    logger.info("• %s.%s: sin fragments (idioma no soportado o lista vacía)", slug, current_lang)
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
```

- [ ] **Step 4: Run tests, verificar pass**

Run: `cd backend && uv run pytest tests/rag/test_ingest_cli.py -v`
Expected: 6 passed.

- [ ] **Step 5: Verificar suite completa**

Run: `cd backend && uv run pytest -q`
Expected: todos los tests verde (suite previa + nueva). Tiempo total <30 s.

- [ ] **Step 6: Añadir target al `Makefile` raíz**

Editar `Makefile` (raíz del repo). Añadir target `ingest`:

```makefile
.PHONY: ingest
ingest:
	cd backend && uv run python -m app.rag.ingest
```

(Si `make` existente tiene formato distinto, ajustar al estilo. Ver el resto del Makefile antes de editar.)

- [ ] **Step 7: Lint**

Run: `cd backend && uv run ruff check src/app/rag/ingest/__main__.py tests/rag/test_ingest_cli.py && uv run ruff format src/app/rag/ingest/__main__.py tests/rag/test_ingest_cli.py`
Expected: All checks passed.

- [ ] **Step 8: Commit**

```bash
git add backend/src/app/rag/ingest/__main__.py backend/tests/rag/test_ingest_cli.py Makefile
git commit -m "$(cat <<'EOF'
feat(rag): CLI python -m app.rag.ingest (F2-01)

Orquesta las 6 sources (ESPR, baterías, actos delegados, CIRPASS-2,
GS1, ISO/IEC 15459) × es+en. Persiste a data/corpus/{slug}.{lang}.jsonl
con escritura atómica.

Exit codes:
  0  OK
  1  alguna source falló por red (resto continuó)
  2  regresión de parser (bloqueante)

CIRPASS-2 y GS1 solo en "en" (no hay versión es oficial); el CLI
genera ficheros vacíos para "es" no, simplemente los omite con log.

Makefile: make ingest atajo al comando.
EOF
)"
```

---

## Task 11: F2-04 dataset `queries.yaml` + pydantic schema (TDD)

**Files:**
- Create: `backend/tests/rag/queries.yaml`
- Create: `backend/src/app/rag/eval/__init__.py`
- Create: `backend/src/app/rag/eval/dataset.py`

- [ ] **Step 1: Crear `backend/tests/rag/queries.yaml` con 21 queries**

Crear `backend/tests/rag/queries.yaml`. Distribución mínima: ≥8 ESPR, ≥8 baterías (3+ sobre Art. 77/Annex XIII), ≥2 CIRPASS, ≥2 GS1, ≥2 ISO, ≥40% es, ≥40% en. 21 entradas:

```yaml
- id: espr-pasaporte-art7-1
  query: "¿Qué productos deben tener pasaporte digital de producto?"
  expected_citation:
    reglamento: "UE 2024/1781"
    articulo: "7"
  idioma: es
  tags: [espr, alcance]

- id: espr-pasaporte-art7-en
  query: "Which products require a digital product passport?"
  expected_citation:
    reglamento: "UE 2024/1781"
    articulo: "7"
  idioma: en
  tags: [espr, alcance]

- id: espr-informacion-actualizada-art7-3
  query: "¿La información del pasaporte digital tiene que estar actualizada?"
  expected_citation:
    reglamento: "UE 2024/1781"
    articulo: "7"
    apartado: "3"
  idioma: es
  tags: [espr, calidad-datos]

- id: espr-essential-requirements-art9
  query: "What are the essential requirements for the digital product passport?"
  expected_citation:
    reglamento: "UE 2024/1781"
    articulo: "9"
  idioma: en
  tags: [espr, requisitos]

- id: espr-identificador-unico-art9
  query: "¿Cómo se conecta el pasaporte digital con el identificador del producto?"
  expected_citation:
    reglamento: "UE 2024/1781"
    articulo: "9"
  idioma: es
  tags: [espr, identificador]

- id: espr-objeto-art1
  query: "¿Cuál es el objeto del reglamento ESPR?"
  expected_citation:
    reglamento: "UE 2024/1781"
    articulo: "1"
  idioma: es
  tags: [espr, objeto]

- id: espr-scope-art1-en
  query: "What is the scope of the ESPR regulation?"
  expected_citation:
    reglamento: "UE 2024/1781"
    articulo: "1"
  idioma: en
  tags: [espr, alcance]

- id: espr-ecodesign-framework
  query: "What does the ESPR framework establish for ecodesign requirements?"
  expected_citation:
    reglamento: "UE 2024/1781"
    articulo: "1"
  idioma: en
  tags: [espr, framework]

- id: batteries-pasaporte-art77-1
  query: "¿A partir de qué fecha es obligatorio el pasaporte de batería?"
  expected_citation:
    reglamento: "UE 2023/1542"
    articulo: "77"
    apartado: "1"
  idioma: es
  tags: [batteries, fecha]

- id: batteries-passport-info-art77-2
  query: "What information must the battery passport contain?"
  expected_citation:
    reglamento: "UE 2023/1542"
    articulo: "77"
    apartado: "2"
  idioma: en
  tags: [batteries, contenido]

- id: batteries-iso-15459-art77-3
  query: "¿Qué normas ISO debe cumplir el identificador único del pasaporte de batería?"
  expected_citation:
    reglamento: "UE 2023/1542"
    articulo: "77"
    apartado: "3"
  idioma: es
  tags: [batteries, identificador, iso]

- id: batteries-qr-code-art77-3-en
  query: "How is the battery passport linked to the physical battery via QR code?"
  expected_citation:
    reglamento: "UE 2023/1542"
    articulo: "77"
    apartado: "3"
  idioma: en
  tags: [batteries, qr]

- id: batteries-annex-xiii-public
  query: "¿Qué información del pasaporte de batería es accesible al público?"
  expected_citation:
    reglamento: "UE 2023/1542"
    articulo: "Annex XIII"
  idioma: es
  tags: [batteries, annex-xiii, public]

- id: batteries-annex-xiii-legitimate
  query: "Which battery passport information is accessible only to those with a legitimate interest?"
  expected_citation:
    reglamento: "UE 2023/1542"
    articulo: "Annex XIII"
  idioma: en
  tags: [batteries, annex-xiii, legitimate]

- id: batteries-objeto-art1
  query: "¿Cuál es el objeto del reglamento de baterías?"
  expected_citation:
    reglamento: "UE 2023/1542"
    articulo: "1"
  idioma: es
  tags: [batteries, objeto]

- id: batteries-scope-art1-en
  query: "What is the subject matter of the batteries regulation?"
  expected_citation:
    reglamento: "UE 2023/1542"
    articulo: "1"
  idioma: en
  tags: [batteries, alcance]

- id: cirpass-product-class
  query: "What is a Product in the CIRPASS-2 Core Ontology?"
  expected_citation:
    reglamento: "CIRPASS-2 Core"
    articulo: "Product"
  idioma: en
  tags: [cirpass]

- id: cirpass-material-class
  query: "How does CIRPASS-2 define a Material?"
  expected_citation:
    reglamento: "CIRPASS-2 Core"
    articulo: "Material"
  idioma: en
  tags: [cirpass]

- id: gs1-uri-syntax
  query: "What is the URI syntax of GS1 Digital Link?"
  expected_citation:
    reglamento: "GS1 Digital Link 1.3.0"
    articulo: "sección 2"
  idioma: en
  tags: [gs1, uri]

- id: gs1-identifier-mappings
  query: "How does GS1 Digital Link map Application Identifiers to URIs?"
  expected_citation:
    reglamento: "GS1 Digital Link 1.3.0"
    articulo: "sección 3"
  idioma: en
  tags: [gs1, ai]

- id: iso-15459-part-4-products
  query: "What ISO standard covers unique identification of individual products?"
  expected_citation:
    reglamento: "ISO/IEC 15459"
    articulo: "Part 4"
  idioma: en
  tags: [iso, identificador]

- id: iso-15459-parte-1-es
  query: "¿Qué norma ISO especifica la identificación única de unidades de transporte?"
  expected_citation:
    reglamento: "ISO/IEC 15459"
    articulo: "Part 1"
  idioma: es
  tags: [iso, identificador]
```

- [ ] **Step 2: Crear `backend/src/app/rag/eval/__init__.py`**

```python
"""Evaluación del RAG: dataset de queries y métricas (F2-04)."""

from app.rag.eval.dataset import (
    DatasetEntry,
    ExpectedCitation,
    load_queries,
    render_expected_citation,
)

__all__ = [
    "DatasetEntry",
    "ExpectedCitation",
    "load_queries",
    "render_expected_citation",
]
```

- [ ] **Step 3: Crear `backend/src/app/rag/eval/dataset.py`**

```python
"""Carga y validación del dataset de queries de calidad RAG."""

from pathlib import Path

import yaml
from pydantic import BaseModel

from app.rag.schema import Language


class ExpectedCitation(BaseModel):
    reglamento: str
    articulo: str
    apartado: str | None = None


class DatasetEntry(BaseModel):
    id: str
    query: str
    expected_citation: ExpectedCitation
    idioma: Language
    tags: list[str] = []


_DEFAULT_PATH = Path(__file__).resolve().parents[3] / "tests" / "rag" / "queries.yaml"


def load_queries(path: Path | None = None) -> list[DatasetEntry]:
    yaml_path = path or _DEFAULT_PATH
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    return [DatasetEntry.model_validate(entry) for entry in raw]


def render_expected_citation(citation: ExpectedCitation) -> str:
    """Renderiza la cita esperada en el mismo formato que `format_citation()`."""
    base = f"Reglamento {citation.reglamento}, Art. {citation.articulo}"
    return f"{base}.{citation.apartado}" if citation.apartado else base
```

- [ ] **Step 4: Verificar que el YAML se carga sin errores**

Run: `cd backend && uv run python -c "from app.rag.eval import load_queries; q = load_queries(); print(len(q), 'queries')"`
Expected: `21 queries` (o el número exacto que tenga el YAML).

- [ ] **Step 5: Lint**

Run: `cd backend && uv run ruff check src/app/rag/eval/ && uv run ruff format src/app/rag/eval/`
Expected: All checks passed.

- [ ] **Step 6: Commit**

```bash
git add backend/tests/rag/queries.yaml backend/src/app/rag/eval/
git commit -m "$(cat <<'EOF'
feat(rag): dataset de 21 queries de calidad + loader (F2-04)

queries.yaml: 8 sobre ESPR, 8 sobre baterías (4 sobre Art. 77 +
Annex XIII), 2 CIRPASS-2, 2 GS1, 2 ISO 15459. 10 es + 11 en.
load_queries() valida con pydantic; render_expected_citation()
reproduce el formato exacto de format_citation() para comparar.
EOF
)"
```

---

## Task 12: Tests de validación del dataset (no xfail) (TDD)

**Files:**
- Create: `backend/tests/rag/test_query_dataset.py`

- [ ] **Step 1: Escribir tests de validación**

Crear `backend/tests/rag/test_query_dataset.py`:

```python
"""Tests del dataset de queries F2-04. Corren siempre, NO xfail."""

from collections import Counter

from app.rag.eval import DatasetEntry, load_queries


def test_dataset_loads_and_validates() -> None:
    entries = load_queries()
    assert len(entries) >= 20, "F2-04 exige ≥20 queries"
    assert len(entries) <= 30, "F2-04 exige ≤30 queries"
    for e in entries:
        assert isinstance(e, DatasetEntry)


def test_dataset_no_duplicate_ids() -> None:
    entries = load_queries()
    ids = [e.id for e in entries]
    duplicates = [k for k, c in Counter(ids).items() if c > 1]
    assert not duplicates, f"IDs duplicados: {duplicates}"


def test_dataset_distribution_by_reglamento() -> None:
    entries = load_queries()
    by_reg = Counter(e.expected_citation.reglamento for e in entries)
    assert by_reg["UE 2024/1781"] >= 8, "≥8 queries sobre ESPR"
    assert by_reg["UE 2023/1542"] >= 8, "≥8 queries sobre baterías"
    assert by_reg["CIRPASS-2 Core"] >= 2, "≥2 sobre CIRPASS-2"
    assert by_reg["GS1 Digital Link 1.3.0"] >= 2, "≥2 sobre GS1"
    assert by_reg["ISO/IEC 15459"] >= 2, "≥2 sobre ISO 15459"


def test_dataset_batteries_covers_art77_or_annex_xiii() -> None:
    entries = load_queries()
    art77_or_annex = [
        e for e in entries
        if e.expected_citation.reglamento == "UE 2023/1542"
        and e.expected_citation.articulo in {"77", "Annex XIII"}
    ]
    assert len(art77_or_annex) >= 3, "≥3 queries sobre Art. 77 o Annex XIII de baterías"


def test_dataset_language_balance() -> None:
    entries = load_queries()
    by_lang = Counter(e.idioma for e in entries)
    total = len(entries)
    assert by_lang["es"] / total >= 0.40, "≥40% queries en castellano"
    assert by_lang["en"] / total >= 0.40, "≥40% queries en inglés"
```

- [ ] **Step 2: Run tests, verificar pass**

Run: `cd backend && uv run pytest tests/rag/test_query_dataset.py -v`
Expected: 5 passed.

- [ ] **Step 3: Lint**

Run: `cd backend && uv run ruff check tests/rag/test_query_dataset.py && uv run ruff format tests/rag/test_query_dataset.py`
Expected: All checks passed.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/rag/test_query_dataset.py
git commit -m "$(cat <<'EOF'
test(rag): validación estructural del dataset F2-04

Corren siempre (no xfail). Garantizan: ≥20 entradas, IDs únicos,
distribución mínima por reglamento (8 ESPR / 8 baterías / 2 CIRPASS
/ 2 GS1 / 2 ISO), ≥3 queries sobre Art. 77 o Annex XIII (puntos
críticos del DPP de batería), ≥40% en cada idioma.
EOF
)"
```

---

## Task 13: Tests de calidad del retrieval (xfail strict=False) (TDD)

**Files:**
- Create: `backend/tests/rag/test_retrieval_quality.py`

- [ ] **Step 1: Escribir tests xfail**

Crear `backend/tests/rag/test_retrieval_quality.py`:

```python
"""Tests de calidad del retrieval — F2-04.

Estos tests llaman al stub `search_corpus()` definido en
`app.rag.schema`. Hasta que F2-03 implemente la versión real, el
stub lanza `NotImplementedError` → cada test cae como `xfail`.

Cuando F2-03 mergee a develop y entre a esta rama, los tests pasarán
automáticamente y aparecerán como `XPASS`. En ese momento se retira
la marca `xfail` en un PR puente.

Por qué `strict=False`: queremos que CI siga verde cuando los tests
pasen (XPASS) sin que el equipo tenga que rebotar al test runner.
"""

from dataclasses import dataclass

import pytest

from app.rag.eval import DatasetEntry, load_queries, render_expected_citation
from app.rag.schema import Filters, search_corpus


XFAIL_REASON = (
    "Requiere F2-03 (search_corpus implementado). "
    "Retirar marca al mergear F2-03 a develop."
)


@dataclass
class EvalSummary:
    total: int
    correct: int

    @property
    def top3_accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0


def _expected_in_results(entry: DatasetEntry, citations: list[str]) -> bool:
    expected = render_expected_citation(entry.expected_citation)
    return any(expected in c for c in citations)


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
@pytest.mark.parametrize("entry", load_queries(), ids=lambda e: e.id)
def test_expected_citation_in_top3(entry: DatasetEntry) -> None:
    results = search_corpus(
        entry.query,
        top_k=3,
        filters=Filters(idioma=entry.idioma),
    )
    citations = [r.cita for r in results]
    assert _expected_in_results(entry, citations), (
        f"Esperado '{render_expected_citation(entry.expected_citation)}' en top-3, "
        f"obtenido: {citations}"
    )


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
def test_top3_accuracy_over_80_percent() -> None:
    entries = load_queries()
    correct = 0
    for entry in entries:
        results = search_corpus(
            entry.query,
            top_k=3,
            filters=Filters(idioma=entry.idioma),
        )
        citations = [r.cita for r in results]
        if _expected_in_results(entry, citations):
            correct += 1
    summary = EvalSummary(total=len(entries), correct=correct)
    assert summary.top3_accuracy >= 0.80, (
        f"Top-3 accuracy = {summary.top3_accuracy:.0%}, esperado ≥80%"
    )
```

- [ ] **Step 2: Run tests, verificar xfail**

Run: `cd backend && uv run pytest tests/rag/test_retrieval_quality.py -v`
Expected: cada test marcado XFAIL (la firma `search_corpus()` lanza `NotImplementedError`). Resumen al final: "22 xfailed" (21 parametrized + 1 aggregate), 0 failed.

- [ ] **Step 3: Verificar tiempo total <60s para `tests/rag/`**

Run: `cd backend && uv run pytest tests/rag/ -q`
Expected: todo verde (passed + xfailed), tiempo total <30 s.

- [ ] **Step 4: Lint**

Run: `cd backend && uv run ruff check tests/rag/test_retrieval_quality.py && uv run ruff format tests/rag/test_retrieval_quality.py`
Expected: All checks passed.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/rag/test_retrieval_quality.py
git commit -m "$(cat <<'EOF'
test(rag): calidad de retrieval xfail strict=False (F2-04)

22 tests (21 parametrizados + 1 agregado): top-3 contiene la cita
esperada y ≥80% accuracy global. Mientras F2-03 no exista,
search_corpus() lanza NotImplementedError → todos xfail → CI verde.
Cuando F2-03 aterrice, XPASS automático → el equipo retira marcas
en PR puente.
EOF
)"
```

---

## Task 14: Badge de calidad RAG + integración en README + CI hook (TDD light)

**Files:**
- Create: `backend/scripts/__init__.py` (si no existe — ya existe en el repo, verificar)
- Create: `backend/scripts/rag_quality_badge.py`
- Create: `backend/tests/test_rag_quality_badge.py`
- Modify: `README.md` (raíz)

- [ ] **Step 1: Verificar scripts/__init__.py existe**

Run: `ls backend/scripts/__init__.py`
Expected: el fichero existe (lo creó F1).

- [ ] **Step 2: Escribir test del script de badge**

Crear `backend/tests/test_rag_quality_badge.py`:

```python
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
            {"outcome": "failed"},
        ]
    }
    report_path = tmp_path / "rag.json"
    report_path.write_text(json.dumps(report))

    summary = summarize_pytest_report(report_path)
    assert summary.total == 4
    assert summary.passed == 3
    assert summary.failed == 1
    assert summary.status == "warn"   # 75% < 80%


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
    assert "F2-03" in md


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
```

- [ ] **Step 3: Run test, verificar fallo**

Run: `cd backend && uv run pytest tests/test_rag_quality_badge.py -v`
Expected: ImportError.

- [ ] **Step 4: Implementar `scripts/rag_quality_badge.py`**

Crear `backend/scripts/rag_quality_badge.py`:

```python
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
        return "![RAG quality](https://img.shields.io/badge/RAG_quality-pendiente_(F2--03)-lightgrey)"
    if status == "fail":
        return "![RAG quality](https://img.shields.io/badge/RAG_quality-failing-red)"
    color = "brightgreen" if status == "ok" else "yellow"
    return (
        f"![RAG quality](https://img.shields.io/badge/RAG_quality-{percent}%25_top--3-{color})"
    )


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
```

- [ ] **Step 5: Run test, verificar pass**

Run: `cd backend && uv run pytest tests/test_rag_quality_badge.py -v`
Expected: 7 passed.

- [ ] **Step 6: Insertar marcadores HTML del badge en `README.md` (raíz)**

Editar `README.md` raíz. Localizar el área donde ya viven otros badges (al inicio, debajo del título). Añadir entre marcadores HTML:

```html
<!-- RAG_QUALITY_BADGE:START -->
![RAG quality](https://img.shields.io/badge/RAG_quality-pendiente_(F2--03)-lightgrey)
<!-- RAG_QUALITY_BADGE:END -->
```

- [ ] **Step 7: Probar el script contra los marcadores reales**

Run: `cd backend && uv run pytest tests/rag/test_retrieval_quality.py --json-report --json-report-file=/tmp/rag.json -q && cd backend && uv run python -m scripts.rag_quality_badge --report /tmp/rag.json --readme ../README.md`
Expected: imprime "RAG quality badge: status=pending percent=None → ../README.md". El README mantiene el badge "pendiente (F2-03)".

- [ ] **Step 8: Lint**

Run: `cd backend && uv run ruff check scripts/rag_quality_badge.py tests/test_rag_quality_badge.py && uv run ruff format scripts/rag_quality_badge.py tests/test_rag_quality_badge.py`
Expected: All checks passed.

- [ ] **Step 9: Verificar suite completa final**

Run: `cd backend && uv run pytest -q`
Expected: todos los tests verde. Tiempo total <30s.

- [ ] **Step 10: Commit**

```bash
git add backend/scripts/rag_quality_badge.py backend/tests/test_rag_quality_badge.py README.md
git commit -m "$(cat <<'EOF'
feat(rag): badge de calidad RAG en README (F2-04)

scripts/rag_quality_badge.py lee el JSON de pytest-json-report y
actualiza el README entre marcadores HTML
<!-- RAG_QUALITY_BADGE:START/END -->.

Estados:
  pending  todos los tests xfailed (F2-03 aún no aterrizó)
  ok       passed/total ≥80%  (verde)
  warn     passed/total <80%  (ámbar)
  fail     algún test failed  (rojo)

En esta rama el badge dice "pendiente (F2-03)" hasta que la rama
de F2-03 mergee a develop y se rebobine sobre f2_01_04.
EOF
)"
```

---

## Task 15: Smoke test real + README ingest section + cierre

**Files:**
- Modify: `README.md` (raíz)
- Modify: `backend/README.md` (si existe — verificar)

- [ ] **Step 1: Smoke test real (manual, NO en CI)**

Run: `cd backend && uv run python -m app.rag.ingest --only iso-15459`
Expected: imprime "✓ iso-15459.es: 6 fragments" y "✓ iso-15459.en: 6 fragments". Exit 0. Ficheros aparecen en `backend/data/corpus/iso-15459.{es,en}.jsonl`.

- [ ] **Step 2: Verificar JSONL real producido**

Run: `head -1 backend/data/corpus/iso-15459.es.jsonl | uv run python -c "import json,sys; print(json.loads(sys.stdin.read())['articulo'])"`
Expected: "Part 1".

- [ ] **Step 3: Smoke test EUR-Lex (con red)**

Run: `cd backend && uv run python -m app.rag.ingest --only ue-2024-1781 --lang es`
Expected: descarga del HTML real (primera vez), parsea, escribe JSONL. Exit 0. Si EUR-Lex está caído, exit 1 (no bloqueante).

Run: `wc -l backend/data/corpus/ue-2024-1781.es.jsonl`
Expected: >100 líneas (Reg. ESPR tiene >50 artículos con varios apartados cada uno).

- [ ] **Step 4: Validar que los Fragment producidos cargan correctamente**

Run: `cd backend && uv run python -c "from app.rag.schema import Fragment; import json; lines = open('data/corpus/ue-2024-1781.es.jsonl').readlines(); fragments = [Fragment.model_validate_json(l) for l in lines]; print(f'{len(fragments)} fragments válidos; primer art:', fragments[0].articulo); from app.rag.schema import format_citation; print('cita:', format_citation(fragments[0]))"`
Expected: imprime nº de fragments y la cita formateada del primero.

- [ ] **Step 5: Añadir sección "Corpus normativo" al README raíz**

Editar `README.md` raíz. Añadir una sección bajo "Comandos" (o equivalente) con el contenido siguiente:

```markdown
### Corpus normativo (RAG)

El corpus regulatorio europeo se descarga y persiste con:

\`\`\`bash
make ingest                     # ingiere todo (es + en, todas las fuentes)
make ingest -- --only iso-15459 # solo una fuente
\`\`\`

Sources:
- Reg. UE 2024/1781 (ESPR) — EUR-Lex, es + en
- Reg. UE 2023/1542 (baterías, incluye Art. 77 y Annex XIII) — EUR-Lex, es + en
- Actos delegados ESPR publicados — EUR-Lex (lista declarativa)
- CIRPASS-2 Core Ontology — JSON-LD, en
- GS1 Digital Link 1.3.0 — HTML público, en
- ISO/IEC 15459-1..6 — fragmentos-stub con abstract público + URL canónica (texto bajo licencia ISO no se redistribuye)

Salida: \`backend/data/corpus/{slug}.{lang}.jsonl\`. F2-02 consume desde ese directorio.

Exit codes:
- \`0\` todo OK
- \`1\` alguna source falló por red; el resto se completó
- \`2\` regresión de parser (HTML cambió en EUR-Lex)
```

(Reemplazar las triple-backtick escapadas según convenga al fichero real.)

- [ ] **Step 6: Limpiar JSONL del smoke (no commitar el corpus)**

Run: `rm -rf backend/data/corpus/`
Expected: `data/corpus/` desaparece. `git status` no muestra cambios bajo `backend/data/`.

- [ ] **Step 7: Verificar suite completa final**

Run: `cd backend && uv run pytest -q && uv run ruff check && uv run ruff format --check`
Expected: All tests pass, ruff clean.

- [ ] **Step 8: Commit final**

```bash
git add README.md
git commit -m "$(cat <<'EOF'
docs(readme): añade sección Corpus normativo (F2-01)

Documenta `make ingest`, las 6 sources del corpus, el formato de
salida data/corpus/{slug}.{lang}.jsonl que F2-02 consumirá y los
exit codes del CLI.
EOF
)"
```

- [ ] **Step 9: Push (decisión del usuario, no auto)**

Run: `git log --oneline origin/f2_01_04..HEAD 2>/dev/null || git log --oneline -20`

Verificar la lista de commits propios de la rama. **No pushear automáticamente** — el usuario decide cuándo abrir PR a `develop`.

---

## Self-Review

He revisado el plan contra el spec:

**1. Spec coverage:**
- Alcance corpus completo ✓ (T4 ISO, T5/T6/T7 EUR-Lex, T8 CIRPASS, T9 GS1)
- Fragmentos-stub ISO ✓ (T4, sin red, abstract + URL)
- Descarga HTML EUR-Lex en runtime ✓ (T3 cache, T5/T6 parser, T10 CLI)
- F2-04 xfail strict=False ✓ (T13)
- Adaptadores por fuente ✓ (estructura T1, implementaciones T4–T9)
- Badge en README ✓ (T14)
- F2-01 NO Langfuse ✓ (no aparece en ningún task — coherente)
- Idempotencia atómica ✓ (T2)
- Cache HTTP + force-refresh ✓ (T3)
- Tests fixtures locales (no red CI) ✓ (T5/T6/T8/T9)
- 21 queries con distribución mínima ✓ (T11, validada en T12)
- Smoke real manual ✓ (T15)

**2. Placeholders:**
- T7 Step 1 incluye un comando real para consultar EUR-Lex y rellenar `KNOWN_DELEGATED_ACTS`. Si la consulta devuelve vacío (caso real en 2026-05-25, hay que comprobar), la lista vacía es respuesta válida y el plan lo documenta.
- T15 Step 5 contiene contenido real para el README, no "TBD".
- No quedan "TODO", "TBD", "fill in" en el plan.

**3. Type consistency:**
- `Fragment` (de `app.rag.schema`) usado en todas las sources con los mismos campos.
- `Filters(idioma=...)` consistente en T11 y T13.
- `Language` literal `"es" | "en"` consistente en todos los módulos.
- `SOURCES` en `__main__.py` define tuplas `(slug, fn)` con firma uniforme `(client, lang, force_refresh) -> Iterable[Fragment]`.
- `KNOWN_DELEGATED_ACTS` consistente entre T7 (define) y T10 (consume).
- `DatasetEntry` / `ExpectedCitation` definidos en T11, consumidos en T12 y T13.

Plan listo.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-25-f2-01-04-corpus-ingesta-tests.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Mejor para este plan: 15 tareas TDD bien aisladas, cada una termina con commit verde.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints. Mejor si quieres ver el progreso real-time en la conversación.

Which approach?
