async function getHealth() {
  const url = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  try {
    const res = await fetch(`${url}/api/v1/health`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as { version: string; model: string; backend: string };
  } catch {
    return null;
  }
}

export default async function Home() {
  const health = await getHealth();
  return (
    <main className="min-h-screen p-12">
      <h1 className="text-3xl font-bold">PasaporteAbierto</h1>
      <p className="text-sm text-gray-600 mt-2">
        Pasaporte Digital de Producto · Reglamento UE 2024/1781
      </p>
      <section className="mt-8 rounded-lg border p-4">
        <h2 className="font-semibold mb-2">Backend</h2>
        {health ? (
          <ul className="text-sm">
            <li>version: {health.version}</li>
            <li>model: {health.model}</li>
            <li>backend: {health.backend}</li>
          </ul>
        ) : (
          <p className="text-sm text-red-600">Backend no responde en /api/v1/health</p>
        )}
      </section>
    </main>
  );
}
