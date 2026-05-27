// Paso 4: listado y subida de documentos (F4-04).
//
// Muestra documentos requeridos (derivados del plugin + BOM, nunca
// hardcodeados) y permite subir PDFs con drag & drop. Dedup por SHA-256.
// Límite 10 MB por fichero.

"use client";

import { useCallback, useEffect, useRef, useState, useTransition } from "react";
import { isDemoMode } from "@/lib/demo-mode";
import {
  ApiError,
  api,
  type DocumentsListResponse,
  type SessionState,
} from "@/modules/wizard/lib/wizard-api";

const MAX_SIZE = 10 * 1024 * 1024; // 10 MB

const DOC_LABELS: Record<string, string> = {
  datasheet: "Ficha técnica",
  certificate: "Certificado",
  lca: "Análisis de ciclo de vida (LCA)",
  sds: "Ficha de datos de seguridad (SDS)",
  ce_declaration: "Declaración CE",
};

export function Step4Documents({
  session,
  onSessionChange,
}: {
  session: SessionState;
  onSessionChange: (s: SessionState) => void;
}) {
  const [docs, setDocs] = useState<DocumentsListResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [uploadingType, setUploadingType] = useState<string | null>(null);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const [seedingDemo, setSeedingDemo] = useState(false);

  const refresh = useCallback(() => {
    api
      .listDocuments(session.session_id)
      .then(setDocs)
      .catch((e) => setLoadError(e instanceof ApiError ? e.message : "Error cargando documentos"));
  }, [session.session_id]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function handleUpload(file: File, docType: string) {
    if (file.size > MAX_SIZE) {
      setUploadMsg(`El fichero supera el límite de 10 MB.`);
      return;
    }
    setUploadingType(docType);
    setUploadMsg(null);
    try {
      const result = await api.uploadDocument(session.session_id, file, docType);
      if (result.deduplicated) {
        setUploadMsg("Este documento ya estaba subido (mismo hash SHA-256).");
      } else {
        setUploadMsg("Documento subido correctamente.");
      }
      refresh();
    } catch (err) {
      setUploadMsg(
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error subiendo documento.",
      );
    } finally {
      setUploadingType(null);
    }
  }

  async function seedDemoDocuments() {
    setSeedingDemo(true);
    setUploadMsg(null);
    try {
      const res = await api.seedDemoDocuments(session.session_id);
      const newCount = res.seeded.filter((s) => !s.deduplicated).length;
      const dedupCount = res.seeded.filter((s) => s.deduplicated).length;
      setUploadMsg(
        `✓ ${newCount} documentos generados${dedupCount > 0 ? ` (${dedupCount} ya existían)` : ""}`,
      );
      refresh();
    } catch (err) {
      setUploadMsg(
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error generando documentos de ejemplo",
      );
    } finally {
      setSeedingDemo(false);
    }
  }

  const allMandatoryUploaded =
    docs?.required.filter((r) => r.mandatory).every((r) => r.uploaded) ?? false;

  function onContinue() {
    if (!allMandatoryUploaded || pending) return;
    startTransition(async () => {
      try {
        const updated = await api.updateProgress(session.session_id, { step: 5 });
        onSessionChange(updated);
      } catch {
        setUploadMsg("Error al avanzar al paso 5.");
      }
    });
  }

  if (loadError) {
    return <p className="status-panel is-danger">{loadError}</p>;
  }

  if (!docs) {
    return <p className="muted">Cargando documentos requeridos…</p>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 16,
        }}
      >
        <p className="muted" style={{ margin: 0, flex: 1 }}>
          Sube los documentos requeridos para tu producto. La lista se genera a partir del plugin y
          del BOM que has introducido.
        </p>
        {isDemoMode && (
          <button
            type="button"
            onClick={seedDemoDocuments}
            disabled={seedingDemo || pending}
            className="btn btn-secondary"
            style={{ fontSize: 12, whiteSpace: "nowrap" }}
            title="Genera y sube 4 PDFs sintéticos como certificación de ejemplo"
          >
            {seedingDemo ? "Generando…" : "✨ Cargar PDFs de ejemplo"}
          </button>
        )}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {docs.required.map((req) => (
          <DocumentRow
            key={req.doc_type}
            docType={req.doc_type}
            label={DOC_LABELS[req.doc_type] ?? req.doc_type}
            mandatory={req.mandatory}
            uploaded={req.uploaded}
            citation={req.citation}
            uploading={uploadingType === req.doc_type}
            onUpload={(file) => handleUpload(file, req.doc_type)}
          />
        ))}
      </div>

      {docs.uploaded.length > 0 && (
        <div>
          <h3 className="eyebrow" style={{ marginBottom: 8 }}>
            Documentos subidos
          </h3>
          <ul
            style={{
              listStyle: "none",
              padding: 0,
              margin: 0,
              display: "flex",
              flexDirection: "column",
              gap: 6,
            }}
          >
            {docs.uploaded.map((u) => (
              <li
                key={u.id}
                style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}
              >
                <span
                  style={{
                    display: "inline-block",
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: "var(--success)",
                  }}
                />
                {DOC_LABELS[u.doc_type] ?? u.doc_type} —{" "}
                <code className="mono" style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  {u.sha256.slice(0, 12)}…
                </code>
              </li>
            ))}
          </ul>
        </div>
      )}

      {uploadMsg && (
        <p className="status-panel" style={{ margin: 0, padding: 12, fontSize: 13 }}>
          {uploadMsg}
        </p>
      )}

      <div>
        <button
          type="button"
          onClick={onContinue}
          disabled={!allMandatoryUploaded || pending}
          className="btn btn-primary btn-lg"
        >
          {pending ? "Avanzando…" : "Continuar al paso 5 →"}
        </button>
      </div>

      {!allMandatoryUploaded && (
        <p className="muted" style={{ fontSize: 12, margin: 0 }}>
          Sube todos los documentos obligatorios para continuar.
        </p>
      )}
    </div>
  );
}

function DocumentRow({
  docType: _docType,
  label,
  mandatory,
  uploaded,
  citation,
  uploading,
  onUpload,
}: {
  docType: string;
  label: string;
  mandatory: boolean;
  uploaded: boolean;
  citation: { regulation: string; article: string } | null;
  uploading: boolean;
  onUpload: (file: File) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) onUpload(file);
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
    if (inputRef.current) inputRef.current.value = "";
  }

  const className = `doc-card${uploaded ? " is-uploaded" : ""}${dragOver ? " is-drag" : ""}`;

  return (
    // biome-ignore lint/a11y/noStaticElementInteractions: drag-and-drop drop zone
    <section
      className={className}
      style={{ justifyContent: "space-between" }}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      <div style={{ flex: 1 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <span style={{ fontWeight: 500 }}>{label}</span>
          {mandatory && <span className="badge badge-warn">obligatorio</span>}
          {uploaded && <span className="badge badge-success">subido</span>}
        </div>
        {citation && (
          <p
            className="mono"
            style={{ margin: "6px 0 0", fontSize: 11, color: "var(--text-muted)" }}
          >
            {citation.regulation}, {citation.article}
          </p>
        )}
      </div>

      {!uploaded && (
        <div>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf"
            style={{ display: "none" }}
            onChange={handleFileChange}
          />
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
            className="btn btn-secondary"
            style={{ fontSize: 12, padding: "8px 14px" }}
          >
            {uploading ? "Subiendo…" : "Seleccionar PDF"}
          </button>
        </div>
      )}
    </section>
  );
}
