# Reparto F3 + F4 entre dos personas

Documento de coordinación para paralelizar Fase 3 (componentes IA) y Fase 4 (wizard de 7 pasos) entre dos personas — **Persona A** y **Persona B** — minimizando dependencias bloqueantes.

Asignación nominal de A/B: pendiente. Cuando se asigne, actualizar este documento.

## Premisa: slicing vertical, no horizontal

El reparto natural "una persona el backend, otra el frontend" genera 5 dependencias bloqueantes (cada endpoint de F3 que B necesita esperar). Para evitarlo, cada persona se queda con **backend + frontend de su mitad del wizard** y consume **sus propios endpoints**. Tras el PR-0 conjunto, no quedan endpoints cruzados entre A y B.

## Asignación

### Persona A — "Mitad izquierda: entrada y verificación"

Pasos 1, 2, 3, 6, 7 del wizard + el shell. Backend determinista y el Clasificador.

| Ticket | Naturaleza |
|---|---|
| **F4-01** Layout wizard + persistencia sesión | full-stack |
| **F3-01** Clasificador (paso 2) | backend IA |
| **F4-02** Paso 1 + 2 (descripción + sector) | frontend — consume su propio F3-01 |
| **F4-03** Paso 3 BOM dinámico desde plugin YAML | full-stack |
| **F3-03** Verificador (paso 6 determinista) | backend |
| **F4-06** Paso 6 + 7 (verificación + generación DPP) | frontend — consume su propio F3-03 + endpoint `/dpp` |

### Persona B — "Mitad derecha: extracción y chat"

Pasos 4 y 5 del wizard + chat lateral en los 7 pasos. Recolector con SSE.

| Ticket | Naturaleza |
|---|---|
| **F3-02** Recolector (paso 5, PDFs + asyncio) | backend IA — el más pesado |
| **F4-05** Paso 5 SSE viewer | frontend — consume su propio F3-02 |
| **F4-04** Paso 4 documentos (drag & drop) | full-stack |
| **F3-04** Chat lateral (backend + frontend) | full-stack IA |

### Carga estimada (relativa)

| Persona A | Persona B |
|---|---|
| F4-01 (3) + F3-01 (4) + F4-02 (2) + F4-03 (3) + F3-03 (2) + F4-06 (3) = **17 pts** | F3-02 (6) + F4-05 (3) + F4-04 (3) + F3-04 (4) = **16 pts** |

F3-02 es el ticket más pesado del proyecto. Por eso B tiene menos tickets pero comparable carga.

## Dependencias residuales

Tras este PR-0 **no hay endpoints cruzados** entre A y B. Lo único compartido son **datos y schemas**, ya migrados en F1:

| Recurso compartido | Quién escribe | Quién lee |
|---|---|---|
| Tabla `sessions` (F1) | A en F4-01 (persistencia y override) | B en F4-04 (al subir documentos) y F4-05 (al leer estado tras Recolector) |
| Tabla `extracted_fields` (F1) | A escribe `self_declared` en F4-03 (BOM) | B escribe `verified` / `required_pending` en F3-02; ambos leen en F4-05 y F3-03 |
| Tabla `documents` (F1) | B la usa en F4-04 | A no escribe; F3-03 de A la consulta para verificación |
| `audit_log` (F1) | ambos | ambos (operación `classify`, `override`, `verify`, `publish`, `extract`) |
| `plugins/_schema.yaml` + `batteries.yaml` (F1) | inmutable salvo PR de schema | A en F3-01, F4-03, F3-03; B en F3-02 |

**Regla:** cualquier cambio a schemas SQL o al schema del plugin se hace por **PR conjunto** con revisión de ambas personas, no en solitario.

## Reglas de merge

1. **Toda PR aterriza en `F3-main-branch`**, no en `develop` ni `main`. Cuando F3+F4 estén listas, se mergea `F3-main-branch` → `develop` por PR único de fase.
2. **Una PR de B no se mergea hasta que el ticket de A correspondiente (si aplica) esté en `F3-main-branch`.** Esto solo afecta a F3-04 (chat front consume chat back) — el resto de tickets de B son autocontenidos.
3. **Cambios al PR-0** (schemas Pydantic, stubs, REPARTO) son **conjuntos**. No se modifica `backend/src/app/api/v1/schemas.py` ni los stubs sin acordarlo.
4. **F4-01 shell estructural ya está incluido en PR-0.** A solo añade la lógica de persistencia y reanudación por URL en su primer ticket.
5. **No skip de hooks ni `--no-verify`**. Si falla pre-commit, se arregla el problema, no se bypassa.

## Camino crítico

```
PR-0 conjunto
   │
   ├── A: F4-01 → F3-01 → F4-02 → F4-03 → F3-03 → F4-06
   │
   └── B: F3-02 (PESADO) → F4-05 → F4-04 → F3-04
```

**El cuello de botella es F3-02 (Recolector).** Si B se retrasa ahí, el demo end-to-end del paso 5 se cae. Recomendación: B arranca F3-02 lo antes posible tras el PR-0, en paralelo con F4-04 ligero si quiere alternar.

## Qué está disponible al arrancar (gracias a F1 + F2)

Antes de tocar ningún ticket de F3/F4:

**Backend ya operativo:**
- Las 5 tablas migradas (`sessions`, `documents`, `extracted_fields`, `audit_log`, `published_dpps`)
- `app.models.*` con SQLModel para cada tabla
- `app.db.session.get_session` para inyección en endpoints
- `app.plugins.loader.load_plugin` / `load_all_plugins` con validación contra `_schema.yaml`
- `app.rag.retrieval.search_corpus(query, top_k, filters)` — punto único de RAG
- `app.llm.complete(prompt, **opts)` — wrapper LiteLLM
- `app.observability` con decoradores `@observe(name="...")` de Langfuse

**Frontend ya operativo:**
- Next.js 16 + App Router + TS estricto + Tailwind v4
- `frontend/app/page.tsx` consume `/api/v1/health`
- vitest + @testing-library configurado
- biome para lint/format

**Datos:**
- `plugins/batteries.yaml` con ≥25 campos del Annex XIII (Reg. UE 2023/1542)
- Corpus normativo indexado en ChromaDB

## Tras el PR-0, qué hay nuevo

- `backend/src/app/api/v1/schemas.py` — request/response Pydantic de los 8 endpoints
- `backend/src/app/api/v1/wizard.py` y `chat.py` — stubs marcados con header `X-Stub: true`
- `frontend/app/lib/api.ts` — cliente tipado contra esos schemas
- `frontend/app/wizard/[sessionId]/page.tsx` — shell estructural mínimo (sidebar 7 pasos + área central + slot chat)
- Este documento

A partir de ahí, cada persona puede empezar su primer ticket sin esperar al otro.
