// Shell estructural del wizard (PR-0).
//
// Esto es solo el ANDAMIO: layout de 3 zonas (sidebar + paso actual + chat
// lateral) consumiendo GET /sessions/{id}. F4-01 (Persona A) sustituye este
// archivo por uno con persistencia real, navegación por URL entre pasos,
// formularios por paso y panel de chat funcional.
//
// Cómo probarlo:
//   1) docker compose up
//   2) curl -X POST http://localhost:8000/api/v1/sessions \
//        -H 'Content-Type: application/json' \
//        -d '{"description":"Batería industrial recargable de Li-ion 5kWh"}'
//   3) abre http://localhost:3000/wizard/<session_id>

import { ApiError, api, type SessionState } from "@/app/lib/api";

const STEPS = [
  { n: 1, label: "Descripción" },
  { n: 2, label: "Sector" },
  { n: 3, label: "BOM" },
  { n: 4, label: "Documentos" },
  { n: 5, label: "Extracción" },
  { n: 6, label: "Verificación" },
  { n: 7, label: "Publicar DPP" },
] as const;

async function loadSession(sessionId: string): Promise<SessionState | null> {
  try {
    return await api.getSession(sessionId);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

export default async function WizardPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await params;
  const session = await loadSession(sessionId);

  if (!session) {
    return (
      <main className="min-h-screen p-12">
        <h1 className="text-2xl font-bold">Sesión no encontrada</h1>
        <p className="mt-2 text-sm text-gray-600">
          La sesión <code className="font-mono">{sessionId}</code> no existe.
        </p>
      </main>
    );
  }

  return (
    <div className="grid min-h-screen grid-cols-[240px_1fr_360px]">
      <SidebarSteps current={session.current_step} />
      <StepSlot session={session} />
      <ChatPanel />
    </div>
  );
}

function SidebarSteps({ current }: { current: number }) {
  return (
    <aside className="border-r border-gray-200 bg-gray-50 p-6">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500">
        Wizard
      </h2>
      <ol className="mt-4 space-y-1">
        {STEPS.map((step) => {
          const isCurrent = step.n === current;
          const isDone = step.n < current;
          return (
            <li
              key={step.n}
              className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm ${
                isCurrent
                  ? "bg-blue-100 font-semibold text-blue-900"
                  : isDone
                    ? "text-gray-500"
                    : "text-gray-700"
              }`}
            >
              <span
                className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-xs ${
                  isCurrent
                    ? "bg-blue-600 text-white"
                    : isDone
                      ? "bg-gray-300 text-gray-700"
                      : "border border-gray-300 text-gray-500"
                }`}
              >
                {step.n}
              </span>
              <span>{step.label}</span>
            </li>
          );
        })}
      </ol>
    </aside>
  );
}

function StepSlot({ session }: { session: SessionState }) {
  return (
    <section className="p-10">
      <header className="mb-6">
        <p className="text-xs font-mono text-gray-500">session_id: {session.session_id}</p>
        <h1 className="mt-1 text-2xl font-bold">
          Paso {session.current_step} —{" "}
          {STEPS.find((s) => s.n === session.current_step)?.label}
        </h1>
      </header>

      <div className="rounded-lg border-2 border-dashed border-gray-300 bg-white p-8">
        <p className="text-sm text-gray-600">
          Slot del paso {session.current_step}. Cada paso del wizard se monta aquí.
        </p>
        <ul className="mt-4 list-disc pl-6 text-sm text-gray-500">
          <li>Pasos 1, 2, 3, 6, 7 → Persona A (F4-01, F4-02, F4-03, F4-06)</li>
          <li>Pasos 4, 5 → Persona B (F4-04, F4-05)</li>
        </ul>
      </div>

      {session.sector && (
        <p className="mt-6 text-sm text-gray-600">
          Sector clasificado:{" "}
          <span className="font-mono">{session.sector}</span> · confianza{" "}
          <span className="font-mono">{session.classification_confidence ?? "—"}</span>
        </p>
      )}
    </section>
  );
}

function ChatPanel() {
  // Slot del chat lateral. Persona B lo implementa en F3-04 (frontend).
  // Invariante: el chat NUNCA escribe en el estado del wizard.
  return (
    <aside className="flex flex-col border-l border-gray-200 bg-white p-6">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500">
        Chat normativo
      </h2>
      <div className="mt-4 flex-1 rounded-lg border-2 border-dashed border-gray-300 p-4 text-xs text-gray-500">
        Panel pendiente · F3-04
        <br />
        <span className="mt-2 block">
          Toda respuesta debe incluir cita normativa concreta. Si el RAG no
          devuelve fragmentos, responder con la negativa estándar.
        </span>
      </div>
    </aside>
  );
}
