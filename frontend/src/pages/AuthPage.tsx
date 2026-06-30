import { useState } from "react";
import type { FormEvent } from "react";

import { login, register } from "../api/auth";
import type { AuthSession } from "../types/api";

type AuthPageProps = {
  onAuthenticated: (session: AuthSession) => void;
};

export function AuthPage({ onAuthenticated }: AuthPageProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      const payload = {
        email,
        password,
        display_name: displayName || null,
      };
      const session =
        mode === "login" ? await login(payload) : await register(payload);
      onAuthenticated(session);
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Authentication failed.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="auth-screen">
      <section className="auth-panel" aria-labelledby="auth-title">
        <div className="brand-block">
          <span className="brand-mark" aria-hidden="true">
            CA
          </span>
          <div>
            <p className="brand-name">CareerAgent</p>
            <p className="brand-subtitle">P1 foundation checkpoint</p>
          </div>
        </div>

        <div className="auth-tabs" role="tablist" aria-label="Authentication mode">
          <button
            className={mode === "login" ? "auth-tab active" : "auth-tab"}
            onClick={() => setMode("login")}
            type="button"
          >
            Login
          </button>
          <button
            className={mode === "register" ? "auth-tab active" : "auth-tab"}
            onClick={() => setMode("register")}
            type="button"
          >
            Register
          </button>
        </div>

        <form className="form-stack" onSubmit={handleSubmit}>
          <h1 id="auth-title">{mode === "login" ? "Sign in" : "Create account"}</h1>
          <label>
            Email
            <input
              autoComplete="email"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </label>
          {mode === "register" ? (
            <label>
              Display name
              <input
                autoComplete="name"
                onChange={(event) => setDisplayName(event.target.value)}
                type="text"
                value={displayName}
              />
            </label>
          ) : null}
          <label>
            Password
            <input
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              minLength={mode === "register" ? 8 : 1}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>
          {error ? <p className="error-text">{error}</p> : null}
          <button className="primary-action" disabled={isSubmitting} type="submit">
            {isSubmitting ? "Working..." : mode === "login" ? "Login" : "Register"}
          </button>
        </form>
      </section>
    </main>
  );
}
