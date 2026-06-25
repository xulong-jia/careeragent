export type ApiResponse<T> = {
  data: T;
  request_id: string;
};

export type ApiErrorResponse = {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  };
  request_id: string;
};

export type ListResponse<T> = {
  items: T[];
  total: number;
};

export type StructuredResume = {
  basic_info: Record<string, unknown>;
  education: Record<string, unknown>[];
  projects: Record<string, unknown>[];
  experience: Record<string, unknown>[];
  skills: Record<string, string[]>;
  certificates: Record<string, unknown>[];
  awards: Record<string, unknown>[];
};

export type ResumeRecord = {
  resume_id: string;
  filename: string;
  file_type: string;
  parse_status: string;
  raw_text_preview: string;
  extraction_status: string;
  extraction_method: string;
  extraction_warnings: string[];
  structured_resume: StructuredResume;
  source_file: {
    filename: string;
    file_type: string;
    text_hash: string | null;
  };
  risk_flags: Record<string, unknown>[];
  risk_report: Record<string, unknown>;
};

export type ResumeVersionRecord = {
  resume_version_id: string;
  resume_id: string;
  version_name: string;
  version_number: number;
  target_role: string | null;
  raw_text_preview: string;
  structured_resume: StructuredResume;
  extraction_status: string;
  extraction_method: string;
  extraction_warnings: string[];
  risk_flags: Record<string, unknown>[];
  risk_report: Record<string, unknown>;
  status: string;
  is_archived: boolean;
  created_at: string;
  archived_at: string | null;
};

export type ResumeVersionClonePayload = {
  version_name: string | null;
  target_role: string | null;
};

export type ResumeParseRequest = {
  resume_version_id?: string | null;
  parser_mode?: "deterministic";
};

export type ResumeParseResponse = {
  resume_id: string;
  source_version_id: string;
  raw_text_preview: string;
  structured_resume: StructuredResume;
  extraction_method: string;
  extraction_warnings: string[];
  parsed_at: string;
};

export type ResumeRiskFlag = {
  type: string;
  severity: "low" | "medium" | "high";
  message: string;
  location: string | null;
  evidence: string | null;
};

export type ResumeRiskCheckRequest = {
  resume_version_id?: string | null;
  structured_resume?: StructuredResume | null;
};

export type ResumeRiskCheckResponse = {
  resume_id: string;
  source_version_id: string | null;
  risk_flags: ResumeRiskFlag[];
  risk_report: Record<string, unknown>;
  checked_at: string;
};

export type SaveResumeVersionRequest = {
  version_name: string;
  target_role?: string | null;
  structured_resume: StructuredResume;
  risk_report?: Record<string, unknown> | null;
  source_version_id?: string | null;
};

export type ProfileRecord = {
  id: string;
  user_id: string;
  target_roles: string[];
  target_industries: string[];
  target_locations: string[];
  skill_map: Record<string, unknown>;
  preferences: Record<string, unknown>;
  source_resume_version_id: string | null;
  created_at: string;
  updated_at: string;
};

export type ProfileCreatePayload = {
  target_roles: string[];
  target_industries: string[];
  target_locations: string[];
  skill_map: Record<string, unknown>;
  preferences: Record<string, unknown>;
  source_resume_version_id?: string | null;
};

export type ProfileUpdatePayload = Partial<ProfileCreatePayload>;

export type ProfileSummary = {
  profile_id: string;
  completeness_score: number;
  missing_fields: string[];
  target_roles_count: number;
  target_locations_count: number;
  skill_categories_count: number;
  source_resume_version_id: string | null;
  readiness_level: "incomplete" | "basic" | "ready";
};

export type ProjectStatus = "active" | "archived";

export type ProjectRecord = {
  id: string;
  user_id: string;
  profile_id: string | null;
  resume_version_id: string | null;
  name: string;
  role: string | null;
  period: string | null;
  background: string | null;
  tech_stack: string[];
  responsibilities: string[];
  results: string[];
  evidence: Record<string, unknown>[];
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
};

export type ProjectCreateRequest = {
  profile_id?: string | null;
  resume_version_id?: string | null;
  name: string;
  role?: string | null;
  period?: string | null;
  background?: string | null;
  tech_stack?: string[];
  responsibilities?: string[];
  results?: string[];
  evidence?: Record<string, unknown>[];
  status?: ProjectStatus;
};

export type ProjectUpdateRequest = Partial<ProjectCreateRequest>;

export type ProjectFilters = {
  profileId?: string;
  resumeVersionId?: string;
  status?: ProjectStatus | "";
};

export type ProjectListResponse = ListResponse<ProjectRecord>;

export type ProjectRewriteRequest = {
  jd_id: string;
  resume_version_id?: string | null;
  match_report_id?: string | null;
  profile_id?: string | null;
};

export type ProjectMatchedPoint = {
  skill: string;
  source_field: string;
  project_text: string;
  jd_requirement: string;
  match_type:
    | "required_skill"
    | "preferred_skill"
    | "responsibility"
    | "business_scenario";
};

export type ProjectMissingPoint = {
  requirement: string;
  requirement_type: "required_skill" | "preferred_skill";
  reason: string;
  priority: "high" | "medium";
};

export type ProjectEvidenceRequired = {
  type:
    | "unsupported_metric"
    | "missing_evidence"
    | "timeline_or_scope_evidence";
  source_field: string;
  project_text: string;
  reason: string;
};

export type ProjectRewrittenBullet = {
  before: string;
  after: string;
  reason: string;
  evidence_required: string;
  risk_level: "low" | "medium" | "high";
};

export type ProjectRiskFlag = {
  type:
    | "unsupported_metric"
    | "missing_evidence"
    | "overclaim"
    | "fabricated_skill"
    | "learning_to_business_overclaim";
  severity: "low" | "medium" | "high";
  source_field: string;
  message: string;
};

export type ProjectForbiddenChange =
  | "company"
  | "user_count"
  | "revenue"
  | "accuracy"
  | "production_status"
  | "business_scale"
  | "tech_stack_not_in_facts"
  | "unsupported_metric"
  | string;

export type ProjectRewriteRecord = {
  id: string;
  project_id: string;
  jd_id: string;
  resume_version_id: string | null;
  match_report_id: string | null;
  profile_id: string | null;
  matched_points: ProjectMatchedPoint[];
  missing_points: ProjectMissingPoint[];
  evidence_required: ProjectEvidenceRequired[];
  rewritten_bullets: ProjectRewrittenBullet[];
  forbidden_changes: ProjectForbiddenChange[];
  risk_flags: ProjectRiskFlag[];
  rewrite_strategy: string;
  created_at: string;
};

export type InterviewQuestionType =
  | "project_deep_dive"
  | "technical_depth"
  | "jd_skill_check"
  | "risk_or_gap_explanation"
  | "behavior_or_collaboration"
  | "resume_challenge";

export type InterviewDifficulty = "easy" | "medium" | "hard";

export type InterviewSourceRef = {
  source_type: string;
  source_id: string;
  field: string;
  label: string;
  preview: string;
};

export type InterviewQuestionGenerateRequest = {
  jd_id: string;
  resume_version_id: string;
  project_id?: string | null;
  project_rewrite_id?: string | null;
  question_types?: InterviewQuestionType[] | null;
  max_questions?: number;
};

export type InterviewQuestionRecord = {
  id: string;
  user_id: string;
  jd_id: string;
  resume_version_id: string;
  project_id: string | null;
  project_rewrite_id: string | null;
  question_type: InterviewQuestionType;
  question: string;
  expected_points: Record<string, unknown>[];
  source_refs: InterviewSourceRef[];
  difficulty: InterviewDifficulty;
  created_at: string;
};

export type InterviewQuestionGenerateResponse = {
  questions: InterviewQuestionRecord[];
  warnings: string[];
  need_more_info: string[];
};

export type InterviewQuestionFilters = {
  jd_id?: string;
  resume_version_id?: string;
  project_id?: string;
  question_type?: InterviewQuestionType | "";
  difficulty?: InterviewDifficulty | "";
};

export type InterviewQuestionListResponse =
  ListResponse<InterviewQuestionRecord>;

export type InterviewAnswerCreateRequest = {
  question_id: string;
  answer_text: string;
};

export type InterviewScores = {
  structure?: number;
  technical_depth?: number;
  business_understanding?: number;
  evidence?: number;
  clarity?: number;
  risk_control?: number;
  overall_average?: number;
};

export type InterviewAnswerRecord = {
  id: string;
  question_id: string;
  user_id: string;
  answer_text_preview: string;
  scores: InterviewScores;
  feedback: string | null;
  weakness_tags: string[];
  created_at: string;
};

export type InterviewAnswerFilters = {
  question_id?: string;
  jd_id?: string;
  resume_version_id?: string;
  project_id?: string;
};

export type InterviewAnswerListResponse = ListResponse<InterviewAnswerRecord>;

export type InterviewAnswerScoreResponse = InterviewAnswerRecord;

export type InterviewStats = {
  total_questions: number;
  total_answers: number;
  scored_answers: number;
  latest_average_score: number | null;
  latest_weakness_tags: string[];
  by_question_type: Record<string, number>;
  by_difficulty: Record<string, number>;
};

export type StudyPlanStatus = "active" | "completed" | "archived";

export type StudyTaskStatus =
  | "todo"
  | "in_progress"
  | "done"
  | "blocked"
  | "skipped";

export type StudyTaskPriority = "high" | "medium" | "low";

export type StudySourceRef = {
  source_type: string;
  source_id: string;
  field: string;
  label: string;
  preview: string;
};

export type StudyPlanGenerateRequest = {
  target_role?: string | null;
  profile_id?: string | null;
  match_report_id?: string | null;
  project_rewrite_id?: string | null;
  interview_answer_ids?: string[];
  weakness_tags?: string[];
  available_hours_per_week?: number;
  horizon_weeks?: number;
};

export type StudyTask = {
  task_id: string;
  title: string;
  description: string;
  source_gap: string;
  priority: StudyTaskPriority;
  status: StudyTaskStatus;
  due_hint: string | null;
  acceptance_criteria: string[];
  evidence_required: string[];
  source_refs: StudySourceRef[];
};

export type StudyPhase = {
  phase_id: string;
  phase: string;
  goal: string;
  tasks: StudyTask[];
  resources: Record<string, unknown>[];
  deliverables: string[];
  acceptance_criteria: string[];
};

export type StudyPlanRecord = {
  id: string;
  user_id: string;
  match_report_id: string | null;
  profile_id: string | null;
  project_rewrite_id: string | null;
  target_role: string;
  source_refs: StudySourceRef[];
  phases: StudyPhase[];
  status: StudyPlanStatus;
  created_at: string;
  updated_at: string;
};

export type StudyPlanGenerateResponse = StudyPlanRecord;

export type StudyPlanListFilters = {
  status?: StudyPlanStatus | "";
  target_role?: string;
  profile_id?: string;
  match_report_id?: string;
};

export type StudyPlanListResponse = ListResponse<StudyPlanRecord>;

export type StudyTaskStatusUpdateRequest = {
  status: StudyTaskStatus;
};

export type StudyPlanStats = {
  total_plans: number;
  active_plans: number;
  completed_plans: number;
  archived_plans: number;
  pending_tasks: number;
  blocked_tasks: number;
  done_tasks: number;
  in_progress_tasks: number;
  skipped_tasks: number;
  latest_plan_id: string | null;
  latest_target_role: string | null;
};

export type JobCreatePayload = {
  company: string;
  job_title: string;
  location: string | null;
  raw_text: string;
  source_url: string | null;
};

export type JobProfile = {
  job_profile_id: string;
  role_category: string;
  required_skills: string[];
  preferred_skills: string[];
  responsibilities: string[];
  business_scenarios: string[];
  hidden_requirements: Record<string, unknown>[];
  interview_focus: string[];
  risk_level: string;
  summary: string | null;
};

export type JobRecord = {
  jd_id: string;
  company: string;
  job_title: string;
  location: string | null;
  raw_text_preview: string;
  source_url: string | null;
  job_profile: JobProfile;
};

export type MatchEvidence = {
  dimension: string;
  jd_requirement: string;
  resume_signal: string | null;
  score_impact: string;
};

export type MatchReport = {
  match_report_id: string;
  resume_id: string;
  resume_version_id?: string | null;
  jd_id: string;
  job_profile_id?: string | null;
  total_score: number;
  dimension_scores: Record<string, number>;
  evidence: MatchEvidence[];
  strengths: string[];
  gaps: string[];
  rewrite_priorities: string[];
  risk_flags: Record<string, unknown>[];
  created_at?: string | null;
};

export type RagDocumentRecord = {
  doc_id: string;
  title: string;
  source_type: string;
  source_uri: string | null;
  raw_text_preview: string;
  metadata: Record<string, unknown>;
  index_status: string;
  chunk_count: number;
  created_at: string;
  updated_at: string;
};

export type RagChunkRecord = {
  chunk_id: string;
  doc_id: string;
  chunk_index: number;
  section: string | null;
  text_preview: string;
  token_count: number;
  metadata: Record<string, unknown>;
  embedding_id: string | null;
  created_at: string;
};

export type RagDocumentCreatePayload = {
  title: string;
  source_type: string;
  source_uri: string | null;
  raw_text: string;
  metadata: Record<string, unknown>;
};

export type RagDocumentIndexPayload = {
  max_chars: number;
  overlap_chars: number;
};

export type RagDocumentIndexResult = {
  doc_id: string;
  index_status: string;
  chunk_count: number;
  chunks: RagChunkRecord[];
};

export type RagSearchFilters = {
  source_type?: string | null;
  doc_id?: string | null;
  tags?: string[] | null;
  role_category?: string | null;
  company?: string | null;
  topic?: string | null;
  domain?: string | null;
};

export type RagSearchRequest = {
  query: string;
  top_k: number;
  filters?: RagSearchFilters | null;
};

export type RagSearchSource = {
  doc_id: string;
  chunk_id: string;
  title: string;
  source_type: string;
  section: string | null;
  snippet: string;
  score: number;
  metadata: Record<string, unknown>;
};

export type RagSearchResult = {
  query: string;
  top_k: number;
  sources: RagSearchSource[];
  uncertainty: string | null;
};

export type RagAnswerRequest = {
  question: string;
  top_k: number;
  filters?: RagSearchFilters | null;
};

export type RagAnswerResult = {
  question: string;
  answer: string;
  sources: RagSearchSource[];
  uncertainty: string | null;
  grounded: boolean;
  answer_type: string;
};

export type AgentRunStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "need_more_info";

export type AgentStepStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "skipped"
  | "need_more_info";

export type AgentRunRecord = {
  id: string;
  user_id: string;
  workflow_name: string;
  status: AgentRunStatus;
  input_refs: Record<string, unknown>;
  output_refs: Record<string, unknown>;
  missing_slots: Record<string, unknown>[] | null;
  questions: Record<string, unknown>[] | null;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
};

export type AgentStepRecord = {
  id: string;
  run_id: string;
  step_name: string;
  step_order: number;
  status: AgentStepStatus;
  input_refs: Record<string, unknown>;
  output_refs: Record<string, unknown>;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
};

export type AgentRunCreatePayload = {
  workflow_name: string;
  resume_id?: string | null;
  resume_version_id?: string | null;
  jd_id?: string | null;
  use_rag?: boolean;
  rag_query?: string | null;
};

export type AgentRunCreateResponse = {
  run: AgentRunRecord;
  steps_count: number | null;
};

export type AgentRunDetailResponse = {
  run: AgentRunRecord;
  steps_count: number | null;
};

export type AgentStepListResponse = {
  steps: AgentStepRecord[];
  total: number;
};

export type BadCaseSourceType =
  | "match_report"
  | "rag_answer"
  | "rag_document"
  | "agent_run"
  | "agent_step"
  | "resume_version"
  | "job_description"
  | "ui_flow"
  | "data_persistence"
  | "other";

export type BadCaseCategory =
  | "match_score_inaccurate"
  | "missing_skill_extraction"
  | "irrelevant_rag_source"
  | "unsupported_answer"
  | "hallucination_risk"
  | "agent_step_failed"
  | "need_more_info_wrong"
  | "privacy_risk"
  | "ui_confusing"
  | "data_persistence_issue"
  | "other";

export type BadCaseSeverity = "low" | "medium" | "high" | "critical";

export type BadCaseStatus = "open" | "reviewing" | "fixed" | "wont_fix";

export type BadCaseRecord = {
  id: string;
  user_id: string;
  source_type: BadCaseSourceType;
  source_id: string;
  category: BadCaseCategory;
  severity: BadCaseSeverity;
  title: string;
  description: string;
  expected_behavior: string | null;
  actual_behavior: string | null;
  suggested_fix: string | null;
  status: BadCaseStatus;
  created_at: string;
  resolved_at: string | null;
};

export type BadCaseCreatePayload = {
  source_type: BadCaseSourceType;
  source_id: string;
  category: BadCaseCategory;
  severity?: BadCaseSeverity;
  title: string;
  description: string;
  expected_behavior?: string | null;
  actual_behavior?: string | null;
  suggested_fix?: string | null;
};

export type BadCaseUpdatePayload = {
  status?: BadCaseStatus;
  severity?: BadCaseSeverity;
  title?: string;
  description?: string;
  expected_behavior?: string | null;
  actual_behavior?: string | null;
  suggested_fix?: string | null;
  category?: BadCaseCategory;
};

export type BadCaseFilters = {
  sourceType?: BadCaseSourceType | "";
  sourceId?: string;
  category?: BadCaseCategory | "";
  severity?: BadCaseSeverity | "";
  status?: BadCaseStatus | "";
  limit?: number;
};

export type EvaluationModule =
  | "match"
  | "rag"
  | "agent"
  | "application"
  | "bad_case";

export type EvaluationRunModule = EvaluationModule | "all";

export type EvaluationRunStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed";

export type EvaluationResultStatus = "passed" | "failed" | "error";

export type EvaluationCaseSourceType = "synthetic" | "bad_case" | "manual";

export type EvaluationRunCreatePayload = {
  module?: EvaluationRunModule | null;
  dataset_name?: string;
  name?: string | null;
};

export type EvaluationCaseCreatePayload = {
  module: EvaluationModule;
  dataset_name?: string;
  case_name: string;
  input_payload?: Record<string, unknown>;
  expected_output?: Record<string, unknown>;
  tags?: string[];
  source_type?: EvaluationCaseSourceType;
  bad_case_id?: string | null;
};

export type EvaluationRunRecord = {
  id: string;
  name: string;
  module: EvaluationRunModule;
  dataset_name: string;
  status: EvaluationRunStatus;
  metrics: Record<string, unknown>;
  run_config: Record<string, unknown>;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
};

export type EvaluationCaseRecord = {
  id: string;
  module: EvaluationModule;
  dataset_name: string;
  case_name: string;
  input_payload: Record<string, unknown>;
  expected_output: Record<string, unknown>;
  tags: string[];
  source_type: EvaluationCaseSourceType;
  bad_case_id: string | null;
  created_at: string;
  updated_at: string;
};

export type EvaluationResultRecord = {
  id: string;
  run_id: string;
  case_id: string;
  module: EvaluationModule;
  status: EvaluationResultStatus;
  actual_output: Record<string, unknown>;
  expected_output: Record<string, unknown>;
  passed: boolean;
  score: number;
  error: string | null;
  created_at: string;
};

export type EvaluationRunSummary = {
  run: EvaluationRunRecord;
  results_count: number;
};

export type EvaluationStats = {
  total_runs: number;
  latest_run_status: EvaluationRunStatus | null;
  latest_pass_rate: number | null;
  total_cases: number;
  failed_results: number;
  by_module: Record<EvaluationModule, number>;
};

export type EvaluationRunFilters = {
  module?: EvaluationRunModule | "";
  datasetName?: string;
  limit?: number;
};

export type EvaluationCaseFilters = {
  module?: EvaluationModule | "";
  datasetName?: string;
  sourceType?: EvaluationCaseSourceType | "";
  limit?: number;
};

export type ApplicationStatus =
  | "saved"
  | "ready_to_apply"
  | "applied"
  | "written_test"
  | "first_interview"
  | "second_interview"
  | "hr_interview"
  | "offer"
  | "rejected"
  | "withdrawn"
  | "archived";

export type ApplicationRecord = {
  application_id: string;
  user_id: string;
  company: string;
  role_title: string;
  role_category: string | null;
  jd_id: string | null;
  resume_version_id: string | null;
  match_report_id: string | null;
  status: ApplicationStatus;
  apply_date: string | null;
  next_step_date: string | null;
  interview_notes: string | null;
  reflection: string | null;
  tags: string[];
  created_at: string;
  updated_at: string;
};

export type ApplicationCreatePayload = {
  company: string;
  role_title: string;
  role_category?: string | null;
  jd_id?: string | null;
  resume_version_id?: string | null;
  match_report_id?: string | null;
  status?: ApplicationStatus;
  apply_date?: string | null;
  next_step_date?: string | null;
  interview_notes?: string | null;
  reflection?: string | null;
  tags?: string[];
};

export type ApplicationUpdatePayload = Partial<ApplicationCreatePayload>;

export type ApplicationFilters = {
  status?: ApplicationStatus | "";
  company?: string;
  roleCategory?: string;
  resumeVersionId?: string;
  jdId?: string;
};

export type ApplicationStats = {
  total_applications: number;
  by_status: Record<ApplicationStatus, number>;
  interview_count: number;
  offer_count: number;
  rejected_count: number;
  active_count: number;
};

export type WorkbenchState = {
  latestResume: ResumeRecord | null;
  latestJob: JobRecord | null;
  latestMatch: MatchReport | null;
  profiles: ProfileRecord[];
  latestProfileSummary: ProfileSummary | null;
  projects: ProjectRecord[];
  resumes: ResumeRecord[];
  jobs: JobRecord[];
  matches: MatchReport[];
  ragDocuments: RagDocumentRecord[];
  agentRuns: AgentRunRecord[];
  badCases: BadCaseRecord[];
  applications: ApplicationRecord[];
  applicationStats: ApplicationStats | null;
  interviewStats: InterviewStats | null;
  studyPlanStats: StudyPlanStats | null;
  evaluationStats: EvaluationStats | null;
};
