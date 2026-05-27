import { redirect } from "next/navigation";
import { Suspense } from "react";

import { getCurrentUser } from "@/modules/auth/lib/auth-api";
import { LoginPage } from "@/modules/auth/pages/LoginPage";

// Solo permitimos destinos internos en `next` (evita open redirect).
function safeNext(next: string | undefined): string {
  return next?.startsWith("/") && !next.startsWith("//") ? next : "/panel";
}

// Si ya hay sesión, no tiene sentido mostrar el formulario: vamos al destino
// pedido (`next`) o al panel. Si no hay sesión (o el backend falla), se muestra
// el login. `useSearchParams` en LoginPage exige el límite de Suspense.
export default async function Page({ searchParams }: { searchParams: Promise<{ next?: string }> }) {
  let isAuthenticated = false;
  try {
    isAuthenticated = (await getCurrentUser()) !== null;
  } catch {
    isAuthenticated = false;
  }
  if (isAuthenticated) {
    const { next } = await searchParams;
    redirect(safeNext(next));
  }
  return (
    <Suspense fallback={null}>
      <LoginPage />
    </Suspense>
  );
}
