import {
  createProject,
  getProject,
  getProjectRewrite,
  listProjects,
  runProjectRewrite,
  updateProject,
} from "./api/projects";
import { ProjectOptimizationPage } from "./pages/ProjectOptimizationPage";
import type {
  ListResponse,
  ProjectCreateRequest,
  ProjectRecord,
  ProjectRewriteRecord,
  ProjectRewriteRequest,
  ProjectUpdateRequest,
} from "./types/api";
import type { PageKey } from "./types/navigation";

const pageKey: PageKey = "project-optimization";
const createPayload: ProjectCreateRequest = {
  name: "Synthetic project",
  role: "Backend Engineer",
  period: "2026",
  background: "Local project facts only.",
  tech_stack: ["Python"],
  responsibilities: ["Built deterministic APIs."],
  results: ["Created local smoke checks."],
  evidence: [{ type: "test", description: "Synthetic checks" }],
  status: "active",
};
const updatePayload: ProjectUpdateRequest = {
  status: "archived",
};
const rewritePayload: ProjectRewriteRequest = {
  jd_id: "jd_0001",
};

void pageKey;
void createPayload;
void updatePayload;
void rewritePayload;
void ProjectOptimizationPage;

const projectPromise: Promise<ProjectRecord> = createProject(createPayload);
const listPromise: Promise<ListResponse<ProjectRecord>> = listProjects();
const detailPromise: Promise<ProjectRecord> = getProject("project_1");
const updatePromise: Promise<ProjectRecord> = updateProject(
  "project_1",
  updatePayload,
);
const rewritePromise: Promise<ProjectRewriteRecord> = runProjectRewrite(
  "project_1",
  rewritePayload,
);
const rewriteDetailPromise: Promise<ProjectRewriteRecord> =
  getProjectRewrite("project_rewrite_1");

void projectPromise;
void listPromise;
void detailPromise;
void updatePromise;
void rewritePromise;
void rewriteDetailPromise;
