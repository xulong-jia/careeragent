import { clearAuthToken, requestJson, setAuthToken } from "./client";
import type { AuthMe, AuthSession, AuthSessionRecord, ListResponse } from "../types/api";

export type AuthPayload = {
  email: string;
  password: string;
  display_name?: string | null;
};

export async function login(payload: AuthPayload): Promise<AuthSession> {
  const session = await requestJson<AuthSession>("/api/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email: payload.email,
      password: payload.password,
    }),
  });
  setAuthToken(session.access_token);
  return session;
}

export async function register(payload: AuthPayload): Promise<AuthSession> {
  const session = await requestJson<AuthSession>("/api/auth/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  setAuthToken(session.access_token);
  return session;
}

export function getMe(): Promise<AuthMe> {
  return requestJson<AuthMe>("/api/auth/me");
}

export function listSessions(): Promise<ListResponse<AuthSessionRecord>> {
  return requestJson<ListResponse<AuthSessionRecord>>("/api/auth/sessions");
}

export function revokeSession(sessionId: string): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>(`/api/auth/sessions/${sessionId}/revoke`, {
    method: "POST",
  });
}

export async function logout(): Promise<void> {
  try {
    await requestJson<Record<string, unknown>>("/api/auth/logout", {
      method: "POST",
    });
  } finally {
    clearAuthToken();
  }
}
