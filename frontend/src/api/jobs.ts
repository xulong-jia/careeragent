import { requestJson } from "./client";
import type { JobCreatePayload, JobRecord, ListResponse } from "../types/api";

export function createJob(payload: JobCreatePayload): Promise<JobRecord> {
  return requestJson<JobRecord>("/api/jobs", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function listJobs(): Promise<ListResponse<JobRecord>> {
  return requestJson<ListResponse<JobRecord>>("/api/jobs");
}
