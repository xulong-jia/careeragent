import type { PageKey } from "../types/navigation";
import type { WorkbenchState } from "../types/api";

type DashboardPageProps = {
  loadError: string | null;
  state: WorkbenchState;
  onNavigate: (page: PageKey) => void;
};

const workflow = [
  "Profile Confirm",
  "Resume Upload",
  "Version History",
  "JD Create",
  "Match History",
  "RAG Search",
  "Agent Run",
  "Frontend Display",
];

export function DashboardPage({
  loadError,
  state,
  onNavigate,
}: DashboardPageProps) {
  const profileDetail = state.latestProfileSummary
    ? `${state.latestProfileSummary.readiness_level} / ${state.latestProfileSummary.completeness_score}%`
    : "等待创建";
  const metrics = [
    {
      label: "Profile",
      value: String(state.profiles.length),
      detail: profileDetail,
      tone: "green",
      page: "profile" as const,
    },
    {
      label: "Resume",
      value: String(state.resumes.length),
      detail: state.latestResume?.resume_id ?? "等待上传",
      tone: "green",
      page: "resume" as const,
    },
    {
      label: "JD",
      value: String(state.jobs.length),
      detail: state.latestJob?.jd_id ?? "等待创建",
      tone: "blue",
      page: "jd" as const,
    },
    {
      label: "Match",
      value: String(state.matches.length),
      detail: state.latestMatch?.match_report_id ?? "等待运行",
      tone: "amber",
      page: "match" as const,
    },
    {
      label: "Risk",
      value: String(state.latestMatch?.risk_flags.length ?? 0),
      detail: "Quality signals",
      tone: "red",
      page: "match" as const,
    },
    {
      label: "Knowledge",
      value: String(state.ragDocuments.length),
      detail: "RAG documents",
      tone: "blue",
      page: "knowledge" as const,
    },
    {
      label: "Agent",
      value: String(state.agentRuns.length),
      detail: "Deterministic runs",
      tone: "green",
      page: "agents" as const,
    },
    {
      label: "Applications",
      value: String(state.applicationStats?.total_applications ?? 0),
      detail: "Manual tracking",
      tone: "blue",
      page: "applications" as const,
    },
    {
      label: "Interviews",
      value: String(state.applicationStats?.interview_count ?? 0),
      detail: "Active interview stages",
      tone: "amber",
      page: "applications" as const,
    },
    {
      label: "Offers",
      value: String(state.applicationStats?.offer_count ?? 0),
      detail: "Application outcomes",
      tone: "green",
      page: "applications" as const,
    },
    {
      label: "Rejected",
      value: String(state.applicationStats?.rejected_count ?? 0),
      detail: "Rejected applications",
      tone: "red",
      page: "applications" as const,
    },
    {
      label: "Active Apps",
      value: String(state.applicationStats?.active_count ?? 0),
      detail: "Not closed",
      tone: "blue",
      page: "applications" as const,
    },
    {
      label: "Quality",
      value: String(state.badCases.length),
      detail: "Manual bad cases",
      tone: "red",
      page: "quality" as const,
    },
    {
      label: "Evaluation",
      value: String(state.evaluationStats?.total_runs ?? 0),
      detail:
        state.evaluationStats?.latest_pass_rate != null
          ? `${Math.round(state.evaluationStats.latest_pass_rate * 100)}% latest`
          : "Deterministic smoke",
      tone: "blue",
      page: "evaluation" as const,
    },
  ];

  return (
    <section className="page-stack" aria-labelledby="dashboard-title">
      <div className="page-heading">
        <p className="eyebrow">Workbench</p>
        <h2 id="dashboard-title">Dashboard</h2>
        <p>当前稳定节点：v0.8.0-resume-profile-foundation，已支持 Profile Center MVP、真实 PDF / DOCX 文本提取、deterministic resume parsing、risk-check API、SQLite 持久化工作台、Knowledge Base、deterministic Agent Runs、手动投递 tracking、Bad Case 和 deterministic evaluation。当前不接真实 LLM，不做 LLM judge，不自动投递。</p>
      </div>
      {loadError ? <p className="error-text">{loadError}</p> : null}

      <div className="metric-grid">
        {metrics.map((metric) => (
          <button
            className={`metric-card ${metric.tone}`}
            key={metric.label}
            onClick={() => onNavigate(metric.page)}
            type="button"
          >
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            <small>{metric.detail}</small>
          </button>
        ))}
      </div>

      <div className="two-column">
        <article className="panel">
          <div className="panel-header">
            <h3>持久化闭环</h3>
            <span className="status-pill">v0.6.0 Evaluation</span>
          </div>
          <div className="workflow-rail" aria-label="阶段 2F 持久化流程">
            {workflow.map((step) => (
              <div className="workflow-step" key={step}>
                <span aria-hidden="true" />
                <p>{step}</p>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>当前对象</h3>
            <span className="status-pill muted">SQLite-backed</span>
          </div>
          <ul className="activity-list">
            <li>
              <strong>Profile</strong>
              <span>
                {state.latestProfileSummary
                  ? `${state.latestProfileSummary.readiness_level} / ${state.latestProfileSummary.completeness_score}%`
                  : "未创建"}
              </span>
            </li>
            <li>
              <strong>Resume</strong>
              <span>{state.latestResume?.filename ?? "未上传"}</span>
            </li>
            <li>
              <strong>JD</strong>
              <span>{state.latestJob?.job_title ?? "未创建"}</span>
            </li>
            <li>
              <strong>Match</strong>
              <span>{state.latestMatch?.match_report_id ?? "未运行"}</span>
            </li>
            <li>
              <strong>Knowledge</strong>
              <span>{state.ragDocuments.length} documents</span>
            </li>
            <li>
              <strong>Agent Runs</strong>
              <span>{state.agentRuns.length} deterministic runs</span>
            </li>
            <li>
              <strong>Applications</strong>
              <span>
                {state.applicationStats?.total_applications ?? 0} records /{" "}
                {state.applicationStats?.active_count ?? 0} active
              </span>
            </li>
            <li>
              <strong>Quality Review</strong>
              <span>{state.badCases.length} manual bad cases</span>
            </li>
            <li>
              <strong>Evaluation</strong>
              <span>
                {state.evaluationStats?.total_runs ?? 0} runs /{" "}
                {state.evaluationStats?.failed_results ?? 0} failed results
              </span>
            </li>
          </ul>
        </article>
      </div>
    </section>
  );
}
