import { useState } from "react";

import { createBadCase } from "../api/evaluations";
import type {
  BadCaseCategory,
  BadCaseRecord,
  BadCaseSeverity,
  BadCaseSourceType,
} from "../types/api";

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
const summaryPlaceholder = "只填写问题摘要，不要粘贴完整原文。";

type MarkBadCasePanelProps = {
  sourceType: BadCaseSourceType;
  sourceId: string | null | undefined;
  defaultCategory: BadCaseCategory;
  defaultTitle: string;
};

function optionalSummary(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

export function MarkBadCasePanel({
  sourceType,
  sourceId,
  defaultCategory,
  defaultTitle,
}: MarkBadCasePanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [category, setCategory] = useState<BadCaseCategory>(defaultCategory);
  const [severity, setSeverity] = useState<BadCaseSeverity>("medium");
  const [title, setTitle] = useState(defaultTitle);
  const [description, setDescription] = useState("");
  const [expectedBehavior, setExpectedBehavior] = useState("");
  const [actualBehavior, setActualBehavior] = useState("");
  const [suggestedFix, setSuggestedFix] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [createdCase, setCreatedCase] = useState<BadCaseRecord | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const resolvedSourceId = sourceId?.trim() ?? "";

  const handleCreate = async () => {
    if (!resolvedSourceId) {
      setErrorMessage("缺少 source_id，无法创建 bad case。");
      return;
    }
    setIsCreating(true);
    setCreatedCase(null);
    setErrorMessage(null);
    try {
      const badCase = await createBadCase({
        source_type: sourceType,
        source_id: resolvedSourceId,
        category,
        severity,
        title: title.trim(),
        description: description.trim(),
        expected_behavior: optionalSummary(expectedBehavior),
        actual_behavior: optionalSummary(actualBehavior),
        suggested_fix: optionalSummary(suggestedFix),
      });
      setCreatedCase(badCase);
      setDescription("");
      setExpectedBehavior("");
      setActualBehavior("");
      setSuggestedFix("");
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Bad case 创建失败。",
      );
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="mark-bad-case-panel">
      <button
        className="ghost-action"
        disabled={!resolvedSourceId}
        onClick={() => setIsExpanded((current) => !current)}
        type="button"
      >
        {isExpanded ? "Close bad case form" : "Mark as bad case"}
      </button>
      {!resolvedSourceId ? (
        <p className="helper-text">缺少 source_id，当前对象无法标记。</p>
      ) : null}

      {isExpanded ? (
        <div className="mark-bad-case-form">
          <p className="helper-text">
            只写问题摘要，不要粘贴完整简历、JD、RAG chunk、投递记录、面试复盘或 API Key。
          </p>
          <div className="readonly-grid">
            <span>source_type: {sourceType}</span>
            <span>source_id: {resolvedSourceId}</span>
          </div>
          <div className="form-stack">
            <div className="filter-grid">
              <label>
                Category
                <select
                  onChange={(event) =>
                    setCategory(event.target.value as BadCaseCategory)
                  }
                  value={category}
                >
                  {categories.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Severity
                <select
                  onChange={(event) =>
                    setSeverity(event.target.value as BadCaseSeverity)
                  }
                  value={severity}
                >
                  {severities.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <label>
              Title
              <input
                onChange={(event) => setTitle(event.target.value)}
                value={title}
              />
            </label>
            <label>
              Description
              <textarea
                className="metadata-textarea compact-textarea"
                onChange={(event) => setDescription(event.target.value)}
                placeholder={summaryPlaceholder}
                value={description}
              />
            </label>
            <label>
              Expected behavior
              <textarea
                className="metadata-textarea compact-textarea"
                onChange={(event) => setExpectedBehavior(event.target.value)}
                placeholder={summaryPlaceholder}
                value={expectedBehavior}
              />
            </label>
            <label>
              Actual behavior
              <textarea
                className="metadata-textarea compact-textarea"
                onChange={(event) => setActualBehavior(event.target.value)}
                placeholder={summaryPlaceholder}
                value={actualBehavior}
              />
            </label>
            <label>
              Suggested fix
              <textarea
                className="metadata-textarea compact-textarea"
                onChange={(event) => setSuggestedFix(event.target.value)}
                placeholder={summaryPlaceholder}
                value={suggestedFix}
              />
            </label>
            <button
              className="primary-action"
              disabled={isCreating || !resolvedSourceId}
              onClick={handleCreate}
              type="button"
            >
              {isCreating ? "Creating..." : "Create bad case"}
            </button>
          </div>
          {createdCase ? (
            <div className="state-callout success">
              <strong>Bad case created</strong>
              <span>{createdCase.id}</span>
              <p>可在 Quality Review 页面查看。</p>
            </div>
          ) : null}
          {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
