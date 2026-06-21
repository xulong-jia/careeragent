import { useEffect, useState } from "react";

import { AppShell } from "./components/AppShell";
import { listJobs } from "./api/jobs";
import { listMatches } from "./api/matches";
import { listRagDocuments } from "./api/rag";
import { listResumes } from "./api/resumes";
import { DashboardPage } from "./pages/DashboardPage";
import { JDCenterPage } from "./pages/JDCenterPage";
import { KnowledgeBasePage } from "./pages/KnowledgeBasePage";
import { MatchReportPage } from "./pages/MatchReportPage";
import { ResumeCenterPage } from "./pages/ResumeCenterPage";
import type {
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
  const [loadError, setLoadError] = useState<string | null>(null);

  const refreshWorkbench = async () => {
    try {
      const [resumeList, jobList, matchList, ragDocumentList] = await Promise.all([
        listResumes(),
        listJobs(),
        listMatches(),
        listRagDocuments(),
      ]);
      setResumes(resumeList.items);
      setJobs(jobList.items);
      setMatches(matchList.items);
      setRagDocuments(ragDocumentList.items);
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
