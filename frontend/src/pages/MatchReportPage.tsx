import { useEffect, useState } from "react";

import { MarkBadCasePanel } from "../components/MarkBadCasePanel";
import { getMatch, runMatch } from "../api/matches";
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
  const [selectedReport, setSelectedReport] = useState<MatchReport | null>(
    latestMatch,
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const canRun = Boolean(latestResume && latestJob);

  useEffect(() => {
    if (latestMatch) {
      setSelectedReport(latestMatch);
    }
  }, [latestMatch]);

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
      setSelectedReport(report);
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
  const detailReport = selectedReport ?? latestMatch;
  const detailScoreRows = detailReport
    ? Object.entries(detailReport.dimension_scores)
    : [];

  const handleSelectReport = async (matchReportId: string) => {
    setErrorMessage(null);
    try {
      const report = await getMatch(matchReportId);
      setSelectedReport(report);
      onMatchRun(report);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "加载报告失败。");
    }
  };

  return (
    <section className="page-stack" aria-labelledby="match-title">
      <div className="page-heading">
        <p className="eyebrow">Report</p>
        <h2 id="match-title">Match Report</h2>
        <p>使用最近的 resume_id 和 jd_id 生成 deterministic match report，并从 DB-backed API 展示历史报告。</p>
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
            {isRunning ? "Running..." : "Run match"}
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
            <span>{latestMatch ? "Deterministic score" : "等待匹配评分"}</span>
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
          <h3>Match History</h3>
          <span className="status-pill">{matches.length} items</span>
        </div>
        {matches.length ? (
          <ul className="activity-list report-list">
            {matches.map((match) => (
              <li
                className={
                  detailReport?.match_report_id === match.match_report_id
                    ? "selected-row"
                    : undefined
                }
                key={match.match_report_id}
              >
                <div>
                  <strong>{match.match_report_id}</strong>
                  <small>
                    Resume Version: {match.resume_version_id ?? "unknown"}
                  </small>
                </div>
                <span>JD: {match.jd_id}</span>
                <span>score {match.total_score}</span>
                <span>
                  {match.created_at
                    ? new Date(match.created_at).toLocaleString()
                    : "No date"}
                </span>
                <button
                  className="ghost-action"
                  onClick={() => void handleSelectReport(match.match_report_id)}
                  type="button"
                >
                  Detail
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <div className="empty-state">
            <strong>暂无 Match Report</strong>
            <span>运行 Match 后会保存到 DB 并出现在这里。</span>
          </div>
        )}
      </article>

      <article className="panel">
        <div className="panel-header">
          <h3>Report Detail</h3>
          <span className="status-pill muted">
            {detailReport?.match_report_id ?? "None"}
          </span>
        </div>
        {detailReport ? (
          <>
            <ul className="activity-list">
              <li>
                <strong>Resume Version</strong>
                <span>{detailReport.resume_version_id ?? "unknown"}</span>
              </li>
              <li>
                <strong>JD</strong>
                <span>{detailReport.jd_id}</span>
              </li>
              <li>
                <strong>Created</strong>
                <span>
                  {detailReport.created_at
                    ? new Date(detailReport.created_at).toLocaleString()
                    : "No date"}
                </span>
              </li>
            </ul>
            <MarkBadCasePanel
              defaultCategory="match_score_inaccurate"
              defaultTitle="Match report review"
              key={detailReport.match_report_id}
              sourceId={detailReport.match_report_id}
              sourceType="match_report"
            />
            <div className="score-list">
              {detailScoreRows.map(([key, value]) => (
                <div className="score-row" key={`detail-${key}`}>
                  <span>{dimensionLabels[key] ?? key}</span>
                  <div className="score-track" aria-label={`${key} score ${value}`}>
                    <span style={{ width: `${value}%` }} />
                  </div>
                  <strong>{value}</strong>
                </div>
              ))}
            </div>
            <div className="three-column">
              <div>
                <h3>Strengths</h3>
                <ul className="compact-list">
                  {detailReport.strengths.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h3>Gaps</h3>
                <ul className="compact-list">
                  {detailReport.gaps.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h3>Priorities</h3>
                <ul className="compact-list">
                  {detailReport.rewrite_priorities.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            </div>
            <ul className="compact-list">
              {detailReport.evidence.map((item) => (
                <li key={`${item.dimension}-${item.jd_requirement}`}>
                  {item.dimension}: {item.jd_requirement} /{" "}
                  {item.resume_signal ?? "no resume signal"}
                </li>
              ))}
            </ul>
          </>
        ) : (
          <div className="empty-state">
            <strong>未选择报告</strong>
            <span>运行或选择一条历史报告查看详情。</span>
          </div>
        )}
        <p className="hint-text">
          Resume version selector 和多版本对比页面留到后续阶段。
        </p>
      </article>
    </section>
  );
}
