// Shell interactivo del wizard (F4-01) — diseño "Pipeline + DPP en vivo".
//
// Layout de 3 zonas:
//   1. Rail vertical del pipeline (izquierda): los 7 pasos como una línea de
//      montaje normativa, con distinción visual det/IA (invariante: solo los
//      pasos 2 y 5 son IA) y navegación hacia pasos ya completados.
//   2. Stage central: cabecera del paso + contenido del paso activo.
//   3. Panel "DPP en vivo" (derecha): se rellena a medida que avanzas
//      (producto → sector → BOM → campos → firma → QR), cerrando el círculo
//      con el mockup de la landing.
//
// Carga inicial: el Server Component pasa `initialSession`. A partir de ahí se
// mantiene estado local y se persiste cada cambio de step con PATCH. La URL no
// cambia entre pasos: una recarga reanuda el `current_step` desde BD.
//
// El chat lateral (F3-04) se invoca con un FAB y se muestra en un drawer modal.
// Sigue siendo un endpoint independiente del pipeline: jamás escribe en el
// estado del wizard (tampoco en el panel "DPP en vivo", que es solo lectura).

"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState, useTransition } from "react";

import { Icon } from "@/core/ui/Icon";
import { Step1Description } from "@/modules/wizard/components/Step1Description";
import { Step2Sector } from "@/modules/wizard/components/Step2Sector";
import { Step3Bom } from "@/modules/wizard/components/Step3Bom";
import { Step4Documents } from "@/modules/wizard/components/Step4Documents";
import { Step5Extract } from "@/modules/wizard/components/Step5Extract";
import { Step6Verify } from "@/modules/wizard/components/Step6Verify";
import { Step7Publish } from "@/modules/wizard/components/Step7Publish";
import { api, type DppResponse, type SessionState } from "@/modules/wizard/lib/wizard-api";

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
  // Estado del DPP publicado, elevado desde Step7 para alimentar el panel en
  // vivo (firma + QR). Solo lectura: no es estado del pipeline.
  const [published, setPublished] = useState<DppResponse | null>(null);

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
        <span className="appbar-pill">
          <span className="dot" />
          {session.session_id.slice(0, 8)} · auto-guardado
        </span>
      </header>

      <div className="wizard-shell">
        <div className="wizard-bg" aria-hidden />
        <div className="wizard-layout">
          <PipelineRail current={session.current_step} onNavigate={navigateTo} disabled={pending} />

          <main id="main-content" className="wizard-stage">
            <StepSlot
              session={session}
              onSessionChange={setSession}
              onBack={() => navigateTo(session.current_step - 1)}
              backPending={pending}
              onPublished={setPublished}
            />
          </main>

          <DppLivePanel session={session} published={published} />
        </div>
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
        <Icon name="forum" size={24} />
      </button>

      {chatOpen && <ChatDrawer sessionId={session.session_id} onClose={handleChatClose} />}
    </>
  );
}

// ============================================================
// Rail del pipeline — los 7 pasos como línea de montaje vertical
// ============================================================

function PipelineRail({
  current,
  onNavigate,
  disabled,
}: {
  current: number;
  onNavigate: (n: number) => void;
  disabled: boolean;
}) {
  const pct = Math.round(((current - 1) / (STEPS.length - 1)) * 100);
  return (
    <aside
      className="wizard-rail"
      aria-label="Pasos del asistente"
      role="progressbar"
      aria-valuenow={current}
      aria-valuemin={1}
      aria-valuemax={7}
      aria-valuetext={`Paso ${current} de 7: ${STEPS[current - 1].label}`}
    >
      <div className="rail-head">
        <span className="rail-kicker">Pipeline DPP</span>
        <span className="rail-count mono">
          {String(current).padStart(2, "0")}
          <span className="faint"> / 07</span>
        </span>
      </div>

      <ol className="rail-steps" style={{ "--rail-pct": `${pct}%` } as React.CSSProperties}>
        {STEPS.map((s) => {
          const isCurrent = s.n === current;
          const isDone = s.n < current;
          const isReachable = s.n <= current;
          const isAI = s.kind === "ai";
          const stateLabel = isDone ? "(completado)" : isCurrent ? "(actual)" : "(pendiente)";
          const cls = [
            "rail-step",
            isCurrent ? "is-current" : "",
            isDone ? "is-done" : "",
            !isReachable ? "is-upcoming" : "",
            isAI ? "is-ai" : "",
          ]
            .filter(Boolean)
            .join(" ");
          return (
            <li key={s.n} className={cls}>
              <button
                type="button"
                className="rail-step-btn"
                disabled={!isReachable || disabled || isCurrent}
                onClick={() => onNavigate(s.n)}
                aria-current={isCurrent ? "step" : undefined}
                aria-label={`Paso ${s.n}: ${s.label} ${stateLabel}`}
                title={isDone ? `Volver al paso ${s.n}` : s.label}
              >
                <span className="rail-node" aria-hidden>
                  {isDone ? <Icon name="check" size={15} weight={500} /> : <span>{s.n}</span>}
                </span>
                <span className="rail-step-body">
                  <span className="rail-step-label">{s.label}</span>
                  <span className="rail-step-kind">
                    {isAI ? (
                      <>
                        <Icon name="auto_awesome" size={12} />
                        Agente IA
                      </>
                    ) : (
                      "Determinista"
                    )}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>

      <p className="rail-legend">
        <span className="rail-legend-item">
          <Icon name="auto_awesome" size={12} /> IA
        </span>
        <span className="rail-legend-item">
          <span className="rail-legend-dot" /> Determinista
        </span>
      </p>
    </aside>
  );
}

// ============================================================
// Panel "DPP en vivo" — se rellena a medida que avanza el pipeline
// ============================================================

function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max - 1).trimEnd()}…` : text;
}

function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

type FacetState = "done" | "partial" | "pending";

function DppLivePanel({
  session,
  published,
}: {
  session: SessionState;
  published: DppResponse | null;
}) {
  const verified = session.extracted_fields.filter((f) => f.provenance === "verified").length;
  const pendingFields = session.extracted_fields.filter(
    (f) => f.provenance === "required_pending",
  ).length;
  const hasExtraction = session.extracted_fields.length > 0;
  const bomCount = Object.keys(session.bom ?? {}).length;
  const hasSector = !!session.sector && session.sector !== "unknown";
  const description = session.description?.trim();
  const pct =
    session.classification_confidence != null
      ? Math.round(session.classification_confidence * 100)
      : null;

  const facets: { icon: string; label: string; value: string; state: FacetState }[] = [
    {
      icon: "inventory_2",
      label: "Producto",
      value: description ? truncate(description, 34) : "Sin describir",
      state: description ? "done" : "pending",
    },
    {
      icon: "category",
      label: "Sector ESPR",
      value: hasSector
        ? `${capitalize(session.sector as string)}${pct != null ? ` · ${pct}%` : ""}`
        : "Sin clasificar",
      state: hasSector ? "done" : "pending",
    },
    {
      icon: "account_tree",
      label: "Materiales (BOM)",
      value: bomCount > 0 ? `${bomCount} campos` : "Pendiente",
      state: bomCount > 0 ? "done" : "pending",
    },
    {
      icon: "fact_check",
      label: "Campos extraídos",
      value: hasExtraction ? `${verified} verif. · ${pendingFields} pend.` : "Sin extraer",
      state: hasExtraction ? (pendingFields === 0 ? "done" : "partial") : "pending",
    },
    {
      icon: "lock",
      label: "Firma Ed25519",
      value: published?.signed ? "Firmado" : "Pendiente",
      state: published?.signed ? "done" : "pending",
    },
    {
      icon: "qr_code_2",
      label: "QR + URL pública",
      value: published ? "Generado" : "Pendiente",
      state: published ? "done" : "pending",
    },
  ];

  return (
    <aside className="wizard-live" aria-label="DPP en construcción">
      <div className="live-card">
        <div className="live-head">
          <span className="live-title">DPP en vivo</span>
          <span className={`live-status${published ? " is-conforme" : ""}`}>
            {published ? (
              <>
                <Icon name="verified" size={13} fill />
                Conforme
              </>
            ) : (
              "Borrador"
            )}
          </span>
        </div>

        <ul className="live-facets">
          {facets.map((f) => (
            <li key={f.label} className={`live-facet is-${f.state}`}>
              <span className="live-facet-icon" aria-hidden>
                <Icon name={f.icon} size={18} />
              </span>
              <span className="live-facet-body">
                <span className="live-facet-label">{f.label}</span>
                <span className="live-facet-value">{f.value}</span>
              </span>
              <span className="live-facet-state" aria-hidden>
                {f.state === "done" ? (
                  <Icon name="check_circle" size={16} fill />
                ) : f.state === "partial" ? (
                  <Icon name="contrast" size={16} fill />
                ) : (
                  <span className="live-dot" />
                )}
              </span>
            </li>
          ))}
        </ul>

        {published && (
          <div className="live-uri">
            <span className="live-uri-label">Identificador</span>
            <code className="mono">{truncate(published.gs1_uri, 30)}</code>
          </div>
        )}
      </div>
      <p className="live-note">
        <Icon name="visibility" size={13} />
        Solo lectura · refleja tu progreso. El chat nunca escribe aquí.
      </p>
    </aside>
  );
}

// ============================================================
// Stage central — cabecera del paso + contenido del paso activo
// ============================================================

function StepSlot({
  session,
  onSessionChange,
  onBack,
  backPending,
  onPublished,
}: {
  session: SessionState;
  onSessionChange: (s: SessionState) => void;
  onBack: () => void;
  backPending: boolean;
  onPublished: (dpp: DppResponse) => void;
}) {
  const meta = STEPS.find((s) => s.n === session.current_step);
  const isAI = meta?.kind === "ai";
  return (
    <section className="fade-up" key={session.current_step}>
      <header className="wm-head">
        {session.current_step > 1 && (
          <button
            type="button"
            onClick={onBack}
            disabled={backPending}
            className="btn btn-ghost wm-back"
          >
            <Icon name="arrow_back" size={16} />
            Volver al paso {session.current_step - 1}
          </button>
        )}
        <div className={`label${isAI ? " is-ai" : ""}`}>
          {isAI ? <Icon name="auto_awesome" size={12} /> : null}
          PASO {String(session.current_step).padStart(2, "0")} ·{" "}
          {isAI ? "Componente IA" : "Determinista"}
        </div>
        <h1>{meta?.label}</h1>
        <p className="subtitle">{STEP_SUBTITLES[session.current_step]}</p>
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
      {session.current_step === 7 && <Step7Publish session={session} onPublished={onPublished} />}
    </section>
  );
}

// ============================================================
// Chat — drawer modal abierto desde el FAB
// ============================================================

let chatMsgId = 1;

interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  text: string;
  citation: { regulation: string; article: string; url: string | null } | null;
}

const MSG_BIENVENIDA: ChatMessage = {
  id: 0,
  role: "assistant",
  text: "¡Hola! Soy tu asistente normativo. ¿En qué puedo ayudarte?",
  citation: null,
};

function ChatDrawer({ sessionId, onClose }: { sessionId: string; onClose: () => void }) {
  // Invariante: el chat NUNCA escribe en el estado del wizard. Sí persiste su
  // propio histórico en chat_messages (canal independiente, F3-04 criterio 3).
  const [messages, setMessages] = useState<ChatMessage[]>([MSG_BIENVENIDA]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const drawerRef = useRef<HTMLElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  // Carga el histórico persistido al montar; si existe, reemplaza el saludo inicial.
  useEffect(() => {
    let cancelled = false;
    api
      .chatHistory(sessionId)
      .then((res) => {
        if (cancelled) return;
        if (res.messages.length > 0) {
          setMessages(
            res.messages.map((m) => ({
              id: ++chatMsgId,
              role: m.role,
              text: m.content,
              citation: m.citation,
            })),
          );
          setTimeout(() => scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight), 0);
        }
      })
      .catch(() => {
        // Sin histórico accesible → mantiene el saludo inicial ya visible.
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
            <Icon name="close" size={20} />
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
