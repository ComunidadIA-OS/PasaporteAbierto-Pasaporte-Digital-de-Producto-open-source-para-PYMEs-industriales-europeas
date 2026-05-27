import { ApiError } from "@/core/errors";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const API_V1 = `${API_BASE}/api/v1`;

// Transporte único sobre fetch. Mismo comportamiento que el `request` previo:
// JSON por defecto, cache no-store, lanza ApiError si !ok.
export async function serverFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_V1}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
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
