import { requestJson } from "./client";
import type { ListResponse, MatchReport } from "../types/api";

export function runMatch(resumeId: string, jdId: string): Promise<MatchReport> {
  return requestJson<MatchReport>("/api/matches/run", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ resume_id: resumeId, jd_id: jdId }),
  });
}

export function listMatches(): Promise<ListResponse<MatchReport>> {
  return requestJson<ListResponse<MatchReport>>("/api/matches");
}
