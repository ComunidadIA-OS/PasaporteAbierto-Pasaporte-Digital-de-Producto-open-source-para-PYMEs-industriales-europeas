// Paso 2 del wizard: clasificación del sector + override manual.
//
// Estados:
//   - Sin clasificar (session.sector === null):
//       muestra botón "Clasificar ahora" → POST /classify
//   - Clasificado (session.sector !== null && !== "unknown"):
//       badge con sector + % confianza + cita normativa
//   - Unknown o confianza baja (<0.7):
//       aviso destacado "Revisa la clasificación"
//   - Override abierto:
//       form con select de plugin + textarea de motivo
//
// Toda variante permite "Cambiar manualmente" y, cuando hay sector
// válido (no unknown), "Continuar al paso 3".

"use client";

import { useEffect, useState, useTransition } from "react";

import { Icon } from "@/core/ui/Icon";
import {
  ApiError,
  api,
  type Citation,
  type PluginSummary,
  type SessionState,
} from "@/modules/wizard/lib/wizard-api";

const CONFIDENCE_THRESHOLD = 0.7;

export function Step2Sector({
  session,
  onSessionChange,
}: {
  session: SessionState;
  onSessionChange: (s: SessionState) => void;
}) {
  const [pluginCatalog, setPluginCatalog] = useState<PluginSummary[]>([]);
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [overrideOpen, setOverrideOpen] = useState(false);

  useEffect(() => {
    api
      .listPlugins()
      .then((r) => setPluginCatalog(r.plugins))
      .catch(() => setPluginCatalog([]));
  }, []);

  const hasSector = session.sector !== null && session.sector !== "unknown";
  const requiresReview =
    !hasSector || (session.classification_confidence ?? 0) < CONFIDENCE_THRESHOLD;

  // La cita viene siempre de session.classification_citation: el backend la
  // persiste en sessions.progress y _to_session_state la rehidrata. No
  // mantenemos un state local porque se desincronizaría al recargar la página
  // (la cita persistida llegaría como prop pero el useState ya estaría fijado
  // al primer valor del render inicial).
  const citation: Citation | null = session.classification_citation;

  function runClassify() {
    setError(null);
    startTransition(async () => {
      try {
        await api.classify(session.session_id);
        const next = await api.getSession(session.session_id);
        onSessionChange(next);
      } catch (err) {
        setError(
          err instanceof ApiError ? `Error ${err.status} al clasificar.` : "Clasificación falló.",
        );
      }
    });
  }

  function submitOverride(sector: string, plugin: string, reason: string) {
    setError(null);
    startTransition(async () => {
      try {
        // El override en backend borra progress["classification_citation"]
        // (no hay cita normativa que respalde una decisión humana del fabricante).
        const updated = await api.overrideClassification(session.session_id, {
          sector,
          plugin,
          reason,
        });
        setOverrideOpen(false);
        onSessionChange(updated);
      } catch (err) {
        setError(
          err instanceof ApiError ? `Error ${err.status} al guardar override.` : "Override falló.",
        );
      }
    });
  }

  function continueToStep3() {
    startTransition(async () => {
      const updated = await api.updateProgress(session.session_id, { step: 3 });
      onSessionChange(updated);
    });
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {!hasSector ? (
        <NoClassification onClassify={runClassify} pending={pending} />
      ) : (
        <ClassificationBadge
          sector={session.sector ?? ""}
          confidence={session.classification_confidence ?? 0}
          citation={citation}
        />
      )}

      {requiresReview && hasSector && <ReviewWarning />}

      {overrideOpen ? (
        <OverrideForm
          plugins={pluginCatalog}
          currentSector={session.sector}
          onCancel={() => setOverrideOpen(false)}
          onSubmit={submitOverride}
          pending={pending}
        />
      ) : (
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={() => setOverrideOpen(true)}
            disabled={pending}
            className="btn btn-secondary"
          >
            Cambiar manualmente
          </button>
          {hasSector && !requiresReview && (
            <button
              type="button"
              onClick={continueToStep3}
              disabled={pending}
              className="btn btn-primary btn-lg"
            >
              Continuar al paso 3
              <Icon name="arrow_forward" size={18} />
            </button>
          )}
        </div>
      )}

      {error && (
        <p role="alert" className="status-panel is-danger" style={{ margin: 0, padding: 14 }}>
          {error}
        </p>
      )}
    </div>
  );
}

function NoClassification({ onClassify, pending }: { onClassify: () => void; pending: boolean }) {
  return (
    <div className="status-panel">
      <h2 className="typ-2" style={{ margin: 0 }}>
        Clasificar el <em>producto</em>
      </h2>
      <p className="muted" style={{ marginTop: 8, marginBottom: 0 }}>
        El sistema identificará el sector ESPR aplicable a partir de la descripción del paso 1 y
        citará el reglamento que lo justifica.
      </p>
      <button
        type="button"
        onClick={onClassify}
        disabled={pending}
        className="btn btn-primary"
        style={{ marginTop: 16 }}
      >
        {pending ? "Clasificando…" : "Clasificar ahora"}
      </button>
    </div>
  );
}

function ClassificationBadge({
  sector,
  confidence,
  citation,
}: {
  sector: string;
  confidence: number;
  citation: Citation | null;
}) {
  const pct = Math.round(confidence * 100);
  const toneClass =
    confidence >= 0.85
      ? "is-success"
      : confidence >= CONFIDENCE_THRESHOLD
        ? "is-warn"
        : "is-danger";

  return (
    <div className={`status-panel ${toneClass}`}>
      <span className="eyebrow">Sector clasificado</span>
      <h2
        className="typ-1"
        style={{
          marginTop: 8,
          marginBottom: 0,
          textTransform: "capitalize",
          fontStyle: "italic",
        }}
      >
        {sector}
      </h2>
      <p style={{ marginTop: 8, marginBottom: 0 }}>
        Confianza · <strong className="mono">{pct}%</strong>
      </p>

      {citation && (
        <p style={{ marginTop: 16, marginBottom: 0, fontSize: 13 }}>
          Justificado por{" "}
          {citation.url ? (
            <a
              href={citation.url}
              target="_blank"
              rel="noreferrer"
              style={{ color: "var(--accent)", textDecoration: "underline" }}
            >
              {citation.regulation}, {citation.article}
            </a>
          ) : (
            <strong>
              {citation.regulation}, {citation.article}
            </strong>
          )}
        </p>
      )}
    </div>
  );
}

function ReviewWarning() {
  return (
    <div role="alert" className="status-panel is-warn">
      <strong>Revisa la clasificación.</strong> La confianza es inferior al 70%. Confirma
      manualmente que el sector es correcto antes de continuar.
    </div>
  );
}

function OverrideForm({
  plugins,
  currentSector,
  onCancel,
  onSubmit,
  pending,
}: {
  plugins: PluginSummary[];
  currentSector: string | null;
  onCancel: () => void;
  onSubmit: (sector: string, plugin: string, reason: string) => void;
  pending: boolean;
}) {
  const [sector, setSector] = useState(plugins[0]?.name ?? "");
  const [reason, setReason] = useState("");

  const isValid = sector.length > 0 && reason.trim().length >= 10;

  return (
    <form
      className="card"
      style={{ display: "flex", flexDirection: "column", gap: 16 }}
      onSubmit={(e) => {
        e.preventDefault();
        if (!isValid || pending) return;
        onSubmit(sector, sector, reason.trim());
      }}
    >
      <h3 className="typ-3" style={{ margin: 0 }}>
        Override manual del sector
      </h3>

      <label htmlFor="override-sector">
        <span className="eyebrow" style={{ display: "block", marginBottom: 6 }}>
          Sector correcto
        </span>
        <select
          id="override-sector"
          value={sector}
          onChange={(e) => setSector(e.target.value)}
          className="select"
          disabled={pending}
        >
          {plugins.length === 0 && <option value="">— sin plugins instalados —</option>}
          {plugins.map((p) => (
            <option key={p.name} value={p.name}>
              {p.name} ({p.regulation})
            </option>
          ))}
        </select>
        {currentSector && (
          <span
            className="mono"
            style={{ marginTop: 6, display: "block", fontSize: 11, color: "var(--text-muted)" }}
          >
            Actual: <code>{currentSector}</code>
          </span>
        )}
      </label>

      <label htmlFor="override-reason">
        <span className="eyebrow" style={{ display: "block", marginBottom: 6 }}>
          Motivo (mínimo 10 caracteres)
        </span>
        <textarea
          id="override-reason"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={3}
          className="textarea"
          placeholder="Ej.: el clasificador confundió mi tejido técnico con una batería."
          disabled={pending}
        />
      </label>

      <div style={{ display: "flex", gap: 12 }}>
        <button type="submit" disabled={!isValid || pending} className="btn btn-primary">
          {pending ? "Guardando…" : "Guardar override"}
        </button>
        <button type="button" onClick={onCancel} disabled={pending} className="btn btn-secondary">
          Cancelar
        </button>
      </div>
    </form>
  );
}
