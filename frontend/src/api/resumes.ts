import { requestJson } from "./client";
import type {
  ListResponse,
  ResumeRecord,
  ResumeVersionClonePayload,
  ResumeVersionRecord,
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
