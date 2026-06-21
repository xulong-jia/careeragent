import { requestJson } from "./client";
import type {
  AgentRunCreatePayload,
  AgentRunCreateResponse,
  AgentRunDetailResponse,
  AgentRunRecord,
  AgentRunStatus,
  AgentStepListResponse,
  ListResponse,
} from "../types/api";

type AgentRunListFilters = {
  workflowName?: string;
  status?: AgentRunStatus;
  limit?: number;
};

export function createAgentRun(
  payload: AgentRunCreatePayload,
): Promise<AgentRunCreateResponse> {
  return requestJson<AgentRunCreateResponse>("/api/agents/runs", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function listAgentRuns(
  filters: AgentRunListFilters = {},
): Promise<ListResponse<AgentRunRecord>> {
  const params = new URLSearchParams();
  if (filters.workflowName) {
    params.set("workflow_name", filters.workflowName);
  }
  if (filters.status) {
    params.set("status", filters.status);
  }
  if (filters.limit) {
    params.set("limit", String(filters.limit));
  }
  const query = params.toString();
  return requestJson<ListResponse<AgentRunRecord>>(
    query ? `/api/agents/runs?${query}` : "/api/agents/runs",
  );
}

export function getAgentRun(runId: string): Promise<AgentRunDetailResponse> {
  return requestJson<AgentRunDetailResponse>(`/api/agents/runs/${runId}`);
}

export function listAgentRunSteps(
  runId: string,
): Promise<AgentStepListResponse> {
  return requestJson<AgentStepListResponse>(`/api/agents/runs/${runId}/steps`);
}
