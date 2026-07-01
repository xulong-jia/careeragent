import { useEffect, useMemo, useState } from "react";

import { listAgentRuns } from "../api/agents";
import { listApplications } from "../api/applications";
import { listInterviewAnswers } from "../api/interviews";
import { listJobs } from "../api/jobs";
import { listMatches } from "../api/matches";
import { listProfiles } from "../api/profiles";
import { listProjects } from "../api/projects";
import { listRagAnswerRuns, listRagDocuments } from "../api/rag";
import { listResumes, listResumeVersions } from "../api/resumes";
import type {
  AgentRunRecord,
  ApplicationRecord,
  InterviewAnswerRecord,
  JobRecord,
  MatchReport,
  ProfileRecord,
  ProjectRecord,
  RagAnswerRunRecord,
  RagDocumentRecord,
  ResumeRecord,
  ResumeVersionRecord,
} from "../types/api";

type EntitySelectorProps<T> = {
  emptyText: string;
  getLabel: (item: T) => string;
  getMeta?: (item: T) => string;
  getValue: (item: T) => string;
  items: T[];
  label: string;
  loading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
  onValueChange: (value: string, item: T | null) => void;
  value: string;
};

type LoadingSelectorProps<T> = {
  emptyText?: string;
  label: string;
  onChange: (value: string, item: T | null) => void;
  value: string;
};

type ResumeVersionOption = ResumeVersionRecord & {
  resume_filename: string;
};

const workflows = [
  "job_application_preparation",
  "interview_preparation",
  "application_review",
  "study_gap_planning",
];

function idSuffix(value: string | null | undefined): string {
  if (!value) {
    return "No ID";
  }
  return value.length > 14 ? `ID ...${value.slice(-10)}` : `ID ${value}`;
}

function formatDate(value: string | null | undefined): string {
  return value ? new Date(value).toLocaleDateString() : "No date";
}

function useLoadedItems<T>(loader: () => Promise<T[]>) {
  const [items, setItems] = useState<T[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await loader());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Load failed.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, [loader]);

  return { error, items, loading, refresh };
}

export function EntitySelector<T>({
  emptyText,
  error,
  getLabel,
  getMeta,
  getValue,
  items,
  label,
  loading = false,
  onRefresh,
  onValueChange,
  value,
}: EntitySelectorProps<T>) {
  const selected = useMemo(
    () => items.find((item) => getValue(item) === value) ?? null,
    [getValue, items, value],
  );

  return (
    <div className="entity-selector">
      <label>
        {label}
        <select
          disabled={loading || items.length === 0}
          onChange={(event) => {
            const nextValue = event.target.value;
            onValueChange(
              nextValue,
              items.find((item) => getValue(item) === nextValue) ?? null,
            );
          }}
          value={value}
        >
          <option value="">{loading ? "Loading..." : emptyText}</option>
          {items.map((item) => (
            <option key={getValue(item)} value={getValue(item)}>
              {getLabel(item)}
            </option>
          ))}
        </select>
      </label>
      {selected && getMeta ? (
        <span className="entity-selector-meta">{getMeta(selected)}</span>
      ) : null}
      {error ? <span className="error-text compact">{error}</span> : null}
      {onRefresh ? (
        <button
          className="ghost-action tiny-action"
          disabled={loading}
          onClick={onRefresh}
          type="button"
        >
          Refresh
        </button>
      ) : null}
    </div>
  );
}

export function ProfileSelector({
  emptyText = "Select profile",
  label,
  onChange,
  value,
}: LoadingSelectorProps<ProfileRecord>) {
  const loadProfiles = useMemo(() => () => listProfiles().then((data) => data.items), []);
  const { error, items, loading, refresh } = useLoadedItems(loadProfiles);
  return (
    <EntitySelector
      emptyText={emptyText}
      error={error}
      getLabel={(item) => item.target_roles[0] ?? "Untitled profile"}
      getMeta={(item) =>
        `${item.target_roles.length} roles / ${item.target_locations.length} locations / ${idSuffix(item.id)}`
      }
      getValue={(item) => item.id}
      items={items}
      label={label}
      loading={loading}
      onRefresh={() => void refresh()}
      onValueChange={onChange}
      value={value}
    />
  );
}

export function ResumeSelector({
  emptyText = "Select resume",
  label,
  onChange,
  value,
}: LoadingSelectorProps<ResumeRecord>) {
  const loadResumes = useMemo(() => () => listResumes().then((data) => data.items), []);
  const { error, items, loading, refresh } = useLoadedItems(loadResumes);
  return (
    <EntitySelector
      emptyText={emptyText}
      error={error}
      getLabel={(item) => item.filename}
      getMeta={(item) =>
        `${item.parse_status} / ${item.risk_flags.length} risks / ${idSuffix(item.resume_id)}`
      }
      getValue={(item) => item.resume_id}
      items={items}
      label={label}
      loading={loading}
      onRefresh={() => void refresh()}
      onValueChange={onChange}
      value={value}
    />
  );
}

export function ResumeVersionSelector({
  emptyText = "Select resume version",
  label,
  onChange,
  resumeId,
  value,
}: LoadingSelectorProps<ResumeVersionRecord> & { resumeId: string }) {
  const loadVersions = useMemo(
    () => () =>
      resumeId ? listResumeVersions(resumeId).then((data) => data.items) : Promise.resolve([]),
    [resumeId],
  );
  const { error, items, loading, refresh } = useLoadedItems(loadVersions);
  return (
    <EntitySelector
      emptyText={resumeId ? emptyText : "Select resume first"}
      error={error}
      getLabel={(item) =>
        `${item.version_name} v${item.version_number}${item.target_role ? ` / ${item.target_role}` : ""}`
      }
      getMeta={(item) =>
        `${item.status}${item.is_archived ? " / archived" : ""} / ${idSuffix(item.resume_version_id)}`
      }
      getValue={(item) => item.resume_version_id}
      items={items}
      label={label}
      loading={loading}
      onRefresh={() => void refresh()}
      onValueChange={onChange}
      value={value}
    />
  );
}

export function AllResumeVersionSelector({
  emptyText = "Select resume version",
  label,
  onChange,
  value,
}: LoadingSelectorProps<ResumeVersionOption>) {
  const loadVersions = useMemo(
    () => async () => {
      const resumeList = await listResumes();
      const versionLists = await Promise.all(
        resumeList.items.map(async (resume) => {
          const versionList = await listResumeVersions(resume.resume_id);
          return versionList.items.map((version) => ({
            ...version,
            resume_filename: resume.filename,
          }));
        }),
      );
      return versionLists.flat();
    },
    [],
  );
  const { error, items, loading, refresh } = useLoadedItems(loadVersions);
  return (
    <EntitySelector
      emptyText={emptyText}
      error={error}
      getLabel={(item) =>
        `${item.resume_filename} / ${item.version_name} v${item.version_number}`
      }
      getMeta={(item) =>
        `${item.target_role ?? "No target role"} / ${item.status} / ${idSuffix(item.resume_version_id)}`
      }
      getValue={(item) => item.resume_version_id}
      items={items}
      label={label}
      loading={loading}
      onRefresh={() => void refresh()}
      onValueChange={onChange}
      value={value}
    />
  );
}

export function JDSelector({
  emptyText = "Select JD",
  label,
  onChange,
  value,
}: LoadingSelectorProps<JobRecord>) {
  const loadJobs = useMemo(() => () => listJobs().then((data) => data.items), []);
  const { error, items, loading, refresh } = useLoadedItems(loadJobs);
  return (
    <EntitySelector
      emptyText={emptyText}
      error={error}
      getLabel={(item) => `${item.company} / ${item.job_title}`}
      getMeta={(item) =>
        `${item.job_profile.role_category} / ${item.job_profile.risk_level} / ${idSuffix(item.jd_id)}`
      }
      getValue={(item) => item.jd_id}
      items={items}
      label={label}
      loading={loading}
      onRefresh={() => void refresh()}
      onValueChange={onChange}
      value={value}
    />
  );
}

export function MatchReportSelector({
  emptyText = "Select match report",
  label,
  onChange,
  value,
}: LoadingSelectorProps<MatchReport>) {
  const loadMatches = useMemo(() => () => listMatches().then((data) => data.items), []);
  const { error, items, loading, refresh } = useLoadedItems(loadMatches);
  return (
    <EntitySelector
      emptyText={emptyText}
      error={error}
      getLabel={(item) => `Score ${item.total_score} / ${formatDate(item.created_at)}`}
      getMeta={(item) =>
        `${item.gaps.length} gaps / ${item.risk_flags.length} risks / ${idSuffix(item.match_report_id)}`
      }
      getValue={(item) => item.match_report_id}
      items={items}
      label={label}
      loading={loading}
      onRefresh={() => void refresh()}
      onValueChange={onChange}
      value={value}
    />
  );
}

export function ProjectSelector({
  emptyText = "Select project",
  label,
  onChange,
  value,
}: LoadingSelectorProps<ProjectRecord>) {
  const loadProjects = useMemo(() => () => listProjects().then((data) => data.items), []);
  const { error, items, loading, refresh } = useLoadedItems(loadProjects);
  return (
    <EntitySelector
      emptyText={emptyText}
      error={error}
      getLabel={(item) => `${item.name}${item.role ? ` / ${item.role}` : ""}`}
      getMeta={(item) => `${item.status} / ${idSuffix(item.id)}`}
      getValue={(item) => item.id}
      items={items}
      label={label}
      loading={loading}
      onRefresh={() => void refresh()}
      onValueChange={onChange}
      value={value}
    />
  );
}

export function ApplicationSelector({
  emptyText = "Select application",
  label,
  onChange,
  value,
}: LoadingSelectorProps<ApplicationRecord>) {
  const loadApplications = useMemo(
    () => () => listApplications().then((data) => data.items),
    [],
  );
  const { error, items, loading, refresh } = useLoadedItems(loadApplications);
  return (
    <EntitySelector
      emptyText={emptyText}
      error={error}
      getLabel={(item) => `${item.company} / ${item.role_title}`}
      getMeta={(item) => `${item.status} / ${item.priority} / ${idSuffix(item.application_id)}`}
      getValue={(item) => item.application_id}
      items={items}
      label={label}
      loading={loading}
      onRefresh={() => void refresh()}
      onValueChange={onChange}
      value={value}
    />
  );
}

export function AgentRunSelector({
  emptyText = "Select agent run",
  label,
  onChange,
  value,
}: LoadingSelectorProps<AgentRunRecord>) {
  const loadRuns = useMemo(() => () => listAgentRuns({ limit: 50 }).then((data) => data.items), []);
  const { error, items, loading, refresh } = useLoadedItems(loadRuns);
  return (
    <EntitySelector
      emptyText={emptyText}
      error={error}
      getLabel={(item) => `${item.workflow_name} / ${item.status}`}
      getMeta={(item) => `${formatDate(item.created_at)} / ${idSuffix(item.id)}`}
      getValue={(item) => item.id}
      items={items}
      label={label}
      loading={loading}
      onRefresh={() => void refresh()}
      onValueChange={onChange}
      value={value}
    />
  );
}

export function KnowledgeDocumentSelector({
  emptyText = "Select knowledge document",
  label,
  onChange,
  value,
}: LoadingSelectorProps<RagDocumentRecord>) {
  const loadDocuments = useMemo(
    () => () => listRagDocuments().then((data) => data.items),
    [],
  );
  const { error, items, loading, refresh } = useLoadedItems(loadDocuments);
  return (
    <EntitySelector
      emptyText={emptyText}
      error={error}
      getLabel={(item) => item.title}
      getMeta={(item) =>
        `${item.source_type} / ${item.index_status} / ${item.chunk_count} chunks / ${idSuffix(item.doc_id)}`
      }
      getValue={(item) => item.doc_id}
      items={items}
      label={label}
      loading={loading}
      onRefresh={() => void refresh()}
      onValueChange={onChange}
      value={value}
    />
  );
}

export function RagAnswerRunSelector({
  emptyText = "Select RAG answer",
  label,
  onChange,
  value,
}: LoadingSelectorProps<RagAnswerRunRecord>) {
  const loadAnswerRuns = useMemo(
    () => () => listRagAnswerRuns().then((data) => data.items),
    [],
  );
  const { error, items, loading, refresh } = useLoadedItems(loadAnswerRuns);
  return (
    <EntitySelector
      emptyText={emptyText}
      error={error}
      getLabel={(item) => item.question}
      getMeta={(item) =>
        `${item.grounded ? "grounded" : "ungrounded"} / ${item.uncertainty} / ${idSuffix(item.answer_run_id)}`
      }
      getValue={(item) => item.answer_run_id}
      items={items}
      label={label}
      loading={loading}
      onRefresh={() => void refresh()}
      onValueChange={onChange}
      value={value}
    />
  );
}

export function InterviewAnswerSelector({
  emptyText = "Select interview answer",
  label,
  onChange,
  value,
}: LoadingSelectorProps<InterviewAnswerRecord>) {
  const loadAnswers = useMemo(
    () => () => listInterviewAnswers().then((data) => data.items),
    [],
  );
  const { error, items, loading, refresh } = useLoadedItems(loadAnswers);
  return (
    <EntitySelector
      emptyText={emptyText}
      error={error}
      getLabel={(item) => item.answer_text_preview || `Answer ${idSuffix(item.id)}`}
      getMeta={(item) =>
        `overall ${item.scores.overall_average ?? "--"} / ${idSuffix(item.id)}`
      }
      getValue={(item) => item.id}
      items={items}
      label={label}
      loading={loading}
      onRefresh={() => void refresh()}
      onValueChange={onChange}
      value={value}
    />
  );
}

export function AgentWorkflowSelector({
  label,
  onChange,
  value,
}: {
  label: string;
  onChange: (value: string) => void;
  value: string;
}) {
  return (
    <EntitySelector
      emptyText="Select workflow"
      getLabel={(item) => item}
      getMeta={(item) => `workflow ${item}`}
      getValue={(item) => item}
      items={workflows}
      label={label}
      onValueChange={(nextValue) => onChange(nextValue)}
      value={value}
    />
  );
}
