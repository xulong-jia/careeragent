import { useEffect, useState } from "react";

import { MarkBadCasePanel } from "../components/MarkBadCasePanel";
import {
  AgentWorkflowSelector,
  AllResumeVersionSelector,
  ApplicationSelector,
  JDSelector,
  ProjectSelector,
  RagAnswerRunSelector,
  ResumeSelector,
} from "../components/EntitySelectors";
import {
  createAgentRun,
  cancelAgentRun,
  getAgentRun,
  listAgentRuns,
  listAgentRunSteps,
  resumeAgentRun,
  retryAgentRun,
} from "../api/agents";
import type {
  AgentFinalSummary,
  AgentRunCreateResponse,
  AgentRunDetailResponse,
  AgentRunRecord,
  AgentStepListResponse,
  AgentStepRecord,
} from "../types/api";

const workflowOptions = [
  "job_application_preparation",
  "interview_preparation",
  "application_review",
  "study_gap_planning",
];
const sensitiveKeyPatterns = [
  "raw_text",
  "jd_raw_text",
  "chunk_text",
  "full_text",
  "snippet",
  "api_key",
  "secret",
  "token",
];

type AgentRunsPageProps = {
  agentRuns: AgentRunRecord[];
  onAgentRunsChanged?: (runs: AgentRunRecord[]) => void;
};

function formatDate(value: string | null) {
  if (!value) {
    return "None";
  }
  return new Date(value).toLocaleString();
}

function formatDuration(value: number | null) {
  return value === null ? "None" : `${value} ms`;
}

function statusClass(status: string) {
  return `status-pill status-${status.replace(/_/g, "-")}`;
}

function isSensitiveKey(key: string) {
  const normalized = key.toLowerCase();
  return sensitiveKeyPatterns.some((pattern) => normalized.includes(pattern));
}

function sanitizeForDisplay(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => sanitizeForDisplay(item));
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([key, item]) => [
        key,
        isSensitiveKey(key) ? "[hidden]" : sanitizeForDisplay(item),
      ]),
    );
  }
  if (typeof value === "string" && value.length > 240) {
    return `${value.slice(0, 240)}... [truncated]`;
  }
  return value;
}

function SafeJsonBlock({
  label,
  value,
}: {
  label: string;
  value: unknown;
}) {
  return (
    <div className="refs-block">
      <strong>{label}</strong>
      <pre className="json-preview compact">
        {JSON.stringify(sanitizeForDisplay(value ?? {}), null, 2)}
      </pre>
    </div>
  );
}

function parseIdList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function FinalSummaryPanel({ summary }: { summary: AgentFinalSummary | null }) {
  if (!summary) {
    return null;
  }

  return (
    <div className="state-callout success">
      <strong>Final summary</strong>
      <span>
        Match score:{" "}
        {typeof summary.total_score === "number" ? summary.total_score : "None"}
      </span>
      {summary.top_strengths?.length ? (
        <ul className="compact-list">
          {summary.top_strengths.slice(0, 3).map((item) => (
            <li key={item}>Strength: {item}</li>
          ))}
        </ul>
      ) : null}
      {summary.top_gaps?.length ? (
        <ul className="compact-list">
          {summary.top_gaps.slice(0, 3).map((item) => (
            <li key={item}>Gap: {item}</li>
          ))}
        </ul>
      ) : null}
      {summary.next_actions?.length ? (
        <ul className="compact-list">
          {summary.next_actions.map((item) => (
            <li key={item}>Next: {item}</li>
          ))}
        </ul>
      ) : null}
      {summary.created_records?.length ? (
        <ul className="compact-list">
          {summary.created_records.map((item) => (
            <li key={`${item.type}-${item.id ?? "none"}`}>
              {item.type}: {item.id ?? "None"}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function BusinessState({ run }: { run: AgentRunRecord }) {
  if (run.status === "need_more_info") {
    return (
      <div className="state-callout warning">
        <strong>Need more info</strong>
        <SafeJsonBlock label="Missing slots" value={run.missing_slots ?? []} />
        <SafeJsonBlock label="Questions" value={run.questions ?? []} />
      </div>
    );
  }
  if (run.status === "failed") {
    return (
      <div className="state-callout danger">
        <strong>Workflow failed</strong>
        <span>{run.error_code ?? "agent_run_failed"}</span>
        <p>{run.error_message ?? "No error message."}</p>
      </div>
    );
  }
  if (run.status === "cancelled") {
    return (
      <div className="state-callout warning">
        <strong>Workflow cancelled</strong>
        <span>Run was stopped before producing a final output.</span>
      </div>
    );
  }
  if (run.status === "running" || run.status === "retrying") {
    return (
      <div className="state-callout warning">
        <strong>Workflow in progress</strong>
        <span>{run.status}</span>
      </div>
    );
  }
  if (run.status === "completed") {
    return (
      <div className="state-callout success">
        <strong>Workflow completed</strong>
        <span>Deterministic workflow outputs are linked below.</span>
      </div>
    );
  }
  return null;
}

function defaultRunBadCaseCategory(status: AgentRunRecord["status"]) {
  if (status === "failed") {
    return "agent_step_failed";
  }
  if (status === "need_more_info") {
    return "need_more_info_wrong";
  }
  return "other";
}

export function AgentRunsPage({
  agentRuns,
  onAgentRunsChanged,
}: AgentRunsPageProps) {
  const [runs, setRuns] = useState<AgentRunRecord[]>(agentRuns);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(
    agentRuns[0]?.id ?? null,
  );
  const [runDetail, setRunDetail] = useState<AgentRunDetailResponse | null>(null);
  const [steps, setSteps] = useState<AgentStepRecord[]>([]);
  const [selectedWorkflowName, setSelectedWorkflowName] = useState(
    workflowOptions[0],
  );
  const [resumeId, setResumeId] = useState("");
  const [resumeVersionId, setResumeVersionId] = useState("");
  const [jdId, setJdId] = useState("");
  const [projectIds, setProjectIds] = useState("");
  const [applicationId, setApplicationId] = useState("");
  const [createApplication, setCreateApplication] = useState(true);
  const [useRag, setUseRag] = useState(false);
  const [ragQuery, setRagQuery] = useState("");
  const [ragAnswerRunIds, setRagAnswerRunIds] = useState("");
  const [lastCreatedRun, setLastCreatedRun] =
    useState<AgentRunCreateResponse | null>(null);
  const [isListLoading, setIsListLoading] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [isActing, setIsActing] = useState(false);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [isStepsLoading, setIsStepsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const refreshRuns = async () => {
    setIsListLoading(true);
    try {
      const response = await listAgentRuns({ limit: 50 });
      setRuns(response.items);
      onAgentRunsChanged?.(response.items);
      if (!selectedRunId && response.items[0]) {
        setSelectedRunId(response.items[0].id);
      }
      return response.items;
    } finally {
      setIsListLoading(false);
    }
  };

  const loadRun = async (runId: string) => {
    setIsDetailLoading(true);
    setIsStepsLoading(true);
    setErrorMessage(null);
    try {
      const [detail, stepList] = await Promise.all([
        getAgentRun(runId),
        listAgentRunSteps(runId),
      ]);
      setSelectedRunId(runId);
      setRunDetail(detail);
      setSteps(stepList.steps);
    } catch (error) {
      setRunDetail(null);
      setSteps([]);
      setErrorMessage(error instanceof Error ? error.message : "加载 Agent run 失败。");
    } finally {
      setIsDetailLoading(false);
      setIsStepsLoading(false);
    }
  };

  useEffect(() => {
    setRuns(agentRuns);
    if (!selectedRunId && agentRuns[0]) {
      setSelectedRunId(agentRuns[0].id);
    }
  }, [agentRuns, selectedRunId]);

  useEffect(() => {
    const loadInitialRuns = async () => {
      try {
        const items = await refreshRuns();
        if (items[0]) {
          await loadRun(items[0].id);
        }
      } catch (error) {
        setErrorMessage(
          error instanceof Error ? error.message : "Agent runs 加载失败。",
        );
      }
    };
    void loadInitialRuns();
  }, []);

  const handleCreateRun = async () => {
    setIsCreating(true);
    setErrorMessage(null);
    setLastCreatedRun(null);
    try {
      const result = await createAgentRun({
        workflow_name: selectedWorkflowName,
        resume_id: resumeId.trim() || null,
        resume_version_id: resumeVersionId.trim() || null,
        jd_id: jdId.trim() || null,
        project_ids: parseIdList(projectIds),
        application_id: applicationId.trim() || null,
        create_application: createApplication,
        use_rag: useRag,
        rag_query: ragQuery.trim() || null,
        rag_answer_run_ids: parseIdList(ragAnswerRunIds),
      });
      setLastCreatedRun(result);
      const items = await refreshRuns();
      const createdRun = items.find((item) => item.id === result.run.id);
      await loadRun(createdRun?.id ?? result.run.id);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Agent run 创建失败。");
    } finally {
      setIsCreating(false);
    }
  };

  const actionPayload = () => ({
    resume_id: resumeId.trim() || null,
    resume_version_id: resumeVersionId.trim() || null,
    jd_id: jdId.trim() || null,
    project_ids: parseIdList(projectIds),
    application_id: applicationId.trim() || null,
    create_application: createApplication,
    use_rag: useRag,
    rag_query: ragQuery.trim() || null,
    rag_answer_run_ids: parseIdList(ragAnswerRunIds),
  });

  const handleRunAction = async (
    action: "resume" | "retry" | "cancel",
    runId: string,
  ) => {
    setIsActing(true);
    setErrorMessage(null);
    try {
      if (action === "resume") {
        await resumeAgentRun(runId, actionPayload());
      } else if (action === "retry") {
        await retryAgentRun(runId);
      } else {
        await cancelAgentRun(runId);
      }
      const items = await refreshRuns();
      const updated = items.find((item) => item.id === runId);
      await loadRun(updated?.id ?? runId);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Agent run action failed.",
      );
    } finally {
      setIsActing(false);
    }
  };

  const detailRun = runDetail?.run ?? null;

  return (
    <section className="page-stack" aria-labelledby="agent-runs-title">
      <div className="page-heading">
        <p className="eyebrow">Agent Workflow</p>
        <h2 id="agent-runs-title">Agent Runs</h2>
        <p>阶段 2.5 workflow workbench：创建、查看、resume、retry、cancel，并检查 step timeline。</p>
      </div>

      <article className="panel warning-panel">
        <div>
          <h3>安全边界</h3>
          <p>当前 Agent Workflow 是 deterministic state machine，不接真实 LLM，不自动投递，也不是自由聊天 Agent。</p>
          <p>不要输入真实简历、真实 JD、投递记录、面试复盘或 API Key；页面只展示 refs 和 short metadata。</p>
        </div>
        <span className="status-pill">Refs only</span>
      </article>

      {errorMessage ? <p className="error-text">{errorMessage}</p> : null}

      <div className="two-column wide-left">
        <article className="panel">
          <div className="panel-header">
            <h3>Create Agent Run</h3>
            <span className="status-pill muted">POST /api/agents/runs</span>
          </div>
          <div className="form-stack">
            <div className="selector-grid">
              <AgentWorkflowSelector
                label="Workflow"
                onChange={setSelectedWorkflowName}
                value={selectedWorkflowName}
              />
              <ResumeSelector
                emptyText="No resume context"
                label="Resume"
                onChange={(value) => setResumeId(value)}
                value={resumeId}
              />
              <AllResumeVersionSelector
                emptyText="No resume version context"
                label="Resume Version"
                onChange={(value) => setResumeVersionId(value)}
                value={resumeVersionId}
              />
              <JDSelector
                emptyText="No JD context"
                label="JD"
                onChange={(value) => setJdId(value)}
                value={jdId}
              />
              <ProjectSelector
                emptyText="No project context"
                label="Project"
                onChange={(value) => setProjectIds(value)}
                value={projectIds}
              />
              <ApplicationSelector
                emptyText="No existing application"
                label="Existing Application"
                onChange={(value) => setApplicationId(value)}
                value={applicationId}
              />
            </div>
            <label className="checkbox-row">
              <input
                checked={createApplication}
                type="checkbox"
                onChange={(event) => setCreateApplication(event.target.checked)}
              />
              Create draft if no existing application
            </label>
            <label className="checkbox-row">
              <input
                checked={useRag}
                type="checkbox"
                onChange={(event) => setUseRag(event.target.checked)}
              />
              Use RAG
            </label>
            <label>
              RAG Query
              <input
                disabled={!useRag}
                placeholder="optional synthetic query"
                value={ragQuery}
                onChange={(event) => setRagQuery(event.target.value)}
              />
            </label>
            <RagAnswerRunSelector
              emptyText="No RAG answer context"
              label="RAG Answer"
              onChange={(value) => setRagAnswerRunIds(value)}
              value={ragAnswerRunIds}
            />
            <button
              className="primary-action"
              disabled={isCreating}
              onClick={handleCreateRun}
              type="button"
            >
              {isCreating ? "Creating..." : "Create run"}
            </button>
          </div>
          {lastCreatedRun ? (
            <div className="agent-result">
              <span className={statusClass(lastCreatedRun.run.status)}>
                {lastCreatedRun.run.status}
              </span>
              <span>{lastCreatedRun.steps_count ?? 0} steps</span>
              <BusinessState run={lastCreatedRun.run} />
              <FinalSummaryPanel summary={lastCreatedRun.run.final_summary} />
            </div>
          ) : null}
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Runs List</h3>
            <span className="status-pill">{runs.length} items</span>
          </div>
          {isListLoading ? <p className="hint-text">Loading runs...</p> : null}
          {runs.length ? (
            <ul className="activity-list agent-run-list">
              {runs.map((run) => (
                <li
                  className={selectedRunId === run.id ? "selected-row" : undefined}
                  key={run.id}
                >
                  <div>
                    <strong>{run.id}</strong>
                    <small>{run.workflow_name}</small>
                  </div>
                  <span className={statusClass(run.status)}>{run.status}</span>
                  <span>{formatDate(run.created_at)}</span>
                  <span>{formatDuration(run.duration_ms)}</span>
                  <button
                    className="ghost-action"
                    onClick={() => void loadRun(run.id)}
                    type="button"
                  >
                    Detail
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <div className="empty-state">
              <strong>暂无 agent runs</strong>
              <span>创建 deterministic workflow run 后会显示在这里。</span>
            </div>
          )}
        </article>
      </div>

      <div className="two-column">
        <article className="panel">
          <div className="panel-header">
            <h3>Run Detail</h3>
            <span className={detailRun ? statusClass(detailRun.status) : "status-pill muted"}>
              {detailRun?.status ?? "None"}
            </span>
          </div>
          {isDetailLoading ? <p className="hint-text">Loading detail...</p> : null}
          {detailRun ? (
            <>
              <ul className="activity-list">
                <li>
                  <strong>ID</strong>
                  <span>{detailRun.id}</span>
                </li>
                <li>
                  <strong>Workflow</strong>
                  <span>{detailRun.workflow_name}</span>
                </li>
                <li>
                  <strong>Created</strong>
                  <span>{formatDate(detailRun.created_at)}</span>
                </li>
                <li>
                  <strong>Updated</strong>
                  <span>{formatDate(detailRun.updated_at)}</span>
                </li>
                <li>
                  <strong>Attempt</strong>
                  <span>{detailRun.retry_attempt}</span>
                </li>
                <li>
                  <strong>Duration</strong>
                  <span>{formatDuration(detailRun.duration_ms)}</span>
                </li>
                <li>
                  <strong>Steps</strong>
                  <span>{runDetail?.steps_count ?? steps.length}</span>
                </li>
              </ul>
              <BusinessState run={detailRun} />
              <div className="inline-actions">
                <button
                  className="ghost-action"
                  disabled={isActing || detailRun.status !== "need_more_info"}
                  onClick={() => void handleRunAction("resume", detailRun.id)}
                  type="button"
                >
                  Resume
                </button>
                <button
                  className="ghost-action"
                  disabled={isActing || detailRun.status !== "failed"}
                  onClick={() => void handleRunAction("retry", detailRun.id)}
                  type="button"
                >
                  Retry
                </button>
                <button
                  className="ghost-action"
                  disabled={
                    isActing ||
                    !["pending", "running", "need_more_info", "retrying"].includes(
                      detailRun.status,
                    )
                  }
                  onClick={() => void handleRunAction("cancel", detailRun.id)}
                  type="button"
                >
                  Cancel
                </button>
              </div>
              <FinalSummaryPanel summary={detailRun.final_summary} />
              <MarkBadCasePanel
                defaultCategory={defaultRunBadCaseCategory(detailRun.status)}
                defaultTitle="Agent run review"
                key={detailRun.id}
                sourceId={detailRun.id}
                sourceType="agent_run"
              />
              <SafeJsonBlock label="Input refs" value={detailRun.input_refs} />
              <SafeJsonBlock label="Output refs" value={detailRun.output_refs} />
              <SafeJsonBlock label="Final output ref" value={detailRun.final_output_ref} />
              <SafeJsonBlock label="Run config" value={detailRun.run_config} />
              {detailRun.bad_case_id ? (
                <SafeJsonBlock
                  label="Bad case payload"
                  value={{
                    bad_case_id: detailRun.bad_case_id,
                    ...detailRun.bad_case_payload,
                  }}
                />
              ) : null}
              {detailRun.missing_slots?.length ? (
                <SafeJsonBlock label="Missing slots" value={detailRun.missing_slots} />
              ) : null}
              {detailRun.questions?.length ? (
                <SafeJsonBlock label="Questions" value={detailRun.questions} />
              ) : null}
              {detailRun.error_code ? (
                <ul className="activity-list">
                  <li>
                    <strong>Error Code</strong>
                    <span>{detailRun.error_code}</span>
                  </li>
                  <li>
                    <strong>Error Message</strong>
                    <span>{detailRun.error_message ?? "None"}</span>
                  </li>
                </ul>
              ) : null}
            </>
          ) : (
            <div className="empty-state">
              <strong>未选择 run</strong>
              <span>选择 run 后查看 refs 和业务状态。</span>
            </div>
          )}
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Steps Timeline</h3>
            <span className="status-pill">{steps.length} steps</span>
          </div>
          {isStepsLoading ? <p className="hint-text">Loading steps...</p> : null}
          {steps.length ? (
            <div className="agent-timeline">
              {steps.map((step) => (
                <article className="timeline-step" key={step.id}>
                  <div className="timeline-step-header">
                    <div>
                      <strong>
                        Attempt {step.attempt} / {step.step_order}. {step.step_name}
                      </strong>
                      <small>{formatDuration(step.duration_ms)}</small>
                    </div>
                    <span className={statusClass(step.status)}>{step.status}</span>
                  </div>
                  <SafeJsonBlock label="Input refs" value={step.input_refs} />
                  <SafeJsonBlock label="Output refs" value={step.output_refs} />
                  <SafeJsonBlock
                    label="Privacy-safe payload"
                    value={step.privacy_safe_payload}
                  />
                  {step.error_code ? (
                    <ul className="compact-list">
                      <li>error_code: {step.error_code}</li>
                      <li>error_message: {step.error_message ?? "None"}</li>
                    </ul>
                  ) : null}
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <strong>暂无 steps</strong>
              <span>创建或选择 run 后查看 timeline。</span>
            </div>
          )}
        </article>
      </div>
    </section>
  );
}
