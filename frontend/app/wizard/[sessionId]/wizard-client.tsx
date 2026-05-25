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

import { useCallback, useRef, useState, useTransition } from "react";

import { api, type SessionState } from "@/app/lib/api";

import { Step1Description } from "./steps/Step1Description";
import { Step2Sector } from "./steps/Step2Sector";
import { Step3Bom } from "./steps/Step3Bom";
import { Step4Documents } from "./steps/Step4Documents";
import { Step5Extract } from "./steps/Step5Extract";
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
    <div className="grid min-h-screen grid-cols-[280px_1fr_380px] bg-slate-100">
      <SidebarSteps current={session.current_step} onNavigate={navigateTo} disabled={pending} />
      <StepSlot session={session} onSessionChange={setSession} />
      <ChatPanel sessionId={session.session_id} />
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
    <aside className="flex flex-col bg-slate-900 p-6 text-white">
      {/* Brand */}
      <div className="mb-8">
        <h2 className="text-xl font-bold tracking-tight">
          <span className="text-teal-400">Pasaporte</span>Abierto
        </h2>
        <p className="mt-1 text-xs text-slate-400">Pasaporte Digital de Producto</p>
      </div>

      {/* Progress bar */}
      <div role="progressbar" aria-label="Progreso del wizard">
        <div className="h-2 w-full overflow-hidden rounded-full bg-slate-700">
          <div
            className="h-full rounded-full bg-gradient-to-r from-teal-500 to-teal-400 shadow-[0_0_8px_rgba(20,184,166,0.5)] transition-all duration-500 ease-out"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <p className="mt-2 text-xs text-slate-400">
          Paso {current} de 7 &middot; {progressPct}%
        </p>
      </div>

      {/* Steps */}
      <ol className="mt-6 space-y-1">
        {STEPS.map((step) => {
          const isCurrent = step.n === current;
          const isDone = step.n < current;
          const isReachable = step.n <= current;

          const base =
            "flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition-all duration-200";
          const variant = isCurrent
            ? "bg-teal-600/20 font-semibold text-teal-300 shadow-[0_0_12px_rgba(13,148,136,0.15)]"
            : isDone
              ? "text-slate-300 hover:bg-slate-800"
              : "text-slate-500 cursor-not-allowed";

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
                  className={`inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold transition-all duration-300 ${
                    isCurrent
                      ? "bg-teal-500 text-white shadow-[0_0_10px_rgba(20,184,166,0.4)]"
                      : isDone
                        ? "bg-teal-500 text-white scale-100"
                        : "border border-slate-600 text-slate-500"
                  }`}
                  aria-hidden
                >
                  {isDone ? (
                    <svg
                      aria-hidden="true"
                      className="h-3.5 w-3.5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={3}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    step.n
                  )}
                </span>
                <span>{step.label}</span>
              </button>
            </li>
          );
        })}
      </ol>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Footer */}
      <div className="border-t border-slate-700 pt-4">
        <p className="text-[10px] text-slate-500">Reg. UE 2024/1781 (ESPR)</p>
      </div>
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
    <section className="flex flex-col p-8">
      <header className="mb-6">
        <p className="font-mono text-xs text-slate-400">session_id: {session.session_id}</p>
        <h1 className="mt-1 text-2xl font-bold text-slate-800">
          Paso {session.current_step} &mdash; {stepMeta?.label}
        </h1>
        <div className="mt-2 h-1 w-24 rounded-full bg-gradient-to-r from-teal-500 to-teal-300" />
      </header>

      <div className="animate-fade-in flex-1 rounded-xl bg-white p-8 shadow-lg">
        {session.current_step === 1 && (
          <Step1Description session={session} onSessionChange={onSessionChange} />
        )}

        {session.current_step === 2 && (
          <Step2Sector session={session} onSessionChange={onSessionChange} />
        )}

        {session.current_step === 3 && (
          <Step3Bom session={session} onSessionChange={onSessionChange} />
        )}

        {session.current_step === 4 && (
          <Step4Documents session={session} onSessionChange={onSessionChange} />
        )}

        {session.current_step === 5 && (
          <Step5Extract session={session} onSessionChange={onSessionChange} />
        )}

        {session.current_step === 6 && (
          <Step6Verify session={session} onSessionChange={onSessionChange} />
        )}

        {session.current_step === 7 && <Step7Publish session={session} />}
      </div>
    </section>
  );
}

let chatMsgId = 0;

interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  text: string;
  citation: { regulation: string; article: string; url: string | null } | null;
}

function ChatPanel({ sessionId }: { sessionId: string }) {
  // Invariante: el chat NUNCA escribe en el estado del wizard.
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const send = useCallback(async () => {
    const text = input.trim();
    if (!text || sending) return;

    setMessages((prev) => [...prev, { id: ++chatMsgId, role: "user", text, citation: null }]);
    setInput("");
    setSending(true);

    try {
      const res = await api.chat({ session_id: sessionId, message: text });
      setMessages((prev) => [
        ...prev,
        { id: ++chatMsgId, role: "assistant", text: res.answer, citation: res.citation },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: ++chatMsgId, role: "assistant", text: "Error al consultar el chat.", citation: null },
      ]);
    } finally {
      setSending(false);
      setTimeout(() => scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight), 50);
    }
  }, [input, sending, sessionId]);

  return (
    <aside className="flex flex-col border-l border-slate-200 bg-white">
      {/* Header */}
      <div className="bg-gradient-to-r from-teal-600 to-teal-500 px-6 py-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-white">
          Chat normativo
        </h2>
        <p className="mt-1 text-xs text-teal-100">Pregunta sobre requisitos normativos del DPP.</p>
      </div>

      {/* Mensajes */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="mt-12 text-center">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-teal-50">
              <svg
                aria-hidden="true"
                className="h-6 w-6 text-teal-500"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z"
                />
              </svg>
            </div>
            <p className="text-xs text-slate-400">
              Escribe una pregunta sobre la normativa aplicable a tu producto.
            </p>
          </div>
        )}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm transition-all ${
              msg.role === "user"
                ? "ml-auto bg-teal-500 text-white"
                : "mr-auto bg-slate-100 text-slate-800"
            }`}
          >
            <p className="whitespace-pre-wrap">{msg.text}</p>
            {msg.citation && (
              <span
                className={`mt-1.5 inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  msg.role === "user" ? "bg-teal-400/30 text-teal-50" : "bg-teal-100 text-teal-700"
                }`}
              >
                {msg.citation.regulation}, {msg.citation.article}
              </span>
            )}
          </div>
        ))}
        {sending && (
          <div className="mr-auto max-w-[85%] rounded-2xl bg-slate-100 px-4 py-2.5 text-sm text-slate-400">
            <span className="inline-flex items-center gap-1">
              <span className="animate-pulse">Pensando</span>
              <span className="animate-bounce" style={{ animationDelay: "0ms" }}>
                &middot;
              </span>
              <span className="animate-bounce" style={{ animationDelay: "150ms" }}>
                &middot;
              </span>
              <span className="animate-bounce" style={{ animationDelay: "300ms" }}>
                &middot;
              </span>
            </span>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-slate-100 bg-slate-50/50 p-4">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
            placeholder="Pregunta sobre normativa..."
            disabled={sending}
            className="flex-1 rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm shadow-sm transition-colors focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500/20 disabled:opacity-50"
          />
          <button
            type="button"
            onClick={send}
            disabled={sending || !input.trim()}
            className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-teal-500 text-white shadow-md transition-all hover:bg-teal-600 hover:shadow-lg disabled:bg-slate-200 disabled:text-slate-400 disabled:shadow-none"
          >
            <svg
              aria-hidden="true"
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"
              />
            </svg>
          </button>
        </div>
      </div>
    </aside>
  );
}
