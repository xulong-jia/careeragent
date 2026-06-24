import { useEffect, useState } from "react";

import {
  createProject,
  getProject,
  listProjects,
  runProjectRewrite,
  updateProject,
} from "../api/projects";
import type {
  ProjectCreateRequest,
  ProjectRecord,
  ProjectRewriteRecord,
  ProjectRewriteRequest,
  ProjectStatus,
  ProjectUpdateRequest,
} from "../types/api";

type ProjectOptimizationPageProps = {
  projects: ProjectRecord[];
  onProjectsChanged: (projects: ProjectRecord[]) => void;
};

type ProjectFormState = {
  name: string;
  role: string;
  period: string;
  background: string;
  techStack: string;
  responsibilities: string;
  results: string;
  evidence: string;
  profileId: string;
  resumeVersionId: string;
  status: ProjectStatus;
};

type RewriteFormState = {
  jdId: string;
  resumeVersionId: string;
  matchReportId: string;
  profileId: string;
};

const defaultEvidence = `[
  {
    "type": "manual_note",
    "description": "Synthetic project evidence summary"
  }
]`;

function initialProjectForm(): ProjectFormState {
  return {
    name: "Synthetic Backend Project",
    role: "Backend Engineer",
    period: "2026-01 to 2026-04",
    background: "Local project facts confirmed by the user.",
    techStack: "Python, FastAPI",
    responsibilities: "Built deterministic API endpoints\nValidated API responses",
    results: "Created repeatable local smoke checks",
    evidence: defaultEvidence,
    profileId: "",
    resumeVersionId: "",
    status: "active",
  };
}

function initialRewriteForm(): RewriteFormState {
  return {
    jdId: "",
    resumeVersionId: "",
    matchReportId: "",
    profileId: "",
  };
}

function optionalText(value: string): string | null {
  const normalized = value.trim();
  return normalized || null;
}

function parseList(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseEvidence(value: string): Record<string, unknown>[] {
  const parsed = JSON.parse(value) as unknown;
  if (!Array.isArray(parsed)) {
    throw new Error("Evidence must be a JSON array.");
  }
  if (
    parsed.some(
      (item) =>
        typeof item !== "object" || item === null || Array.isArray(item),
    )
  ) {
    throw new Error("Every evidence item must be a JSON object.");
  }
  return parsed as Record<string, unknown>[];
}

function getValidationError(form: ProjectFormState): string | null {
  if (!form.name.trim()) {
    return "Project name is required.";
  }
  try {
    parseEvidence(form.evidence);
  } catch (error) {
    return error instanceof Error ? error.message : "Evidence JSON is invalid.";
  }
  return null;
}

function formToPayload(
  form: ProjectFormState,
): ProjectCreateRequest | ProjectUpdateRequest {
  return {
    profile_id: optionalText(form.profileId),
    resume_version_id: optionalText(form.resumeVersionId),
    name: form.name.trim(),
    role: optionalText(form.role),
    period: optionalText(form.period),
    background: optionalText(form.background),
    tech_stack: parseList(form.techStack),
    responsibilities: parseList(form.responsibilities),
    results: parseList(form.results),
    evidence: parseEvidence(form.evidence),
    status: form.status,
  };
}

function projectToForm(project: ProjectRecord): ProjectFormState {
  return {
    name: project.name,
    role: project.role ?? "",
    period: project.period ?? "",
    background: project.background ?? "",
    techStack: project.tech_stack.join(", "),
    responsibilities: project.responsibilities.join("\n"),
    results: project.results.join("\n"),
    evidence: JSON.stringify(project.evidence, null, 2),
    profileId: project.profile_id ?? "",
    resumeVersionId: project.resume_version_id ?? "",
    status: project.status,
  };
}

function rewritePayloadFromForm(form: RewriteFormState): ProjectRewriteRequest {
  return {
    jd_id: form.jdId.trim(),
    resume_version_id: optionalText(form.resumeVersionId),
    match_report_id: optionalText(form.matchReportId),
    profile_id: optionalText(form.profileId),
  };
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}

function statusClass(status: string): string {
  return `status-pill status-${status.replace(/_/g, "-")}`;
}

function severityClass(severity: string): string {
  return `status-pill severity-${severity}`;
}

function ListPreview({ items }: { items: string[] }) {
  if (items.length === 0) {
    return <span className="muted-inline">None</span>;
  }
  return (
    <div className="tag-row">
      {items.map((item) => (
        <span className="status-pill muted" key={item}>
          {item}
        </span>
      ))}
    </div>
  );
}

export function ProjectOptimizationPage({
  projects,
  onProjectsChanged,
}: ProjectOptimizationPageProps) {
  const [items, setItems] = useState<ProjectRecord[]>(projects);
  const [selectedId, setSelectedId] = useState<string | null>(
    projects[0]?.id ?? null,
  );
  const [selectedProject, setSelectedProject] = useState<ProjectRecord | null>(
    projects[0] ?? null,
  );
  const [projectForm, setProjectForm] =
    useState<ProjectFormState>(initialProjectForm);
  const [rewriteForm, setRewriteForm] =
    useState<RewriteFormState>(initialRewriteForm);
  const [rewriteResult, setRewriteResult] =
    useState<ProjectRewriteRecord | null>(null);
  const [listLoading, setListLoading] = useState(false);
  const [saveLoading, setSaveLoading] = useState(false);
  const [rewriteLoading, setRewriteLoading] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const validationError = getValidationError(projectForm);
  const canSave = !validationError && !saveLoading;
  const canRunRewrite =
    Boolean(selectedProject) && Boolean(rewriteForm.jdId.trim()) && !rewriteLoading;

  const syncProjects = (nextProjects: ProjectRecord[]) => {
    setItems(nextProjects);
    onProjectsChanged(nextProjects);
  };

  const refreshProjects = async () => {
    setListLoading(true);
    setPageError(null);
    try {
      const response = await listProjects();
      syncProjects(response.items);
      const nextSelected =
        response.items.find((item) => item.id === selectedId) ??
        response.items[0] ??
        null;
      setSelectedId(nextSelected?.id ?? null);
      setSelectedProject(nextSelected);
      if (nextSelected) {
        setProjectForm(projectToForm(nextSelected));
      }
    } catch (error) {
      setPageError(
        error instanceof Error ? error.message : "Project list load failed.",
      );
    } finally {
      setListLoading(false);
    }
  };

  const loadProject = async (projectId: string) => {
    setListLoading(true);
    setPageError(null);
    setStatusMessage(null);
    try {
      const project = await getProject(projectId);
      setSelectedId(project.id);
      setSelectedProject(project);
      setProjectForm(projectToForm(project));
      setRewriteForm((current) => ({
        ...current,
        profileId: project.profile_id ?? current.profileId,
        resumeVersionId: project.resume_version_id ?? current.resumeVersionId,
      }));
      setRewriteResult(null);
    } catch (error) {
      setPageError(
        error instanceof Error ? error.message : "Project detail load failed.",
      );
    } finally {
      setListLoading(false);
    }
  };

  useEffect(() => {
    setItems(projects);
    if (!selectedProject && projects[0]) {
      setSelectedId(projects[0].id);
      setSelectedProject(projects[0]);
      setProjectForm(projectToForm(projects[0]));
    }
  }, [projects, selectedProject]);

  useEffect(() => {
    void refreshProjects();
  }, []);

  const handleCreate = async () => {
    if (validationError) {
      setPageError(validationError);
      return;
    }
    setSaveLoading(true);
    setPageError(null);
    setStatusMessage(null);
    try {
      const created = await createProject(
        formToPayload(projectForm) as ProjectCreateRequest,
      );
      const response = await listProjects();
      syncProjects(response.items);
      setSelectedId(created.id);
      setSelectedProject(created);
      setProjectForm(projectToForm(created));
      setRewriteResult(null);
      setStatusMessage("Project created.");
    } catch (error) {
      setPageError(
        error instanceof Error ? error.message : "Project creation failed.",
      );
    } finally {
      setSaveLoading(false);
    }
  };

  const handleUpdate = async () => {
    if (!selectedProject) {
      setPageError("Select a project before updating.");
      return;
    }
    if (validationError) {
      setPageError(validationError);
      return;
    }
    setSaveLoading(true);
    setPageError(null);
    setStatusMessage(null);
    try {
      const updated = await updateProject(
        selectedProject.id,
        formToPayload(projectForm) as ProjectUpdateRequest,
      );
      const response = await listProjects();
      syncProjects(response.items);
      setSelectedId(updated.id);
      setSelectedProject(updated);
      setProjectForm(projectToForm(updated));
      setStatusMessage("Project updated.");
    } catch (error) {
      setPageError(
        error instanceof Error ? error.message : "Project update failed.",
      );
    } finally {
      setSaveLoading(false);
    }
  };

  const handleRunRewrite = async () => {
    if (!selectedProject) {
      setPageError("Select a project before running rewrite.");
      return;
    }
    if (!rewriteForm.jdId.trim()) {
      setPageError("JD ID is required for rewrite.");
      return;
    }
    setRewriteLoading(true);
    setPageError(null);
    setStatusMessage(null);
    try {
      const rewrite = await runProjectRewrite(
        selectedProject.id,
        rewritePayloadFromForm(rewriteForm),
      );
      setRewriteResult(rewrite);
      setStatusMessage("Project rewrite generated. Suggestions were not written back.");
    } catch (error) {
      setRewriteResult(null);
      setPageError(
        error instanceof Error ? error.message : "Project rewrite failed.",
      );
    } finally {
      setRewriteLoading(false);
    }
  };

  return (
    <section className="page-stack" aria-labelledby="project-optimization-title">
      <div className="page-heading">
        <p className="eyebrow">Project Optimization</p>
        <h2 id="project-optimization-title">Project Optimization</h2>
        <p>维护用户确认过的项目事实，并基于 JD 运行 deterministic rewrite 建议；当前不接真实 LLM，不自动写回 Resume Version，不生成项目事实。</p>
      </div>

      <article className="panel warning-panel">
        <div>
          <h3>事实边界</h3>
          <p>只填写已确认项目事实和 evidence 摘要。Rewrite 结果只作为建议展示，不能新增公司、用户量、收益、准确率、上线状态、业务规模或不存在的技术栈。</p>
        </div>
        <span className="status-pill">No auto-writeback</span>
      </article>

      {pageError ? <p className="error-text">{pageError}</p> : null}
      {validationError ? <p className="error-text">{validationError}</p> : null}
      {statusMessage ? <p className="hint-text">{statusMessage}</p> : null}

      <div className="two-column wide-left">
        <article className="panel">
          <div className="panel-header">
            <h3>Project Facts</h3>
            <span className="status-pill muted">POST / PATCH /api/projects</span>
          </div>
          <div className="form-stack">
            <div className="filter-grid">
              <label>
                Name
                <input
                  onChange={(event) =>
                    setProjectForm((current) => ({
                      ...current,
                      name: event.target.value,
                    }))
                  }
                  value={projectForm.name}
                />
              </label>
              <label>
                Status
                <select
                  onChange={(event) =>
                    setProjectForm((current) => ({
                      ...current,
                      status: event.target.value as ProjectStatus,
                    }))
                  }
                  value={projectForm.status}
                >
                  <option value="active">active</option>
                  <option value="archived">archived</option>
                </select>
              </label>
              <label>
                Role
                <input
                  onChange={(event) =>
                    setProjectForm((current) => ({
                      ...current,
                      role: event.target.value,
                    }))
                  }
                  value={projectForm.role}
                />
              </label>
              <label>
                Period
                <input
                  onChange={(event) =>
                    setProjectForm((current) => ({
                      ...current,
                      period: event.target.value,
                    }))
                  }
                  value={projectForm.period}
                />
              </label>
              <label>
                Profile ID optional
                <input
                  onChange={(event) =>
                    setProjectForm((current) => ({
                      ...current,
                      profileId: event.target.value,
                    }))
                  }
                  value={projectForm.profileId}
                />
              </label>
              <label>
                Resume Version ID optional
                <input
                  onChange={(event) =>
                    setProjectForm((current) => ({
                      ...current,
                      resumeVersionId: event.target.value,
                    }))
                  }
                  value={projectForm.resumeVersionId}
                />
              </label>
            </div>
            <label>
              Background
              <textarea
                className="metadata-textarea compact-textarea"
                onChange={(event) =>
                  setProjectForm((current) => ({
                    ...current,
                    background: event.target.value,
                  }))
                }
                value={projectForm.background}
              />
            </label>
            <label>
              Tech stack
              <textarea
                className="metadata-textarea compact-textarea"
                onChange={(event) =>
                  setProjectForm((current) => ({
                    ...current,
                    techStack: event.target.value,
                  }))
                }
                value={projectForm.techStack}
              />
            </label>
            <label>
              Responsibilities
              <textarea
                className="metadata-textarea compact-textarea"
                onChange={(event) =>
                  setProjectForm((current) => ({
                    ...current,
                    responsibilities: event.target.value,
                  }))
                }
                value={projectForm.responsibilities}
              />
            </label>
            <label>
              Results
              <textarea
                className="metadata-textarea compact-textarea"
                onChange={(event) =>
                  setProjectForm((current) => ({
                    ...current,
                    results: event.target.value,
                  }))
                }
                value={projectForm.results}
              />
            </label>
            <label>
              Evidence JSON array
              <textarea
                className="metadata-textarea resume-json-editor"
                onChange={(event) =>
                  setProjectForm((current) => ({
                    ...current,
                    evidence: event.target.value,
                  }))
                }
                value={projectForm.evidence}
              />
            </label>
            <div className="inline-form">
              <button
                className="primary-action"
                disabled={!canSave}
                onClick={handleCreate}
                type="button"
              >
                {saveLoading ? "Saving..." : "Create project"}
              </button>
              <button
                className="ghost-action"
                disabled={!selectedProject || !canSave}
                onClick={handleUpdate}
                type="button"
              >
                {saveLoading ? "Saving..." : "Update selected"}
              </button>
              <button
                className="ghost-action"
                disabled={listLoading}
                onClick={() => void refreshProjects()}
                type="button"
              >
                {listLoading ? "Loading..." : "Refresh"}
              </button>
            </div>
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Project List</h3>
            <span className="status-pill muted">{items.length} records</span>
          </div>
          {items.length === 0 ? (
            <div className="empty-state compact">
              <strong>No projects</strong>
              <span>Create a project fact record before running rewrite.</span>
            </div>
          ) : (
            <ul className="activity-list project-list">
              {items.map((project) => (
                <li
                  className={project.id === selectedId ? "selected-row" : ""}
                  key={project.id}
                >
                  <div>
                    <strong>{project.name}</strong>
                    <small>{project.role ?? "No role"} / {project.period ?? "No period"}</small>
                  </div>
                  <span>{project.tech_stack.join(", ") || "No stack"}</span>
                  <span className={statusClass(project.status)}>
                    {project.status}
                  </span>
                  <button
                    className="ghost-action"
                    onClick={() => void loadProject(project.id)}
                    type="button"
                  >
                    Select
                  </button>
                </li>
              ))}
            </ul>
          )}
        </article>
      </div>

      <div className="two-column">
        <article className="panel">
          <div className="panel-header">
            <h3>Project Detail</h3>
            <span className="status-pill muted">Facts only</span>
          </div>
          {selectedProject ? (
            <div className="project-detail">
              <div className="readonly-grid">
                <span>ID: {selectedProject.id}</span>
                <span>Status: {selectedProject.status}</span>
                <span>Profile: {selectedProject.profile_id ?? "None"}</span>
                <span>
                  Resume version: {selectedProject.resume_version_id ?? "None"}
                </span>
                <span>Created: {formatDate(selectedProject.created_at)}</span>
                <span>Updated: {formatDate(selectedProject.updated_at)}</span>
              </div>
              <h4>Tech Stack</h4>
              <ListPreview items={selectedProject.tech_stack} />
              <h4>Responsibilities</h4>
              <ul className="compact-list">
                {selectedProject.responsibilities.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              <h4>Results</h4>
              <ul className="compact-list">
                {selectedProject.results.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              <h4>Evidence</h4>
              <pre className="json-preview compact">
                {JSON.stringify(selectedProject.evidence, null, 2)}
              </pre>
            </div>
          ) : (
            <div className="empty-state compact">
              <strong>No selected project</strong>
              <span>Select or create a project to view detail.</span>
            </div>
          )}
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Run Rewrite</h3>
            <span className="status-pill muted">
              POST /api/projects/:id/rewrite
            </span>
          </div>
          <div className="form-stack">
            <label>
              JD ID required
              <input
                onChange={(event) =>
                  setRewriteForm((current) => ({
                    ...current,
                    jdId: event.target.value,
                  }))
                }
                value={rewriteForm.jdId}
              />
            </label>
            <div className="filter-grid">
              <label>
                Resume Version ID optional
                <input
                  onChange={(event) =>
                    setRewriteForm((current) => ({
                      ...current,
                      resumeVersionId: event.target.value,
                    }))
                  }
                  value={rewriteForm.resumeVersionId}
                />
              </label>
              <label>
                Match Report ID optional
                <input
                  onChange={(event) =>
                    setRewriteForm((current) => ({
                      ...current,
                      matchReportId: event.target.value,
                    }))
                  }
                  value={rewriteForm.matchReportId}
                />
              </label>
              <label>
                Profile ID optional
                <input
                  onChange={(event) =>
                    setRewriteForm((current) => ({
                      ...current,
                      profileId: event.target.value,
                    }))
                  }
                  value={rewriteForm.profileId}
                />
              </label>
            </div>
            <button
              className="primary-action"
              disabled={!canRunRewrite}
              onClick={handleRunRewrite}
              type="button"
            >
              {rewriteLoading ? "Running..." : "Run rewrite"}
            </button>
            <p className="helper-text">Rewrite 只返回建议，不会自动修改项目事实或保存 Resume Version。</p>
          </div>
        </article>
      </div>

      <article className="panel">
        <div className="panel-header">
          <h3>Rewrite Result</h3>
          <span className="status-pill muted">
            {rewriteResult?.rewrite_strategy ?? "No result"}
          </span>
        </div>
        {rewriteResult ? (
          <div className="rewrite-result">
            <div className="readonly-grid">
              <span>Rewrite: {rewriteResult.id}</span>
              <span>Project: {rewriteResult.project_id}</span>
              <span>JD: {rewriteResult.jd_id}</span>
              <span>Created: {formatDate(rewriteResult.created_at)}</span>
            </div>

            <section>
              <h4>Matched Points</h4>
              {rewriteResult.matched_points.length === 0 ? (
                <div className="empty-state compact">
                  <span>No matched JD skills found.</span>
                </div>
              ) : (
                <ul className="result-card-list">
                  {rewriteResult.matched_points.map((point) => (
                    <li key={`${point.skill}-${point.source_field}-${point.project_text}`}>
                      <strong>{point.skill}</strong>
                      <span>{point.match_type} / {point.source_field}</span>
                      <p>{point.project_text}</p>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section>
              <h4>Missing Points</h4>
              {rewriteResult.missing_points.length === 0 ? (
                <div className="empty-state compact">
                  <span>No missing JD skills detected.</span>
                </div>
              ) : (
                <ul className="result-card-list">
                  {rewriteResult.missing_points.map((point) => (
                    <li key={`${point.requirement}-${point.requirement_type}`}>
                      <strong>{point.requirement}</strong>
                      <span>{point.requirement_type} / {point.priority}</span>
                      <p>{point.reason}</p>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section>
              <h4>Evidence Required</h4>
              {rewriteResult.evidence_required.length === 0 ? (
                <div className="empty-state compact">
                  <span>No additional evidence required by deterministic rules.</span>
                </div>
              ) : (
                <ul className="result-card-list evidence-list">
                  {rewriteResult.evidence_required.map((item) => (
                    <li key={`${item.type}-${item.source_field}-${item.project_text}`}>
                      <strong>{item.type}</strong>
                      <span>{item.source_field}</span>
                      <p>{item.project_text}</p>
                      <small>{item.reason}</small>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section>
              <h4>Rewritten Bullets</h4>
              {rewriteResult.rewritten_bullets.length === 0 ? (
                <div className="empty-state compact">
                  <span>No rewrite suggestions generated.</span>
                </div>
              ) : (
                <ul className="rewrite-bullet-list">
                  {rewriteResult.rewritten_bullets.map((bullet) => (
                    <li key={`${bullet.before}-${bullet.after}`}>
                      <div className="before-after-grid">
                        <div>
                          <strong>Before</strong>
                          <p>{bullet.before}</p>
                        </div>
                        <div>
                          <strong>After</strong>
                          <p>{bullet.after}</p>
                        </div>
                      </div>
                      <p className="helper-text">{bullet.reason}</p>
                      {bullet.evidence_required ? (
                        <p className="error-text">{bullet.evidence_required}</p>
                      ) : null}
                      <span className={severityClass(bullet.risk_level)}>
                        risk: {bullet.risk_level}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="state-callout warning">
              <strong>Forbidden changes</strong>
              <p>这些内容不能新增，只能由用户补充真实 project facts 和 evidence 后再使用。</p>
              <div className="tag-row">
                {rewriteResult.forbidden_changes.map((change) => (
                  <span className="status-pill" key={change}>
                    {change}
                  </span>
                ))}
              </div>
            </section>

            <section>
              <h4>Risk Flags</h4>
              {rewriteResult.risk_flags.length === 0 ? (
                <div className="empty-state compact">
                  <span>No risk flags.</span>
                </div>
              ) : (
                <ul className="result-card-list risk-flag-list">
                  {rewriteResult.risk_flags.map((flag) => (
                    <li key={`${flag.type}-${flag.source_field}-${flag.message}`}>
                      <strong>{flag.type}</strong>
                      <span className={severityClass(flag.severity)}>
                        {flag.severity}
                      </span>
                      <p>{flag.message}</p>
                      <small>{flag.source_field}</small>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        ) : (
          <div className="empty-state compact">
            <strong>No rewrite result</strong>
            <span>Select a project and provide a JD ID to run rewrite.</span>
          </div>
        )}
      </article>
    </section>
  );
}
