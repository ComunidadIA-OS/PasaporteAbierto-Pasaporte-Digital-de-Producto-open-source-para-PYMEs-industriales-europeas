// Landing — tema Compliance OS (tech SaaS · brutalist · referencias UE · acento eco).
//
// Estructura espejo del prototipo (design bundle): appbar con pill de salud, hero
// 2-col (texto + dashboard oscuro), sección "por qué" con 3 features bordeadas
// brutalist, lista de 7 pasos, plugins disponibles, CTA en card negra y footer 4-col.

import Link from "next/link";

import { Reveal } from "./components/Reveal";

const REPO_URL =
  "https://github.com/ComunidadIA-OS/PasaporteAbierto-Pasaporte-Digital-de-Producto-open-source-para-PYMEs-industriales-europeas";

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

const HERO_STATS = [
  { n: "7", l: "pasos guiados" },
  { n: "≤15min", l: "por pasaporte" },
  { n: "2", l: "sectores activos" },
  { n: "100%", l: "on-premise" },
];

const REGULATION = [
  {
    num: "01",
    glyph: "§",
    title: "Conforme al Reg. UE 2024/1781",
    body: "Cumplimiento de ESPR y de actos delegados sectoriales. Cada campo cita el artículo que lo justifica, en su idioma original.",
  },
  {
    num: "02",
    glyph: "⛨",
    title: "Audit log con hash chain",
    body: "Cada decisión queda registrada y encadenada por hash. Cualquier manipulación rompe la cadena de forma detectable.",
  },
  {
    num: "03",
    glyph: "⚿",
    title: "Firma Ed25519 + JSON-LD CIRPASS-2",
    body: "El DPP se firma criptográficamente y se publica en formato JSON-LD CIRPASS-2 Core. QR resoluble vía URN ISO/IEC 15459.",
  },
];

const STEPS = [
  {
    n: 1,
    kind: "det" as const,
    label: "Descripción del producto",
    desc: "Texto libre. Alimenta la clasificación.",
  },
  {
    n: 2,
    kind: "ai" as const,
    label: "Clasificación de sector",
    desc: "IA con RAG sobre corpus normativo. Cita Art.",
  },
  {
    n: 3,
    kind: "det" as const,
    label: "BOM (Bill of Materials) dinámico",
    desc: "Formulario adaptado al plugin del sector.",
  },
  {
    n: 4,
    kind: "det" as const,
    label: "Documentos requeridos",
    desc: "Datasheets, LCA, declaración CE, SDS…",
  },
  {
    n: 5,
    kind: "ai" as const,
    label: "Extracción IA de campos",
    desc: "pdfplumber + LLM. SSE streaming en vivo.",
  },
  {
    n: 6,
    kind: "det" as const,
    label: "Verificación de completitud",
    desc: "Score y advertencias contra el plugin.",
  },
  {
    n: 7,
    kind: "det" as const,
    label: "Publicación DPP + QR + firma",
    desc: "JSON-LD CIRPASS-2 + Ed25519 + ISO 15459.",
  },
];

const PLUGINS = [
  {
    name: "batteries.yaml",
    title: "Baterías industriales",
    meta: "Reg. UE 2023/1542 · 48 campos",
    status: "estable",
    statusClass: "badge-success",
    glyph: "▮",
    desc: "Cubre Anexo XIII secciones 1, 2 y 3 (públicas, interés legítimo, autoridades). Identificador ISO/IEC 15459 por Art. 77.3.",
  },
  {
    name: "textile.yaml",
    title: "Textil técnico",
    meta: "Acto delegado ESPR · 22 campos",
    status: "beta",
    statusClass: "badge-warn",
    glyph: "✿",
    desc: "Plugin de referencia para validar la arquitectura de extensibilidad. Identificador GS1 Digital Link por defecto.",
  },
  {
    name: "your-sector.yaml",
    title: "Tu sector",
    meta: "Plugin YAML · — campos",
    status: "comunidad",
    statusClass: "badge-neutral",
    glyph: "</>",
    desc: "Añade un sector nuevo con un YAML. El loader valida contra schema; si no cumple, no se carga. Sin tocar el core.",
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
        <nav className="appbar-nav" aria-label="Principal">
          <Link href="/" className="is-active">
            Inicio
          </Link>
          <Link href="/wizard">Wizard</Link>
          <a href={`${REPO_URL}#plugins`} target="_blank" rel="noreferrer">
            Plugins
          </a>
          <a href={REPO_URL} target="_blank" rel="noreferrer">
            GitHub
          </a>
        </nav>
        <div className="appbar-spacer" />
        <span className={`appbar-pill${health ? "" : " is-down"}`}>
          <span className="dot" />
          {health ? `backend · ${health.version}` : "backend · sin conexión"}
        </span>
      </header>

      <main className="fade-in">
        <section className="hero">
          <div className="container">
            <div className="hero-grid">
              <div>
                <Reveal>
                  <div className="hero-tag">
                    <span className="dot" />
                    <span>ESPR · Reg. UE 2024/1781</span>
                    <span aria-hidden style={{ opacity: 0.4 }}>
                      ·
                    </span>
                    <span>Open Source</span>
                  </div>
                </Reveal>

                <Reveal delay={120}>
                  <h1 className="h-display">
                    Compliance <em>auditable</em>
                    <br />
                    end-to-end.
                  </h1>
                </Reveal>

                <Reveal delay={260}>
                  <p className="hero-lede">
                    Aplicación auto-hospedable que ayuda a fabricantes PYME a generar el DPP exigido
                    por el Reglamento UE 2024/1781 en menos de 15 minutos. Trazabilidad inmutable,
                    citas normativas en cada decisión, código abierto.
                  </p>
                </Reveal>

                <Reveal delay={380}>
                  <div className="hero-cta">
                    <Link href="/wizard" className="btn btn-primary btn-lg">
                      Crear mi primer DPP →
                    </Link>
                    <a
                      href={REPO_URL}
                      target="_blank"
                      rel="noreferrer"
                      className="btn btn-secondary btn-lg"
                    >
                      Ver en GitHub
                    </a>
                  </div>
                </Reveal>

                <Reveal delay={500}>
                  <div className="hero-strip">
                    {HERO_STATS.map((s) => (
                      <div key={s.l}>
                        <div className="n">{s.n}</div>
                        <div className="l">{s.l}</div>
                      </div>
                    ))}
                  </div>
                </Reveal>
              </div>

              <Reveal delay={200}>
                <div className="hero-preview" aria-hidden>
                  <div className="preview-head">
                    <div className="dotrow">
                      <span />
                      <span />
                      <span />
                    </div>
                    <div className="preview-url">pasaporte.industriasvolta.eu/dpp/9f3a7b2c1e</div>
                  </div>
                  <div className="preview-body">
                    <div className="preview-product">
                      <div className="preview-thumb">⚡</div>
                      <div>
                        <div className="name">VoltaCore HS-5000</div>
                        <div className="meta">Batería Li-ion · 5 kWh · Industrias Volta</div>
                      </div>
                    </div>

                    {[
                      { l: "Química", v: "NMC-622" },
                      { l: "Capacidad", v: "5,12 kWh @ 51,2 V" },
                      { l: "CO₂e (LCA)", v: "82 kg / kWh" },
                      { l: "Co reciclado", v: "16%", badge: "min Art. 8" },
                      { l: "Vida útil", v: "6 000 ciclos · 15 a" },
                      { l: "Firma", v: "Ed25519 ✓" },
                    ].map((row) => (
                      <div key={row.l} className="preview-row">
                        <span className="lbl">{row.l}</span>
                        <span className="val">
                          {row.v}
                          {row.badge && <span className="badge">{row.badge}</span>}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </Reveal>
            </div>
          </div>
        </section>

        <section className="section">
          <div className="container">
            <div className="section-head">
              <div className="lead">
                <Reveal>
                  <span className="eyebrow">Por qué PasaporteAbierto</span>
                </Reveal>
                <Reveal delay={80}>
                  <h2 className="h-1">Trazabilidad regulatoria, sin atajos.</h2>
                </Reveal>
              </div>
              <Reveal delay={200}>
                <p className="lede-aside">
                  Diseñado con criterios institucionales: cada paso es verificable, cada campo cita
                  norma, y nada se publica si falta un dato obligatorio.
                </p>
              </Reveal>
            </div>

            <div className="feature-grid">
              {REGULATION.map((it, i) => (
                <Reveal key={it.num} delay={i * 100}>
                  <div className="num">— {it.num}</div>
                  <div className="glyph" aria-hidden>
                    {it.glyph}
                  </div>
                  <h3>{it.title}</h3>
                  <p>{it.body}</p>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        <section className="section">
          <div className="container">
            <div className="section-head">
              <div className="lead">
                <Reveal>
                  <span className="eyebrow">El wizard</span>
                </Reveal>
                <Reveal delay={80}>
                  <h2 className="h-1">
                    Siete pasos. Dos son <em>IA</em>.
                    <br />
                    El resto, deterministas.
                  </h2>
                </Reveal>
              </div>
              <Reveal delay={200}>
                <p className="lede-aside">
                  Pipeline lineal. Los pasos de IA están acotados a Clasificador (2) y Recolector
                  (5); todo lo demás es código verificable paso a paso.
                </p>
              </Reveal>
            </div>

            <Reveal>
              <div className="steps-list">
                {STEPS.map((s) => (
                  <div key={s.n} className="step-item">
                    <div className="si-num">PASO {String(s.n).padStart(2, "0")}</div>
                    <div>
                      <div className="si-title">{s.label}</div>
                      <div className="si-desc">{s.desc}</div>
                    </div>
                    <div className={`si-kind ${s.kind}`}>
                      {s.kind === "ai" ? "AI · Recolector" : "determinista"}
                    </div>
                  </div>
                ))}
              </div>
            </Reveal>
          </div>
        </section>

        <section className="section">
          <div className="container">
            <div className="section-head">
              <div className="lead">
                <Reveal>
                  <span className="eyebrow">Cobertura sectorial</span>
                </Reveal>
                <Reveal delay={80}>
                  <h2 className="h-1">
                    Un <em>YAML</em> por sector.
                    <br />
                    Cero código para extender.
                  </h2>
                </Reveal>
              </div>
            </div>

            <div className="feature-grid">
              {PLUGINS.map((p, i) => (
                <Reveal key={p.name} delay={i * 100}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                    }}
                  >
                    <div className="num">{p.name}</div>
                    <span className={`badge ${p.statusClass}`}>{p.status}</span>
                  </div>
                  <div className="glyph" aria-hidden>
                    {p.glyph}
                  </div>
                  <h3>{p.title}</h3>
                  <div
                    className="mono"
                    style={{ fontSize: 11, color: "var(--text-muted)", margin: "4px 0 12px" }}
                  >
                    {p.meta}
                  </div>
                  <p>{p.desc}</p>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        <section className="section">
          <div className="container">
            <Reveal>
              <div className="cta-card">
                <span className="eyebrow">Empieza ahora</span>
                <h2 className="h-1">Tu primer DPP en menos de 15 minutos.</h2>
                <p>
                  Sin login. Sin dependencias SaaS. Levanta toda la solución con{" "}
                  <code className="mono" style={{ color: "var(--accent)" }}>
                    docker compose up
                  </code>{" "}
                  y empieza a generar pasaportes.
                </p>
                <div className="hero-cta">
                  <Link href="/wizard" className="btn btn-primary btn-lg">
                    Crear mi primer DPP →
                  </Link>
                  <a
                    href={REPO_URL}
                    target="_blank"
                    rel="noreferrer"
                    className="btn btn-secondary btn-lg"
                  >
                    Ver en GitHub
                  </a>
                </div>
              </div>
            </Reveal>
          </div>
        </section>
      </main>

      <footer className="footer">
        <div className="container">
          <div className="footer-grid">
            <div>
              <div className="footer-brand">
                <div className="appbar-logo">P</div>
                <span>PasaporteAbierto</span>
              </div>
              <p>
                Pasaporte Digital de Producto auto-hospedable para fabricantes PYME conforme al
                Reglamento UE 2024/1781 (ESPR). Apache 2.0.
              </p>
            </div>
            <div>
              <h4>Producto</h4>
              <ul>
                <li>
                  <Link href="/wizard">Wizard</Link>
                </li>
                <li>Plugins</li>
                <li>DPP público</li>
                <li>Chat normativo</li>
              </ul>
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
            <div>
              <h4>Comunidad</h4>
              <ul>
                <li>
                  <a href={REPO_URL} target="_blank" rel="noreferrer">
                    GitHub
                  </a>
                </li>
                <li>Contribuir un plugin</li>
                <li>DPGA badge</li>
                <li>Licencia Apache 2.0</li>
              </ul>
            </div>
          </div>
        </div>
      </footer>
    </>
  );
}
