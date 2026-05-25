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
const MAX_LENGTH = 2000;

export default function WizardEntryPage() {
  const router = useRouter();
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trimmed = description.trim();
  const tooShort = trimmed.length < MIN_LENGTH;
  const charPercent = Math.min((trimmed.length / MIN_LENGTH) * 100, 100);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (tooShort || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const { session_id } = await api.createSession({ description: trimmed });
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
    <main className="flex flex-1 items-center justify-center px-4 py-12">
      <div className="animate-fade-in w-full max-w-2xl">
        {/* Card */}
        <div className="glass rounded-2xl shadow-xl overflow-hidden">
          {/* Accent bar */}
          <div className="h-1.5 bg-gradient-to-r from-teal-600 via-teal-500 to-emerald-400" />

          <div className="p-8 sm:p-10">
            {/* Header */}
            <div className="mb-8">
              <div className="inline-flex items-center gap-2 rounded-full bg-teal-50 px-3 py-1 text-xs font-medium text-teal-700 mb-4">
                <span className="h-1.5 w-1.5 rounded-full bg-teal-500" />
                Paso 1 de 7
              </div>
              <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">
                Nuevo Pasaporte Digital de Producto
              </h1>
              <p className="mt-3 text-sm leading-relaxed text-slate-500">
                Describe tu producto en lenguaje natural. El sistema identificar&aacute; el sector
                ESPR aplicable y te guiar&aacute; por los 7 pasos del wizard. El borrador se guarda
                autom&aacute;ticamente y puedes retomarlo desde cualquier dispositivo con la URL de
                la sesi&oacute;n.
              </p>
            </div>

            {/* Form */}
            <form onSubmit={onSubmit} className="space-y-6">
              <div>
                <label
                  htmlFor="description"
                  className="block text-sm font-semibold text-slate-700 mb-2"
                >
                  Descripci&oacute;n del producto
                </label>
                <textarea
                  id="description"
                  name="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value.slice(0, MAX_LENGTH))}
                  rows={6}
                  minLength={MIN_LENGTH}
                  maxLength={MAX_LENGTH}
                  placeholder="Ej.: Bater&iacute;a industrial recargable de Li-ion 5 kWh para almacenamiento residencial fotovoltaico..."
                  className="w-full rounded-xl border border-slate-200 bg-white/80 p-4 text-sm leading-relaxed text-slate-800 placeholder:text-slate-300 focus:border-teal-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 disabled:opacity-50"
                  disabled={submitting}
                  required
                />

                {/* Character counter */}
                <div className="mt-3 flex items-center gap-3">
                  <div className="h-1.5 flex-1 rounded-full bg-slate-100 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-300 ease-out"
                      style={{
                        width: `${charPercent}%`,
                        background:
                          charPercent >= 100
                            ? "linear-gradient(90deg, #0d9488, #14b8a6)"
                            : "#cbd5e1",
                      }}
                    />
                  </div>
                  <span
                    className={`text-xs font-mono tabular-nums ${
                      tooShort ? "text-slate-400" : "text-teal-600"
                    }`}
                  >
                    {trimmed.length} / {MAX_LENGTH}
                  </span>
                </div>
                {tooShort && trimmed.length > 0 && (
                  <p className="mt-1.5 text-xs text-slate-400">
                    M&iacute;nimo {MIN_LENGTH} caracteres ({MIN_LENGTH - trimmed.length} restantes)
                  </p>
                )}
              </div>

              {/* Error */}
              {error && (
                <div
                  role="alert"
                  className="flex items-start gap-3 rounded-xl bg-red-50 border border-red-100 p-4"
                >
                  <svg
                    aria-hidden="true"
                    className="h-5 w-5 text-red-400 shrink-0 mt-0.5"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={1.5}
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z"
                    />
                  </svg>
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}

              {/* Submit */}
              <button
                type="submit"
                disabled={tooShort || submitting}
                className="group relative w-full rounded-xl bg-gradient-to-r from-teal-600 to-teal-500 px-6 py-3.5 text-sm font-semibold text-white shadow-lg shadow-teal-500/25 hover:shadow-teal-500/40 hover:from-teal-700 hover:to-teal-600 active:scale-[0.98] disabled:cursor-not-allowed disabled:from-slate-200 disabled:to-slate-200 disabled:text-slate-400 disabled:shadow-none"
              >
                <span className="flex items-center justify-center gap-2">
                  {submitting ? (
                    <>
                      <svg
                        aria-hidden="true"
                        className="h-4 w-4 animate-spin"
                        viewBox="0 0 24 24"
                        fill="none"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        />
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                        />
                      </svg>
                      Creando sesi&oacute;n...
                    </>
                  ) : (
                    <>
                      Empezar wizard
                      <svg
                        aria-hidden="true"
                        className="h-4 w-4 transition-transform group-hover:translate-x-0.5"
                        fill="none"
                        viewBox="0 0 24 24"
                        strokeWidth={2.5}
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3"
                        />
                      </svg>
                    </>
                  )}
                </span>
              </button>
            </form>
          </div>
        </div>
      </div>
    </main>
  );
}
