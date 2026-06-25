import { useEffect, useState } from "react";

import {
  generateStudyPlan,
  getStudyPlan,
  listStudyPlans,
  updateStudyPlanTaskStatus,
} from "../api/studyPlans";
import type {
  StudyPlanListFilters,
  StudyPlanRecord,
  StudyPlanStatus,
  StudySourceRef,
  StudyTask,
  StudyTaskStatus,
} from "../types/api";

type GenerateFormState = {
  targetRole: string;
  profileId: string;
  matchReportId: string;
  projectRewriteId: string;
  interviewAnswerIds: string;
  weaknessTags: string;
  availableHoursPerWeek: string;
  horizonWeeks: string;
};

type FilterState = {
  status: StudyPlanStatus | "";
  targetRole: string;
  profileId: string;
  matchReportId: string;
};

const taskStatusOptions: StudyTaskStatus[] = [
  "todo",
  "in_progress",
  "done",
  "blocked",
  "skipped",
];

const planStatusOptions: StudyPlanStatus[] = ["active", "completed", "archived"];

function initialGenerateForm(): GenerateFormState {
  return {
    targetRole: "",
    profileId: "",
    matchReportId: "",
    projectRewriteId: "",
    interviewAnswerIds: "",
    weaknessTags: "",
    availableHoursPerWeek: "5",
    horizonWeeks: "4",
  };
}

function initialFilters(): FilterState {
  return {
    status: "",
    targetRole: "",
    profileId: "",
    matchReportId: "",
  };
}

function optionalText(value: string): string | null {
  const normalized = value.trim();
  return normalized || null;
}

function parseCsv(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseBoundedInteger(
  value: string,
  fallback: number,
  min: number,
  max: number,
  label: string,
): number {
  const normalized = value.trim();
  if (!normalized) {
    return fallback;
  }
  const parsed = Number(normalized);
  if (!Number.isInteger(parsed) || parsed < min || parsed > max) {
    throw new Error(`${label} must be an integer from ${min} to ${max}.`);
  }
  return parsed;
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}

function countTasks(plan: StudyPlanRecord): number {
  return plan.phases.reduce((total, phase) => total + phase.tasks.length, 0);
}

function statusLabel(status: string): string {
  return status.replace(/_/g, " ");
}

function statusClass(status: string): string {
  if (status === "done" || status === "completed") {
    return "status-pill status-completed";
  }
  if (status === "blocked") {
    return "status-pill status-blocked";
  }
  if (status === "skipped" || status === "archived") {
    return "status-pill status-skipped";
  }
  if (status === "in_progress") {
    return "status-pill status-running";
  }
  return "status-pill muted";
}

function renderResource(resource: Record<string, unknown>, index: number): string {
  const label = typeof resource.label === "string" ? resource.label : null;
  const type = typeof resource.type === "string" ? resource.type : null;
  return [type, label].filter(Boolean).join(" / ") || `Resource ${index + 1}`;
}

function SourceRefList({ refs }: { refs: StudySourceRef[] }) {
  if (!refs.length) {
    return <span className="muted-inline">No source refs</span>;
  }
  return (
    <ul className="compact-list source-ref-list">
      {refs.map((ref) => (
        <li key={`${ref.source_type}-${ref.source_id}-${ref.field}-${ref.preview}`}>
          <strong>{ref.label}</strong>
          <span>
            {ref.source_type}/{ref.field}: {ref.preview}
          </span>
        </li>
      ))}
    </ul>
  );
}

function TaskCard({
  isUpdating,
  onUpdateStatus,
  task,
}: {
  isUpdating: boolean;
  onUpdateStatus: (taskId: string, status: StudyTaskStatus) => void;
  task: StudyTask;
}) {
  return (
    <article className="study-task-card">
      <div className="study-task-header">
        <div>
          <strong>{task.title}</strong>
          <small>
            {task.task_id} / {task.source_gap}
          </small>
        </div>
        <div className="study-task-actions">
          <span className={statusClass(task.priority)}>{task.priority}</span>
          <select
            disabled={isUpdating}
            onChange={(event) =>
              onUpdateStatus(task.task_id, event.target.value as StudyTaskStatus)
            }
            value={task.status}
          >
            {taskStatusOptions.map((status) => (
              <option key={status} value={status}>
                {statusLabel(status)}
              </option>
            ))}
          </select>
        </div>
      </div>
      <p className="snippet-text">{task.description}</p>
      {task.due_hint ? <span className="status-pill muted">{task.due_hint}</span> : null}
      <div className="study-task-grid">
        <div>
          <strong>Acceptance criteria</strong>
          {task.acceptance_criteria.length ? (
            <ul className="compact-list">
              {task.acceptance_criteria.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : (
            <p className="helper-text">No criteria</p>
          )}
        </div>
        <div>
          <strong>Evidence required</strong>
          {task.evidence_required.length ? (
            <ul className="compact-list">
              {task.evidence_required.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : (
            <p className="helper-text">No evidence listed</p>
          )}
        </div>
      </div>
      <SourceRefList refs={task.source_refs} />
    </article>
  );
}

export function StudyPlanPage() {
  const [generateForm, setGenerateForm] =
    useState<GenerateFormState>(initialGenerateForm);
  const [filters, setFilters] = useState<FilterState>(initialFilters);
  const [plans, setPlans] = useState<StudyPlanRecord[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<StudyPlanRecord | null>(null);
  const [listLoading, setListLoading] = useState(false);
  const [generateLoading, setGenerateLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [updateTaskLoading, setUpdateTaskLoading] = useState<string | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const generateValidationError =
    !generateForm.targetRole.trim() && !generateForm.profileId.trim()
      ? "Target role or Profile ID is required."
      : null;

  const refreshPlans = async (nextFilters: FilterState = filters) => {
    setListLoading(true);
    setPageError(null);
    try {
      const filterPayload: StudyPlanListFilters = {
        status: nextFilters.status,
        target_role: optionalText(nextFilters.targetRole) ?? undefined,
        profile_id: optionalText(nextFilters.profileId) ?? undefined,
        match_report_id: optionalText(nextFilters.matchReportId) ?? undefined,
      };
      const response = await listStudyPlans(filterPayload);
      setPlans(response.items);
      setSelectedPlan((current) =>
        current
          ? response.items.find((item) => item.id === current.id) ?? current
          : response.items[0] ?? null,
      );
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Study plan list load failed.");
    } finally {
      setListLoading(false);
    }
  };

  const refreshPlanDetail = async (planId: string) => {
    setDetailLoading(true);
    setPageError(null);
    try {
      const detail = await getStudyPlan(planId);
      setSelectedPlan(detail);
      setPlans((current) =>
        current.map((plan) => (plan.id === detail.id ? detail : plan)),
      );
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Study plan detail load failed.");
    } finally {
      setDetailLoading(false);
    }
  };

  useEffect(() => {
    void refreshPlans();
  }, []);

  const handleGenerate = async () => {
    if (generateValidationError) {
      setPageError(generateValidationError);
      return;
    }
    setGenerateLoading(true);
    setPageError(null);
    setStatusMessage(null);
    try {
      const plan = await generateStudyPlan({
        target_role: optionalText(generateForm.targetRole),
        profile_id: optionalText(generateForm.profileId),
        match_report_id: optionalText(generateForm.matchReportId),
        project_rewrite_id: optionalText(generateForm.projectRewriteId),
        interview_answer_ids: parseCsv(generateForm.interviewAnswerIds),
        weakness_tags: parseCsv(generateForm.weaknessTags),
        available_hours_per_week: parseBoundedInteger(
          generateForm.availableHoursPerWeek,
          5,
          1,
          80,
          "Available hours per week",
        ),
        horizon_weeks: parseBoundedInteger(
          generateForm.horizonWeeks,
          4,
          1,
          52,
          "Horizon weeks",
        ),
      });
      setSelectedPlan(plan);
      setPlans((current) => [plan, ...current.filter((item) => item.id !== plan.id)]);
      setStatusMessage(`Generated study plan ${plan.id}.`);
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Study plan generation failed.");
    } finally {
      setGenerateLoading(false);
    }
  };

  const handleApplyFilters = () => {
    void refreshPlans();
  };

  const handleSelectPlan = (plan: StudyPlanRecord) => {
    setSelectedPlan(plan);
    setPageError(null);
    setStatusMessage(null);
    void refreshPlanDetail(plan.id);
  };

  const handleUpdateTaskStatus = async (
    taskId: string,
    status: StudyTaskStatus,
  ) => {
    if (!selectedPlan) {
      setPageError("Select a study plan before updating task status.");
      return;
    }
    setUpdateTaskLoading(taskId);
    setPageError(null);
    setStatusMessage(null);
    try {
      const updated = await updateStudyPlanTaskStatus(selectedPlan.id, taskId, {
        status,
      });
      setSelectedPlan(updated);
      setPlans((current) =>
        current.map((plan) => (plan.id === updated.id ? updated : plan)),
      );
      setStatusMessage(`Updated ${taskId} to ${statusLabel(status)}.`);
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Task status update failed.");
    } finally {
      setUpdateTaskLoading(null);
    }
  };

  return (
    <section className="page-stack" aria-labelledby="study-plan-title">
      <div className="page-heading">
        <p className="eyebrow">Study Plan Center</p>
        <h2 id="study-plan-title">Study Plan Center</h2>
        <p>Deterministic learning phases, evidence tasks and task status tracking.</p>
      </div>

      <article className="panel warning-panel">
        <div>
          <h3>Privacy Boundary</h3>
          <p>Source refs render previews only. This page does not render Resume/JD full raw text or saved answer text.</p>
        </div>
        <span className="status-pill">No LLM</span>
      </article>

      {pageError ? <p className="error-text">{pageError}</p> : null}
      {generateValidationError ? (
        <p className="error-text">{generateValidationError}</p>
      ) : null}
      {statusMessage ? <p className="hint-text">{statusMessage}</p> : null}

      <div className="two-column wide-left">
        <article className="panel">
          <div className="panel-header">
            <h3>Generate Study Plan</h3>
            <span className="status-pill muted">POST /api/study-plans/generate</span>
          </div>
          <div className="form-stack">
            <div className="filter-grid">
              <label>
                Target role
                <input
                  onChange={(event) =>
                    setGenerateForm((current) => ({
                      ...current,
                      targetRole: event.target.value,
                    }))
                  }
                  value={generateForm.targetRole}
                />
              </label>
              <label>
                Profile ID
                <input
                  onChange={(event) =>
                    setGenerateForm((current) => ({
                      ...current,
                      profileId: event.target.value,
                    }))
                  }
                  value={generateForm.profileId}
                />
              </label>
              <label>
                Match Report ID
                <input
                  onChange={(event) =>
                    setGenerateForm((current) => ({
                      ...current,
                      matchReportId: event.target.value,
                    }))
                  }
                  value={generateForm.matchReportId}
                />
              </label>
              <label>
                Project Rewrite ID
                <input
                  onChange={(event) =>
                    setGenerateForm((current) => ({
                      ...current,
                      projectRewriteId: event.target.value,
                    }))
                  }
                  value={generateForm.projectRewriteId}
                />
              </label>
              <label>
                Interview Answer IDs
                <input
                  onChange={(event) =>
                    setGenerateForm((current) => ({
                      ...current,
                      interviewAnswerIds: event.target.value,
                    }))
                  }
                  placeholder="interview_answer_..."
                  value={generateForm.interviewAnswerIds}
                />
              </label>
              <label>
                Weakness tags
                <input
                  onChange={(event) =>
                    setGenerateForm((current) => ({
                      ...current,
                      weaknessTags: event.target.value,
                    }))
                  }
                  placeholder="weak_structure, overclaim_risk"
                  value={generateForm.weaknessTags}
                />
              </label>
              <label>
                Available hours / week
                <input
                  inputMode="numeric"
                  onChange={(event) =>
                    setGenerateForm((current) => ({
                      ...current,
                      availableHoursPerWeek: event.target.value,
                    }))
                  }
                  value={generateForm.availableHoursPerWeek}
                />
              </label>
              <label>
                Horizon weeks
                <input
                  inputMode="numeric"
                  onChange={(event) =>
                    setGenerateForm((current) => ({
                      ...current,
                      horizonWeeks: event.target.value,
                    }))
                  }
                  value={generateForm.horizonWeeks}
                />
              </label>
            </div>
            <button
              className="primary-action"
              disabled={Boolean(generateValidationError) || generateLoading}
              onClick={handleGenerate}
              type="button"
            >
              {generateLoading ? "Generating..." : "Generate Study Plan"}
            </button>
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Plan Filters</h3>
            <button
              className="ghost-action"
              disabled={listLoading}
              onClick={handleApplyFilters}
              type="button"
            >
              {listLoading ? "Loading..." : "Refresh"}
            </button>
          </div>
          <div className="form-stack">
            <div className="filter-grid single">
              <label>
                Status
                <select
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      status: event.target.value as StudyPlanStatus | "",
                    }))
                  }
                  value={filters.status}
                >
                  <option value="">All</option>
                  {planStatusOptions.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Target role
                <input
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      targetRole: event.target.value,
                    }))
                  }
                  value={filters.targetRole}
                />
              </label>
              <label>
                Profile ID
                <input
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      profileId: event.target.value,
                    }))
                  }
                  value={filters.profileId}
                />
              </label>
              <label>
                Match Report ID
                <input
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      matchReportId: event.target.value,
                    }))
                  }
                  value={filters.matchReportId}
                />
              </label>
            </div>
          </div>
        </article>
      </div>

      <div className="two-column wide-left">
        <article className="panel">
          <div className="panel-header">
            <h3>Study Plan List</h3>
            <span className="status-pill muted">{plans.length} records</span>
          </div>
          {plans.length === 0 ? (
            <div className="empty-state compact">
              <strong>No study plans</strong>
              <span>Generate or refresh filtered plans.</span>
            </div>
          ) : (
            <ul className="activity-list study-plan-list">
              {plans.map((plan) => (
                <li
                  className={
                    selectedPlan?.id === plan.id ? "selected-row" : undefined
                  }
                  key={plan.id}
                >
                  <div>
                    <strong>{plan.target_role}</strong>
                    <small>
                      {plan.id} / {formatDate(plan.created_at)}
                    </small>
                    <span>
                      {plan.phases.length} phases / {countTasks(plan)} tasks / updated {formatDate(plan.updated_at)}
                    </span>
                  </div>
                  <span className={statusClass(plan.status)}>{plan.status}</span>
                  <button
                    className="ghost-action"
                    onClick={() => handleSelectPlan(plan)}
                    type="button"
                  >
                    Select
                  </button>
                </li>
              ))}
            </ul>
          )}
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Selected Plan</h3>
            {selectedPlan ? (
              <button
                className="ghost-action"
                disabled={detailLoading}
                onClick={() => void refreshPlanDetail(selectedPlan.id)}
                type="button"
              >
                {detailLoading ? "Loading..." : "Refresh Detail"}
              </button>
            ) : null}
          </div>
          {selectedPlan ? (
            <div className="study-plan-summary">
              <div className="readonly-grid">
                <span>ID: {selectedPlan.id}</span>
                <span>Target: {selectedPlan.target_role}</span>
                <span>Status: {selectedPlan.status}</span>
                <span>Tasks: {countTasks(selectedPlan)}</span>
                <span>Created: {formatDate(selectedPlan.created_at)}</span>
                <span>Updated: {formatDate(selectedPlan.updated_at)}</span>
              </div>
              <h4>Source refs</h4>
              <SourceRefList refs={selectedPlan.source_refs} />
            </div>
          ) : (
            <div className="empty-state compact">
              <strong>No selected plan</strong>
              <span>Select a study plan from the list.</span>
            </div>
          )}
        </article>
      </div>

      {selectedPlan ? (
        <article className="panel">
          <div className="panel-header">
            <h3>Plan Detail</h3>
            <span className="status-pill muted">{selectedPlan.phases.length} phases</span>
          </div>
          {selectedPlan.phases.length === 0 ? (
            <div className="empty-state compact">
              <strong>No phases</strong>
              <span>This plan has no generated phases.</span>
            </div>
          ) : (
            <div className="study-phase-list">
              {selectedPlan.phases.map((phase) => (
                <section className="study-phase-card" key={phase.phase_id}>
                  <div className="panel-header">
                    <div>
                      <h4>{phase.phase}</h4>
                      <p className="helper-text">{phase.goal}</p>
                    </div>
                    <span className="status-pill muted">{phase.phase_id}</span>
                  </div>

                  <div className="study-phase-meta">
                    <div>
                      <strong>Resources</strong>
                      {phase.resources.length ? (
                        <ul className="compact-list">
                          {phase.resources.map((resource, index) => (
                            <li key={`${phase.phase_id}-resource-${index}`}>
                              {renderResource(resource, index)}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="helper-text">No resources</p>
                      )}
                    </div>
                    <div>
                      <strong>Deliverables</strong>
                      {phase.deliverables.length ? (
                        <ul className="compact-list">
                          {phase.deliverables.map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="helper-text">No deliverables</p>
                      )}
                    </div>
                    <div>
                      <strong>Acceptance criteria</strong>
                      {phase.acceptance_criteria.length ? (
                        <ul className="compact-list">
                          {phase.acceptance_criteria.map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="helper-text">No criteria</p>
                      )}
                    </div>
                  </div>

                  {phase.tasks.length === 0 ? (
                    <div className="empty-state compact">
                      <strong>No tasks</strong>
                      <span>This phase has no tasks.</span>
                    </div>
                  ) : (
                    <div className="study-task-list">
                      {phase.tasks.map((task) => (
                        <TaskCard
                          isUpdating={updateTaskLoading === task.task_id}
                          key={task.task_id}
                          onUpdateStatus={handleUpdateTaskStatus}
                          task={task}
                        />
                      ))}
                    </div>
                  )}
                </section>
              ))}
            </div>
          )}
        </article>
      ) : null}
    </section>
  );
}
