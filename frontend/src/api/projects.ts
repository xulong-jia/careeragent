import { requestJson } from "./client";
import type {
  ProjectCreateRequest,
  ProjectFilters,
  ProjectListResponse,
  ProjectRecord,
  ProjectRewriteRecord,
  ProjectRewriteRequest,
  ProjectUpdateRequest,
} from "../types/api";

export function createProject(
  payload: ProjectCreateRequest,
): Promise<ProjectRecord> {
  return requestJson<ProjectRecord>("/api/projects", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function listProjects(
  filters: ProjectFilters = {},
): Promise<ProjectListResponse> {
  const params = new URLSearchParams();
  if (filters.profileId) {
    params.set("profile_id", filters.profileId);
  }
  if (filters.resumeVersionId) {
    params.set("resume_version_id", filters.resumeVersionId);
  }
  if (filters.status) {
    params.set("status", filters.status);
  }
  const query = params.toString();
  return requestJson<ProjectListResponse>(
    query ? `/api/projects?${query}` : "/api/projects",
  );
}

export function getProject(projectId: string): Promise<ProjectRecord> {
  return requestJson<ProjectRecord>(`/api/projects/${projectId}`);
}

export function updateProject(
  projectId: string,
  payload: ProjectUpdateRequest,
): Promise<ProjectRecord> {
  return requestJson<ProjectRecord>(`/api/projects/${projectId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function runProjectRewrite(
  projectId: string,
  payload: ProjectRewriteRequest,
): Promise<ProjectRewriteRecord> {
  return requestJson<ProjectRewriteRecord>(`/api/projects/${projectId}/rewrite`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function getProjectRewrite(
  rewriteId: string,
): Promise<ProjectRewriteRecord> {
  return requestJson<ProjectRewriteRecord>(`/api/project-rewrites/${rewriteId}`);
}
