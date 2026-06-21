type Metric = {
  label: string;
  value: string;
  detail: string;
  tone: "green" | "blue" | "amber" | "red";
};

const metrics: Metric[] = [
  {
    label: "简历版本",
    value: "0",
    detail: "等待解析模块接入",
    tone: "green",
  },
  {
    label: "JD 记录",
    value: "0",
    detail: "岗位中心已占位",
    tone: "blue",
  },
  {
    label: "匹配报告",
    value: "0",
    detail: "评分引擎未启用",
    tone: "amber",
  },
  {
    label: "风险项",
    value: "0",
    detail: "Bad Case 后续接入",
    tone: "red",
  },
];

const workflow = [
  "Profile",
  "Resume Parsing",
  "JD Parsing",
  "Match Scoring",
  "Interview Prep",
  "Application Review",
];

export function DashboardPage() {
  return (
    <section className="page-stack" aria-labelledby="dashboard-title">
      <div className="page-heading">
        <p className="eyebrow">Workbench</p>
        <h2 id="dashboard-title">Dashboard</h2>
        <p>阶段 0 只展示工作台结构，不执行解析、匹配、RAG 或 Agent 工作流。</p>
      </div>

      <div className="metric-grid">
        {metrics.map((metric) => (
          <article className={`metric-card ${metric.tone}`} key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            <small>{metric.detail}</small>
          </article>
        ))}
      </div>

      <div className="two-column">
        <article className="panel">
          <div className="panel-header">
            <h3>求职闭环</h3>
            <span className="status-pill">Skeleton</span>
          </div>
          <div className="workflow-rail" aria-label="求职闭环流程">
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
            <h3>近期工作</h3>
            <span className="status-pill muted">Phase 0</span>
          </div>
          <ul className="activity-list">
            <li>
              <strong>后端健康检查</strong>
              <span>GET /health</span>
            </li>
            <li>
              <strong>前端工作台导航</strong>
              <span>Dashboard / Resume / JD / Match</span>
            </li>
            <li>
              <strong>隐私目录隔离</strong>
              <span>local_data ignored</span>
            </li>
          </ul>
        </article>
      </div>
    </section>
  );
}
