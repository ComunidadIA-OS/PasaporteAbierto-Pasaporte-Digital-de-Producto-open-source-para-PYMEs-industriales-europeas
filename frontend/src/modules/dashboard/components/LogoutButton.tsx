// Cierra la sesión: revoca la sesión server-side y borra la cookie (vía
// backend), luego vuelve a /login. No hay estado de auth en el cliente que
// limpiar (la cookie es httpOnly).

"use client";

import { useState } from "react";

import { authApi } from "@/modules/auth/lib/auth-api";

export function LogoutButton() {
  const [pending, setPending] = useState(false);

  async function onLogout() {
    setPending(true);
    try {
      await authApi.logout();
    } catch {
      // El logout es best-effort: aunque falle la llamada, mandamos a /login.
    }
    // Navegación DURA (no el router de Next): además de borrar la cookie en el
    // backend, descarta el Router Cache del cliente para que el próximo login
    // no muestre el /panel cacheado de esta cuenta.
    window.location.replace("/login");
  }

  return (
    <button type="button" onClick={onLogout} disabled={pending}>
      {pending ? "Saliendo…" : "Cerrar sesión"}
    </button>
  );
}
