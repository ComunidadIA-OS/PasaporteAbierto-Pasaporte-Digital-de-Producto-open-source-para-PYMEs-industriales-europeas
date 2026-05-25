// Shell interactivo del wizard (F4-01) — diseño Quiet.
//
// Carga inicial: el Server Component pasa `initialSession`.
// A partir de ahí mantiene estado local y persiste cada cambio de step
// con PATCH /api/v1/sessions/{id}. La URL no cambia entre pasos: una
// recarga reanuda el `current_step` exacto desde BD.
//
// El chat lateral (F3-04) ya no es una columna fija: se invoca con un
// FAB y se muestra en un drawer modal. La lógica del componente
// `ChatPanel` queda intacta (histórico + envío + scroll + citas). El
// chat sigue siendo un endpoint independiente del pipeline; jamás
// escribe en el estado del wizard.

"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState, useTransition } from "react";

import { api, type SessionState } from "@/app/lib/api";

import { Step1Description } from "./steps/Step1Description";
import { Step2Sector } from "./steps/Step2Sector";
import { Step3Bom } from "./steps/Step3Bom";
import { Step4Documents } from "./steps/Step4Documents";
import { Step5Extract } from "./steps/Step5Extract";
import { Step6Verify } from "./steps/Step6Verify";
import { Step7Publish } from "./steps/Step7Publish";

const STEPS = [
  { n: 1, label: "Descripción", kind: "det" as const },
  { n: 2, label: "Sector", kind: "ai" as const },
  { n: 3, label: "BOM", kind: "det" as const },
  { n: 4, label: "Documentos", kind: "det" as const },
  { n: 5, label: "Extracción", kind: "ai" as const },
  { n: 6, label: "Verificación", kind: "det" as const },
  { n: 7, label: "Publicar DPP", kind: "det" as const },
] as const;

const STEP_SUBTITLES: Record<number, string> = {
  1: "Texto libre sobre el producto. Alimenta la clasificación.",
  2: "El clasificador identifica el sector ESPR aplicable y cita el reglamento.",
  3: "Bill of Materials generado desde el plugin del sector. Cada campo cita su artículo.",
  4: "Sube los PDFs requeridos por el plugin y el BOM. SHA-256 evita duplicados.",
  5: "El recolector cruza BOM y PDFs. Cada campo se etiqueta como verified, self-declared o pending.",
  6: "Verificación determinista contra el schema. Bloquea publicación si falta un obligatorio.",
  7: "Firma Ed25519 + JSON-LD CIRPASS-2 + QR resoluble. Identificador ISO/IEC 15459 o GS1.",
};

export function WizardClient({ initialSession }: { initialSession: SessionState }) {
  const [session, setSession] = useState<SessionState>(initialSession);
  const [pending, startTransition] = useTransition();
  const [chatOpen, setChatOpen] = useState(false);

  function navigateTo(step: number) {
    if (step === session.current_step) return;
    if (step > session.current_step) return; // no se permite saltar hacia adelante
    startTransition(async () => {
      const updated = await api.updateProgress(session.session_id, { step });
      setSession(updated);
    });
  }

  return (
    <>
      <header className="appbar">
        <Link href="/" className="appbar-brand">
          <div className="appbar-logo">P</div>
          <span>PasaporteAbierto</span>
        </Link>
        <div className="appbar-spacer" />
        <span className="mono" style={{ fontSize: 11, color: "var(--text-faint)" }}>
          {session.session_id.slice(0, 8)} · auto-guardado
        </span>
      </header>

      <div className="wizard-shell">
        <main className="wizard-main">
          <HorizontalStepper
            current={session.current_step}
            onNavigate={navigateTo}
            disabled={pending}
          />
          <StepSlot session={session} onSessionChange={setSession} />
        </main>
      </div>

      <button
        type="button"
        className="floating-chat-btn"
        onClick={() => setChatOpen(true)}
        aria-label="Abrir chat normativo"
      >
        ?
      </button>

      {chatOpen && (
        <ChatDrawer sessionId={session.session_id} onClose={() => setChatOpen(false)} />
      )}
    </>
  );
}

function HorizontalStepper({
  current,
  onNavigate,
  disabled,
}: {
  current: number;
  onNavigate: (n: number) => void;
  disabled: boolean;
}) {
  const pct = Math.round(((current - 1) / 6) * 100);
  return (
    <div className="h-stepper" role="progressbar" aria-label="Progreso del wizard">
      <div className="h-stepper-progress">
        <div className="h-stepper-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="h-stepper-dots">
        {STEPS.map((s) => {
          const isCurrent = s.n === current;
          const isDone = s.n < current;
          const isReachable = s.n <= current;
          return (
            <button
              key={s.n}
              type="button"
              className={`h-stepper-dot${isCurrent ? " is-current" : ""}${isDone ? " is-done" : ""}`}
              disabled={!isReachable || disabled || isCurrent}
              onClick={() => onNavigate(s.n)}
              title={s.label}
              aria-current={isCurrent ? "step" : undefined}
            >
              <span className="dot-n">{s.n}</span>
              <span className="dot-l">{s.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function StepSlot({
  session,
  onSessionChange,
}: {
  session: SessionState;
  onSessionChange: (s: SessionState) => void;
}) {
  const meta = STEPS.find((s) => s.n === session.current_step);
  return (
    <section className="fade-up" key={session.current_step}>
      <header className="wm-head">
        <div className="label">
          PASO {String(session.current_step).padStart(2, "0")} ·{" "}
          {meta?.kind === "ai" ? "Componente IA" : "Determinista"}
        </div>
        <h1>{meta?.label}</h1>
        <p className="subtitle">{STEP_SUBTITLES[session.current_step]}</p>
        <p className="session-id">session_id: {session.session_id}</p>
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
    </section>
  );
}

// ============================================================
// Chat — drawer modal abierto desde el FAB
// ============================================================

let chatMsgId = 0;

interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  text: string;
  citation: { regulation: string; article: string; url: string | null } | null;
}

function ChatDrawer({ sessionId, onClose }: { sessionId: string; onClose: () => void }) {
  // Invariante: el chat NUNCA escribe en el estado del wizard. Sí persiste su
  // propio histórico en chat_messages (canal independiente, F3-04 criterio 3).
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Carga el histórico persistido al montar.
  useEffect(() => {
    let cancelled = false;
    api
      .chatHistory(sessionId)
      .then((res) => {
        if (cancelled) return;
        setMessages(
          res.messages.map((m) => ({
            id: ++chatMsgId,
            role: m.role,
            text: m.content,
            citation: m.citation,
          })),
        );
        setTimeout(() => scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight), 0);
      })
      .catch(() => {
        // Sin histórico → arranca vacío.
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  // Cerrar con Escape.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

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
        {
          id: ++chatMsgId,
          role: "assistant",
          text: "Error al consultar el chat.",
          citation: null,
        },
      ]);
    } finally {
      setSending(false);
      setTimeout(() => scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight), 50);
    }
  }, [input, sending, sessionId]);

  return (
    <>
      {/* biome-ignore lint/a11y/noStaticElementInteractions: overlay clic-fuera-cierra */}
      {/* biome-ignore lint/a11y/useKeyWithClickEvents: el Escape global ya cierra */}
      <div className="chat-overlay" onClick={onClose} aria-hidden />
      <aside
        className="chat-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Chat normativo"
      >
        <div className="chat-head">
          <div>
            <h3>Chat normativo</h3>
            <p>Pregunta sobre requisitos del DPP. Cada respuesta cita el Art.</p>
          </div>
          <button type="button" className="chat-close" onClick={onClose} aria-label="Cerrar chat">
            ✕
          </button>
        </div>

        <div ref={scrollRef} className="chat-body">
          {messages.length === 0 && (
            <p className="chat-empty">
              Escribe una pregunta sobre la normativa aplicable a tu producto. El chat es
              independiente del wizard: no escribe en tus datos.
            </p>
          )}
          {messages.map((msg) => (
            <div key={msg.id} className={`chat-msg ${msg.role}`}>
              <p style={{ whiteSpace: "pre-wrap", margin: 0 }}>{msg.text}</p>
              {msg.citation && (
                <span className="chat-cite">
                  {msg.citation.regulation}, {msg.citation.article}
                </span>
              )}
            </div>
          ))}
          {sending && <div className="chat-typing">Pensando…</div>}
        </div>

        <div className="chat-input">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
            placeholder="Pregunta sobre normativa…"
            disabled={sending}
          />
          <button type="button" onClick={send} disabled={sending || !input.trim()}>
            Enviar
          </button>
        </div>
      </aside>
    </>
  );
}
