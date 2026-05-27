import { redirect } from "next/navigation";

import { getCurrentUser } from "@/modules/auth/lib/auth-api";
import { LandingPage } from "@/modules/landing/pages/LandingPage";

// El "home" de un usuario con sesión es su panel, no la landing de marketing.
// Si no hay sesión (o el backend no responde), se muestra la landing pública,
// cuyo CTA "Crear DPP" enlaza a /wizard y queda gateado por el proxy a
// login → wizard (flujo del primer DPP).
export default async function Page() {
  let isAuthenticated = false;
  try {
    isAuthenticated = (await getCurrentUser()) !== null;
  } catch {
    // Backend caído o error inesperado: tratamos como deslogueado y mostramos
    // la landing (no rompemos la página pública por un fallo de /auth/me).
    isAuthenticated = false;
  }
  if (isAuthenticated) redirect("/panel");
  return <LandingPage />;
}
