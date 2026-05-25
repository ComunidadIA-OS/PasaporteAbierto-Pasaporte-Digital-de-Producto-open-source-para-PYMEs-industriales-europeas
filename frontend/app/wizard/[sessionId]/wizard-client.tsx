// Shell interactivo del wizard (F4-01).
//
// Carga inicial: el Server Component pasa `initialSession`.
// A partir de ahí mantiene estado local y persiste cada cambio de step
// con PATCH /api/v1/sessions/{id}. La URL no cambia entre pasos: una
// recarga reanuda el `current_step` exacto desde BD.
//
// El chat lateral (F3-04) vive aquí dentro del componente cliente, por
// lo que **no se desmonta al cambiar de paso** (cumple criterio 3 de F4-01).

"use client";

import { useState, useTransition } from "react";

import { api, type SessionState } from "@/app/lib/api";

import { Step1Description } from "./steps/Step1Description";
import { Step2Sector } from "./steps/Step2Sector";
import { Step3Bom } from "./steps/Step3Bom";
import { Step6Verify } from "./steps/Step6Verify";
import { Step7Publish } from "./steps/Step7Publish";

const STEPS = [
  { n: 1, label: "Descripción" },
  { n: 2, label: "Sector" },
  { n: 3, label: "BOM" },
  { n: 4, label: "Documentos" },
  { n: 5, label: "Extracción" },
  { n: 6, label: "Verificación" },
  { n: 7, label: "Publicar DPP" },
] as const;

export function WizardClient({ initialSession }: { initialSession: SessionState }) {
  const [session, setSession] = useState<SessionState>(initialSession);
  const [pending, startTransition] = useTransition();

  function navigateTo(step: number) {
    if (step === session.current_step) return;
    if (step > session.current_step) return; // no se permite saltar hacia adelante
    startTransition(async () => {
      const updated = await api.updateProgress(session.session_id, { step });
      setSession(updated);
    });
  }

  return (
    <div className="grid min-h-screen grid-cols-[240px_1fr_360px]">
      <SidebarSteps
        current={session.current_step}
        onNavigate={navigateTo}
        disabled={pending}
      />
      <StepSlot session={session} onSessionChange={setSession} />
      <ChatPanel />
    </div>
  );
}

function SidebarSteps({
  current,
  onNavigate,
  disabled,
}: {
  current: number;
  onNavigate: (step: number) => void;
  disabled: boolean;
}) {
  const progressPct = Math.round(((current - 1) / 6) * 100);

  return (
    <aside className="border-r border-gray-200 bg-gray-50 p-6">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500">
        Wizard
      </h2>

      <div className="mt-3" aria-label="Progreso del wizard">
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-200">
          <div
            className="h-full bg-blue-600 transition-all"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <p className="mt-1 text-xs text-gray-500">
          Paso {current} de 7 · {progressPct}%
        </p>
      </div>

      <ol className="mt-4 space-y-1">
        {STEPS.map((step) => {
          const isCurrent = step.n === current;
          const isDone = step.n < current;
          const isReachable = step.n <= current;

          const base = "flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm";
          const variant = isCurrent
            ? "bg-blue-100 font-semibold text-blue-900"
            : isDone
              ? "text-gray-500 hover:bg-gray-100"
              : "text-gray-400 cursor-not-allowed";

          return (
            <li key={step.n}>
              <button
                type="button"
                disabled={!isReachable || disabled || isCurrent}
                onClick={() => onNavigate(step.n)}
                className={`${base} ${variant}`}
                aria-current={isCurrent ? "step" : undefined}
              >
                <span
                  className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-xs ${
                    isCurrent
                      ? "bg-blue-600 text-white"
                      : isDone
                        ? "bg-green-500 text-white"
                        : "border border-gray-300 text-gray-400"
                  }`}
                  aria-hidden
                >
                  {isDone ? "✓" : step.n}
                </span>
                <span>{step.label}</span>
              </button>
            </li>
          );
        })}
      </ol>
    </aside>
  );
}

function StepSlot({
  session,
  onSessionChange,
}: {
  session: SessionState;
  onSessionChange: (s: SessionState) => void;
}) {
  const stepMeta = STEPS.find((s) => s.n === session.current_step);
  return (
    <section className="p-10">
      <header className="mb-6">
        <p className="font-mono text-xs text-gray-500">session_id: {session.session_id}</p>
        <h1 className="mt-1 text-2xl font-bold">
          Paso {session.current_step} — {stepMeta?.label}
        </h1>
      </header>

      {session.current_step === 1 && (
        <Step1Description session={session} onSessionChange={onSessionChange} />
      )}

      {session.current_step === 2 && (
        <Step2Sector session={session} onSessionChange={onSessionChange} />
      )}

      {session.current_step === 3 && (
        <Step3Bom session={session} onSessionChange={onSessionChange} />
      )}

      {(session.current_step === 4 || session.current_step === 5) && (
        <div className="rounded-lg border-2 border-dashed border-gray-300 bg-white p-8">
          <p className="text-sm text-gray-600">
            Paso {session.current_step} pendiente — los implementa Persona B.
          </p>
          <ul className="mt-4 list-disc pl-6 text-sm text-gray-500">
            <li>Paso 4 documentos → F4-04</li>
            <li>Paso 5 SSE extracción → F4-05 (Recolector F3-02)</li>
          </ul>
        </div>
      )}

      {session.current_step === 6 && (
        <Step6Verify session={session} onSessionChange={onSessionChange} />
      )}

      {session.current_step === 7 && <Step7Publish session={session} />}
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
          Toda respuesta debe incluir cita normativa concreta. Si el RAG no devuelve
          fragmentos relevantes, responder con la negativa estándar.
        </span>
      </div>
    </aside>
  );
}
