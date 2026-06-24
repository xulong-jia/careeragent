import { useEffect, useState } from "react";

import { AppShell } from "./components/AppShell";
import { listAgentRuns } from "./api/agents";
import { getApplicationStats, listApplications } from "./api/applications";
import { getEvaluationStats, listBadCases } from "./api/evaluations";
import { listJobs } from "./api/jobs";
import { listMatches } from "./api/matches";
import { listRagDocuments } from "./api/rag";
import { listResumes } from "./api/resumes";
import { AgentRunsPage } from "./pages/AgentRunsPage";
import { ApplicationTrackerPage } from "./pages/ApplicationTrackerPage";
import { DashboardPage } from "./pages/DashboardPage";
import { EvaluationPage } from "./pages/EvaluationPage";
import { JDCenterPage } from "./pages/JDCenterPage";
import { KnowledgeBasePage } from "./pages/KnowledgeBasePage";
import { MatchReportPage } from "./pages/MatchReportPage";
import { QualityReviewPage } from "./pages/QualityReviewPage";
import { ResumeCenterPage } from "./pages/ResumeCenterPage";
import type {
  AgentRunRecord,
  ApplicationRecord,
  ApplicationStats,
  BadCaseRecord,
  EvaluationStats,
  JobRecord,
  MatchReport,
  RagDocumentRecord,
  ResumeRecord,
} from "./types/api";
import type { NavigationItem, PageKey } from "./types/navigation";

const navigation: NavigationItem[] = [
  {
    key: "dashboard",
    label: "Dashboard",
    description: "总览",
  },
  {
    key: "resume",
    label: "Resume Center",
    description: "简历版本",
  },
  {
    key: "jd",
    label: "JD Center",
    description: "岗位画像",
  },
  {
    key: "match",
    label: "Match Report",
    description: "匹配报告",
  },
  {
    key: "knowledge",
    label: "Knowledge Base",
    description: "RAG 知识库",
  },
  {
    key: "agents",
    label: "Agent Runs",
    description: "工作流状态机",
  },
  {
    key: "applications",
    label: "Applications",
    description: "投递 tracking",
  },
  {
    key: "evaluation",
    label: "Evaluation",
    description: "确定性评测",
  },
  {
    key: "quality",
    label: "Quality Review",
    description: "Bad Case 复盘",
  },
];

export default function App() {
  const [activePage, setActivePage] = useState<PageKey>("dashboard");
  const [latestResume, setLatestResume] = useState<ResumeRecord | null>(null);
  const [latestJob, setLatestJob] = useState<JobRecord | null>(null);
  const [latestMatch, setLatestMatch] = useState<MatchReport | null>(null);
  const [resumes, setResumes] = useState<ResumeRecord[]>([]);
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [matches, setMatches] = useState<MatchReport[]>([]);
  const [ragDocuments, setRagDocuments] = useState<RagDocumentRecord[]>([]);
  const [agentRuns, setAgentRuns] = useState<AgentRunRecord[]>([]);
  const [applications, setApplications] = useState<ApplicationRecord[]>([]);
  const [applicationStats, setApplicationStats] =
    useState<ApplicationStats | null>(null);
  const [badCases, setBadCases] = useState<BadCaseRecord[]>([]);
  const [evaluationStats, setEvaluationStats] = useState<EvaluationStats | null>(
    null,
  );
  const [loadError, setLoadError] = useState<string | null>(null);

  const refreshWorkbench = async () => {
    try {
      const [
        resumeList,
        jobList,
        matchList,
        ragDocumentList,
        agentRunList,
        applicationList,
        applicationStatsData,
        badCaseList,
        evaluationStatsData,
      ] = await Promise.all([
          listResumes(),
          listJobs(),
          listMatches(),
          listRagDocuments(),
          listAgentRuns({ limit: 50 }),
          listApplications(),
          getApplicationStats(),
          listBadCases({ limit: 50 }),
          getEvaluationStats(),
        ]);
      setResumes(resumeList.items);
      setJobs(jobList.items);
      setMatches(matchList.items);
      setRagDocuments(ragDocumentList.items);
      setAgentRuns(agentRunList.items);
      setApplications(applicationList.items);
      setApplicationStats(applicationStatsData);
      setBadCases(badCaseList.items);
      setEvaluationStats(evaluationStatsData);
      setLatestResume(
        (current) => current ?? resumeList.items[resumeList.items.length - 1] ?? null,
      );
      setLatestJob(
        (current) => current ?? jobList.items[jobList.items.length - 1] ?? null,
      );
      setLatestMatch(
        (current) => current ?? matchList.items[matchList.items.length - 1] ?? null,
      );
      setLoadError(null);
    } catch (error) {
      setLoadError(
        error instanceof Error ? error.message : "Unable to load workbench data.",
      );
    }
  };

  useEffect(() => {
    void refreshWorkbench();
  }, []);

  const workbenchState = {
    latestResume,
    latestJob,
    latestMatch,
    resumes,
    jobs,
    matches,
    ragDocuments,
    agentRuns,
    applications,
    applicationStats,
    badCases,
    evaluationStats,
  };

  const renderPage = () => {
    if (activePage === "resume") {
      return (
        <ResumeCenterPage
          latestResume={latestResume}
          onRefresh={refreshWorkbench}
          onResumeUploaded={setLatestResume}
          resumes={resumes}
        />
      );
    }
    if (activePage === "jd") {
      return (
        <JDCenterPage
          jobs={jobs}
          latestJob={latestJob}
          onJobCreated={setLatestJob}
          onRefresh={refreshWorkbench}
        />
      );
    }
    if (activePage === "match") {
      return (
        <MatchReportPage
          jobs={jobs}
          latestJob={latestJob}
          latestMatch={latestMatch}
          latestResume={latestResume}
          matches={matches}
          onMatchRun={setLatestMatch}
          onRefresh={refreshWorkbench}
          resumes={resumes}
        />
      );
    }
    if (activePage === "knowledge") {
      return <KnowledgeBasePage onDocumentsChanged={setRagDocuments} />;
    }
    if (activePage === "agents") {
      return (
        <AgentRunsPage
          agentRuns={agentRuns}
          onAgentRunsChanged={setAgentRuns}
        />
      );
    }
    if (activePage === "applications") {
      return (
        <ApplicationTrackerPage
          applicationStats={applicationStats}
          applications={applications}
          onApplicationStatsChanged={setApplicationStats}
          onApplicationsChanged={setApplications}
        />
      );
    }
    if (activePage === "quality") {
      return (
        <QualityReviewPage
          badCases={badCases}
          onBadCasesChanged={setBadCases}
        />
      );
    }
    if (activePage === "evaluation") {
      return <EvaluationPage />;
    }
    return (
      <DashboardPage
        loadError={loadError}
        onNavigate={setActivePage}
        state={workbenchState}
      />
    );
  };

  return (
    <AppShell
      activePage={activePage}
      navigation={navigation}
      onNavigate={setActivePage}
    >
      {renderPage()}
    </AppShell>
  );
}
