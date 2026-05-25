// Entrada al wizard — paso 1 inicial (F4-01).
//
// El fabricante describe su producto en lenguaje libre. Al enviar:
//   POST /api/v1/sessions → redirige a /wizard/{session_id}
// donde se sirve el shell con persistencia y reanudación por URL.

"use client";

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
    <main className="mx-auto max-w-2xl p-12">
      <h1 className="text-3xl font-bold">Nuevo Pasaporte Digital de Producto</h1>
      <p className="mt-2 text-sm text-gray-600">
        Describe tu producto en lenguaje natural. El sistema identificará el sector ESPR
        aplicable y te guiará por los 7 pasos del wizard. El borrador se guarda
        automáticamente y puedes retomarlo desde cualquier dispositivo con la URL de la
        sesión.
      </p>

      <form onSubmit={onSubmit} className="mt-8 space-y-4">
        <label htmlFor="description" className="block">
          <span className="text-sm font-semibold">Descripción del producto</span>
          <textarea
            id="description"
            name="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={6}
            minLength={MIN_LENGTH}
            placeholder="Ej.: Batería industrial recargable de Li-ion 5 kWh para almacenamiento residencial fotovoltaico…"
            className="mt-2 w-full rounded-md border border-gray-300 p-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            disabled={submitting}
            required
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
          type="submit"
          disabled={tooShort || submitting}
          className="rounded-md bg-blue-600 px-6 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-gray-300"
        >
          {submitting ? "Creando sesión…" : "Empezar wizard"}
        </button>
      </form>
    </main>
  );
}
