import type { NavigationItem, PageKey } from "../types/navigation";
import type { AuthSessionRecord } from "../types/api";

type AppShellProps = {
  activePage: PageKey;
  navigation: NavigationItem[];
  userEmail: string;
  workspaceName: string;
  sessions: AuthSessionRecord[];
  onNavigate: (page: PageKey) => void;
  onLogout: () => void;
  onRevokeSession: (sessionId: string) => void;
  children: React.ReactNode;
};

export function AppShell({
  activePage,
  navigation,
  sessions,
  userEmail,
  workspaceName,
  onNavigate,
  onLogout,
  onRevokeSession,
  children,
}: AppShellProps) {
  const activeSessions = sessions.filter((session) => !session.revoked_at);
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
            <p className="eyebrow">P1 Production Foundation in progress</p>
            <h1>Career Operating System</h1>
          </div>
          <div className="header-actions">
            <div className="stage-badge">
              {workspaceName} · {userEmail}
            </div>
            <details className="session-menu">
              <summary>Sessions ({activeSessions.length})</summary>
              <div className="session-menu-panel">
                {sessions.length ? (
                  sessions.map((session) => (
                    <div className="session-row" key={session.session_id}>
                      <span>
                        {session.device_label}
                        {session.current ? " · current" : ""}
                      </span>
                      <small>
                        {session.revoked_at
                          ? `revoked: ${session.revoke_reason ?? "manual"}`
                          : `expires ${new Date(session.expires_at).toLocaleString()}`}
                      </small>
                      {!session.revoked_at ? (
                        <button
                          className="tiny-action"
                          onClick={() => onRevokeSession(session.session_id)}
                          type="button"
                        >
                          Revoke
                        </button>
                      ) : null}
                    </div>
                  ))
                ) : (
                  <p className="muted-text">No active session metadata.</p>
                )}
              </div>
            </details>
            <button className="ghost-action" onClick={onLogout} type="button">
              Logout
            </button>
          </div>
        </header>

        {children}
      </main>
    </div>
  );
}
