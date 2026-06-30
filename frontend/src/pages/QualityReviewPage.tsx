import { useEffect, useState } from "react";

import {
  addBadCaseToEval,
  createBadCase,
  getBadCaseStats,
  getBadCase,
  listBadCases,
  updateBadCase,
} from "../api/evaluations";
import type {
  BadCaseCategory,
  BadCaseCreatePayload,
  BadCaseFilters,
  BadCaseRecord,
  BadCaseSeverity,
  BadCaseSourceType,
  BadCaseStats,
  BadCaseStatus,
  BadCaseUpdatePayload,
} from "../types/api";

const sourceTypes: BadCaseSourceType[] = [
  "match_report",
  "rag_answer",
  "rag_document",
  "agent_run",
  "agent_step",
  "resume_version",
  "job_description",
  "ui_flow",
  "data_persistence",
  "other",
];

const categories: BadCaseCategory[] = [
  "match_score_inaccurate",
  "missing_skill_extraction",
  "irrelevant_rag_source",
  "unsupported_answer",
  "hallucination_risk",
  "agent_step_failed",
  "need_more_info_wrong",
  "privacy_risk",
  "ui_confusing",
  "data_persistence_issue",
  "other",
];

const severities: BadCaseSeverity[] = ["low", "medium", "high", "critical"];
const statuses: BadCaseStatus[] = [
  "open",
  "reviewing",
  "fixed",
  "verified",
  "wont_fix",
];
const summaryPlaceholder = "只填写问题摘要，不要粘贴完整原文。";

type QualityReviewPageProps = {
  badCases: BadCaseRecord[];
  onBadCasesChanged?: (badCases: BadCaseRecord[]) => void;
};

type BadCaseFormState = {
  source_type: BadCaseSourceType;
  source_id: string;
  category: BadCaseCategory;
  severity: BadCaseSeverity;
  title: string;
  description: string;
  expected_behavior: string;
  actual_behavior: string;
  suggested_fix: string;
  root_cause: string;
  fix_strategy: string;
  tags: string;
};

type BadCaseUpdateFormState = {
  status: BadCaseStatus;
  severity: BadCaseSeverity;
  category: BadCaseCategory;
  title: string;
  description: string;
  expected_behavior: string;
  actual_behavior: string;
  suggested_fix: string;
  root_cause: string;
  fix_strategy: string;
  tags: string;
};

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleString() : "None";
}

function statusClass(status: string) {
  return `status-pill status-${status.replace(/_/g, "-")}`;
}

function severityClass(severity: string) {
  return `status-pill severity-${severity}`;
}

function normalizeOptionalText(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function normalizeTags(value: string) {
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function toUpdateForm(badCase: BadCaseRecord): BadCaseUpdateFormState {
  return {
    status: badCase.status,
    severity: badCase.severity,
    category: badCase.category,
    title: badCase.title,
    description: badCase.description,
    expected_behavior: badCase.expected_behavior ?? "",
    actual_behavior: badCase.actual_behavior ?? "",
    suggested_fix: badCase.suggested_fix ?? "",
    root_cause: badCase.root_cause ?? "",
    fix_strategy: badCase.fix_strategy ?? "",
    tags: badCase.tags.join(", "),
  };
}

function BadCaseField({
  label,
  value,
}: {
  label: string;
  value: string | null;
}) {
  return (
    <li>
      <strong>{label}</strong>
      <span>{value || "None"}</span>
    </li>
  );
}

export function QualityReviewPage({
  badCases,
  onBadCasesChanged,
}: QualityReviewPageProps) {
  const [items, setItems] = useState<BadCaseRecord[]>(badCases);
  const [stats, setStats] = useState<BadCaseStats | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(
    badCases[0]?.id ?? null,
  );
  const [selectedBadCase, setSelectedBadCase] =
    useState<BadCaseRecord | null>(null);
  const [formState, setFormState] = useState<BadCaseFormState>({
    source_type: "match_report",
    source_id: "",
    category: "match_score_inaccurate",
    severity: "medium",
    title: "",
    description: "",
    expected_behavior: "",
    actual_behavior: "",
    suggested_fix: "",
    root_cause: "",
    fix_strategy: "",
    tags: "",
  });
  const [filters, setFilters] = useState<BadCaseFilters>({ limit: 50 });
  const [updateForm, setUpdateForm] = useState<BadCaseUpdateFormState | null>(
    null,
  );
  const [lastCreated, setLastCreated] = useState<BadCaseRecord | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isListLoading, setIsListLoading] = useState(false);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [isLinking, setIsLinking] = useState(false);

  const refreshBadCaseStats = async () => {
    const nextStats = await getBadCaseStats();
    setStats(nextStats);
    return nextStats;
  };

  const refreshBadCases = async (nextFilters = filters) => {
    setIsListLoading(true);
    try {
      const [response] = await Promise.all([
        listBadCases(nextFilters),
        refreshBadCaseStats(),
      ]);
      setItems(response.items);
      onBadCasesChanged?.(response.items);
      if (!selectedId && response.items[0]) {
        setSelectedId(response.items[0].id);
      }
      return response.items;
    } finally {
      setIsListLoading(false);
    }
  };

  const loadBadCase = async (badCaseId: string) => {
    setIsDetailLoading(true);
    setErrorMessage(null);
    try {
      const record = await getBadCase(badCaseId);
      setSelectedId(record.id);
      setSelectedBadCase(record);
      setUpdateForm(toUpdateForm(record));
    } catch (error) {
      setSelectedBadCase(null);
      setUpdateForm(null);
      setErrorMessage(
        error instanceof Error ? error.message : "Bad case detail 加载失败。",
      );
    } finally {
      setIsDetailLoading(false);
    }
  };

  useEffect(() => {
    setItems(badCases);
    if (!selectedId && badCases[0]) {
      setSelectedId(badCases[0].id);
    }
  }, [badCases, selectedId]);

  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const loadedItems = await refreshBadCases();
        if (loadedItems[0]) {
          await loadBadCase(loadedItems[0].id);
        }
      } catch (error) {
        setErrorMessage(
          error instanceof Error ? error.message : "Bad cases 加载失败。",
        );
      }
    };
    void loadInitialData();
  }, []);

  const handleCreate = async () => {
    setIsCreating(true);
    setErrorMessage(null);
    setStatusMessage(null);
    setLastCreated(null);
    try {
      const payload: BadCaseCreatePayload = {
        source_type: formState.source_type,
        source_id: formState.source_id.trim(),
        category: formState.category,
        severity: formState.severity,
        title: formState.title.trim(),
        description: formState.description.trim(),
        expected_behavior: normalizeOptionalText(formState.expected_behavior),
        actual_behavior: normalizeOptionalText(formState.actual_behavior),
        suggested_fix: normalizeOptionalText(formState.suggested_fix),
        root_cause: normalizeOptionalText(formState.root_cause),
        fix_strategy: normalizeOptionalText(formState.fix_strategy),
        tags: normalizeTags(formState.tags),
      };
      const created = await createBadCase(payload);
      setLastCreated(created);
      setSelectedBadCase(created);
      setUpdateForm(toUpdateForm(created));
      await refreshBadCases();
      setSelectedId(created.id);
      setStatusMessage("Bad case created.");
      setFormState((current) => ({
        ...current,
        source_id: "",
        title: "",
        description: "",
        expected_behavior: "",
        actual_behavior: "",
        suggested_fix: "",
        root_cause: "",
        fix_strategy: "",
        tags: "",
      }));
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Bad case 创建失败。",
      );
    } finally {
      setIsCreating(false);
    }
  };

  const handleApplyFilters = async () => {
    setErrorMessage(null);
    setStatusMessage(null);
    try {
      const loadedItems = await refreshBadCases(filters);
      if (loadedItems[0]) {
        await loadBadCase(loadedItems[0].id);
      } else {
        setSelectedId(null);
        setSelectedBadCase(null);
        setUpdateForm(null);
      }
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "筛选 bad cases 失败。",
      );
    }
  };

  const handleClearFilters = async () => {
    const nextFilters: BadCaseFilters = { limit: 50 };
    setFilters(nextFilters);
    setErrorMessage(null);
    setStatusMessage(null);
    try {
      const loadedItems = await refreshBadCases(nextFilters);
      if (loadedItems[0]) {
        await loadBadCase(loadedItems[0].id);
      }
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "清空筛选失败。",
      );
    }
  };

  const handleUpdate = async () => {
    if (!selectedBadCase || !updateForm) {
      setErrorMessage("请先选择 bad case。");
      return;
    }
    setIsUpdating(true);
    setErrorMessage(null);
    setStatusMessage(null);
    try {
      const payload: BadCaseUpdatePayload = {
        status: updateForm.status,
        severity: updateForm.severity,
        category: updateForm.category,
        title: updateForm.title.trim(),
        description: updateForm.description.trim(),
        expected_behavior: normalizeOptionalText(updateForm.expected_behavior),
        actual_behavior: normalizeOptionalText(updateForm.actual_behavior),
        suggested_fix: normalizeOptionalText(updateForm.suggested_fix),
        root_cause: normalizeOptionalText(updateForm.root_cause),
        fix_strategy: normalizeOptionalText(updateForm.fix_strategy),
        tags: normalizeTags(updateForm.tags),
      };
      const updated = await updateBadCase(selectedBadCase.id, payload);
      setSelectedBadCase(updated);
      setUpdateForm(toUpdateForm(updated));
      await refreshBadCases();
      setStatusMessage("Bad case updated.");
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Bad case 更新失败。",
      );
    } finally {
      setIsUpdating(false);
    }
  };

  const handleAddToEval = async () => {
    if (!selectedBadCase) {
      setErrorMessage("请先选择 bad case。");
      return;
    }
    setIsLinking(true);
    setErrorMessage(null);
    setStatusMessage(null);
    try {
      const link = await addBadCaseToEval(selectedBadCase.id);
      setSelectedBadCase(link.bad_case);
      setUpdateForm(toUpdateForm(link.bad_case));
      await refreshBadCases();
      setStatusMessage(
        link.created
          ? `Added to regression eval set: ${link.evaluation_case.id}`
          : `Already linked: ${link.evaluation_case.id}`,
      );
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "加入 eval set 失败。",
      );
    } finally {
      setIsLinking(false);
    }
  };

  return (
    <section className="page-stack" aria-labelledby="quality-review-title">
      <div className="page-heading">
        <p className="eyebrow">Quality Review</p>
        <h2 id="quality-review-title">Bad Case Review</h2>
        <p>阶段 5F 已完成：人工记录、筛选、查看和更新 Bad Case，不做自动评估，也不接真实 LLM。</p>
      </div>

      <article className="panel warning-panel">
        <div>
          <h3>安全边界</h3>
          <p>Quality Review 当前是人工 bad case 记录，只保存问题摘要和 source refs。</p>
          <p>不要粘贴完整简历、JD、RAG chunk、投递记录、面试复盘或 API Key；当前不接真实 LLM，不做自动评估，不做自动投递。</p>
        </div>
        <span className="status-pill">Summary only</span>
      </article>

      {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
      {statusMessage ? <p className="hint-text">{statusMessage}</p> : null}

      <div className="metric-grid">
        <article className="metric-card blue">
          <span>Bad Cases</span>
          <strong>{stats?.total ?? items.length}</strong>
          <small>Total tracked</small>
        </article>
        <article className="metric-card amber">
          <span>Open</span>
          <strong>{stats?.open_count ?? 0}</strong>
          <small>open / reviewing</small>
        </article>
        <article className="metric-card green">
          <span>In Eval</span>
          <strong>{stats?.added_to_eval_set_count ?? 0}</strong>
          <small>regression-linked</small>
        </article>
        <article className="metric-card red">
          <span>Verified</span>
          <strong>{stats?.verified_count ?? 0}</strong>
          <small>passed regression</small>
        </article>
      </div>

      <div className="two-column wide-left">
        <article className="panel">
          <div className="panel-header">
            <h3>Create Bad Case</h3>
            <span className="status-pill muted">POST /api/evaluations/bad-cases</span>
          </div>
          <div className="form-stack">
            <div className="filter-grid">
              <label>
                Source type
                <select
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      source_type: event.target.value as BadCaseSourceType,
                    }))
                  }
                  value={formState.source_type}
                >
                  {sourceTypes.map((sourceType) => (
                    <option key={sourceType} value={sourceType}>
                      {sourceType}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Source ID
                <input
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      source_id: event.target.value,
                    }))
                  }
                  placeholder="source object id only"
                  value={formState.source_id}
                />
              </label>
              <label>
                Category
                <select
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      category: event.target.value as BadCaseCategory,
                    }))
                  }
                  value={formState.category}
                >
                  {categories.map((category) => (
                    <option key={category} value={category}>
                      {category}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Severity
                <select
                  onChange={(event) =>
                    setFormState((current) => ({
                      ...current,
                      severity: event.target.value as BadCaseSeverity,
                    }))
                  }
                  value={formState.severity}
                >
                  {severities.map((severity) => (
                    <option key={severity} value={severity}>
                      {severity}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <label>
              Title
              <input
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    title: event.target.value,
                  }))
                }
                placeholder="short issue title"
                value={formState.title}
              />
            </label>
            <label>
              Description
              <textarea
                className="metadata-textarea compact-textarea"
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    description: event.target.value,
                  }))
                }
                placeholder={summaryPlaceholder}
                value={formState.description}
              />
            </label>
            <label>
              Expected behavior
              <textarea
                className="metadata-textarea compact-textarea"
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    expected_behavior: event.target.value,
                  }))
                }
                placeholder={summaryPlaceholder}
                value={formState.expected_behavior}
              />
            </label>
            <label>
              Actual behavior
              <textarea
                className="metadata-textarea compact-textarea"
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    actual_behavior: event.target.value,
                  }))
                }
                placeholder={summaryPlaceholder}
                value={formState.actual_behavior}
              />
            </label>
            <label>
              Suggested fix
              <textarea
                className="metadata-textarea compact-textarea"
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    suggested_fix: event.target.value,
                  }))
                }
                placeholder={summaryPlaceholder}
                value={formState.suggested_fix}
              />
            </label>
            <label>
              Root cause
              <textarea
                className="metadata-textarea compact-textarea"
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    root_cause: event.target.value,
                  }))
                }
                placeholder={summaryPlaceholder}
                value={formState.root_cause}
              />
            </label>
            <label>
              Fix strategy
              <textarea
                className="metadata-textarea compact-textarea"
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    fix_strategy: event.target.value,
                  }))
                }
                placeholder={summaryPlaceholder}
                value={formState.fix_strategy}
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
                placeholder="regression, parser"
                value={formState.tags}
              />
            </label>
            <button
              className="primary-action"
              disabled={isCreating}
              onClick={handleCreate}
              type="button"
            >
              {isCreating ? "Creating..." : "Create bad case"}
            </button>
            {lastCreated ? (
              <p className="hint-text">Created: {lastCreated.id}</p>
            ) : null}
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Filters</h3>
            <span className="status-pill muted">Default limit 50</span>
          </div>
          <div className="form-stack">
            <div className="filter-grid">
              <label>
                Source type
                <select
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      sourceType: event.target.value as BadCaseSourceType | "",
                    }))
                  }
                  value={filters.sourceType ?? ""}
                >
                  <option value="">All</option>
                  {sourceTypes.map((sourceType) => (
                    <option key={sourceType} value={sourceType}>
                      {sourceType}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Source ID
                <input
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      sourceId: event.target.value,
                    }))
                  }
                  value={filters.sourceId ?? ""}
                />
              </label>
              <label>
                Category
                <select
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      category: event.target.value as BadCaseCategory | "",
                    }))
                  }
                  value={filters.category ?? ""}
                >
                  <option value="">All</option>
                  {categories.map((category) => (
                    <option key={category} value={category}>
                      {category}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Severity
                <select
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      severity: event.target.value as BadCaseSeverity | "",
                    }))
                  }
                  value={filters.severity ?? ""}
                >
                  <option value="">All</option>
                  {severities.map((severity) => (
                    <option key={severity} value={severity}>
                      {severity}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Status
                <select
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      status: event.target.value as BadCaseStatus | "",
                    }))
                  }
                  value={filters.status ?? ""}
                >
                  <option value="">All</option>
                  {statuses.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Limit
                <input
                  min={1}
                  max={100}
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      limit: Number(event.target.value) || 50,
                    }))
                  }
                  type="number"
                  value={filters.limit ?? 50}
                />
              </label>
            </div>
            <div className="run-row">
              <button
                className="primary-action"
                disabled={isListLoading}
                onClick={handleApplyFilters}
                type="button"
              >
                {isListLoading ? "Loading..." : "Apply filters"}
              </button>
              <button
                className="ghost-action"
                disabled={isListLoading}
                onClick={handleClearFilters}
                type="button"
              >
                Clear
              </button>
            </div>
          </div>
        </article>
      </div>

      <div className="two-column wide-left">
        <article className="panel">
          <div className="panel-header">
            <h3>Bad Case List</h3>
            <span className="status-pill muted">{items.length} items</span>
          </div>
          {isListLoading ? <p className="hint-text">Loading bad cases...</p> : null}
          {!isListLoading && !items.length ? (
            <div className="empty-state compact">
              <strong>暂无 bad cases</strong>
              <span>创建或调整筛选条件后再查看。</span>
            </div>
          ) : (
            <ul className="activity-list bad-case-list">
              {items.map((badCase) => (
                <li
                  className={badCase.id === selectedId ? "selected-row" : undefined}
                  key={badCase.id}
                >
                  <div>
                    <strong>{badCase.title}</strong>
                    <small>{badCase.id}</small>
                    <small>
                      {badCase.source_type}: {badCase.source_id}
                    </small>
                  </div>
                  <span>{badCase.category}</span>
                  <span className={severityClass(badCase.severity)}>
                    {badCase.severity}
                  </span>
                  <span className={statusClass(badCase.status)}>
                    {badCase.status}
                  </span>
                  <span>{formatDate(badCase.created_at)}</span>
                  <button
                    className="ghost-action"
                    onClick={() => loadBadCase(badCase.id)}
                    type="button"
                  >
                    Detail
                  </button>
                </li>
              ))}
            </ul>
          )}
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Bad Case Detail</h3>
            {selectedBadCase ? (
              <span className={statusClass(selectedBadCase.status)}>
                {selectedBadCase.status}
              </span>
            ) : (
              <span className="status-pill muted">No selection</span>
            )}
          </div>
          {isDetailLoading ? <p className="hint-text">Loading detail...</p> : null}
          {!isDetailLoading && !selectedBadCase ? (
            <div className="empty-state compact">
              <strong>未选择 bad case</strong>
              <span>从列表选择一条记录查看详情。</span>
            </div>
          ) : null}
          {selectedBadCase ? (
            <ul className="activity-list bad-case-detail">
              <BadCaseField label="ID" value={selectedBadCase.id} />
              <BadCaseField label="Source type" value={selectedBadCase.source_type} />
              <BadCaseField label="Source ID" value={selectedBadCase.source_id} />
              <BadCaseField label="Category" value={selectedBadCase.category} />
              <BadCaseField label="Severity" value={selectedBadCase.severity} />
              <BadCaseField label="Title" value={selectedBadCase.title} />
              <BadCaseField label="Description" value={selectedBadCase.description} />
              <BadCaseField
                label="Expected"
                value={selectedBadCase.expected_behavior}
              />
              <BadCaseField label="Actual" value={selectedBadCase.actual_behavior} />
              <BadCaseField
                label="Suggested fix"
                value={selectedBadCase.suggested_fix}
              />
              <BadCaseField label="Root cause" value={selectedBadCase.root_cause} />
              <BadCaseField
                label="Fix strategy"
                value={selectedBadCase.fix_strategy}
              />
              <BadCaseField
                label="Tags"
                value={selectedBadCase.tags.length ? selectedBadCase.tags.join(", ") : null}
              />
              <BadCaseField
                label="Added to eval"
                value={selectedBadCase.added_to_eval_set ? "Yes" : "No"}
              />
              <BadCaseField
                label="Regression case"
                value={selectedBadCase.regression_evaluation_case_id}
              />
              <BadCaseField
                label="Regression run"
                value={selectedBadCase.regression_evaluation_run_id}
              />
              <BadCaseField label="Created" value={formatDate(selectedBadCase.created_at)} />
              <BadCaseField
                label="Resolved"
                value={formatDate(selectedBadCase.resolved_at)}
              />
              <BadCaseField
                label="Verified"
                value={formatDate(selectedBadCase.verified_at)}
              />
            </ul>
          ) : null}
          {selectedBadCase ? (
            <button
              className="primary-action"
              disabled={isLinking}
              onClick={handleAddToEval}
              type="button"
            >
              {isLinking ? "Linking..." : "Add to regression eval"}
            </button>
          ) : null}
        </article>
      </div>

      <article className="panel">
        <div className="panel-header">
          <h3>Update Bad Case</h3>
          <span className="status-pill muted">PATCH selected record</span>
        </div>
        {!selectedBadCase || !updateForm ? (
          <div className="empty-state compact">
            <strong>请选择一条 bad case</strong>
            <span>选择后可以更新状态、严重级别、分类和摘要字段。</span>
          </div>
        ) : (
          <div className="form-stack">
            <div className="filter-grid">
              <label>
                Status
                <select
                  onChange={(event) =>
                    setUpdateForm((current) =>
                      current
                        ? {
                            ...current,
                            status: event.target.value as BadCaseStatus,
                          }
                        : current,
                    )
                  }
                  value={updateForm.status}
                >
                  {statuses.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Severity
                <select
                  onChange={(event) =>
                    setUpdateForm((current) =>
                      current
                        ? {
                            ...current,
                            severity: event.target.value as BadCaseSeverity,
                          }
                        : current,
                    )
                  }
                  value={updateForm.severity}
                >
                  {severities.map((severity) => (
                    <option key={severity} value={severity}>
                      {severity}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Category
                <select
                  onChange={(event) =>
                    setUpdateForm((current) =>
                      current
                        ? {
                            ...current,
                            category: event.target.value as BadCaseCategory,
                          }
                        : current,
                    )
                  }
                  value={updateForm.category}
                >
                  {categories.map((category) => (
                    <option key={category} value={category}>
                      {category}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <label>
              Title
              <input
                onChange={(event) =>
                  setUpdateForm((current) =>
                    current ? { ...current, title: event.target.value } : current,
                  )
                }
                value={updateForm.title}
              />
            </label>
            <label>
              Description
              <textarea
                className="metadata-textarea compact-textarea"
                onChange={(event) =>
                  setUpdateForm((current) =>
                    current
                      ? { ...current, description: event.target.value }
                      : current,
                  )
                }
                placeholder={summaryPlaceholder}
                value={updateForm.description}
              />
            </label>
            <label>
              Expected behavior
              <textarea
                className="metadata-textarea compact-textarea"
                onChange={(event) =>
                  setUpdateForm((current) =>
                    current
                      ? { ...current, expected_behavior: event.target.value }
                      : current,
                  )
                }
                placeholder={summaryPlaceholder}
                value={updateForm.expected_behavior}
              />
            </label>
            <label>
              Actual behavior
              <textarea
                className="metadata-textarea compact-textarea"
                onChange={(event) =>
                  setUpdateForm((current) =>
                    current
                      ? { ...current, actual_behavior: event.target.value }
                      : current,
                  )
                }
                placeholder={summaryPlaceholder}
                value={updateForm.actual_behavior}
              />
            </label>
            <label>
              Suggested fix
              <textarea
                className="metadata-textarea compact-textarea"
                onChange={(event) =>
                  setUpdateForm((current) =>
                    current
                      ? { ...current, suggested_fix: event.target.value }
                      : current,
                  )
                }
                placeholder={summaryPlaceholder}
                value={updateForm.suggested_fix}
              />
            </label>
            <label>
              Root cause
              <textarea
                className="metadata-textarea compact-textarea"
                onChange={(event) =>
                  setUpdateForm((current) =>
                    current
                      ? { ...current, root_cause: event.target.value }
                      : current,
                  )
                }
                placeholder={summaryPlaceholder}
                value={updateForm.root_cause}
              />
            </label>
            <label>
              Fix strategy
              <textarea
                className="metadata-textarea compact-textarea"
                onChange={(event) =>
                  setUpdateForm((current) =>
                    current
                      ? { ...current, fix_strategy: event.target.value }
                      : current,
                  )
                }
                placeholder={summaryPlaceholder}
                value={updateForm.fix_strategy}
              />
            </label>
            <label>
              Tags
              <input
                onChange={(event) =>
                  setUpdateForm((current) =>
                    current ? { ...current, tags: event.target.value } : current,
                  )
                }
                placeholder="regression, parser"
                value={updateForm.tags}
              />
            </label>
            <button
              className="primary-action"
              disabled={isUpdating}
              onClick={handleUpdate}
              type="button"
            >
              {isUpdating ? "Updating..." : "Update bad case"}
            </button>
          </div>
        )}
      </article>
    </section>
  );
}
