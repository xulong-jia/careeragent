import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";


function read(path) {
  return readFileSync(new URL(`../${path}`, import.meta.url), "utf8");
}


test("Sentry initializes only when a browser DSN is configured", () => {
  const source = read("src/observability.ts");
  assert.match(source, /const dsn = import\.meta\.env\.VITE_SENTRY_DSN\?\.trim\(\)/);
  assert.match(source, /if \(!dsn\) {\s+return false;\s+}/);
  assert.match(source, /Sentry\.init\(/);
});


test("frontend observability scrubs auth, cookie, pii, and raw career text fields", () => {
  const source = read("src/observability.ts");
  for (const field of [
    "authorization",
    "cookie",
    "localstorage",
    "resume_text",
    "jd_text",
    "interview_answer",
    "chunk_text",
    "raw_text",
  ]) {
    assert.match(source, new RegExp(`"${field}"`));
  }
  assert.match(source, /EMAIL_PATTERN/);
  assert.match(source, /PHONE_PATTERN/);
  assert.match(source, /delete scrubbed\.user/);
});


test("Sentry tracing is target-limited and Session Replay is not configured", () => {
  const source = read("src/observability.ts");
  const packageJson = JSON.parse(read("package.json"));
  assert.match(source, /tracePropagationTargets: traceTargets\(\)/);
  assert.doesNotMatch(source, /replayIntegration|Replay/);
  assert.equal(packageJson.dependencies["@sentry/replay"], undefined);
});


test("React app is wrapped in a Sentry error boundary", () => {
  const main = read("src/main.tsx");
  const boundary = read("src/ErrorBoundary.tsx");
  assert.match(main, /<ErrorBoundary>/);
  assert.match(boundary, /Sentry\.ErrorBoundary/);
  assert.match(boundary, /role="alert"/);
});
