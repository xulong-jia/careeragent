import { useEffect, useState } from "react";

import {
  createApplication,
  getApplication,
  getApplicationStats,
  listApplications,
  updateApplication,
} from "../api/applications";
import type {
  ApplicationFilters,
  ApplicationRecord,
  ApplicationStats,
  ApplicationStatus,
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
  status: ApplicationStatus;
  applyDate: string;
  nextStepDate: string;
  interviewNotes: string;
  reflection: string;
  tags: string;
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
    status: "saved",
    applyDate: "",
    nextStepDate: "",
    interviewNotes: "",
    reflection: "",
    tags: "synthetic",
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
  const [statusUpdate, setStatusUpdate] = useState<ApplicationStatus>("applied");
  const [isLoading, setIsLoading] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

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
      setSelectedId(application.application_id);
      setSelectedApplication(application);
      setStatusUpdate(application.status);
    } catch (error) {
      setSelectedApplication(null);
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
        status: formState.status,
        apply_date: optionalText(formState.applyDate),
        next_step_date: optionalText(formState.nextStepDate),
        interview_notes: optionalText(formState.interviewNotes),
        reflection: optionalText(formState.reflection),
        tags: parseTags(formState.tags),
      });
      setFormState(initialFormState());
      const loadedItems = await refreshApplications(filters);
      setSelectedApplication(created);
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
      });
      setSelectedApplication(updated);
      await refreshApplications(filters);
      await refreshStats();
      setStatusMessage("Application status updated.");
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "状态更新失败。",
      );
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <section className="page-stack" aria-labelledby="applications-title">
      <div className="page-heading">
        <p className="eyebrow">Applications</p>
        <h2 id="applications-title">Application Tracker</h2>
        <p>手动记录投递进度，绑定可选 JD / Resume Version / Match Report refs；当前不自动投递、不接招聘网站、不接真实 LLM。</p>
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
                  placeholder="optional jd_0001"
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
                  placeholder="optional resume_0001_version_0001"
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
            </div>
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
                  </div>
                  <span className={statusClass(application.status)}>
                    {application.status}
                  </span>
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
                    {selectedApplication.match_report_id ?? "none"}
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
                    interview_notes: selectedApplication.interview_notes,
                    reflection: selectedApplication.reflection,
                  },
                  null,
                  2,
                )}
              </pre>
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
                <button
                  className="primary-action"
                  disabled={isUpdating}
                  onClick={handleUpdateStatus}
                  type="button"
                >
                  {isUpdating ? "Updating..." : "Update status"}
                </button>
              </div>
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
