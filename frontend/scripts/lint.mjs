import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const root = process.cwd();
const srcRoot = join(root, "src");
const failures = [];

function walk(dir) {
  return readdirSync(dir).flatMap((entry) => {
    const path = join(dir, entry);
    if (entry === "node_modules" || entry === "dist") {
      return [];
    }
    return statSync(path).isDirectory() ? walk(path) : [path];
  });
}

function read(path) {
  return readFileSync(path, "utf8");
}

function fail(message) {
  failures.push(message);
}

const sourceFiles = walk(srcRoot).filter((path) => /\.(ts|tsx)$/.test(path));
const directFetchAllowed = new Set(["src/api/client.ts", "src/observability.ts"]);
const rawBackendUrlAllowed = new Set(["src/api/client.ts", "src/observability.ts"]);

for (const file of sourceFiles) {
  const rel = relative(root, file);
  const text = read(file);
  if (text.includes("fetch(") && !directFetchAllowed.has(rel)) {
    fail(`${rel}: direct fetch is only allowed in src/api/client.ts`);
  }
  if (text.includes("http://localhost") && !rawBackendUrlAllowed.has(rel)) {
    fail(`${rel}: raw backend URL is only allowed in src/api/client.ts`);
  }
}

const pageText = sourceFiles
  .filter((file) => relative(root, file).startsWith("src/pages/"))
  .map(read)
  .join("\n");

for (const label of [
  "JD ID",
  "Resume Version ID",
  "Profile ID",
  "Project ID",
  "Match Report ID",
  "Agent Run ID",
  "Source ID",
  "resume_id 和 jd_id",
]) {
  if (pageText.includes(label)) {
    fail(`frontend pages still expose hand-filled internal ID copy: ${label}`);
  }
}

const selectorText = read(join(root, "src/components/EntitySelectors.tsx"));
for (const exportName of [
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
  if (!selectorText.includes(`export function ${exportName}`)) {
    fail(`missing selector export: ${exportName}`);
  }
}

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log("frontend lint contracts passed");
