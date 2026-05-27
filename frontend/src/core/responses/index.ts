// Tipos espejo de backend/src/app/api/v1/schemas.py.
// Si cambia un schema, ambos lados se actualizan en el mismo PR.

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

// --- Autenticación (ADR-0004) -----------------------------------------------

export interface AuthCredentials {
  email: string;
  password: string;
}

export interface AuthUser {
  id: string;
  email: string;
  created_at: string;
}

// --- Sesiones ---------------------------------------------------------------

export interface CreateSessionRequest {
  description: string;
}

export interface SessionSummary {
  session_id: string;
  description: string | null;
  sector: string | null;
  plugin: string | null;
  current_step: number;
  has_chat: boolean;
  published: boolean;
  created_at: string;
  updated_at: string;
}

export interface SessionListResponse {
  sessions: SessionSummary[];
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
  label: string | null;
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

export interface DocumentExcerptResponse {
  document_id: number;
  field_id: string;
  value: string;
  excerpt: string;
  match_found: boolean;
  page_number: number | null;
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

export interface ChatHistoryMessage {
  role: "user" | "assistant";
  content: string;
  citation: Citation | null;
  created_at: string;
}

export interface ChatHistoryResponse {
  messages: ChatHistoryMessage[];
}

// --- Demo (opcional, solo si DEMO_MODE=true en backend) ---------------------

export interface DemoSampleResponse {
  sector: string;
  description: string;
  bom_fields: Record<string, unknown>;
  documents: { doc_type: DocType; title: string; embeds_count: number }[];
}

export interface DemoSeededDoc {
  id: number;
  doc_type: DocType;
  sha256: string;
  deduplicated: boolean;
  bytes: number;
}

export interface DemoSeedDocumentsResponse {
  seeded: DemoSeededDoc[];
}

export interface DemoSeedDashboardResponse {
  created_in_progress: number;
  created_published: number;
  total_user_sessions: number;
}
