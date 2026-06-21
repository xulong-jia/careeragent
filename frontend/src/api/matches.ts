import { requestJson } from "./client";
import type { ListResponse, MatchReport } from "../types/api";

type MatchListFilters = {
  jdId?: string;
  resumeVersionId?: string;
};

export function runMatch(resumeId: string, jdId: string): Promise<MatchReport> {
  return requestJson<MatchReport>("/api/matches/run", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ resume_id: resumeId, jd_id: jdId }),
  });
}

export function listMatches(
  filters: MatchListFilters = {},
): Promise<ListResponse<MatchReport>> {
  const params = new URLSearchParams();
  if (filters.jdId) {
    params.set("jd_id", filters.jdId);
  }
  if (filters.resumeVersionId) {
    params.set("resume_version_id", filters.resumeVersionId);
  }
  const query = params.toString();
  return requestJson<ListResponse<MatchReport>>(
    query ? `/api/matches?${query}` : "/api/matches",
  );
}

export function getMatch(matchReportId: string): Promise<MatchReport> {
  return requestJson<MatchReport>(`/api/matches/${matchReportId}`);
}
