import { useState } from "react";

import { runMatch } from "../api/matches";
import type { JobRecord, MatchReport, ResumeRecord } from "../types/api";

type MatchReportPageProps = {
  jobs: JobRecord[];
  latestResume: ResumeRecord | null;
  latestJob: JobRecord | null;
  latestMatch: MatchReport | null;
  matches: MatchReport[];
  onRefresh: () => Promise<void>;
  onMatchRun: (report: MatchReport) => void;
  resumes: ResumeRecord[];
};

const dimensionLabels: Record<string, string> = {
  skill_match: "Skill Match",
  project_relevance: "Project Relevance",
  business_understanding: "Business Understanding",
  expression_quality: "Expression Quality",
  education_fit: "Education Fit",
  risk_control: "Risk Control",
};

export function MatchReportPage({
  jobs,
  latestResume,
  latestJob,
  latestMatch,
  matches,
  onRefresh,
  onMatchRun,
  resumes,
}: MatchReportPageProps) {
  const [isRunning, setIsRunning] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const canRun = Boolean(latestResume && latestJob);

  const handleRun = async () => {
    if (!latestResume || !latestJob) {
      setErrorMessage("请先上传 Resume 并创建 JD。");
      return;
    }
    setIsRunning(true);
    setErrorMessage(null);
    try {
      const report = await runMatch(latestResume.resume_id, latestJob.jd_id);
      onMatchRun(report);
      await onRefresh();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "匹配失败。");
    } finally {
      setIsRunning(false);
    }
  };

  const scoreRows = latestMatch
    ? Object.entries(latestMatch.dimension_scores)
    : [];

  return (
    <section className="page-stack" aria-labelledby="match-title">
      <div className="page-heading">
        <p className="eyebrow">Report</p>
        <h2 id="match-title">Match Report</h2>
        <p>使用最近的 resume_id 和 jd_id 生成 deterministic Mock match report。</p>
      </div>

      <article className="panel">
        <div className="panel-header">
          <h3>运行匹配</h3>
          <span className="status-pill muted">POST /api/matches/run</span>
        </div>
        <div className="run-row">
          <span>Resume: {latestResume?.resume_id ?? "未上传"} ({resumes.length})</span>
          <span>JD: {latestJob?.jd_id ?? "未创建"} ({jobs.length})</span>
          <button
            className="primary-action"
            disabled={!canRun || isRunning}
            onClick={handleRun}
            type="button"
          >
            {isRunning ? "Running..." : "Run mock match"}
          </button>
        </div>
        {!canRun ? (
          <p className="hint-text">需要至少一个 Resume 和一个 JD 才能运行 Match。</p>
        ) : null}
        {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
      </article>

      <div className="two-column">
        <article className="panel score-panel">
          <div className="panel-header">
            <h3>总分</h3>
            <span className="status-pill">
              {latestMatch ? latestMatch.match_report_id : "No run"}
            </span>
          </div>
          <div className="score-dial">
            <strong>{latestMatch ? latestMatch.total_score : "--"}</strong>
            <span>{latestMatch ? "Mock score" : "等待匹配评分"}</span>
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>维度评分</h3>
            <span className="status-pill">{scoreRows.length} dimensions</span>
          </div>
          <div className="score-list">
            {(scoreRows.length ? scoreRows : [["skill_match", 0]]).map(
              ([key, value]) => (
                <div className="score-row" key={key}>
                  <span>{dimensionLabels[key] ?? key}</span>
                  <div className="score-track" aria-label={`${key} score ${value}`}>
                    <span style={{ width: `${value}%` }} />
                  </div>
                  <strong>{value}</strong>
                </div>
              ),
            )}
          </div>
        </article>
      </div>

      <div className="three-column">
        <article className="panel mini-panel">
          <h3>Evidence</h3>
          <ul className="compact-list">
            {latestMatch?.evidence.map((item) => (
              <li key={`${item.dimension}-${item.jd_requirement}`}>
                {item.dimension}: {item.jd_requirement}
              </li>
            )) ?? <li>暂无证据</li>}
          </ul>
        </article>
        <article className="panel mini-panel">
          <h3>Gaps</h3>
          <ul className="compact-list">
            {latestMatch?.gaps.map((gap) => <li key={gap}>{gap}</li>) ?? (
              <li>暂无差距</li>
            )}
          </ul>
        </article>
        <article className="panel mini-panel">
          <h3>Rewrite Priorities</h3>
          <ul className="compact-list">
            {latestMatch?.rewrite_priorities.map((priority) => (
              <li key={priority}>{priority}</li>
            )) ?? <li>暂无建议</li>}
          </ul>
        </article>
      </div>

      <article className="panel">
        <div className="panel-header">
          <h3>Match 列表</h3>
          <span className="status-pill">{matches.length} items</span>
        </div>
        {matches.length ? (
          <ul className="activity-list">
            {matches.map((match) => (
              <li key={match.match_report_id}>
                <strong>{match.match_report_id}</strong>
                <span>score {match.total_score}</span>
              </li>
            ))}
          </ul>
        ) : (
          <div className="empty-state">
            <strong>暂无 Match Report</strong>
            <span>运行 Mock Match 后会出现在这里。</span>
          </div>
        )}
      </article>
    </section>
  );
}
