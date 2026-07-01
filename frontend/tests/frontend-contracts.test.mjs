import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

function read(path) {
  return readFileSync(new URL(`../${path}`, import.meta.url), "utf8");
}

test("v3.3 object selectors are centralized and exported", () => {
  const selectors = read("src/components/EntitySelectors.tsx");
  for (const name of [
    "ResumeSelector",
    "AllResumeVersionSelector",
    "JDSelector",
    "MatchReportSelector",
    "ProjectSelector",
    "ApplicationSelector",
    "AgentRunSelector",
    "KnowledgeDocumentSelector",
    "RagAnswerRunSelector",
    "InterviewAnswerSelector",
    "AgentWorkflowSelector",
  ]) {
    assert.match(selectors, new RegExp(`export function ${name}\\b`));
  }
  assert.match(selectors, /listResumes/);
  assert.match(selectors, /listJobs/);
  assert.match(selectors, /listMatches/);
  assert.match(selectors, /listAgentRuns/);
});

test("main workflow pages no longer ask users to hand-fill internal IDs", () => {
  const pages = [
    "src/pages/MatchReportPage.tsx",
    "src/pages/ProjectOptimizationPage.tsx",
    "src/pages/InterviewCenterPage.tsx",
    "src/pages/StudyPlanPage.tsx",
    "src/pages/ApplicationTrackerPage.tsx",
    "src/pages/AgentRunsPage.tsx",
    "src/pages/QualityReviewPage.tsx",
  ];
  const combined = pages.map(read).join("\n");
  for (const forbidden of [
    "JD ID",
    "Resume Version ID",
    "Profile ID",
    "Project ID",
    "Match Report ID",
    "Agent Run ID",
    "Source ID",
  ]) {
    assert.equal(combined.includes(forbidden), false, forbidden);
  }
});

test("match page runs by resume version and exposes compare workflow", () => {
  const page = read("src/pages/MatchReportPage.tsx");
  assert.match(page, /ResumeVersionSelector/);
  assert.match(page, /runMatch\(\{\s*jdId: selectedJdId/s);
  assert.match(page, /resumeVersionId: selectedResumeVersionId/);
  assert.match(page, /compareMatches/);
});

test("privacy-sensitive displays stay preview-first", () => {
  const agentPage = read("src/pages/AgentRunsPage.tsx");
  const knowledgePage = read("src/pages/KnowledgeBasePage.tsx");
  assert.match(agentPage, /sanitizeForDisplay/);
  assert.match(agentPage, /privacy_safe_payload/);
  assert.match(knowledgePage, /raw_text_preview/);
  assert.match(knowledgePage, /text_preview/);
  assert.match(knowledgePage, /answer_mode/);
  assert.match(knowledgePage, /retrieval_mode/);
});
