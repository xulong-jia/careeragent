import { requestJson } from "./client";
import type {
  BadCaseCreatePayload,
  BadCaseFilters,
  BadCaseRecord,
  BadCaseUpdatePayload,
  EvaluationCaseCreatePayload,
  EvaluationCaseFilters,
  EvaluationCaseRecord,
  EvaluationResultRecord,
  EvaluationRunCreatePayload,
  EvaluationRunFilters,
  EvaluationRunRecord,
  EvaluationRunSummary,
  EvaluationStats,
  ListResponse,
} from "../types/api";

const evaluationsPath = "/api/evaluations";
const badCasesPath = "/api/evaluations/bad-cases";

export function runEvaluation(
  payload: EvaluationRunCreatePayload = {},
): Promise<EvaluationRunSummary> {
  return requestJson<EvaluationRunSummary>(`${evaluationsPath}/runs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function listEvaluationRuns(
  filters: EvaluationRunFilters = {},
): Promise<ListResponse<EvaluationRunRecord>> {
  const params = new URLSearchParams();
  if (filters.module) {
    params.set("module", filters.module);
  }
  if (filters.datasetName) {
    params.set("dataset_name", filters.datasetName);
  }
  if (filters.limit) {
    params.set("limit", String(filters.limit));
  }
  const query = params.toString();
  return requestJson<ListResponse<EvaluationRunRecord>>(
    query ? `${evaluationsPath}/runs?${query}` : `${evaluationsPath}/runs`,
  );
}

export function getEvaluationRun(
  runId: string,
): Promise<EvaluationRunSummary> {
  return requestJson<EvaluationRunSummary>(`${evaluationsPath}/runs/${runId}`);
}

export function listEvaluationResults(
  runId: string,
): Promise<ListResponse<EvaluationResultRecord>> {
  return requestJson<ListResponse<EvaluationResultRecord>>(
    `${evaluationsPath}/runs/${runId}/results`,
  );
}

export function listEvaluationCases(
  filters: EvaluationCaseFilters = {},
): Promise<ListResponse<EvaluationCaseRecord>> {
  const params = new URLSearchParams();
  if (filters.module) {
    params.set("module", filters.module);
  }
  if (filters.datasetName) {
    params.set("dataset_name", filters.datasetName);
  }
  if (filters.sourceType) {
    params.set("source_type", filters.sourceType);
  }
  if (filters.limit) {
    params.set("limit", String(filters.limit));
  }
  const query = params.toString();
  return requestJson<ListResponse<EvaluationCaseRecord>>(
    query ? `${evaluationsPath}/cases?${query}` : `${evaluationsPath}/cases`,
  );
}

export function createEvaluationCase(
  payload: EvaluationCaseCreatePayload,
): Promise<EvaluationCaseRecord> {
  return requestJson<EvaluationCaseRecord>(`${evaluationsPath}/cases`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function createEvaluationCaseFromBadCase(
  badCaseId: string,
): Promise<EvaluationCaseRecord> {
  return requestJson<EvaluationCaseRecord>(
    `${evaluationsPath}/cases/from-bad-case/${badCaseId}`,
    {
      method: "POST",
    },
  );
}

export function getEvaluationStats(): Promise<EvaluationStats> {
  return requestJson<EvaluationStats>(`${evaluationsPath}/stats`);
}

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
