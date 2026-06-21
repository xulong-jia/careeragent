import { requestJson } from "./client";
import type {
  BadCaseCreatePayload,
  BadCaseFilters,
  BadCaseRecord,
  BadCaseUpdatePayload,
  ListResponse,
} from "../types/api";

const badCasesPath = "/api/evaluations/bad-cases";

export function createBadCase(
  payload: BadCaseCreatePayload,
): Promise<BadCaseRecord> {
  return requestJson<BadCaseRecord>(badCasesPath, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function listBadCases(
  filters: BadCaseFilters = {},
): Promise<ListResponse<BadCaseRecord>> {
  const params = new URLSearchParams();
  if (filters.sourceType) {
    params.set("source_type", filters.sourceType);
  }
  if (filters.sourceId) {
    params.set("source_id", filters.sourceId);
  }
  if (filters.category) {
    params.set("category", filters.category);
  }
  if (filters.severity) {
    params.set("severity", filters.severity);
  }
  if (filters.status) {
    params.set("status", filters.status);
  }
  if (filters.limit) {
    params.set("limit", String(filters.limit));
  }
  const query = params.toString();
  return requestJson<ListResponse<BadCaseRecord>>(
    query ? `${badCasesPath}?${query}` : badCasesPath,
  );
}

export function getBadCase(badCaseId: string): Promise<BadCaseRecord> {
  return requestJson<BadCaseRecord>(`${badCasesPath}/${badCaseId}`);
}

export function updateBadCase(
  badCaseId: string,
  payload: BadCaseUpdatePayload,
): Promise<BadCaseRecord> {
  return requestJson<BadCaseRecord>(`${badCasesPath}/${badCaseId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}
