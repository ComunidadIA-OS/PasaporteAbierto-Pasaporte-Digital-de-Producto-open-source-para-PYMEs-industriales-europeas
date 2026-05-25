// Entrada al wizard — paso 1 inicial (F4-01).
//
// El fabricante describe su producto en lenguaje libre. Al enviar:
//   POST /api/v1/sessions → redirige a /wizard/{session_id}
// donde se sirve el shell con persistencia y reanudación por URL.
//
// Diseño Compliance OS: columna única centrada, sin aside derecha, textarea
// brutalist con borde nítido, contador en mono, CTA verde compliance.

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError, api } from "@/app/lib/api";

const MIN_LENGTH = 20;

export default function WizardEntryPage() {
  const router = useRouter();
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const tooShort = description.trim().length < MIN_LENGTH;
  const remaining = Math.max(MIN_LENGTH - description.trim().length, 0);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (tooShort || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const { session_id } = await api.createSession({ description: description.trim() });
      router.push(`/wizard/${session_id}`);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `Error ${err.status} al crear la sesión.`
          : "No se pudo crear la sesión. Revisa la conexión con el backend.";
      setError(msg);
      setSubmitting(false);
    }
  }

  return (
    <>
      <header className="appbar">
        <Link href="/" className="appbar-brand">
          <div className="appbar-logo">P</div>
          <span>PasaporteAbierto</span>
        </Link>
        <div className="appbar-spacer" />
      </header>

      <main className="wizard-entry">
        <div className="wizard-entry-main fade-in">
          <Link href="/" className="btn btn-ghost" style={{ marginLeft: -12, marginBottom: 16 }}>
            ← Volver
          </Link>
          <div className="eyebrow">Paso 01 · Descripción</div>
          <h1 className="h-1" style={{ marginTop: 12 }}>
            Cuéntanos qué <em>fabricas</em>.
          </h1>
          <p className="muted" style={{ marginTop: 16, fontSize: 16, maxWidth: 600 }}>
            En lenguaje natural: para qué sirve, de qué está hecho, a quién se vende. La IA
            identifica el sector ESPR aplicable, te muestra la cita normativa que lo justifica, y
            carga el plugin con sus campos obligatorios.
          </p>

          <form onSubmit={onSubmit} style={{ marginTop: 40 }}>
            <div className="framed-textarea">
              <label htmlFor="description" className="sr-only">
                Descripción del producto
              </label>
              <textarea
                id="description"
                name="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={7}
                minLength={MIN_LENGTH}
                placeholder="Ej.: Batería industrial recargable de Li-ion 5 kWh para almacenamiento residencial fotovoltaico…"
                className="textarea"
                disabled={submitting}
                required
              />
              <div className="meta">
                <span>
                  {tooShort ? (
                    <>
                      Mínimo {MIN_LENGTH} caracteres · faltan{" "}
                      <strong style={{ color: "var(--warn)" }}>{remaining}</strong>
                    </>
                  ) : (
                    <span style={{ color: "var(--success)" }}>
                      ✓ longitud OK · {description.trim().length} caracteres
                    </span>
                  )}
                </span>
                <span>auto-guardado activado</span>
              </div>
            </div>

            {error && (
              <p
                role="alert"
                className="status-panel is-danger"
                style={{ marginTop: 24, padding: 14 }}
              >
                {error}
              </p>
            )}

            <div
              style={{
                marginTop: 32,
                display: "flex",
                gap: 12,
                alignItems: "center",
                flexWrap: "wrap",
              }}
            >
              <button
                type="submit"
                disabled={tooShort || submitting}
                className="btn btn-primary btn-lg"
              >
                {submitting ? (
                  <>
                    <span className="spinner" />
                    Creando sesión…
                  </>
                ) : (
                  <>Continuar al paso 2 →</>
                )}
              </button>
              <span className="mono" style={{ fontSize: 11, color: "var(--text-faint)" }}>
                ⌘ + Enter
              </span>
            </div>
          </form>
        </div>
      </main>
    </>
  );
}
