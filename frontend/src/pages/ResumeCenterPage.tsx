import { useEffect, useState } from "react";

import {
  archiveResumeVersion,
  cloneResumeVersion,
  getResumeVersion,
  listResumeVersions,
  parseResume,
  riskCheckResume,
  saveResumeVersion,
  uploadResume,
} from "../api/resumes";
import type {
  ResumeParseResponse,
  ResumeRecord,
  ResumeRiskCheckResponse,
  ResumeVersionRecord,
  StructuredResume,
} from "../types/api";

type ResumeCenterPageProps = {
  latestResume: ResumeRecord | null;
  resumes: ResumeRecord[];
  onRefresh: () => Promise<void>;
  onResumeUploaded: (resume: ResumeRecord) => void;
};

const resumeSections = [
  "Basic Info",
  "Education",
  "Projects",
  "Experience",
  "Skills",
  "Risk Flags",
];

export function ResumeCenterPage({
  latestResume,
  resumes,
  onRefresh,
  onResumeUploaded,
}: ResumeCenterPageProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedResumeId, setSelectedResumeId] = useState<string | null>(
    latestResume?.resume_id ?? null,
  );
  const [versions, setVersions] = useState<ResumeVersionRecord[]>([]);
  const [selectedVersion, setSelectedVersion] =
    useState<ResumeVersionRecord | null>(null);
  const [cloneVersionName, setCloneVersionName] = useState("");
  const [cloneTargetRole, setCloneTargetRole] = useState("");
  const [parseResult, setParseResult] = useState<ResumeParseResponse | null>(null);
  const [riskResult, setRiskResult] = useState<ResumeRiskCheckResponse | null>(null);
  const [structuredResumeJson, setStructuredResumeJson] = useState("");
  const [structuredJsonError, setStructuredJsonError] = useState<string | null>(null);
  const [confirmedVersionName, setConfirmedVersionName] = useState("");
  const [confirmedTargetRole, setConfirmedTargetRole] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isVersionBusy, setIsVersionBusy] = useState(false);
  const [parseLoading, setParseLoading] = useState(false);
  const [riskLoading, setRiskLoading] = useState(false);
  const [saveVersionLoading, setSaveVersionLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [versionMessage, setVersionMessage] = useState<string | null>(null);
  const [workflowMessage, setWorkflowMessage] = useState<string | null>(null);
  const [workflowError, setWorkflowError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedResumeId && latestResume) {
      setSelectedResumeId(latestResume.resume_id);
    }
  }, [latestResume, selectedResumeId]);

  useEffect(() => {
    if (!selectedResumeId) {
      setVersions([]);
      setSelectedVersion(null);
      resetWorkflowState();
      return;
    }

    const loadVersions = async () => {
      setVersionMessage(null);
      try {
        const response = await listResumeVersions(selectedResumeId);
        setVersions(response.items);
        setSelectedVersion((current) => {
          if (current && response.items.some((item) => item.resume_version_id === current.resume_version_id)) {
            return current;
          }
          return response.items[response.items.length - 1] ?? null;
        });
        resetWorkflowState();
      } catch (error) {
        setVersions([]);
        setSelectedVersion(null);
        resetWorkflowState();
        setVersionMessage(
          error instanceof Error ? error.message : "加载版本失败。",
        );
      }
    };

    void loadVersions();
  }, [selectedResumeId]);

  const refreshVersions = async (resumeId = selectedResumeId) => {
    if (!resumeId) {
      return;
    }
    const response = await listResumeVersions(resumeId);
    setVersions(response.items);
    setSelectedVersion(response.items[response.items.length - 1] ?? null);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setErrorMessage("请选择 PDF、DOCX、Markdown 或 txt 文件。");
      return;
    }

    setIsUploading(true);
    setErrorMessage(null);
    try {
      const resume = await uploadResume(selectedFile);
      onResumeUploaded(resume);
      setSelectedResumeId(resume.resume_id);
      resetWorkflowState();
      await onRefresh();
      await refreshVersions(resume.resume_id);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "上传失败。");
    } finally {
      setIsUploading(false);
    }
  };

  const handleSelectVersion = async (versionId: string) => {
    setIsVersionBusy(true);
    setVersionMessage(null);
    try {
      const version = await getResumeVersion(versionId);
      setSelectedVersion(version);
      resetWorkflowState();
    } catch (error) {
      setVersionMessage(error instanceof Error ? error.message : "加载版本详情失败。");
    } finally {
      setIsVersionBusy(false);
    }
  };

  const handleCloneVersion = async () => {
    if (!selectedVersion) {
      setVersionMessage("请先选择一个 version。");
      return;
    }
    setIsVersionBusy(true);
    setVersionMessage(null);
    try {
      const cloned = await cloneResumeVersion(selectedVersion.resume_version_id, {
        version_name: cloneVersionName || null,
        target_role: cloneTargetRole || null,
      });
      setCloneVersionName("");
      setCloneTargetRole("");
      await refreshVersions(cloned.resume_id);
      setSelectedVersion(cloned);
      setVersionMessage("Version cloned.");
    } catch (error) {
      setVersionMessage(error instanceof Error ? error.message : "复制版本失败。");
    } finally {
      setIsVersionBusy(false);
    }
  };

  const handleArchiveVersion = async (versionId: string) => {
    setIsVersionBusy(true);
    setVersionMessage(null);
    try {
      const archived = await archiveResumeVersion(versionId);
      await refreshVersions(archived.resume_id);
      setSelectedVersion(archived);
      setVersionMessage("Version archived.");
    } catch (error) {
      setVersionMessage(error instanceof Error ? error.message : "归档版本失败。");
    } finally {
      setIsVersionBusy(false);
    }
  };

  const resetWorkflowState = () => {
    setParseResult(null);
    setRiskResult(null);
    setStructuredResumeJson("");
    setStructuredJsonError(null);
    setConfirmedVersionName("");
    setConfirmedTargetRole("");
    setWorkflowMessage(null);
    setWorkflowError(null);
  };

  const selectedResume = selectedResumeId
    ? resumes.find((resume) => resume.resume_id === selectedResumeId) ??
      (latestResume?.resume_id === selectedResumeId ? latestResume : null)
    : null;
  const sourceVersionId =
    parseResult?.source_version_id ?? selectedVersion?.resume_version_id ?? null;
  const canUseStructuredEditor =
    Boolean(parseResult) && Boolean(structuredResumeJson.trim()) && !structuredJsonError;
  const canSaveConfirmedVersion =
    canUseStructuredEditor && Boolean(confirmedVersionName.trim()) && !saveVersionLoading;

  const handleParseResume = async () => {
    if (!selectedResumeId) {
      setWorkflowError("请先选择一个 Resume。");
      return;
    }
    setParseLoading(true);
    setWorkflowError(null);
    setWorkflowMessage(null);
    try {
      const result = await parseResume(selectedResumeId, {
        resume_version_id: selectedVersion?.resume_version_id ?? null,
        parser_mode: "deterministic",
      });
      setParseResult(result);
      setRiskResult(null);
      setStructuredResumeJson(JSON.stringify(result.structured_resume, null, 2));
      setStructuredJsonError(null);
      setConfirmedVersionName("");
      setConfirmedTargetRole(selectedVersion?.target_role ?? "");
      setWorkflowMessage("Parse completed. Review structured JSON before saving.");
    } catch (error) {
      setWorkflowError(error instanceof Error ? error.message : "解析 Resume 失败。");
    } finally {
      setParseLoading(false);
    }
  };

  const handleStructuredJsonChange = (value: string) => {
    setStructuredResumeJson(value);
    setRiskResult(null);
    setStructuredJsonError(validateStructuredResumeJson(value));
  };

  const handleRiskCheck = async () => {
    if (!selectedResumeId) {
      setWorkflowError("请先选择一个 Resume。");
      return;
    }
    const structuredResume = parseStructuredResumeJson(structuredResumeJson);
    if (!structuredResume) {
      setStructuredJsonError("Structured resume JSON must be a valid object.");
      return;
    }
    setRiskLoading(true);
    setWorkflowError(null);
    setWorkflowMessage(null);
    try {
      const result = await riskCheckResume(selectedResumeId, {
        resume_version_id: sourceVersionId,
        structured_resume: structuredResume,
      });
      setRiskResult(result);
      setWorkflowMessage(
        result.risk_flags.length
          ? "Risk check completed. Review flags before saving."
          : "Risk check completed. No deterministic risks detected.",
      );
    } catch (error) {
      setWorkflowError(error instanceof Error ? error.message : "风险检测失败。");
    } finally {
      setRiskLoading(false);
    }
  };

  const handleSaveConfirmedVersion = async () => {
    if (!selectedResumeId) {
      setWorkflowError("请先选择一个 Resume。");
      return;
    }
    if (!confirmedVersionName.trim()) {
      setWorkflowError("请填写 version_name。");
      return;
    }
    const structuredResume = parseStructuredResumeJson(structuredResumeJson);
    if (!structuredResume) {
      setStructuredJsonError("Structured resume JSON must be a valid object.");
      return;
    }
    setSaveVersionLoading(true);
    setWorkflowError(null);
    setWorkflowMessage(null);
    try {
      const saved = await saveResumeVersion(selectedResumeId, {
        version_name: confirmedVersionName.trim(),
        target_role: confirmedTargetRole.trim() || null,
        structured_resume: structuredResume,
        risk_report: riskResult?.risk_report ?? null,
        source_version_id: sourceVersionId,
      });
      await refreshVersions(saved.resume_id);
      setSelectedVersion(saved);
      setConfirmedVersionName("");
      setConfirmedTargetRole(saved.target_role ?? "");
      setVersionMessage("Confirmed version saved.");
      setWorkflowMessage("Confirmed version saved. Existing versions were not overwritten.");
      await onRefresh();
    } catch (error) {
      setWorkflowError(error instanceof Error ? error.message : "保存确认版本失败。");
    } finally {
      setSaveVersionLoading(false);
    }
  };

  return (
    <section className="page-stack" aria-labelledby="resume-title">
      <div className="page-heading">
        <p className="eyebrow">Resume</p>
        <h2 id="resume-title">Resume Center</h2>
        <p>PDF / DOCX / Markdown / txt 会真实提取文本；deterministic parse、risk-check 和 confirmed version 保存来自 DB-backed API。</p>
      </div>

      <div className="two-column wide-left">
        <article className="panel upload-panel">
          <div className="panel-header">
            <h3>简历入口</h3>
            <span className="status-pill muted">POST /api/resumes/upload</span>
          </div>
          <div className="form-stack">
            <input
              accept=".pdf,.docx,.md,.markdown,.txt"
              onChange={(event) =>
                setSelectedFile(event.target.files?.[0] ?? null)
              }
              type="file"
            />
            <button
              className="primary-action"
              disabled={isUploading}
              onClick={handleUpload}
              type="button"
            >
              {isUploading ? "Uploading..." : "Upload resume"}
            </button>
            {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>最近简历</h3>
            <span className="status-pill">
              {latestResume ? latestResume.resume_id : "None"}
            </span>
          </div>
          {latestResume ? (
            <ul className="activity-list">
              <li>
                <strong>Filename</strong>
                <span>{latestResume.filename}</span>
              </li>
              <li>
                <strong>Type</strong>
                <span>{latestResume.file_type}</span>
              </li>
              <li>
                <strong>Status</strong>
                <span>{latestResume.parse_status}</span>
              </li>
              <li>
                <strong>Extraction</strong>
                <span>{latestResume.extraction_status}</span>
              </li>
              <li>
                <strong>Method</strong>
                <span>{latestResume.extraction_method}</span>
              </li>
            </ul>
          ) : (
            <div className="empty-state">
              <strong>暂无简历</strong>
              <span>上传后会创建 initial version。</span>
            </div>
          )}
        </article>
      </div>

      <article className="panel">
        <div className="panel-header">
          <h3>Resume 列表</h3>
          <span className="status-pill">{resumes.length} items</span>
        </div>
        {resumes.length ? (
          <ul className="activity-list">
            {resumes.map((resume) => (
              <li key={resume.resume_id}>
                <strong>{resume.filename}</strong>
                <span>{resume.resume_id}</span>
                <button
                  className="ghost-action"
                  onClick={() => setSelectedResumeId(resume.resume_id)}
                  type="button"
                >
                  Versions
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <div className="empty-state">
            <strong>暂无 Resume 记录</strong>
            <span>上传 PDF、DOCX、Markdown 或 txt 文件后会出现在这里。</span>
          </div>
        )}
      </article>

      <div className="two-column">
        <article className="panel">
          <div className="panel-header">
            <h3>Resume Versions</h3>
            <span className="status-pill">{versions.length} items</span>
          </div>
          {selectedResumeId ? (
            <p className="hint-text">Selected resume: {selectedResumeId}</p>
          ) : null}
          {versionMessage ? <p className="hint-text">{versionMessage}</p> : null}
          {versions.length ? (
            <ul className="activity-list version-list">
              {versions.map((version) => (
                <li
                  className={
                    selectedVersion?.resume_version_id === version.resume_version_id
                      ? "selected-row"
                      : undefined
                  }
                  key={version.resume_version_id}
                >
                  <div>
                    <strong>{version.version_name}</strong>
                    <small>
                      v{version.version_number} · {version.target_role || "No target role"}
                    </small>
                  </div>
                  <span>{version.status}</span>
                  <span>{new Date(version.created_at).toLocaleString()}</span>
                  <button
                    className="ghost-action"
                    disabled={isVersionBusy}
                    onClick={() => void handleSelectVersion(version.resume_version_id)}
                    type="button"
                  >
                    Detail
                  </button>
                  <button
                    className="ghost-action"
                    disabled={isVersionBusy || version.is_archived}
                    onClick={() => void handleArchiveVersion(version.resume_version_id)}
                    type="button"
                  >
                    Archive
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <div className="empty-state">
              <strong>暂无版本</strong>
              <span>选择或上传 Resume 后查看版本历史。</span>
            </div>
          )}
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Version Detail</h3>
            <span className="status-pill muted">
              {selectedVersion?.resume_version_id ?? "None"}
            </span>
          </div>
          {selectedVersion ? (
            <>
              <ul className="activity-list">
                <li>
                  <strong>Status</strong>
                  <span>
                    {selectedVersion.status}
                    {selectedVersion.is_archived ? " / archived" : ""}
                  </span>
                </li>
                <li>
                  <strong>Extraction</strong>
                  <span>{selectedVersion.extraction_status}</span>
                </li>
                <li>
                  <strong>Method</strong>
                  <span>{selectedVersion.extraction_method}</span>
                </li>
                <li>
                  <strong>Warnings</strong>
                  <span>
                    {selectedVersion.extraction_warnings.length
                      ? selectedVersion.extraction_warnings.join(" | ")
                      : "None"}
                  </span>
                </li>
              </ul>
              <pre className="json-preview text-preview">
                {selectedVersion.raw_text_preview}
              </pre>
            </>
          ) : (
            <div className="empty-state">
              <strong>未选择 version</strong>
              <span>点击 Detail 查看 raw text preview 和 extraction 状态。</span>
            </div>
          )}
        </article>
      </div>

      <article className="panel">
        <div className="panel-header">
          <h3>Clone Version</h3>
          <span className="status-pill muted">POST /api/resume-versions/:id/clone</span>
        </div>
        <div className="inline-form">
          <input
            onChange={(event) => setCloneVersionName(event.target.value)}
            placeholder="Version name"
            value={cloneVersionName}
          />
          <input
            onChange={(event) => setCloneTargetRole(event.target.value)}
            placeholder="Target role"
            value={cloneTargetRole}
          />
          <button
            className="primary-action"
            disabled={!selectedVersion || isVersionBusy}
            onClick={() => void handleCloneVersion()}
            type="button"
          >
            Clone selected version
          </button>
        </div>
        <p className="hint-text">
          Clone 会创建新 version，不覆盖原始版本；diff / compare 留到后续阶段。
        </p>
      </article>

      {latestResume ? (
        <article className="panel">
          <div className="panel-header">
            <h3>文本提取结果</h3>
            <span className="status-pill">{latestResume.extraction_status}</span>
          </div>
          <ul className="activity-list">
            <li>
              <strong>Method</strong>
              <span>{latestResume.extraction_method}</span>
            </li>
            <li>
              <strong>Warnings</strong>
              <span>
                {latestResume.extraction_warnings.length
                  ? latestResume.extraction_warnings.join(" | ")
                  : "None"}
              </span>
            </li>
          </ul>
          {latestResume.extraction_status === "parser_placeholder" ? (
            <p className="hint-text">
              该记录来自早期 parser placeholder 数据；重新上传后会使用真实 PDF / DOCX 文本提取。
            </p>
          ) : null}
          <pre className="json-preview text-preview">
            {latestResume.raw_text_preview || "No preview available."}
          </pre>
        </article>
      ) : null}

      <article className="panel">
        <div className="panel-header">
          <h3>Parse / Risk Check / Save</h3>
          <span className="status-pill muted">Resume parser workflow</span>
        </div>
        <ul className="activity-list">
          <li>
            <strong>Selected resume</strong>
            <span>{selectedResume?.resume_id ?? "None"}</span>
          </li>
          <li>
            <strong>Source version</strong>
            <span>{sourceVersionId ?? "Latest active version"}</span>
          </li>
          <li>
            <strong>Parser</strong>
            <span>{parseResult?.extraction_method ?? "Not parsed"}</span>
          </li>
        </ul>
        <div className="inline-form">
          <button
            className="primary-action"
            disabled={!selectedResumeId || parseLoading}
            onClick={() => void handleParseResume()}
            type="button"
          >
            {parseLoading ? "Parsing..." : "Parse selected resume"}
          </button>
          <button
            className="ghost-action"
            disabled={!canUseStructuredEditor || riskLoading}
            onClick={() => void handleRiskCheck()}
            type="button"
          >
            {riskLoading ? "Checking..." : "Run risk check"}
          </button>
        </div>
        {workflowError ? <p className="error-text">{workflowError}</p> : null}
        {workflowMessage ? <p className="hint-text">{workflowMessage}</p> : null}
        {parseResult ? (
          <>
            <div className="two-column">
              <article className="mini-panel">
                <h3>Parse Result</h3>
                <p>Parsed at: {new Date(parseResult.parsed_at).toLocaleString()}</p>
                <p>
                  Warnings:{" "}
                  {parseResult.extraction_warnings.length
                    ? parseResult.extraction_warnings.join(" | ")
                    : "None"}
                </p>
              </article>
              <article className="mini-panel">
                <h3>Raw Text Preview</h3>
                <p>{parseResult.raw_text_preview || "No preview available."}</p>
              </article>
            </div>
            <label className="json-editor-label">
              Structured resume JSON
              <textarea
                className="metadata-textarea resume-json-editor"
                onChange={(event) => handleStructuredJsonChange(event.target.value)}
                value={structuredResumeJson}
              />
            </label>
            {structuredJsonError ? (
              <p className="error-text">{structuredJsonError}</p>
            ) : (
              <p className="hint-text">
                JSON valid. Risk check and save will use the edited structured resume.
              </p>
            )}
          </>
        ) : (
          <div className="empty-state compact">
            <strong>暂无 parse result</strong>
            <span>点击 Parse 后会生成可编辑 structured_resume JSON。</span>
          </div>
        )}
      </article>

      <div className="two-column">
        <article className="panel">
          <div className="panel-header">
            <h3>Risk Check Result</h3>
            <span className="status-pill">
              {riskResult ? `${riskResult.risk_flags.length} flags` : "None"}
            </span>
          </div>
          {riskResult ? (
            <>
              <p className="hint-text">
                Checked at: {new Date(riskResult.checked_at).toLocaleString()}
              </p>
              {riskResult.risk_flags.length ? (
                <ul className="activity-list">
                  {riskResult.risk_flags.map((flag, index) => (
                    <li key={`${flag.type}-${index}`}>
                      <div>
                        <strong>{flag.type}</strong>
                        <small>{flag.message}</small>
                      </div>
                      <span>{flag.severity}</span>
                      <span>{flag.location ?? "No location"}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="empty-state compact">
                  <strong>无确定性风险</strong>
                  <span>当前规则没有发现 unsupported metric、overclaim 或 timeline conflict。</span>
                </div>
              )}
              <pre className="json-preview compact">
                {JSON.stringify(riskResult.risk_report, null, 2)}
              </pre>
            </>
          ) : (
            <div className="empty-state compact">
              <strong>暂无风险检测结果</strong>
              <span>Parse 并确认 JSON 有效后可以运行 risk-check。</span>
            </div>
          )}
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Save Confirmed Version</h3>
            <span className="status-pill muted">POST /api/resumes/:id/versions</span>
          </div>
          <div className="form-stack">
            <label>
              Version name
              <input
                onChange={(event) => setConfirmedVersionName(event.target.value)}
                placeholder="Backend target confirmed"
                value={confirmedVersionName}
              />
            </label>
            <label>
              Target role
              <input
                onChange={(event) => setConfirmedTargetRole(event.target.value)}
                placeholder="Backend Engineer"
                value={confirmedTargetRole}
              />
            </label>
            <button
              className="primary-action"
              disabled={!canSaveConfirmedVersion}
              onClick={() => void handleSaveConfirmedVersion()}
              type="button"
            >
              {saveVersionLoading ? "Saving..." : "Save confirmed version"}
            </button>
            <p className="hint-text">
              保存会创建新的 confirmed version，不覆盖 initial / cloned version。
            </p>
          </div>
        </article>
      </div>

      <article className="panel">
        <div className="panel-header">
          <h3>结构化结果</h3>
          <span className="status-pill muted">Structured preview</span>
        </div>
        <div className="section-grid">
          {resumeSections.map((section) => (
            <div className="schema-tile" key={section}>
              <span>{section}</span>
              <small>{latestResume ? "Ready" : "Not parsed"}</small>
            </div>
          ))}
        </div>
        {latestResume ? (
          <pre className="json-preview">
            {JSON.stringify(latestResume.structured_resume, null, 2)}
          </pre>
        ) : null}
      </article>
    </section>
  );
}

function validateStructuredResumeJson(value: string): string | null {
  if (!value.trim()) {
    return "Structured resume JSON is required.";
  }
  try {
    const parsed = JSON.parse(value) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return "Structured resume JSON must be an object.";
    }
    return null;
  } catch {
    return "Structured resume JSON is invalid.";
  }
}

function parseStructuredResumeJson(value: string): StructuredResume | null {
  if (validateStructuredResumeJson(value)) {
    return null;
  }
  return JSON.parse(value) as StructuredResume;
}
