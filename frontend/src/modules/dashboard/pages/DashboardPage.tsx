// Dashboard del usuario (ADR-0004): es lo que se ve tras iniciar sesión.
// Muestra métricas de sus DPP (total / en curso / finalizados / tasa) y un
// desplegable para entrar a sus productos en curso y finalizados.
//
// Server Component — el fetch reenvía la cookie de sesión. Si la cookie es
// inválida/caducada (pasó el proxy pero el backend la rechaza), va a /login.

import Link from "next/link";
import { redirect } from "next/navigation";

import { ApiError } from "@/core/errors";
import type { SessionSummary } from "@/core/responses";
import { Icon } from "@/core/ui/Icon";
import { isDemoMode } from "@/lib/demo-mode";
import { getCurrentUser } from "@/modules/auth/lib/auth-api";
import { LogoutButton } from "@/modules/dashboard/components/LogoutButton";
import { ProductBrowser } from "@/modules/dashboard/components/ProductBrowser";
import { SeedDemoButton } from "@/modules/dashboard/components/SeedDemoButton";
import { api } from "@/modules/wizard/lib/wizard-api";

async function loadDashboard(): Promise<{ email: string; sessions: SessionSummary[] }> {
  const user = await getCurrentUser();
  if (user === null) redirect("/login");
  const { sessions } = await api.listSessions();
  return { email: user.email, sessions };
}

function StatCard({
  variant,
  icon,
  fill,
  value,
  label,
  sub,
  rate,
}: {
  variant?: "progress" | "done";
  icon: string;
  fill?: boolean;
  value: string | number;
  label: string;
  sub?: string;
  rate?: number;
}) {
  return (
    <div className={`stat-card${variant ? ` is-${variant}` : ""}`}>
      <div className="stat-top">
        <span className="stat-icon">
          <Icon name={icon} size={20} fill={fill} />
        </span>
      </div>
      <div className="stat-num">{value}</div>
      <div className="stat-label">{label}</div>
      {sub && <div className="stat-sub">{sub}</div>}
      {rate !== undefined && (
        <div className="stat-rate-bar">
          <span style={{ width: `${rate}%` }} />
        </div>
      )}
    </div>
  );
}

export async function DashboardPage() {
  let data: { email: string; sessions: SessionSummary[] };
  try {
    data = await loadDashboard();
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) redirect("/login");
    throw err;
  }
  const { email, sessions } = data;

  const total = sessions.length;
  const done = sessions.filter((s) => s.published).length;
  const inProgress = total - done;
  const rate = total > 0 ? Math.round((done / total) * 100) : 0;

  return (
    <>
      <header className="appbar">
        <Link href="/" className="appbar-brand">
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
        </Link>
        <div className="appbar-spacer" />
        <nav className="appbar-nav">
          <span className="mono" style={{ fontSize: 12, color: "var(--text-muted)" }}>
            {email}
          </span>
          <LogoutButton />
        </nav>
      </header>

      <main className="dashboard fade-in">
        <div className="dash-head">
          <div>
            <div className="eyebrow">Mi cuenta</div>
            <h1 className="typ-2" style={{ marginTop: 10, marginBottom: 6 }}>
              Tus <em>pasaportes</em>
            </h1>
            <p className="muted" style={{ margin: 0 }}>
              Un vistazo a tus DPP. Reanuda los que están en curso o consulta los publicados.
            </p>
          </div>
          <div className="dash-actions">
            {isDemoMode && <SeedDemoButton />}
            <Link href="/wizard" className="btn btn-primary btn-lg">
              <Icon name="add" size={18} />
              Nuevo DPP
            </Link>
          </div>
        </div>

        <div className="stat-grid">
          <StatCard icon="inventory_2" value={total} label="TOTAL" sub="productos creados" />
          <StatCard
            variant="progress"
            icon="pending"
            value={inProgress}
            label="EN CURSO"
            sub="sin publicar aún"
          />
          <StatCard
            variant="done"
            icon="verified"
            fill
            value={done}
            label="FINALIZADOS"
            sub="publicados con QR"
          />
          <StatCard
            icon="trending_up"
            value={`${rate}%`}
            label="TASA DE FINALIZACIÓN"
            rate={rate}
          />
        </div>

        <ProductBrowser sessions={sessions} />
      </main>
    </>
  );
}
