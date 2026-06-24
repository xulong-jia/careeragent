import { useEffect, useState } from "react";

import {
  createProfile,
  getProfile,
  getProfileSummary,
  listProfiles,
  updateProfile,
} from "../api/profiles";
import type {
  ProfileCreatePayload,
  ProfileRecord,
  ProfileSummary,
} from "../types/api";

type ProfilePageProps = {
  profiles: ProfileRecord[];
  latestProfileSummary: ProfileSummary | null;
  onProfilesChanged: (profiles: ProfileRecord[]) => void;
  onProfileSummaryChanged: (summary: ProfileSummary | null) => void;
};

const emptySkillMap = {
  programming: [],
  backend: [],
  ai: [],
  frontend: [],
  database: [],
};

const emptyPreferences = {
  preferred_company_type: [],
  language: [],
};

export function ProfilePage({
  profiles,
  latestProfileSummary,
  onProfilesChanged,
  onProfileSummaryChanged,
}: ProfilePageProps) {
  const [selectedProfile, setSelectedProfile] = useState<ProfileRecord | null>(null);
  const [selectedSummary, setSelectedSummary] = useState<ProfileSummary | null>(
    latestProfileSummary,
  );
  const [targetRoles, setTargetRoles] = useState("");
  const [targetIndustries, setTargetIndustries] = useState("");
  const [targetLocations, setTargetLocations] = useState("");
  const [skillMapJson, setSkillMapJson] = useState(formatJson(emptySkillMap));
  const [preferencesJson, setPreferencesJson] = useState(formatJson(emptyPreferences));
  const [sourceResumeVersionId, setSourceResumeVersionId] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  async function refreshProfiles(nextSelectedId?: string) {
    const response = await listProfiles();
    onProfilesChanged(response.items);
    const selectedId =
      nextSelectedId ??
      selectedProfile?.id ??
      response.items[response.items.length - 1]?.id;
    if (selectedId) {
      await handleSelectProfile(selectedId);
      return;
    }
    setSelectedProfile(null);
    setSelectedSummary(null);
    onProfileSummaryChanged(null);
  }

  async function handleSelectProfile(profileId: string) {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [profile, summary] = await Promise.all([
        getProfile(profileId),
        getProfileSummary(profileId),
      ]);
      setSelectedProfile(profile);
      setSelectedSummary(summary);
      onProfileSummaryChanged(summary);
      hydrateForm(profile);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "加载 Profile 失败。",
      );
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    if (!selectedProfile && profiles.length) {
      void handleSelectProfile(profiles[profiles.length - 1].id);
    }
  }, [profiles, selectedProfile]);

  const hydrateForm = (profile: ProfileRecord) => {
    setTargetRoles(profile.target_roles.join(", "));
    setTargetIndustries(profile.target_industries.join(", "));
    setTargetLocations(profile.target_locations.join(", "));
    setSkillMapJson(formatJson(profile.skill_map));
    setPreferencesJson(formatJson(profile.preferences));
    setSourceResumeVersionId(profile.source_resume_version_id ?? "");
  };

  const buildPayload = (): ProfileCreatePayload | null => {
    try {
      return {
        target_roles: parseCommaList(targetRoles),
        target_industries: parseCommaList(targetIndustries),
        target_locations: parseCommaList(targetLocations),
        skill_map: parseJsonObject(skillMapJson, "skill_map"),
        preferences: parseJsonObject(preferencesJson, "preferences"),
        source_resume_version_id: sourceResumeVersionId.trim() || null,
      };
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Profile 表单无效。");
      return null;
    }
  };

  const handleCreateProfile = async () => {
    const payload = buildPayload();
    if (!payload) {
      return;
    }
    setIsSaving(true);
    setErrorMessage(null);
    setActionMessage(null);
    try {
      const created = await createProfile(payload);
      await refreshProfiles(created.id);
      setActionMessage("Profile created.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "创建 Profile 失败。");
    } finally {
      setIsSaving(false);
    }
  };

  const handleUpdateProfile = async () => {
    if (!selectedProfile) {
      setErrorMessage("请先选择一个 Profile。");
      return;
    }
    const payload = buildPayload();
    if (!payload) {
      return;
    }
    setIsSaving(true);
    setErrorMessage(null);
    setActionMessage(null);
    try {
      const updated = await updateProfile(selectedProfile.id, payload);
      await refreshProfiles(updated.id);
      setActionMessage("Profile updated.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "更新 Profile 失败。");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <section className="page-stack" aria-labelledby="profile-title">
      <div className="page-heading">
        <p className="eyebrow">Profile</p>
        <h2 id="profile-title">Profile Center</h2>
        <p>维护目标岗位、地点、行业、技能结构和偏好。当前不接认证、不自动从简历生成画像。</p>
      </div>

      <div className="two-column wide-left">
        <article className="panel">
          <div className="panel-header">
            <h3>Profile 表单</h3>
            <span className="status-pill muted">POST / PATCH /api/profiles</span>
          </div>
          <div className="form-stack">
            <label>
              Target roles
              <input
                onChange={(event) => setTargetRoles(event.target.value)}
                placeholder="LLM Application Engineer, Backend Engineer"
                value={targetRoles}
              />
            </label>
            <label>
              Target industries
              <input
                onChange={(event) => setTargetIndustries(event.target.value)}
                placeholder="Internet, Enterprise Software"
                value={targetIndustries}
              />
            </label>
            <label>
              Target locations
              <input
                onChange={(event) => setTargetLocations(event.target.value)}
                placeholder="Shanghai, Sydney"
                value={targetLocations}
              />
            </label>
            <label>
              Skill map JSON
              <textarea
                className="metadata-textarea"
                onChange={(event) => setSkillMapJson(event.target.value)}
                value={skillMapJson}
              />
            </label>
            <label>
              Preferences JSON
              <textarea
                className="metadata-textarea"
                onChange={(event) => setPreferencesJson(event.target.value)}
                value={preferencesJson}
              />
            </label>
            <label>
              Source resume version id
              <input
                onChange={(event) => setSourceResumeVersionId(event.target.value)}
                placeholder="Optional"
                value={sourceResumeVersionId}
              />
            </label>
            <div className="inline-form">
              <button
                className="primary-action"
                disabled={isSaving}
                onClick={() => void handleCreateProfile()}
                type="button"
              >
                Create profile
              </button>
              <button
                className="ghost-action"
                disabled={!selectedProfile || isSaving}
                onClick={() => void handleUpdateProfile()}
                type="button"
              >
                Update selected
              </button>
            </div>
            {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
            {actionMessage ? <p className="hint-text">{actionMessage}</p> : null}
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Readiness</h3>
            <span className="status-pill">
              {selectedSummary?.readiness_level ?? "None"}
            </span>
          </div>
          {selectedSummary ? (
            <ul className="activity-list">
              <li>
                <strong>Completeness</strong>
                <span>{selectedSummary.completeness_score}%</span>
              </li>
              <li>
                <strong>Target roles</strong>
                <span>{selectedSummary.target_roles_count}</span>
              </li>
              <li>
                <strong>Locations</strong>
                <span>{selectedSummary.target_locations_count}</span>
              </li>
              <li>
                <strong>Skill categories</strong>
                <span>{selectedSummary.skill_categories_count}</span>
              </li>
              <li>
                <strong>Missing fields</strong>
                <span>
                  {selectedSummary.missing_fields.length
                    ? selectedSummary.missing_fields.join(", ")
                    : "None"}
                </span>
              </li>
            </ul>
          ) : (
            <div className="empty-state">
              <strong>暂无 readiness</strong>
              <span>创建或选择 Profile 后会显示 summary。</span>
            </div>
          )}
        </article>
      </div>

      <div className="two-column">
        <article className="panel">
          <div className="panel-header">
            <h3>Profile 列表</h3>
            <span className="status-pill">{profiles.length} items</span>
          </div>
          {isLoading ? <p className="hint-text">Loading profile...</p> : null}
          {profiles.length ? (
            <ul className="activity-list">
              {profiles.map((profile) => (
                <li
                  className={
                    selectedProfile?.id === profile.id ? "selected-row" : undefined
                  }
                  key={profile.id}
                >
                  <div>
                    <strong>{profile.target_roles.join(", ") || "No target roles"}</strong>
                    <small>{profile.id}</small>
                  </div>
                  <span>{profile.target_locations.join(", ") || "No locations"}</span>
                  <button
                    className="ghost-action"
                    disabled={isLoading}
                    onClick={() => void handleSelectProfile(profile.id)}
                    type="button"
                  >
                    Detail
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <div className="empty-state">
              <strong>暂无 Profile</strong>
              <span>创建后会保存到 SQLite-backed Profile API。</span>
            </div>
          )}
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Profile Detail</h3>
            <span className="status-pill muted">{selectedProfile?.id ?? "None"}</span>
          </div>
          {selectedProfile ? (
            <>
              <ul className="activity-list">
                <li>
                  <strong>User</strong>
                  <span>{selectedProfile.user_id}</span>
                </li>
                <li>
                  <strong>Source version</strong>
                  <span>{selectedProfile.source_resume_version_id ?? "None"}</span>
                </li>
                <li>
                  <strong>Updated</strong>
                  <span>{new Date(selectedProfile.updated_at).toLocaleString()}</span>
                </li>
              </ul>
              <pre className="json-preview">
                {JSON.stringify(selectedProfile, null, 2)}
              </pre>
            </>
          ) : (
            <div className="empty-state">
              <strong>未选择 Profile</strong>
              <span>点击列表中的 Detail 查看结构化画像。</span>
            </div>
          )}
        </article>
      </div>
    </section>
  );
}

function parseCommaList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseJsonObject(value: string, fieldName: string): Record<string, unknown> {
  const trimmed = value.trim();
  if (!trimmed) {
    return {};
  }
  const parsed = JSON.parse(trimmed) as unknown;
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(`${fieldName} must be a JSON object.`);
  }
  return parsed as Record<string, unknown>;
}

function formatJson(value: Record<string, unknown>): string {
  return JSON.stringify(value, null, 2);
}
