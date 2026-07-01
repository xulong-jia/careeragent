import { useEffect, useState } from "react";

import { MarkBadCasePanel } from "../components/MarkBadCasePanel";
import {
  JDSelector,
  ResumeSelector,
  ResumeVersionSelector,
} from "../components/EntitySelectors";
import { compareMatches, getMatch, runMatch } from "../api/matches";
import type {
  JobRecord,
  MatchCompareResponse,
  MatchReport,
  ResumeRecord,
} from "../types/api";

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
  const [selectedResumeId, setSelectedResumeId] = useState(
    latestResume?.resume_id ?? "",
  );
  const [selectedResumeVersionId, setSelectedResumeVersionId] = useState(
    latestMatch?.resume_version_id ?? "",
  );
  const [selectedJdId, setSelectedJdId] = useState(latestJob?.jd_id ?? "");
  const [compareResumeId, setCompareResumeId] = useState(
    latestResume?.resume_id ?? "",
  );
  const [compareVersionA, setCompareVersionA] = useState(
    latestMatch?.resume_version_id ?? "",
  );
  const [compareVersionB, setCompareVersionB] = useState("");
  const [compareJdId, setCompareJdId] = useState(latestJob?.jd_id ?? "");
  const [compareResult, setCompareResult] =
    useState<MatchCompareResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [compareError, setCompareError] = useState<string | null>(null);
  const [isComparing, setIsComparing] = useState(false);

  const canRun = Boolean(selectedJdId && (selectedResumeVersionId || selectedResumeId));
  const canCompare =
    Boolean(compareJdId && compareVersionA && compareVersionB) &&
    compareVersionA !== compareVersionB;

  useEffect(() => {
    if (latestMatch) {
      setSelectedReport(latestMatch);
      setSelectedResumeVersionId(latestMatch.resume_version_id ?? "");
      setCompareVersionA(latestMatch.resume_version_id ?? "");
    }
  }, [latestMatch]);

  useEffect(() => {
    if (!selectedResumeId && latestResume) {
      setSelectedResumeId(latestResume.resume_id);
      setCompareResumeId(latestResume.resume_id);
    }
  }, [latestResume, selectedResumeId]);

  useEffect(() => {
    if (!selectedJdId && latestJob) {
      setSelectedJdId(latestJob.jd_id);
      setCompareJdId(latestJob.jd_id);
    }
  }, [latestJob, selectedJdId]);

  const handleRun = async () => {
    if (!canRun) {
      setErrorMessage("请先选择 Resume Version 和 JD。");
      return;
    }
    setIsRunning(true);
    setErrorMessage(null);
    try {
      const report = await runMatch({
        jdId: selectedJdId,
        resumeId: selectedResumeVersionId ? null : selectedResumeId,
        resumeVersionId: selectedResumeVersionId || null,
      });
      onMatchRun(report);
      setSelectedReport(report);
      setCompareJdId(report.jd_id);
      setCompareVersionA(report.resume_version_id ?? "");
      await onRefresh();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "匹配失败。");
    } finally {
      setIsRunning(false);
    }
  };

  const handleCompare = async () => {
    if (!canCompare) {
      setCompareError("请选择同一 JD 下的两个不同 Resume Version。");
      return;
    }
    setIsComparing(true);
    setCompareError(null);
    try {
      const result = await compareMatches({
        jd_id: compareJdId,
        resume_version_ids: [compareVersionA, compareVersionB],
      });
      setCompareResult(result);
      await onRefresh();
    } catch (error) {
      setCompareError(error instanceof Error ? error.message : "对比失败。");
    } finally {
      setIsComparing(false);
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
        <p>选择 Resume Version 与 JD 运行 deterministic match report，并从 DB-backed API 展示历史和对比结果。</p>
      </div>

      <article className="panel">
        <div className="panel-header">
          <h3>运行匹配</h3>
          <span className="status-pill muted">POST /api/matches/run</span>
        </div>
        <div className="selector-grid">
          <ResumeSelector
            label={`Resume (${resumes.length})`}
            onChange={(value) => {
              setSelectedResumeId(value);
              setSelectedResumeVersionId("");
            }}
            value={selectedResumeId}
          />
          <ResumeVersionSelector
            label="Resume Version"
            onChange={(value) => setSelectedResumeVersionId(value)}
            resumeId={selectedResumeId}
            value={selectedResumeVersionId}
          />
          <JDSelector
            label={`JD (${jobs.length})`}
            onChange={(value) => setSelectedJdId(value)}
            value={selectedJdId}
          />
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

      <article className="panel">
        <div className="panel-header">
          <h3>Compare Match Reports</h3>
          <span className="status-pill muted">POST /api/matches/compare</span>
        </div>
        <div className="selector-grid">
          <ResumeSelector
            label="Resume"
            onChange={(value) => {
              setCompareResumeId(value);
              setCompareVersionA("");
              setCompareVersionB("");
            }}
            value={compareResumeId}
          />
          <ResumeVersionSelector
            label="Version A"
            onChange={(value) => setCompareVersionA(value)}
            resumeId={compareResumeId}
            value={compareVersionA}
          />
          <ResumeVersionSelector
            label="Version B"
            onChange={(value) => setCompareVersionB(value)}
            resumeId={compareResumeId}
            value={compareVersionB}
          />
          <JDSelector
            label="JD"
            onChange={(value) => setCompareJdId(value)}
            value={compareJdId}
          />
          <button
            className="primary-action"
            disabled={!canCompare || isComparing}
            onClick={handleCompare}
            type="button"
          >
            {isComparing ? "Comparing..." : "Compare"}
          </button>
        </div>
        {compareError ? <p className="error-text">{compareError}</p> : null}
        {compareResult ? (
          <div className="compare-result">
            <div className="readonly-grid">
              <span>Mode: {compareResult.compare_mode}</span>
              <span>Sort: {compareResult.sort_key}</span>
              <span>Items: {compareResult.items.length}</span>
            </div>
            <ul className="activity-list report-list">
              {compareResult.items.map((item) => (
                <li key={item.match_report_id}>
                  <div>
                    <strong>Rank {item.rank}: score {item.total_score}</strong>
                    <small>{item.score_delta_from_top} from top / {item.main_gaps.length} gaps</small>
                  </div>
                  <span>{item.resume_version_id ?? "No version"}</span>
                  <span>{item.main_strengths.slice(0, 2).join(", ") || "No strengths"}</span>
                  <button
                    className="ghost-action"
                    onClick={() => void handleSelectReport(item.match_report_id)}
                    type="button"
                  >
                    Detail
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </article>

      <div className="two-column">
        <article className="panel score-panel">
          <div className="panel-header">
            <h3>总分</h3>
            <span className="status-pill">
              {latestMatch ? "Latest report" : "No run"}
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
                  <strong>Score {match.total_score}</strong>
                  <small>
                    Resume Version: {match.resume_version_id ?? "unknown"}
                  </small>
                </div>
                <span>{match.jd_id}</span>
                <span>{match.risk_flags.length} risks</span>
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
            {detailReport ? "Selected report" : "None"}
          </span>
        </div>
        {detailReport ? (
          <>
            <ul className="activity-list">
              <li>
                <strong>Report Ref</strong>
                <span>{detailReport.match_report_id}</span>
              </li>
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
      </article>
    </section>
  );
}
