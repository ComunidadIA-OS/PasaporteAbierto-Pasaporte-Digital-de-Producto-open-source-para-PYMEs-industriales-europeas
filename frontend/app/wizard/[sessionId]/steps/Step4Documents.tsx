// Paso 4: listado y subida de documentos (F4-04).
//
// Muestra documentos requeridos (derivados del plugin + BOM, nunca
// hardcodeados) y permite subir PDFs con drag & drop. Dedup por SHA-256.
// Límite 10 MB por fichero.

"use client";

import { useCallback, useEffect, useRef, useState, useTransition } from "react";

import { ApiError, api, type DocumentsListResponse, type SessionState } from "@/app/lib/api";

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
    return <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700 shadow">{loadError}</p>;
  }

  if (!docs) {
    return <p className="text-sm text-gray-500">Cargando documentos requeridos...</p>;
  }

  return (
    <div className="animate-fade-in space-y-6">
      <p className="text-sm text-gray-600">
        Sube los documentos requeridos para tu producto. La lista se genera a partir del plugin y
        del BOM que has introducido.
      </p>

      <div className="space-y-3">
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
          <h3 className="text-sm font-semibold text-gray-700">Documentos subidos</h3>
          <ul className="mt-2 space-y-1">
            {docs.uploaded.map((u) => (
              <li key={u.id} className="flex items-center gap-2 text-sm text-gray-600">
                <span className="inline-block h-2 w-2 rounded-full bg-green-500" />
                {DOC_LABELS[u.doc_type] ?? u.doc_type} —{" "}
                <code className="text-xs">{u.sha256.slice(0, 12)}...</code>
              </li>
            ))}
          </ul>
        </div>
      )}

      {uploadMsg && (
        <p className="rounded-xl bg-teal-50 p-3 text-sm text-teal-700 shadow">{uploadMsg}</p>
      )}

      <button
        type="button"
        onClick={onContinue}
        disabled={!allMandatoryUploaded || pending}
        className="rounded-xl bg-gradient-to-r from-teal-600 to-teal-500 px-6 py-2 text-sm font-semibold text-white shadow disabled:cursor-not-allowed disabled:bg-none disabled:bg-gray-300"
      >
        {pending ? "Avanzando..." : "Continuar al paso 5 →"}
      </button>

      {!allMandatoryUploaded && (
        <p className="text-xs text-gray-500">
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

  return (
    // biome-ignore lint/a11y/noStaticElementInteractions: drag-and-drop drop zone
    <section
      className={`flex items-center justify-between rounded-xl border p-4 shadow-sm ${
        dragOver
          ? "border-teal-400 bg-teal-50"
          : uploaded
            ? "border-green-300 bg-green-50"
            : "border-gray-200"
      }`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{label}</span>
          {mandatory && (
            <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
              obligatorio
            </span>
          )}
          {uploaded && (
            <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
              subido
            </span>
          )}
        </div>
        {citation && (
          <p className="mt-0.5 text-xs text-gray-500">
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
            className="hidden"
            onChange={handleFileChange}
          />
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
            className="rounded-xl border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 shadow-sm hover:bg-gray-50 disabled:opacity-50"
          >
            {uploading ? "Subiendo..." : "Seleccionar PDF"}
          </button>
        </div>
      )}
    </section>
  );
}
