# PasaporteAbierto

<!-- RAG_QUALITY_BADGE:START -->
![RAG quality](https://img.shields.io/badge/RAG_quality-activo-brightgreen)
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

## Quickstart (≤30 minutos)

### Requisitos

- **Docker 24+** y Docker Compose v2.
- **8 GB de RAM** libres (Ollama carga el modelo en memoria).
- ~5 GB de disco la primera vez (descarga del modelo Qwen 2.5 7B).

### 1. Clonar y configurar

```bash
git clone https://github.com/ComunidadIA-OS/PasaporteAbierto-Pasaporte-Digital-de-Producto-open-source-para-PYMEs-industriales-europeas.git
cd PasaporteAbierto-Pasaporte-Digital-de-Producto-open-source-para-PYMEs-industriales-europeas
cp .env.example .env
```

### 2. Elegir backend de IA y levantar

**Opcion A — Modelo local con Ollama (sin API key, sin coste por token):**

El `.env.example` ya viene configurado para esta opcion (`MODEL_LOCAL=true`, `MODEL_BACKEND=ollama:qwen2.5:7b`).

```bash
docker compose --profile ollama up -d --build
```

> La primera vez tarda ~5-10 min: construye las imagenes y descarga el modelo (~5 GB).

**Opcion B — API comercial (Anthropic, OpenAI, Groq...):**

Edita `.env`:

```bash
MODEL_LOCAL=false
MODEL_BACKEND=anthropic:claude-sonnet-4-20250514   # o openai:gpt-4o, groq:llama-3.1-70b-versatile
ANTHROPIC_API_KEY=sk-ant-...                        # descomenta y rellena la key del proveedor
```

```bash
docker compose up -d --build
```

### 3. Verificar que todo esta arriba

```bash
curl -s http://localhost:8000/api/v1/health | python -m json.tool
```

Debe devolver `version`, `model` y `backend`.

| Servicio | URL | Descripcion |
|---|---|---|
| Frontend | http://localhost:3000 | UI del wizard — abre aqui para empezar |
| Backend API | http://localhost:8000/docs | Documentacion OpenAPI interactiva |
| Langfuse | http://localhost:3010 | Panel de observabilidad (crea cuenta admin la primera vez) |
| Ollama | http://localhost:11434 | Solo si usaste Opcion A |

### 4. Generar tu primer DPP

1. Abre **http://localhost:3000** y haz clic en **Crear mi primer DPP**.
2. Describe tu producto (ej: "Bateria industrial Li-ion 5 kWh para almacenamiento residencial").
3. La IA clasifica el sector y carga el plugin con sus campos obligatorios.
4. Rellena el BOM (Bill of Materials) y sube las fichas tecnicas en PDF.
5. El Recolector extrae datos de los PDFs automaticamente.
6. El Verificador confirma completitud.
7. Publica: obtienes JSON-LD firmado con Ed25519, codigo QR y URL publica.

### Activar Langfuse (trazas de IA)

1. Abre `http://localhost:3010` y crea la primera cuenta (queda como admin).
2. Crea un proyecto y copia `Public Key` + `Secret Key`.
3. Pegalas en `.env` como `LANGFUSE_PUBLIC_KEY` y `LANGFUSE_SECRET_KEY`.
4. `docker compose restart backend`.

A partir de ahi, cada decision IA (Clasificador, Recolector, Chat) emitira una traza completa en Langfuse.

## Desarrollo

### Backend (Python 3.11 + FastAPI + SQLModel)

```bash
cd backend
uv sync                              # instala deps
uv run pytest                        # tests (58/58 al cierre de F1)
uv run ruff check .                  # lint
uv run ruff format --check .         # format check
uv run uvicorn app.main:app --reload --port 8000 --app-dir src
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

Cobertura al cierre de F6:

- **`batteries.yaml`** — Reglamento UE 2023/1542. Cubre las 3 secciones estáticas del Anexo XIII (1 pública, 2 interés legítimo, 3 autoridades) con ~48 campos. La Sección 4 (datos individuales dinámicos: SoH operativo, ciclos consumidos, accidentes) queda fuera del alcance del wizard — corresponde a telemetría post-registro.
- **`textile.yaml`** — Plugin beta para textil técnico (~22 campos). Prueba de extensibilidad: valida que añadir un sector nuevo es solo un YAML, sin tocar el core.

## Diagrama de arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                        docker compose up                        │
├──────────────┬──────────────┬──────────────┬────────────────────┤
│   Frontend   │   Backend    │   Langfuse   │  Ollama (opcional) │
│  Next.js 16  │ FastAPI 0.115│  self-hosted │  qwen2.5:7b/14b    │
│    :3000     │    :8000     │    :3010     │     :11434         │
└──────┬───────┴──────┬───────┴──────┬───────┴────────┬───────────┘
       │              │              │                │
       │  REST/SSE    │              │                │
       ├──────────────┤              │                │
       │              │   @observe   │                │
       │              ├──────────────┤                │
       │              │                               │
       │         ┌────┴────────────────────────┐      │
       │         │        Backend interno       │      │
       │         ├─────────┬─────────┬─────────┤      │
       │         │ SQLite  │ChromaDB │ LiteLLM ├──────┤
       │         │ (datos) │ (RAG)   │ (router) │      │
       │         │         │ bge-m3  │         │   ┌──┴──────────┐
       │         └─────────┴─────────┴─────────┘   │ API remota  │
       │                                           │ Claude/GPT  │
       │         ┌─────────────────────────────┐   └─────────────┘
       │         │      plugins/*.yaml          │
       │         │  batteries · textile · ...   │
       │         └─────────────────────────────┘
```

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
| F1 | Fundación: scaffold, modelos, plugins, LLM router, Langfuse | ✅ cerrada |
| F2 | Corpus normativo (RAG con ChromaDB + bge-m3) | ✅ cerrada |
| F3 | Componentes IA: Clasificador, Recolector, Verificador, Chat | ✅ cerrada |
| F4 | Wizard de 7 pasos + persistencia + SSE | ✅ cerrada |
| F5 | Generación y publicación del DPP + firma + audit chain | ✅ cerrada |
| F6 | Comunidad, calidad, DPGA, plugin textil | ⏳ en curso |

Trabajo restante en F6: CI con GitHub Actions, test E2E del flujo completo, video demo.

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

## Pasaporte Abierto

### Misión

PasaporteAbierto es la primera implementación de referencia open source del Pasaporte Digital de Producto (DPP) exigido por el Reglamento UE 2024/1781. Su misión es que cualquier PYME industrial europea pueda cumplir ESPR sin depender de SaaS propietario, ejecutando una instancia bajo su propio control.

### Métricas iniciales

*Al cierre de la fase F6 del hackathon (2026-05-25):*

- **Sectores cubiertos por plugins**: 2 (`batteries`, `textile`).
- **Fuentes referenciadas en el corpus RAG**: 6 (ESPR — Reg. UE 2024/1781, baterías — Reg. UE 2023/1542, actos delegados ESPR, CIRPASS-2 Core, GS1 Digital Link 1.3.0, ISO/IEC 15459).
- **Endpoints públicos del DPP**: 1 (`GET /dpp/{slug}` con content negotiation `application/ld+json` / `text/html`).
- **Componentes IA acotados**: 2 (Clasificador, Recolector); el resto del pipeline es código determinista.

### Proceso de adhesión

Para postularse como instancia oficial del ecosistema Pasaporte Abierto:

1. Desplegar la instancia siguiendo el [quickstart](#setup-en-30-minutos).
2. Contribuir un plugin de tu sector si todavía no está cubierto. Ver [guía de plugins](./docs/plugins.md).
3. Cumplir los criterios de [`docs/dpga.md`](./docs/dpga.md) (licencia, privacidad, no recopilación de PII).
4. Abrir issue en el repositorio principal con la URL pública de tu instancia.

> **Importante**: cada instancia es soberana. El proyecto no impone un registro central; las instancias se conectan opcionalmente vía el DPP federado (roadmap post-hackathon).

## Licencia

Apache License 2.0. Ver [`LICENSE`](./LICENSE).
