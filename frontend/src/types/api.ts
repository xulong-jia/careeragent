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
  basic_info: Record<string, string | null>;
  education: Record<string, unknown>[];
  projects: Record<string, unknown>[];
  experience: Record<string, unknown>[];
  skills: Record<string, string[]>;
  certificates: Record<string, unknown>[];
};

export type ResumeRecord = {
  resume_id: string;
  filename: string;
  file_type: string;
  parse_status: string;
  raw_text: string;
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
};

export type ResumeVersionRecord = {
  resume_version_id: string;
  resume_id: string;
  version_name: string;
  version_number: number;
  target_role: string | null;
  raw_text: string;
  raw_text_preview: string;
  structured_resume: StructuredResume;
  extraction_status: string;
  extraction_method: string;
  extraction_warnings: string[];
  risk_flags: Record<string, unknown>[];
  status: string;
  is_archived: boolean;
  created_at: string;
  archived_at: string | null;
};

export type ResumeVersionClonePayload = {
  version_name: string | null;
  target_role: string | null;
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
  raw_text: string;
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

export type WorkbenchState = {
  latestResume: ResumeRecord | null;
  latestJob: JobRecord | null;
  latestMatch: MatchReport | null;
  resumes: ResumeRecord[];
  jobs: JobRecord[];
  matches: MatchReport[];
  ragDocuments: RagDocumentRecord[];
};
