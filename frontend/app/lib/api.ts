// Cliente API tipado para el wizard (PR-0 conjunto).
//
// Estos tipos son espejo manual de backend/src/app/api/v1/schemas.py.
// Si cambia un schema, ambos lados deben actualizarse en el mismo PR.

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_V1 = `${API_BASE}/api/v1`;

// --- Tipos compartidos ------------------------------------------------------

export type Provenance = "verified" | "self_declared" | "required_pending";
export type AccessLevel = "public" | "legitimate_interest" | "authorities_only" | "individual";
export type DocType = "datasheet" | "certificate" | "lca" | "sds" | "ce_declaration";

export interface Citation {
  regulation: string;
  article: string;
  url: string | null;
}

export interface FieldValue {
  field_id: string;
  value: unknown;
  provenance: Provenance;
  confidence: number;
  source_document_id: number | null;
}

// --- Sesiones ---------------------------------------------------------------

export interface CreateSessionRequest {
  description: string;
}

export interface CreateSessionResponse {
  session_id: string;
  created_at: string;
}

export interface UpdateProgressRequest {
  step?: number;
  description?: string;
  bom?: Record<string, unknown>;
}

export interface SessionState {
  session_id: string;
  current_step: number;
  description: string | null;
  sector: string | null;
  plugin: string | null;
  classification_confidence: number | null;
  classification_citation: Citation | null;
  bom: Record<string, unknown>;
  extracted_fields: FieldValue[];
  created_at: string;
  updated_at: string;
}

// --- Clasificador (F3-01) ---------------------------------------------------

export interface ClassifyResponse {
  sector: string;
  plugin: string;
  confidence: number;
  citation: Citation | null;
  requires_review: boolean;
}

export interface ClassifyOverrideRequest {
  sector: string;
  plugin: string;
  reason: string;
}

// --- Plugins ----------------------------------------------------------------

export interface PluginSummary {
  name: string;
  regulation: string;
  description: string;
}

export interface PluginsListResponse {
  plugins: PluginSummary[];
}

export type FieldType = "string" | "number" | "integer" | "boolean" | "enum" | "repeater";

export interface PluginFieldDefinition {
  id: string;
  type: FieldType;
  required: boolean;
  citation: { regulation: string; article: string };
  access_level: AccessLevel;
  enum_values: string[] | null;
  validation: string | null;
}

export interface PluginRequiredDocument {
  type: DocType;
  mandatory: boolean;
  when: string | null;
}

export interface PluginDetail {
  name: string;
  regulation: string;
  version: string;
  description: string;
  identifier_scheme: "gs1_digital_link" | "iso_iec_15459";
  fields: PluginFieldDefinition[];
  required_documents: PluginRequiredDocument[];
}

// --- BOM (F4-03) ------------------------------------------------------------

export interface BomRequest {
  fields: Record<string, unknown>;
}

export interface BomValidationError {
  field_id: string;
  message: string;
}

export interface BomResponse {
  accepted: boolean;
  errors: BomValidationError[];
}

// --- Documentos (F4-04) -----------------------------------------------------

export interface RequiredDocumentSpec {
  doc_type: DocType;
  mandatory: boolean;
  citation: Citation | null;
  uploaded: boolean;
}

export interface UploadedDocument {
  id: number;
  doc_type: DocType;
  sha256: string;
  uploaded_at: string;
}

export interface DocumentsListResponse {
  required: RequiredDocumentSpec[];
  uploaded: UploadedDocument[];
}

export interface UploadDocumentResponse {
  document: UploadedDocument;
  deduplicated: boolean;
}

// --- Recolector SSE (F3-02 / F4-05) -----------------------------------------

export type ExtractEvent =
  | { event: "progress"; processed: number; total: number; current_document: string | null }
  | { event: "field_extracted"; field: FieldValue }
  | {
      event: "done";
      fields_total: number;
      fields_verified: number;
      fields_self_declared: number;
      fields_pending: number;
    }
  | { event: "error"; message: string; document_id: number | null };

// --- Verificador (F3-03) ----------------------------------------------------

export interface MissingField {
  field_id: string;
  citation: Citation | null;
  reason: string;
}

export interface VerifyWarning {
  field_id: string | null;
  message: string;
  rule_id: string | null;
}

export interface VerifyResponse {
  completeness: number;
  missing_fields: MissingField[];
  warnings: VerifyWarning[];
  can_publish: boolean;
}

// --- DPP (F4-06 / paso 7) ---------------------------------------------------

export interface DppResponse {
  gs1_uri: string;
  public_url: string;
  qr_png_url: string;
  qr_svg_url: string;
  signed: boolean;
  jsonld_url: string;
}

// --- Chat (F3-04) -----------------------------------------------------------

export interface ChatRequest {
  session_id: string;
  message: string;
}

export interface ChatFragment {
  cita: string;
  texto: string;
  score: number;
}

export interface ChatResponse {
  answer: string;
  citation: Citation | null;
  fragments: ChatFragment[];
}

// --- Cliente ----------------------------------------------------------------

class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly body: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_V1}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(`${init?.method ?? "GET"} ${path} → ${res.status}`, res.status, body);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

// `sessionId` viene de la URL pública; pasamos siempre por encodeURIComponent
// para evitar que un id raro (caracteres reservados, slashes) salga del path
// previsto y aterrice en otra ruta del API.
const sid = (sessionId: string): string => encodeURIComponent(sessionId);

export const api = {
  createSession(body: CreateSessionRequest): Promise<CreateSessionResponse> {
    return request("/sessions", { method: "POST", body: JSON.stringify(body) });
  },

  getSession(sessionId: string): Promise<SessionState> {
    return request(`/sessions/${sid(sessionId)}`);
  },

  updateProgress(sessionId: string, body: UpdateProgressRequest): Promise<SessionState> {
    return request(`/sessions/${sid(sessionId)}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  },

  classify(sessionId: string): Promise<ClassifyResponse> {
    return request(`/sessions/${sid(sessionId)}/classify`, { method: "POST" });
  },

  overrideClassification(sessionId: string, body: ClassifyOverrideRequest): Promise<SessionState> {
    return request(`/sessions/${sid(sessionId)}/classify/override`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  listPlugins(): Promise<PluginsListResponse> {
    return request("/plugins");
  },

  getPluginDetail(name: string): Promise<PluginDetail> {
    return request(`/plugins/${encodeURIComponent(name)}`);
  },

  putBom(sessionId: string, body: BomRequest): Promise<BomResponse> {
    return request(`/sessions/${sid(sessionId)}/bom`, {
      method: "PUT",
      body: JSON.stringify(body),
    });
  },

  listDocuments(sessionId: string): Promise<DocumentsListResponse> {
    return request(`/sessions/${sid(sessionId)}/documents`);
  },

  async uploadDocument(
    sessionId: string,
    file: File,
    docType: string,
  ): Promise<UploadDocumentResponse> {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(
      `${API_V1}/sessions/${sid(sessionId)}/documents?doc_type=${encodeURIComponent(docType)}`,
      { method: "POST", body: form },
    );
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(
        (body as Record<string, string>).detail ?? res.statusText,
        res.status,
        body,
      );
    }
    return (await res.json()) as UploadDocumentResponse;
  },

  verify(sessionId: string): Promise<VerifyResponse> {
    return request(`/sessions/${sid(sessionId)}/verify`);
  },

  generateDpp(sessionId: string): Promise<DppResponse> {
    return request(`/sessions/${sid(sessionId)}/dpp`, { method: "POST" });
  },

  chat(body: ChatRequest): Promise<ChatResponse> {
    return request("/chat", { method: "POST", body: JSON.stringify(body) });
  },

  // SSE del Recolector. NOTA F4-05: EventSource solo hace GET; al ser
  // /extract un POST, el caller debe usar fetch streaming con ReadableStream
  // o el endpoint cambiará a GET en F3-02. Esta helper queda como referencia.
  extractStreamUrl(sessionId: string): string {
    return `${API_V1}/sessions/${sid(sessionId)}/extract`;
  },
};

export { ApiError };
