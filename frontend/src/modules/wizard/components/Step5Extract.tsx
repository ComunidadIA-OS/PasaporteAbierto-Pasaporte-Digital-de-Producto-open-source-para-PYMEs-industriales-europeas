// Paso 5: extracción de campos con SSE (F4-05).
//
// Lanza POST /sessions/{id}/extract y consume el stream SSE con
// ReadableStream (no EventSource, porque es POST). Muestra progreso
// en tiempo real y tabla de campos con badges de provenance.

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Icon } from "@/core/ui/Icon";
import { API_V1 } from "@/lib/fetch";
import { resolveLabel, usePluginFields } from "@/modules/wizard/lib/field-labels";
import {
  api,
  type DocumentExcerptResponse,
  type SessionState,
} from "@/modules/wizard/lib/wizard-api";

type Provenance = "verified" | "self_declared" | "required_pending";

interface ExtractedField {
  field_id: string;
  value: unknown;
  provenance: Provenance;
  confidence: number;
  source_document_id: number | null;
}

interface ProgressState {
  processed: number;
  total: number;
  current_document: string | null;
}

interface DoneSummary {
  fields_total: number;
  fields_verified: number;
  fields_self_declared: number;
  fields_pending: number;
}

const PROVENANCE_BADGE: Record<Provenance, { className: string; label: string }> = {
  verified: { className: "badge badge-success", label: "verificado" },
  self_declared: { className: "badge badge-warn", label: "autodeclarado" },
  required_pending: { className: "badge badge-danger", label: "pendiente" },
};

// Formatea un valor extraído para mostrarlo legible. Algunos campos del plugin
// (sustancias peligrosas, materias primas) llegan como arrays de objetos: hay
// que aplanarlos en lugar de dejar que String() devuelva "[object Object]".
function formatValue(value: unknown): string {
  if (value == null) return "";
  if (Array.isArray(value)) {
    return value
      .map(formatValue)
      .filter(Boolean)
      .join(", ");
  }
  if (typeof value === "object") {
    const obj = value as Record<string, unknown>;
    for (const key of ["name", "label", "value", "substance", "material", "cas"]) {
      if (obj[key] != null) return formatValue(obj[key]);
    }
    return Object.values(obj)
      .map(formatValue)
      .filter(Boolean)
      .join(" · ");
  }
  return String(value);
}

export function Step5Extract({
  session,
  onSessionChange,
}: {
  session: SessionState;
  onSessionChange: (s: SessionState) => void;
}) {
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<ProgressState | null>(null);
  const [fields, setFields] = useState<ExtractedField[]>([]);
  const [done, setDone] = useState<DoneSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [excerpt, setExcerpt] = useState<DocumentExcerptResponse | null>(null);
  const [excerptLoading, setExcerptLoading] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const fieldsMap = usePluginFields(session.plugin);
  const excerptCloseRef = useRef<HTMLButtonElement>(null);
  const excerptOpenerRef = useRef<HTMLElement | null>(null);

  const showExcerpt = useCallback(
    async (field: ExtractedField, opener: HTMLElement) => {
      if (field.source_document_id == null) return;
      excerptOpenerRef.current = opener;
      setExcerptLoading(field.field_id);
      try {
        const res = await api.documentExcerpt(
          session.session_id,
          field.source_document_id,
          field.field_id,
        );
        setExcerpt(res);
      } catch {
        setError("No se pudo cargar el fragmento del PDF.");
      } finally {
        setExcerptLoading(null);
      }
    },
    [session.session_id],
  );

  // Gestión de foco del modal de extracto
  useEffect(() => {
    if (excerpt) {
      excerptCloseRef.current?.focus();
    } else {
      (excerptOpenerRef.current as HTMLElement | null)?.focus();
    }
  }, [excerpt]);

  // Aborta el stream SSE al desmontar para no dejar fetch huérfanos ni
  // disparar setState sobre componente desmontado.
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      abortRef.current = null;
    };
  }, []);

  const startExtraction = useCallback(async () => {
    setRunning(true);
    setFields([]);
    setProgress(null);
    setDone(null);
    setError(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch(`${API_V1}/sessions/${session.session_id}/extract`, {
        method: "POST",
        // credentials: la cookie de sesión (auth) viaja con el stream SSE.
        credentials: "include",
        signal: controller.signal,
      });

      if (!res.ok) {
        const body = await res.text();
        setError(`Error ${res.status}: ${body}`);
        setRunning(false);
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        setError("El navegador no soporta streaming.");
        setRunning(false);
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done: streamDone, value } = await reader.read();
        if (streamDone) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const json = line.slice(6).trim();
          if (!json) continue;

          try {
            const evt = JSON.parse(json);
            switch (evt.event) {
              case "progress":
                setProgress({
                  processed: evt.processed,
                  total: evt.total,
                  current_document: evt.current_document,
                });
                break;
              case "field_extracted":
                setFields((prev) => [...prev, evt.field]);
                break;
              case "done":
                setDone({
                  fields_total: evt.fields_total,
                  fields_verified: evt.fields_verified,
                  fields_self_declared: evt.fields_self_declared,
                  fields_pending: evt.fields_pending,
                });
                break;
              case "error":
                setError(evt.message);
                break;
            }
          } catch {
            // línea SSE no parseable, ignorar
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setError("Error de conexión con el servidor.");
      }
    } finally {
      setRunning(false);
      abortRef.current = null;
    }
  }, [session.session_id]);

  async function onContinue() {
    try {
      const updated = await api.updateProgress(session.session_id, { step: 6 });
      onSessionChange(updated);
    } catch {
      setError("Error al avanzar al paso 6.");
    }
  }

  const pct =
    progress && progress.total > 0 ? Math.round((progress.processed / progress.total) * 100) : 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <p className="muted" style={{ margin: 0 }}>
        Extrae automáticamente los campos del DPP a partir de los documentos subidos. El sistema
        cruza la información de los PDFs con el BOM para determinar la procedencia de cada dato.
      </p>

      {/* Botón de inicio / re-extracción */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <button
          type="button"
          onClick={startExtraction}
          disabled={running}
          className="btn btn-primary btn-lg"
        >
          {running ? "Extrayendo…" : done ? "Re-extraer" : "Iniciar extracción"}
        </button>
        {running && progress?.current_document && (
          <span className="mono" style={{ fontSize: 11, color: "var(--text-muted)" }}>
            Procesando: {progress.current_document}
          </span>
        )}
      </div>

      {/* Barra de progreso */}
      {running && progress && (
        <div>
          <div
            className="bar"
            role="progressbar"
            aria-label="Progreso de extracción"
            aria-valuenow={progress.processed}
            aria-valuemin={0}
            aria-valuemax={progress.total}
            aria-valuetext={`${progress.processed} de ${progress.total} documentos procesados`}
          >
            <span style={{ width: `${pct}%` }} />
          </div>
          <p
            className="mono"
            style={{ marginTop: 6, fontSize: 11, color: "var(--text-muted)" }}
            aria-hidden="true"
          >
            {progress.processed} / {progress.total} documentos · {pct}%
          </p>
        </div>
      )}

      {/* Campos extraídos — rejilla de tarjetas (cada valor parte de línea, no
          desborda hacia el panel lateral). */}
      {fields.length > 0 && (
        <ul className="xf-grid" aria-label={`Campos extraídos del DPP — ${fields.length} campos`}>
          {fields.map((f) => {
            const badge = PROVENANCE_BADGE[f.provenance];
            const fieldLabel = fieldsMap ? resolveLabel(f.field_id, fieldsMap) : f.field_id;
            const formatted = formatValue(f.value);
            // F4-05 criterio 2: cada campo verified/self_declared enlaza al
            // fragmento del PDF fuente. required_pending no tiene fuente.
            const canShowSource =
              f.source_document_id != null && f.provenance !== "required_pending";
            return (
              <li key={f.field_id} className={`xf-card is-${f.provenance}`}>
                <div className="xf-card-head">
                  <span className="xf-label">{fieldLabel}</span>
                  <span className={badge.className}>{badge.label}</span>
                </div>
                <p className="xf-value">
                  {formatted || <span className="faint">—</span>}
                </p>
                <div className="xf-card-foot">
                  <span className="xf-conf mono">{Math.round(f.confidence * 100)}% confianza</span>
                  {canShowSource && (
                    <button
                      type="button"
                      onClick={(e) => showExcerpt(f, e.currentTarget)}
                      disabled={excerptLoading === f.field_id}
                      aria-label={`Ver fuente del campo ${fieldLabel}`}
                      className="xf-source"
                    >
                      {excerptLoading === f.field_id ? "Cargando…" : "Ver fuente"}
                    </button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {/* Modal del fragmento del PDF fuente (F4-05 criterio 2) */}
      {excerpt && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="excerpt-title"
          style={{
            position: "fixed",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "rgba(42, 36, 24, 0.32)",
            padding: 24,
            zIndex: 80,
          }}
        >
          <div
            className="card"
            style={{
              maxHeight: "80vh",
              width: "100%",
              maxWidth: 720,
              overflowY: "auto",
              boxShadow: "var(--shadow)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", gap: 16 }}>
              <div>
                <h3 id="excerpt-title" className="typ-3" style={{ margin: 0 }}>
                  Fragmento fuente ·{" "}
                  <code className="mono">
                    {fieldsMap ? resolveLabel(excerpt.field_id, fieldsMap) : excerpt.field_id}
                  </code>
                </h3>
                <p className="muted" style={{ marginTop: 6, marginBottom: 0, fontSize: 12 }}>
                  Valor extraído: <code className="mono">{excerpt.value}</code>
                  {excerpt.page_number != null && (
                    <span style={{ marginLeft: 8 }}>· página {excerpt.page_number}</span>
                  )}
                </p>
              </div>
              <button
                ref={excerptCloseRef}
                type="button"
                onClick={() => setExcerpt(null)}
                className="btn btn-ghost"
                aria-label="Cerrar fragmento fuente"
              >
                <Icon name="close" size={20} />
              </button>
            </div>
            {!excerpt.match_found && (
              <p
                className="status-panel is-warn"
                style={{ marginTop: 16, padding: 10, fontSize: 12 }}
              >
                El valor no aparece literal en el PDF (posiblemente formateado distinto o inferido).
                Mostramos un pantallazo del inicio del documento como contexto.
              </p>
            )}
            <pre
              className="mono"
              style={{
                marginTop: 16,
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                background: "var(--panel-2)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius)",
                padding: 14,
                fontSize: 12,
                lineHeight: 1.5,
              }}
            >
              {excerpt.excerpt}
            </pre>
          </div>
        </div>
      )}

      {/* Resumen final */}
      {done && (
        <div className="status-panel is-success">
          <h3 className="typ-3" style={{ margin: 0 }}>
            Extracción completada
          </h3>
          <div
            style={{
              marginTop: 12,
              display: "flex",
              gap: 16,
              flexWrap: "wrap",
              fontSize: 13,
            }}
          >
            <span
              className="provenance-verified"
              style={{ display: "inline-flex", alignItems: "center", gap: 5 }}
            >
              <Icon name="check_circle" size={15} fill />
              {done.fields_verified} verificados
            </span>
            <span
              className="provenance-self"
              style={{ display: "inline-flex", alignItems: "center", gap: 5 }}
            >
              <Icon name="contrast" size={15} fill />
              {done.fields_self_declared} autodeclarados
            </span>
            <span
              className="provenance-pending"
              style={{ display: "inline-flex", alignItems: "center", gap: 5 }}
            >
              <Icon name="cancel" size={15} fill />
              {done.fields_pending} pendientes
            </span>
          </div>
          {done.fields_pending > 0 && (
            <p className="muted" style={{ marginTop: 8, marginBottom: 0, fontSize: 12 }}>
              Puedes rellenar los campos pendientes a mano, subir otro PDF o consultar el chat
              (botón flotante).
            </p>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <p className="status-panel is-danger" style={{ margin: 0, padding: 14 }}>
          {error}
        </p>
      )}

      {/* Continuar */}
      {done && (
        <div>
          <button type="button" onClick={onContinue} className="btn btn-primary btn-lg">
            Continuar al paso 6
            <Icon name="arrow_forward" size={18} />
          </button>
        </div>
      )}
    </div>
  );
}
