import type { PageKey } from "../types/navigation";
import type { WorkbenchState } from "../types/api";

type DashboardPageProps = {
  loadError: string | null;
  state: WorkbenchState;
  onNavigate: (page: PageKey) => void;
};

const workflow = [
  "Resume Upload",
  "JD Create",
  "Match Report",
  "Frontend Display",
];

export function DashboardPage({
  loadError,
  state,
  onNavigate,
}: DashboardPageProps) {
  const metrics = [
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
      detail: "Mock risk flags",
      tone: "red",
      page: "match" as const,
    },
  ];

  return (
    <section className="page-stack" aria-labelledby="dashboard-title">
      <div className="page-heading">
        <p className="eyebrow">Workbench</p>
        <h2 id="dashboard-title">Dashboard</h2>
        <p>阶段 1C 展示内存 Mock 状态；刷新页面或重启后端会丢失数据。</p>
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
            <h3>Mock 闭环</h3>
            <span className="status-pill">Phase 1C</span>
          </div>
          <div className="workflow-rail" aria-label="阶段 1C Mock 流程">
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
            <span className="status-pill muted">In memory</span>
          </div>
          <ul className="activity-list">
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
          </ul>
        </article>
      </div>
    </section>
  );
}
