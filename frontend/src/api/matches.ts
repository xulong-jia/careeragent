import { requestJson } from "./client";
import type {
  ListResponse,
  MatchCompareRequest,
  MatchCompareResponse,
  MatchReport,
} from "../types/api";

type MatchListFilters = {
  jdId?: string;
  resumeVersionId?: string;
};

type MatchRunPayload = {
  jdId: string;
  resumeId?: string | null;
  resumeVersionId?: string | null;
};

export function runMatch({
  jdId,
  resumeId,
  resumeVersionId,
}: MatchRunPayload): Promise<MatchReport> {
  return requestJson<MatchReport>("/api/matches/run", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      jd_id: jdId,
      resume_id: resumeId ?? null,
      resume_version_id: resumeVersionId ?? null,
    }),
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

export function compareMatches(
  payload: MatchCompareRequest,
): Promise<MatchCompareResponse> {
  return requestJson<MatchCompareResponse>("/api/matches/compare", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}
