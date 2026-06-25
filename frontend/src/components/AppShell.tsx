import type { NavigationItem, PageKey } from "../types/navigation";

type AppShellProps = {
  activePage: PageKey;
  navigation: NavigationItem[];
  onNavigate: (page: PageKey) => void;
  children: React.ReactNode;
};

export function AppShell({
  activePage,
  navigation,
  onNavigate,
  children,
}: AppShellProps) {
  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="主导航">
        <div className="brand-block">
          <span className="brand-mark" aria-hidden="true">
            CA
          </span>
          <div>
            <p className="brand-name">CareerAgent</p>
            <p className="brand-subtitle">校招求职工作台</p>
          </div>
        </div>

        <nav className="nav-list">
          {navigation.map((item) => (
            <button
              className={item.key === activePage ? "nav-item active" : "nav-item"}
              key={item.key}
              onClick={() => onNavigate(item.key)}
              type="button"
            >
              <span>{item.label}</span>
              <small>{item.description}</small>
            </button>
          ))}
        </nav>
      </aside>

      <main className="workspace">
        <header className="workspace-header">
          <div>
            <p className="eyebrow">v0.9 Project Optimization</p>
            <h1>Career Operating System</h1>
          </div>
          <div className="stage-badge">CareerAgent Workbench</div>
        </header>

        {children}
      </main>
    </div>
  );
}
