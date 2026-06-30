import { requestJson } from "./client";
import type {
  ListResponse,
  ResumeParseRequest,
  ResumeParseResponse,
  ResumeRecord,
  ResumeRiskCheckRequest,
  ResumeRiskCheckResponse,
  ResumeVersionClonePayload,
  ResumeVersionRecord,
  SaveResumeVersionRequest,
} from "../types/api";

export function uploadResume(file: File): Promise<ResumeRecord> {
  const formData = new FormData();
  formData.append("file", file);

  return requestJson<ResumeRecord>("/api/resumes/upload", {
    method: "POST",
    body: formData,
  });
}

export function listResumes(): Promise<ListResponse<ResumeRecord>> {
  return requestJson<ListResponse<ResumeRecord>>("/api/resumes");
}

export function deleteResume(
  resumeId: string,
): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>(`/api/resumes/${resumeId}`, {
    method: "DELETE",
  });
}

export function listResumeVersions(
  resumeId: string,
): Promise<ListResponse<ResumeVersionRecord>> {
  return requestJson<ListResponse<ResumeVersionRecord>>(
    `/api/resumes/${resumeId}/versions`,
  );
}

export function getResumeVersion(
  versionId: string,
): Promise<ResumeVersionRecord> {
  return requestJson<ResumeVersionRecord>(`/api/resume-versions/${versionId}`);
}

export function parseResume(
  resumeId: string,
  payload: ResumeParseRequest = {},
): Promise<ResumeParseResponse> {
  return requestJson<ResumeParseResponse>(`/api/resumes/${resumeId}/parse`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function riskCheckResume(
  resumeId: string,
  payload: ResumeRiskCheckRequest,
): Promise<ResumeRiskCheckResponse> {
  return requestJson<ResumeRiskCheckResponse>(
    `/api/resumes/${resumeId}/risk-check`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  );
}

export function saveResumeVersion(
  resumeId: string,
  payload: SaveResumeVersionRequest,
): Promise<ResumeVersionRecord> {
  return requestJson<ResumeVersionRecord>(`/api/resumes/${resumeId}/versions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function cloneResumeVersion(
  versionId: string,
  payload: ResumeVersionClonePayload,
): Promise<ResumeVersionRecord> {
  return requestJson<ResumeVersionRecord>(
    `/api/resume-versions/${versionId}/clone`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  );
}

export function archiveResumeVersion(
  versionId: string,
): Promise<ResumeVersionRecord> {
  return requestJson<ResumeVersionRecord>(
    `/api/resume-versions/${versionId}/archive`,
    {
      method: "PATCH",
    },
  );
}
