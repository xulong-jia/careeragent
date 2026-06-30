import { useEffect, useState } from "react";

import {
  createApplication,
  getApplication,
  getApplicationStats,
  listApplicationStatusHistory,
  listApplications,
  updateApplication,
  updateApplicationReflection,
} from "../api/applications";
import type {
  ApplicationFilters,
  ApplicationPriority,
  ApplicationRecord,
  ApplicationStats,
  ApplicationStatus,
  ApplicationStatusHistoryRecord,
} from "../types/api";

const applicationStatuses: ApplicationStatus[] = [
  "saved",
  "ready_to_apply",
  "applied",
  "written_test",
  "first_interview",
  "second_interview",
  "hr_interview",
  "offer",
  "rejected",
  "withdrawn",
  "archived",
];

const applicationPriorities: ApplicationPriority[] = ["high", "medium", "low"];

type ApplicationTrackerPageProps = {
  applications: ApplicationRecord[];
  applicationStats: ApplicationStats | null;
  onApplicationsChanged: (applications: ApplicationRecord[]) => void;
  onApplicationStatsChanged: (stats: ApplicationStats | null) => void;
};

type ApplicationFormState = {
  company: string;
  roleTitle: string;
  roleCategory: string;
  jdId: string;
  resumeVersionId: string;
  matchReportId: string;
  agentRunId: string;
  status: ApplicationStatus;
  applyDate: string;
  nextStepDate: string;
  sourceUrl: string;
  location: string;
  priority: ApplicationPriority;
  notes: string;
  interviewNotes: string;
  reflection: string;
  interviewQuestionIds: string;
  lastContactDate: string;
  tags: string;
};

type DetailFormState = {
  nextStepDate: string;
  sourceUrl: string;
  location: string;
  priority: ApplicationPriority;
  notes: string;
  interviewNotes: string;
  reflection: string;
  interviewQuestionIds: string;
  lastContactDate: string;
  tags: string;
};

type ReflectionFormState = {
  reflection: string;
  interviewNotes: string;
  failureReason: string;
  preparationGaps: string;
  nextActions: string;
  weaknessTags: string;
  note: string;
};

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleString() : "None";
}

function optionalText(value: string) {
  const normalized = value.trim();
  return normalized || null;
}

function parseTags(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatCsv(values: string[]) {
  return values.join(", ");
}

function statusClass(status: string) {
  return `status-pill status-${status.replace(/_/g, "-")}`;
}

function initialFormState(): ApplicationFormState {
  return {
    company: "Synthetic Company",
    roleTitle: "AI Application Engineer",
    roleCategory: "AI Application",
    jdId: "",
    resumeVersionId: "",
    matchReportId: "",
    agentRunId: "",
    status: "saved",
    applyDate: "",
    nextStepDate: "",
    sourceUrl: "",
    location: "",
    priority: "medium",
    notes: "",
    interviewNotes: "",
    reflection: "",
    interviewQuestionIds: "",
    lastContactDate: "",
    tags: "synthetic",
  };
}

function detailFormFromApplication(
  application: ApplicationRecord | null,
): DetailFormState {
  return {
    nextStepDate: application?.next_step_date ?? "",
    sourceUrl: application?.source_url ?? "",
    location: application?.location ?? "",
    priority: application?.priority ?? "medium",
    notes: application?.notes ?? "",
    interviewNotes: application?.interview_notes ?? "",
    reflection: application?.reflection ?? "",
    interviewQuestionIds: formatCsv(application?.interview_question_ids ?? []),
    lastContactDate: application?.last_contact_date ?? "",
    tags: formatCsv(application?.tags ?? []),
  };
}

function initialReflectionState(): ReflectionFormState {
  return {
    reflection: "",
    interviewNotes: "",
    failureReason: "",
    preparationGaps: "",
    nextActions: "",
    weaknessTags: "",
    note: "",
  };
}

export function ApplicationTrackerPage({
  applications,
  applicationStats,
  onApplicationsChanged,
  onApplicationStatsChanged,
}: ApplicationTrackerPageProps) {
  const [items, setItems] = useState<ApplicationRecord[]>(applications);
  const [stats, setStats] = useState<ApplicationStats | null>(applicationStats);
  const [selectedId, setSelectedId] = useState<string | null>(
    applications[0]?.application_id ?? null,
  );
  const [selectedApplication, setSelectedApplication] =
    useState<ApplicationRecord | null>(null);
  const [filters, setFilters] = useState<ApplicationFilters>({});
  const [formState, setFormState] =
    useState<ApplicationFormState>(initialFormState);
  const [detailForm, setDetailForm] = useState<DetailFormState>(
    detailFormFromApplication(null),
  );
  const [reflectionForm, setReflectionForm] = useState<ReflectionFormState>(
    initialReflectionState,
  );
  const [statusHistory, setStatusHistory] = useState<
    ApplicationStatusHistoryRecord[]
  >([]);
  const [statusUpdate, setStatusUpdate] = useState<ApplicationStatus>("applied");
  const [statusReason, setStatusReason] = useState("");
  const [statusNote, setStatusNote] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [isSavingDetail, setIsSavingDetail] = useState(false);
  const [isSavingReflection, setIsSavingReflection] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const boardGroups = applicationStatuses.map((status) => ({
    status,
    applications: items.filter((application) => application.status === status),
  }));

  const refreshStats = async () => {
    const nextStats = await getApplicationStats();
    setStats(nextStats);
    onApplicationStatsChanged(nextStats);
    return nextStats;
  };

  const refreshApplications = async (nextFilters = filters) => {
    const response = await listApplications(nextFilters);
    setItems(response.items);
    onApplicationsChanged(response.items);
    await refreshStats();
    return response.items;
  };

  const loadApplication = async (applicationId: string) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const application = await getApplication(applicationId);
      const history = await listApplicationStatusHistory(applicationId);
      setSelectedId(application.application_id);
      setSelectedApplication(application);
      setDetailForm(detailFormFromApplication(application));
      setReflectionForm({
        ...initialReflectionState(),
        reflection: application.reflection ?? "",
        interviewNotes: application.interview_notes ?? "",
      });
      setStatusHistory(history.items);
      setStatusUpdate(application.status);
      setStatusReason("");
      setStatusNote("");
    } catch (error) {
      setSelectedApplication(null);
      setDetailForm(detailFormFromApplication(null));
      setReflectionForm(initialReflectionState());
      setStatusHistory([]);
      setErrorMessage(
        error instanceof Error ? error.message : "投递详情加载失败。",
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    setItems(applications);
    if (!selectedId && applications[0]) {
      setSelectedId(applications[0].application_id);
    }
  }, [applications, selectedId]);

  useEffect(() => {
    setStats(applicationStats);
  }, [applicationStats]);

  useEffect(() => {
    const loadInitialData = async () => {
      setIsLoading(true);
      try {
        const loadedItems = await refreshApplications({});
        if (loadedItems[0]) {
          await loadApplication(loadedItems[0].application_id);
        }
      } catch (error) {
        setErrorMessage(
          error instanceof Error ? error.message : "投递数据加载失败。",
        );
      } finally {
        setIsLoading(false);
      }
    };
    void loadInitialData();
  }, []);

  const handleCreate = async () => {
    setIsCreating(true);
    setErrorMessage(null);
    setStatusMessage(null);
    try {
      const created = await createApplication({
        company: formState.company,
        role_title: formState.roleTitle,
        role_category: optionalText(formState.roleCategory),
        jd_id: optionalText(formState.jdId),
        resume_version_id: optionalText(formState.resumeVersionId),
        match_report_id: optionalText(formState.matchReportId),
        agent_run_id: optionalText(formState.agentRunId),
        status: formState.status,
        apply_date: optionalText(formState.applyDate),
        next_step_date: optionalText(formState.nextStepDate),
        source_url: optionalText(formState.sourceUrl),
        location: optionalText(formState.location),
        priority: formState.priority,
        notes: optionalText(formState.notes),
        interview_notes: optionalText(formState.interviewNotes),
        reflection: optionalText(formState.reflection),
        interview_question_ids: parseTags(formState.interviewQuestionIds),
        last_contact_date: optionalText(formState.lastContactDate),
        tags: parseTags(formState.tags),
      });
      setFormState(initialFormState());
      const loadedItems = await refreshApplications(filters);
      setSelectedApplication(created);
      setDetailForm(detailFormFromApplication(created));
      setStatusHistory(created.status_history ?? []);
      setSelectedId(created.application_id);
      setStatusUpdate(created.status);
      if (!loadedItems.some((item) => item.application_id === created.application_id)) {
        setItems((current) => [created, ...current]);
      }
      setStatusMessage("Application created.");
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "创建投递记录失败。",
      );
    } finally {
      setIsCreating(false);
    }
  };

  const handleApplyFilters = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    setStatusMessage(null);
    try {
      const loadedItems = await refreshApplications(filters);
      if (loadedItems[0]) {
        await loadApplication(loadedItems[0].application_id);
      } else {
        setSelectedId(null);
        setSelectedApplication(null);
        setDetailForm(detailFormFromApplication(null));
        setReflectionForm(initialReflectionState());
        setStatusHistory([]);
      }
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "投递记录筛选失败。",
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateStatus = async () => {
    if (!selectedApplication) {
      setErrorMessage("请先选择一条投递记录。");
      return;
    }
    setIsUpdating(true);
    setErrorMessage(null);
    setStatusMessage(null);
    try {
      const updated = await updateApplication(selectedApplication.application_id, {
        status: statusUpdate,
        status_reason: optionalText(statusReason),
        status_note: optionalText(statusNote),
      });
      setSelectedApplication(updated);
      setDetailForm(detailFormFromApplication(updated));
      setStatusHistory(updated.status_history ?? []);
      await refreshApplications(filters);
      await refreshStats();
      setStatusReason("");
      setStatusNote("");
      setStatusMessage("Application status updated.");
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "状态更新失败。",
      );
    } finally {
      setIsUpdating(false);
    }
  };

  const handleSaveDetail = async () => {
    if (!selectedApplication) {
      setErrorMessage("请先选择一条投递记录。");
      return;
    }
    setIsSavingDetail(true);
    setErrorMessage(null);
    setStatusMessage(null);
    try {
      const updated = await updateApplication(selectedApplication.application_id, {
        next_step_date: optionalText(detailForm.nextStepDate),
        source_url: optionalText(detailForm.sourceUrl),
        location: optionalText(detailForm.location),
        priority: detailForm.priority,
        notes: optionalText(detailForm.notes),
        interview_notes: optionalText(detailForm.interviewNotes),
        reflection: optionalText(detailForm.reflection),
        interview_question_ids: parseTags(detailForm.interviewQuestionIds),
        last_contact_date: optionalText(detailForm.lastContactDate),
        tags: parseTags(detailForm.tags),
      });
      setSelectedApplication(updated);
      setDetailForm(detailFormFromApplication(updated));
      setStatusHistory(updated.status_history ?? []);
      await refreshApplications(filters);
      await refreshStats();
      setStatusMessage("Application detail saved.");
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "投递详情保存失败。",
      );
    } finally {
      setIsSavingDetail(false);
    }
  };

  const handleSaveReflection = async () => {
    if (!selectedApplication) {
      setErrorMessage("请先选择一条投递记录。");
      return;
    }
    setIsSavingReflection(true);
    setErrorMessage(null);
    setStatusMessage(null);
    try {
      const updated = await updateApplicationReflection(
        selectedApplication.application_id,
        {
          reflection: optionalText(reflectionForm.reflection),
          interview_notes: optionalText(reflectionForm.interviewNotes),
          failure_reason: optionalText(reflectionForm.failureReason),
          preparation_gaps: parseTags(reflectionForm.preparationGaps),
          next_actions: parseTags(reflectionForm.nextActions),
          weakness_tags: parseTags(reflectionForm.weaknessTags),
          note: optionalText(reflectionForm.note),
        },
      );
      setSelectedApplication(updated);
      setDetailForm(detailFormFromApplication(updated));
      setStatusHistory(updated.status_history ?? []);
      await refreshApplications(filters);
      await refreshStats();
      setStatusMessage("Application reflection saved.");
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "复盘保存失败。",
      );
    } finally {
      setIsSavingReflection(false);
    }
  };

  return (
    <section className="page-stack" aria-labelledby="applications-title">
      <div className="page-heading">
        <p className="eyebrow">Applications</p>
        <h2 id="applications-title">Application Tracker</h2>
        <p>手动记录投递进度，必须绑定 JD 与 Resume Version，可继续关联 Match Report 与 Agent Run；当前不自动投递、不接招聘网站、不接真实 LLM。</p>
      </div>

      <article className="panel warning-panel">
        <div>
          <h3>安全边界</h3>
          <p>只填写投递状态、日期和摘要备注，不粘贴完整简历、JD、投递材料、面试复盘或 API Key。</p>
        </div>
        <span className="status-pill">Manual tracking</span>
      </article>

      {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
      {statusMessage ? <p className="hint-text">{statusMessage}</p> : null}

      <div className="metric-grid">
        <div className="metric-card blue">
          <span>Total</span>
          <strong>{stats?.total_applications ?? 0}</strong>
          <small>applications</small>
        </div>
        <div className="metric-card green">
          <span>Active</span>
          <strong>{stats?.active_count ?? 0}</strong>
          <small>not closed</small>
        </div>
        <div className="metric-card amber">
          <span>Interview</span>
          <strong>{stats?.interview_count ?? 0}</strong>
          <small>in interview</small>
        </div>
        <div className="metric-card green">
          <span>Offer</span>
          <strong>{stats?.offer_count ?? 0}</strong>
          <small>offers</small>
        </div>
        <div className="metric-card red">
          <span>Rejected</span>
          <strong>{stats?.rejected_count ?? 0}</strong>
          <small>rejections</small>
        </div>
        <div className="metric-card amber">
          <span>Upcoming</span>
          <strong>{stats?.upcoming_count ?? 0}</strong>
          <small>next steps</small>
        </div>
        <div className="metric-card red">
          <span>Overdue</span>
          <strong>{stats?.overdue_count ?? 0}</strong>
          <small>needs follow-up</small>
        </div>
        <div className="metric-card green">
          <span>Applied to Offer</span>
          <strong>
            {Math.round((stats?.conversion.applied_to_offer_rate ?? 0) * 100)}%
          </strong>
          <small>conversion</small>
        </div>
      </div>

      <div className="two-column wide-left">
        <article className="panel">
          <div className="panel-header">
            <h3>Create Application</h3>
            <span className="status-pill muted">POST /api/applications</span>
          </div>
          <div className="form-stack">
            <div className="filter-grid">
              <label>
                Company
                <input
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      company: event.target.value,
                    }))
                  }
                  value={formState.company}
                />
              </label>
              <label>
                Role title
                <input
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      roleTitle: event.target.value,
                    }))
                  }
                  value={formState.roleTitle}
                />
              </label>
              <label>
                Role category
                <input
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      roleCategory: event.target.value,
                    }))
                  }
                  value={formState.roleCategory}
                />
              </label>
              <label>
                Status
                <select
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      status: event.target.value as ApplicationStatus,
                    }))
                  }
                  value={formState.status}
                >
                  {applicationStatuses.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Apply date
                <input
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      applyDate: event.target.value,
                    }))
                  }
                  type="date"
                  value={formState.applyDate}
                />
              </label>
              <label>
                Next step date
                <input
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      nextStepDate: event.target.value,
                    }))
                  }
                  type="date"
                  value={formState.nextStepDate}
                />
              </label>
              <label>
                Source URL
                <input
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      sourceUrl: event.target.value,
                    }))
                  }
                  value={formState.sourceUrl}
                />
              </label>
              <label>
                Location
                <input
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      location: event.target.value,
                    }))
                  }
                  value={formState.location}
                />
              </label>
              <label>
                Priority
                <select
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      priority: event.target.value as ApplicationPriority,
                    }))
                  }
                  value={formState.priority}
                >
                  {applicationPriorities.map((priority) => (
                    <option key={priority} value={priority}>
                      {priority}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Last contact date
                <input
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      lastContactDate: event.target.value,
                    }))
                  }
                  type="date"
                  value={formState.lastContactDate}
                />
              </label>
            </div>
            <div className="filter-grid">
              <label>
                JD ID
                <input
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      jdId: event.target.value,
                    }))
                  }
                  placeholder="required jd_0001"
                  value={formState.jdId}
                />
              </label>
              <label>
                Resume Version ID
                <input
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      resumeVersionId: event.target.value,
                    }))
                  }
                  placeholder="required resume_0001_version_0001"
                  value={formState.resumeVersionId}
                />
              </label>
              <label>
                Match Report ID
                <input
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      matchReportId: event.target.value,
                    }))
                  }
                  placeholder="optional match_0001"
                  value={formState.matchReportId}
                />
              </label>
              <label>
                Agent Run ID
                <input
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      agentRunId: event.target.value,
                    }))
                  }
                  placeholder="optional agent_run_0001"
                  value={formState.agentRunId}
                />
              </label>
            </div>
            <label>
              Notes
              <textarea
                className="metadata-textarea compact-textarea"
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    notes: event.target.value,
                  }))
                }
                placeholder="运营备注摘要"
                value={formState.notes}
              />
            </label>
            <label>
              Interview notes
              <textarea
                className="metadata-textarea compact-textarea"
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    interviewNotes: event.target.value,
                  }))
                }
                placeholder="摘要即可，不粘贴完整面试复盘"
                value={formState.interviewNotes}
              />
            </label>
            <label>
              Reflection
              <textarea
                className="metadata-textarea compact-textarea"
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    reflection: event.target.value,
                  }))
                }
                placeholder="摘要即可"
                value={formState.reflection}
              />
            </label>
            <label>
              Interview question IDs
              <input
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    interviewQuestionIds: event.target.value,
                  }))
                }
                placeholder="comma separated"
                value={formState.interviewQuestionIds}
              />
            </label>
            <label>
              Tags
              <input
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    tags: event.target.value,
                  }))
                }
                placeholder="comma separated"
                value={formState.tags}
              />
            </label>
            <button
              className="primary-action"
              disabled={isCreating}
              onClick={handleCreate}
              type="button"
            >
              {isCreating ? "Creating..." : "Create application"}
            </button>
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Filters</h3>
            <span className="status-pill muted">GET /api/applications</span>
          </div>
          <div className="form-stack">
            <div className="filter-grid">
              <label>
                Status
                <select
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      status: event.target.value as ApplicationStatus | "",
                    }))
                  }
                  value={filters.status ?? ""}
                >
                  <option value="">All</option>
                  {applicationStatuses.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Company
                <input
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      company: event.target.value,
                    }))
                  }
                  value={filters.company ?? ""}
                />
              </label>
              <label>
                Role category
                <input
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      roleCategory: event.target.value,
                    }))
                  }
                  value={filters.roleCategory ?? ""}
                />
              </label>
              <label>
                JD ID
                <input
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      jdId: event.target.value,
                    }))
                  }
                  placeholder="optional jd_0001"
                  value={filters.jdId ?? ""}
                />
              </label>
              <label>
                Resume Version ID
                <input
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      resumeVersionId: event.target.value,
                    }))
                  }
                  placeholder="optional resume_0001_version_0001"
                  value={filters.resumeVersionId ?? ""}
                />
              </label>
              <label>
                Agent Run ID
                <input
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      agentRunId: event.target.value,
                    }))
                  }
                  placeholder="optional agent_run_0001"
                  value={filters.agentRunId ?? ""}
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
                  placeholder="optional match_0001"
                  value={filters.matchReportId ?? ""}
                />
              </label>
              <label>
                Priority
                <select
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      priority: event.target.value as ApplicationPriority | "",
                    }))
                  }
                  value={filters.priority ?? ""}
                >
                  <option value="">All</option>
                  {applicationPriorities.map((priority) => (
                    <option key={priority} value={priority}>
                      {priority}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <button
              className="primary-action"
              disabled={isLoading}
              onClick={handleApplyFilters}
              type="button"
            >
              {isLoading ? "Loading..." : "Apply filters"}
            </button>
          </div>
        </article>
      </div>

      <article className="panel">
        <div className="panel-header">
          <h3>Application Board</h3>
          <span className="status-pill">{items.length} cards</span>
        </div>
        <div className="application-board">
          {boardGroups.map((group) => (
            <section className="application-column" key={group.status}>
              <div className="application-column-header">
                <span className={statusClass(group.status)}>{group.status}</span>
                <strong>{group.applications.length}</strong>
              </div>
              {group.applications.length ? (
                group.applications.map((application) => (
                  <button
                    className="application-card"
                    key={application.application_id}
                    onClick={() => void loadApplication(application.application_id)}
                    type="button"
                  >
                    <strong>{application.company}</strong>
                    <span>{application.role_title}</span>
                    <small>
                      {application.priority} /{" "}
                      {application.next_step_date ?? "no next step"}
                    </small>
                    <small>
                      JD {application.jd_id ?? "none"} / Resume{" "}
                      {application.resume_version_id ?? "none"}
                    </small>
                    <small>
                      Match {application.match_report_id ?? "none"} / Agent{" "}
                      {application.agent_run_id ?? "none"}
                    </small>
                  </button>
                ))
              ) : (
                <span className="empty-column">No cards</span>
              )}
            </section>
          ))}
        </div>
      </article>

      <div className="two-column wide-left">
        <article className="panel">
          <div className="panel-header">
            <h3>Application List</h3>
            <span className="status-pill">{items.length} items</span>
          </div>
          {items.length ? (
            <ul className="activity-list bad-case-list">
              {items.map((application) => (
                <li
                  className={
                    selectedId === application.application_id ? "selected-row" : undefined
                  }
                  key={application.application_id}
                >
                  <div>
                    <strong>{application.company}</strong>
                    <small>{application.role_title}</small>
                    <small>{application.application_id}</small>
                    <small>
                      JD {application.jd_id ?? "none"} / Resume{" "}
                      {application.resume_version_id ?? "none"}
                    </small>
                    <small>
                      Match {application.match_report_id ?? "none"} / Agent{" "}
                      {application.agent_run_id ?? "none"}
                    </small>
                  </div>
                  <span className={statusClass(application.status)}>
                    {application.status}
                  </span>
                  <span>{application.priority}</span>
                  <span>{application.role_category ?? "No category"}</span>
                  <span>{application.next_step_date ?? "No next step"}</span>
                  <button
                    className="ghost-action"
                    onClick={() => void loadApplication(application.application_id)}
                    type="button"
                  >
                    Detail
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <div className="empty-state">
              <strong>暂无投递记录</strong>
              <span>创建手动 tracking 记录后会显示在这里。</span>
            </div>
          )}
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Application Detail</h3>
            <span className={selectedApplication ? statusClass(selectedApplication.status) : "status-pill muted"}>
              {selectedApplication?.status ?? "None"}
            </span>
          </div>
          {selectedApplication ? (
            <>
              <ul className="activity-list">
                <li>
                  <strong>Company</strong>
                  <span>{selectedApplication.company}</span>
                </li>
                <li>
                  <strong>Role</strong>
                  <span>{selectedApplication.role_title}</span>
                </li>
                <li>
                  <strong>Refs</strong>
                  <span>
                    JD {selectedApplication.jd_id ?? "none"} / Resume Version{" "}
                    {selectedApplication.resume_version_id ?? "none"} / Match{" "}
                    {selectedApplication.match_report_id ?? "none"} / Agent{" "}
                    {selectedApplication.agent_run_id ?? "none"}
                  </span>
                </li>
                <li>
                  <strong>Apply date</strong>
                  <span>{selectedApplication.apply_date ?? "None"}</span>
                </li>
                <li>
                  <strong>Next step</strong>
                  <span>{selectedApplication.next_step_date ?? "None"}</span>
                </li>
                <li>
                  <strong>Priority</strong>
                  <span>{selectedApplication.priority}</span>
                </li>
                <li>
                  <strong>Location</strong>
                  <span>{selectedApplication.location ?? "None"}</span>
                </li>
                <li>
                  <strong>Source</strong>
                  <span>{selectedApplication.source_url ?? "None"}</span>
                </li>
                <li>
                  <strong>Last contact</strong>
                  <span>{selectedApplication.last_contact_date ?? "None"}</span>
                </li>
                <li>
                  <strong>Interview question refs</strong>
                  <span>
                    {selectedApplication.interview_question_ids.join(", ") || "None"}
                  </span>
                </li>
                <li>
                  <strong>Tags</strong>
                  <span>{selectedApplication.tags.join(", ") || "None"}</span>
                </li>
                <li>
                  <strong>Created</strong>
                  <span>{formatDate(selectedApplication.created_at)}</span>
                </li>
              </ul>
              <pre className="json-preview compact">
                {JSON.stringify(
                  {
                    notes: selectedApplication.notes,
                    interview_notes: selectedApplication.interview_notes,
                    reflection: selectedApplication.reflection,
                  },
                  null,
                  2,
                )}
              </pre>
              <div className="form-stack detail-edit-panel">
                <div className="filter-grid">
                  <label>
                    Next step date
                    <input
                      onChange={(event) =>
                        setDetailForm((current) => ({
                          ...current,
                          nextStepDate: event.target.value,
                        }))
                      }
                      type="date"
                      value={detailForm.nextStepDate}
                    />
                  </label>
                  <label>
                    Last contact date
                    <input
                      onChange={(event) =>
                        setDetailForm((current) => ({
                          ...current,
                          lastContactDate: event.target.value,
                        }))
                      }
                      type="date"
                      value={detailForm.lastContactDate}
                    />
                  </label>
                  <label>
                    Priority
                    <select
                      onChange={(event) =>
                        setDetailForm((current) => ({
                          ...current,
                          priority: event.target.value as ApplicationPriority,
                        }))
                      }
                      value={detailForm.priority}
                    >
                      {applicationPriorities.map((priority) => (
                        <option key={priority} value={priority}>
                          {priority}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Location
                    <input
                      onChange={(event) =>
                        setDetailForm((current) => ({
                          ...current,
                          location: event.target.value,
                        }))
                      }
                      value={detailForm.location}
                    />
                  </label>
                  <label>
                    Source URL
                    <input
                      onChange={(event) =>
                        setDetailForm((current) => ({
                          ...current,
                          sourceUrl: event.target.value,
                        }))
                      }
                      value={detailForm.sourceUrl}
                    />
                  </label>
                  <label>
                    Interview question IDs
                    <input
                      onChange={(event) =>
                        setDetailForm((current) => ({
                          ...current,
                          interviewQuestionIds: event.target.value,
                        }))
                      }
                      value={detailForm.interviewQuestionIds}
                    />
                  </label>
                </div>
                <label>
                  Notes
                  <textarea
                    className="metadata-textarea compact-textarea"
                    onChange={(event) =>
                      setDetailForm((current) => ({
                        ...current,
                        notes: event.target.value,
                      }))
                    }
                    value={detailForm.notes}
                  />
                </label>
                <label>
                  Interview notes
                  <textarea
                    className="metadata-textarea compact-textarea"
                    onChange={(event) =>
                      setDetailForm((current) => ({
                        ...current,
                        interviewNotes: event.target.value,
                      }))
                    }
                    value={detailForm.interviewNotes}
                  />
                </label>
                <label>
                  Reflection
                  <textarea
                    className="metadata-textarea compact-textarea"
                    onChange={(event) =>
                      setDetailForm((current) => ({
                        ...current,
                        reflection: event.target.value,
                      }))
                    }
                    value={detailForm.reflection}
                  />
                </label>
                <label>
                  Tags
                  <input
                    onChange={(event) =>
                      setDetailForm((current) => ({
                        ...current,
                        tags: event.target.value,
                      }))
                    }
                    value={detailForm.tags}
                  />
                </label>
                <button
                  className="primary-action"
                  disabled={isSavingDetail}
                  onClick={handleSaveDetail}
                  type="button"
                >
                  {isSavingDetail ? "Saving..." : "Save detail"}
                </button>
              </div>
              <div className="inline-form">
                <select
                  onChange={(event) =>
                    setStatusUpdate(event.target.value as ApplicationStatus)
                  }
                  value={statusUpdate}
                >
                  {applicationStatuses.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
                <input
                  onChange={(event) => setStatusReason(event.target.value)}
                  placeholder="status reason"
                  value={statusReason}
                />
                <input
                  onChange={(event) => setStatusNote(event.target.value)}
                  placeholder="status note"
                  value={statusNote}
                />
                <button
                  className="primary-action"
                  disabled={isUpdating}
                  onClick={handleUpdateStatus}
                  type="button"
                >
                  {isUpdating ? "Updating..." : "Update status"}
                </button>
              </div>
              <div className="form-stack detail-edit-panel">
                <label>
                  Reflection
                  <textarea
                    className="metadata-textarea compact-textarea"
                    onChange={(event) =>
                      setReflectionForm((current) => ({
                        ...current,
                        reflection: event.target.value,
                      }))
                    }
                    value={reflectionForm.reflection}
                  />
                </label>
                <label>
                  Interview feedback
                  <textarea
                    className="metadata-textarea compact-textarea"
                    onChange={(event) =>
                      setReflectionForm((current) => ({
                        ...current,
                        interviewNotes: event.target.value,
                      }))
                    }
                    value={reflectionForm.interviewNotes}
                  />
                </label>
                <div className="filter-grid">
                  <label>
                    Failure reason
                    <input
                      onChange={(event) =>
                        setReflectionForm((current) => ({
                          ...current,
                          failureReason: event.target.value,
                        }))
                      }
                      value={reflectionForm.failureReason}
                    />
                  </label>
                  <label>
                    Preparation gaps
                    <input
                      onChange={(event) =>
                        setReflectionForm((current) => ({
                          ...current,
                          preparationGaps: event.target.value,
                        }))
                      }
                      placeholder="comma separated"
                      value={reflectionForm.preparationGaps}
                    />
                  </label>
                  <label>
                    Next actions
                    <input
                      onChange={(event) =>
                        setReflectionForm((current) => ({
                          ...current,
                          nextActions: event.target.value,
                        }))
                      }
                      placeholder="comma separated"
                      value={reflectionForm.nextActions}
                    />
                  </label>
                  <label>
                    Weakness tags
                    <input
                      onChange={(event) =>
                        setReflectionForm((current) => ({
                          ...current,
                          weaknessTags: event.target.value,
                        }))
                      }
                      placeholder="comma separated"
                      value={reflectionForm.weaknessTags}
                    />
                  </label>
                </div>
                <label>
                  Note
                  <input
                    onChange={(event) =>
                      setReflectionForm((current) => ({
                        ...current,
                        note: event.target.value,
                      }))
                    }
                    value={reflectionForm.note}
                  />
                </label>
                <button
                  className="primary-action"
                  disabled={isSavingReflection}
                  onClick={handleSaveReflection}
                  type="button"
                >
                  {isSavingReflection ? "Saving..." : "Save reflection"}
                </button>
              </div>
              <ul className="activity-list status-history-list">
                {statusHistory.map((history) => (
                  <li key={history.history_id}>
                    <div>
                      <strong>
                        {history.from_status ?? "created"} -&gt; {history.to_status}
                      </strong>
                      <small>{formatDate(history.changed_at)}</small>
                    </div>
                    <span>{history.reason ?? "No reason"}</span>
                    <span>{history.note ?? "No note"}</span>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <div className="empty-state">
              <strong>未选择投递记录</strong>
              <span>从列表选择记录后查看详情和更新状态。</span>
            </div>
          )}
        </article>
      </div>
    </section>
  );
}
