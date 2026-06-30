import type { ApiErrorResponse, ApiResponse } from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const AUTH_TOKEN_KEY = "careeragent.auth_token";

export class ApiRequestError extends Error {
  status: number;
  code: string;

  constructor(message: string, status: number, code: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export function getAuthToken(): string | null {
  return window.localStorage.getItem(AUTH_TOKEN_KEY);
}

export function setAuthToken(token: string): void {
  window.localStorage.setItem(AUTH_TOKEN_KEY, token);
}

export function clearAuthToken(): void {
  window.localStorage.removeItem(AUTH_TOKEN_KEY);
}

export async function requestJson<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  const token = getAuthToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });
  const payload = (await response.json()) as ApiResponse<T> | ApiErrorResponse;

  if (!response.ok || "error" in payload) {
    const message =
      "error" in payload ? payload.error.message : "Request failed.";
    const code = "error" in payload ? payload.error.code : "request_failed";
    if (response.status === 401) {
      clearAuthToken();
      window.dispatchEvent(new Event("careeragent:auth-expired"));
    }
    throw new ApiRequestError(message, response.status, code);
  }

  return payload.data;
}
