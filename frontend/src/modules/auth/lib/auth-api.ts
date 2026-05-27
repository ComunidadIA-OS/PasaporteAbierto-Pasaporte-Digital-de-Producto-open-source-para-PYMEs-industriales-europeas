// Cliente de autenticación (ADR-0004). Espeja /api/v1/auth/* del backend.
//
// El token de sesión viaja en una cookie httpOnly que fija el backend; este
// cliente NUNCA toca el token (no hay localStorage). `serverFetch` ya manda
// `credentials: "include"` y reenvía la cookie en Server Components.

import { ApiError } from "@/core/errors";
import type { AuthCredentials, AuthUser } from "@/core/responses";
import { serverFetch } from "@/lib/fetch";

export { ApiError } from "@/core/errors";
export type { AuthCredentials, AuthUser } from "@/core/responses";

export const authApi = {
  register(body: AuthCredentials): Promise<AuthUser> {
    return serverFetch("/auth/register", { method: "POST", body: JSON.stringify(body) });
  },
  login(body: AuthCredentials): Promise<AuthUser> {
    return serverFetch("/auth/login", { method: "POST", body: JSON.stringify(body) });
  },
  logout(): Promise<void> {
    return serverFetch("/auth/logout", { method: "POST" });
  },
  me(): Promise<AuthUser> {
    return serverFetch("/auth/me");
  },
};

// `me()` lanza ApiError(401) si no hay sesión; este helper lo traduce a null
// para usarlo en Server Components sin try/catch repetido.
export async function getCurrentUser(): Promise<AuthUser | null> {
  try {
    return await authApi.me();
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) return null;
    throw err;
  }
}
