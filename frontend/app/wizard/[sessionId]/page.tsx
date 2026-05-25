// Página del wizard reanudable por URL (F4-01).
//
// Server Component: hace el fetch inicial de la sesión en SSR. Si no
// existe, muestra 404. Si existe, delega toda la interactividad a
// `WizardClient` para que la navegación entre pasos sea client-side
// (sin recargar y sin desmontar el chat lateral).

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
      <main className="min-h-screen p-12">
        <h1 className="text-2xl font-bold">Sesión no encontrada</h1>
        <p className="mt-2 text-sm text-gray-600">
          La sesión <code className="font-mono">{sessionId}</code> no existe. Vuelve a{" "}
          <a href="/wizard" className="text-blue-600 underline">
            crear una nueva
          </a>
          .
        </p>
      </main>
    );
  }

  return <WizardClient initialSession={session} />;
}
