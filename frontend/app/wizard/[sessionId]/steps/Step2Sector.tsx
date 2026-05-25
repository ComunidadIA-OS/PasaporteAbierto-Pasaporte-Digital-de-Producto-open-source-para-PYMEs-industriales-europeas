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

import {
  ApiError,
  api,
  type Citation,
  type ClassifyResponse,
  type PluginSummary,
  type SessionState,
} from "@/app/lib/api";

const CONFIDENCE_THRESHOLD = 0.7;

export function Step2Sector({
  session,
  onSessionChange,
}: {
  session: SessionState;
  onSessionChange: (s: SessionState) => void;
}) {
  const [pluginCatalog, setPluginCatalog] = useState<PluginSummary[]>([]);
  const [lastCitation, setLastCitation] = useState<Citation | null>(
    session.classification_citation,
  );
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

  function runClassify() {
    setError(null);
    startTransition(async () => {
      try {
        const r: ClassifyResponse = await api.classify(session.session_id);
        setLastCitation(r.citation);
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
        const updated = await api.overrideClassification(session.session_id, {
          sector,
          plugin,
          reason,
        });
        setOverrideOpen(false);
        setLastCitation(null); // override no garantiza cita previa
        onSessionChange(updated);
      } catch (err) {
        setError(
          err instanceof ApiError
            ? `Error ${err.status} al guardar override.`
            : "Override falló.",
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
    <div className="space-y-6">
      {!hasSector ? (
        <NoClassification onClassify={runClassify} pending={pending} />
      ) : (
        <ClassificationBadge
          sector={session.sector!}
          confidence={session.classification_confidence ?? 0}
          citation={lastCitation}
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
        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => setOverrideOpen(true)}
            disabled={pending}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cambiar manualmente
          </button>
          {hasSector && !requiresReview && (
            <button
              type="button"
              onClick={continueToStep3}
              disabled={pending}
              className="rounded-md bg-blue-600 px-6 py-2 text-sm font-semibold text-white disabled:bg-gray-300"
            >
              Continuar al paso 3 →
            </button>
          )}
        </div>
      )}

      {error && (
        <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error}
        </p>
      )}
    </div>
  );
}

function NoClassification({
  onClassify,
  pending,
}: {
  onClassify: () => void;
  pending: boolean;
}) {
  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-6">
      <h2 className="text-lg font-semibold text-blue-900">Clasificar el producto</h2>
      <p className="mt-1 text-sm text-blue-800">
        El sistema identificará el sector ESPR aplicable a partir de la descripción
        del paso 1 y citará el reglamento que lo justifica.
      </p>
      <button
        type="button"
        onClick={onClassify}
        disabled={pending}
        className="mt-4 rounded-md bg-blue-600 px-5 py-2 text-sm font-semibold text-white disabled:bg-gray-300"
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
  const tone =
    confidence >= 0.85
      ? "border-green-300 bg-green-50 text-green-900"
      : confidence >= CONFIDENCE_THRESHOLD
        ? "border-amber-300 bg-amber-50 text-amber-900"
        : "border-red-300 bg-red-50 text-red-900";

  return (
    <div className={`rounded-lg border p-6 ${tone}`}>
      <p className="text-xs uppercase tracking-wider opacity-70">Sector clasificado</p>
      <h2 className="mt-1 text-2xl font-bold capitalize">{sector}</h2>
      <p className="mt-1 text-sm">Confianza · {pct}%</p>

      {citation && (
        <p className="mt-3 text-sm">
          Justificado por{" "}
          {citation.url ? (
            <a
              href={citation.url}
              target="_blank"
              rel="noreferrer"
              className="font-semibold underline"
            >
              {citation.regulation}, {citation.article}
            </a>
          ) : (
            <span className="font-semibold">
              {citation.regulation}, {citation.article}
            </span>
          )}
        </p>
      )}
    </div>
  );
}

function ReviewWarning() {
  return (
    <div
      role="alert"
      className="rounded-md border-l-4 border-amber-500 bg-amber-50 p-4 text-sm text-amber-900"
    >
      <strong className="font-semibold">Revisa la clasificación.</strong> La confianza es
      inferior al 70%. Confirma manualmente que el sector es correcto antes de continuar.
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
      className="space-y-3 rounded-lg border border-gray-300 bg-white p-5"
      onSubmit={(e) => {
        e.preventDefault();
        if (!isValid || pending) return;
        onSubmit(sector, sector, reason.trim());
      }}
    >
      <h3 className="text-sm font-semibold">Override manual del sector</h3>

      <label htmlFor="override-sector" className="block">
        <span className="text-xs text-gray-600">Sector correcto</span>
        <select
          id="override-sector"
          value={sector}
          onChange={(e) => setSector(e.target.value)}
          className="mt-1 w-full rounded-md border border-gray-300 p-2 text-sm"
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
          <span className="mt-1 block text-xs text-gray-500">
            Actual: <code className="font-mono">{currentSector}</code>
          </span>
        )}
      </label>

      <label htmlFor="override-reason" className="block">
        <span className="text-xs text-gray-600">Motivo (mínimo 10 caracteres)</span>
        <textarea
          id="override-reason"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={3}
          className="mt-1 w-full rounded-md border border-gray-300 p-2 text-sm"
          placeholder="Ej.: el clasificador confundió mi tejido técnico con una batería."
          disabled={pending}
        />
      </label>

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={!isValid || pending}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white disabled:bg-gray-300"
        >
          {pending ? "Guardando…" : "Guardar override"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={pending}
          className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
