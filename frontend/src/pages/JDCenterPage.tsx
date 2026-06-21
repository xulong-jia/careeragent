import { useState } from "react";

import { createJob } from "../api/jobs";
import type { JobRecord } from "../types/api";

type JDCenterPageProps = {
  jobs: JobRecord[];
  latestJob: JobRecord | null;
  onRefresh: () => Promise<void>;
  onJobCreated: (job: JobRecord) => void;
};

export function JDCenterPage({
  jobs,
  latestJob,
  onRefresh,
  onJobCreated,
}: JDCenterPageProps) {
  const [company, setCompany] = useState("Mock Company");
  const [jobTitle, setJobTitle] = useState("AI Application Engineer");
  const [location, setLocation] = useState("Shanghai");
  const [sourceUrl, setSourceUrl] = useState("");
  const [rawText, setRawText] = useState(
    "We need Python, FastAPI and RAG experience. React is a plus.",
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleCreate = async () => {
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      const job = await createJob({
        company,
        job_title: jobTitle,
        location: location || null,
        raw_text: rawText,
        source_url: sourceUrl || null,
      });
      onJobCreated(job);
      await onRefresh();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "创建 JD 失败。");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="page-stack" aria-labelledby="jd-title">
      <div className="page-heading">
        <p className="eyebrow">Job Description</p>
        <h2 id="jd-title">JD Center</h2>
        <p>提交 JD 后生成 deterministic job profile，并通过 DB-backed API 保留历史记录。不调用真实 LLM。</p>
      </div>

      <div className="two-column wide-left">
        <article className="panel">
          <div className="panel-header">
            <h3>JD 表单</h3>
            <span className="status-pill muted">POST /api/jobs</span>
          </div>
          <div className="form-stack">
            <label>
              Company
              <input
                onChange={(event) => setCompany(event.target.value)}
                value={company}
              />
            </label>
            <label>
              Job title
              <input
                onChange={(event) => setJobTitle(event.target.value)}
                value={jobTitle}
              />
            </label>
            <label>
              Location
              <input
                onChange={(event) => setLocation(event.target.value)}
                value={location}
              />
            </label>
            <label>
              Source URL
              <input
                onChange={(event) => setSourceUrl(event.target.value)}
                placeholder="https://example.com/job"
                value={sourceUrl}
              />
            </label>
            <label>
              Raw JD text
              <textarea
                className="jd-textarea"
                onChange={(event) => setRawText(event.target.value)}
                value={rawText}
              />
            </label>
            <button
              className="primary-action"
              disabled={isSubmitting}
              onClick={handleCreate}
              type="button"
            >
              {isSubmitting ? "Creating..." : "Create JD"}
            </button>
            {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>岗位画像</h3>
            <span className="status-pill">
              {latestJob ? latestJob.jd_id : "Not created"}
            </span>
          </div>
          {latestJob ? (
            <div className="profile-field-list">
              <div className="profile-field">
                <span>Role Category</span>
                <small>{latestJob.job_profile.role_category}</small>
              </div>
              <div className="profile-field">
                <span>Required Skills</span>
                <small>{latestJob.job_profile.required_skills.join(", ") || "[]"}</small>
              </div>
              <div className="profile-field">
                <span>Preferred Skills</span>
                <small>{latestJob.job_profile.preferred_skills.join(", ") || "[]"}</small>
              </div>
              <div className="profile-field">
                <span>Responsibilities</span>
                <small>{latestJob.job_profile.responsibilities.length}</small>
              </div>
              <div className="profile-field">
                <span>Interview Focus</span>
                <small>{latestJob.job_profile.interview_focus.length}</small>
              </div>
              <div className="profile-field">
                <span>Risk Level</span>
                <small>{latestJob.job_profile.risk_level}</small>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <strong>暂无 JD</strong>
              <span>创建后会显示 job profile 摘要。</span>
            </div>
          )}
        </article>
      </div>

      <article className="panel">
        <div className="panel-header">
          <h3>JD 列表</h3>
          <span className="status-pill">{jobs.length} items</span>
        </div>
        {jobs.length ? (
          <ul className="activity-list">
            {jobs.map((job) => (
              <li key={job.jd_id}>
                <div>
                  <strong>{job.job_title}</strong>
                  <small>{job.company}</small>
                </div>
                <span>{job.jd_id}</span>
                <span>{job.job_profile.role_category}</span>
                <small>
                  Required: {job.job_profile.required_skills.join(", ") || "[]"}
                </small>
              </li>
            ))}
          </ul>
        ) : (
          <div className="empty-state">
            <strong>暂无 JD 记录</strong>
            <span>创建 JD 后会出现在这里。</span>
          </div>
        )}
      </article>

      <article className="panel">
        <div className="panel-header">
          <h3>JD Profile Summary</h3>
          <span className="status-pill muted">DB-backed</span>
        </div>
        {jobs.length ? (
          <div className="profile-grid">
            {jobs.map((job) => (
              <div className="profile-card" key={`${job.jd_id}-profile`}>
                <strong>{job.job_title}</strong>
                <span>{job.job_profile.role_category}</span>
                <small>
                  Required: {job.job_profile.required_skills.join(", ") || "[]"}
                </small>
                <small>
                  Preferred: {job.job_profile.preferred_skills.join(", ") || "[]"}
                </small>
                <small>
                  Responsibilities: {job.job_profile.responsibilities.length}
                </small>
                <small>
                  Interview Focus: {job.job_profile.interview_focus.join(", ") || "[]"}
                </small>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <strong>暂无岗位画像</strong>
            <span>创建 JD 后会展示 role category 和技能摘要。</span>
          </div>
        )}
      </article>
    </section>
  );
}
