// Landing page rediseñada (tema Quiet · D).
//
// Estructura: appbar con pill de salud + hero centrado + sección "cómo
// funciona" (lista de 7 pasos) + sección "plugins disponibles" + footer.
// El fetch a /api/v1/health se hace SSR; el resultado alimenta el pill.

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

const STEPS = [
  { n: 1, kind: "det" as const, label: "Descripción del producto", desc: "Texto libre. Alimenta la clasificación." },
  { n: 2, kind: "ai" as const, label: "Clasificación de sector", desc: "IA con RAG sobre corpus normativo. Cita Art." },
  { n: 3, kind: "det" as const, label: "BOM dinámico", desc: "Formulario adaptado al plugin del sector." },
  { n: 4, kind: "det" as const, label: "Documentos requeridos", desc: "Datasheets, LCA, declaración CE, SDS…" },
  { n: 5, kind: "ai" as const, label: "Extracción IA de campos", desc: "pdfplumber + LLM. SSE en vivo." },
  { n: 6, kind: "det" as const, label: "Verificación de completitud", desc: "Score y advertencias contra el plugin." },
  { n: 7, kind: "det" as const, label: "Publicación DPP + QR + firma", desc: "JSON-LD CIRPASS-2 + Ed25519 + ISO 15459." },
];

const PLUGINS = [
  {
    name: "batteries.yaml",
    title: "Baterías industriales",
    meta: "Reg. UE 2023/1542 · 48 campos",
    status: "estable",
    statusClass: "badge-success",
    desc: "Cubre Anexo XIII secciones 1, 2 y 3. Identificador ISO/IEC 15459 por Art. 77.3.",
  },
  {
    name: "textile.yaml",
    title: "Textil técnico",
    meta: "Acto delegado ESPR · 22 campos",
    status: "beta",
    statusClass: "badge-warn",
    desc: "Plugin de referencia para validar la arquitectura de extensibilidad. GS1 Digital Link.",
  },
  {
    name: "your-sector.yaml",
    title: "Tu sector",
    meta: "Plugin YAML · — campos",
    status: "comunidad",
    statusClass: "badge-neutral",
    desc: "Añade un sector con un YAML. El loader valida contra schema. Sin tocar el core.",
  },
];

export default async function Home() {
  const health = await getHealth();

  return (
    <>
      <header className="appbar">
        <div className="appbar-brand">
          <div className="appbar-logo">P</div>
          <span>PasaporteAbierto</span>
        </div>
        <div className="appbar-spacer" />
        <span className={`appbar-pill${health ? "" : " is-down"}`}>
          <span className="dot" />
          {health ? `backend · ${health.version}` : "backend · sin conexión"}
        </span>
      </header>

      <main className="fade-in">
        <section className="hero">
          <div className="container-narrow">
            <span className="hero-tag">ESPR · Reg. UE 2024/1781 · Open Source</span>
            <h1 className="h-display">
              Pasaporte Digital de <em>Producto</em>,
              <br />
              sin prisa.
            </h1>
            <p className="hero-lede">
              Aplicación auto-hospedable que ayuda a fabricantes PYME a generar el DPP exigido
              por la normativa europea en menos de 15 minutos. Siete pasos, una pantalla por
              paso, cita normativa en cada decisión.
            </p>
            <div className="hero-cta">
              <Link href="/wizard" className="btn btn-primary btn-lg">
                Generar pasaporte →
              </Link>
              <a
                href="https://github.com/ComunidadIA-OS/PasaporteAbierto-Pasaporte-Digital-de-Producto-open-source-para-PYMEs-industriales-europeas"
                target="_blank"
                rel="noreferrer"
                className="btn btn-ghost btn-lg"
              >
                Ver en GitHub
              </a>
            </div>
          </div>
        </section>

        <section className="section">
          <div className="container">
            <div className="section-head">
              <span className="eyebrow">El wizard</span>
              <h2 className="h-1">
                Siete pasos. Dos son <em>IA</em>.
                <br />
                El resto, deterministas.
              </h2>
              <p className="muted">
                Pipeline lineal. Los pasos de IA se acotan al Clasificador (paso 2) y al
                Recolector (paso 5). Todo lo demás es código verificable paso a paso.
              </p>
            </div>

            <div className="steps-list">
              {STEPS.map((s) => (
                <div key={s.n} className="step-item">
                  <div className="si-num">PASO {String(s.n).padStart(2, "0")}</div>
                  <div>
                    <div className="si-title">{s.label}</div>
                    <div className="si-desc">{s.desc}</div>
                  </div>
                  <div className={`si-kind ${s.kind}`}>
                    {s.kind === "ai" ? "IA" : "determinista"}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="section">
          <div className="container">
            <div className="section-head">
              <span className="eyebrow">Cobertura sectorial</span>
              <h2 className="h-1">
                Un <em>YAML</em> por sector.
                <br />
                Cero código para extender.
              </h2>
            </div>

            <div className="plugins-list">
              {PLUGINS.map((p) => (
                <div key={p.name} className="plugin-item">
                  <div className="pi-head">
                    <span className="pi-name">{p.name}</span>
                    <span className={`badge ${p.statusClass}`}>{p.status}</span>
                  </div>
                  <h3 className="pi-title">{p.title}</h3>
                  <p className="pi-meta">{p.meta}</p>
                  <p className="pi-desc">{p.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer className="footer">
        <div className="container">
          <div className="footer-grid">
            <div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  marginBottom: 16,
                }}
              >
                <div className="appbar-logo">P</div>
                <strong style={{ fontFamily: "var(--font-head)", fontSize: 16 }}>
                  PasaporteAbierto
                </strong>
              </div>
              <p style={{ maxWidth: 360, margin: 0 }}>
                Pasaporte Digital de Producto auto-hospedable para fabricantes PYME conforme al
                Reglamento UE 2024/1781 (ESPR). Apache 2.0.
              </p>
            </div>
            <div>
              <h4>Normativa</h4>
              <ul>
                <li>Reg. UE 2024/1781 (ESPR)</li>
                <li>Reg. UE 2023/1542 (baterías)</li>
                <li>CIRPASS-2 Core</li>
                <li>ISO/IEC 15459</li>
              </ul>
            </div>
          </div>
        </div>
      </footer>
    </>
  );
}
