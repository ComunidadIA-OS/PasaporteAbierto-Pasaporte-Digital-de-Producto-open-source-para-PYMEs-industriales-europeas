import { ApiError } from "@/core/errors";
import type {
  BomRequest,
  BomResponse,
  ChatHistoryResponse,
  ChatRequest,
  ChatResponse,
  ClassifyOverrideRequest,
  ClassifyResponse,
  CreateSessionRequest,
  CreateSessionResponse,
  DemoSampleResponse,
  DemoSeedDashboardResponse,
  DemoSeedDocumentsResponse,
  DocumentExcerptResponse,
  DocumentsListResponse,
  DppResponse,
  PluginDetail,
  PluginsListResponse,
  SessionListResponse,
  SessionState,
  UpdateProgressRequest,
  UploadDocumentResponse,
  VerifyResponse,
} from "@/core/responses";
import { API_V1, serverFetch } from "@/lib/fetch";

export { ApiError } from "@/core/errors";
// Re-export para ergonomía: los consumidores importan tipos y `api` del
// mismo módulo, igual que antes (solo cambia la ruta).
export * from "@/core/responses";

const sid = (sessionId: string): string => encodeURIComponent(sessionId);

export const api = {
  createSession(body: CreateSessionRequest): Promise<CreateSessionResponse> {
    return serverFetch("/sessions", { method: "POST", body: JSON.stringify(body) });
  },
  getSession(sessionId: string): Promise<SessionState> {
    return serverFetch(`/sessions/${sid(sessionId)}`);
  },
  listSessions(): Promise<SessionListResponse> {
    return serverFetch("/sessions");
  },
  updateProgress(sessionId: string, body: UpdateProgressRequest): Promise<SessionState> {
    return serverFetch(`/sessions/${sid(sessionId)}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  },
  classify(sessionId: string): Promise<ClassifyResponse> {
    return serverFetch(`/sessions/${sid(sessionId)}/classify`, { method: "POST" });
  },
  overrideClassification(sessionId: string, body: ClassifyOverrideRequest): Promise<SessionState> {
    return serverFetch(`/sessions/${sid(sessionId)}/classify/override`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  listPlugins(): Promise<PluginsListResponse> {
    return serverFetch("/plugins");
  },
  getPluginDetail(name: string): Promise<PluginDetail> {
    return serverFetch(`/plugins/${encodeURIComponent(name)}`);
  },
  putBom(sessionId: string, body: BomRequest): Promise<BomResponse> {
    return serverFetch(`/sessions/${sid(sessionId)}/bom`, {
      method: "PUT",
      body: JSON.stringify(body),
    });
  },
  listDocuments(sessionId: string): Promise<DocumentsListResponse> {
    return serverFetch(`/sessions/${sid(sessionId)}/documents`);
  },
  documentExcerpt(
    sessionId: string,
    docId: number,
    fieldId: string,
  ): Promise<DocumentExcerptResponse> {
    const qs = `?field_id=${encodeURIComponent(fieldId)}`;
    return serverFetch(`/sessions/${sid(sessionId)}/documents/${docId}/excerpt${qs}`);
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
      // credentials: incluye la cookie de sesión (auth) en la subida multipart.
      { method: "POST", body: form, credentials: "include" },
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
    return serverFetch(`/sessions/${sid(sessionId)}/verify`);
  },
  generateDpp(sessionId: string): Promise<DppResponse> {
    return serverFetch(`/sessions/${sid(sessionId)}/dpp`, { method: "POST" });
  },
  // Rehidrata un DPP ya publicado (QR + URL pública) al reentrar desde la
  // lista de finalizados. 404 (ApiError.status === 404) si aún no se publicó.
  getDpp(sessionId: string): Promise<DppResponse> {
    return serverFetch(`/sessions/${sid(sessionId)}/dpp`);
  },
  chat(body: ChatRequest): Promise<ChatResponse> {
    return serverFetch("/chat", { method: "POST", body: JSON.stringify(body) });
  },
  chatHistory(sessionId: string): Promise<ChatHistoryResponse> {
    return serverFetch(`/sessions/${sid(sessionId)}/chat`);
  },
  extractStreamUrl(sessionId: string): string {
    return `${API_V1}/sessions/${sid(sessionId)}/extract`;
  },
  getDemoSample(sector: string): Promise<DemoSampleResponse> {
    return serverFetch(`/demo/sample/${encodeURIComponent(sector)}`);
  },
  seedDemoDocuments(sessionId: string): Promise<DemoSeedDocumentsResponse> {
    return serverFetch(`/demo/sessions/${sid(sessionId)}/seed-documents`, { method: "POST" });
  },
  seedDemoDashboard(): Promise<DemoSeedDashboardResponse> {
    return serverFetch("/demo/seed-dashboard", { method: "POST" });
  },
};
