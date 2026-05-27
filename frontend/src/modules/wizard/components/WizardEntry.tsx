// Entrada al wizard — crea sesión y redirige al shell (F4-01).
//
// Al montar la página, POST /api/v1/sessions crea una sesión vacía y
// redirige a /wizard/{session_id} donde el paso 1 del shell recoge
// la descripción. Así el paso 1 solo aparece una vez.

"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { ApiError, api } from "@/modules/wizard/lib/wizard-api";

export function WizardEntry() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const creating = useRef(false);

  useEffect(() => {
    if (creating.current) return;
    creating.current = true;

    api
      .createSession({ description: "" })
      .then(({ session_id }) => {
        router.replace(`/wizard/${session_id}`);
      })
      .catch((err) => {
        creating.current = false;
        setError(
          err instanceof ApiError
            ? `Error ${err.status} al crear la sesión.`
            : "No se pudo crear la sesión. Revisa la conexión con el backend.",
        );
      });
  }, [router]);

  if (error) {
    return (
      <main className="wizard-entry">
        <div className="wizard-entry-main fade-in">
          <p className="status-panel is-danger" style={{ padding: 14 }}>
            {error}
          </p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => window.location.reload()}
            style={{ marginTop: 16 }}
          >
            Reintentar
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="wizard-entry">
      <div className="wizard-entry-main fade-in" style={{ textAlign: "center", paddingTop: 120 }}>
        <span className="spinner" />
        <p className="muted" style={{ marginTop: 16 }}>
          Creando sesión…
        </p>
      </div>
    </main>
  );
}
