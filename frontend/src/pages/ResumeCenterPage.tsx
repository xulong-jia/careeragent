const resumeSections = [
  "Basic Info",
  "Education",
  "Projects",
  "Experience",
  "Skills",
  "Risk Flags",
];

export function ResumeCenterPage() {
  return (
    <section className="page-stack" aria-labelledby="resume-title">
      <div className="page-heading">
        <p className="eyebrow">Resume</p>
        <h2 id="resume-title">Resume Center</h2>
        <p>预留上传、解析结果确认、版本管理和风险检测区域。</p>
      </div>

      <div className="two-column wide-left">
        <article className="panel upload-panel">
          <div className="panel-header">
            <h3>简历入口</h3>
            <span className="status-pill muted">Pending API</span>
          </div>
          <div className="drop-zone" aria-label="简历上传占位区">
            <strong>PDF / DOCX / Markdown</strong>
            <span>文件只会在后续阶段写入受控本地目录。</span>
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>版本队列</h3>
            <span className="status-pill">0 saved</span>
          </div>
          <div className="empty-state">
            <strong>暂无简历版本</strong>
            <span>后续阶段会保存 confirmed version，并支持匹配和投递绑定。</span>
          </div>
        </article>
      </div>

      <article className="panel">
        <div className="panel-header">
          <h3>结构化结果</h3>
          <span className="status-pill muted">Schema preview</span>
        </div>
        <div className="section-grid">
          {resumeSections.map((section) => (
            <div className="schema-tile" key={section}>
              <span>{section}</span>
              <small>Not parsed</small>
            </div>
          ))}
        </div>
      </article>
    </section>
  );
}
