// Página del wizard reanudable por URL (F4-01).
//
// Server Component: hace el fetch inicial de la sesión en SSR. Si no
// existe, muestra 404. Si existe, delega toda la interactividad a
// `WizardContent` para que la navegación entre pasos sea client-side.

import Link from "next/link";
import { redirect } from "next/navigation";

import { WizardContent } from "@/modules/wizard/components/WizardContent";
import { ApiError, api, type SessionState } from "@/modules/wizard/lib/wizard-api";

async function loadSession(sessionId: string): Promise<SessionState | null> {
  try {
    return await api.getSession(sessionId);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    // 401: cookie caducada/ausente (o sesión de otro usuario, que el backend
    // trata como 404, no 401). Al login conservando el destino.
    if (err instanceof ApiError && err.status === 401) redirect(`/login?next=/wizard/${sessionId}`);
    throw err;
  }
}

export async function WizardPage({ sessionId }: { sessionId: string }) {
  const session = await loadSession(sessionId);

  if (!session) {
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
        </header>
        <main className="wizard-entry-main fade-in">
          <div className="eyebrow">404</div>
          <h1 className="typ-1" style={{ marginTop: 12 }}>
            Sesión no <em>encontrada</em>.
          </h1>
          <p className="muted" style={{ marginTop: 16, maxWidth: 540 }}>
            La sesión <code className="mono">{sessionId}</code> no existe. Vuelve a{" "}
            <Link href="/wizard" style={{ color: "var(--accent)", textDecoration: "underline" }}>
              crear una nueva
            </Link>
            .
          </p>
        </main>
      </>
    );
  }

  return <WizardContent initialSession={session} />;
}
