import { useEffect, useState } from "react";

import { MarkBadCasePanel } from "../components/MarkBadCasePanel";
import {
  createAgentRun,
  getAgentRun,
  listAgentRuns,
  listAgentRunSteps,
} from "../api/agents";
import type {
  AgentRunCreateResponse,
  AgentRunDetailResponse,
  AgentRunRecord,
  AgentStepListResponse,
  AgentStepRecord,
} from "../types/api";

const workflowName = "job_application_preparation";
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
  if (run.status === "completed") {
    return (
      <div className="state-callout success">
        <strong>Workflow completed</strong>
        <span>Deterministic final summary is available in output refs.</span>
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
  const [resumeId, setResumeId] = useState("");
  const [resumeVersionId, setResumeVersionId] = useState("");
  const [jdId, setJdId] = useState("");
  const [useRag, setUseRag] = useState(false);
  const [ragQuery, setRagQuery] = useState("");
  const [lastCreatedRun, setLastCreatedRun] =
    useState<AgentRunCreateResponse | null>(null);
  const [isListLoading, setIsListLoading] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
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
        workflow_name: workflowName,
        resume_id: resumeId.trim() || null,
        resume_version_id: resumeVersionId.trim() || null,
        jd_id: jdId.trim() || null,
        use_rag: useRag,
        rag_query: ragQuery.trim() || null,
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

  const detailRun = runDetail?.run ?? null;

  return (
    <section className="page-stack" aria-labelledby="agent-runs-title">
      <div className="page-heading">
        <p className="eyebrow">Agent Workflow</p>
        <h2 id="agent-runs-title">Agent Runs</h2>
        <p>阶段 4E 前端最小 UI：创建 deterministic workflow run，查看 run list、detail 和 steps timeline。</p>
      </div>

      <article className="panel warning-panel">
        <div>
          <h3>安全边界</h3>
          <p>当前 Agent Workflow 是 deterministic state machine，不接真实 LLM，不自动投递，也不是自由聊天 Agent。</p>
          <p>不要输入真实简历、真实 JD、投递记录、面试复盘或 API Key；页面只展示 refs、IDs 和 short metadata。</p>
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
            <label>
              Workflow
              <input readOnly value={workflowName} />
            </label>
            <label>
              Resume ID
              <input
                placeholder="resume_0001"
                value={resumeId}
                onChange={(event) => setResumeId(event.target.value)}
              />
            </label>
            <label>
              Resume Version ID
              <input
                placeholder="resume_0001_version_0001"
                value={resumeVersionId}
                onChange={(event) => setResumeVersionId(event.target.value)}
              />
            </label>
            <label>
              JD ID
              <input
                placeholder="jd_0001"
                value={jdId}
                onChange={(event) => setJdId(event.target.value)}
              />
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
                  <strong>Duration</strong>
                  <span>{formatDuration(detailRun.duration_ms)}</span>
                </li>
                <li>
                  <strong>Steps</strong>
                  <span>{runDetail?.steps_count ?? steps.length}</span>
                </li>
              </ul>
              <BusinessState run={detailRun} />
              <MarkBadCasePanel
                defaultCategory={defaultRunBadCaseCategory(detailRun.status)}
                defaultTitle="Agent run review"
                key={detailRun.id}
                sourceId={detailRun.id}
                sourceType="agent_run"
              />
              <SafeJsonBlock label="Input refs" value={detailRun.input_refs} />
              <SafeJsonBlock label="Output refs" value={detailRun.output_refs} />
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
                        {step.step_order}. {step.step_name}
                      </strong>
                      <small>{formatDuration(step.duration_ms)}</small>
                    </div>
                    <span className={statusClass(step.status)}>{step.status}</span>
                  </div>
                  <SafeJsonBlock label="Input refs" value={step.input_refs} />
                  <SafeJsonBlock label="Output refs" value={step.output_refs} />
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
