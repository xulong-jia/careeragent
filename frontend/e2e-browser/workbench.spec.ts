import { expect, test, type Page, type Route } from "@playwright/test";

const now = "2026-06-01T10:00:00.000Z";
const forbiddenPrivateText = "PRIVATE_RAW_RESUME_BODY_SHOULD_NOT_RENDER";
const backendApiPattern = "http://localhost:8000/api/**";

const authUser = {
  id: "user_e2e",
  email: "browser-e2e@example.test",
  display_name: "Browser E2E",
  role: "owner",
  is_active: true,
};

const authWorkspace = {
  id: "workspace_e2e",
  name: "Synthetic Workspace",
  role: "owner",
};

const structuredResume = {
  basic_info: { name: "Redacted Candidate" },
  education: [],
  projects: [{ name: "CareerAgent synthetic project" }],
  experience: [],
  skills: { backend: ["Python", "FastAPI"], frontend: ["React"] },
  certificates: [],
  awards: [],
  risk_flags: [],
  parse_confidence: 0.92,
  evidence: [],
  warnings: [],
  parser_metadata: { mode: "browser_e2e" },
};

const resume = {
  resume_id: "resume_e2e",
  filename: "candidate-redacted.pdf",
  file_type: "pdf",
  parse_status: "parsed",
  raw_text_preview: "Redacted preview with Python, FastAPI, React and RAG evidence.",
  extraction_status: "completed",
  extraction_method: "deterministic",
  extraction_warnings: [],
  structured_resume: structuredResume,
  source_file: {
    filename: "candidate-redacted.pdf",
    file_type: "pdf",
    text_hash: "hash_e2e",
  },
  risk_flags: [],
  risk_report: {},
};

const resumeVersions = [
  {
    resume_version_id: "resume_version_e2e_a",
    resume_id: resume.resume_id,
    version_name: "Backend target",
    version_number: 1,
    target_role: "AI Application Engineer",
    raw_text_preview: resume.raw_text_preview,
    structured_resume: structuredResume,
    extraction_status: "completed",
    extraction_method: "deterministic",
    extraction_warnings: [],
    risk_flags: [],
    risk_report: {},
    status: "active",
    is_archived: false,
    created_at: now,
    archived_at: null,
  },
  {
    resume_version_id: "resume_version_e2e_b",
    resume_id: resume.resume_id,
    version_name: "RAG target",
    version_number: 2,
    target_role: "RAG Engineer",
    raw_text_preview: "Redacted RAG preview with retrieval and grounded answer experience.",
    structured_resume: structuredResume,
    extraction_status: "completed",
    extraction_method: "deterministic",
    extraction_warnings: [],
    risk_flags: [],
    risk_report: {},
    status: "active",
    is_archived: false,
    created_at: now,
    archived_at: null,
  },
];

const profile = {
  id: "profile_e2e",
  user_id: authUser.id,
  target_roles: ["AI Application Engineer"],
  target_industries: ["SaaS"],
  target_locations: ["Sydney"],
  skill_map: { backend: ["FastAPI"], ai: ["RAG"] },
  preferences: { remote: true },
  source_resume_version_id: resumeVersions[0].resume_version_id,
  created_at: now,
  updated_at: now,
};

const profileSummary = {
  profile_id: profile.id,
  completeness_score: 92,
  missing_fields: [],
  target_roles_count: 1,
  target_locations_count: 1,
  skill_categories_count: 2,
  source_resume_version_id: resumeVersions[0].resume_version_id,
  readiness_level: "ready",
};

const jobProfile = {
  job_profile_id: "job_profile_e2e",
  job_title: "AI Application Engineer",
  company: "Synthetic Company",
  location: "Sydney",
  role_category: "ai_engineer",
  required_skills: ["Python", "FastAPI", "RAG"],
  preferred_skills: ["React"],
  responsibilities: ["Build grounded AI workflows"],
  business_scenarios: ["career workflow automation"],
  hidden_requirements: [],
  interview_focus: ["RAG grounding", "API design"],
  risk_level: "medium",
  summary: "Synthetic JD profile.",
  parse_confidence: 0.91,
  evidence: [],
  warnings: [],
  parser_metadata: { mode: "browser_e2e" },
};

const job = {
  jd_id: "jd_e2e",
  company: "Synthetic Company",
  job_title: "AI Application Engineer",
  location: "Sydney",
  raw_text_preview: "Synthetic JD preview mentioning Python, FastAPI, RAG and React.",
  source_url: null,
  job_profile: jobProfile,
};

const matchReport = {
  match_report_id: "match_e2e",
  resume_id: resume.resume_id,
  resume_version_id: resumeVersions[0].resume_version_id,
  jd_id: job.jd_id,
  job_profile_id: jobProfile.job_profile_id,
  total_score: 86,
  dimension_scores: {
    skills: 90,
    project: 84,
    experience: 82,
    education: 78,
    communication: 80,
    risk_control: 88,
  },
  evidence: [
    {
      dimension: "skills",
      jd_requirement: "FastAPI",
      resume_signal: "FastAPI project",
      score_impact: "+",
      source: "resume_preview",
      confidence: 0.9,
    },
  ],
  strengths: ["FastAPI", "RAG"],
  gaps: ["React production depth"],
  rewrite_priorities: ["Tie project evidence to JD RAG requirements"],
  risk_flags: [],
  recommended_projects: [{ project_id: "project_e2e", reason: "RAG evidence" }],
  score_breakdown: { skills: 90 },
  scoring_method: "deterministic",
  confidence: 0.88,
  created_at: now,
};

const project = {
  id: "project_e2e",
  user_id: authUser.id,
  profile_id: profile.id,
  resume_version_id: resumeVersions[0].resume_version_id,
  name: "CareerAgent RAG Workbench",
  role: "Backend engineer",
  period: "2026",
  background: "Synthetic project facts only.",
  tech_stack: ["FastAPI", "React", "RAG"],
  responsibilities: ["Built API workflow"],
  results: ["Reduced manual comparison steps"],
  evidence: [{ label: "demo", preview: "safe summary" }],
  status: "active",
  created_at: now,
  updated_at: now,
};

const rewrite = {
  id: "rewrite_e2e",
  project_id: project.id,
  jd_id: job.jd_id,
  resume_version_id: resumeVersions[0].resume_version_id,
  match_report_id: matchReport.match_report_id,
  profile_id: profile.id,
  matched_points: [
    {
      skill: "FastAPI",
      source_field: "tech_stack",
      project_text: "Built API workflow",
      jd_requirement: "Build grounded AI workflows",
      match_type: "required_skill",
    },
  ],
  missing_points: [],
  evidence_required: [],
  rewritten_bullets: [
    {
      before: "Built API workflow",
      after: "Built FastAPI workflow with grounded RAG evidence paths.",
      reason: "Aligns project fact with JD requirement.",
      evidence_required: "",
      forbidden_changes: [],
      matched_jd_requirements: ["RAG"],
      missing_points: [],
      risk_level: "low",
      confidence: 0.86,
    },
  ],
  forbidden_changes: [],
  risk_flags: [],
  rewrite_strategy: "evidence_preserving",
  rewrite_method: "deterministic",
  confidence: 0.86,
  created_at: now,
};

const interviewQuestion = {
  id: "question_e2e",
  user_id: authUser.id,
  jd_id: job.jd_id,
  resume_version_id: resumeVersions[0].resume_version_id,
  project_id: project.id,
  project_rewrite_id: rewrite.id,
  question_type: "technical_depth",
  question: "How did you keep the RAG answer grounded?",
  expected_points: [{ point: "cite source refs" }],
  source_refs: [
    {
      source_type: "project",
      source_id: project.id,
      field: "responsibilities",
      label: "Project responsibility",
      preview: "Built API workflow",
    },
  ],
  difficulty: "medium",
  created_at: now,
};

const interviewAnswer = {
  id: "answer_e2e",
  question_id: interviewQuestion.id,
  user_id: authUser.id,
  answer_text_preview: "I used source refs and refused unsupported claims.",
  scores: { overall_average: 0.82, evidence: 0.9, clarity: 0.8 },
  feedback: "Grounded answer with clear evidence.",
  weakness_tags: ["structure"],
  created_at: now,
};

const studyPlan = {
  id: "study_plan_e2e",
  user_id: authUser.id,
  match_report_id: matchReport.match_report_id,
  profile_id: profile.id,
  project_rewrite_id: rewrite.id,
  target_role: "AI Application Engineer",
  source_refs: [
    {
      source_type: "match",
      source_id: matchReport.match_report_id,
      field: "gaps",
      label: "Match gap",
      preview: "React production depth",
    },
  ],
  phases: [
    {
      phase_id: "phase_1",
      phase: "Grounded RAG",
      goal: "Improve evidence handling.",
      resources: [{ title: "Internal rubric" }],
      deliverables: ["Citation checklist"],
      acceptance_criteria: ["No unsupported answer"],
      tasks: [
        {
          task_id: "task_1",
          title: "Practice citation review",
          description: "Review answers for source alignment.",
          source_gap: "RAG groundedness",
          priority: "high",
          status: "todo",
          due_hint: "this week",
          acceptance_criteria: ["Evidence refs present"],
          evidence_required: ["Review note"],
          source_refs: [],
        },
      ],
    },
  ],
  status: "active",
  created_at: now,
  updated_at: now,
};

const citation = {
  source_type: "knowledge",
  document_id: "doc_e2e",
  chunk_id: "chunk_e2e",
  title: "RAG Evaluation Notes",
  section: "grounding",
  label: "RAG Evaluation Notes / grounding",
  snippet: "Grounded answers cite source refs.",
  score: 0.91,
  metadata_preview: { topic: "rag" },
};

const ragSource = {
  doc_id: "doc_e2e",
  chunk_id: "chunk_e2e",
  title: "RAG Evaluation Notes",
  source_type: "note",
  section: "grounding",
  snippet: "Grounded answers cite source refs.",
  score: 0.91,
  metadata: { topic: "rag" },
  retrieval_mode: "hybrid",
  embedding_provider: "fake",
  embedding_model: "fake",
  vector_index_used: true,
  original_score: 0.7,
  rerank_score: 0.9,
  final_score: 0.91,
  reranker_mode: "fake",
  reranker_model: "fake",
};

const retrievalDebug = {
  retrieval_mode: "hybrid",
  schema_version: "browser_e2e",
  answer_mode: "grounded",
  run_config: {},
  vector_index_used: true,
  query_tokens: ["rag", "grounded"],
  candidate_count: 1,
  selected_chunk_ids: ["chunk_e2e"],
  scores: [0.91],
  top_k: 3,
  filters: {},
  insufficient_reason: null,
};

const ragAnswerRun = {
  answer_run_id: "rag_answer_e2e",
  question: "How should grounded RAG cite evidence?",
  filters: {},
  top_k: 3,
  retrieval_mode: "hybrid",
  answer: "Use source refs and citations for every material claim.",
  answer_type: "grounded",
  answer_mode: "grounded",
  grounded: true,
  uncertainty: "grounded",
  evidence_summary: ["Grounded answers cite source refs."],
  citations: [citation],
  source_refs: [
    {
      source_type: "rag_chunk",
      source_id: "chunk_e2e",
      document_id: "doc_e2e",
      chunk_id: "chunk_e2e",
      field: "snippet",
      label: "RAG Evaluation Notes",
      preview: "Grounded answers cite source refs.",
      score: 0.91,
    },
  ],
  retrieval_debug: retrievalDebug,
  created_at: now,
  updated_at: now,
};

const ragDocument = {
  doc_id: "doc_e2e",
  title: "RAG Evaluation Notes",
  source_type: "note",
  source_uri: null,
  raw_text_preview: "Safe preview: grounded answers cite source refs.",
  metadata: { topic: "rag" },
  index_status: "indexed",
  chunk_count: 1,
  created_at: now,
  updated_at: now,
};

const application = {
  application_id: "application_e2e",
  user_id: authUser.id,
  company: job.company,
  role_title: job.job_title,
  role_category: "ai_engineer",
  jd_id: job.jd_id,
  resume_version_id: resumeVersions[0].resume_version_id,
  match_report_id: matchReport.match_report_id,
  agent_run_id: "agent_e2e",
  status: "ready_to_apply",
  apply_date: null,
  next_step_date: "2026-06-15",
  source_url: null,
  location: "Sydney",
  priority: "high",
  notes: "Short safe summary only.",
  interview_notes: "Safe interview summary.",
  reflection: "Safe reflection.",
  interview_question_ids: [interviewQuestion.id],
  last_contact_date: null,
  tags: ["synthetic"],
  status_history: [],
  created_at: now,
  updated_at: now,
};

const agentNeedMoreInfo = {
  id: "agent_e2e",
  user_id: authUser.id,
  workflow_name: "job_application_preparation",
  status: "need_more_info",
  input_refs: { resume_version_id: resumeVersions[0].resume_version_id, jd_id: job.jd_id },
  output_refs: {},
  final_output_ref: {},
  run_config: { browser_e2e: true },
  final_summary: null,
  missing_slots: [{ slot: "application_id", reason: "Need application selection" }],
  questions: [{ question: "Select an application?" }],
  error_code: null,
  error_message: null,
  bad_case_id: null,
  bad_case_payload: {},
  retry_attempt: 0,
  created_at: now,
  updated_at: now,
  started_at: now,
  finished_at: null,
  duration_ms: null,
};

const agentFailed = {
  ...agentNeedMoreInfo,
  id: "agent_failed_e2e",
  status: "failed",
  error_code: "synthetic_failure",
  error_message: "Synthetic retry scenario.",
};

const agentStep = {
  id: "agent_step_e2e",
  run_id: agentNeedMoreInfo.id,
  step_name: "collect_refs",
  step_order: 1,
  attempt: 0,
  status: "need_more_info",
  input_refs: { jd_id: job.jd_id },
  output_refs: {},
  run_config: {},
  privacy_safe_payload: { jd_id: job.jd_id, raw_text: "[redacted]" },
  error_code: null,
  error_message: null,
  created_at: now,
  started_at: now,
  finished_at: null,
  duration_ms: null,
};

const badCase = {
  id: "bad_case_e2e",
  user_id: authUser.id,
  source_type: "rag_answer",
  source_id: ragAnswerRun.answer_run_id,
  category: "unsupported_answer",
  severity: "medium",
  title: "RAG answer needs citation review",
  description: "Safe summary without raw private text.",
  expected_behavior: "Every material claim cites evidence.",
  actual_behavior: "One claim lacked a source.",
  suggested_fix: "Require source refs.",
  root_cause: "Retrieval threshold too low.",
  fix_strategy: "Add regression case.",
  tags: ["browser-e2e"],
  added_to_eval_set: true,
  status: "reviewing",
  created_at: now,
  resolved_at: null,
  verified_at: null,
  regression_evaluation_run_id: "eval_run_e2e",
  regression_evaluation_case_id: "eval_case_e2e",
};

const evaluationRun = {
  id: "eval_run_e2e",
  name: "Browser E2E synthetic eval",
  module: "all",
  dataset_name: "synthetic_smoke_v1",
  status: "completed",
  metrics: { total_count: 2, passed_count: 2, failed_count: 0, pass_rate: 1 },
  run_config: { browser_e2e: true },
  started_at: now,
  finished_at: now,
  created_at: now,
};

const evaluationCase = {
  id: "eval_case_e2e",
  module: "rag",
  dataset_name: "synthetic_smoke_v1",
  case_name: "citation regression",
  input_payload: { question: "grounded RAG" },
  expected_output: { grounded: true },
  tags: ["browser-e2e"],
  source_type: "manual",
  bad_case_id: badCase.id,
  created_at: now,
  updated_at: now,
};

const evaluationResult = {
  id: "eval_result_e2e",
  run_id: evaluationRun.id,
  case_id: evaluationCase.id,
  module: "rag",
  status: "passed",
  actual_output: { grounded: true },
  expected_output: { grounded: true },
  passed: true,
  score: 1,
  error: null,
  created_at: now,
};

function list<T>(items: T[]) {
  return { items, total: items.length };
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

async function apiOk(route: Route, data: unknown) {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ data, request_id: "browser-e2e" }),
  });
}

async function apiError(route: Route, status: number, code: string, message: string) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify({
      error: { code, message, details: {} },
      request_id: "browser-e2e",
    }),
  });
}

function agentRun(status: string, id = "agent_e2e") {
  return {
    ...clone(agentNeedMoreInfo),
    id,
    status,
    final_summary:
      status === "completed"
        ? {
            total_score: 86,
            top_strengths: ["FastAPI"],
            top_gaps: ["React depth"],
            next_actions: ["Review application"],
          }
        : null,
    missing_slots: status === "need_more_info" ? agentNeedMoreInfo.missing_slots : null,
    questions: status === "need_more_info" ? agentNeedMoreInfo.questions : null,
    finished_at: status === "completed" || status === "cancelled" ? now : null,
  };
}

async function installMockApi(page: Page, options: { unauthorizedMe?: boolean } = {}) {
  const agentStatuses = new Map<string, string>([
    [agentNeedMoreInfo.id, "need_more_info"],
    [agentFailed.id, "failed"],
  ]);
  const currentAgentRun = (id: string) => {
    const status = agentStatuses.get(id) ?? "completed";
    if (id === agentFailed.id && status === "failed") {
      return agentFailed;
    }
    return agentRun(status, id);
  };

  await page.route(backendApiPattern, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();

    if (options.unauthorizedMe && path === "/api/auth/me") {
      await apiError(route, 401, "token_expired", "Session expired.");
      return;
    }

    if (path === "/api/auth/login" || path === "/api/auth/register") {
      await apiOk(route, {
        access_token: "browser-e2e-token",
        token_type: "bearer",
        expires_at: "2026-06-01T11:00:00.000Z",
        session_id: "session_e2e",
        user: authUser,
        workspace: authWorkspace,
      });
      return;
    }
    if (path === "/api/auth/me") {
      await apiOk(route, { user: authUser, workspace: authWorkspace });
      return;
    }
    if (path === "/api/auth/sessions") {
      await apiOk(route, list([
        {
          session_id: "session_e2e",
          device_label: "web session",
          issued_at: now,
          expires_at: "2026-06-01T11:00:00.000Z",
          revoked_at: null,
          revoke_reason: null,
          current: true,
        },
      ]));
      return;
    }
    if (path.startsWith("/api/auth/sessions/") && path.endsWith("/revoke")) {
      await apiOk(route, { status: "session_revoked", session_id: "session_e2e" });
      return;
    }
    if (path === "/api/auth/logout") {
      await apiOk(route, { status: "logged_out" });
      return;
    }

    if (path === "/api/profiles" && method === "GET") {
      await apiOk(route, list([profile]));
      return;
    }
    if (path === "/api/profiles" && method === "POST") {
      await apiOk(route, profile);
      return;
    }
    if (path === `/api/profiles/${profile.id}`) {
      await apiOk(route, profile);
      return;
    }
    if (path === `/api/profiles/${profile.id}/summary`) {
      await apiOk(route, profileSummary);
      return;
    }

    if (path === "/api/resumes" && method === "GET") {
      await apiOk(route, list([resume]));
      return;
    }
    if (path === "/api/resumes/upload") {
      await apiOk(route, resume);
      return;
    }
    if (path === `/api/resumes/${resume.resume_id}/versions`) {
      await apiOk(route, list(resumeVersions));
      return;
    }
    if (path.startsWith("/api/resume-versions/")) {
      await apiOk(route, resumeVersions[0]);
      return;
    }

    if (path === "/api/jobs" && method === "GET") {
      await apiOk(route, list([job]));
      return;
    }
    if (path === "/api/jobs" && method === "POST") {
      await apiOk(route, job);
      return;
    }

    if (path === "/api/matches" && method === "GET") {
      await apiOk(route, list([matchReport]));
      return;
    }
    if (path === "/api/matches/run") {
      await apiOk(route, matchReport);
      return;
    }
    if (path === "/api/matches/compare") {
      await apiOk(route, {
        compare_mode: "resume_versions",
        sort_key: "total_score",
        items: [
          {
            rank: 1,
            match_report_id: "match_e2e_b",
            resume_id: resume.resume_id,
            resume_version_id: resumeVersions[1].resume_version_id,
            jd_id: job.jd_id,
            total_score: 90,
            score_delta_from_top: 0,
            main_strengths: ["RAG"],
            main_gaps: [],
            risk_flags: [],
            dimension_scores: matchReport.dimension_scores,
          },
          {
            rank: 2,
            match_report_id: matchReport.match_report_id,
            resume_id: resume.resume_id,
            resume_version_id: resumeVersions[0].resume_version_id,
            jd_id: job.jd_id,
            total_score: matchReport.total_score,
            score_delta_from_top: -4,
            main_strengths: matchReport.strengths,
            main_gaps: matchReport.gaps,
            risk_flags: [],
            dimension_scores: matchReport.dimension_scores,
          },
        ],
      });
      return;
    }
    if (path.startsWith("/api/matches/")) {
      await apiOk(route, matchReport);
      return;
    }

    if (path === "/api/projects" && method === "GET") {
      await apiOk(route, list([project]));
      return;
    }
    if (path === "/api/projects" && method === "POST") {
      await apiOk(route, project);
      return;
    }
    if (path === `/api/projects/${project.id}/rewrite`) {
      await apiOk(route, rewrite);
      return;
    }
    if (path === `/api/projects/${project.id}`) {
      await apiOk(route, project);
      return;
    }

    if (path === "/api/interviews/stats") {
      await apiOk(route, {
        total_questions: 1,
        total_answers: 1,
        scored_answers: 1,
        latest_average_score: 0.82,
        latest_weakness_tags: ["structure"],
        by_question_type: { technical_depth: 1 },
        by_difficulty: { medium: 1 },
      });
      return;
    }
    if (path === "/api/interviews/questions/generate") {
      await apiOk(route, { questions: [interviewQuestion], warnings: [], need_more_info: [] });
      return;
    }
    if (path === "/api/interviews/questions") {
      await apiOk(route, list([interviewQuestion]));
      return;
    }
    if (path === "/api/interviews/answers" && method === "POST") {
      await apiOk(route, interviewAnswer);
      return;
    }
    if (path === "/api/interviews/answers") {
      await apiOk(route, list([interviewAnswer]));
      return;
    }
    if (path === `/api/interviews/answers/${interviewAnswer.id}/score`) {
      await apiOk(route, interviewAnswer);
      return;
    }

    if (path === "/api/study-plans/stats") {
      await apiOk(route, {
        total_plans: 1,
        active_plans: 1,
        completed_plans: 0,
        archived_plans: 0,
        pending_tasks: 1,
        blocked_tasks: 0,
        done_tasks: 0,
        in_progress_tasks: 0,
        skipped_tasks: 0,
        latest_plan_id: studyPlan.id,
        latest_target_role: studyPlan.target_role,
      });
      return;
    }
    if (path === "/api/study-plans") {
      await apiOk(route, list([studyPlan]));
      return;
    }
    if (path === "/api/study-plans/generate") {
      await apiOk(route, studyPlan);
      return;
    }
    if (path === `/api/study-plans/${studyPlan.id}`) {
      await apiOk(route, studyPlan);
      return;
    }
    if (path === `/api/study-plans/${studyPlan.id}/tasks/task_1`) {
      const updated = clone(studyPlan);
      updated.phases[0].tasks[0].status = "done";
      await apiOk(route, updated);
      return;
    }

    if (path === "/api/rag/stats") {
      await apiOk(route, {
        total_documents: 1,
        indexed_documents: 1,
        total_chunks: 1,
        total_answer_runs: 1,
        grounded_answer_runs: 1,
        ungrounded_answer_runs: 0,
        latest_answer_run_id: ragAnswerRun.answer_run_id,
        latest_answer_question_preview: ragAnswerRun.question,
        latest_answer_uncertainty: ragAnswerRun.uncertainty,
        latest_answer_created_at: now,
      });
      return;
    }
    if (path === "/api/rag/documents") {
      await apiOk(route, list([ragDocument]));
      return;
    }
    if (path === `/api/rag/documents/${ragDocument.doc_id}`) {
      await apiOk(route, ragDocument);
      return;
    }
    if (path === "/api/rag/chunks") {
      await apiOk(route, list([
        {
          chunk_id: "chunk_e2e",
          doc_id: ragDocument.doc_id,
          chunk_index: 0,
          section: "grounding",
          text_preview: "Grounded answers cite source refs.",
          token_count: 42,
          metadata: { topic: "rag" },
          embedding_id: "embedding_e2e",
          created_at: now,
        },
      ]));
      return;
    }
    if (path === "/api/rag/search") {
      await apiOk(route, {
        query: "grounded RAG",
        top_k: 3,
        sources: [ragSource],
        uncertainty: "grounded",
        retrieval_debug: retrievalDebug,
      });
      return;
    }
    if (path === "/api/rag/answer") {
      await apiOk(route, {
        ...ragAnswerRun,
        answer_run_id: ragAnswerRun.answer_run_id,
        sources: [ragSource],
        prompt_version: "browser_e2e",
        model_provider: "fake",
        model_name: "fake",
        groundedness_flags: [],
        refused_due_to_no_evidence: false,
        run_config: {},
        evidence_used: ["chunk_e2e"],
      });
      return;
    }
    if (path === "/api/rag/answers") {
      await apiOk(route, list([ragAnswerRun]));
      return;
    }
    if (path === `/api/rag/answers/${ragAnswerRun.answer_run_id}`) {
      await apiOk(route, ragAnswerRun);
      return;
    }

    if (path === "/api/agents/runs" && method === "GET") {
      await apiOk(route, list([
        currentAgentRun(agentNeedMoreInfo.id),
        currentAgentRun(agentFailed.id),
      ]));
      return;
    }
    if (path === "/api/agents/runs" && method === "POST") {
      await apiOk(route, { run: agentRun("completed", "agent_created_e2e"), steps_count: 1 });
      return;
    }
    if (path === `/api/agents/runs/${agentNeedMoreInfo.id}`) {
      await apiOk(route, { run: currentAgentRun(agentNeedMoreInfo.id), steps_count: 1 });
      return;
    }
    if (path === `/api/agents/runs/${agentNeedMoreInfo.id}/steps`) {
      await apiOk(route, { steps: [agentStep], total: 1 });
      return;
    }
    if (path === `/api/agents/runs/${agentNeedMoreInfo.id}/resume`) {
      agentStatuses.set(agentNeedMoreInfo.id, "completed");
      await apiOk(route, { run: currentAgentRun(agentNeedMoreInfo.id), steps_count: 1 });
      return;
    }
    if (path === `/api/agents/runs/${agentNeedMoreInfo.id}/cancel`) {
      agentStatuses.set(agentNeedMoreInfo.id, "cancelled");
      await apiOk(route, { run: currentAgentRun(agentNeedMoreInfo.id), steps_count: 1 });
      return;
    }
    if (path === `/api/agents/runs/${agentFailed.id}`) {
      await apiOk(route, { run: currentAgentRun(agentFailed.id), steps_count: 1 });
      return;
    }
    if (path === `/api/agents/runs/${agentFailed.id}/steps`) {
      await apiOk(route, { steps: [{ ...agentStep, run_id: agentFailed.id, status: "failed" }], total: 1 });
      return;
    }
    if (path === `/api/agents/runs/${agentFailed.id}/retry`) {
      agentStatuses.set(agentFailed.id, "completed");
      await apiOk(route, { run: currentAgentRun(agentFailed.id), steps_count: 1 });
      return;
    }

    if (path === "/api/applications/stats") {
      await apiOk(route, {
        total: 1,
        total_applications: 1,
        by_status: {
          saved: 0,
          ready_to_apply: 1,
          applied: 0,
          written_test: 0,
          first_interview: 0,
          second_interview: 0,
          hr_interview: 0,
          offer: 0,
          rejected: 0,
          withdrawn: 0,
          archived: 0,
        },
        active_count: 1,
        interview_count: 0,
        offer_count: 0,
        rejected_count: 0,
        withdrawn_count: 0,
        conversion: {
          applied_to_interview_rate: 0,
          interview_to_offer_rate: 0,
          applied_to_offer_rate: 0,
        },
        upcoming_count: 1,
        overdue_count: 0,
        latest_applications: [application],
      });
      return;
    }
    if (path === "/api/applications" && method === "GET") {
      await apiOk(route, list([application]));
      return;
    }
    if (path === "/api/applications" && method === "POST") {
      await apiOk(route, application);
      return;
    }
    if (path === `/api/applications/${application.application_id}`) {
      const next = method === "PATCH" ? { ...application, status: "applied" } : application;
      await apiOk(route, next);
      return;
    }
    if (path === `/api/applications/${application.application_id}/status-history`) {
      await apiOk(route, list(application.status_history));
      return;
    }
    if (path === `/api/applications/${application.application_id}/reflection`) {
      await apiOk(route, application);
      return;
    }

    if (path === "/api/bad-cases/stats") {
      await apiOk(route, {
        total: 1,
        by_status: { reviewing: 1 },
        by_module: { rag: 1 },
        by_case_type: { unsupported_answer: 1 },
        added_to_eval_set_count: 1,
        verified_count: 0,
        open_count: 1,
      });
      return;
    }
    if (path === "/api/bad-cases") {
      await apiOk(route, list([badCase]));
      return;
    }
    if (path === `/api/bad-cases/${badCase.id}`) {
      await apiOk(route, badCase);
      return;
    }

    if (path === "/api/evaluations/stats") {
      await apiOk(route, {
        total_runs: 1,
        latest_run_status: "completed",
        latest_pass_rate: 1,
        total_cases: 1,
        failed_results: 0,
        by_module: {
          jd_parser: 0,
          resume_parser: 0,
          match: 0,
          rag: 1,
          agent: 0,
          application: 0,
          bad_case: 0,
        },
      });
      return;
    }
    if (path === "/api/evaluations/runs" && method === "GET") {
      await apiOk(route, list([evaluationRun]));
      return;
    }
    if (path === "/api/evaluations/runs" && method === "POST") {
      await apiOk(route, { run: evaluationRun, results_count: 1 });
      return;
    }
    if (path === `/api/evaluations/runs/${evaluationRun.id}`) {
      await apiOk(route, { run: evaluationRun, results_count: 1 });
      return;
    }
    if (path === `/api/evaluations/runs/${evaluationRun.id}/results`) {
      await apiOk(route, list([evaluationResult]));
      return;
    }
    if (path === "/api/evaluations/cases") {
      await apiOk(route, list([evaluationCase]));
      return;
    }
    if (path === "/api/evaluations/datasets") {
      await apiOk(route, list([
        {
          dataset_name: "synthetic_smoke_v1",
          module: "rag",
          case_count: 1,
          source_type: "manual",
          description: "Browser E2E dataset summary.",
          version: "browser-e2e",
        },
      ]));
      return;
    }

    await apiOk(route, {});
  });
}

async function signIn(page: Page) {
  await installMockApi(page);
  await page.goto("/");
  await page.getByLabel("Email").fill(authUser.email);
  await page.getByLabel("Password").fill("synthetic-password");
  await page.locator("form").getByRole("button", { name: "Login" }).click();
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
}

test("login, dashboard and session state render in Chromium", async ({ page }) => {
  await signIn(page);
  await expect(page.getByText("Sessions (1)")).toBeVisible();
  await page.getByText("Sessions (1)").click();
  await expect(page.getByText("web session · current")).toBeVisible();
  await expect(page.getByText(authUser.email)).toBeVisible();
  await expect(page.locator("body")).not.toContainText(forbiddenPrivateText);
});

test("main workflow supports selectors, match compare and privacy-safe display", async ({ page }) => {
  await signIn(page);

  await page.getByRole("button", { name: /Profile Center/ }).click();
  await expect(page.getByRole("heading", { name: "Profile Center" })).toBeVisible();
  await expect(
    page.locator(".activity-list strong").filter({ hasText: "AI Application Engineer" }).first(),
  ).toBeVisible();

  await page.getByRole("button", { name: /Resume Center/ }).click();
  await expect(page.getByRole("heading", { name: "Resume Center" })).toBeVisible();
  await page.locator('input[type="file"]').setInputFiles({
    name: "synthetic-resume.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("synthetic resume preview"),
  });
  await page.getByRole("button", { name: "Upload resume" }).click();
  await expect(
    page.locator(".activity-list strong").filter({ hasText: "candidate-redacted.pdf" }).first(),
  ).toBeVisible();

  await page.getByRole("button", { name: /JD Center/ }).click();
  await expect(page.getByRole("heading", { name: "JD Center" })).toBeVisible();
  await page.getByRole("button", { name: "Create JD" }).click();
  await expect(page.getByText("Synthetic Company / ref jd_e2e")).toBeVisible();

  await page.getByRole("button", { name: /Match Report/ }).click();
  await expect(
    page.getByRole("heading", { name: "Match Report", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Compare Match Reports")).toBeVisible();
  await page.getByRole("button", { name: "Run match" }).click();
  await expect(page.getByText("Score 86")).toBeVisible();
  await page.getByLabel("Version A").selectOption(resumeVersions[0].resume_version_id);
  await page.getByLabel("Version B").selectOption(resumeVersions[1].resume_version_id);
  await page.getByRole("button", { name: "Compare" }).click();
  await expect(page.getByText("Rank 1: score 90")).toBeVisible();
  await expect(page.locator("body")).not.toContainText(forbiddenPrivateText);
});

test("productized workbench pages expose browser interactions", async ({ page }) => {
  await signIn(page);

  await page.getByRole("button", { name: /Project Optimization/ }).click();
  await expect(page.getByRole("heading", { name: "Project Optimization" })).toBeVisible();
  const rewritePanel = page.locator("article").filter({ hasText: "Run Rewrite" });
  await rewritePanel.getByLabel("JD").selectOption(job.jd_id);
  await rewritePanel.getByRole("button", { name: "Run rewrite" }).click();
  await expect(page.getByText("Built FastAPI workflow with grounded RAG evidence paths.")).toBeVisible();

  await page.getByRole("button", { name: /Interview Center/ }).click();
  await expect(page.getByRole("heading", { name: "Interview Center" })).toBeVisible();
  const questionPanel = page.locator("article").filter({ hasText: "Generate Questions" });
  await questionPanel.getByLabel("JD").selectOption(job.jd_id);
  await questionPanel.getByLabel("Resume Version").selectOption(resumeVersions[0].resume_version_id);
  await questionPanel.getByRole("button", { name: "Generate Questions" }).click();
  await expect(page.getByText("How did you keep the RAG answer grounded?")).toBeVisible();
  await page.getByRole("button", { name: "Select" }).first().click();
  await page.getByLabel("Answer text").fill("I cite source refs and refuse unsupported claims.");
  await page.getByRole("button", { name: "Submit Answer" }).click();
  await expect(page.getByText("Grounded answer with clear evidence.")).toBeVisible();

  await page.getByRole("button", { name: /Study Plan/ }).click();
  await expect(page.getByRole("heading", { name: "Study Plan Center" })).toBeVisible();
  await expect(page.getByText("Practice citation review")).toBeVisible();
  await page.locator(".study-task-actions select").first().selectOption("done");
  await expect(page.getByText("Updated task_1 to Done.")).toBeVisible();

  await page.getByRole("button", { name: /Applications/ }).click();
  await expect(page.getByRole("heading", { name: "Application Tracker" })).toBeVisible();
  await page.locator(".application-card").first().click();
  await page.getByRole("button", { name: "Update status" }).click();
  await expect(page.locator(".status-applied").filter({ hasText: /^applied$/ }).first()).toBeVisible();

  await page.getByRole("button", { name: /Knowledge Base/ }).click();
  await expect(page.getByRole("heading", { name: "Knowledge Base" })).toBeVisible();
  await page.getByRole("button", { name: "Answer" }).click();
  await expect(
    page.getByText("Use source refs and citations for every material claim.").first(),
  ).toBeVisible();
  await expect(page.getByText("RAG Evaluation Notes / grounding").first()).toBeVisible();

  await page.getByRole("button", { name: /Agent Runs/ }).click();
  await expect(page.getByRole("heading", { name: "Agent Runs" })).toBeVisible();
  await page.getByRole("button", { name: "Detail" }).first().click();
  await page.getByRole("button", { name: "Resume", exact: true }).click();
  await expect(page.locator(".status-completed").filter({ hasText: "completed" }).first()).toBeVisible();
  await page.getByRole("button", { name: "Detail" }).nth(1).click();
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(page.getByText("Workflow completed").first()).toBeVisible();

  await page.getByRole("button", { name: /Quality Review/ }).click();
  await expect(page.getByRole("heading", { name: "Bad Case Review" })).toBeVisible();
  await expect(
    page.locator(".bad-case-list strong").filter({ hasText: "RAG answer needs citation review" }).first(),
  ).toBeVisible();

  await page.getByRole("button", { name: /Evaluation/ }).click();
  await expect(page.getByRole("heading", { name: "Evaluation Center" })).toBeVisible();
  await expect(page.getByText("Browser E2E synthetic eval")).toBeVisible();
  await expect(page.locator("body")).not.toContainText(forbiddenPrivateText);
});

test("401 and empty-state paths stay user-safe", async ({ page }) => {
  await installMockApi(page, { unauthorizedMe: true });
  await page.addInitScript(() => {
    window.localStorage.setItem("careeragent.auth_token", "stale-token");
  });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();

  await page.unroute(backendApiPattern);
  await installMockApi(page);
  await page.route("http://localhost:8000/api/resumes", async (route) => {
    await apiOk(route, list([]));
  });
  await page.getByLabel("Email").fill(authUser.email);
  await page.getByLabel("Password").fill("synthetic-password");
  await page.locator("form").getByRole("button", { name: "Login" }).click();
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await page.getByRole("button", { name: /Resume Center/ }).click();
  await expect(page.getByText("暂无 Resume")).toBeVisible();
});
