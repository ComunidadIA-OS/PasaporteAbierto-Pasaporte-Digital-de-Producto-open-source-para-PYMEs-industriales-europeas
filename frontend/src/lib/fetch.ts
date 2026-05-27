import { ApiError } from "@/core/errors";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const API_V1 = `${API_BASE}/api/v1`;

// La cookie de sesión es httpOnly: el navegador la adjunta solo si la petición
// va con `credentials: "include"`. Pero en un Server Component el fetch corre en
// el servidor de Next (no en el navegador), así que ahí no hay cookie que
// adjuntar: la reenviamos leyéndola de la request entrante con `next/headers`.
// El import es dinámico y guardado por `typeof window` para que no entre en el
// bundle del cliente (next/headers es server-only).
async function serverCookieHeader(): Promise<string | undefined> {
  if (typeof window !== "undefined") return undefined;
  try {
    const { cookies } = await import("next/headers");
    const store = await cookies();
    const all = store.getAll();
    if (all.length === 0) return undefined;
    return all.map((c) => `${c.name}=${c.value}`).join("; ");
  } catch {
    // Fuera de un scope de request (build estático): no hay cookies que reenviar.
    return undefined;
  }
}

// Transporte único sobre fetch. JSON por defecto, cache no-store, lanza ApiError
// si !ok, y propaga la cookie de sesión en ambos lados (cliente y servidor).
export async function serverFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const cookieHeader = await serverCookieHeader();
  const res = await fetch(`${API_V1}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(cookieHeader ? { Cookie: cookieHeader } : {}),
      ...init?.headers,
    },
    credentials: "include",
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(`${init?.method ?? "GET"} ${path} → ${res.status}`, res.status, body);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// Hook para llamadas ad-hoc desde Client Components que no pasen por el
// objeto `api`. Mismo transporte; existe para cumplir la convención (nunca
// fetch() nativo en cliente). Estable entre renders.
export function useClientFetch() {
  return serverFetch;
}
