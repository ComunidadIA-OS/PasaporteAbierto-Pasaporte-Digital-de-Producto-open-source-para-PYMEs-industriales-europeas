// Manejo centralizado de errores de API.

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly body: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// Envuelve una promesa de fetch para devolver datos o un error tipado
// sin lanzar. Disponible para código nuevo; los call-sites actuales siguen
// usando try/catch sobre el objeto `api` (comportamiento sin cambios).
export async function getDataOrError<T>(
  promise: Promise<T>,
): Promise<{ data: T; error: null } | { data: null; error: ApiError | Error }> {
  try {
    return { data: await promise, error: null };
  } catch (err) {
    return { data: null, error: err instanceof Error ? err : new Error(String(err)) };
  }
}
