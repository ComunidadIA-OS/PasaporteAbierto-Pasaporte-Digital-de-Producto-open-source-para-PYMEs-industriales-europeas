// Shell interactivo del wizard (F4-01) — diseño Compliance OS.
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

import { Step1Description } from "@/modules/wizard/components/Step1Description";
import { Step2Sector } from "@/modules/wizard/components/Step2Sector";
import { Step3Bom } from "@/modules/wizard/components/Step3Bom";
import { Step4Documents } from "@/modules/wizard/components/Step4Documents";
import { Step5Extract } from "@/modules/wizard/components/Step5Extract";
import { Step6Verify } from "@/modules/wizard/components/Step6Verify";
import { Step7Publish } from "@/modules/wizard/components/Step7Publish";
import { api, type SessionState } from "@/modules/wizard/lib/wizard-api";

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

export function WizardContent({ initialSession }: { initialSession: SessionState }) {
  const [session, setSession] = useState<SessionState>(initialSession);
  const [pending, startTransition] = useTransition();
  const [chatOpen, setChatOpen] = useState(false);
  const fabRef = useRef<HTMLButtonElement>(null);

  function handleChatClose() {
    setChatOpen(false);
    // Restaura el foco al FAB tras desmontar el drawer
    requestAnimationFrame(() => fabRef.current?.focus());
  }

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
          <div className="appbar-logo">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M6 2h12a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z" />
              <circle cx="12" cy="10" r="3" />
              <path d="M7 17a5 5 0 0 1 10 0" />
            </svg>
          </div>
          <span>PasaporteAbierto</span>
        </Link>
        <div className="appbar-spacer" />
        <span className="mono" style={{ fontSize: 11, color: "var(--text-faint)" }}>
          {session.session_id.slice(0, 8)} · auto-guardado
        </span>
      </header>

      <div className="wizard-shell">
        <main id="main-content" className="wizard-main">
          <HorizontalStepper
            current={session.current_step}
            onNavigate={navigateTo}
            disabled={pending}
          />
          <StepSlot
            session={session}
            onSessionChange={setSession}
            onBack={() => navigateTo(session.current_step - 1)}
            backPending={pending}
          />
        </main>
      </div>

      <button
        ref={fabRef}
        type="button"
        className="floating-chat-btn"
        onClick={() => setChatOpen(true)}
        aria-label="Abrir chat normativo"
        aria-haspopup="dialog"
        aria-expanded={chatOpen}
      >
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.75"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
        </svg>
      </button>

      {chatOpen && <ChatDrawer sessionId={session.session_id} onClose={handleChatClose} />}
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
    <div
      className="h-stepper"
      role="progressbar"
      aria-label="Progreso del wizard"
      aria-valuenow={current}
      aria-valuemin={1}
      aria-valuemax={7}
      aria-valuetext={`Paso ${current} de 7: ${STEPS[current - 1].label}`}
    >
      <div className="h-stepper-progress">
        <div className="h-stepper-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="h-stepper-dots" role="list">
        {STEPS.map((s) => {
          const isCurrent = s.n === current;
          const isDone = s.n < current;
          const isReachable = s.n <= current;
          const stateLabel = isDone ? "(completado)" : isCurrent ? "(actual)" : "(pendiente)";
          return (
            <button
              key={s.n}
              role="listitem"
              type="button"
              className={`h-stepper-dot${isCurrent ? " is-current" : ""}${isDone ? " is-done" : ""}`}
              disabled={!isReachable || disabled || isCurrent}
              onClick={() => onNavigate(s.n)}
              aria-label={`Paso ${s.n}: ${s.label} ${stateLabel}`}
              aria-current={isCurrent ? "step" : undefined}
            >
              <span className="dot-n" aria-hidden="true">{s.n}</span>
              <span className="dot-l" aria-hidden="true">{s.label}</span>
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
  onBack,
  backPending,
}: {
  session: SessionState;
  onSessionChange: (s: SessionState) => void;
  onBack: () => void;
  backPending: boolean;
}) {
  const meta = STEPS.find((s) => s.n === session.current_step);
  return (
    <section className="fade-up" key={session.current_step}>
      <header className="wm-head">
        {session.current_step > 1 && (
          <button
            type="button"
            onClick={onBack}
            disabled={backPending}
            className="btn btn-ghost"
            style={{ marginBottom: 8, fontSize: 13, padding: "6px 0", color: "var(--text-muted)" }}
          >
            ← Volver al paso {session.current_step - 1}
          </button>
        )}
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
  const drawerRef = useRef<HTMLElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

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

  // Foco en botón cerrar al montar
  useEffect(() => {
    closeButtonRef.current?.focus();
  }, []);

  // Cerrar con Escape + focus trap dentro del drawer
  useEffect(() => {
    const drawer = drawerRef.current;
    if (!drawer) return;

    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key !== "Tab") return;
      const focusable = Array.from(
        drawer!.querySelectorAll<HTMLElement>(
          "button:not([disabled]), input:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex=\"-1\"])",
        ),
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }

    drawer.addEventListener("keydown", onKey);
    return () => drawer.removeEventListener("keydown", onKey);
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
      {/* biome-ignore lint/a11y/useKeyWithClickEvents: overlay actúa de fondo clicable */}
      <div className="chat-overlay" onClick={onClose} aria-hidden="true" tabIndex={-1} />
      <aside
        ref={drawerRef}
        className="chat-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Chat normativo"
        aria-labelledby="chat-drawer-title"
      >
        <div className="chat-head">
          <div>
            <h3 id="chat-drawer-title">Chat normativo</h3>
            <p>Pregunta sobre requisitos del DPP. Cada respuesta cita el Art.</p>
          </div>
          <button
            ref={closeButtonRef}
            type="button"
            className="chat-close"
            onClick={onClose}
            aria-label="Cerrar chat normativo"
          >
            ✕
          </button>
        </div>

        <div
          ref={scrollRef}
          className="chat-body"
          role="log"
          aria-live="polite"
          aria-label="Mensajes del chat"
        >
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
          {sending && <div className="chat-typing" aria-live="polite">Pensando…</div>}
        </div>

        <div className="chat-input">
          <label htmlFor="chat-msg-input" className="sr-only">
            Mensaje de consulta normativa
          </label>
          <input
            id="chat-msg-input"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
            placeholder="Pregunta sobre normativa…"
            disabled={sending}
            aria-describedby="chat-drawer-title"
          />
          <button
            type="button"
            onClick={send}
            disabled={sending || !input.trim()}
            aria-label="Enviar mensaje"
          >
            Enviar
          </button>
        </div>
      </aside>
    </>
  );
}
