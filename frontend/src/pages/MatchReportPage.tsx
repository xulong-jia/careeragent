const scoreRows = [
  ["Skill Match", 0],
  ["Project Relevance", 0],
  ["Business Understanding", 0],
  ["Expression Quality", 0],
  ["Education Fit", 0],
  ["Risk Control", 0],
] as const;

export function MatchReportPage() {
  return (
    <section className="page-stack" aria-labelledby="match-title">
      <div className="page-heading">
        <p className="eyebrow">Report</p>
        <h2 id="match-title">Match Report</h2>
        <p>预留总分、分维度评分、证据、差距、风险和修改优先级展示。</p>
      </div>

      <div className="two-column">
        <article className="panel score-panel">
          <div className="panel-header">
            <h3>总分</h3>
            <span className="status-pill muted">No run</span>
          </div>
          <div className="score-dial">
            <strong>--</strong>
            <span>等待匹配评分引擎</span>
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>维度评分</h3>
            <span className="status-pill">0 dimensions</span>
          </div>
          <div className="score-list">
            {scoreRows.map(([label, value]) => (
              <div className="score-row" key={label}>
                <span>{label}</span>
                <div className="score-track" aria-label={`${label} score ${value}`}>
                  <span style={{ width: `${value}%` }} />
                </div>
                <strong>{value}</strong>
              </div>
            ))}
          </div>
        </article>
      </div>

      <div className="three-column">
        <article className="panel mini-panel">
          <h3>Evidence</h3>
          <p>证据列表将在匹配报告生成后展示。</p>
        </article>
        <article className="panel mini-panel">
          <h3>Gaps</h3>
          <p>技能、项目和表达差距将在后续阶段接入。</p>
        </article>
        <article className="panel mini-panel">
          <h3>Risks</h3>
          <p>编造、夸大和证据不足风险保持独立展示。</p>
        </article>
      </div>
    </section>
  );
}
