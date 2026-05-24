# Fase 1 — Fundación del sistema · Plan de implementación

> **Para agentes:** SUB-SKILL REQUERIDA: usa `superpowers:subagent-driven-development` (recomendado) o `superpowers:executing-plans` para ejecutar este plan tarea a tarea. Los pasos usan checkboxes (`- [ ]`) para tracking.

**Objetivo:** Levantar el monorepo de PasaporteAbierto con backend FastAPI, frontend Next.js, persistencia SQLite, observabilidad Langfuse, router de modelos LiteLLM y sistema de plugins YAML, de modo que `docker compose up` arranque todo en una máquina nueva en ≤30 min.

**Arquitectura:** Monorepo con `backend/` (FastAPI 0.115 + Python 3.11 + SQLModel + Pydantic v2) y `frontend/` (Next.js 16 App Router + TypeScript + Tailwind + shadcn/ui), orquestados por `docker-compose.yml` con cuatro servicios (backend, frontend, langfuse, ollama opcional vía profile). Persistencia con SQLite + Alembic. Plugins regulatorios en `plugins/` como YAMLs validados contra un schema al arrancar. LLM accedido siempre vía un único wrapper sobre LiteLLM controlado por `MODEL_BACKEND`.

**Tech stack:**
- Backend: Python 3.11, uv (package manager), FastAPI 0.115, SQLModel, Pydantic v2, Alembic, ruff (lint), pytest + pytest-asyncio, LiteLLM, Langfuse SDK.
- Frontend: Node 20, pnpm, Next.js 16, TypeScript estricto, Tailwind CSS, shadcn/ui, biome (lint+format), vitest.
- Infra: Docker + docker compose, Langfuse self-hosted, Ollama (opt-in profile).

---

## Mapa de archivos

### Backend (`backend/`)
- `pyproject.toml`, `.python-version`, `uv.lock` — gestión deps con uv.
- `Dockerfile` — imagen del backend.
- `src/app/main.py` — instancia FastAPI, incluye routers.
- `src/app/config.py` — `Settings` con pydantic-settings (lee `.env`).
- `src/app/api/v1/router.py` — agregador de rutas v1.
- `src/app/api/v1/health.py` — endpoint `GET /api/v1/health`.
- `src/app/db/session.py` — engine SQLModel y dependency `get_session`.
- `src/app/models/{sessions,documents,extracted_fields,audit_log,published_dpps}.py` — un archivo por tabla.
- `src/app/plugins/loader.py` — carga y valida YAMLs contra `plugins/_schema.yaml`.
- `src/app/llm/router.py` — wrapper único `llm.complete(...)` sobre LiteLLM.
- `src/app/observability/langfuse_client.py` — init del cliente Langfuse.
- `src/app/observability/decorators.py` — `@trace_classifier`, `@trace_collector`, `@trace_chat`.
- `alembic.ini`, `alembic/env.py`, `alembic/versions/*.py` — migraciones.
- `scripts/seed.py`, `scripts/reset_db.py` — utilidades de DB.
- `tests/test_health.py`, `tests/test_models.py`, `tests/test_plugin_loader.py`, `tests/test_batteries_plugin.py`, `tests/test_llm_router.py`, `tests/test_decorators.py`.

### Frontend (`frontend/`)
- `package.json`, `pnpm-lock.yaml`, `tsconfig.json`, `next.config.ts`, `tailwind.config.ts`, `postcss.config.js`, `biome.json`.
- `app/layout.tsx`, `app/page.tsx`, `app/globals.css` — shell mínimo.
- `Dockerfile` — imagen del frontend.

### Raíz del repo
- `docker-compose.yml` — cuatro servicios + profile `ollama`.
- `.env.example` — variables documentadas.
- `Makefile` — atajos (`make up`, `make test`, `make seed`).
- `plugins/_schema.yaml` — interfaz del plugin.
- `plugins/batteries.yaml` — plugin del Reglamento UE 2023/1542.
- `README.md` — guía de setup ≤30 min.

---

## Mapa de tickets ↔ tareas

| Ticket | Tarea(s) |
|---|---|
| F1-01 Scaffolding monorepo | T1 (backend shell) + T2 (frontend shell) + T3 (docker compose) |
| F1-02 Modelo SQLite | T4 |
| F1-03 Plugins YAML | T5 (schema + loader) + **T5.1 (access_level + identifier_scheme)** + T6 (batteries.yaml conforme Annex XIII) |
| F1-04 Router LiteLLM | T7 |
| F1-05 Langfuse + decoradores | T8 |
| Cierre F1 | T9 (README + verificación 30-min) |

T1 es prerrequisito de todo lo demás. T2 y T3 dependen de T1. T4 y T5 son independientes y pueden correr en paralelo tras T3. **T5.1 depende de T5 commiteado; T6 depende de T5.1 commiteado** (la nueva sección del schema condiciona la forma del plugin). T7 y T8 pueden correr en paralelo tras T3. T9 cierra.

---

## Task 1 — Backend FastAPI mínimo con health endpoint

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.python-version`
- Create: `backend/src/app/__init__.py`
- Create: `backend/src/app/config.py`
- Create: `backend/src/app/main.py`
- Create: `backend/src/app/api/__init__.py`
- Create: `backend/src/app/api/v1/__init__.py`
- Create: `backend/src/app/api/v1/router.py`
- Create: `backend/src/app/api/v1/health.py`
- Test: `backend/tests/test_health.py`
- Create: `backend/ruff.toml`

- [ ] **Paso 1.1 — Inicializar proyecto con uv**

```bash
cd backend
echo "3.11" > .python-version
uv init --no-readme --no-workspace
```

Edita el `pyproject.toml` resultante para que quede así:

```toml
[project]
name = "pasaporteabierto-backend"
version = "0.1.0"
description = "Backend FastAPI para PasaporteAbierto"
requires-python = ">=3.11,<3.12"
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
]

[dependency-groups]
dev = [
    "pytest==8.*",
    "pytest-asyncio==0.24.*",
    "ruff==0.7.*",
    "pytest-cov==5.*",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
pythonpath = ["src"]
```

```bash
uv sync
```

- [ ] **Paso 1.2 — Configurar ruff**

Crea `backend/ruff.toml`:

```toml
line-length = 100
target-version = "py311"

[lint]
select = ["E", "F", "I", "UP", "B", "SIM", "RUF"]
ignore = ["E501"]  # line-length la maneja el formatter

[format]
quote-style = "double"
```

- [ ] **Paso 1.3 — Test de health endpoint (rojo)**

Crea `backend/tests/__init__.py` vacío y `backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_version_model_and_backend():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert "version" in payload
    assert "model" in payload
    assert "backend" in payload


def test_health_reflects_env_backend(monkeypatch):
    monkeypatch.setenv("MODEL_BACKEND", "ollama:qwen2.5:14b")
    # Reimport settings to pick env up
    from importlib import reload

    from app import config

    reload(config)
    response = client.get("/api/v1/health")
    assert response.json()["backend"] == "ollama:qwen2.5:14b"
```

- [ ] **Paso 1.4 — Verificar que falla**

```bash
uv run pytest tests/test_health.py -v
```

Esperado: `ModuleNotFoundError: No module named 'app'` (porque no existe aún).

- [ ] **Paso 1.5 — Crear `config.py`**

Crea `backend/src/app/__init__.py` con `__version__ = "0.1.0"` y `backend/src/app/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    model_backend: str = "ollama:qwen2.5:14b"
    database_url: str = "sqlite:///./pasaporteabierto.db"
    langfuse_host: str = "http://localhost:3001"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""


settings = Settings()
```

- [ ] **Paso 1.6 — Crear el router de health**

`backend/src/app/api/__init__.py` vacío. `backend/src/app/api/v1/__init__.py` vacío.

`backend/src/app/api/v1/health.py`:

```python
from fastapi import APIRouter

from app import __version__
from app.config import settings

router = APIRouter()


@router.get("/health")
def health() -> dict:
    backend = settings.model_backend
    model = backend.split(":", 1)[1] if ":" in backend else backend
    return {
        "version": __version__,
        "model": model,
        "backend": backend,
    }
```

`backend/src/app/api/v1/router.py`:

```python
from fastapi import APIRouter

from app.api.v1 import health

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
```

- [ ] **Paso 1.7 — Crear `main.py`**

`backend/src/app/main.py`:

```python
from fastapi import FastAPI

from app.api.v1.router import api_router

app = FastAPI(title="PasaporteAbierto", version="0.1.0")
app.include_router(api_router)
```

- [ ] **Paso 1.8 — Verificar que el test pasa**

```bash
uv run pytest tests/test_health.py -v
```

Esperado: 2 tests PASS.

- [ ] **Paso 1.9 — Arrancar el server manualmente como sanity check**

```bash
uv run uvicorn app.main:app --reload --port 8000
```

En otra terminal:
```bash
curl -s http://localhost:8000/api/v1/health | python -m json.tool
```

Esperado: JSON con `version`, `model`, `backend`. Mata el server con Ctrl+C.

- [ ] **Paso 1.10 — Commit**

```bash
git add backend/
git commit -m "feat(backend): scaffold FastAPI con health endpoint (F1-01)"
```

---

## Task 2 — Frontend Next.js mínimo

**Files:**
- Create: `frontend/package.json`, `frontend/pnpm-lock.yaml`, `frontend/tsconfig.json`, `frontend/next.config.ts`, `frontend/tailwind.config.ts`, `frontend/postcss.config.js`, `frontend/biome.json`
- Create: `frontend/app/layout.tsx`, `frontend/app/page.tsx`, `frontend/app/globals.css`

- [ ] **Paso 2.1 — Scaffolding Next.js 16 con pnpm**

```bash
cd ..  # volver a raíz del repo
pnpm dlx create-next-app@16 frontend \
  --typescript \
  --tailwind \
  --app \
  --src-dir=false \
  --import-alias="@/*" \
  --no-eslint \
  --use-pnpm
```

Confirma cuando te pregunte por Turbopack: **Yes**.

- [ ] **Paso 2.2 — Instalar biome y vitest**

```bash
cd frontend
pnpm add -D @biomejs/biome vitest @vitejs/plugin-react @testing-library/react @testing-library/jest-dom jsdom
```

Crea `frontend/biome.json`:

```json
{
  "$schema": "https://biomejs.dev/schemas/1.9.4/schema.json",
  "organizeImports": { "enabled": true },
  "linter": {
    "enabled": true,
    "rules": { "recommended": true }
  },
  "formatter": {
    "enabled": true,
    "indentStyle": "space",
    "indentWidth": 2,
    "lineWidth": 100
  },
  "files": { "ignore": [".next", "node_modules"] }
}
```

Edita `package.json` para los scripts (añade dentro del bloque existente):

```json
{
  "scripts": {
    "dev": "next dev --turbo",
    "build": "next build",
    "start": "next start",
    "lint": "biome check .",
    "format": "biome format --write .",
    "test": "vitest run",
    "test:watch": "vitest"
  }
}
```

- [ ] **Paso 2.3 — Página inicial con health probe**

Reemplaza `frontend/app/page.tsx`:

```tsx
async function getHealth() {
  const url = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  try {
    const res = await fetch(`${url}/api/v1/health`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as { version: string; model: string; backend: string };
  } catch {
    return null;
  }
}

export default async function Home() {
  const health = await getHealth();
  return (
    <main className="min-h-screen p-12">
      <h1 className="text-3xl font-bold">PasaporteAbierto</h1>
      <p className="text-sm text-gray-600 mt-2">
        Pasaporte Digital de Producto · Reglamento UE 2024/1781
      </p>
      <section className="mt-8 rounded-lg border p-4">
        <h2 className="font-semibold mb-2">Backend</h2>
        {health ? (
          <ul className="text-sm">
            <li>version: {health.version}</li>
            <li>model: {health.model}</li>
            <li>backend: {health.backend}</li>
          </ul>
        ) : (
          <p className="text-sm text-red-600">Backend no responde en /api/v1/health</p>
        )}
      </section>
    </main>
  );
}
```

- [ ] **Paso 2.4 — Verificar arranque local**

```bash
pnpm dev
```

Abre `http://localhost:3000`. Esperado: título, descripción y el bloque "Backend no responde" (si el backend de la tarea anterior no está corriendo) o los datos del health endpoint si lo arrancas en paralelo. Mata el server con Ctrl+C.

- [ ] **Paso 2.5 — Verificar build**

```bash
pnpm build
```

Esperado: build exitoso sin errores de TypeScript.

- [ ] **Paso 2.6 — Commit**

```bash
cd ..
git add frontend/
git commit -m "feat(frontend): scaffold Next.js 16 con probe del health del backend (F1-01)"
```

---

## Task 3 — Docker Compose con backend, frontend y Langfuse

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/.dockerignore`
- Create: `frontend/Dockerfile`
- Create: `frontend/.dockerignore`
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `Makefile`

- [ ] **Paso 3.1 — Dockerfile del backend**

Crea `backend/Dockerfile`:

```dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health').read()" || exit 1

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Crea `backend/.dockerignore`:

```
.venv
__pycache__
*.pyc
.pytest_cache
.ruff_cache
tests/
*.db
```

- [ ] **Paso 3.2 — Dockerfile del frontend**

Crea `frontend/Dockerfile`:

```dockerfile
FROM node:20-alpine AS deps
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

FROM node:20-alpine AS builder
WORKDIR /app
RUN corepack enable
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN pnpm build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN corepack enable
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 3000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:3000 > /dev/null || exit 1
CMD ["pnpm", "start"]
```

Crea `frontend/.dockerignore`:

```
node_modules
.next
.turbo
```

- [ ] **Paso 3.3 — docker-compose.yml**

Crea `docker-compose.yml` en la raíz:

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: .env
    volumes:
      - ./plugins:/app/plugins:ro
      - backend_data:/app/data
    depends_on:
      langfuse:
        condition: service_started

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://backend:8000
    depends_on:
      backend:
        condition: service_healthy

  langfuse:
    image: langfuse/langfuse:2
    ports:
      - "3001:3000"
    environment:
      DATABASE_URL: postgresql://postgres:postgres@langfuse-db:5432/langfuse
      NEXTAUTH_URL: http://localhost:3001
      NEXTAUTH_SECRET: ${LANGFUSE_NEXTAUTH_SECRET:-changeme-langfuse-secret}
      SALT: ${LANGFUSE_SALT:-changeme-langfuse-salt}
      TELEMETRY_ENABLED: "false"
    depends_on:
      langfuse-db:
        condition: service_healthy

  langfuse-db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: langfuse
    volumes:
      - langfuse_db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 10

  ollama:
    image: ollama/ollama:latest
    profiles: ["ollama"]
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  backend_data:
  langfuse_db_data:
  ollama_data:
```

> Nota: Postgres aparece sólo como dependencia *interna* de Langfuse self-hosted (lo exige su contenedor). El backend de PasaporteAbierto sigue usando SQLite — la decisión de "no Postgres para la app" se mantiene.

- [ ] **Paso 3.4 — `.env.example`**

Crea `.env.example` en la raíz:

```bash
# Backend de modelos (LiteLLM)
# Formatos válidos: ollama:qwen2.5:14b | ollama:llama3.1:8b | anthropic:claude-opus-4 | openai:gpt-4o
MODEL_BACKEND=ollama:qwen2.5:14b

# Persistencia (SQLite local)
DATABASE_URL=sqlite:////app/data/pasaporteabierto.db

# Langfuse self-hosted (las claves se generan en su UI tras el primer login)
LANGFUSE_HOST=http://langfuse:3000
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=

# Secretos de Langfuse self-hosted (cambia en producción)
LANGFUSE_NEXTAUTH_SECRET=changeme-langfuse-secret
LANGFUSE_SALT=changeme-langfuse-salt

# APIs comerciales opcionales (descomenta sólo si MODEL_BACKEND las usa)
# ANTHROPIC_API_KEY=
# OPENAI_API_KEY=
```

```bash
cp .env.example .env
```

- [ ] **Paso 3.5 — Makefile con atajos**

Crea `Makefile`:

```makefile
.PHONY: up down logs test seed reset health

up:
	docker compose up -d --build

up-ollama:
	docker compose --profile ollama up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

test:
	cd backend && uv run pytest -v
	cd frontend && pnpm test

health:
	@curl -s http://localhost:8000/api/v1/health | python -m json.tool

seed:
	cd backend && uv run python -m scripts.seed

reset:
	cd backend && uv run python -m scripts.reset_db
```

- [ ] **Paso 3.6 — Levantar y verificar el stack**

```bash
docker compose up -d --build
```

Espera ~30s a que arranquen todos los servicios y verifica:

```bash
curl -s http://localhost:8000/api/v1/health
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3001
```

Esperado: backend devuelve JSON, frontend devuelve 200, Langfuse devuelve 200/302.

- [ ] **Paso 3.7 — Bajar el stack**

```bash
docker compose down
```

- [ ] **Paso 3.8 — `.gitignore` actualizado**

Modifica `.gitignore` (en la raíz; ya existe vacío):

```
# Python
backend/.venv/
backend/__pycache__/
backend/.pytest_cache/
backend/.ruff_cache/
backend/*.db
backend/data/

# Node
frontend/node_modules/
frontend/.next/
frontend/.turbo/

# Entorno
.env

# Editor
.DS_Store
.idea/
.vscode/
```

- [ ] **Paso 3.9 — Commit**

```bash
git add backend/Dockerfile backend/.dockerignore frontend/Dockerfile frontend/.dockerignore docker-compose.yml .env.example Makefile .gitignore
git commit -m "feat(infra): docker compose con backend, frontend, langfuse y ollama opcional (F1-01)"
```

---

## Task 4 — Modelo de datos SQLite (5 tablas + Alembic + seed)

**Files:**
- Create: `backend/src/app/db/__init__.py`, `backend/src/app/db/session.py`
- Create: `backend/src/app/models/__init__.py`
- Create: `backend/src/app/models/sessions.py`, `documents.py`, `extracted_fields.py`, `audit_log.py`, `published_dpps.py`
- Create: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`, `backend/alembic/versions/0001_initial.py`
- Create: `backend/scripts/__init__.py`, `backend/scripts/seed.py`, `backend/scripts/reset_db.py`
- Test: `backend/tests/test_models.py`

- [ ] **Paso 4.1 — Test de migración y schema (rojo)**

`backend/tests/test_models.py`:

```python
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import inspect
from sqlmodel import Session, SQLModel, create_engine

EXPECTED_TABLES = {
    "sessions",
    "documents",
    "extracted_fields",
    "audit_log",
    "published_dpps",
}


@pytest.fixture
def engine(tmp_path: Path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    # Importa modelos para registrar metadata
    from app.models import audit_log, documents, extracted_fields, published_dpps, sessions  # noqa: F401

    SQLModel.metadata.create_all(engine)
    return engine


def test_all_five_tables_exist(engine):
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert EXPECTED_TABLES.issubset(tables), f"Faltan tablas: {EXPECTED_TABLES - tables}"


def test_audit_log_has_prev_hash_and_index(engine):
    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("audit_log")}
    assert "prev_hash" in columns
    assert "content_hash" in columns
    indexes = inspector.get_indexes("audit_log")
    assert any(idx["column_names"] == ["id"] or "id" in idx["column_names"] for idx in indexes) or \
        "id" in {c["name"] for c in inspector.get_columns("audit_log") if c.get("primary_key")}


def test_extracted_fields_provenance_canonical(engine):
    """Los tres estados deben caber: verified, self_declared, required_pending."""
    from app.models.extracted_fields import ExtractedField

    with Session(engine) as s:
        for provenance in ("verified", "self_declared", "required_pending"):
            ef = ExtractedField(
                session_id="sess-1",
                field_id="capacity_kwh",
                value="100",
                provenance=provenance,
                confidence=0.9,
            )
            s.add(ef)
        s.commit()
        results = s.exec("SELECT provenance FROM extracted_fields").all()  # type: ignore[arg-type]
        assert {r[0] for r in results} == {"verified", "self_declared", "required_pending"}


def test_alembic_upgrade_downgrade_reversible(tmp_path: Path):
    """La migración 0001 debe ser totalmente reversible."""
    db_path = tmp_path / "rev.db"
    env = {"DATABASE_URL": f"sqlite:///{db_path}"}
    backend_dir = Path(__file__).resolve().parents[1]
    base = ["uv", "run", "alembic", "-c", "alembic.ini"]

    subprocess.run([*base, "upgrade", "head"], cwd=backend_dir, env={**__import__("os").environ, **env}, check=True)
    subprocess.run([*base, "downgrade", "base"], cwd=backend_dir, env={**__import__("os").environ, **env}, check=True)
    # Tras downgrade no debe quedar ninguna de las 5 tablas
    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert not EXPECTED_TABLES.intersection(tables), "El downgrade no limpió todas las tablas"
```

- [ ] **Paso 4.2 — Verificar que falla**

```bash
cd backend
uv run pytest tests/test_models.py -v
```

Esperado: errores de import de `app.models.*`.

- [ ] **Paso 4.3 — DB session helper**

`backend/src/app/db/__init__.py` vacío. `backend/src/app/db/session.py`:

```python
from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


def init_db() -> None:
    """Sólo para tests/desarrollo — en runtime se usa Alembic."""
    SQLModel.metadata.create_all(engine)
```

- [ ] **Paso 4.4 — Los 5 modelos**

`backend/src/app/models/__init__.py`:

```python
from app.models.audit_log import AuditLogEntry
from app.models.documents import Document
from app.models.extracted_fields import ExtractedField
from app.models.published_dpps import PublishedDPP
from app.models.sessions import WizardSession

__all__ = ["AuditLogEntry", "Document", "ExtractedField", "PublishedDPP", "WizardSession"]
```

`backend/src/app/models/sessions.py`:

```python
from datetime import datetime
from typing import Optional

from sqlmodel import JSON, Column, Field, SQLModel


class WizardSession(SQLModel, table=True):
    __tablename__ = "sessions"

    id: str = Field(primary_key=True)
    progress: dict = Field(default_factory=dict, sa_column=Column(JSON))
    sector: Optional[str] = None
    plugin: Optional[str] = None
    classification_confidence: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

`backend/src/app/models/documents.py`:

```python
from datetime import datetime

from sqlmodel import Field, SQLModel


class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    doc_type: str  # datasheet | certificate | lca | sds | ce_declaration
    blob_path: str
    sha256: str = Field(index=True)
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
```

`backend/src/app/models/extracted_fields.py`:

```python
from sqlmodel import Field, SQLModel


class ExtractedField(SQLModel, table=True):
    __tablename__ = "extracted_fields"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    field_id: str = Field(index=True)
    value: str
    source_document_id: int | None = Field(default=None, foreign_key="documents.id")
    provenance: str  # "verified" | "self_declared" | "required_pending"
    confidence: float = 0.0
```

`backend/src/app/models/audit_log.py`:

```python
from datetime import datetime

from sqlmodel import JSON, Column, Field, SQLModel


class AuditLogEntry(SQLModel, table=True):
    __tablename__ = "audit_log"

    id: int | None = Field(default=None, primary_key=True, index=True)
    prev_hash: str | None = None  # null sólo en la primera entrada
    content_hash: str
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    operation: str  # classify | override | verify | publish | sign
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
```

`backend/src/app/models/published_dpps.py`:

```python
from datetime import datetime

from sqlmodel import JSON, Column, Field, SQLModel


class PublishedDPP(SQLModel, table=True):
    __tablename__ = "published_dpps"

    gs1_uri: str = Field(primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    jsonld: dict = Field(sa_column=Column(JSON))
    signature: str | None = None  # base64 Ed25519
    public_key: str | None = None
    published_at: datetime = Field(default_factory=datetime.utcnow)
```

- [ ] **Paso 4.5 — Inicializar Alembic**

```bash
cd backend
uv run alembic init alembic
```

Esto crea `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, `alembic/versions/`.

Edita `backend/alembic.ini`, en la sección `[alembic]` cambia:

```
script_location = alembic
sqlalchemy.url = sqlite:///./pasaporteabierto.db
```

(El `env.py` lo sobrescribiremos para leer del entorno.)

Sobrescribe `backend/alembic/env.py`:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from app.config import settings
from app.models import (  # noqa: F401  --- registro de metadata
    AuditLogEntry,
    Document,
    ExtractedField,
    PublishedDPP,
    WizardSession,
)

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # imprescindible para SQLite ALTER
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Paso 4.6 — Generar la migración 0001**

```bash
cd backend
uv run alembic revision --autogenerate -m "initial 5 tables"
```

Esto genera un archivo `backend/alembic/versions/<hash>_initial_5_tables.py`. Renómbralo a `0001_initial.py` y revisa que el `upgrade()` cree las 5 tablas y `downgrade()` haga el reverso simétrico. Si autogenerate olvida algún índice (clásico de SQLModel), añádelo a mano.

- [ ] **Paso 4.7 — Scripts de seed y reset**

`backend/scripts/__init__.py` vacío. `backend/scripts/reset_db.py`:

```python
"""Borra y recrea la DB desde cero usando Alembic."""

from pathlib import Path
import subprocess

from app.config import settings


def main() -> None:
    if settings.database_url.startswith("sqlite:///"):
        db_path = Path(settings.database_url.replace("sqlite:///", ""))
        if db_path.exists():
            db_path.unlink()
            print(f"Borrado: {db_path}")
    subprocess.run(["uv", "run", "alembic", "upgrade", "head"], check=True)
    print("Migraciones aplicadas.")


if __name__ == "__main__":
    main()
```

`backend/scripts/seed.py`:

```python
"""Seed mínimo: una sesión demo en estado paso 1."""

from datetime import datetime

from sqlmodel import Session

from app.db.session import engine, init_db
from app.models import WizardSession


def main() -> None:
    init_db()
    with Session(engine) as s:
        demo = WizardSession(
            id="demo-session-001",
            progress={"step": 1, "description": "Batería industrial de demo"},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        s.merge(demo)
        s.commit()
    print("Seed completado: sesión demo-session-001")


if __name__ == "__main__":
    main()
```

- [ ] **Paso 4.8 — Verificar tests**

```bash
cd backend
uv run pytest tests/test_models.py -v
```

Esperado: 4 tests PASS.

- [ ] **Paso 4.9 — Verificar seed manual**

```bash
cd backend
DATABASE_URL=sqlite:///./dev.db uv run python -m scripts.reset_db
DATABASE_URL=sqlite:///./dev.db uv run python -m scripts.seed
sqlite3 dev.db "SELECT id, sector FROM sessions;"
```

Esperado: una fila `demo-session-001|`. Limpia con `rm dev.db`.

- [ ] **Paso 4.10 — Commit**

```bash
cd ..
git add backend/src/app/db backend/src/app/models backend/alembic backend/alembic.ini backend/scripts backend/tests/test_models.py
git commit -m "feat(db): 5 tablas SQLModel + Alembic reversible + seed (F1-02)"
```

---

## Task 5 — Schema de plugins YAML + loader

**Files:**
- Create: `plugins/_schema.yaml`
- Create: `backend/src/app/plugins/__init__.py`
- Create: `backend/src/app/plugins/loader.py`
- Test: `backend/tests/test_plugin_loader.py`
- Test: `backend/tests/fixtures/plugin_valid.yaml`
- Test: `backend/tests/fixtures/plugin_missing_field.yaml`
- Test: `backend/tests/fixtures/plugin_missing_citation.yaml`

- [ ] **Paso 5.1 — Definir el schema**

Crea `plugins/_schema.yaml`:

```yaml
# Schema canónico de plugins de sector ESPR.
# Cada plugin YAML en plugins/ debe cumplir esta estructura.

plugin:
  required: [name, regulation, version, fields, required_documents]
  properties:
    name: { type: string }
    regulation: { type: string }   # e.g. "EU 2023/1542"
    version: { type: string }      # semver
    description: { type: string }

fields:
  description: "Lista de campos del DPP exigidos por el sector"
  item_required: [id, type, required, citation]
  item_properties:
    id: { type: string }
    type: { type: string, enum: [string, number, integer, boolean, enum, repeater] }
    required: { type: boolean }
    citation:
      required: [regulation, article]
      properties:
        regulation: { type: string }
        article: { type: string }
    enum_values: { type: list, optional: true }
    validation: { type: string, optional: true }  # expresión opcional

required_documents:
  description: "Documentos que el Recolector necesita"
  item_required: [type, mandatory]
  item_properties:
    type: { type: string, enum: [datasheet, certificate, lca, sds, ce_declaration] }
    mandatory: { type: boolean }
    when: { type: string, optional: true }  # condición sobre campos del BOM

cross_validations:
  description: "Reglas adicionales que cruzan campos"
  optional: true
  item_required: [id, rule]
  item_properties:
    id: { type: string }
    rule: { type: string }
    message: { type: string }
```

> Nota: usamos un schema *descriptivo* (no JSON Schema formal) porque las reglas son simples y el loader las recorre directamente. Si en futuras fases necesitamos validación más rica, migrar a JSON Schema o pydantic.

- [ ] **Paso 5.2 — Fixtures de test**

Crea `backend/tests/fixtures/plugin_valid.yaml`:

```yaml
name: "demo-sector"
regulation: "EU 2024/1781"
version: "0.1.0"
description: "Plugin de prueba mínimo"

fields:
  - id: model_name
    type: string
    required: true
    citation:
      regulation: "EU 2024/1781"
      article: "Art. 7(1)"
  - id: weight_kg
    type: number
    required: false
    citation:
      regulation: "EU 2024/1781"
      article: "Annex II"

required_documents:
  - type: datasheet
    mandatory: true
  - type: certificate
    mandatory: false
```

`backend/tests/fixtures/plugin_missing_field.yaml`:

```yaml
name: "broken-sector"
regulation: "EU 2024/1781"
version: "0.1.0"

# OJO: faltan los apartados "fields" y "required_documents" obligatorios.
```

`backend/tests/fixtures/plugin_missing_citation.yaml`:

```yaml
name: "no-cite-sector"
regulation: "EU 2024/1781"
version: "0.1.0"

fields:
  - id: model_name
    type: string
    required: true
    # OJO: falta "citation" — cada campo debe declarar reglamento + artículo.

required_documents:
  - type: datasheet
    mandatory: true
```

- [ ] **Paso 5.3 — Test del loader (rojo)**

`backend/tests/test_plugin_loader.py`:

```python
from pathlib import Path

import pytest

from app.plugins.loader import Plugin, PluginValidationError, load_plugin

FIXTURES = Path(__file__).parent / "fixtures"


def test_loader_accepts_valid_plugin():
    plugin = load_plugin(FIXTURES / "plugin_valid.yaml")
    assert isinstance(plugin, Plugin)
    assert plugin.name == "demo-sector"
    assert plugin.regulation == "EU 2024/1781"
    assert len(plugin.fields) == 2
    assert plugin.fields[0].id == "model_name"
    assert plugin.fields[0].citation.article == "Art. 7(1)"


def test_loader_rejects_missing_required_section():
    with pytest.raises(PluginValidationError) as exc:
        load_plugin(FIXTURES / "plugin_missing_field.yaml")
    assert "fields" in str(exc.value).lower() or "required_documents" in str(exc.value).lower()


def test_loader_rejects_field_without_citation():
    with pytest.raises(PluginValidationError) as exc:
        load_plugin(FIXTURES / "plugin_missing_citation.yaml")
    assert "citation" in str(exc.value).lower()


def test_loader_lists_required_fields():
    plugin = load_plugin(FIXTURES / "plugin_valid.yaml")
    required_ids = [f.id for f in plugin.fields if f.required]
    assert required_ids == ["model_name"]
```

- [ ] **Paso 5.4 — Verificar que falla**

```bash
cd backend
uv run pytest tests/test_plugin_loader.py -v
```

Esperado: ImportError de `app.plugins.loader`.

- [ ] **Paso 5.5 — Implementar el loader**

`backend/src/app/plugins/__init__.py` vacío. `backend/src/app/plugins/loader.py`:

```python
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, ValidationError

DocType = Literal["datasheet", "certificate", "lca", "sds", "ce_declaration"]
FieldType = Literal["string", "number", "integer", "boolean", "enum", "repeater"]


class PluginValidationError(Exception):
    """Se eleva cuando un YAML no cumple `_schema.yaml`."""


class Citation(BaseModel):
    regulation: str
    article: str


class PluginField(BaseModel):
    id: str
    type: FieldType
    required: bool
    citation: Citation
    enum_values: list[str] | None = None
    validation: str | None = None


class RequiredDocument(BaseModel):
    type: DocType
    mandatory: bool
    when: str | None = None


class CrossValidation(BaseModel):
    id: str
    rule: str
    message: str | None = None


class Plugin(BaseModel):
    name: str
    regulation: str
    version: str
    description: str = ""
    fields: list[PluginField] = Field(default_factory=list)
    required_documents: list[RequiredDocument] = Field(default_factory=list)
    cross_validations: list[CrossValidation] = Field(default_factory=list)


def load_plugin(path: Path) -> Plugin:
    """Carga y valida un YAML de plugin. Eleva PluginValidationError si no cumple."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise PluginValidationError(f"{path.name}: el YAML debe ser un mapping en la raíz")

    for required_section in ("fields", "required_documents"):
        if required_section not in raw or raw[required_section] is None:
            raise PluginValidationError(
                f"{path.name}: falta sección obligatoria '{required_section}'"
            )

    try:
        return Plugin(**raw)
    except ValidationError as e:
        raise PluginValidationError(f"{path.name}: {e}") from e


def load_all_plugins(plugins_dir: Path) -> dict[str, Plugin]:
    """Carga todos los YAMLs de `plugins_dir` excepto `_schema.yaml`."""
    plugins: dict[str, Plugin] = {}
    for yaml_file in plugins_dir.glob("*.yaml"):
        if yaml_file.name.startswith("_"):
            continue
        plugin = load_plugin(yaml_file)
        plugins[plugin.name] = plugin
    return plugins
```

- [ ] **Paso 5.6 — Verificar tests verdes**

```bash
cd backend
uv run pytest tests/test_plugin_loader.py -v
```

Esperado: 4 tests PASS.

- [ ] **Paso 5.7 — Commit**

```bash
cd ..
git add plugins/_schema.yaml backend/src/app/plugins backend/tests/test_plugin_loader.py backend/tests/fixtures
git commit -m "feat(plugins): schema YAML + loader con validación (F1-03)"
```

---

## Task 5.1 — Extender el plugin schema con `access_level` y `identifier_scheme`

> **Razón:** la validación del plugin de baterías contra el texto oficial del Reglamento UE 2023/1542 (Art. 77 + Annex XIII + Anexo VI Parte A) reveló que el schema commiteado en T5 (`bdf4555`) no modela dos dimensiones obligatorias:
>
> 1. **`access_level` por campo** — el Annex XIII define 4 niveles de visibilidad (`public`, `legitimate_interest`, `authorities_only`, `individual`) que son ortogonales al `provenance`. Sin esto, el endpoint público del DPP expondría datos que la regulación exige restringir.
> 2. **`identifier_scheme` del plugin** — el Art. 77.3 obliga a ISO/IEC 15459-1/2/3/4/5/6 para baterías; GS1 Digital Link es solo válido como fallback genérico para sectores sin acto delegado específico.
>
> T5.1 extiende el schema con **backward compatibility** (defaults razonables: `access_level=public`, `identifier_scheme=gs1_digital_link`) para no romper los fixtures ni los tests existentes. Es prerrequisito de T6 — sin esto, `batteries.yaml` no se puede expresar fielmente.

**Files:**
- Modify: `plugins/_schema.yaml`
- Modify: `backend/src/app/plugins/loader.py`
- Modify: `backend/tests/test_plugin_loader.py`
- Modify: `backend/tests/fixtures/plugin_valid.yaml`
- Create: `backend/tests/fixtures/plugin_invalid_access_level.yaml`
- Create: `backend/tests/fixtures/plugin_invalid_identifier_scheme.yaml`

- [ ] **Paso 5.1.1 — Tests nuevos (rojos)**

Añadir a `backend/tests/test_plugin_loader.py` (al final, antes de cualquier fixture):

```python
def test_loader_accepts_access_level_legitimate_interest():
    """Un fixture con access_level != 'public' debe cargar y exponerlo correctamente."""
    plugin = load_plugin(FIXTURES / "plugin_valid.yaml")
    al = [f.access_level for f in plugin.fields]
    assert "legitimate_interest" in al, f"Esperaba algún campo con legitimate_interest, vi {al}"


def test_loader_defaults_access_level_to_public():
    """Un campo sin access_level explícito debe heredar 'public' (backward compat)."""
    plugin = load_plugin(FIXTURES / "plugin_valid.yaml")
    # El campo model_name del fixture NO declara access_level — debe ser 'public' por default
    model_name = next(f for f in plugin.fields if f.id == "model_name")
    assert model_name.access_level == "public"


def test_loader_rejects_invalid_access_level():
    """Valor fuera del enum debe ser rechazado por Pydantic Literal."""
    with pytest.raises(PluginValidationError) as exc:
        load_plugin(FIXTURES / "plugin_invalid_access_level.yaml")
    msg = str(exc.value).lower()
    assert "access_level" in msg or "literal" in msg or "no cumple el esquema" in msg


def test_loader_accepts_iso_iec_15459_identifier_scheme():
    """identifier_scheme debe aceptar iso_iec_15459 (obligatorio para baterías)."""
    plugin = load_plugin(FIXTURES / "plugin_valid.yaml")
    assert plugin.identifier_scheme in ("iso_iec_15459", "gs1_digital_link")


def test_loader_defaults_identifier_scheme_to_gs1_digital_link():
    """Un plugin sin identifier_scheme explícito hereda 'gs1_digital_link' (backward compat)."""
    # Los fixtures de error que no declaran identifier_scheme tienen que poder cargarse sin él
    # (el rechazo viene del error específico, no de la ausencia del campo nuevo)
    # Lo verificamos cargando el fixture original (cuando aún no añadamos identifier_scheme).
    # Después de Paso 5.1.3, plugin_valid.yaml SÍ lo declarará explícitamente.
    # Este test se ejecuta sobre un plugin construido manualmente en memoria:
    from app.plugins.loader import Plugin
    p = Plugin(name="x", regulation="y", version="0.0.0", fields=[], required_documents=[])
    assert p.identifier_scheme == "gs1_digital_link"


def test_loader_rejects_unknown_identifier_scheme():
    """identifier_scheme fuera del enum debe ser rechazado."""
    with pytest.raises(PluginValidationError) as exc:
        load_plugin(FIXTURES / "plugin_invalid_identifier_scheme.yaml")
    msg = str(exc.value).lower()
    assert "identifier_scheme" in msg or "literal" in msg or "no cumple el esquema" in msg
```

- [ ] **Paso 5.1.2 — Fixtures inválidos**

`backend/tests/fixtures/plugin_invalid_access_level.yaml`:

```yaml
name: "invalid-access-level-sector"
regulation: "EU 2024/1781"
version: "0.1.0"
identifier_scheme: "gs1_digital_link"

fields:
  - id: model_name
    type: string
    required: true
    access_level: not_a_real_level   # ← rechazado por Literal
    citation:
      regulation: "EU 2024/1781"
      article: "Art. 7(1)"

required_documents:
  - type: datasheet
    mandatory: true
```

`backend/tests/fixtures/plugin_invalid_identifier_scheme.yaml`:

```yaml
name: "invalid-identifier-scheme-sector"
regulation: "EU 2024/1781"
version: "0.1.0"
identifier_scheme: "carrier_pigeon"   # ← rechazado por Literal

fields:
  - id: model_name
    type: string
    required: true
    citation:
      regulation: "EU 2024/1781"
      article: "Art. 7(1)"

required_documents:
  - type: datasheet
    mandatory: true
```

- [ ] **Paso 5.1.3 — Actualizar fixture válido**

Modificar `backend/tests/fixtures/plugin_valid.yaml`:

```yaml
name: "demo-sector"
regulation: "EU 2024/1781"
version: "0.1.0"
description: "Plugin de prueba mínimo"
identifier_scheme: "gs1_digital_link"

fields:
  - id: model_name
    type: string
    required: true
    # access_level deliberadamente ausente para verificar default 'public'
    citation:
      regulation: "EU 2024/1781"
      article: "Art. 7(1)"
  - id: weight_kg
    type: number
    required: false
    access_level: legitimate_interest   # ejercita un valor distinto del default
    citation:
      regulation: "EU 2024/1781"
      article: "Annex II"

required_documents:
  - type: datasheet
    mandatory: true
  - type: certificate
    mandatory: false
```

- [ ] **Paso 5.1.4 — Verificar rojo**

```bash
cd backend
PATH="$HOME/.local/bin:$PATH" uv run pytest tests/test_plugin_loader.py -v
```

Esperado: los 6 tests nuevos fallan (AttributeError o assertion errors). Los 7 tests existentes pueden seguir verdes o fallar — depende de si el fixture actualizado en 5.1.3 rompió el test `test_loader_accepts_valid_plugin` (que ahora encuentra `access_level: legitimate_interest` en `weight_kg`). Si falla, se arreglará en el Paso 5.1.6 con la actualización del aserto. Es esperado en TDD.

- [ ] **Paso 5.1.5 — Extender `loader.py`**

En `backend/src/app/plugins/loader.py`:

```python
# Añadir bajo las definiciones existentes de DocType y FieldType:
AccessLevel = Literal["public", "legitimate_interest", "authorities_only", "individual"]
IdentifierScheme = Literal["gs1_digital_link", "iso_iec_15459"]


# Modificar PluginField para añadir access_level con default 'public':
class PluginField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: FieldType
    required: bool
    citation: Citation
    access_level: AccessLevel = "public"
    enum_values: list[str] | None = None
    validation: str | None = None


# Modificar Plugin para añadir identifier_scheme con default 'gs1_digital_link':
class Plugin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    regulation: str
    version: str
    description: str = ""
    identifier_scheme: IdentifierScheme = "gs1_digital_link"
    fields: list[PluginField] = Field(default_factory=list)
    required_documents: list[RequiredDocument] = Field(default_factory=list)
    cross_validations: list[CrossValidation] = Field(default_factory=list)
```

- [ ] **Paso 5.1.6 — Actualizar `_schema.yaml`**

Reescribir `plugins/_schema.yaml` (manteniendo el comentario header existente):

```yaml
# Schema canónico de plugins de sector ESPR.
# Cada plugin YAML en plugins/ debe cumplir esta estructura.
# Documentación canónica. La validación real vive en backend/src/app/plugins/loader.py.

plugin:
  required: [name, regulation, version, fields, required_documents]
  properties:
    name: { type: string }
    regulation: { type: string }   # e.g. "EU 2023/1542"
    version: { type: string }      # semver
    description: { type: string }
    identifier_scheme:
      type: string
      enum: [gs1_digital_link, iso_iec_15459]
      default: gs1_digital_link
      description: "Esquema del identificador único del DPP. Para baterías, ISO/IEC 15459-1/2/3/4/5/6 es obligatorio por Art. 77.3 del Reglamento UE 2023/1542. GS1 Digital Link es el esquema por defecto para sectores sin acto delegado específico."

fields:
  description: "Lista de campos del DPP exigidos por el sector"
  item_required: [id, type, required, citation]
  item_properties:
    id: { type: string }
    type: { type: string, enum: [string, number, integer, boolean, enum, repeater] }
    required: { type: boolean }
    citation:
      required: [regulation, article]
      properties:
        regulation: { type: string }
        article: { type: string }
    access_level:
      type: string
      enum: [public, legitimate_interest, authorities_only, individual]
      default: public
      description: "Nivel de visibilidad del campo conforme a las 4 secciones del Annex XIII del Reglamento UE 2023/1542 (ver FUNCIONAL.md §9.2). Default 'public' para sectores sin acto delegado específico."
    enum_values: { type: list, optional: true }
    validation: { type: string, optional: true }

required_documents:
  description: "Documentos que el Recolector necesita"
  item_required: [type, mandatory]
  item_properties:
    type: { type: string, enum: [datasheet, certificate, lca, sds, ce_declaration] }
    mandatory: { type: boolean }
    when: { type: string, optional: true }

cross_validations:
  description: "Reglas adicionales que cruzan campos"
  optional: true
  item_required: [id, rule]
  item_properties:
    id: { type: string }
    rule: { type: string }
    message: { type: string, optional: true }
```

Si el test `test_loader_accepts_valid_plugin` falla en este punto por la nueva aserción de tipos, **actualizarlo**: el campo `weight_kg` ahora tiene `access_level == "legitimate_interest"` — añadir un assert que verifique que `plugin.fields[1].access_level == "legitimate_interest"` para reforzar la cobertura.

- [ ] **Paso 5.1.7 — Verificar verde**

```bash
cd backend
PATH="$HOME/.local/bin:$PATH" uv run pytest tests/test_plugin_loader.py -v
PATH="$HOME/.local/bin:$PATH" uv run ruff check .
PATH="$HOME/.local/bin:$PATH" uv run ruff format --check .
# Si format falla: uv run ruff format .
```

Esperado: 13 tests verdes (7 originales + 6 nuevos). Ruff limpio.

- [ ] **⛔ Paso 5.1.8 — NO commit (política `feedback-commit-after-validation`)**

Dejar el working tree con cambios sin commitear. Reportar status DONE con la lista de archivos modificados/creados. El controller commitea con mensaje:

```
feat(plugins): añade access_level por campo y identifier_scheme por plugin (F1-03)
```

tras dos APPROVED (spec compliance + code quality).

---

## Task 6 — Plugin `batteries.yaml` (Reglamento UE 2023/1542) conforme Annex XIII completo

> **Importante:** este Task 6 ha sido **reescrito** tras validar el plan original contra el texto oficial del Reglamento UE 2023/1542 (Anexo XIII + Art. 77 + Anexo VI Parte A). El plan anterior tenía 17 campos con ~22 % de cobertura del Annex XIII y 5 citas erróneas (citaba Anexo VI Parte A donde debía citar Annex XIII; usaba `kWh` donde el reglamento exige Ah; usaba `Art. 19` para CE marking en lugar del correcto `Art. 18 + Annex XIII (1r)` para la Declaración UE de conformidad). Esta versión cubre **las 3 secciones estáticas del Annex XIII**: Sección 1 (pública, 19 ítems → ~38 campos al expandir agregadores como 1a, 1b y 1s), Sección 2 (interés legítimo, 4 ítems → 7 campos), Sección 3 (autoridades, 1 ítem). **Total: ~46-48 campos**. La Sección 4 (datos dinámicos individuales: SoC actual, ciclos consumidos, accidentes, temperatura operativa) queda **fuera del alcance** porque corresponde a telemetría operativa post-registro, no a datos que el fabricante introduzca en el wizard.

> **Prerrequisito:** Task 5.1 commiteada (el schema necesita `access_level` y `identifier_scheme`).

**Files:**
- Create: `plugins/batteries.yaml`
- Create: `backend/tests/test_batteries_plugin.py`

- [ ] **Paso 6.1 — Tests rojos**

`backend/tests/test_batteries_plugin.py`:

```python
from pathlib import Path

from app.plugins.loader import load_plugin

PLUGINS = Path(__file__).resolve().parents[2] / "plugins"


def test_batteries_plugin_loads_with_iso_iec_15459():
    """Art. 77.3 obliga a ISO/IEC 15459 para baterías."""
    plugin = load_plugin(PLUGINS / "batteries.yaml")
    assert plugin.regulation == "EU 2023/1542"
    assert plugin.identifier_scheme == "iso_iec_15459"


def test_batteries_has_at_least_25_required_fields():
    """F1-03 acceptance: ≥25 campos obligatorios cubriendo Secciones 1+2+3."""
    plugin = load_plugin(PLUGINS / "batteries.yaml")
    required = [f for f in plugin.fields if f.required]
    assert len(required) >= 25, f"Sólo {len(required)} campos obligatorios, F1-03 exige ≥25"


def test_batteries_covers_annex_xiii_section_1():
    """Annex XIII Sección 1 (público): ≥19 campos."""
    plugin = load_plugin(PLUGINS / "batteries.yaml")
    public = [f for f in plugin.fields if f.access_level == "public"]
    assert len(public) >= 19, (
        f"Sólo {len(public)} campos public; Annex XIII Sección 1 tiene 19 ítems agregados"
    )


def test_batteries_covers_annex_xiii_section_2():
    """Annex XIII Sección 2 (interés legítimo): ≥4 campos."""
    plugin = load_plugin(PLUGINS / "batteries.yaml")
    legitimate = [f for f in plugin.fields if f.access_level == "legitimate_interest"]
    assert len(legitimate) >= 4, (
        f"Sólo {len(legitimate)} campos legitimate_interest; Annex XIII Sección 2 tiene 4 ítems"
    )


def test_batteries_covers_annex_xiii_section_3():
    """Annex XIII Sección 3 (autoridades): ≥1 campo."""
    plugin = load_plugin(PLUGINS / "batteries.yaml")
    authorities = [f for f in plugin.fields if f.access_level == "authorities_only"]
    assert len(authorities) >= 1, "Annex XIII Sección 3 exige resultados de informes de ensayo"


def test_every_field_cites_reg_2023_1542_with_article_or_annex():
    """Todas las citas son al Reglamento de baterías, con Art./Annex concreto."""
    plugin = load_plugin(PLUGINS / "batteries.yaml")
    for f in plugin.fields:
        assert "2023/1542" in f.citation.regulation, (
            f"Campo {f.id} cita reglamento incorrecto: {f.citation.regulation}"
        )
        article = f.citation.article
        assert any(token in article for token in ("Art.", "Anexo", "Annex")), (
            f"Campo {f.id} cita sin Art./Anexo: {article}"
        )


def test_batteries_uses_amperes_hours_for_rated_capacity():
    """Annex XIII (1g) literal: 'capacidad asignada (en amperios-hora)'. NO kWh."""
    plugin = load_plugin(PLUGINS / "batteries.yaml")
    has_ah_capacity = any(f.id == "rated_capacity_ah" for f in plugin.fields)
    has_kwh_capacity = any("kwh" in f.id.lower() and "capacity" in f.id.lower() for f in plugin.fields)
    assert has_ah_capacity, "Annex XIII (1g) exige capacidad en Ah; campo rated_capacity_ah ausente"
    assert not has_kwh_capacity, (
        "Annex XIII (1g) exige Ah, no kWh — el plan original tenía esto incorrectamente como capacity_kwh"
    )


def test_batteries_eu_declaration_url_cites_art_18():
    """Annex XIII (1r) → Art. 18, NO Art. 19 (Art. 19 sería marcado CE, no DPP)."""
    plugin = load_plugin(PLUGINS / "batteries.yaml")
    decl = next((f for f in plugin.fields if f.id == "eu_declaration_of_conformity_url"), None)
    assert decl is not None, "Falta campo eu_declaration_of_conformity_url (Annex XIII 1r)"
    assert "Art. 18" in decl.citation.article, (
        f"La Declaración UE de conformidad cita Art. 18, no {decl.citation.article}"
    )


def test_batteries_requires_typical_documents():
    plugin = load_plugin(PLUGINS / "batteries.yaml")
    doc_types = {d.type for d in plugin.required_documents}
    assert {"datasheet", "ce_declaration"}.issubset(doc_types)
```

- [ ] **Paso 6.2 — Crear `plugins/batteries.yaml`**

El YAML cubre **Annex XIII Secciones 1, 2 y 3** del Reglamento UE 2023/1542. La numeración (1a)-(1s) sigue las letras del Anexo XIII en el texto oficial; los citados a Anexo VI Parte A son sub-elementos heredados del agregador 1a.

```yaml
name: "batteries"
regulation: "EU 2023/1542"
version: "0.1.0"
description: "Plugin del Reglamento UE 2023/1542 sobre pilas y baterías. v0.1.0 cubre las 3 secciones estáticas del Annex XIII (1 pública, 2 interés legítimo, 3 autoridades) para baterías industriales >2 kWh y vehículos eléctricos. Sección 4 (datos individuales dinámicos) queda fuera del alcance del wizard — corresponde a telemetría operativa post-registro."
identifier_scheme: "iso_iec_15459"   # Art. 77.3 de Reg. UE 2023/1542

fields:
  # ═══ Annex XIII Sección 1 — INFO PÚBLICA DEL MODELO ═══

  # (1a) → Anexo VI Parte A, expandido a sub-campos
  - id: battery_passport_unique_id
    type: string
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Art. 77.3 (identificador único conforme ISO/IEC 15459)"
  - id: battery_serial_number
    type: string
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Art. 38.6; Anexo IX"
  - id: manufacturer_identifier
    type: string
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Anexo VI Parte A(1); Art. 38.7"
  - id: battery_category
    type: enum
    required: true
    access_level: public
    enum_values: [lmt, industrial, ev, sli, stationary, portable]
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1a); Anexo VI Parte A(2); Art. 38.6"
  - id: manufacturing_place
    type: string
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1a); Anexo VI Parte A(3)"
  - id: manufacturing_date
    type: string
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1a); Anexo VI Parte A(4)"
  - id: battery_mass_kg
    type: number
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1a); Anexo VI Parte A(5)"
  - id: extinguishing_agent
    type: string
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1a); Anexo VI Parte A(9)"

  # (1b) composición material
  - id: battery_chemistry
    type: enum
    required: true
    access_level: public
    enum_values: [li_ion, lifepo4, ni_mh, ni_cd, lead_acid, na_ion, other]
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1b); Anexo VI Parte A(7)"
  - id: hazardous_substances
    type: repeater
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1b); Anexo VI Parte A(8)"
  - id: critical_raw_materials
    type: repeater
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1b); Anexo VI Parte A(10)"

  # (1c) huella de carbono
  - id: carbon_footprint_kgco2e_per_kwh_total
    type: number
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1c); Art. 7.1"
  - id: carbon_footprint_study_url
    type: string
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1c); Art. 7.1(g)"

  # (1d) diligencia debida
  - id: due_diligence_report_url
    type: string
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1d); Art. 52.3"

  # (1e) contenido reciclado
  - id: recycled_content_cobalt_pct
    type: number
    required: true
    access_level: public
    validation: ">=0 and <=100"
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1e); Art. 8.1"
  - id: recycled_content_lithium_pct
    type: number
    required: true
    access_level: public
    validation: ">=0 and <=100"
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1e); Art. 8.1"
  - id: recycled_content_nickel_pct
    type: number
    required: true
    access_level: public
    validation: ">=0 and <=100"
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1e); Art. 8.1"
  - id: recycled_content_lead_pct
    type: number
    required: true
    access_level: public
    validation: ">=0 and <=100"
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1e); Art. 8.1"

  # (1f) contenido renovable
  - id: renewable_content_pct
    type: number
    required: true
    access_level: public
    validation: ">=0 and <=100"
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1f)"

  # (1g) capacidad asignada — Annex XIII literal: "amperios-hora"
  - id: rated_capacity_ah
    type: number
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1g)"

  # (1h) tensiones mín/nominal/máx
  - id: voltage_min_v
    type: number
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1h)"
  - id: voltage_nominal_v
    type: number
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1h)"
  - id: voltage_max_v
    type: number
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1h)"

  # (1i) capacidad de potencia original + límites
  - id: original_power_capability_w
    type: number
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1i); Art. 10; Anexo IV Parte B(4)"
  - id: max_permitted_power_w
    type: number
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1i)"

  # (1j) vida útil prevista + prueba de referencia
  - id: expected_lifetime_cycles
    type: integer
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1j); Anexo IV Parte A(5)"
  - id: cycle_life_reference_test
    type: string
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1j)"

  # (1k) límite de capacidad para agotamiento — solo EV
  - id: capacity_exhaustion_threshold_pct
    type: number
    required: false   # condicional: solo aplicable a EV (validar en cross_validation)
    access_level: public
    validation: ">=0 and <=100"
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1k) — solo vehículos eléctricos"

  # (1l) rango temperatura en reposo
  - id: idle_temp_range_min_c
    type: number
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1l)"
  - id: idle_temp_range_max_c
    type: number
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1l)"

  # (1m) garantía
  - id: warranty_period_months
    type: integer
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1m)"

  # (1n) eficiencia round-trip inicial + al 50% del ciclo
  - id: roundtrip_efficiency_initial_pct
    type: number
    required: true
    access_level: public
    validation: ">=0 and <=100"
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1n); Art. 10; Anexo IV(6)"
  - id: roundtrip_efficiency_at_50pct_lifecycle_pct
    type: number
    required: true
    access_level: public
    validation: ">=0 and <=100"
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1n); Anexo IV(6)"

  # (1o) resistencia interna celda + pack
  - id: internal_resistance_cell_ohm
    type: number
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1o); Art. 10; Anexo IV Parte A(3)"
  - id: internal_resistance_pack_ohm
    type: number
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1o); Anexo IV Parte A(3)"

  # (1p) C-rate de la prueba ciclo de vida
  - id: cycle_life_test_c_rate
    type: number
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1p)"

  # (1q) marcado del Art. 13.3 y .4
  - id: marking_requirements_url
    type: string
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1q); Art. 13.3-4"

  # (1r) Declaración UE de conformidad — NO es Art. 19 (CE marking), es Art. 18
  - id: eu_declaration_of_conformity_url
    type: string
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1r); Art. 18"

  # (1s) info gestión de residuos (Art. 74.1.a-f consolidado en 2 URLs)
  - id: waste_management_info_url
    type: string
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1s); Art. 74.1.a-e"
  - id: environmental_health_impact_info_url
    type: string
    required: true
    access_level: public
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (1s); Art. 74.1.f"

  # ═══ Annex XIII Sección 2 — INTERÉS LEGÍTIMO + COMISIÓN ═══

  - id: composition_cathode
    type: string
    required: true
    access_level: legitimate_interest
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (2a)"
  - id: composition_anode
    type: string
    required: true
    access_level: legitimate_interest
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (2a)"
  - id: composition_electrolyte
    type: string
    required: true
    access_level: legitimate_interest
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (2a)"
  - id: component_part_numbers
    type: repeater
    required: true
    access_level: legitimate_interest
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (2b)"
  - id: spare_parts_sources_url
    type: string
    required: true
    access_level: legitimate_interest
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (2b)"
  - id: dismantling_info_url
    type: string
    required: true
    access_level: legitimate_interest
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (2c)"
  - id: safety_measures_url
    type: string
    required: true
    access_level: legitimate_interest
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (2d); Art. 74.2"

  # ═══ Annex XIII Sección 3 — SOLO AUTORIDADES Y COMISIÓN ═══

  - id: conformity_test_reports_url
    type: string
    required: true
    access_level: authorities_only
    citation:
      regulation: "EU 2023/1542"
      article: "Annex XIII (3); Anexo VIII Parte A(2h)"

required_documents:
  - type: datasheet
    mandatory: true
  - type: ce_declaration
    mandatory: true
  - type: certificate
    mandatory: true
    when: "battery_category in [industrial, ev]"
  - type: lca
    mandatory: true
    when: "rated_capacity_ah * voltage_nominal_v / 1000 > 2"   # >2 kWh
  - type: sds
    mandatory: false

cross_validations:
  - id: voltage_consistency
    rule: "voltage_min_v <= voltage_nominal_v <= voltage_max_v"
    message: "Las tensiones declaradas deben cumplir min ≤ nominal ≤ max (Annex XIII (1h))"
  - id: idle_temp_consistency
    rule: "idle_temp_range_min_c < idle_temp_range_max_c"
    message: "El rango de temperatura en reposo debe tener mínimo menor que máximo (Annex XIII (1l))"
  - id: lifetime_min_cycles
    rule: "expected_lifetime_cycles >= 500"
    message: "Por debajo de 500 ciclos, revisar Anexo IV Parte A(5) del Reglamento UE 2023/1542"
  - id: capacity_exhaustion_required_for_ev
    rule: "battery_category != 'ev' or capacity_exhaustion_threshold_pct != null"
    message: "El límite de capacidad para agotamiento es obligatorio para baterías de vehículos eléctricos (Annex XIII (1k))"
```

- [ ] **Paso 6.3 — Verificar verde**

```bash
cd backend
PATH="$HOME/.local/bin:$PATH" uv run pytest tests/test_batteries_plugin.py -v
PATH="$HOME/.local/bin:$PATH" uv run pytest -v   # full suite, expect 22 verde (13 anteriores + 9 nuevos)
PATH="$HOME/.local/bin:$PATH" uv run ruff check .
PATH="$HOME/.local/bin:$PATH" uv run ruff format --check .
```

Esperado: 9 tests del plugin de baterías verdes. Suite completa 22/22.

- [ ] **⛔ Paso 6.4 — NO commit (política `feedback-commit-after-validation`)**

Dejar el working tree con cambios. Reportar status DONE con la lista de archivos creados. El controller commitea con mensaje:

```
feat(plugins): plugin baterías conforme Annex XIII de Reg. UE 2023/1542 (F1-03)
```

tras dos APPROVED.

---

## Task 7 — Router de modelos con LiteLLM (con defensas OWASP LLM01/LLM07/LLM10)

> **Endurecimiento OWASP del 2026-05-24:** este Task 7 incorpora 3 defensas del OWASP Top 10 for LLM Applications (versión 2025) desde el primer commit, para que los callers (F3 Clasificador, F3+F5 Recolector, F4 Chat) hereden una API segura por defecto y no haya que retrofittear seguridad en cada componente IA.
>
> 1. **LLM01 Prompt Injection** — la API expone parámetro `system: str | None` separado de `prompt: str`. Los callers nunca concatenan instrucción de sistema con input de usuario; LiteLLM y el modelo distinguen los roles `system` / `user` explícitamente.
> 2. **LLM07 System Prompt Leakage** — el mensaje exterior de `LLMBackendError` es **sanitizado** y NO contiene el contenido del prompt ni el detalle de la excepción original de LiteLLM (que puede embeber el prompt en su `args[0]`). El detalle completo queda accesible vía `__cause__` (preservado por `raise ... from exc`) para depuración interna (Langfuse, traceback en logs).
> 3. **LLM10 Unbounded Consumption** — defaults conservadores `timeout=30.0` segundos y `max_tokens=2000`. Mitiga (a) llamadas a Ollama que se cuelgan bloqueando workers, (b) respuestas infinitas con APIs comerciales que disparan coste. Los callers pueden overridear cuando la tarea lo justifique (Recolector con PDFs largos, etc.).
>
> Fuente: https://genai.owasp.org/llm-top-10/ (2025). Decisión y trazabilidad en el commit `docs(plan)` que precede a esta tarea.

**Files:**
- Create: `backend/src/app/llm/__init__.py`, `backend/src/app/llm/router.py`
- Test: `backend/tests/test_llm_router.py`

- [ ] **Paso 7.1 — Tests del wrapper (rojos)**

`backend/tests/test_llm_router.py` — 8 tests: 5 funcionales + 3 OWASP.

```python
from unittest.mock import patch

import pytest

from app.config import settings
from app.llm.router import LLMBackendError, LLMResponse, complete, parse_backend


# ═══ Tests funcionales ═══

def test_parse_backend_ollama():
    backend = parse_backend("ollama:qwen2.5:14b")
    assert backend.provider == "ollama"
    assert backend.model == "qwen2.5:14b"


def test_parse_backend_anthropic():
    backend = parse_backend("anthropic:claude-opus-4")
    assert backend.provider == "anthropic"
    assert backend.model == "claude-opus-4"


def test_parse_backend_rejects_malformed():
    with pytest.raises(ValueError):
        parse_backend("just-a-string")


def test_complete_returns_typed_response(monkeypatch):
    # NOTE: Settings es un singleton de pydantic-settings instanciado a nivel
    # módulo; monkeypatch.setenv no afecta al singleton ya creado. Usar
    # monkeypatch.setattr sobre el objeto settings, igual que test_health.py.
    monkeypatch.setattr(settings, "model_backend", "ollama:qwen2.5:14b")

    fake_response = {
        "choices": [{"message": {"content": "respuesta del modelo"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
        "model": "ollama/qwen2.5:14b",
    }

    with patch("app.llm.router.litellm.completion", return_value=fake_response) as mocked:
        result = complete("hola mundo")

    assert isinstance(result, LLMResponse)
    assert result.content == "respuesta del modelo"
    assert result.tokens_in == 10
    assert result.tokens_out == 4
    assert result.model == "ollama/qwen2.5:14b"
    assert result.backend == "ollama:qwen2.5:14b"
    mocked.assert_called_once()


def test_complete_raises_typed_error_on_backend_failure(monkeypatch):
    monkeypatch.setattr(settings, "model_backend", "ollama:qwen2.5:14b")

    with patch("app.llm.router.litellm.completion", side_effect=RuntimeError("ollama down")):
        with pytest.raises(LLMBackendError) as exc:
            complete("hola")

    assert exc.value.backend == "ollama:qwen2.5:14b"
    # El backend identifica el origen del fallo; el detalle del exc original
    # queda en __cause__ (preservado por raise ... from exc) — accesible para
    # depuración interna pero no expuesto en el mensaje del error.
    assert exc.value.__cause__ is not None


# ═══ Defensas OWASP ═══

def test_complete_passes_system_message_when_provided(monkeypatch):
    """OWASP LLM01 (Prompt Injection): separar system de user evita injection
    por concatenación. El parámetro `system=` debe traducirse en un mensaje
    con role=system distinto del role=user.
    """
    monkeypatch.setattr(settings, "model_backend", "ollama:qwen2.5:14b")

    fake_response = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 6},
        "model": "ollama/qwen2.5:14b",
    }

    with patch("app.llm.router.litellm.completion", return_value=fake_response) as mocked:
        complete("¿qué es ESPR?", system="Eres asistente normativo. Cita siempre.")

    call_kwargs = mocked.call_args.kwargs
    messages = call_kwargs["messages"]
    assert messages[0] == {"role": "system", "content": "Eres asistente normativo. Cita siempre."}
    assert messages[1] == {"role": "user", "content": "¿qué es ESPR?"}


def test_complete_passes_timeout_and_max_tokens(monkeypatch):
    """OWASP LLM10 (Unbounded Consumption): los overrides explícitos de
    timeout y max_tokens deben propagarse a litellm.completion.
    """
    monkeypatch.setattr(settings, "model_backend", "ollama:qwen2.5:14b")

    fake_response = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        "model": "ollama/qwen2.5:14b",
    }

    with patch("app.llm.router.litellm.completion", return_value=fake_response) as mocked:
        complete("test", timeout=10.0, max_tokens=500)

    call_kwargs = mocked.call_args.kwargs
    assert call_kwargs["timeout"] == 10.0
    assert call_kwargs["max_tokens"] == 500


def test_complete_uses_safe_defaults_for_timeout_and_max_tokens(monkeypatch):
    """OWASP LLM10: si no se pasan, defaults conservadores (timeout=30.0,
    max_tokens=2000) — mitigan DoS por llamadas que se cuelgan y respuestas
    sin tope con APIs comerciales.
    """
    monkeypatch.setattr(settings, "model_backend", "ollama:qwen2.5:14b")

    fake_response = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        "model": "ollama/qwen2.5:14b",
    }

    with patch("app.llm.router.litellm.completion", return_value=fake_response) as mocked:
        complete("test")

    call_kwargs = mocked.call_args.kwargs
    assert call_kwargs["timeout"] == 30.0
    assert call_kwargs["max_tokens"] == 2000


def test_llm_backend_error_does_not_echo_prompt(monkeypatch):
    """OWASP LLM07 (System Prompt Leakage): el mensaje exterior de
    LLMBackendError NO debe contener el prompt ni el mensaje crudo de la
    excepción original de LiteLLM (que algunos backends populan con eco del
    request body). El detalle queda accesible via __cause__ para depuración.
    """
    monkeypatch.setattr(settings, "model_backend", "ollama:qwen2.5:14b")

    secret_prompt = "SYSTEM_PROMPT_SECRETO_QUE_NO_DEBE_FILTRARSE"
    backend_exception_with_echo = RuntimeError(f"Bad request: messages=[{secret_prompt}]")

    with patch("app.llm.router.litellm.completion", side_effect=backend_exception_with_echo):
        with pytest.raises(LLMBackendError) as exc:
            complete(secret_prompt)

    # El mensaje exterior identifica el backend pero NO contiene el prompt
    assert secret_prompt not in str(exc.value)
    # El detalle completo sigue accesible via __cause__ para Langfuse/tracebacks
    assert exc.value.__cause__ is backend_exception_with_echo
```

- [ ] **Paso 7.2 — Verificar que falla**

```bash
cd backend
PATH="$HOME/.local/bin:$PATH" uv run pytest tests/test_llm_router.py -v
```

Esperado: ImportError de `app.llm.router`.

- [ ] **Paso 7.3 — Implementar el router con defensas OWASP**

`backend/src/app/llm/__init__.py` vacío. `backend/src/app/llm/router.py`:

```python
from dataclasses import dataclass

import litellm

from app.config import settings


@dataclass(frozen=True)
class ParsedBackend:
    provider: str  # ollama | anthropic | openai | ...
    model: str     # qwen2.5:14b | claude-opus-4 | gpt-4o | ...
    raw: str


@dataclass(frozen=True)
class LLMResponse:
    content: str
    tokens_in: int
    tokens_out: int
    model: str
    backend: str


class LLMBackendError(RuntimeError):
    """Fallo del backend de LLM con mensaje sanitizado.

    OWASP LLM07 (System Prompt Leakage): el mensaje exterior identifica el
    backend (`self.backend`) pero NO contiene el contenido del prompt ni el
    mensaje crudo de la excepción original. El detalle completo queda
    accesible via `__cause__` (preservado por `raise ... from exc`) para
    depuración en entorno controlado (Langfuse, tracebacks).
    """

    def __init__(self, message: str, *, backend: str) -> None:
        super().__init__(message)
        self.backend = backend


def parse_backend(value: str) -> ParsedBackend:
    """Convierte 'provider:model[:variant]' en ParsedBackend.

    Acepta:
      ollama:qwen2.5:14b   -> provider=ollama, model=qwen2.5:14b
      anthropic:claude-... -> provider=anthropic, model=claude-...
    """
    if ":" not in value:
        raise ValueError(f"MODEL_BACKEND inválido: '{value}'. Formato esperado provider:model")
    provider, model = value.split(":", 1)
    if not provider or not model:
        raise ValueError(f"MODEL_BACKEND inválido: '{value}'")
    return ParsedBackend(provider=provider, model=model, raw=value)


def _to_litellm_model(parsed: ParsedBackend) -> str:
    """LiteLLM usa 'provider/model' como identificador unificado."""
    if parsed.provider == "ollama":
        return f"ollama/{parsed.model}"
    if parsed.provider == "anthropic":
        return f"anthropic/{parsed.model}"
    if parsed.provider == "openai":
        return parsed.model  # LiteLLM acepta el modelo openai directo
    return f"{parsed.provider}/{parsed.model}"


# Defaults OWASP LLM10 (Unbounded Consumption) — conservadores; los callers
# pueden overridear cuando la tarea lo justifique (Recolector con PDFs largos,
# Clasificador con corpus extenso, etc.).
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_TOKENS = 2000


def complete(
    prompt: str,
    *,
    system: str | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_tokens: int | None = DEFAULT_MAX_TOKENS,
    **opts,
) -> LLMResponse:
    """Wrapper único de LLM para todo el sistema. Lee MODEL_BACKEND del entorno.

    OWASP LLM01 (Prompt Injection): `system` y `prompt` van como mensajes
    separados (role=system y role=user) a litellm; nunca se concatenan en una
    sola cadena. Los callers deben usar `system=` para instrucciones del
    sistema; `prompt` queda exclusivamente para input de usuario.

    OWASP LLM10 (Unbounded Consumption): defaults conservadores de timeout y
    max_tokens. Override explícito por argumento cuando la tarea lo justifique.

    OWASP LLM07 (System Prompt Leakage): si el backend falla, levanta
    LLMBackendError con mensaje genérico (NO contiene el prompt ni el detalle
    de la excepción original). El detalle queda en `__cause__` para
    depuración interna.
    """
    parsed = parse_backend(settings.model_backend)
    model_id = _to_litellm_model(parsed)
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        response = litellm.completion(
            model=model_id,
            messages=messages,
            timeout=timeout,
            max_tokens=max_tokens,
            **opts,
        )
    except Exception as exc:
        # OWASP LLM07: mensaje sanitizado al exterior; detalle en __cause__.
        raise LLMBackendError(
            f"Backend {parsed.raw} ({parsed.provider}) falló — ver __cause__ para detalle.",
            backend=parsed.raw,
        ) from exc

    content = response["choices"][0]["message"]["content"]
    usage = response.get("usage", {})
    return LLMResponse(
        content=content,
        tokens_in=int(usage.get("prompt_tokens", 0)),
        tokens_out=int(usage.get("completion_tokens", 0)),
        model=response.get("model", model_id),
        backend=parsed.raw,
    )
```

- [ ] **Paso 7.4 — Verificar tests verdes**

```bash
cd backend
PATH="$HOME/.local/bin:$PATH" uv run pytest tests/test_llm_router.py -v
PATH="$HOME/.local/bin:$PATH" uv run pytest -v   # full suite, expect 38 (30 + 8 nuevos)
PATH="$HOME/.local/bin:$PATH" uv run ruff check .
PATH="$HOME/.local/bin:$PATH" uv run ruff format --check .
```

Esperado: 8 tests del router verdes. Suite completa 38/38. Ruff limpio.

- [ ] **Paso 7.5 — Verificación de no regresión del health endpoint**

`backend/tests/test_health.py` ya tiene 2 tests (instalados en T1) que verifican que `/api/v1/health` refleja `settings.model_backend`. La suite completa debe seguir verde.

- [ ] **⛔ Paso 7.6 — NO commit**

Política `feedback-commit-after-validation`: el implementer subagent **no commitea**. Deja working tree con cambios. Controller commitea tras spec compliance review + code quality review APPROVED con mensaje:

```
feat(llm): wrapper LiteLLM con defensas OWASP y error tipado (F1-04)
```

---

## Task 8 — Observabilidad: cliente Langfuse y decoradores

**Files:**
- Create: `backend/src/app/observability/__init__.py`, `backend/src/app/observability/langfuse_client.py`, `backend/src/app/observability/decorators.py`
- Modify: `backend/src/app/llm/router.py` (integración opcional con Langfuse)
- Test: `backend/tests/test_decorators.py`

**Alcance F1-05:** sólo infraestructura de observabilidad. Los agentes (Clasificador, Recolector, Chat) no existen aún — vienen en F2/F3/F4. Aquí dejamos los decoradores listos y los testeamos con funciones sintéticas. Las criterios 2 y 3 de F1-05 ("trazas en una corrida del wizard demo") se validarán al cierre de F2/F3.

- [ ] **Paso 8.1 — Tests de los decoradores (rojo)**

`backend/tests/test_decorators.py`:

```python
from unittest.mock import MagicMock

from app.observability.decorators import trace_chat, trace_classifier, trace_collector


def test_trace_classifier_captures_inputs_and_outputs(monkeypatch):
    fake_client = MagicMock()
    monkeypatch.setattr("app.observability.decorators._client", fake_client)

    @trace_classifier
    def fake_classify(description: str) -> dict:
        return {
            "sector": "batteries",
            "confidence": 0.91,
            "cita_normativa": "EU 2023/1542 Art. 13",
        }

    result = fake_classify("batería para EV")
    assert result["sector"] == "batteries"

    # Debe haber abierto una span "classifier"
    fake_client.trace.assert_called_once()
    trace_kwargs = fake_client.trace.call_args.kwargs
    assert trace_kwargs.get("name") == "classifier"
    # Debe haber registrado la cita normativa cuando el output la incluye
    assert "cita_normativa" in trace_kwargs.get("metadata", {})


def test_trace_collector_separates_spans(monkeypatch):
    fake_client = MagicMock()
    monkeypatch.setattr("app.observability.decorators._client", fake_client)

    @trace_collector
    def fake_collect(pdf_path: str) -> dict:
        return {"fields_extracted": 12}

    fake_collect("doc.pdf")
    assert fake_client.trace.call_args.kwargs["name"] == "collector"


def test_trace_chat_includes_citation(monkeypatch):
    fake_client = MagicMock()
    monkeypatch.setattr("app.observability.decorators._client", fake_client)

    @trace_chat
    def fake_chat(q: str) -> dict:
        return {"answer": "...", "cita_normativa": "EU 2024/1781 Art. 7"}

    fake_chat("¿qué exige el ESPR?")
    metadata = fake_client.trace.call_args.kwargs["metadata"]
    assert metadata["cita_normativa"] == "EU 2024/1781 Art. 7"


def test_decorator_does_not_swallow_exceptions(monkeypatch):
    fake_client = MagicMock()
    monkeypatch.setattr("app.observability.decorators._client", fake_client)

    @trace_classifier
    def broken(description: str) -> dict:
        raise ValueError("boom")

    import pytest

    with pytest.raises(ValueError, match="boom"):
        broken("x")

    # La traza debe haberse abierto y cerrado con el error registrado
    fake_client.trace.assert_called_once()
```

- [ ] **Paso 8.2 — Verificar que falla**

```bash
cd backend
uv run pytest tests/test_decorators.py -v
```

Esperado: ImportError.

- [ ] **Paso 8.3 — Cliente Langfuse**

`backend/src/app/observability/__init__.py` vacío. `backend/src/app/observability/langfuse_client.py`:

```python
from functools import lru_cache

from langfuse import Langfuse

from app.config import settings


@lru_cache(maxsize=1)
def get_client() -> Langfuse | None:
    """Devuelve un cliente Langfuse si hay credenciales configuradas, si no None.

    En desarrollo local sin claves, Langfuse no se invoca pero la app sigue.
    """
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return None
    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )
```

- [ ] **Paso 8.4 — Decoradores**

`backend/src/app/observability/decorators.py`:

```python
"""Decoradores que emiten trazas Langfuse por componente IA.

Los decoradores son tolerantes a la ausencia de cliente Langfuse: si no hay
credenciales en `.env`, ejecutan la función envuelta sin emitir traza.
"""

from collections.abc import Callable
from functools import wraps
from time import perf_counter
from typing import Any

from app.observability.langfuse_client import get_client

_client = get_client()  # patcheable en tests


def _make_tracer(component_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            client = _client
            start = perf_counter()
            metadata: dict[str, Any] = {}
            error: Exception | None = None
            output: Any = None
            try:
                output = fn(*args, **kwargs)
                if isinstance(output, dict) and "cita_normativa" in output:
                    metadata["cita_normativa"] = output["cita_normativa"]
                return output
            except Exception as exc:
                error = exc
                metadata["error"] = repr(exc)
                raise
            finally:
                if client is not None:
                    client.trace(
                        name=component_name,
                        input={"args": args, "kwargs": kwargs},
                        output=None if error else output,
                        metadata=metadata,
                        latency_ms=int((perf_counter() - start) * 1000),
                    )

        return wrapper

    return decorator


trace_classifier = _make_tracer("classifier")
trace_collector = _make_tracer("collector")
trace_chat = _make_tracer("chat")
```

- [ ] **Paso 8.5 — Verificar tests verdes**

```bash
cd backend
uv run pytest tests/test_decorators.py -v
```

Esperado: 4 tests PASS.

- [ ] **Paso 8.6 — Verificar Langfuse en docker compose**

```bash
docker compose up -d langfuse langfuse-db
sleep 15
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3001
```

Esperado: 200 o 302. Abre `http://localhost:3001` en el navegador, crea cuenta admin, copia las API keys generadas en la UI y rellena `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` en `.env`. Para el alcance de F1 esto se documenta en el README — no se automatiza.

```bash
docker compose down
```

- [ ] **Paso 8.7 — Commit**

```bash
git add backend/src/app/observability backend/tests/test_decorators.py
git commit -m "feat(observability): cliente Langfuse + decoradores classifier/collector/chat (F1-05)"
```

---

## Task 9 — README, verificación 30-min y cierre de F1

**Files:**
- Modify: `README.md`

- [ ] **Paso 9.1 — README de setup**

Sobrescribe `README.md`:

````markdown
# PasaporteAbierto

Aplicación web auto-hospedable para generar el Pasaporte Digital de Producto (DPP) exigido por el Reglamento UE 2024/1781 (ESPR).

## Documentación

- Arquitectura: [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md)
- Especificación funcional: [`docs/FUNCIONAL.md`](./docs/FUNCIONAL.md)
- Tickets por fase: [`docs/tickets/F1.md`](./docs/tickets/F1.md) … `F6.md`

## Requisitos

- Docker 24+ y docker compose
- (Opcional, sólo para desarrollo local sin contenedor) Python 3.11, [uv](https://docs.astral.sh/uv/), Node 20, pnpm 9.

## Setup en ≤30 minutos

```bash
git clone <repo-url>
cd PasaporteAbierto-*
cp .env.example .env
docker compose up -d --build
```

Tras ~2 min, verifica:

```bash
curl -s http://localhost:8000/api/v1/health | python -m json.tool
```

Debe devolver `version`, `model` y `backend`.

| Servicio | URL | Notas |
|---|---|---|
| Backend FastAPI | http://localhost:8000 | OpenAPI en `/docs` |
| Frontend Next.js | http://localhost:3000 | UI del wizard (vacía en F1) |
| Langfuse | http://localhost:3001 | Crea cuenta admin la primera vez |
| Ollama (opcional) | http://localhost:11434 | Sólo con `--profile ollama` |

### Activar Langfuse para trazas IA

1. Abre `http://localhost:3001`, crea la primera cuenta (queda como admin).
2. Crea un proyecto y copia `Public Key` + `Secret Key`.
3. Pégalas en `.env` como `LANGFUSE_PUBLIC_KEY` y `LANGFUSE_SECRET_KEY`.
4. `docker compose restart backend`.

### Activar Ollama local (modelo gratuito)

```bash
docker compose --profile ollama up -d
docker compose exec ollama ollama pull qwen2.5:14b
```

Edita `.env`: `MODEL_BACKEND=ollama:qwen2.5:14b`. Reinicia el backend.

## Desarrollo

### Backend

```bash
cd backend
uv sync
uv run pytest                  # tests
uv run ruff check .            # lint
uv run uvicorn app.main:app --reload --port 8000
```

Migraciones:

```bash
cd backend
uv run alembic upgrade head    # aplicar
uv run alembic downgrade base  # revertir todo
uv run python -m scripts.seed  # cargar datos demo
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev          # http://localhost:3000
pnpm test         # vitest
pnpm lint         # biome
```

### Comandos rápidos (raíz)

```bash
make up           # docker compose up -d --build
make down         # parar todo
make test         # backend + frontend
make health       # curl al health endpoint
make seed         # carga datos demo en backend
```

## Plugins regulatorios

Cada sector ESPR se modela como un YAML en `plugins/`. Para añadir un sector nuevo, crea `plugins/<sector>.yaml` siguiendo `plugins/_schema.yaml`. El loader valida en arranque — un plugin que no cumpla el schema no se carga y aparece en logs.

Cobertura actual: `batteries.yaml` (Reglamento UE 2023/1542).

## Licencia

Apache 2.0.
````

- [ ] **Paso 9.2 — Verificación 30-min en máquina limpia**

En un terminal nuevo, simulando un colaborador que clona por primera vez:

```bash
cd /tmp && rm -rf pa-verify && git clone <ruta-al-repo-local> pa-verify
cd pa-verify
cp .env.example .env
time docker compose up -d --build
```

Espera a que termine. El `time` debe marcar mucho menos de 30 min en una máquina razonable (objetivo <10 min en build limpio).

Verifica los tres endpoints:

```bash
curl -s http://localhost:8000/api/v1/health | python -m json.tool
curl -s -o /dev/null -w "frontend: %{http_code}\n" http://localhost:3000
curl -s -o /dev/null -w "langfuse: %{http_code}\n" http://localhost:3001
```

Tras verificar, limpia:

```bash
docker compose down -v
cd / && rm -rf /tmp/pa-verify
```

- [ ] **Paso 9.3 — Suite de tests completa**

```bash
cd backend && uv run pytest -v
cd ../frontend && pnpm test
```

Esperado: todos los tests PASS.

- [ ] **Paso 9.4 — Lint**

```bash
cd backend && uv run ruff check .
cd ../frontend && pnpm lint
```

Esperado: sin errores. Corrige cualquier hallazgo antes de commitear.

- [ ] **Paso 9.5 — Commit final F1**

```bash
git add README.md
git commit -m "docs: README con setup ≤30 min y referencias cruzadas (F1)"
```

- [ ] **Paso 9.6 — Auto-revisión contra criterios de F1**

Marca con ✅/❌ cada criterio. Cualquier ❌ es bloqueante para cerrar F1.

**F1-01:**
- [ ] `docker compose up` levanta backend, frontend y Langfuse sin errores; Ollama queda opt-in vía profile.
- [ ] `GET /api/v1/health` responde 200 con versión, modelo activo y backend.
- [ ] README documenta setup ≤30 min.

**F1-02:**
- [ ] Existen las 5 tablas con los nombres exactos de la arquitectura.
- [ ] `audit_log` tiene `prev_hash` y queda preparado para el hash chain.
- [ ] Migración `upgrade`/`downgrade` reversible y seed reproducible.

**F1-03:**
- [ ] El loader rechaza con error claro YAMLs que no cumplen `_schema.yaml`.
- [ ] `batteries.yaml` define ≥25 campos obligatorios con cita normativa cada uno, cubriendo las 3 secciones estáticas del Annex XIII del Reg. UE 2023/1542 (Sección 1 pública, Sección 2 interés legítimo, Sección 3 autoridades).
- [ ] Tests cubren ≥1 plugin válido y ≥2 inválidos.

**F1-04:**
- [ ] Cambiar `MODEL_BACKEND` no requiere recompilar ni tocar otros módulos.
- [ ] Trazas Langfuse incluyen `model` y `backend` usados (validable end-to-end en F2 cuando exista el Clasificador).
- [ ] Test verifica error tipado si el backend no responde.

**F1-05:**
- [ ] UI de Langfuse accesible en `localhost:3001`.
- [ ] Decoradores `@trace_classifier`, `@trace_collector`, `@trace_chat` listos y probados con mocks.
- [ ] Validación end-to-end (criterios 2 y 3 de F1-05) **aplazada a F2/F3** cuando existan los agentes — anotado explícitamente.

---

## Apéndice — Decisiones cerradas en este plan

- **Tooling Python**: uv + ruff + pytest. Decidido conjuntamente con la usuaria al inicio.
- **Tooling Frontend**: pnpm + vitest + biome. Idem.
- **Migrations**: Alembic. Idem.
- **Postgres aparece sólo como dependencia interna de Langfuse self-hosted.** La decisión "no Postgres para la app" se mantiene: el backend de PasaporteAbierto usa SQLite.
- **F1-05 criterios end-to-end**: validación completa se aplaza a F2/F3 cuando existan los agentes. F1 cierra con la infraestructura lista y testeada con mocks.
