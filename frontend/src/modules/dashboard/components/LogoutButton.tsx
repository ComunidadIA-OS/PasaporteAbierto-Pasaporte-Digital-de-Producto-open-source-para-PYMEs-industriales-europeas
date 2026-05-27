// Cierra la sesión: revoca la sesión server-side y borra la cookie (vía
// backend), luego vuelve a /login. No hay estado de auth en el cliente que
// limpiar (la cookie es httpOnly).

"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { authApi } from "@/modules/auth/lib/auth-api";

export function LogoutButton() {
  const router = useRouter();
  const [pending, setPending] = useState(false);

  async function onLogout() {
    setPending(true);
    try {
      await authApi.logout();
    } catch {
      // El logout es best-effort: aunque falle la llamada, mandamos a /login.
    }
    router.replace("/login");
    router.refresh();
  }

  return (
    <button type="button" onClick={onLogout} disabled={pending}>
      {pending ? "Saliendo…" : "Cerrar sesión"}
    </button>
  );
}
