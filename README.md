# PasaporteAbierto

[![CI](https://github.com/ComunidadIA-OS/PasaporteAbierto-Pasaporte-Digital-de-Producto-open-source-para-PYMEs-industriales-europeas/actions/workflows/ci.yml/badge.svg)](https://github.com/ComunidadIA-OS/PasaporteAbierto-Pasaporte-Digital-de-Producto-open-source-para-PYMEs-industriales-europeas/actions/workflows/ci.yml)
[![Licencia: Apache 2.0](https://img.shields.io/badge/licencia-Apache--2.0-blue.svg)](./LICENSE)
![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)
![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg)
[![Código de conducta: Contributor Covenant](https://img.shields.io/badge/c%C3%B3digo%20de%20conducta-Contributor%20Covenant%202.1-ff69b4.svg)](./CODE_OF_CONDUCT.md)
<!-- RAG_QUALITY_BADGE:START -->
![RAG quality](https://img.shields.io/badge/RAG_quality-activo-brightgreen)
<!-- RAG_QUALITY_BADGE:END -->

Aplicación web auto-hospedable para que fabricantes PYME generen el **Pasaporte Digital de Producto (DPP)** exigido por el Reglamento UE 2024/1781 (ESPR). Open source, Apache 2.0.

## Tabla de contenidos

- [Documentación](#documentación)
- [Requisitos](#requisitos)
- [Quickstart (≤30 minutos)](#quickstart-30-minutos)
- [Probar en modo demo](#probar-en-modo-demo)
- [Autenticación (login / logout)](#autenticación-login--logout)
- [Accesibilidad](#accesibilidad)
- [Desarrollo](#desarrollo)
- [Plugins regulatorios](#plugins-regulatorios)
- [Diagrama de arquitectura](#diagrama-de-arquitectura)
- [Arquitectura en 60 segundos](#arquitectura-en-60-segundos)
- [Estado del proyecto](#estado-del-proyecto-fases-del-hackathon)
- [Decisiones técnicas explícitas](#decisiones-técnicas-explícitas)
- [Contribuir](#contribuir)
- [Pasaporte Abierto](#pasaporte-abierto)
- [Licencia](#licencia)

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

## Probar en modo demo

El **modo demo** precarga datos de ejemplo en el wizard para que recorras el flujo completo sin teclear la descripción, sin rellenar los ~47 campos del BOM y sin preparar PDFs. Se controla con el flag `DEMO_MODE`.

### Activarlo

```bash
make demo-ui
```

Pone `DEMO_MODE=true` en `.env` (si no estaba), re-arranca el stack para aplicarlo y abre `http://localhost:3000/wizard`. Equivale a editarlo a mano y reconstruir:

```bash
# en .env
DEMO_MODE=true

docker compose up -d --build   # o `make up`
```

> Con `DEMO_MODE=false` (valor por defecto y recomendado en producción) los botones desaparecen y los endpoints `/api/v1/demo/*` devuelven `404`.

### Qué carga

Con el modo activo y **sesión iniciada** ([login](#autenticación-login--logout)), aparecen botones de ejemplo a lo largo del flujo:

| Dónde | Botón | Qué hace |
|---|---|---|
| Paso 1 · descripción | **Cargar ejemplo** | Rellena la descripción del producto (una batería). |
| Paso 3 · BOM | **✨ Cargar ejemplo** | Rellena los ~47 campos del plugin de baterías. |
| Paso 4 · documentos | **Cargar PDFs de ejemplo** | Genera e inserta 4 PDFs sintéticos (certificados/datasheets). |
| Panel (`/panel`) | **Generar ejemplos** | Siembra DPP de ejemplo (en curso y publicados) para probar el panel sin Ollama. |

Los datos salen de un único origen, `scripts/e2e_demo/config.yaml`. Los botones del frontend se gobiernan con `NEXT_PUBLIC_DEMO_MODE`, que `docker compose` espeja desde el `DEMO_MODE` del backend — por eso hay que **reconstruir** el stack al cambiar el flag, no basta con reiniciar.

## Autenticación (login / logout)

Desde [ADR-0004](./docs/adr/0004-login-sesion-server-side-cookie-httponly.md) la app tiene **login propio de email + contraseña**. No es OAuth ni multi-tenant: son cuentas dentro de la misma instancia auto-hospedada (una instancia = un fabricante). Protege los datos de la PYME (BOM, PDFs, chat, DPP en curso) y permite reanudar "mis sesiones" por persona, no por URL.

Cómo funciona:

- **Hash de contraseña** con `scrypt` (stdlib, sin dependencias nuevas) y salt por contraseña.
- **Sesión server-side** persistida en SQLite (`auth_sessions`); en BD solo se guarda el **SHA-256** del token, así una fuga de BD no entrega sesiones reutilizables. Es revocable (logout) y caduca a los 30 días por defecto.
- **Cookie `httpOnly` + `SameSite=Lax`:** inaccesible desde JS (mitiga XSS). No se guarda nada de auth en `localStorage`.
- **Propiedad de sesiones:** `POST /sessions` exige login y graba `user_id`; una sesión ajena devuelve `404` sin confirmar su existencia.

### En la UI

1. Abre **http://localhost:3000** → te redirige a **`/login`** si no hay sesión activa.
2. Regístrate (si `ALLOW_REGISTRATION=true`) o inicia sesión con email + contraseña.
3. El panel **`/panel`** lista tus sesiones y DPP empezados, listos para reanudar.
4. **Cerrar sesión** revoca la sesión en el servidor y borra la cookie.

> El `proxy.ts` de Next 16 protege `/wizard` y `/panel`: sin cookie de sesión, redirige a `/login`.

### Endpoints (`/api/v1/auth`)

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/auth/register` | Alta de cuenta (solo si `ALLOW_REGISTRATION=true`). |
| `POST` | `/auth/login` | Inicia sesión y fija la cookie. Error genérico `401` (no distingue email de contraseña). |
| `POST` | `/auth/logout` | Revoca la sesión server-side y borra la cookie. |
| `GET` | `/auth/me` | Devuelve el usuario autenticado. |

### Configuración (`.env`)

| Variable | Por defecto | Para qué |
|---|---|---|
| `ALLOW_REGISTRATION` | `true` | Permite el alta self-service. Ponlo a `false` para cerrar el registro tras dar de alta a los operarios. |
| `AUTH_COOKIE_SECURE` | `false` | La cookie solo viaja por HTTPS si es `true`. **Obligatorio `true` tras HTTPS.** |
| `AUTH_COOKIE_SAMESITE` | `lax` | `lax` si front y back son same-site; `none` (exige `Secure=true`) entre dominios distintos. |
| `AUTH_COOKIE_NAME` | `pa_session` | Nombre de la cookie (espéjalo en `NEXT_PUBLIC_AUTH_COOKIE_NAME` del frontend). |
| `AUTH_SESSION_TTL_DAYS` | `30` | Vida de la sesión en días. |

## Accesibilidad

El frontend cumple **WCAG 2.1 nivel AA** ([PR #61](https://github.com/ComunidadIA-OS/PasaporteAbierto-Pasaporte-Digital-de-Producto-open-source-para-PYMEs-industriales-europeas/pull/61)). Son dos capas: ajustes estructurales siempre activos y un widget para que cada persona adapte la interfaz a su necesidad.

### Widget de accesibilidad

Botón flotante en la esquina inferior izquierda (no se solapa con el chat, que vive a la derecha) que abre un panel con **6 modos conmutables**, persistidos en `localStorage`. Un script inline en `layout.tsx` los reaplica antes de pintar, sin parpadeo al recargar:

| Modo | Qué hace |
|---|---|
| **Modo daltónico** | Paleta segura Okabe-Ito; los avisos usan símbolos (✓ / ⚠ / ✕), no solo color. |
| **Modo dislexia** | Tipografía Atkinson Hyperlegible y más espacio entre letras, palabras y líneas. |
| **Alto contraste** | Refuerza el contraste de texto y bordes, y subraya los enlaces. |
| **Texto más grande** | Aumenta el tamaño de todo el contenido. |
| **Subrayar enlaces** | Distingue los enlaces sin depender del color. |
| **Reducir animaciones** | Desactiva transiciones y movimientos de la interfaz. |

El panel se maneja por teclado (Escape para cerrar, foco al primer control al abrir y devolución del foco al botón al salir) e incluye un **"Restablecer todo"**.

### Cumplimiento WCAG 2.1 AA (siempre activo)

Sin tocar ningún interruptor, el frontend ya incorpora:

- **Skip-link** "Saltar al contenido principal" como primer elemento del `<body>` (WCAG 2.4.1); cada ruta marca su `<main id="main-content">`.
- **Anillo de foco** `:focus-visible` en todos los elementos interactivos (2.4.7 / 2.4.11).
- **Barras de progreso** con `role="progressbar"` y `aria-valuenow/min/max/text`: stepper del wizard, completitud del BOM, extracción SSE (paso 5) y verificación (paso 6).
- **Formularios accesibles**: `aria-required`, `aria-invalid` y `aria-describedby` en los inputs del BOM.
- **Regiones dinámicas**: `role="log"` + `aria-live` en el historial del chat; `role="status"` para los avisos de subida de PDFs y mensajes dinámicos.
- **Focus trap** en el chat lateral y en los modales (p. ej. "ver fuente" del extracto), devolviendo el foco al elemento que los abrió al cerrarlos.
- Respeto de `prefers-reduced-motion` y texto `sr-only` para contexto (p. ej. "(abre en nueva pestaña)" en los enlaces externos).

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

1. Desplegar la instancia siguiendo el [quickstart](#quickstart-30-minutos).
2. Contribuir un plugin de tu sector si todavía no está cubierto. Ver [guía de plugins](./docs/plugins.md).
3. Cumplir los criterios de [`docs/dpga.md`](./docs/dpga.md) (licencia, privacidad, no recopilación de PII).
4. Abrir issue en el repositorio principal con la URL pública de tu instancia.

> **Importante**: cada instancia es soberana. El proyecto no impone un registro central; las instancias se conectan opcionalmente vía el DPP federado (roadmap post-hackathon).

## Licencia

El proyecto se publica bajo la **Licencia Apache 2.0** (identificador SPDX: `Apache-2.0`), una licencia permisiva aprobada por la OSI. El texto legal íntegro está en [`LICENSE`](./LICENSE) — en inglés, porque la Apache Software Foundation solo reconoce como jurídicamente válida la versión original; las traducciones son orientativas, no vinculantes.

**Qué te permite** (sin pedir permiso ni pagar):

- Usar el software con cualquier fin, incluido **comercial**.
- **Modificarlo** y crear trabajos derivados.
- **Distribuirlo** y sublicenciarlo, en abierto o dentro de un producto cerrado.
- Incluye una **concesión expresa de patentes** por parte de los contribuidores: quien aporta código no puede luego demandarte por la patente que ese código cubre. Lleva además una cláusula de retorsión: si tú inicias un litigio de patentes contra el proyecto, pierdes la licencia.

**Qué te exige:**

- Conservar el **aviso de copyright y la licencia** en las copias.
- **Indicar los cambios** relevantes en los archivos que modifiques.
- Mantener el archivo `NOTICE` (si existe) con sus atribuciones.

**No ofrece** garantía ni asume responsabilidad: el software se entrega "tal cual".

**Por qué Apache 2.0 y no otra:** es permisiva (máxima adopción por PYMEs, sin fricción legal) pero, a diferencia de MIT, **añade protección de patentes** explícita — algo relevante en un proyecto de cumplimiento normativo. Cumple además el requisito del hackathon de usar una licencia reconocida por OSI/FSF. Para cualquier duda legal, prevalece el texto de [`LICENSE`](./LICENSE).
