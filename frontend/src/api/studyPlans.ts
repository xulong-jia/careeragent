import { requestJson } from "./client";
import type {
  StudyPlanGenerateRequest,
  StudyPlanGenerateResponse,
  StudyPlanListFilters,
  StudyPlanListResponse,
  StudyPlanRecord,
  StudyPlanStats,
  StudyTaskStatusUpdateRequest,
} from "../types/api";

function buildQuery(filters: Record<string, string | undefined>): string {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) {
      params.set(key, value);
    }
  });
  return params.toString();
}

export function generateStudyPlan(
  payload: StudyPlanGenerateRequest,
): Promise<StudyPlanGenerateResponse> {
  return requestJson<StudyPlanGenerateResponse>("/api/study-plans/generate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function listStudyPlans(
  filters: StudyPlanListFilters = {},
): Promise<StudyPlanListResponse> {
  const query = buildQuery({
    status: filters.status || undefined,
    target_role: filters.target_role,
    profile_id: filters.profile_id,
    match_report_id: filters.match_report_id,
  });
  return requestJson<StudyPlanListResponse>(
    query ? `/api/study-plans?${query}` : "/api/study-plans",
  );
}

export function getStudyPlan(studyPlanId: string): Promise<StudyPlanRecord> {
  return requestJson<StudyPlanRecord>(`/api/study-plans/${studyPlanId}`);
}

export function updateStudyPlanTaskStatus(
  studyPlanId: string,
  taskId: string,
  payload: StudyTaskStatusUpdateRequest,
): Promise<StudyPlanRecord> {
  return requestJson<StudyPlanRecord>(
    `/api/study-plans/${studyPlanId}/tasks/${taskId}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  );
}

export function getStudyPlanStats(): Promise<StudyPlanStats> {
  return requestJson<StudyPlanStats>("/api/study-plans/stats");
}
