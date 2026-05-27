// Página de acceso (ADR-0004): iniciar sesión o crear cuenta.
//
// El backend fija la cookie de sesión (httpOnly) en la respuesta; aquí solo
// redirigimos a `next` (o al panel) tras el éxito. No se guarda nada en local.

"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { ApiError, authApi } from "@/modules/auth/lib/auth-api";

type Mode = "login" | "register";

const MIN_PASSWORD = 8;

function messageForError(err: unknown, mode: Mode): string {
  if (err instanceof ApiError) {
    if (err.status === 401) return "Email o contraseña incorrectos.";
    if (err.status === 409) return "Ya existe una cuenta con ese email. Inicia sesión.";
    if (err.status === 403) return "El alta de cuentas está deshabilitada en esta instancia.";
    if (err.status === 422) return "Revisa el email y que la contraseña tenga al menos 8 caracteres.";
    return `Error ${err.status}. Inténtalo de nuevo.`;
  }
  return mode === "login"
    ? "No se pudo iniciar sesión. Revisa la conexión con el backend."
    : "No se pudo crear la cuenta. Revisa la conexión con el backend.";
}

export function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next") ?? "/panel";

  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const passwordTooShort = mode === "register" && password.length > 0 && password.length < MIN_PASSWORD;
  const canSubmit = email.trim().length > 0 && password.length > 0 && !passwordTooShort && !pending;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setPending(true);
    setError(null);
    try {
      const body = { email: email.trim(), password };
      if (mode === "login") {
        await authApi.login(body);
      } else {
        await authApi.register(body);
      }
      // La cookie ya está fijada por el backend; vamos al destino solicitado.
      router.replace(next);
      router.refresh();
    } catch (err) {
      setError(messageForError(err, mode));
      setPending(false);
    }
  }

  function switchMode(target: Mode) {
    setMode(target);
    setError(null);
  }

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
      </header>

      <main className="auth-shell fade-in">
        <div className="card auth-card">
          <div className="eyebrow">Acceso</div>
          <h1 className="typ-2" style={{ marginTop: 10, marginBottom: 4 }}>
            {mode === "login" ? (
              <>
                Inicia <em>sesión</em>
              </>
            ) : (
              <>
                Crea tu <em>cuenta</em>
              </>
            )}
          </h1>
          <p className="muted" style={{ marginTop: 0, fontSize: 14 }}>
            Tus conversaciones y los DPP que empieces quedan guardados en tu cuenta.
          </p>

          <div className="auth-tabs" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={mode === "login"}
              className={mode === "login" ? "is-active" : ""}
              onClick={() => switchMode("login")}
            >
              Iniciar sesión
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === "register"}
              className={mode === "register" ? "is-active" : ""}
              onClick={() => switchMode("register")}
            >
              Crear cuenta
            </button>
          </div>

          <form onSubmit={onSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <label className="field">
              <span className="eyebrow" style={{ display: "block", marginBottom: 6 }}>
                Email
              </span>
              <input
                type="email"
                className="input"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={pending}
                required
              />
            </label>

            <label className="field">
              <span className="eyebrow" style={{ display: "block", marginBottom: 6 }}>
                Contraseña
              </span>
              <input
                type="password"
                className="input"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={pending}
                required
              />
              {mode === "register" && (
                <span
                  className="mono"
                  style={{ marginTop: 6, display: "block", fontSize: 11, color: "var(--text-muted)" }}
                >
                  {passwordTooShort
                    ? `Mínimo ${MIN_PASSWORD} caracteres`
                    : "Mínimo 8 caracteres. Se cifra con scrypt; no se guarda en claro."}
                </span>
              )}
            </label>

            {error && (
              <p role="alert" className="status-panel is-danger" style={{ margin: 0, padding: 12 }}>
                {error}
              </p>
            )}

            <button type="submit" className="btn btn-primary btn-lg" disabled={!canSubmit}>
              {pending
                ? "Procesando…"
                : mode === "login"
                  ? "Entrar"
                  : "Crear cuenta y entrar"}
            </button>
          </form>
        </div>
      </main>
    </>
  );
}
