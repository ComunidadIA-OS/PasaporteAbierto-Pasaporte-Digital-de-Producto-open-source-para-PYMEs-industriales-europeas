# Contribuir a PasaporteAbierto

¡Gracias por tu interés! PasaporteAbierto es la implementación de referencia open source del
**Pasaporte Digital de Producto (DPP)** exigido por el Reglamento UE 2024/1781 (ESPR). El
objetivo es que cualquier PYME industrial europea pueda cumplir ESPR sin depender de SaaS
propietario.

La forma de contribución con más impacto es **añadir plugins sectoriales** (ver
[§ Añadir un plugin sectorial](#añadir-un-plugin-sectorial)), porque amplía la cobertura
regulatoria sin tocar el núcleo.

Antes de empezar, lee el [Código de Conducta](./CODE_OF_CONDUCT.md): la participación implica
respetarlo.

## Índice

- [Cómo levantar el entorno](#cómo-levantar-el-entorno)
- [Flujo de trabajo con Git](#flujo-de-trabajo-con-git)
- [Convención de commits](#convención-de-commits)
- [Tests y linting](#tests-y-linting)
- [Añadir un plugin sectorial](#añadir-un-plugin-sectorial)
- [Invariantes que no se negocian](#invariantes-que-no-se-negocian)
- [Abrir un Pull Request](#abrir-un-pull-request)
- [Idioma](#idioma)

## Cómo levantar el entorno

El [README](./README.md#desarrollo) tiene el detalle. En resumen:

```bash
# Backend (Python 3.11 + FastAPI + SQLModel)
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000 --app-dir src

# Frontend (Next.js 16 + TypeScript + Tailwind)
cd frontend
pnpm install
pnpm dev

# Todo junto, en contenedores
make up            # o make up-ollama para incluir el modelo local
```

Verifica que el backend responde: `make health` (o `curl http://localhost:8000/api/v1/health`).

## Flujo de trabajo con Git

El proyecto usa un flujo de tres niveles:

1. **Rama de tarea** — parte siempre de `develop`. Nómbrala por tipo y ámbito, p. ej.
   `feat/plugin-textil`, `fix/verifier-campo-opcional`, `docs/contributing`.
2. **`develop`** — rama de integración. **Todos los PRs van contra `develop`**, nunca contra
   `main` directamente.
3. **`main`** — solo recibe `develop` cuando hay una versión probada (CI verde + revisión).

```bash
git checkout develop && git pull
git checkout -b feat/mi-cambio
# ... trabajo ...
git push -u origin feat/mi-cambio   # abre el PR contra develop
```

## Convención de commits

Los mensajes de commit son la documentación viva del proyecto: priorizan el **porqué** sobre el
qué. Seguimos [Conventional Commits](https://www.conventionalcommits.org/) en castellano.

- **Formato:** `<tipo>(<ámbito>): <resumen imperativo>`
  - Tipos: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `build`, `ci`, `perf`.
  - Ámbito: `backend`, `frontend`, `docs`, `plugins`, `infra`, o el módulo (`pipeline`, `rag`,
    `audit`…).
- **Asunto** ≤ 72 caracteres, imperativo, sin punto final.
  - ✅ `feat(plugins): añade plugin textil con 22 campos del Anexo ESPR`
  - ❌ `cambios`
- **Cuerpo** (obligatorio salvo cambios triviales): separado por una línea en blanco. Explica
  **motivación** (qué requisito cubre, cita el ticket si aplica), **decisiones no obvias**
  (alternativas descartadas, invariantes respetadas) e **impacto** (cambios de contrato API,
  schema YAML, formato del DPP; `BREAKING CHANGE:` al final si rompe compatibilidad).
- **Sin co-author de IA:** los commits van firmados solo por la persona desarrolladora. Nada de
  trailers `Co-Authored-By:`.
- **Granularidad:** un commit = un cambio lógico coherente. Si el mensaje empieza con
  "y además…", divídelo.

Las convenciones completas están en [`CLAUDE.md`](./CLAUDE.md) § "Convención de commits".

## Tests y linting

Un PR no se fusiona sin **CI en verde** (lint + tests). Antes de subir:

```bash
# Backend
cd backend
uv run pytest                  # tests (omite los lentos con -m "not slow")
uv run ruff check .            # lint
uv run ruff format --check .   # formato

# Frontend
cd frontend
pnpm test                      # vitest
pnpm lint                      # biome
```

- Todo cambio de comportamiento llega **con tests**. El pipeline determinista (validación,
  generación del DPP, firma, publicación) está cubierto por tests y debe seguir estándolo.
- Los tests marcados `slow` descargan el modelo `bge-m3` (~2 GB) o tocan ChromaDB; en CI/local
  rápido omítelos con `-m "not slow"`.

## Añadir un plugin sectorial

Añadir un sector ESPR es **solo un YAML en `plugins/`, sin tocar el núcleo**. Pasos:

1. Crea `plugins/<sector>.yaml` siguiendo [`plugins/_schema.yaml`](./plugins/_schema.yaml).
   Usa [`plugins/batteries.yaml`](./plugins/batteries.yaml) como referencia.
2. Declara para cada campo su estado de _provenance_ y su `access_level` conforme a la
   especificación funcional ([`docs/FUNCIONAL.md`](./docs/FUNCIONAL.md) §9).
3. **Cada respuesta normativa exige cita concreta** (`[Reglamento X, Art. Y]`). Referencia la
   base legal del sector.
4. El _loader_ valida el plugin contra el schema al arrancar: si no cumple, no se carga y el
   error aparece en logs. Ejecuta los tests de contrato: `cd backend && uv run pytest tests/plugins`.

Guía detallada de plugins: [`docs/plugins.md`](./docs/plugins.md).

## Invariantes que no se negocian

Estas reglas vienen del diseño ([`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md)). Un PR que las
rompa será rechazado salvo que actualice antes el documento correspondiente:

- **Solo dos pasos del pipeline son IA:** Clasificador (paso 2) y Recolector (paso 5). El resto
  es código determinista cubierto por tests.
- **El chat lateral nunca escribe en el estado del wizard.** El dato lo introduce siempre el
  fabricante.
- **Toda respuesta del chat exige cita normativa.** Sin fragmentos relevantes del RAG, la
  respuesta canónica es "No tengo información suficiente para responder con base normativa".
- **No se puede emitir un DPP parcial conforme.** Falta un campo obligatorio → publicación
  bloqueada en el Verificador.
- **Extensibilidad por configuración:** añadir un sector = un YAML, no modificar el núcleo.
- **Audit log con hash chain:** cada operación significativa escribe en `audit_log` con
  `prev_hash`.

## Abrir un Pull Request

1. Asegúrate de que CI pasa en local (sección anterior).
2. Abre el PR **contra `develop`** y rellena la
   [plantilla de PR](./.github/pull_request_template.md).
3. Describe motivación e impacto; enlaza el issue o ticket que cierra.
4. Espera revisión. Responde al feedback con rigor técnico (no cambies algo solo por cambiarlo;
   si una sugerencia no encaja, explícalo).

## Idioma

- **Documentación, UI, mensajes y commits en castellano.**
- **Las citas normativas conservan el idioma original del reglamento.**
- Lenguaje inclusivo en commits, issues, PRs, docs y comentarios.

¿Dudas sobre cómo contribuir? Abre una
[discusión](https://github.com/ComunidadIA-OS/PasaporteAbierto-Pasaporte-Digital-de-Producto-open-source-para-PYMEs-industriales-europeas/discussions)
o consulta [SECURITY](./SECURITY.md) para reportar vulnerabilidades.
