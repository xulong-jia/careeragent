import { requestJson } from "./client";
import type {
  ListResponse,
  ProfileCreatePayload,
  ProfileRecord,
  ProfileSummary,
  ProfileUpdatePayload,
} from "../types/api";

export function createProfile(
  payload: ProfileCreatePayload,
): Promise<ProfileRecord> {
  return requestJson<ProfileRecord>("/api/profiles", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function listProfiles(): Promise<ListResponse<ProfileRecord>> {
  return requestJson<ListResponse<ProfileRecord>>("/api/profiles");
}

export function getProfile(profileId: string): Promise<ProfileRecord> {
  return requestJson<ProfileRecord>(`/api/profiles/${profileId}`);
}

export function updateProfile(
  profileId: string,
  payload: ProfileUpdatePayload,
): Promise<ProfileRecord> {
  return requestJson<ProfileRecord>(`/api/profiles/${profileId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function getProfileSummary(profileId: string): Promise<ProfileSummary> {
  return requestJson<ProfileSummary>(`/api/profiles/${profileId}/summary`);
}
