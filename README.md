# PasaporteAbierto

<!-- RAG_QUALITY_BADGE:START -->
![RAG quality](https://img.shields.io/badge/RAG_quality-pendiente_(F2--03)-lightgrey)
<!-- RAG_QUALITY_BADGE:END -->

Aplicación web auto-hospedable para que fabricantes PYME generen el **Pasaporte Digital de Producto (DPP)** exigido por el Reglamento UE 2024/1781 (ESPR). Open source, Apache 2.0.

## Documentación

- **Arquitectura técnica:** [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md)
- **Especificación funcional:** [`docs/FUNCIONAL.md`](./docs/FUNCIONAL.md)
- **Tickets por fase:** [`docs/tickets/F1.md`](./docs/tickets/F1.md) … [`docs/tickets/F6.md`](./docs/tickets/F6.md)
- **Decisiones arquitectónicas (ADRs):** [`docs/adr/`](./docs/adr/)

## Requisitos

- **Docker 24+** y `docker compose`.
- Opcional (sólo para desarrollo local sin contenedor): Python 3.11, [uv](https://docs.astral.sh/uv/), Node 20, pnpm 9.

## Setup en ≤30 minutos

```bash
git clone <repo-url>
cd PasaporteAbierto-*
cp .env.example .env
docker compose up -d --build
```

Tras ~2 minutos (primera vez ~5-10 min por el build), verifica:

```bash
curl -s http://localhost:8000/api/v1/health | python -m json.tool
```

Debe devolver `version`, `model` y `backend`.

| Servicio | URL | Notas |
|---|---|---|
| Backend FastAPI | http://localhost:8000 | OpenAPI en `/docs` |
| Frontend Next.js | http://localhost:3000 | UI del wizard (vacía en F1, se construye en F3) |
| Langfuse | http://localhost:3001 | Crea cuenta admin la primera vez |
| Ollama (opcional) | http://localhost:11434 | Sólo con `--profile ollama` |

### Activar Langfuse para trazas IA

1. Abre `http://localhost:3001` y crea la primera cuenta (queda como admin).
2. Crea un proyecto y copia `Public Key` + `Secret Key`.
3. Pégalas en `.env` como `LANGFUSE_PUBLIC_KEY` y `LANGFUSE_SECRET_KEY`.
4. `docker compose restart backend`.

A partir de ahí cada llamada a `litellm.completion()` y cada función decorada con `@trace_classifier` / `@trace_collector` / `@trace_chat` emitirá una traza automáticamente. Ver `backend/src/app/observability/` para detalles.

### Activar Ollama local (modelo gratuito)

```bash
docker compose --profile ollama up -d
docker compose exec ollama ollama pull qwen2.5:14b
```

Edita `.env`: `MODEL_BACKEND=ollama:qwen2.5:14b`. Reinicia el backend.

Para usar una API comercial en su lugar, edita `MODEL_BACKEND` con `anthropic:claude-...`, `openai:gpt-...`, etc. (sintaxis canónica de [LiteLLM](https://docs.litellm.ai/docs/providers)) y añade la API key correspondiente al `.env`.

## Desarrollo

### Backend (Python 3.11 + FastAPI + SQLModel)

```bash
cd backend
uv sync                              # instala deps
uv run pytest                        # tests (58/58 al cierre de F1)
uv run ruff check .                  # lint
uv run ruff format --check .         # format check
uv run uvicorn app.main:app --reload --port 8000
```

Migraciones de base de datos (Alembic):

```bash
cd backend
uv run alembic upgrade head          # aplicar todas las migraciones
uv run alembic downgrade base        # revertir todo (DB queda vacía)
uv run python -m scripts.reset_db    # borra el .db y reaplica migraciones
uv run python -m scripts.seed        # carga sesión demo
```

### Frontend (Next.js 16 + TypeScript + Tailwind 4 + Biome)

```bash
cd frontend
pnpm install
pnpm dev                             # http://localhost:3000
pnpm test                            # vitest
pnpm lint                            # biome
```

### Comandos rápidos (raíz)

```bash
make up           # docker compose up -d --build
make up-ollama    # docker compose --profile ollama up -d --build
make down         # parar todo
make logs         # docker compose logs -f
make test         # backend + frontend
make health       # curl al health endpoint con json pretty
make seed         # carga datos demo
make reset        # borra DB y la recrea
```

### Corpus normativo (RAG)

El corpus regulatorio europeo se descarga y persiste con:

```bash
make ingest                                    # ingiere todo (es + en, todas las fuentes)
make ingest INGEST_ARGS="--only iso-15459"     # solo una fuente
# Alternativa sin make: cd backend && uv run python -m scripts.ingest_corpus
```

Sources:
- Reg. UE 2024/1781 (ESPR) — EUR-Lex, es + en
- Reg. UE 2023/1542 (baterías, incluye Art. 77 y Annex XIII) — EUR-Lex, es + en
- Actos delegados ESPR publicados — EUR-Lex (lista declarativa)
- CIRPASS-2 Core Ontology — JSON-LD, en
- GS1 Digital Link 1.3.0 — HTML público, en
- ISO/IEC 15459-1..6 — fragmentos-stub con abstract público + URL canónica (texto bajo licencia ISO no se redistribuye)

Salida: `backend/data/corpus/{slug}.{lang}.jsonl`. F2-02 consume desde ese directorio.

Exit codes:
- `0` todo OK
- `1` alguna source falló por red; el resto se completó
- `2` regresión de parser (HTML cambió en EUR-Lex)

## Plugins regulatorios

Cada sector ESPR se modela como un YAML en `plugins/`. Para añadir un sector nuevo, crea `plugins/<sector>.yaml` siguiendo `plugins/_schema.yaml`. El loader valida en arranque: un plugin que no cumpla el schema no se carga y aparece en logs con cita del error.

Cobertura al cierre de F1:

- **`batteries.yaml`** — Reglamento UE 2023/1542. Cubre las 3 secciones estáticas del Anexo XIII (1 pública, 2 interés legítimo, 3 autoridades) con ~48 campos. La Sección 4 (datos individuales dinámicos: SoH operativo, ciclos consumidos, accidentes) queda fuera del alcance del wizard — corresponde a telemetría post-registro.

Próximos sectores (fases futuras):

- `textile.yaml` (F6-04) — ejemplo de contribución comunitaria, plugin sin acto delegado específico todavía.

## Arquitectura en 60 segundos

- **Pipeline lineal**, 7 pasos. Solo 2 son IA: Clasificador (paso 2) y Recolector (paso 5).
- **Una sola SQLite** por instancia. Cinco tablas: `sessions`, `documents`, `extracted_fields`, `audit_log` (con hash chain), `published_dpps`.
- **LiteLLM** como router universal de modelos vía `MODEL_BACKEND`. Backends soportados: Ollama (local), Anthropic, OpenAI, Groq, etc.
- **Langfuse** self-hosted para observabilidad. Cada decisión IA emite una traza con `@observe`; cada `litellm.completion()` emite un span `generation` automáticamente.
- **Identificador del DPP por plugin**: el sector lo declara. Baterías → `iso_iec_15459` por Art. 77.3 del Reg. UE 2023/1542; sectores sin acto delegado específico → `gs1_digital_link` como default. Ver [`docs/adr/0001-identificador-dpp-plugin-declared.md`](./docs/adr/0001-identificador-dpp-plugin-declared.md).
- **Cuatro niveles de acceso** del DPP conforme al Anexo XIII de Reg. 2023/1542: `public`, `legitimate_interest`, `authorities_only`, `individual`. El endpoint público sólo expone `public`.
- **Stack:** FastAPI 0.115 + Pydantic v2, SQLModel 0.0.22, ChromaDB embebido (F2+), embeddings `bge-m3`, LiteLLM, Langfuse v2 (`@observe`), pdfplumber + LLM para PDFs, `segno` para QR, PyNaCl (Ed25519) para firma. Next.js 16 con App Router + Tailwind 4 + Biome 2 + Vitest. Todo en Docker Compose.

## Estado del proyecto (fases del hackathon)

| Fase | Tema | Estado |
|---|---|---|
| **F1** | Fundación: scaffold, modelos, plugins, LLM router, Langfuse | ✅ cerrada |
| F2 | Corpus normativo (RAG con ChromaDB + bge-m3) | ⏳ siguiente |
| F3 | Wizard + Clasificador + BOM dinámico + Recolector | ⏳ |
| F4 | Chat lateral con cita normativa obligatoria | ⏳ |
| F5 | DPP público + QR + firma Ed25519 | ⏳ |
| F6 | Comunidad, calidad, DPGA, plugin textil | ⏳ |

## Decisiones técnicas explícitas

Documentadas en [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) §"Decisiones técnicas explícitas". Resumen:

- **No LangGraph ni LangChain.** Pipeline lineal con FastAPI + `asyncio.gather`.
- **No PostgreSQL ni Redis** para la app. SQLite + FastAPI BackgroundTasks. Postgres aparece sólo como dep interna de Langfuse self-hosted, sin puerto expuesto.
- **No multi-tenant ni OAuth** en el alcance del hackathon. Una instancia = un fabricante.
- **`identifier_scheme` plugin-declared**, no global. ISO/IEC 15459 obligatorio para baterías por Art. 77.3 (Reg. 2023/1542); GS1 Digital Link como esquema por defecto para sectores sin acto delegado específico.

## Contribuir

Las fases F2–F6 están abiertas a contribución. Para añadir un plugin sectorial, ver `plugins/_schema.yaml` y el plugin de baterías como referencia. Detalles de la guía de contribución de plugins llegan en F6-04 (`docs/plugins.md`).

Convenciones del repo:

- **Conventional Commits** en castellano (ver [`CLAUDE.md`](./CLAUDE.md) §"Convención de commits").
- **Sin `Co-Authored-By: Claude`** ni trailers de IA en los commits.
- Documentación e UI en castellano; citas normativas conservan el idioma original del reglamento.

## Licencia

[Apache 2.0](./LICENSE) (cuando exista el archivo formal; el repositorio se publica bajo esta licencia).
