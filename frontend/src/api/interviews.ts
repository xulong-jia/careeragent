import { requestJson } from "./client";
import type {
  InterviewAnswerCreateRequest,
  InterviewAnswerFilters,
  InterviewAnswerListResponse,
  InterviewAnswerRecord,
  InterviewAnswerScoreResponse,
  InterviewQuestionFilters,
  InterviewQuestionGenerateRequest,
  InterviewQuestionGenerateResponse,
  InterviewQuestionListResponse,
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

export function generateInterviewQuestions(
  payload: InterviewQuestionGenerateRequest,
): Promise<InterviewQuestionGenerateResponse> {
  return requestJson<InterviewQuestionGenerateResponse>(
    "/api/interviews/questions/generate",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  );
}

export function listInterviewQuestions(
  filters: InterviewQuestionFilters = {},
): Promise<InterviewQuestionListResponse> {
  const query = buildQuery({
    jd_id: filters.jd_id,
    resume_version_id: filters.resume_version_id,
    project_id: filters.project_id,
    question_type: filters.question_type || undefined,
    difficulty: filters.difficulty || undefined,
  });
  return requestJson<InterviewQuestionListResponse>(
    query ? `/api/interviews/questions?${query}` : "/api/interviews/questions",
  );
}

export function submitInterviewAnswer(
  payload: InterviewAnswerCreateRequest,
): Promise<InterviewAnswerRecord> {
  return requestJson<InterviewAnswerRecord>("/api/interviews/answers", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function listInterviewAnswers(
  filters: InterviewAnswerFilters = {},
): Promise<InterviewAnswerListResponse> {
  const query = buildQuery({
    question_id: filters.question_id,
    jd_id: filters.jd_id,
    resume_version_id: filters.resume_version_id,
    project_id: filters.project_id,
  });
  return requestJson<InterviewAnswerListResponse>(
    query ? `/api/interviews/answers?${query}` : "/api/interviews/answers",
  );
}

export function scoreInterviewAnswer(
  answerId: string,
): Promise<InterviewAnswerScoreResponse> {
  return requestJson<InterviewAnswerScoreResponse>(
    `/api/interviews/answers/${answerId}/score`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({}),
    },
  );
}
