# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Contexto del proyecto

PasaporteAbierto es una aplicación web auto-hospedable que ayuda a fabricantes PYME a generar el **Pasaporte Digital de Producto (DPP)** exigido por el Reglamento UE 2024/1781 (ESPR). El alcance inicial es un hackathon de 1 semana dividido en 6 fases (F1–F6).

**Estado actual del repo:** scaffolding pendiente. Sólo existen los documentos de diseño y los tickets de las 6 fases. No hay `package.json`, `pyproject.toml`, `docker-compose.yml` ni código aún. La fase F1 (`docs/tickets/F1.md`) define la creación del monorepo.

## Fuentes de verdad

Antes de tocar nada, consulta en este orden:

1. `docs/ARCHITECTURE.md` — arquitectura técnica, contratos entre componentes, stack, decisiones explícitas y descartes razonados.
2. `docs/FUNCIONAL.md` — especificación funcional, UX paso a paso, reglas duras del producto y criterios globales de aceptación.
3. `docs/tickets/F1.md` … `docs/tickets/F6.md` — tickets de cada fase con historia de usuario, descripción y criterios de aceptación.

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

Aún no existen — se definen en el ticket **F1-01** (scaffolding del monorepo). Una vez aplicado, esta sección debe actualizarse con los comandos reales (`docker compose up`, healthcheck `GET /api/v1/health`, Makefile, scripts de test, etc.). Hasta entonces, no inventes comandos: revisa primero si el ticket que estás implementando ya los introduce.
