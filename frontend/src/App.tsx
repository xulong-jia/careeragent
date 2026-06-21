import { useState } from "react";

import { AppShell } from "./components/AppShell";
import { DashboardPage } from "./pages/DashboardPage";
import { JDCenterPage } from "./pages/JDCenterPage";
import { MatchReportPage } from "./pages/MatchReportPage";
import { ResumeCenterPage } from "./pages/ResumeCenterPage";
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

const pages: Record<PageKey, React.ComponentType> = {
  dashboard: DashboardPage,
  resume: ResumeCenterPage,
  jd: JDCenterPage,
  match: MatchReportPage,
};

export default function App() {
  const [activePage, setActivePage] = useState<PageKey>("dashboard");
  const ActivePage = pages[activePage];

  return (
    <AppShell
      activePage={activePage}
      navigation={navigation}
      onNavigate={setActivePage}
    >
      <ActivePage />
    </AppShell>
  );
}
