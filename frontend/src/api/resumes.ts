import { requestJson } from "./client";
import type { ListResponse, ResumeRecord } from "../types/api";

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
