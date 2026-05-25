// Paso 5: extracción de campos con SSE (F4-05).
//
// Lanza POST /sessions/{id}/extract y consume el stream SSE con
// ReadableStream (no EventSource, porque es POST). Muestra progreso
// en tiempo real y tabla de campos con badges de provenance.

"use client";

import { useCallback, useRef, useState } from "react";

import { api, type SessionState } from "@/app/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_V1 = `${API_BASE}/api/v1`;

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

const PROVENANCE_BADGE: Record<Provenance, { bg: string; text: string; label: string }> = {
  verified: { bg: "bg-green-100", text: "text-green-700", label: "verificado" },
  self_declared: { bg: "bg-orange-100", text: "text-orange-700", label: "autodeclarado" },
  required_pending: { bg: "bg-red-100", text: "text-red-700", label: "pendiente" },
};

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
  const abortRef = useRef<AbortController | null>(null);

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
    <div className="space-y-6">
      <p className="text-sm text-gray-600">
        Extrae automáticamente los campos del DPP a partir de los documentos subidos. El sistema
        cruza la información de los PDFs con el BOM para determinar la procedencia de cada dato.
      </p>

      {/* Botón de inicio / re-extracción */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={startExtraction}
          disabled={running}
          className="rounded-md bg-blue-600 px-6 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-gray-300"
        >
          {running ? "Extrayendo..." : done ? "Re-extraer" : "Iniciar extracción"}
        </button>
        {running && progress && (
          <span className="text-xs text-gray-500">
            {progress.current_document && `Procesando: ${progress.current_document}`}
          </span>
        )}
      </div>

      {/* Barra de progreso */}
      {running && progress && (
        <div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
            <div className="h-full bg-blue-600 transition-all" style={{ width: `${pct}%` }} />
          </div>
          <p className="mt-1 text-xs text-gray-500">
            {progress.processed} / {progress.total} documentos · {pct}%
          </p>
        </div>
      )}

      {/* Tabla de campos extraídos */}
      {fields.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-gray-200">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left font-medium text-gray-600">Campo</th>
                <th className="px-4 py-2 text-left font-medium text-gray-600">Valor</th>
                <th className="px-4 py-2 text-left font-medium text-gray-600">Procedencia</th>
                <th className="px-4 py-2 text-left font-medium text-gray-600">Confianza</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {fields.map((f) => {
                const badge = PROVENANCE_BADGE[f.provenance];
                return (
                  <tr key={f.field_id}>
                    <td className="px-4 py-2 font-mono text-xs">{f.field_id}</td>
                    <td className="px-4 py-2">
                      {f.value != null ? String(f.value) : <span className="text-gray-400">—</span>}
                    </td>
                    <td className="px-4 py-2">
                      <span
                        className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${badge.bg} ${badge.text}`}
                      >
                        {badge.label}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-xs text-gray-500">
                      {Math.round(f.confidence * 100)}%
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Resumen final */}
      {done && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4">
          <h3 className="text-sm font-semibold text-green-800">Extracción completada</h3>
          <div className="mt-2 flex gap-4 text-sm">
            <span className="text-green-700">✓ {done.fields_verified} verificados</span>
            <span className="text-orange-600">◐ {done.fields_self_declared} autodeclarados</span>
            <span className="text-red-600">✗ {done.fields_pending} pendientes</span>
          </div>
          {done.fields_pending > 0 && (
            <p className="mt-2 text-xs text-gray-600">
              Puedes rellenar los campos pendientes a mano, subir otro PDF o consultar al chat
              lateral.
            </p>
          )}
        </div>
      )}

      {/* Error */}
      {error && <p className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      {/* Continuar */}
      {done && (
        <button
          type="button"
          onClick={onContinue}
          className="rounded-md bg-blue-600 px-6 py-2 text-sm font-semibold text-white"
        >
          Continuar al paso 6 →
        </button>
      )}
    </div>
  );
}
