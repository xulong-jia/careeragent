import { useEffect, useState } from "react";

import { AppShell } from "./components/AppShell";
import {
  getMe,
  listSessions,
  logout as logoutUser,
  revokeSession as revokeAuthSession,
} from "./api/auth";
import { clearAuthToken, getAuthToken } from "./api/client";
import { listAgentRuns } from "./api/agents";
import { getApplicationStats, listApplications } from "./api/applications";
import { getEvaluationStats, listBadCases } from "./api/evaluations";
import { getInterviewStats } from "./api/interviews";
import { listJobs } from "./api/jobs";
import { listMatches } from "./api/matches";
import { getProfileSummary, listProfiles } from "./api/profiles";
import { listProjects } from "./api/projects";
import { getRagStats, listRagDocuments } from "./api/rag";
import { listResumes } from "./api/resumes";
import { getStudyPlanStats } from "./api/studyPlans";
import { AgentRunsPage } from "./pages/AgentRunsPage";
import { ApplicationTrackerPage } from "./pages/ApplicationTrackerPage";
import { AuthPage } from "./pages/AuthPage";
import { DashboardPage } from "./pages/DashboardPage";
import { EvaluationPage } from "./pages/EvaluationPage";
import { InterviewCenterPage } from "./pages/InterviewCenterPage";
import { JDCenterPage } from "./pages/JDCenterPage";
import { KnowledgeBasePage } from "./pages/KnowledgeBasePage";
import { MatchReportPage } from "./pages/MatchReportPage";
import { ProfilePage } from "./pages/ProfilePage";
import { ProjectOptimizationPage } from "./pages/ProjectOptimizationPage";
import { QualityReviewPage } from "./pages/QualityReviewPage";
import { ResumeCenterPage } from "./pages/ResumeCenterPage";
import { StudyPlanPage } from "./pages/StudyPlanPage";
import type {
  AgentRunRecord,
  AuthMe,
  AuthSession,
  AuthSessionRecord,
  ApplicationRecord,
  ApplicationStats,
  BadCaseRecord,
  EvaluationStats,
  InterviewStats,
  JobRecord,
  MatchReport,
  ProfileRecord,
  ProfileSummary,
  ProjectRecord,
  RagDocumentRecord,
  RagStats,
  ResumeRecord,
  StudyPlanStats,
} from "./types/api";
import type { NavigationItem, PageKey } from "./types/navigation";

const navigation: NavigationItem[] = [
  {
    key: "dashboard",
    label: "Dashboard",
    description: "总览",
  },
  {
    key: "profile",
    label: "Profile Center",
    description: "用户画像",
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
    key: "project-optimization",
    label: "Project Optimization",
    description: "项目优化",
  },
  {
    key: "interview",
    label: "Interview Center",
    description: "面试准备",
  },
  {
    key: "study-plan",
    label: "Study Plan",
    description: "学习计划",
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

async function loadProfileWorkbench(): Promise<{
  profiles: ProfileRecord[];
  latestProfileSummary: ProfileSummary | null;
}> {
  try {
    const profileList = await listProfiles();
    const latestProfile = profileList.items[profileList.items.length - 1] ?? null;
    const latestProfileSummary = latestProfile
      ? await getProfileSummary(latestProfile.id)
      : null;
    return {
      profiles: profileList.items,
      latestProfileSummary,
    };
  } catch {
    return {
      profiles: [],
      latestProfileSummary: null,
    };
  }
}

async function loadInterviewStats(): Promise<InterviewStats | null> {
  try {
    return await getInterviewStats();
  } catch {
    return null;
  }
}

async function loadStudyPlanStats(): Promise<StudyPlanStats | null> {
  try {
    return await getStudyPlanStats();
  } catch {
    return null;
  }
}

async function loadRagStats(): Promise<RagStats | null> {
  try {
    return await getRagStats();
  } catch {
    return null;
  }
}

export default function App() {
  const [auth, setAuth] = useState<AuthMe | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [activePage, setActivePage] = useState<PageKey>("dashboard");
  const [latestResume, setLatestResume] = useState<ResumeRecord | null>(null);
  const [latestJob, setLatestJob] = useState<JobRecord | null>(null);
  const [latestMatch, setLatestMatch] = useState<MatchReport | null>(null);
  const [resumes, setResumes] = useState<ResumeRecord[]>([]);
  const [profiles, setProfiles] = useState<ProfileRecord[]>([]);
  const [latestProfileSummary, setLatestProfileSummary] =
    useState<ProfileSummary | null>(null);
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [matches, setMatches] = useState<MatchReport[]>([]);
  const [ragDocuments, setRagDocuments] = useState<RagDocumentRecord[]>([]);
  const [ragStats, setRagStats] = useState<RagStats | null>(null);
  const [agentRuns, setAgentRuns] = useState<AgentRunRecord[]>([]);
  const [applications, setApplications] = useState<ApplicationRecord[]>([]);
  const [applicationStats, setApplicationStats] =
    useState<ApplicationStats | null>(null);
  const [interviewStats, setInterviewStats] = useState<InterviewStats | null>(
    null,
  );
  const [studyPlanStats, setStudyPlanStats] = useState<StudyPlanStats | null>(
    null,
  );
  const [badCases, setBadCases] = useState<BadCaseRecord[]>([]);
  const [evaluationStats, setEvaluationStats] = useState<EvaluationStats | null>(
    null,
  );
  const [sessions, setSessions] = useState<AuthSessionRecord[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  const refreshSessions = async () => {
    try {
      const sessionList = await listSessions();
      setSessions(sessionList.items);
    } catch {
      setSessions([]);
    }
  };

  const refreshWorkbench = async () => {
    try {
      const [
        resumeList,
        profileWorkbench,
        projectList,
        jobList,
        matchList,
        ragDocumentList,
        ragStatsData,
        agentRunList,
        applicationList,
        applicationStatsData,
        interviewStatsData,
        studyPlanStatsData,
        badCaseList,
        evaluationStatsData,
      ] = await Promise.all([
          listResumes(),
          loadProfileWorkbench(),
          listProjects(),
          listJobs(),
          listMatches(),
          listRagDocuments(),
          loadRagStats(),
          listAgentRuns({ limit: 50 }),
          listApplications(),
          getApplicationStats(),
          loadInterviewStats(),
          loadStudyPlanStats(),
          listBadCases({ limit: 50 }),
          getEvaluationStats(),
        ]);
      setResumes(resumeList.items);
      setProfiles(profileWorkbench.profiles);
      setLatestProfileSummary(profileWorkbench.latestProfileSummary);
      setProjects(projectList.items);
      setJobs(jobList.items);
      setMatches(matchList.items);
      setRagDocuments(ragDocumentList.items);
      setRagStats(ragStatsData);
      setAgentRuns(agentRunList.items);
      setApplications(applicationList.items);
      setApplicationStats(applicationStatsData);
      setInterviewStats(interviewStatsData);
      setStudyPlanStats(studyPlanStatsData);
      setBadCases(badCaseList.items);
      setEvaluationStats(evaluationStatsData);
      setLatestResume(
        (current) =>
          current &&
          resumeList.items.some((item) => item.resume_id === current.resume_id)
            ? current
            : resumeList.items[resumeList.items.length - 1] ?? null,
      );
      setLatestJob(
        (current) =>
          current && jobList.items.some((item) => item.jd_id === current.jd_id)
            ? current
            : jobList.items[jobList.items.length - 1] ?? null,
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
    const handleExpired = () => {
      setAuth(null);
      setSessions([]);
      setLoadError("Session expired. Please sign in again.");
    };
    window.addEventListener("careeragent:auth-expired", handleExpired);
    if (!getAuthToken()) {
      setSessions([]);
      setAuthChecked(true);
      return () => {
        window.removeEventListener("careeragent:auth-expired", handleExpired);
      };
    }
    getMe()
      .then(async (me) => {
        setAuth(me);
        await refreshSessions();
      })
      .catch(() => {
        clearAuthToken();
        setAuth(null);
        setSessions([]);
      })
      .finally(() => setAuthChecked(true));
    return () => {
      window.removeEventListener("careeragent:auth-expired", handleExpired);
    };
  }, []);

  useEffect(() => {
    if (auth) {
      void refreshWorkbench();
      void refreshSessions();
    }
  }, [auth]);

  const handleAuthenticated = (session: AuthSession) => {
    setAuth({
      user: session.user,
      workspace: session.workspace,
    });
    setLoadError(null);
    void refreshSessions();
  };

  const handleLogout = async () => {
    await logoutUser();
    setAuth(null);
    setSessions([]);
    setActivePage("dashboard");
  };

  const handleRevokeSession = async (sessionId: string) => {
    const revokingCurrent = sessions.some(
      (session) => session.session_id === sessionId && session.current,
    );
    await revokeAuthSession(sessionId);
    if (revokingCurrent) {
      clearAuthToken();
      setAuth(null);
      setSessions([]);
      setActivePage("dashboard");
      return;
    }
    await refreshSessions();
  };

  const workbenchState = {
    latestResume,
    latestJob,
    latestMatch,
    profiles,
    latestProfileSummary,
    projects,
    resumes,
    jobs,
    matches,
    ragDocuments,
    ragStats,
    agentRuns,
    applications,
    applicationStats,
    interviewStats,
    studyPlanStats,
    badCases,
    evaluationStats,
  };

  const renderPage = () => {
    if (activePage === "profile") {
      return (
        <ProfilePage
          latestProfileSummary={latestProfileSummary}
          onProfileSummaryChanged={setLatestProfileSummary}
          onProfilesChanged={setProfiles}
          profiles={profiles}
        />
      );
    }
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
    if (activePage === "project-optimization") {
      return (
        <ProjectOptimizationPage
          onProjectsChanged={setProjects}
          projects={projects}
        />
      );
    }
    if (activePage === "interview") {
      return <InterviewCenterPage />;
    }
    if (activePage === "study-plan") {
      return <StudyPlanPage />;
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

  if (!authChecked) {
    return (
      <main className="auth-screen">
        <p className="stage-badge">Loading session</p>
      </main>
    );
  }

  if (!auth) {
    return <AuthPage onAuthenticated={handleAuthenticated} />;
  }

  return (
    <AppShell
      activePage={activePage}
      navigation={navigation}
      onNavigate={setActivePage}
      onLogout={handleLogout}
      onRevokeSession={handleRevokeSession}
      sessions={sessions}
      userEmail={auth.user.email}
      workspaceName={auth.workspace.name}
    >
      {renderPage()}
    </AppShell>
  );
}
