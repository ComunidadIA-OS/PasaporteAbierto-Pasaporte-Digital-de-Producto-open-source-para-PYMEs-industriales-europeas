import Link from "next/link";

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
    <main className="flex flex-1 flex-col items-center justify-center px-6 py-16">
      {/* Hero */}
      <section className="animate-fade-in text-center max-w-3xl">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-teal-200 bg-teal-50 px-4 py-1.5 text-sm font-medium text-teal-700">
          <span>Reglamento UE 2024/1781 (ESPR)</span>
        </div>

        <h1 className="text-5xl font-bold tracking-tight sm:text-6xl">
          <span className="bg-gradient-to-r from-teal-700 via-teal-600 to-teal-500 bg-clip-text text-transparent">
            PasaporteAbierto
          </span>
        </h1>

        <p className="mt-6 text-lg leading-relaxed text-slate-600 max-w-2xl mx-auto">
          Genera el Pasaporte Digital de Producto de tu empresa en minutos. Open source,
          auto-hospedable y conforme a la normativa europea para PYMEs industriales.
        </p>

        <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
          <Link
            href="/wizard"
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-teal-600 to-teal-500 px-8 py-3.5 text-base font-semibold text-white shadow-lg shadow-teal-500/25 hover:shadow-teal-500/40 hover:from-teal-700 hover:to-teal-600 active:scale-[0.98]"
          >
            Comenzar
            <svg
              aria-hidden="true"
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2.5}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3"
              />
            </svg>
          </Link>

          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-8 py-3.5 text-base font-semibold text-slate-700 shadow-sm hover:bg-slate-50 hover:border-slate-300 active:scale-[0.98]"
          >
            Ver en GitHub
          </a>
        </div>
      </section>

      {/* Features */}
      <section className="animate-fade-in-delay-2 mt-20 grid max-w-4xl gap-6 sm:grid-cols-3">
        {[
          {
            icon: (
              <svg
                aria-hidden="true"
                className="h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z"
                />
              </svg>
            ),
            title: "Conforme ESPR",
            desc: "Cumple el Reglamento UE 2024/1781 con verificador determinista integrado.",
          },
          {
            icon: (
              <svg
                aria-hidden="true"
                className="h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z"
                />
              </svg>
            ),
            title: "IA asistida",
            desc: "Clasificador y extractor automático de datos desde documentación técnica.",
          },
          {
            icon: (
              <svg
                aria-hidden="true"
                className="h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M13.5 10.5V6.75a4.5 4.5 0 1 1 9 0v3.75M3.75 21.75h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H3.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z"
                />
              </svg>
            ),
            title: "Open source",
            desc: "Auto-hospedable. Tus datos no salen de tu infraestructura.",
          },
        ].map((f) => (
          <div
            key={f.title}
            className="card hover:shadow-xl hover:-translate-y-0.5 transition-all duration-300"
          >
            <div className="mb-3 inline-flex rounded-lg bg-teal-50 p-2.5 text-teal-600">
              {f.icon}
            </div>
            <h3 className="font-semibold text-slate-800">{f.title}</h3>
            <p className="mt-1.5 text-sm leading-relaxed text-slate-500">{f.desc}</p>
          </div>
        ))}
      </section>

      {/* Health status */}
      <section className="animate-fade-in-delay-3 mt-16 w-full max-w-md">
        <div className="card border border-slate-100">
          <div className="flex items-center gap-3 mb-3">
            <span
              className={`h-2.5 w-2.5 rounded-full ${
                health ? "bg-emerald-500 animate-pulse-glow" : "bg-red-400"
              }`}
            />
            <h2 className="text-sm font-semibold text-slate-700">Estado del backend</h2>
          </div>
          {health ? (
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
              {Object.entries(health).map(([k, v]) => (
                <div key={k} className="contents">
                  <dt className="text-slate-400 font-mono">{k}</dt>
                  <dd className="text-slate-700">{v}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="text-sm text-red-500">
              Backend no disponible en <code className="font-mono text-xs">/api/v1/health</code>
            </p>
          )}
        </div>
      </section>
    </main>
  );
}
