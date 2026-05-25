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
    <div className="space-y-4">
      <p className="text-sm text-gray-600">
        Describe tu producto con suficiente detalle para que el Clasificador identifique el
        sector ESPR aplicable. Cuanto más concreto (materiales, función, capacidad), mejor.
      </p>

      <label htmlFor="description" className="block">
        <span className="text-sm font-semibold">Descripción del producto</span>
        <textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={6}
          className="mt-2 w-full rounded-md border border-gray-300 p-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          disabled={pending}
        />
        <span
          className={`mt-1 block text-xs ${tooShort ? "text-gray-500" : "text-green-700"}`}
        >
          {description.trim().length} / mínimo {MIN_LENGTH} caracteres
        </span>
      </label>

      {error && (
        <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error}
        </p>
      )}

      <button
        type="button"
        onClick={onContinue}
        disabled={tooShort || pending}
        className="rounded-md bg-blue-600 px-6 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-gray-300"
      >
        {pending ? "Guardando…" : "Continuar al paso 2 →"}
      </button>
    </div>
  );
}
