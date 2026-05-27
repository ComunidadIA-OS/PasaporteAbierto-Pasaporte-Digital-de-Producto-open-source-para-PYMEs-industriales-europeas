# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Contexto del proyecto

PasaporteAbierto es una aplicación web auto-hospedable que ayuda a fabricantes PYME a generar el **Pasaporte Digital de Producto (DPP)** exigido por el Reglamento UE 2024/1781 (ESPR). El alcance inicial es un hackathon de 1 semana dividido en 6 fases (F1–F6).

**Estado actual del repo:** el scaffolding (F1) está hecho y el monorepo funciona con `docker compose`. Mapa:

```
backend/          FastAPI + SQLModel + RAG. Código en backend/src/app/, tests en backend/tests/.
  src/app/api/v1/    rutas /api/v1 (wizard, chat, audit, plugins, health, demo) + public_dpp.py (GET /dpp/{uri})
  src/app/{classifier,collector,chat}/  agentes IA (agent.py)
  src/app/{verifier,dpp,audit}/          pasos deterministas del pipeline
  src/app/rag/       ingest (solo eurlex: corpus normativo), chunking, embeddings, index, retrieval, eval
  src/app/plugins/   loader (carga y valida YAML sectoriales)
  src/app/{models,db}/  SQLModel + sesión SQLite; migraciones en backend/alembic/
  src/app/{llm,observability}/  router LiteLLM y cliente Langfuse
  scripts/           seed, reset_db, ingest_corpus, reindex, rag_quality_badge
frontend/         Next.js 16 (App Router), arquitectura modular en frontend/src/
plugins/          batteries.yaml, textile.yaml + _schema.yaml
docs/             ARCHITECTURE.md, FUNCIONAL.md, adr/, tickets/, handoffs/, research/
```

## Fuentes de verdad

Antes de tocar nada, consulta en este orden:

1. **`.claude/HACKATHON.md`** — reglas duras del hackathon (deadlines, licencia OSS, TRL, criterios de evaluación). Si una decisión técnica entra en conflicto con estas reglas, **la regla del hackathon gana**.
2. `docs/ARCHITECTURE.md` — arquitectura técnica, contratos entre componentes, stack, decisiones explícitas y descartes razonados.
3. `docs/FUNCIONAL.md` — especificación funcional, UX paso a paso, reglas duras del producto y criterios globales de aceptación.
4. `docs/adr/` — decisiones de arquitectura ya cerradas (0001 identificador declarado por el plugin, 0002 vocabulario JSON-LD local, 0003 slug opaco en la URL pública). Un ADR aceptado pesa lo mismo que `ARCHITECTURE.md`.
5. `docs/tickets/F1.md` … `docs/tickets/F6.md` — tickets de cada fase con historia de usuario, descripción y criterios de aceptación.

Apoyo: `README.md` es la referencia operativa más completa (quickstart, comandos). `docs/handoffs/` guarda el estado al cierre de cada sesión.

Si una decisión técnica o funcional contradice estos documentos, **el documento gana**: actualiza el doc antes de implementar, no al revés.

## Stack planificado (definido en ARCHITECTURE.md)

- **Backend:** FastAPI 0.115 + Python 3.11, Pydantic v2, SQLModel sobre SQLite única, ChromaDB embebido, embeddings `bge-m3` vía sentence-transformers, LiteLLM como router de modelos, Ollama (Qwen 2.5 14B por defecto) o APIs comerciales vía `MODEL_BACKEND`, `pdfplumber` + LLM para PDFs, `segno` para QR, PyNaCl (Ed25519) para firma. **El esquema del identificador único del DPP lo declara el plugin sectorial** (ISO/IEC 15459 para baterías por Art. 77.3 de Reg. UE 2023/1542; GS1 Digital Link como fallback genérico — ver `ARCHITECTURE.md §"Identificador único y niveles de acceso del DPP"`).
- **Frontend:** Next.js 16 (App Router), TypeScript estricto, Tailwind, shadcn/ui, React Hook Form para formularios dinámicos generados desde plugins YAML.
- **Observabilidad:** Langfuse self-hosted. Audit log con hash chain en SQLite (canal independiente de Langfuse).
- **Despliegue:** `docker compose up` con backend, frontend, Langfuse y Ollama opcional (profile).
- **API:** todas las rutas bajo `/api/v1`. Stream de progreso para operaciones largas vía SSE.

## Invariantes arquitectónicas (no negociables)

Estas reglas vienen del diseño y se aplican siempre, salvo que se actualice el doc correspondiente:

- **Sólo dos pasos del pipeline son IA**: Clasificador (paso 2) y Recolector (paso 5). Todo lo demás — validación, generación del DPP, firma, publicación — es código determinista cubierto por tests.
- **El chat lateral nunca escribe en el estado del wizard.** El dato lo introduce siempre el fabricante. El chat es un endpoint independiente del pipeline.
- **Toda respuesta del chat exige cita normativa concreta** (`[Reglamento X, Art. Y]`). Si el RAG no devuelve fragmentos relevantes, la respuesta canónica es "No tengo información suficiente para responder con base normativa".
- **El corpus RAG es exclusivamente normativo**: solo reglamentos UE (ESPR, baterías) y actos delegados — texto citable como ley. El esquema del identificador (ISO/IEC 15459, GS1 Digital Link) y el vocabulario del DPP (CIRPASS-2 Core) **no** están en el RAG: los declara el plugin sectorial y los aplica la generación determinista del DPP. La descarga de EUR-Lex usa el repositorio **Cellar** (`publications.europa.eu/resource/celex/{celex}`), porque el endpoint `legal-content` responde `202` vacío a clientes no-navegador. El chat se alimenta de tres entradas separadas: RAG (cita la ley), plugin `.yaml` (guía por campos/documentos del paso) y estado de la sesión (dónde estás).
- **El Recolector no dialoga con el usuario.** Termina, escribe estado en `extracted_fields` y devuelve control al wizard. Los tres estados de provenance (`verified` / `self_declared` / `required_pending`) son canon — ver §9.1 de `FUNCIONAL.md`. **Cada campo del plugin tiene además un `access_level` ortogonal** (`public` / `legitimate_interest` / `authorities_only` / `individual`) conforme a las 4 secciones del Annex XIII del Reg. UE 2023/1542 — ver §9.2 de `FUNCIONAL.md`. El endpoint público `GET /dpp/{gs1_uri}` solo expone campos con `access_level = public`.
- **No se puede emitir un DPP parcial conforme.** Si falta cualquier campo obligatorio del plugin, la publicación queda bloqueada en el paso 6 (Verificador).
- **Extensibilidad por configuración**: añadir un sector ESPR significa añadir un YAML en `plugins/`, no modificar el núcleo. Cada plugin se valida contra `plugins/_schema.yaml` al arrancar; un plugin que no cumpla el schema no se carga.
- **Audit log con hash chain:** cada operación significativa escribe en `audit_log` con `prev_hash`. El endpoint `GET /audit/verify` recorre la cadena.

## Decisiones descartadas (no reabrir sin justificación nueva)

`ARCHITECTURE.md` lista descartes explícitos. No los reintroduzcas en propuestas:

- **No LangGraph / LangChain.** Pipeline lineal con FastAPI endpoints + `asyncio.gather` para el paralelismo del Recolector.
- **No PostgreSQL ni Redis.** Una instancia = un fabricante PYME, SQLite + FastAPI BackgroundTasks bastan.
- **No multi-tenant ni OAuth** en el alcance del hackathon. Basic auth si hace falta exponer en red local.

## Pipeline del wizard (7 pasos)

| Paso | Tipo | Endpoint |
|---|---|---|
| 1 · descripción | det | `POST /sessions` |
| 2 · clasificación | IA | `POST /sessions/{id}/classify` |
| 3 · BOM | det | `PUT /sessions/{id}/bom` |
| 4 · documentos | det | `GET`/`POST /sessions/{id}/documents` |
| 5 · extracción | IA | `POST /sessions/{id}/extract` (SSE) |
| 6 · verificación | det | `GET /sessions/{id}/verify` |
| 7 · generación DPP | det | `POST /sessions/{id}/dpp` |

Endpoint público del DPP (`GET /dpp/{gs1_uri}`) usa **content negotiation**: `application/ld+json` devuelve JSON-LD CIRPASS-2 Core; `text/html` devuelve la página renderizada (con distinción visual entre `verified` y `self_declared`).

## Convenciones del proyecto

- **Idioma:** documentación, UI, mensajes y commits en castellano. Las citas normativas conservan el idioma original del reglamento.
- **Plugins:** ubicados en `plugins/`, uno por sector. Cobertura mínima del hackathon: `batteries.yaml` (Reglamento UE 2023/1542) y `textile.yaml` como prueba de extensibilidad.
- **Comandos personalizados:** `.claude/commands/` contiene `session_retro.md` para retrospectivas técnicas de sesión.

### Convención de commits

Los mensajes de commit son la documentación viva del proyecto: priorizan el **porqué** sobre el qué.

- **Formato Conventional Commits:** `<tipo>(<ámbito>): <resumen imperativo en castellano>`.
  - Tipos: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `build`, `ci`, `perf`.
  - Ámbito: `backend`, `frontend`, `docs`, `plugins`, `infra`, o el módulo concreto (`pipeline`, `rag`, `audit`, etc.).
- **Asunto (primera línea, ≤ 72 caracteres):** imperativo, sin punto final. Ejemplo válido: `feat(backend): añade endpoint /sessions/{id}/classify con plugin batteries`. Ejemplo a evitar: `cambios`.
- **Cuerpo (obligatorio cuando el cambio no es trivial):** separado del asunto por una línea en blanco. Explica:
  1. **Motivación:** qué problema resuelve o qué requisito del ticket/`FUNCIONAL.md`/`ARCHITECTURE.md` cubre (cita el ticket: `F1-01`, `F3-02`…).
  2. **Decisiones no obvias:** alternativas descartadas, tradeoffs, invariantes que se respetan (p. ej. "mantiene el chat fuera del estado del wizard, §9 FUNCIONAL.md").
  3. **Impacto:** cambios de contrato (API, schema YAML, formato del DPP), migraciones requeridas, breaking changes (`BREAKING CHANGE:` al final del cuerpo).
- **Trivial sí permite asunto solo:** typos, bumps de dependencia menores, formateo. Todo lo demás lleva cuerpo.
- **No co-author de IA:** los commits van firmados solo por el desarrollador. Sin trailers `Co-Authored-By: Claude` u otros agentes (regla aplicada también vía `.claude/settings.json`).
- **Granularidad:** un commit = un cambio lógico coherente. Si el mensaje empieza con "y además…", divide en dos commits.

## Comandos de desarrollo

Vía `Makefile` (raíz):

- `make up` / `make up-ollama` / `make up-remote` — levanta el stack con `docker compose` (toggle `MODEL_LOCAL` en `.env` añade el profile `ollama`). `make down`, `make logs`.
- `make health` — healthcheck `GET /api/v1/health`.
- `make test` — `cd backend && uv run pytest` + tests del frontend.
- `make ingest` — ingesta del corpus normativo (`PYTHONPATH=src uv run python -m app.rag.ingest`; acepta `INGEST_ARGS`, p. ej. `--only ue-2023-1542`, `--lang es`, `--force-refresh`).
- `make seed` / `make reset` — semilla y reseteo de la BD. `make demo` / `make demo-full` — recorrido E2E del pipeline.

RAG (desde `backend/`):

- `PYTHONPATH=src uv run python -m scripts.reindex` — reembebe el corpus (`data/corpus/*.jsonl`) en ChromaDB (`data/chroma/`). Hace reset+rebuild: idempotente aunque cambie el chunking. Tras `make ingest` hay que reindexar para que el cambio llegue al índice.
- `uv run pytest tests/rag/` — tests del RAG; los marcados `slow` descargan bge-m3 (~2 GB) y tocan ChromaDB (omitir con `-m "not slow"`).

Backend usa **uv** (no pip): `cd backend && uv run <cmd>`. Lint/format con `ruff`.
