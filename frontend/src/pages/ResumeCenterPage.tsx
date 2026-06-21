import { useState } from "react";

import { uploadResume } from "../api/resumes";
import type { ResumeRecord } from "../types/api";

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
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

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
      await onRefresh();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "上传失败。");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <section className="page-stack" aria-labelledby="resume-title">
      <div className="page-heading">
        <p className="eyebrow">Resume</p>
        <h2 id="resume-title">Resume Center</h2>
        <p>Markdown / txt 会真实读取 UTF-8 文本；PDF / DOCX 当前返回 parser placeholder。数据仅保存在内存中，刷新页面或重启服务会丢失。</p>
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
              {isUploading ? "Uploading..." : "Upload mock resume"}
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
              <span>上传后会显示 mock result。</span>
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
            {latestResume.raw_text_preview || latestResume.raw_text}
          </pre>
        </article>
      ) : null}

      <article className="panel">
        <div className="panel-header">
          <h3>结构化结果</h3>
          <span className="status-pill muted">Mock schema</span>
        </div>
        <div className="section-grid">
          {resumeSections.map((section) => (
            <div className="schema-tile" key={section}>
              <span>{section}</span>
              <small>{latestResume ? "Mock ready" : "Not parsed"}</small>
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
