// Landing — PasaporteAbierto · Visual corporate landing con animaciones.

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

const HOW_STEPS = [
  {
    n: "01",
    title: "Describe tu producto",
    body: "Introduce los datos de tu producto. La IA clasifica el sector ESPR y carga los campos normativos.",
  },
  {
    n: "02",
    title: "Sube tus documentos",
    body: "Datasheets, LCA, declaración CE. La IA extrae automáticamente los campos del DPP.",
  },
  {
    n: "03",
    title: "Publica con firma",
    body: "Verifica la completitud, firma con Ed25519 y publica el DPP con QR resoluble.",
  },
];

const TRUST_POINTS = [
  {
    icon: "§",
    title: "Conforme a ESPR",
    body: "Cada campo cita el artículo del reglamento que lo exige.",
    color: "#6ea8fe",
    bg: "rgba(110, 168, 254, 0.12)",
  },
  {
    icon: "#",
    title: "Auditoría inmutable",
    body: "Hash chain verificable. Preparado para inspecciones.",
    color: "#4ade80",
    bg: "rgba(74, 222, 128, 0.12)",
  },
  {
    icon: "K",
    title: "Firma criptográfica",
    body: "Ed25519 + JSON-LD CIRPASS-2 + QR por producto.",
    color: "#99bbff",
    bg: "rgba(153, 187, 255, 0.1)",
  },
];

const ROADMAP = [
  {
    year: "2026",
    status: "live",
    color: "#00b14f",
    glow: "rgba(0, 177, 79, 0.4)",
    sectors: ["Baterías"],
    label: "Ya obligatorio",
  },
  {
    year: "2027",
    status: "ready",
    color: "#003399",
    glow: "rgba(0, 51, 153, 0.35)",
    sectors: ["Textil", "Electrónica"],
    label: "Acto delegado finalizado",
  },
  {
    year: "2028",
    status: "coming",
    color: "#ea580c",
    glow: "rgba(234, 88, 12, 0.3)",
    sectors: ["Mobiliario", "Construcción", "Neumáticos"],
    label: "En preparación",
  },
];

export default async function Home() {
  const health = await getHealth();

  return (
    <>
      <header className="appbar">
        <div className="appbar-brand">
          <div className="appbar-logo">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M6 2h12a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z" />
              <circle cx="12" cy="10" r="3" />
              <path d="M7 17a5 5 0 0 1 10 0" />
            </svg>
          </div>
          <span>PasaporteAbierto</span>
        </div>
        <nav className="appbar-nav" aria-label="Principal">
          <Link href="/" className="is-active">
            Inicio
          </Link>
          <Link href="/wizard">Wizard</Link>
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
        {/* ── HERO ── */}
        <section className="v-hero">
          {/* Decoración de fondo */}
          <div className="v-hero-bg" aria-hidden>
            <div className="v-hero-grid" />
            <div className="v-hero-orb v-hero-orb-1" />
            <div className="v-hero-orb v-hero-orb-2" />
            <div className="v-hero-orb v-hero-orb-3" />
          </div>

          <div className="v-hero-content container container-narrow">
            <Reveal>
              <div className="hero-tag hero-tag-dark">
                <span className="dot dot-glow" />
                <span>ESPR · Reg. UE 2024/1781</span>
                <span aria-hidden style={{ opacity: 0.3 }}>
                  ·
                </span>
                <span>Open Source · Apache 2.0</span>
              </div>
            </Reveal>

            <Reveal delay={100}>
              <h1 className="v-hero-title">
                Tu Pasaporte Digital
                <br />
                de Producto, <em>conforme</em>
              </h1>
            </Reveal>

            <Reveal delay={220}>
              <p className="v-hero-sub">
                Genera el DPP que exige el Reglamento ESPR en minutos. Auto-hospedable, con firma
                criptográfica, sin coste de licencia y sin depender de ningún SaaS.
              </p>
            </Reveal>

            <Reveal delay={340}>
              <div className="v-hero-actions">
                <Link href="/wizard" className="btn btn-primary btn-lg btn-glow">
                  Crear mi primer DPP →
                </Link>
                <a
                  href={REPO_URL}
                  target="_blank"
                  rel="noreferrer"
                  className="btn btn-ghost-light btn-lg"
                >
                  Ver en GitHub
                </a>
              </div>
            </Reveal>

            <Reveal delay={460}>
              <div className="v-hero-metrics">
                {[
                  { n: "7", l: "pasos guiados" },
                  { n: "≤15'", l: "por pasaporte" },
                  { n: "6", l: "sectores ESPR" },
                  { n: "0€", l: "licencia" },
                ].map((s) => (
                  <div key={s.l} className="v-metric">
                    <span className="v-metric-n">{s.n}</span>
                    <span className="v-metric-l">{s.l}</span>
                  </div>
                ))}
              </div>
            </Reveal>
          </div>

          {/* Flecha scroll indicator */}
          <div className="v-hero-scroll" aria-hidden>
            <div className="v-hero-scroll-line" />
          </div>
        </section>

        {/* ── CÓMO FUNCIONA (con línea conectora) ── */}
        <section className="v-section v-section-light">
          <div className="container">
            <div className="v-section-head">
              <Reveal>
                <span className="eyebrow">Cómo funciona</span>
              </Reveal>
              <Reveal delay={80}>
                <h2 className="typ-1">
                  De la descripción al DPP firmado
                  <br />
                  en <em>tres pasos</em>
                </h2>
              </Reveal>
            </div>

            <div className="v-steps">
              <div className="v-steps-line" aria-hidden />
              {HOW_STEPS.map((s, i) => (
                <Reveal key={s.n} delay={i * 180}>
                  <div className="v-step">
                    <div className="v-step-dot" aria-hidden>
                      <span className="v-step-dot-num">{s.n}</span>
                    </div>
                    <div className="v-step-content">
                      <div className="v-step-num">Paso {s.n}</div>
                      <h3>{s.title}</h3>
                      <p>{s.body}</p>
                    </div>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* ── CONFIANZA ── */}
        <section className="v-section v-section-dark">
          <div className="container">
            <div className="v-section-head">
              <Reveal>
                <span className="eyebrow eyebrow-light">Diseñado para cumplir</span>
              </Reveal>
              <Reveal delay={80}>
                <h2 className="typ-1 typ-light">Tres garantías para tu equipo de compliance</h2>
              </Reveal>
            </div>

            <div className="v-trust-row">
              {TRUST_POINTS.map((t, i) => (
                <Reveal key={t.title} delay={i * 120}>
                  <div className="v-trust-pill">
                    <span
                      className="v-trust-icon"
                      style={{ background: t.bg, color: t.color }}
                      aria-hidden
                    >
                      {t.icon}
                    </span>
                    <div>
                      <strong>{t.title}</strong>
                      <span>{t.body}</span>
                    </div>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* ── ROADMAP VISUAL ── */}
        <section className="v-section v-section-roadmap">
          <div className="container">
            <div className="v-section-head">
              <Reveal>
                <span className="eyebrow">Roadmap normativo</span>
              </Reveal>
              <Reveal delay={80}>
                <h2 className="typ-1">
                  La ventana para prepararse es <em>ahora</em>
                </h2>
              </Reveal>
            </div>

            <Reveal delay={200}>
              <div className="v-roadmap">
                {/* Línea de progreso horizontal */}
                <div className="v-rm-track" aria-hidden>
                  <div className="v-rm-track-fill" />
                </div>

                <div className="v-rm-nodes">
                  {ROADMAP.map((phase, i) => (
                    <div
                      key={phase.year}
                      className={`v-rm-node v-rm-${phase.status}`}
                      style={
                        {
                          "--rm-color": phase.color,
                          "--rm-glow": phase.glow,
                          "--rm-delay": `${i * 0.2}s`,
                        } as React.CSSProperties
                      }
                    >
                      {/* Nodo circular animado */}
                      <div className="v-rm-circle">
                        <div className="v-rm-ring" aria-hidden />
                        <div className="v-rm-dot-inner" aria-hidden />
                        {phase.status === "live" && <div className="v-rm-glow-ring" aria-hidden />}
                      </div>

                      {/* Año */}
                      <div className="v-rm-year">{phase.year}</div>

                      {/* Badge de estado */}
                      <div className="v-rm-badge">{phase.label}</div>

                      {/* Sectores */}
                      <div className="v-rm-sectors">
                        {phase.sectors.map((s) => (
                          <span key={s} className="v-rm-sector">
                            {s}
                          </span>
                        ))}
                      </div>

                      {/* Indicador EN VIGOR */}
                      {phase.status === "live" && (
                        <div className="v-rm-live-tag">
                          <span className="v-rm-live-dot" aria-hidden />
                          EN VIGOR
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </Reveal>

            <Reveal delay={500}>
              <p className="v-roadmap-note">
                Las marcas que piloten ahora evitarán la avalancha de 2027. Los retailers ya
                preguntan a proveedores por su preparación DPP.
              </p>
            </Reveal>
          </div>
        </section>

        {/* ── CTA ── */}
        <section className="v-section v-section-cta2">
          <div className="container">
            <div className="v-cta2">
              <Reveal>
                <div className="v-cta2-text">
                  <span className="eyebrow">Empieza ahora</span>
                  <h2 className="typ-1">
                    Baterías ya es obligatorio.
                    <br />
                    ¿Tu producto es el siguiente?
                  </h2>
                  <p>
                    Despliega con{" "}
                    <code className="mono" style={{ color: "var(--accent)" }}>
                      docker compose up
                    </code>
                    . Sin licencia, sin vendor lock-in. Apache 2.0.
                  </p>
                  <div className="v-cta2-actions">
                    <Link href="/wizard" className="btn btn-primary btn-lg">
                      Crear mi primer DPP →
                    </Link>
                    <a
                      href={REPO_URL}
                      target="_blank"
                      rel="noreferrer"
                      className="btn btn-ghost btn-lg"
                    >
                      Ver en GitHub
                    </a>
                  </div>
                </div>
              </Reveal>

              <Reveal delay={200}>
                <div className="v-cta2-visual">
                  {/* Mockup de un DPP card con QR */}
                  <div className="v-dpp-mock">
                    <div className="v-dpp-mock-header">
                      <div className="v-dpp-mock-badge">DPP Conforme</div>
                      <div className="v-dpp-mock-id">ES-BAT-2026-001</div>
                    </div>
                    <div className="v-dpp-mock-body">
                      <div className="v-dpp-mock-field">
                        <span className="v-dpp-mock-label">Producto</span>
                        <span className="v-dpp-mock-value">Batería Li-Ion 48V</span>
                      </div>
                      <div className="v-dpp-mock-field">
                        <span className="v-dpp-mock-label">Fabricante</span>
                        <span className="v-dpp-mock-value">TuEmpresa S.L.</span>
                      </div>
                      <div className="v-dpp-mock-field">
                        <span className="v-dpp-mock-label">Firma</span>
                        <span className="v-dpp-mock-value v-dpp-mock-sig">Ed25519 ✓</span>
                      </div>
                    </div>
                    <div className="v-dpp-mock-qr">
                      <svg viewBox="0 0 100 100" width="80" height="80" aria-label="QR code mockup">
                        <rect width="100" height="100" rx="8" fill="#fff" />
                        <g fill="#0a0a0a">
                          {/* QR corners */}
                          <rect x="8" y="8" width="24" height="24" rx="2" />
                          <rect x="12" y="12" width="16" height="16" rx="1" fill="#fff" />
                          <rect x="16" y="16" width="8" height="8" rx="1" fill="#0a0a0a" />
                          <rect x="68" y="8" width="24" height="24" rx="2" />
                          <rect x="72" y="12" width="16" height="16" rx="1" fill="#fff" />
                          <rect x="76" y="16" width="8" height="8" rx="1" fill="#0a0a0a" />
                          <rect x="8" y="68" width="24" height="24" rx="2" />
                          <rect x="12" y="72" width="16" height="16" rx="1" fill="#fff" />
                          <rect x="16" y="76" width="8" height="8" rx="1" fill="#0a0a0a" />
                          {/* QR data dots */}
                          <rect x="40" y="10" width="6" height="6" rx="1" />
                          <rect x="50" y="10" width="6" height="6" rx="1" />
                          <rect x="40" y="20" width="6" height="6" rx="1" />
                          <rect x="56" y="20" width="6" height="6" rx="1" />
                          <rect x="10" y="40" width="6" height="6" rx="1" />
                          <rect x="20" y="40" width="6" height="6" rx="1" />
                          <rect x="36" y="36" width="6" height="6" rx="1" />
                          <rect x="46" y="36" width="6" height="6" rx="1" />
                          <rect x="56" y="36" width="6" height="6" rx="1" />
                          <rect x="36" y="46" width="6" height="6" rx="1" />
                          <rect x="50" y="46" width="6" height="6" rx="1" />
                          <rect x="60" y="46" width="6" height="6" rx="1" />
                          <rect x="36" y="56" width="6" height="6" rx="1" />
                          <rect x="46" y="56" width="6" height="6" rx="1" />
                          <rect x="56" y="56" width="6" height="6" rx="1" />
                          <rect x="70" y="40" width="6" height="6" rx="1" />
                          <rect x="80" y="40" width="6" height="6" rx="1" />
                          <rect x="70" y="50" width="6" height="6" rx="1" />
                          <rect x="84" y="50" width="6" height="6" rx="1" />
                          <rect x="40" y="70" width="6" height="6" rx="1" />
                          <rect x="50" y="70" width="6" height="6" rx="1" />
                          <rect x="60" y="70" width="6" height="6" rx="1" />
                          <rect x="70" y="70" width="6" height="6" rx="1" />
                          <rect x="80" y="70" width="6" height="6" rx="1" />
                          <rect x="40" y="80" width="6" height="6" rx="1" />
                          <rect x="56" y="80" width="6" height="6" rx="1" />
                          <rect x="70" y="80" width="6" height="6" rx="1" />
                          <rect x="84" y="80" width="6" height="6" rx="1" />
                        </g>
                      </svg>
                      <span className="v-dpp-mock-qr-label">Escanea el DPP</span>
                    </div>
                    {/* Glow decorativo */}
                    <div className="v-dpp-mock-glow" aria-hidden />
                  </div>
                </div>
              </Reveal>
            </div>
          </div>
        </section>
      </main>

      <footer className="footer">
        <div className="container">
          <div className="footer-grid">
            <div>
              <div className="footer-brand">
                <div className="appbar-logo">
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M6 2h12a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z" />
                    <circle cx="12" cy="10" r="3" />
                    <path d="M7 17a5 5 0 0 1 10 0" />
                  </svg>
                </div>
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
