// Paso 6 del wizard: Verificador (F4-06).
//
// Llama GET /verify y muestra:
//   - Completitud (barra grande)
//   - Tabla de campos faltantes con cita normativa
//   - Tabla de warnings (cross_validations)
//   - Botón "Continuar a publicar" deshabilitado si !can_publish con motivo
//
// Si can_publish === true, el botón avanza a step 7 con PATCH.

"use client";

import { useEffect, useState, useTransition } from "react";

import {
  ApiError,
  api,
  type MissingField,
  type SessionState,
  type VerifyResponse,
  type VerifyWarning,
} from "@/app/lib/api";

export function Step6Verify({
  session,
  onSessionChange,
}: {
  session: SessionState;
  onSessionChange: (s: SessionState) => void;
}) {
  const [verify, setVerify] = useState<VerifyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  // Re-verifica cuando cambia session_id O updated_at: si el usuario vuelve al
  // paso 3 y modifica el BOM, el wizard actualiza updated_at y al regresar
  // aquí queremos refrescar el resultado (no mostrar el cacheado). updated_at
  // funciona como cache-buster intencional aunque no se referencie dentro.
  // biome-ignore lint/correctness/useExhaustiveDependencies: cache-buster intencional
  useEffect(() => {
    let cancelled = false;
    setError(null);
    setVerify(null);
    api
      .verify(session.session_id)
      .then((v) => {
        if (!cancelled) setVerify(v);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? `Error ${err.status} verificando` : "Verify falló");
      });
    return () => {
      cancelled = true;
    };
  }, [session.session_id, session.updated_at]);

  function continueToPublish() {
    if (!verify?.can_publish) return;
    startTransition(async () => {
      const updated = await api.updateProgress(session.session_id, { step: 7 });
      onSessionChange(updated);
    });
  }

  if (error) {
    return <p className="status-panel is-danger">{error}</p>;
  }
  if (!verify) {
    return <p className="muted">Verificando contra el plugin…</p>;
  }

  const pct = Math.round(verify.completeness * 100);
  const barClass = pct >= 100 ? "bar is-success" : pct >= 70 ? "bar is-warn" : "bar is-danger";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <section>
        <h2 className="eyebrow">Completitud</h2>
        <div className={barClass} style={{ marginTop: 12 }}>
          <span style={{ width: `${pct}%` }} />
        </div>
        <p style={{ marginTop: 12, marginBottom: 0 }}>
          {pct}% de campos obligatorios completados ·{" "}
          {verify.can_publish ? (
            <strong style={{ color: "var(--success)" }}>listo para publicar</strong>
          ) : (
            <strong style={{ color: "var(--danger)" }}>faltan campos críticos</strong>
          )}
        </p>
      </section>

      {verify.missing_fields.length > 0 && (
        <section>
          <h3 className="h-3" style={{ margin: 0 }}>
            Campos faltantes ({verify.missing_fields.length})
          </h3>
          <ul
            style={{
              marginTop: 12,
              padding: 0,
              listStyle: "none",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-lg)",
              background: "var(--panel)",
              overflow: "hidden",
            }}
          >
            {verify.missing_fields.map((m) => (
              <MissingRow key={m.field_id} miss={m} />
            ))}
          </ul>
        </section>
      )}

      {verify.warnings.length > 0 && (
        <section>
          <h3 className="h-3" style={{ margin: 0 }}>
            Advertencias ({verify.warnings.length})
          </h3>
          <ul style={{ marginTop: 12, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 8 }}>
            {verify.warnings.map((w, i) => (
              <WarningRow key={i} warning={w} />
            ))}
          </ul>
        </section>
      )}

      <div style={{ borderTop: "1px solid var(--border)", paddingTop: 16 }}>
        <button
          type="button"
          onClick={continueToPublish}
          disabled={!verify.can_publish || pending}
          className="btn btn-primary btn-lg"
        >
          {pending ? "Avanzando…" : "Continuar a publicar →"}
        </button>
        {!verify.can_publish && (
          <p style={{ marginTop: 8, fontSize: 12, color: "var(--danger)" }}>
            No se puede publicar: rellena los campos faltantes en el paso 3 (o sube documentos en
            el paso 4 para que el Recolector los verifique).
          </p>
        )}
      </div>
    </div>
  );
}

function MissingRow({ miss }: { miss: MissingField }) {
  const toneColor =
    miss.reason === "validation_failed" ? "var(--warn)" : "var(--danger)";
  return (
    <li
      style={{
        display: "flex",
        justifyContent: "space-between",
        gap: 12,
        padding: "12px 16px",
        borderTop: "1px solid var(--border)",
        fontSize: 13,
      }}
    >
      <span className="mono" style={{ fontSize: 12 }}>
        {miss.field_id}
      </span>
      <span className="mono" style={{ fontSize: 11, color: toneColor }}>
        {miss.reason === "validation_failed" ? "Tipo inválido" : "Pendiente"}
      </span>
      {miss.citation && (
        <span
          className="mono"
          style={{ fontSize: 11, color: "var(--text-muted)", textAlign: "right" }}
        >
          {miss.citation.regulation}
          <br />
          {miss.citation.article}
        </span>
      )}
    </li>
  );
}

function WarningRow({ warning }: { warning: VerifyWarning }) {
  return (
    <li
      style={{
        background: "var(--warn-soft)",
        borderLeft: "3px solid var(--warn)",
        borderRadius: "var(--radius-sm)",
        padding: "10px 12px",
        fontSize: 12,
        color: "var(--text)",
      }}
    >
      {warning.rule_id && (
        <span className="mono" style={{ color: "var(--warn)" }}>
          [{warning.rule_id}]{" "}
        </span>
      )}
      {warning.message}
    </li>
  );
}
