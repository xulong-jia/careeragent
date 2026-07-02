import * as Sentry from "@sentry/react";
import type { PropsWithChildren } from "react";

function Fallback() {
  return (
    <main className="app-shell" role="alert">
      <section className="page-section">
        <h1>Something went wrong</h1>
        <p>Please refresh and try again.</p>
      </section>
    </main>
  );
}

export function ErrorBoundary({ children }: PropsWithChildren) {
  return (
    <Sentry.ErrorBoundary fallback={<Fallback />}>
      {children}
    </Sentry.ErrorBoundary>
  );
}
