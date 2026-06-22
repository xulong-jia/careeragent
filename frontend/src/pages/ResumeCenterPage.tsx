import { useEffect, useState } from "react";

import {
  archiveResumeVersion,
  cloneResumeVersion,
  getResumeVersion,
  listResumeVersions,
  uploadResume,
} from "../api/resumes";
import type { ResumeRecord, ResumeVersionRecord } from "../types/api";

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
  const [isUploading, setIsUploading] = useState(false);
  const [isVersionBusy, setIsVersionBusy] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [versionMessage, setVersionMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedResumeId && latestResume) {
      setSelectedResumeId(latestResume.resume_id);
    }
  }, [latestResume, selectedResumeId]);

  useEffect(() => {
    if (!selectedResumeId) {
      setVersions([]);
      setSelectedVersion(null);
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
      } catch (error) {
        setVersions([]);
        setSelectedVersion(null);
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

  return (
    <section className="page-stack" aria-labelledby="resume-title">
      <div className="page-heading">
        <p className="eyebrow">Resume</p>
        <h2 id="resume-title">Resume Center</h2>
        <p>Markdown / txt 会真实读取 UTF-8 文本；PDF / DOCX 当前返回 parser placeholder。Resume 和版本历史来自 DB-backed API。</p>
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
              当前阶段未接入 PDF / DOCX parser，raw text 为明确占位文本，不代表真实解析结果。
            </p>
          ) : null}
          <pre className="json-preview text-preview">
            {latestResume.raw_text_preview || "No preview available."}
          </pre>
        </article>
      ) : null}

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
