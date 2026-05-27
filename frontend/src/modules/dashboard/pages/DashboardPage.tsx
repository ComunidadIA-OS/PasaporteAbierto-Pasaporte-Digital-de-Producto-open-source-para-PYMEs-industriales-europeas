// Panel del usuario (ADR-0004): lista sus conversaciones y DPP empezados para
// reanudarlos. Server Component — el fetch reenvía la cookie de sesión.
//
// Si la cookie es inválida/caducada (pasó el middleware pero el backend la
// rechaza), redirigimos a /login.

import Link from "next/link";
import { redirect } from "next/navigation";

import { ApiError } from "@/core/errors";
import type { SessionSummary } from "@/core/responses";
import { getCurrentUser } from "@/modules/auth/lib/auth-api";
import { LogoutButton } from "@/modules/dashboard/components/LogoutButton";
import { api } from "@/modules/wizard/lib/wizard-api";

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("es-ES", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

async function loadDashboard(): Promise<{ email: string; sessions: SessionSummary[] }> {
  const user = await getCurrentUser();
  if (user === null) redirect("/login");
  const { sessions } = await api.listSessions();
  return { email: user.email, sessions };
}

export async function DashboardPage() {
  let data: { email: string; sessions: SessionSummary[] };
  try {
    data = await loadDashboard();
  } catch (err) {
    // 401 → cookie caducada entre middleware y backend; al login.
    if (err instanceof ApiError && err.status === 401) redirect("/login");
    throw err;
  }
  const { email, sessions } = data;

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
        <div
          style={{
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "space-between",
            gap: 16,
            flexWrap: "wrap",
          }}
        >
          <div>
            <div className="eyebrow">Mi cuenta</div>
            <h1 className="typ-2" style={{ marginTop: 10, marginBottom: 0 }}>
              Tus <em>pasaportes</em>
            </h1>
            <p className="muted" style={{ marginTop: 6 }}>
              Reanuda un DPP en curso o empieza uno nuevo.
            </p>
          </div>
          <Link href="/wizard" className="btn btn-primary btn-lg">
            Nuevo DPP
          </Link>
        </div>

        {sessions.length === 0 ? (
          <div className="card" style={{ marginTop: 28, textAlign: "center", padding: 40 }}>
            <p className="muted" style={{ margin: 0 }}>
              Todavía no has empezado ningún pasaporte. Pulsa <strong>Nuevo DPP</strong> para
              comenzar.
            </p>
          </div>
        ) : (
          <ul
            style={{
              listStyle: "none",
              padding: 0,
              margin: "28px 0 0",
              display: "flex",
              flexDirection: "column",
              gap: 12,
            }}
          >
            {sessions.map((s) => (
              <li key={s.session_id}>
                <Link
                  href={`/wizard/${s.session_id}`}
                  className="card dashboard-row"
                  style={{ display: "block", textDecoration: "none", color: "inherit" }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 16,
                      alignItems: "flex-start",
                    }}
                  >
                    <div style={{ minWidth: 0 }}>
                      <p
                        style={{
                          margin: 0,
                          fontWeight: 600,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {s.description?.trim() || "Sin descripción todavía"}
                      </p>
                      <p
                        className="mono"
                        style={{ margin: "6px 0 0", fontSize: 11, color: "var(--text-muted)" }}
                      >
                        {s.sector ? `${s.sector} · ` : ""}Paso {s.current_step} de 7 · actualizado{" "}
                        {formatDate(s.updated_at)}
                      </p>
                    </div>
                    <div style={{ display: "flex", gap: 6, flexShrink: 0, flexWrap: "wrap" }}>
                      {s.published ? (
                        <span className="badge badge-success">publicado</span>
                      ) : (
                        <span className="badge badge-warn">en curso</span>
                      )}
                      {s.has_chat && <span className="badge badge-neutral">con chat</span>}
                    </div>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </main>
    </>
  );
}
