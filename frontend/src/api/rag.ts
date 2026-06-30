import { requestJson } from "./client";
import type {
  ListResponse,
  RagAnswerRequest,
  RagAnswerResult,
  RagAnswerRunFilters,
  RagAnswerRunRecord,
  RagChunkRecord,
  RagDocumentCreatePayload,
  RagDocumentIndexPayload,
  RagDocumentIndexResult,
  RagDocumentRecord,
  RagSearchRequest,
  RagSearchResult,
  RagStats,
} from "../types/api";

type RagChunkFilters = {
  docId?: string;
  sourceType?: string;
};

function buildAnswerRunQuery(filters: RagAnswerRunFilters = {}) {
  const params = new URLSearchParams();
  if (filters.grounded !== undefined && filters.grounded !== null) {
    params.set("grounded", String(filters.grounded));
  }
  if (filters.uncertainty) {
    params.set("uncertainty", filters.uncertainty);
  }
  if (filters.retrievalMode) {
    params.set("retrieval_mode", filters.retrievalMode);
  }
  return params.toString();
}

export function createRagDocument(
  payload: RagDocumentCreatePayload,
): Promise<RagDocumentRecord> {
  return requestJson<RagDocumentRecord>("/api/rag/documents", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function listRagDocuments(): Promise<ListResponse<RagDocumentRecord>> {
  return requestJson<ListResponse<RagDocumentRecord>>("/api/rag/documents");
}

export function getRagDocument(docId: string): Promise<RagDocumentRecord> {
  return requestJson<RagDocumentRecord>(`/api/rag/documents/${docId}`);
}

export function deleteRagDocument(
  docId: string,
): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>(`/api/rag/documents/${docId}`, {
    method: "DELETE",
  });
}

export function indexRagDocument(
  docId: string,
  payload: RagDocumentIndexPayload,
): Promise<RagDocumentIndexResult> {
  return requestJson<RagDocumentIndexResult>(`/api/rag/documents/${docId}/index`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function listRagChunks(
  filters: RagChunkFilters = {},
): Promise<ListResponse<RagChunkRecord>> {
  const params = new URLSearchParams();
  if (filters.docId) {
    params.set("doc_id", filters.docId);
  }
  if (filters.sourceType) {
    params.set("source_type", filters.sourceType);
  }
  const query = params.toString();
  return requestJson<ListResponse<RagChunkRecord>>(
    query ? `/api/rag/chunks?${query}` : "/api/rag/chunks",
  );
}

export function searchRag(payload: RagSearchRequest): Promise<RagSearchResult> {
  return requestJson<RagSearchResult>("/api/rag/search", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function answerRag(payload: RagAnswerRequest): Promise<RagAnswerResult> {
  return requestJson<RagAnswerResult>("/api/rag/answer", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function listRagAnswerRuns(
  filters: RagAnswerRunFilters = {},
): Promise<ListResponse<RagAnswerRunRecord>> {
  const query = buildAnswerRunQuery(filters);
  return requestJson<ListResponse<RagAnswerRunRecord>>(
    query ? `/api/rag/answers?${query}` : "/api/rag/answers",
  );
}

export function getRagAnswerRun(
  answerRunId: string,
): Promise<RagAnswerRunRecord> {
  return requestJson<RagAnswerRunRecord>(`/api/rag/answers/${answerRunId}`);
}

export function getRagStats(): Promise<RagStats> {
  return requestJson<RagStats>("/api/rag/stats");
}
