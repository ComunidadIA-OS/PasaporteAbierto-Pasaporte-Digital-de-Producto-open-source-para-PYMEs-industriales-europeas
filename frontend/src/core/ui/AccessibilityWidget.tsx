// Widget flotante de accesibilidad (esquina inferior derecha).
//
// Botón con icono de persona que abre un panel con interruptores de modos
// (daltonismo, dislexia, alto contraste, texto grande, subrayar enlaces,
// reducir animaciones). Cada modo añade/quita una clase en <html>; las reglas
// viven en globals.css. La elección se guarda en localStorage y se reaplica al
// cargar (un script inline en layout.tsx evita el parpadeo inicial).

"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const STORAGE_KEY = "pa-accesibilidad";

const MODES = [
  {
    id: "daltonico",
    className: "a11y-daltonico",
    label: "Modo daltónico",
    desc: "Paleta de color segura (Okabe-Ito) y símbolos en los avisos, no solo color.",
  },
  {
    id: "dislexia",
    className: "a11y-dislexia",
    label: "Modo dislexia",
    desc: "Tipografía legible y más espacio entre letras, palabras y líneas.",
  },
  {
    id: "contraste",
    className: "a11y-contraste",
    label: "Alto contraste",
    desc: "Refuerza el contraste de texto y bordes.",
  },
  {
    id: "texto-grande",
    className: "a11y-texto-grande",
    label: "Texto más grande",
    desc: "Aumenta el tamaño de todo el contenido.",
  },
  {
    id: "enlaces",
    className: "a11y-enlaces",
    label: "Subrayar enlaces",
    desc: "Subraya los enlaces para distinguirlos sin depender del color.",
  },
  {
    id: "sin-animaciones",
    className: "a11y-sin-animaciones",
    label: "Reducir animaciones",
    desc: "Desactiva transiciones y movimientos de la interfaz.",
  },
] as const;

type ModeId = (typeof MODES)[number]["id"];
type ModeState = Partial<Record<ModeId, boolean>>;

function applyMode(id: ModeId, on: boolean) {
  const mode = MODES.find((m) => m.id === id);
  if (!mode) return;
  document.documentElement.classList.toggle(mode.className, on);
}

export function AccessibilityWidget() {
  const [open, setOpen] = useState(false);
  const [modes, setModes] = useState<ModeState>({});
  const fabRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  // Carga inicial desde localStorage y reaplica las clases (el script inline
  // de layout.tsx ya las puso antes de pintar; aquí sincronizamos el estado).
  useEffect(() => {
    let stored: ModeState = {};
    try {
      stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}") as ModeState;
    } catch {
      stored = {};
    }
    setModes(stored);
    for (const m of MODES) applyMode(m.id, !!stored[m.id]);
  }, []);

  const toggle = useCallback((id: ModeId) => {
    setModes((prev) => {
      const next = { ...prev, [id]: !prev[id] };
      applyMode(id, !!next[id]);
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        // localStorage no disponible (p. ej. modo privado): el modo sigue
        // activo durante la sesión aunque no se persista.
      }
      return next;
    });
  }, []);

  const reset = useCallback(() => {
    for (const m of MODES) applyMode(m.id, false);
    setModes({});
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // Silencioso: si no hay localStorage, basta con limpiar el estado.
    }
  }, []);

  const close = useCallback(() => {
    setOpen(false);
    requestAnimationFrame(() => fabRef.current?.focus());
  }, []);

  // Escape para cerrar + foco al primer control al abrir.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("keydown", onKey);
    const first = panelRef.current?.querySelector<HTMLElement>("input, button");
    first?.focus();
    return () => document.removeEventListener("keydown", onKey);
  }, [open, close]);

  // Cerrar al hacer clic fuera del panel y del botón.
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      const t = e.target as Node;
      if (!panelRef.current?.contains(t) && !fabRef.current?.contains(t)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const activeCount = MODES.filter((m) => modes[m.id]).length;

  return (
    <>
      <button
        ref={fabRef}
        type="button"
        className="a11y-fab"
        onClick={() => setOpen((o) => !o)}
        aria-label={
          activeCount > 0
            ? `Opciones de accesibilidad, ${activeCount} activas`
            : "Opciones de accesibilidad"
        }
        aria-haspopup="dialog"
        aria-expanded={open}
      >
        <svg viewBox="0 0 24 24" width="26" height="26" fill="currentColor" aria-hidden="true">
          <circle cx="12" cy="3.8" r="2.2" />
          <path d="M20 8.2c-.2-.5-.8-.8-1.3-.6L12 9.9 5.3 7.6c-.5-.2-1.1.1-1.3.6s.1 1.1.6 1.3l4.9 1.7-1.3 7.6c-.1.6.3 1.1.9 1.2.5.1 1-.3 1.1-.8l1.1-6.3h.4l1.1 6.3c.1.5.6.9 1.1.8.6-.1 1-.6.9-1.2l-1.3-7.6 4.9-1.7c.5-.2.8-.8.6-1.3z" />
        </svg>
        {activeCount > 0 && (
          <span className="a11y-fab-badge" aria-hidden="true">
            {activeCount}
          </span>
        )}
      </button>

      {open && (
        <div
          ref={panelRef}
          className="a11y-panel"
          role="dialog"
          aria-label="Opciones de accesibilidad"
        >
          <div className="a11y-panel-head">
            <h2 className="a11y-panel-title">Accesibilidad</h2>
            <button
              type="button"
              className="a11y-panel-close"
              onClick={close}
              aria-label="Cerrar opciones de accesibilidad"
            >
              <svg
                viewBox="0 0 24 24"
                width="20"
                height="20"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                aria-hidden="true"
              >
                <path d="M6 6l12 12M18 6L6 18" />
              </svg>
            </button>
          </div>

          <div className="a11y-options">
            {MODES.map((m) => (
              <label key={m.id} className="a11y-option" htmlFor={`a11y-${m.id}`}>
                <input
                  id={`a11y-${m.id}`}
                  type="checkbox"
                  checked={!!modes[m.id]}
                  onChange={() => toggle(m.id)}
                />
                <span>
                  <span className="a11y-option-label">{m.label}</span>
                  <span className="a11y-option-desc">{m.desc}</span>
                </span>
              </label>
            ))}
          </div>

          <button type="button" className="a11y-reset" onClick={reset} disabled={activeCount === 0}>
            Restablecer todo
          </button>
        </div>
      )}
    </>
  );
}
