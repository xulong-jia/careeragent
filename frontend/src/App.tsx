import { useState } from "react";

import { AppShell } from "./components/AppShell";
import { DashboardPage } from "./pages/DashboardPage";
import { JDCenterPage } from "./pages/JDCenterPage";
import { MatchReportPage } from "./pages/MatchReportPage";
import { ResumeCenterPage } from "./pages/ResumeCenterPage";
import type { JobRecord, MatchReport, ResumeRecord } from "./types/api";
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
];

export default function App() {
  const [activePage, setActivePage] = useState<PageKey>("dashboard");
  const [latestResume, setLatestResume] = useState<ResumeRecord | null>(null);
  const [latestJob, setLatestJob] = useState<JobRecord | null>(null);
  const [latestMatch, setLatestMatch] = useState<MatchReport | null>(null);

  const workbenchState = {
    latestResume,
    latestJob,
    latestMatch,
  };

  const renderPage = () => {
    if (activePage === "resume") {
      return (
        <ResumeCenterPage
          latestResume={latestResume}
          onResumeUploaded={setLatestResume}
        />
      );
    }
    if (activePage === "jd") {
      return <JDCenterPage latestJob={latestJob} onJobCreated={setLatestJob} />;
    }
    if (activePage === "match") {
      return (
        <MatchReportPage
          latestJob={latestJob}
          latestMatch={latestMatch}
          latestResume={latestResume}
          onMatchRun={setLatestMatch}
        />
      );
    }
    return <DashboardPage state={workbenchState} onNavigate={setActivePage} />;
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
