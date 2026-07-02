import * as Sentry from "@sentry/react";
import type { ErrorEvent } from "@sentry/react";

const REDACTED = "[redacted]";
const EMAIL_PATTERN = /\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b/g;
const PHONE_PATTERN = /(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)/g;
const JWT_PATTERN = /\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b/g;
const SECRET_PATTERN =
  /\b(?:api[_-]?key|token|secret|password)\b\s*[:=]\s*['"]?[^'"\s]+/gi;
const SENSITIVE_KEY_PARTS = [
  "authorization",
  "cookie",
  "localstorage",
  "api_key",
  "apikey",
  "password",
  "secret",
  "token",
  "resume_text",
  "jd_text",
  "jd_raw_text",
  "interview_answer",
  "answer_text",
  "chunk_text",
  "raw_text",
  "full_text",
  "user_text",
];

let initialized = false;

function scrubString(value: string): string {
  return value
    .replace(EMAIL_PATTERN, "[redacted-email]")
    .replace(PHONE_PATTERN, "[redacted-phone]")
    .replace(SECRET_PATTERN, "[redacted-secret]")
    .replace(JWT_PATTERN, "[redacted-token]");
}

function isSensitiveKey(key: string): boolean {
  const normalized = key.toLowerCase().replace(/-/g, "_");
  return SENSITIVE_KEY_PARTS.some((part) => normalized.includes(part));
}

function scrubValue(value: unknown): unknown {
  if (typeof value === "string") {
    return scrubString(value);
  }
  if (Array.isArray(value)) {
    return value.map(scrubValue);
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([key, item]) => [
        key,
        isSensitiveKey(key) ? REDACTED : scrubValue(item),
      ]),
    );
  }
  return value;
}

function scrubRequest(event: ErrorEvent): ErrorEvent {
  const request = (event as { request?: Record<string, unknown> }).request;
  if (!request) {
    return event;
  }
  delete request.data;
  delete request.cookies;
  const headers = request.headers;
  if (headers && typeof headers === "object") {
    for (const key of Object.keys(headers)) {
      if (
        ["authorization", "cookie", "set-cookie"].includes(key.toLowerCase())
      ) {
        (headers as Record<string, unknown>)[key] = REDACTED;
      }
    }
  }
  return event;
}

export function scrubSentryEvent(event: ErrorEvent): ErrorEvent {
  const scrubbed = scrubValue(event) as ErrorEvent;
  delete scrubbed.user;
  return scrubRequest(scrubbed);
}

function parseSampleRate(value: string | undefined): number {
  const parsed = Number(value ?? "0");
  if (!Number.isFinite(parsed)) {
    return 0;
  }
  return Math.min(1, Math.max(0, parsed));
}

function traceTargets(): Array<string | RegExp> {
  const configured = import.meta.env.VITE_SENTRY_TRACE_TARGETS?.trim();
  if (configured) {
    return configured
      .split(",")
      .map((target) => target.trim())
      .filter(Boolean);
  }
  return [window.location.origin, import.meta.env.VITE_API_BASE_URL ?? "/api"];
}

export function initObservability(): boolean {
  const dsn = import.meta.env.VITE_SENTRY_DSN?.trim();
  if (!dsn) {
    return false;
  }
  if (initialized) {
    return true;
  }

  Sentry.init({
    dsn,
    environment: import.meta.env.VITE_SENTRY_ENVIRONMENT || import.meta.env.MODE,
    release: import.meta.env.VITE_SENTRY_RELEASE || undefined,
    tracesSampleRate: parseSampleRate(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE),
    tracePropagationTargets: traceTargets(),
    beforeSend: scrubSentryEvent,
    integrations: [Sentry.browserTracingIntegration()],
  });
  initialized = true;
  return true;
}
