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
    return <p className="rounded-md bg-red-50 p-4 text-sm text-red-700">{error}</p>;
  }
  if (!verify) {
    return <p className="text-sm text-gray-500">Verificando contra el plugin…</p>;
  }

  const pct = Math.round(verify.completeness * 100);
  const barTone = pct >= 100 ? "bg-green-500" : pct >= 70 ? "bg-amber-500" : "bg-red-500";

  return (
    <div className="space-y-6">
      <section>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500">
          Completitud
        </h2>
        <div className="mt-2 h-3 w-full overflow-hidden rounded-full bg-gray-200">
          <div className={`h-full ${barTone} transition-all`} style={{ width: `${pct}%` }} />
        </div>
        <p className="mt-2 text-sm">
          {pct}% de campos obligatorios completados ·{" "}
          {verify.can_publish ? (
            <span className="font-semibold text-green-700">listo para publicar</span>
          ) : (
            <span className="font-semibold text-red-700">faltan campos críticos</span>
          )}
        </p>
      </section>

      {verify.missing_fields.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold">
            Campos faltantes ({verify.missing_fields.length})
          </h3>
          <ul className="mt-2 divide-y divide-gray-200 rounded-md border border-gray-200">
            {verify.missing_fields.map((m) => (
              <MissingRow key={m.field_id} miss={m} />
            ))}
          </ul>
        </section>
      )}

      {verify.warnings.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold">Advertencias ({verify.warnings.length})</h3>
          <ul className="mt-2 space-y-1">
            {verify.warnings.map((w, i) => (
              <WarningRow key={i} warning={w} />
            ))}
          </ul>
        </section>
      )}

      <div className="border-t border-gray-200 pt-4">
        <button
          type="button"
          onClick={continueToPublish}
          disabled={!verify.can_publish || pending}
          className="rounded-md bg-blue-600 px-6 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-gray-300"
        >
          {pending ? "Avanzando…" : "Continuar a publicar →"}
        </button>
        {!verify.can_publish && (
          <p className="mt-2 text-xs text-red-700">
            No se puede publicar: rellena los campos faltantes en el paso 3 (o sube documentos en el
            paso 4 para que el Recolector los verifique).
          </p>
        )}
      </div>
    </div>
  );
}

function MissingRow({ miss }: { miss: MissingField }) {
  const tone = miss.reason === "validation_failed" ? "text-amber-700" : "text-red-700";
  return (
    <li className="flex items-center justify-between gap-3 p-3 text-sm">
      <span className="font-mono text-xs">{miss.field_id}</span>
      <span className={`text-xs ${tone}`}>
        {miss.reason === "validation_failed" ? "Tipo inválido" : "Pendiente"}
      </span>
      {miss.citation && (
        <span className="text-right text-xs text-gray-500">
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
    <li className="rounded-md border-l-4 border-amber-400 bg-amber-50 p-2 text-xs text-amber-900">
      {warning.rule_id && <span className="font-mono">[{warning.rule_id}] </span>}
      {warning.message}
    </li>
  );
}
