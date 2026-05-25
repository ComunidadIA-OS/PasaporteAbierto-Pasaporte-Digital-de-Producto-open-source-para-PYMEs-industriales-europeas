// Página del wizard reanudable por URL (F4-01).
//
// Server Component: hace el fetch inicial de la sesión en SSR. Si no
// existe, muestra 404. Si existe, delega toda la interactividad a
// `WizardClient` para que la navegación entre pasos sea client-side.

import Link from "next/link";

import { ApiError, api, type SessionState } from "@/app/lib/api";

import { WizardClient } from "./wizard-client";

async function loadSession(sessionId: string): Promise<SessionState | null> {
  try {
    return await api.getSession(sessionId);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

export default async function WizardPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await params;
  const session = await loadSession(sessionId);

  if (!session) {
    return (
      <>
        <header className="appbar">
          <Link href="/" className="appbar-brand">
            <div className="appbar-logo">P</div>
            <span>PasaporteAbierto</span>
          </Link>
        </header>
        <main className="wizard-entry-main fade-in">
          <div className="eyebrow">404</div>
          <h1 className="h-1" style={{ marginTop: 12 }}>
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

  return <WizardClient initialSession={session} />;
}
