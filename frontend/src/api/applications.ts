import { requestJson } from "./client";
import type {
  ApplicationCreatePayload,
  ApplicationFilters,
  ApplicationRecord,
  ApplicationReflectionPayload,
  ApplicationStats,
  ApplicationStatusHistoryRecord,
  ApplicationUpdatePayload,
  ListResponse,
} from "../types/api";

export function createApplication(
  payload: ApplicationCreatePayload,
): Promise<ApplicationRecord> {
  return requestJson<ApplicationRecord>("/api/applications", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function listApplications(
  filters: ApplicationFilters = {},
): Promise<ListResponse<ApplicationRecord>> {
  const params = new URLSearchParams();
  if (filters.status) {
    params.set("status", filters.status);
  }
  if (filters.company) {
    params.set("company", filters.company);
  }
  if (filters.roleCategory) {
    params.set("role_category", filters.roleCategory);
  }
  if (filters.resumeVersionId) {
    params.set("resume_version_id", filters.resumeVersionId);
  }
  if (filters.jdId) {
    params.set("jd_id", filters.jdId);
  }
  if (filters.matchReportId) {
    params.set("match_report_id", filters.matchReportId);
  }
  if (filters.agentRunId) {
    params.set("agent_run_id", filters.agentRunId);
  }
  if (filters.priority) {
    params.set("priority", filters.priority);
  }
  if (filters.applyDateFrom) {
    params.set("apply_date_from", filters.applyDateFrom);
  }
  if (filters.applyDateTo) {
    params.set("apply_date_to", filters.applyDateTo);
  }
  if (filters.nextStepDateFrom) {
    params.set("next_step_date_from", filters.nextStepDateFrom);
  }
  if (filters.nextStepDateTo) {
    params.set("next_step_date_to", filters.nextStepDateTo);
  }
  const query = params.toString();
  return requestJson<ListResponse<ApplicationRecord>>(
    query ? `/api/applications?${query}` : "/api/applications",
  );
}

export function getApplication(
  applicationId: string,
): Promise<ApplicationRecord> {
  return requestJson<ApplicationRecord>(`/api/applications/${applicationId}`);
}

export function updateApplication(
  applicationId: string,
  payload: ApplicationUpdatePayload,
): Promise<ApplicationRecord> {
  return requestJson<ApplicationRecord>(`/api/applications/${applicationId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function updateApplicationReflection(
  applicationId: string,
  payload: ApplicationReflectionPayload,
): Promise<ApplicationRecord> {
  return requestJson<ApplicationRecord>(
    `/api/applications/${applicationId}/reflection`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  );
}

export function listApplicationStatusHistory(
  applicationId: string,
): Promise<ListResponse<ApplicationStatusHistoryRecord>> {
  return requestJson<ListResponse<ApplicationStatusHistoryRecord>>(
    `/api/applications/${applicationId}/status-history`,
  );
}

export function getApplicationStats(): Promise<ApplicationStats> {
  return requestJson<ApplicationStats>("/api/applications/stats");
}
