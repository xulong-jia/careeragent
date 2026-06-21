const profileFields = [
  "Role Category",
  "Required Skills",
  "Preferred Skills",
  "Responsibilities",
  "Interview Focus",
  "Risk Level",
];

export function JDCenterPage() {
  return (
    <section className="page-stack" aria-labelledby="jd-title">
      <div className="page-heading">
        <p className="eyebrow">Job Description</p>
        <h2 id="jd-title">JD Center</h2>
        <p>预留 JD 原文、岗位画像、技能分类和面试重点区域。</p>
      </div>

      <div className="two-column wide-left">
        <article className="panel">
          <div className="panel-header">
            <h3>JD 原文</h3>
            <span className="status-pill muted">Draft</span>
          </div>
          <textarea
            className="jd-textarea"
            placeholder="粘贴岗位描述，后续阶段将保存原文并生成 job profile。"
          />
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>岗位画像</h3>
            <span className="status-pill">Not parsed</span>
          </div>
          <div className="profile-field-list">
            {profileFields.map((field) => (
              <div className="profile-field" key={field}>
                <span>{field}</span>
                <small>待生成</small>
              </div>
            ))}
          </div>
        </article>
      </div>
    </section>
  );
}
