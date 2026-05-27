# Reorden del front a arquitectura modular Logixs — diseño

**Fecha:** 2026-05-27
**Rama:** `front-reorg-modules` (desde `develop`; PR contra `develop`)
**Estado:** diseño aprobado, pendiente de plan de implementación

## Objetivo

Reordenar el frontend de PasaporteAbierto (`frontend/`) para que siga las
convenciones de arquitectura Next.js de Logixs: `src/app` solo rutas,
features en `src/modules/<feature>`, transporte en `src/lib`, manejo
centralizado en `src/core`. El resultado debe "parecer un proyecto
profesional" sin alterar lo que el usuario ve ni cómo se comporta la app.

## Restricciones duras (no negociables)

1. **Cero cambios de UI/UX.** Mismo `globals.css` (se mueve verbatim), mismo
   JSX, mismas interacciones, mismo aspecto. Es un refactor puramente
   estructural: la salida renderizada y el comportamiento son idénticos.
2. **No se introducen dependencias nuevas.** En particular **no shadcn/ui ni
   CVA** (no están en el proyecto; añadirlos exige confirmación explícita y
   queda fuera de alcance). La capa `components/ui/` de la convención no
   aplica en esta tanda.
3. **Migración incremental por slices.** Cada slice deja la app funcionando y
   se commitea por separado, verificando antes de cada commit. La app nunca
   queda en estado roto.
4. **`page.tsx` / `layout.tsx` mantienen `default export`** (lo exige Next:
   excepción de framework a la regla "nunca default exports"). Todo lo demás,
   named exports.

## Estado actual (hechos verificados)

- Next 16.2.6 / React 19.2.4. Alias `@/*` → `./*` (no hay `src/`).
- 17 archivos planos bajo `app/`. Componentes ya usan **named exports**;
  `default` solo en `page.tsx`/`layout.tsx`.
- `app/lib/api.ts` es un monolito (39 exports): transporte + tipos espejo de
  `backend/.../schemas.py` + manejo de error disperso.
- **Todo el fetch es client-side**; no hay Server Actions.
- `extract` (paso 5, Recolector) es **SSE por streaming** (`fetch` +
  `ReadableStream`, `api.ts:395`), no `EventSource`. Inherentemente cliente.
- Base URL: `api.ts:6` usa `NEXT_PUBLIC_API_URL ?? "http://localhost:8000"`.
  El build solo inyecta `NEXT_PUBLIC_DEMO_MODE` como ARG → el bundle de
  cliente quedó con `localhost:8000` (alcanzable desde el host; CORS lo
  permite, `backend/main.py:27`). La env `NEXT_PUBLIC_API_URL=http://backend:8000`
  de compose solo afecta lecturas server-side en runtime.

## Estructura objetivo

```
frontend/
├── src/
│   ├── app/                              ← SOLO rutas (default exports)
│   │   ├── layout.tsx
│   │   ├── globals.css
│   │   ├── page.tsx                      → renderiza <LandingPage/>
│   │   └── wizard/
│   │       ├── page.tsx                  → entrada (crear sesión)
│   │       └── [sessionId]/page.tsx      → renderiza <WizardPage sessionId/>
│   ├── modules/
│   │   ├── landing/
│   │   │   ├── pages/LandingPage.tsx         (Server)
│   │   │   └── components/{LandingContent,Reveal}.tsx   (Client)
│   │   └── wizard/
│   │       ├── pages/WizardPage.tsx          (Server, wrapper fino)
│   │       ├── components/                   (Client)
│   │       │   ├── WizardContent.tsx         (ex wizard-client.tsx)
│   │       │   └── Step1Description … Step7Publish.tsx
│   │       ├── actions/                       (se crea; ver "Data-flow")
│   │       └── lib/{field-labels,wizard-api}.ts
│   ├── lib/
│   │   ├── fetch.ts                       (serverFetch, useClientFetch)
│   │   └── demo-mode.ts
│   └── core/
│       ├── errors/                        (getDataOrError + tipos de error)
│       └── responses/                     (tipos espejo de schemas backend)
└── tsconfig.json  → alias "@/*": ["./src/*"]
```

## Mapeo archivo por archivo

| Actual | Destino |
|---|---|
| `app/layout.tsx` | `src/app/layout.tsx` (sin cambios de export) |
| `app/globals.css` | `src/app/globals.css` (verbatim) |
| `app/page.tsx` | `src/app/page.tsx` (fino) + lógica → `modules/landing/pages/LandingPage.tsx` |
| `app/components/Reveal.tsx` | `src/modules/landing/components/Reveal.tsx` |
| `app/wizard/page.tsx` | `src/app/wizard/page.tsx` (fino) + lógica → `modules/wizard/components/WizardEntry.tsx` |
| `app/wizard/[sessionId]/page.tsx` | `src/app/wizard/[sessionId]/page.tsx` (fino) → `modules/wizard/pages/WizardPage.tsx` |
| `app/wizard/[sessionId]/wizard-client.tsx` | `src/modules/wizard/components/WizardContent.tsx` (rename a PascalCase) |
| `app/wizard/[sessionId]/steps/Step{1..7}*.tsx` | `src/modules/wizard/components/Step{1..7}*.tsx` |
| `app/lib/api.ts` | dividir: transporte → `src/lib/fetch.ts`; errores → `src/core/errors/`; tipos → `src/core/responses/`; funciones del wizard → `src/modules/wizard/lib/wizard-api.ts` |
| `app/lib/demo-mode.ts` | `src/lib/demo-mode.ts` |
| `app/lib/field-labels.ts` | `src/modules/wizard/lib/field-labels.ts` |

## Data-flow (decisiones)

- **Fetch del wizard: se preserva en cliente.** `WizardPage` (Server) es un
  wrapper fino que renderiza `WizardContent` (Client); la carga del estado
  sigue en cliente, idéntica a hoy. Cumple `page → Page → Content` **sin**
  cambiar el comportamiento de carga (cero delta de UX). No se mueve a SSR
  porque eso alteraría el loading/flash.
- **Mutaciones: se mantienen en cliente** vía `useClientFetch`. Motivos: (a)
  `extract` es SSE y no puede ser Server Action → el modelo es mixto de todos
  modos; (b) convertir a Server Actions es una reescritura (`useTransition`/
  `useActionState`) que cambia cómo aparecen loading/errores → riesgo de delta
  de UX prohibido; (c) añade una pata de red (navegador → Next → backend) sin
  beneficio visible ahora.
- **`actions/` se crea** como parte de la estructura, pero **vacío** (o con un
  README que explica que se poblará si en el futuro se adoptan Server Actions
  como cambio deliberado). No se fuerza contenido en esta tanda.
- **`lib/fetch.ts`** expone `serverFetch()` y `useClientFetch()` como
  envoltorios del `fetch` actual, leyendo la base URL de `NEXT_PUBLIC_API_URL`
  (mismo comportamiento que hoy). `getDataOrError()` en `core/errors`
  centraliza el manejo que hoy está inline en `api.ts`.

## Plan de slices (un commit por slice, verificando antes)

0. **Rama + spec** (este commit).
1. **Esqueleto `src/`:** mover `app/` → `src/app/`, actualizar alias
   `@/*` → `./src/*` en tsconfig, ajustar imports. Verificar: app arranca y
   render idéntico. Commit.
2. **Capa `lib/` + `core/`:** dividir `api.ts` en `lib/fetch.ts` +
   `core/errors` + `core/responses`; mover `demo-mode.ts` → `lib`. Verificar:
   flujo intacto. Commit.
3. **Módulo `landing`:** `page.tsx` → `LandingPage` (Server) → `LandingContent`
   (Client) + `Reveal`. Verificar: home idéntica. Commit.
4. **Módulo `wizard`:** `wizard-client` → `WizardContent`, steps → components,
   `field-labels` → `modules/wizard/lib`, `[sessionId]/page` → `WizardPage`
   fino, entrada del wizard → `WizardEntry`, crear `actions/` vacío. Verificar:
   flujo de 7 pasos idéntico (incluida la extracción SSE). Commit. (Puede
   subdividirse si conviene.)

**Verificación por slice:** la app está levantada (`make up`); se comprueba la
ruta afectada en el navegador y/o con `curl`, confirmando no-regresión antes de
cada commit. (No hay tests de frontend; vitest está configurado pero sin
`*.test`.)

## Fuera de alcance

- shadcn/ui, CVA, `components/ui/`.
- Poblar `actions/` con Server Actions.
- Mover el fetch del wizard a SSR.
- Mover la vista pública del DPP (`GET /dpp/{slug}`, hoy HTML del backend) a
  una ruta Next — es una decisión de arquitectura ya cerrada (content
  negotiation, ver `ARCHITECTURE.md`).
- Cualquier cambio visual o de comportamiento.

## Riesgos

- **Imports rotos al mover a `src/` y cambiar el alias.** Mitigación: slice 1
  aislado, verificación de arranque antes de commitear.
- **`extract` (SSE) frágil.** Mitigación: no se toca su lógica; solo cambia de
  ubicación. Se verifica el paso 5 en el slice 4.
- **`globals.css` (2.274 líneas) ligado a rutas de clase.** Mitigación: se
  mueve verbatim; no se renombra ninguna clase.
