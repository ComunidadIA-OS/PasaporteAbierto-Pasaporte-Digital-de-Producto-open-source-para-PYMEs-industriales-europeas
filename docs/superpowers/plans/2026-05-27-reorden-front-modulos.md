# Reorden del front a arquitectura modular Logixs — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganizar `frontend/` a la arquitectura modular Logixs (`src/app` solo rutas, `src/modules/<feature>`, `src/lib`, `src/core`) sin cambiar nada que el usuario vea.

**Architecture:** Refactor puramente estructural en 4 slices, cada uno deja la app funcionando y termina en un commit verificado. El fetch del wizard se preserva en cliente; `WizardPage`/`LandingPage` son Server Components finos. Sin shadcn/CVA. Sin Server Actions (se crea `actions/` vacío).

**Tech Stack:** Next 16.2.6 · React 19 · TypeScript · Tailwind v4 · pnpm 10.10 · Biome. Spec: `docs/superpowers/specs/2026-05-27-reorden-front-modulos-design.md`.

**Verificación (no hay tests de front):** el gate de cada slice es `pnpm lint && pnpm build` (Biome + `next build`, que falla ante cualquier import/type roto) y una comprobación visual de la ruta afectada. La app vive en `frontend/`; todos los comandos se ejecutan desde ahí.

---

## Task 0: Prerrequisito — dependencias en el host

El stack corre en Docker, pero `pnpm build`/`pnpm lint` necesitan `node_modules` en el host.

- [ ] **Step 1: Instalar dependencias en el host**

Run:
```bash
cd frontend && pnpm install
```
Expected: instala sin errores; aparece `frontend/node_modules`.

- [ ] **Step 2: Baseline verde antes de tocar nada**

Run:
```bash
cd frontend && pnpm lint && pnpm build
```
Expected: lint sin errores y `next build` termina con "Compiled successfully". Si falla aquí, PARAR: el baseline ya estaba roto y hay que resolverlo antes de refactorizar.

> No hay commit en esta task (no cambia el repo).

---

## Task 1: Esqueleto `src/` + alias

Mueve todo el front bajo `src/app/` y reapunta el alias. Gracias al alias, los imports `@/app/...` siguen resolviendo sin cambios.

**Files:**
- Move: `frontend/app/` → `frontend/src/app/` (todo el árbol)
- Modify: `frontend/tsconfig.json` (paths del alias)

- [ ] **Step 1: Mover `app/` a `src/app/`**

Run:
```bash
cd frontend && mkdir src && git mv app src/app
```
Expected: `git status` muestra los 17 archivos como renombrados a `src/app/...`.

- [ ] **Step 2: Reapuntar el alias en tsconfig.json**

En `frontend/tsconfig.json`, cambiar el bloque `paths`:

```json
    "paths": {
      "@/*": ["./src/*"]
    }
```
(antes era `["./*"]`).

- [ ] **Step 3: Verificar build (gate)**

Run:
```bash
cd frontend && pnpm lint && pnpm build
```
Expected: PASS. `@/app/lib/api` ahora resuelve a `./src/app/lib/api` (donde quedó el archivo), así que no debe romperse ningún import. Si algún import falla, es un `@/`-import que no empezaba por `app/`; corregirlo a la nueva ruta `./src/*`.

- [ ] **Step 4: Verificar render (visual)**

Run (en otra terminal, puerto distinto al de Docker):
```bash
cd frontend && pnpm dev -p 3001
```
Abrir `http://localhost:3001` (landing) y `http://localhost:3001/wizard`. Expected: idéntico a hoy. Parar con Ctrl-C.

- [ ] **Step 5: Commit**

```bash
git add frontend/tsconfig.json frontend/src
git commit -m "refactor(front): mueve app/ a src/app y reapunta alias @/* a ./src/*

Primer slice del reorden a arquitectura modular. Mover el árbol completo
bajo src/app y cambiar el alias de ./* a ./src/* deja todos los imports
@/app/... resolviendo igual, sin cambios de comportamiento ni de imports.

Ref: docs/superpowers/specs/2026-05-27-reorden-front-modulos-design.md"
```

---

## Task 2: Capa `lib/` + `core/` (split de `api.ts`)

Divide `src/app/lib/api.ts` en transporte (`lib/fetch.ts`), errores (`core/errors`), tipos (`core/responses`) y el cliente del wizard (`modules/wizard/lib/wizard-api.ts`). Mueve `demo-mode.ts` y `field-labels.ts` a su sitio.

**Files:**
- Create: `frontend/src/core/responses/index.ts`
- Create: `frontend/src/core/errors/index.ts`
- Create: `frontend/src/lib/fetch.ts`
- Create: `frontend/src/modules/wizard/lib/wizard-api.ts`
- Move: `src/app/lib/demo-mode.ts` → `src/lib/demo-mode.ts`
- Move: `src/app/lib/field-labels.ts` → `src/modules/wizard/lib/field-labels.ts`
- Delete: `src/app/lib/api.ts` (tras dividirlo) y la carpeta `src/app/lib/`
- Modify: imports en los archivos que consumían `@/app/lib/*`

- [ ] **Step 1: Crear `core/responses/index.ts` con los tipos**

Mover **verbatim** todo el bloque de tipos de `src/app/lib/api.ts` (desde `export type Provenance` en la línea ~11 hasta `DemoSeedDocumentsResponse` en la ~263) a este archivo nuevo. Son solo `export type`/`export interface`, sin lógica. No incluye `API_BASE`, `request`, `ApiError` ni el objeto `api`.

```ts
// Tipos espejo de backend/src/app/api/v1/schemas.py.
// Si cambia un schema, ambos lados se actualizan en el mismo PR.

export type Provenance = "verified" | "self_declared" | "required_pending";
// ... (resto del bloque de tipos, movido tal cual desde api.ts)
export interface DemoSeedDocumentsResponse {
  seeded: DemoSeededDoc[];
}
```

- [ ] **Step 2: Crear `core/errors/index.ts`**

```ts
// Manejo centralizado de errores de API.

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly body: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// Envuelve una promesa de fetch para devolver datos o un error tipado
// sin lanzar. Disponible para código nuevo; los call-sites actuales siguen
// usando try/catch sobre el objeto `api` (comportamiento sin cambios).
export async function getDataOrError<T>(
  promise: Promise<T>,
): Promise<{ data: T; error: null } | { data: null; error: ApiError | Error }> {
  try {
    return { data: await promise, error: null };
  } catch (err) {
    return { data: null, error: err instanceof Error ? err : new Error(String(err)) };
  }
}
```

- [ ] **Step 3: Crear `lib/fetch.ts` (transporte)**

```ts
import { ApiError } from "@/core/errors";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const API_V1 = `${API_BASE}/api/v1`;

// Transporte único sobre fetch. Mismo comportamiento que el `request` previo:
// JSON por defecto, cache no-store, lanza ApiError si !ok.
export async function serverFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_V1}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(`${init?.method ?? "GET"} ${path} → ${res.status}`, res.status, body);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// Hook para llamadas ad-hoc desde Client Components que no pasen por el
// objeto `api`. Mismo transporte; existe para cumplir la convención (nunca
// fetch() nativo en cliente). Estable entre renders.
export function useClientFetch() {
  return serverFetch;
}
```

- [ ] **Step 4: Crear `modules/wizard/lib/wizard-api.ts` (cliente del wizard)**

Mover el objeto `api` y el helper `sid` (líneas ~297-413 de `api.ts`). Cambia: el cuerpo de `request` pasa a `serverFetch` importado; `ApiError` viene de `core/errors`. Re-exporta tipos y error para que los call-sites solo cambien la ruta del import.

```ts
import { ApiError } from "@/core/errors";
import { API_V1, serverFetch } from "@/lib/fetch";
import type {
  BomRequest, BomResponse, ChatRequest, ChatResponse, ChatHistoryResponse,
  ClassifyOverrideRequest, ClassifyResponse, CreateSessionRequest,
  CreateSessionResponse, DemoSampleResponse, DemoSeedDocumentsResponse,
  DocumentExcerptResponse, DocumentsListResponse, DppResponse, PluginDetail,
  PluginsListResponse, SessionState, UpdateProgressRequest,
  UploadDocumentResponse, VerifyResponse,
} from "@/core/responses";

// Re-export para ergonomía: los consumidores importan tipos y `api` del
// mismo módulo, igual que antes (solo cambia la ruta).
export * from "@/core/responses";
export { ApiError } from "@/core/errors";

const sid = (sessionId: string): string => encodeURIComponent(sessionId);

export const api = {
  createSession(body: CreateSessionRequest): Promise<CreateSessionResponse> {
    return serverFetch("/sessions", { method: "POST", body: JSON.stringify(body) });
  },
  getSession(sessionId: string): Promise<SessionState> {
    return serverFetch(`/sessions/${sid(sessionId)}`);
  },
  updateProgress(sessionId: string, body: UpdateProgressRequest): Promise<SessionState> {
    return serverFetch(`/sessions/${sid(sessionId)}`, { method: "PATCH", body: JSON.stringify(body) });
  },
  classify(sessionId: string): Promise<ClassifyResponse> {
    return serverFetch(`/sessions/${sid(sessionId)}/classify`, { method: "POST" });
  },
  overrideClassification(sessionId: string, body: ClassifyOverrideRequest): Promise<SessionState> {
    return serverFetch(`/sessions/${sid(sessionId)}/classify/override`, { method: "POST", body: JSON.stringify(body) });
  },
  listPlugins(): Promise<PluginsListResponse> {
    return serverFetch("/plugins");
  },
  getPluginDetail(name: string): Promise<PluginDetail> {
    return serverFetch(`/plugins/${encodeURIComponent(name)}`);
  },
  putBom(sessionId: string, body: BomRequest): Promise<BomResponse> {
    return serverFetch(`/sessions/${sid(sessionId)}/bom`, { method: "PUT", body: JSON.stringify(body) });
  },
  listDocuments(sessionId: string): Promise<DocumentsListResponse> {
    return serverFetch(`/sessions/${sid(sessionId)}/documents`);
  },
  documentExcerpt(sessionId: string, docId: number, fieldId: string): Promise<DocumentExcerptResponse> {
    const qs = `?field_id=${encodeURIComponent(fieldId)}`;
    return serverFetch(`/sessions/${sid(sessionId)}/documents/${docId}/excerpt${qs}`);
  },
  async uploadDocument(sessionId: string, file: File, docType: string): Promise<UploadDocumentResponse> {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(
      `${API_V1}/sessions/${sid(sessionId)}/documents?doc_type=${encodeURIComponent(docType)}`,
      { method: "POST", body: form },
    );
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError((body as Record<string, string>).detail ?? res.statusText, res.status, body);
    }
    return (await res.json()) as UploadDocumentResponse;
  },
  verify(sessionId: string): Promise<VerifyResponse> {
    return serverFetch(`/sessions/${sid(sessionId)}/verify`);
  },
  generateDpp(sessionId: string): Promise<DppResponse> {
    return serverFetch(`/sessions/${sid(sessionId)}/dpp`, { method: "POST" });
  },
  chat(body: ChatRequest): Promise<ChatResponse> {
    return serverFetch("/chat", { method: "POST", body: JSON.stringify(body) });
  },
  chatHistory(sessionId: string): Promise<ChatHistoryResponse> {
    return serverFetch(`/sessions/${sid(sessionId)}/chat`);
  },
  extractStreamUrl(sessionId: string): string {
    return `${API_V1}/sessions/${sid(sessionId)}/extract`;
  },
  getDemoSample(sector: string): Promise<DemoSampleResponse> {
    return serverFetch(`/demo/sample/${encodeURIComponent(sector)}`);
  },
  seedDemoDocuments(sessionId: string): Promise<DemoSeedDocumentsResponse> {
    return serverFetch(`/demo/sessions/${sid(sessionId)}/seed-documents`, { method: "POST" });
  },
};
```

- [ ] **Step 5: Mover demo-mode y field-labels**

Run:
```bash
cd frontend
git mv src/app/lib/demo-mode.ts src/lib/demo-mode.ts
mkdir -p src/modules/wizard/lib
git mv src/app/lib/field-labels.ts src/modules/wizard/lib/field-labels.ts
```
Si `field-labels.ts` importa tipos con `from "./api"`, cambiarlo a `from "@/core/responses"`.

- [ ] **Step 6: Borrar el api.ts viejo**

Run:
```bash
cd frontend && git rm src/app/lib/api.ts
```
(La carpeta `src/app/lib/` queda vacía y desaparece.)

- [ ] **Step 7: Actualizar imports en los consumidores**

Reemplazos de ruta (el resto de la línea no cambia, gracias a los re-exports):
- `@/app/lib/api` → `@/modules/wizard/lib/wizard-api` (10 sitios)
- `@/app/lib/demo-mode` → `@/lib/demo-mode` (3 sitios)
- `@/app/lib/field-labels` → `@/modules/wizard/lib/field-labels` (3 sitios)

Run para localizarlos:
```bash
cd frontend && grep -rl "@/app/lib/" src
```

- [ ] **Step 8: Verificar build (gate)**

Run:
```bash
cd frontend && pnpm lint && pnpm build
```
Expected: PASS. Cualquier import olvidado a `@/app/lib/*` lo señala el build.

- [ ] **Step 9: Verificar render (visual)**

`pnpm dev -p 3001` y recorrer landing + entrada del wizard. Expected: idéntico.

- [ ] **Step 10: Commit**

```bash
git add frontend/src frontend/tsconfig.json
git commit -m "refactor(front): extrae transporte, errores y tipos de api.ts a lib/ y core/

Divide app/lib/api.ts en src/lib/fetch.ts (serverFetch/useClientFetch),
src/core/errors (ApiError, getDataOrError), src/core/responses (tipos espejo
de schemas backend) y src/modules/wizard/lib/wizard-api.ts (objeto api).
demo-mode a src/lib; field-labels al módulo wizard. Mismo comportamiento:
mismo transporte y mismas funciones; wizard-api re-exporta tipos para que los
consumidores solo cambien la ruta del import.

Ref: docs/superpowers/specs/2026-05-27-reorden-front-modulos-design.md"
```

---

## Task 3: Módulo `landing`

`app/page.tsx` pasa a ser una ruta fina que renderiza `LandingPage` (Server) → `LandingContent` (Client). `Reveal` entra al módulo.

**Files:**
- Create: `frontend/src/modules/landing/pages/LandingPage.tsx`
- Create: `frontend/src/modules/landing/components/LandingContent.tsx`
- Move: `src/app/components/Reveal.tsx` → `src/modules/landing/components/Reveal.tsx`
- Modify: `frontend/src/app/page.tsx` (queda fino)

- [ ] **Step 1: Mover Reveal al módulo**

Run:
```bash
cd frontend
mkdir -p src/modules/landing/components src/modules/landing/pages
git mv src/app/components/Reveal.tsx src/modules/landing/components/Reveal.tsx
```

- [ ] **Step 2: Crear `LandingContent.tsx` (Client) con el contenido actual de la página**

Mover **verbatim** el cuerpo JSX y la lógica de cliente del actual `src/app/page.tsx` a este componente. Mantener `"use client"` arriba (la landing usa `Reveal`, que es client). Named export.

```tsx
"use client";

import { Reveal } from "@/modules/landing/components/Reveal";
// ... resto de imports que ya tenía page.tsx (sin cambios salvo la ruta de Reveal)

export function LandingContent() {
  // ... cuerpo idéntico al return actual de page.tsx
}
```

- [ ] **Step 3: Crear `LandingPage.tsx` (Server)**

```tsx
import { LandingContent } from "@/modules/landing/components/LandingContent";

export function LandingPage() {
  return <LandingContent />;
}
```

- [ ] **Step 4: Reducir `src/app/page.tsx` a ruta fina**

```tsx
import { LandingPage } from "@/modules/landing/pages/LandingPage";

export default function Page() {
  return <LandingPage />;
}
```

- [ ] **Step 5: Verificar build (gate)**

Run:
```bash
cd frontend && pnpm lint && pnpm build
```
Expected: PASS.

- [ ] **Step 6: Verificar render (visual)**

`pnpm dev -p 3001`, abrir `http://localhost:3001`. Expected: landing pixel a pixel idéntica (animaciones `Reveal` incluidas).

- [ ] **Step 7: Commit**

```bash
git add frontend/src
git commit -m "refactor(front): extrae la landing al módulo modules/landing

app/page.tsx queda como ruta fina que renderiza LandingPage (Server) →
LandingContent (Client); Reveal pasa al módulo. Sin cambios visuales: el JSX
y la lógica se mueven verbatim.

Ref: docs/superpowers/specs/2026-05-27-reorden-front-modulos-design.md"
```

---

## Task 4: Módulo `wizard`

Lleva el wizard a su módulo: `WizardContent` (ex `wizard-client`), los 7 pasos, la entrada, y `WizardPage` (Server fino). Crea `actions/` vacío.

**Files:**
- Create: `frontend/src/modules/wizard/pages/WizardPage.tsx`
- Create: `frontend/src/modules/wizard/components/WizardEntry.tsx`
- Create: `frontend/src/modules/wizard/actions/.gitkeep` (+ README)
- Move: `src/app/wizard/[sessionId]/wizard-client.tsx` → `src/modules/wizard/components/WizardContent.tsx`
- Move: `src/app/wizard/[sessionId]/steps/Step*.tsx` → `src/modules/wizard/components/Step*.tsx`
- Modify: `src/app/wizard/[sessionId]/page.tsx` y `src/app/wizard/page.tsx` (rutas finas)

- [ ] **Step 1: Mover los componentes del wizard al módulo**

Run:
```bash
cd frontend
mkdir -p src/modules/wizard/components src/modules/wizard/pages src/modules/wizard/actions
git mv "src/app/wizard/[sessionId]/wizard-client.tsx" src/modules/wizard/components/WizardContent.tsx
git mv "src/app/wizard/[sessionId]/steps/"*.tsx src/modules/wizard/components/
```

- [ ] **Step 2: Renombrar el símbolo a `WizardContent`**

En `WizardContent.tsx`, renombrar el componente exportado (antes era el de `wizard-client`, p. ej. `WizardClient`) a `WizardContent` (named export). Actualizar dentro del archivo los imports de los pasos: `from "./steps/StepN..."` → `from "@/modules/wizard/components/StepN..."`. Mantener `"use client"`.

- [ ] **Step 3: Crear `WizardPage.tsx` (Server fino)**

Preserva el comportamiento: el fetch del estado sigue en cliente dentro de `WizardContent`. `WizardPage` solo pasa el `sessionId`.

```tsx
import { WizardContent } from "@/modules/wizard/components/WizardContent";

export function WizardPage({ sessionId }: { sessionId: string }) {
  return <WizardContent sessionId={sessionId} />;
}
```
(Si `WizardContent` recibía el `sessionId` con otro nombre de prop, respetar el actual.)

- [ ] **Step 4: Adelgazar la ruta `[sessionId]/page.tsx`**

```tsx
import { WizardPage } from "@/modules/wizard/pages/WizardPage";

export default async function Page({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <WizardPage sessionId={sessionId} />;
}
```
(Respetar la firma de `params` que ya use el archivo actual: en Next 16 suele ser `Promise`. Verificar contra el original antes de cambiar.)

- [ ] **Step 5: Extraer la entrada del wizard a `WizardEntry.tsx`**

Mover el cuerpo de `src/app/wizard/page.tsx` (Client, crea sesión) a `src/modules/wizard/components/WizardEntry.tsx` (named export, `"use client"`). Dejar la ruta fina:

```tsx
// src/app/wizard/page.tsx
import { WizardEntry } from "@/modules/wizard/components/WizardEntry";

export default function Page() {
  return <WizardEntry />;
}
```

- [ ] **Step 6: Crear `actions/` vacío con README**

`src/modules/wizard/actions/README.md`:
```markdown
# Server Actions del wizard

Vacío a propósito. Las mutaciones del wizard van hoy en cliente
(`useClientFetch` / objeto `api`) porque `extract` es SSE y no puede ser
Server Action. Poblar solo si se adoptan Server Actions como cambio
deliberado y aparte. Ver el spec del reorden.
```

- [ ] **Step 7: Verificar build (gate)**

Run:
```bash
cd frontend && pnpm lint && pnpm build
```
Expected: PASS.

- [ ] **Step 8: Verificar render + flujo completo (visual)**

`pnpm dev -p 3001`. Con el backend arriba (`make up`), recorrer el wizard de punta a punta: crear sesión → clasificar → BOM → documentos → **extracción (SSE, comprobar progreso en vivo)** → verificar → generar DPP. Expected: comportamiento idéntico en los 7 pasos.

- [ ] **Step 9: Commit**

```bash
git add frontend/src
git commit -m "refactor(front): extrae el wizard al módulo modules/wizard

wizard-client → WizardContent, los 7 pasos a components/, entrada a
WizardEntry, y [sessionId]/page como ruta fina sobre WizardPage (Server).
Se crea actions/ vacío (mutaciones siguen en cliente; extract es SSE). Sin
cambios de comportamiento: el fetch del estado y el SSE siguen en cliente.

Ref: docs/superpowers/specs/2026-05-27-reorden-front-modulos-design.md"
```

---

## Cierre

- [ ] **Step 1: Rebuild del contenedor frontend con la nueva estructura**

Run:
```bash
docker compose up -d --build frontend
```
Expected: build OK; `http://localhost:3000` sirve la app reordenada.

- [ ] **Step 2: PR a develop**

Abrir PR de `front-reorg-modules` contra `develop` (no a main). El cuerpo del PR resume los 4 slices y enlaza spec + plan.

---

## Self-review (cobertura del spec)

- Estructura objetivo (spec §"Estructura objetivo") → Tasks 1-4 la construyen entera.
- Mapeo archivo-por-archivo (spec) → cubierto: layout/globals (T1), api.ts split + demo-mode + field-labels (T2), page+Reveal (T3), wizard-client+steps+pages+entry (T4).
- Data-flow: fetch cliente preservado (T2/T4 no mueven a SSR), `actions/` vacío (T4 Step 6), `serverFetch`/`useClientFetch` (T2 Step 3), `getDataOrError` (T2 Step 2).
- Restricciones: cero UI/UX (verificación visual en cada slice), sin shadcn (no se añade ninguna dep), commit por slice (cada Task termina en commit), default export solo en rutas (T3 Step 4, T4 Steps 4-5).
- Fuera de alcance (shadcn, Server Actions, SSR, DPP público) → respetado; ninguna task los toca.
