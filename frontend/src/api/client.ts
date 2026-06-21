import type { ApiErrorResponse, ApiResponse } from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function requestJson<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  const payload = (await response.json()) as ApiResponse<T> | ApiErrorResponse;

  if (!response.ok || "error" in payload) {
    const message =
      "error" in payload ? payload.error.message : "Request failed.";
    throw new Error(message);
  }

  return payload.data;
}
