// Paso 1 del wizard: descripción del producto.
//
// El usuario llegó aquí porque ya creó la sesión en /wizard. Aquí puede
// revisar/editar la descripción antes de pasar al Clasificador (paso 2).
// "Continuar" hace PATCH { description, step: 2 } y refresca el shell.

"use client";

import { useState, useTransition } from "react";

import { ApiError, api, type SessionState } from "@/app/lib/api";

const MIN_LENGTH = 20;

export function Step1Description({
  session,
  onSessionChange,
}: {
  session: SessionState;
  onSessionChange: (s: SessionState) => void;
}) {
  const [description, setDescription] = useState(session.description ?? "");
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const tooShort = description.trim().length < MIN_LENGTH;
  const remaining = Math.max(MIN_LENGTH - description.trim().length, 0);

  function onContinue() {
    if (tooShort || pending) return;
    setError(null);
    startTransition(async () => {
      try {
        const updated = await api.updateProgress(session.session_id, {
          description: description.trim(),
          step: 2,
        });
        onSessionChange(updated);
      } catch (err) {
        setError(
          err instanceof ApiError
            ? `Error ${err.status} al guardar.`
            : "No se pudo guardar el progreso.",
        );
      }
    });
  }

  return (
    <div className="col gap-4" style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <p className="muted" style={{ margin: 0, fontSize: 15 }}>
        Describe tu producto con suficiente detalle para que el Clasificador identifique el sector
        ESPR aplicable. Cuanto más concreto (materiales, función, capacidad), mejor.
      </p>

      <div className="framed-textarea">
        <label htmlFor="description" className="sr-only">
          Descripción del producto
        </label>
        <textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={7}
          className="textarea"
          disabled={pending}
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
        <p role="alert" className="status-panel is-danger" style={{ margin: 0, padding: 14 }}>
          {error}
        </p>
      )}

      <div>
        <button
          type="button"
          onClick={onContinue}
          disabled={tooShort || pending}
          className="btn btn-primary btn-lg"
        >
          {pending ? "Guardando…" : "Continuar al paso 2 →"}
        </button>
      </div>
    </div>
  );
}
