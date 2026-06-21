import { useEffect, useState } from "react";

import { AppShell } from "./components/AppShell";
import { listAgentRuns } from "./api/agents";
import { listBadCases } from "./api/evaluations";
import { listJobs } from "./api/jobs";
import { listMatches } from "./api/matches";
import { listRagDocuments } from "./api/rag";
import { listResumes } from "./api/resumes";
import { AgentRunsPage } from "./pages/AgentRunsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { JDCenterPage } from "./pages/JDCenterPage";
import { KnowledgeBasePage } from "./pages/KnowledgeBasePage";
import { MatchReportPage } from "./pages/MatchReportPage";
import { QualityReviewPage } from "./pages/QualityReviewPage";
import { ResumeCenterPage } from "./pages/ResumeCenterPage";
import type {
  AgentRunRecord,
  BadCaseRecord,
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
  const [badCases, setBadCases] = useState<BadCaseRecord[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  const refreshWorkbench = async () => {
    try {
      const [
        resumeList,
        jobList,
        matchList,
        ragDocumentList,
        agentRunList,
        badCaseList,
      ] = await Promise.all([
          listResumes(),
          listJobs(),
          listMatches(),
          listRagDocuments(),
          listAgentRuns({ limit: 50 }),
          listBadCases({ limit: 50 }),
        ]);
      setResumes(resumeList.items);
      setJobs(jobList.items);
      setMatches(matchList.items);
      setRagDocuments(ragDocumentList.items);
      setAgentRuns(agentRunList.items);
      setBadCases(badCaseList.items);
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
        error instanceof Error ? error.message : "Unable to load mock state.",
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
    badCases,
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
    if (activePage === "quality") {
      return (
        <QualityReviewPage
          badCases={badCases}
          onBadCasesChanged={setBadCases}
        />
      );
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
