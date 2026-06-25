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
  "Project Facts",
  "Project Rewrite",
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
  const resumeDetail = state.latestResume
    ? `${state.latestResume.parse_status} / ${state.latestResume.risk_flags.length} resume risks`
    : "等待上传";
  const latestProject = state.projects[state.projects.length - 1] ?? null;
  const activeProjectCount = state.projects.filter(
    (project) => project.status === "active",
  ).length;
  const interviewStats = state.interviewStats;
  const latestInterviewScore =
    interviewStats?.latest_average_score != null
      ? interviewStats.latest_average_score.toFixed(2)
      : "--";
  const latestWeaknessTags =
    interviewStats?.latest_weakness_tags.length
      ? interviewStats.latest_weakness_tags.join(", ")
      : "No weakness tags";
  const studyPlanStats = state.studyPlanStats;
  const latestStudyTarget =
    studyPlanStats?.latest_target_role ?? "No study target";
  const ragStats = state.ragStats;
  const latestRagAnswer =
    ragStats?.latest_answer_question_preview ?? "No RAG answer";
  const latestRagUncertainty =
    ragStats?.latest_answer_uncertainty ?? "No uncertainty";
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
      detail: resumeDetail,
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
      label: "Projects",
      value: String(state.projects.length),
      detail: latestProject
        ? `${latestProject.name} / ${latestProject.status}`
        : "等待创建",
      tone: "green",
      page: "project-optimization" as const,
    },
    {
      label: "Active Projects",
      value: String(activeProjectCount),
      detail: "Confirmed facts",
      tone: "blue",
      page: "project-optimization" as const,
    },
    {
      label: "Risk",
      value: String(state.latestMatch?.risk_flags.length ?? 0),
      detail: "Quality signals",
      tone: "red",
      page: "match" as const,
    },
    {
      label: "RAG Documents",
      value: String(ragStats?.total_documents ?? state.ragDocuments.length),
      detail: "RAG documents",
      tone: "blue",
      page: "knowledge" as const,
    },
    {
      label: "Indexed Documents",
      value: String(ragStats?.indexed_documents ?? 0),
      detail: "RAG indexed docs",
      tone: "green",
      page: "knowledge" as const,
    },
    {
      label: "RAG Chunks",
      value: String(ragStats?.total_chunks ?? 0),
      detail: "Preview-first chunks",
      tone: "amber",
      page: "knowledge" as const,
    },
    {
      label: "Grounded Answers",
      value: String(ragStats?.grounded_answer_runs ?? 0),
      detail: "RAG answer runs",
      tone: "green",
      page: "knowledge" as const,
    },
    {
      label: "Ungrounded Answers",
      value: String(ragStats?.ungrounded_answer_runs ?? 0),
      detail: "Needs source review",
      tone: "red",
      page: "knowledge" as const,
    },
    {
      label: "Latest RAG Answer",
      value: String(ragStats?.total_answer_runs ?? 0),
      detail: latestRagAnswer,
      tone: "blue",
      page: "knowledge" as const,
    },
    {
      label: "Latest RAG Uncertainty",
      value: latestRagUncertainty,
      detail: ragStats?.latest_answer_run_id ?? "No answer run",
      tone: "amber",
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
      label: "Interview Questions",
      value: String(interviewStats?.total_questions ?? 0),
      detail: "Interview training",
      tone: "amber",
      page: "interview" as const,
    },
    {
      label: "Interview Answers",
      value: String(interviewStats?.total_answers ?? 0),
      detail: `${interviewStats?.scored_answers ?? 0} scored`,
      tone: "blue",
      page: "interview" as const,
    },
    {
      label: "Latest Interview Score",
      value: latestInterviewScore,
      detail: "Deterministic training score",
      tone: "green",
      page: "interview" as const,
    },
    {
      label: "Study Plans",
      value: String(studyPlanStats?.total_plans ?? 0),
      detail: "Study plan center",
      tone: "green",
      page: "study-plan" as const,
    },
    {
      label: "Active Study Plans",
      value: String(studyPlanStats?.active_plans ?? 0),
      detail: latestStudyTarget,
      tone: "blue",
      page: "study-plan" as const,
    },
    {
      label: "Pending Tasks",
      value: String(studyPlanStats?.pending_tasks ?? 0),
      detail: `${studyPlanStats?.in_progress_tasks ?? 0} in progress`,
      tone: "amber",
      page: "study-plan" as const,
    },
    {
      label: "Blocked Tasks",
      value: String(studyPlanStats?.blocked_tasks ?? 0),
      detail: "Study plan tasks",
      tone: "red",
      page: "study-plan" as const,
    },
    {
      label: "Done Tasks",
      value: String(studyPlanStats?.done_tasks ?? 0),
      detail: "Study plan tasks",
      tone: "green",
      page: "study-plan" as const,
    },
    {
      label: "App Interview Stages",
      value: String(state.applicationStats?.interview_count ?? 0),
      detail: "Application tracking",
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
        <p>当前稳定节点：v1.1 Study Plan Center，已支持 Profile、Resume parsing / risk-check、Project Optimization、Interview Training、Study Plan、SQLite 持久化工作台、Knowledge Base、deterministic Agent Runs、手动投递 tracking、Bad Case 和 deterministic evaluation。当前不接真实 LLM，不做 LLM judge，不自动投递。</p>
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
            <span className="status-pill">v0.9 Project Optimization</span>
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
              <span>
                {state.latestResume
                  ? `${state.latestResume.filename} / ${state.latestResume.parse_status}`
                  : "未上传"}
              </span>
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
              <strong>Projects</strong>
              <span>
                {latestProject
                  ? `${latestProject.name} / ${latestProject.status}`
                  : `${state.projects.length} records / ${activeProjectCount} active`}
              </span>
            </li>
            <li>
              <strong>Knowledge</strong>
              <span>
                {ragStats
                  ? `${ragStats.total_documents} docs / ${ragStats.indexed_documents} indexed / ${ragStats.total_chunks} chunks`
                  : `${state.ragDocuments.length} docs / 0 indexed / 0 chunks`}
              </span>
            </li>
            <li>
              <strong>RAG Answers</strong>
              <span>
                {ragStats
                  ? `${ragStats.grounded_answer_runs} grounded / ${ragStats.ungrounded_answer_runs} ungrounded`
                  : "0 grounded / 0 ungrounded"}
              </span>
            </li>
            <li>
              <strong>Latest RAG Uncertainty</strong>
              <span>{latestRagUncertainty}</span>
            </li>
            <li>
              <strong>Agent Runs</strong>
              <span>{state.agentRuns.length} deterministic runs</span>
            </li>
            <li>
              <strong>Interview Training</strong>
              <span>
                {interviewStats
                  ? `${interviewStats.total_questions} questions / ${interviewStats.total_answers} answers / ${interviewStats.scored_answers} scored`
                  : "0 questions / 0 answers / 0 scored"}
              </span>
            </li>
            <li>
              <strong>Latest Weakness Tags</strong>
              <span>{latestWeaknessTags}</span>
            </li>
            <li>
              <strong>Study Plan Center</strong>
              <span>
                {studyPlanStats
                  ? `${studyPlanStats.total_plans} plans / ${studyPlanStats.active_plans} active / ${studyPlanStats.pending_tasks} pending tasks`
                  : "0 plans / 0 active / 0 pending tasks"}
              </span>
            </li>
            <li>
              <strong>Latest Study Target</strong>
              <span>{latestStudyTarget}</span>
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
