import assert from "node:assert/strict";
import { test } from "node:test";

const resume = {
  filename: "candidate-redacted.pdf",
  resume_id: "resume_0001",
  raw_text: "Private phone 0400 000 000 and full resume body",
  version: {
    resume_version_id: "resume_0001_version_0001",
    version_name: "Backend target",
  },
};
const jd = {
  jd_id: "jd_0001",
  company: "Synthetic Company",
  job_title: "AI Application Engineer",
  raw_text: "Private JD body",
};
const match = {
  match_report_id: "match_0001",
  resume_version_id: resume.version.resume_version_id,
  jd_id: jd.jd_id,
  total_score: 82,
  gaps: ["React depth"],
  strengths: ["FastAPI"],
};

function selectorLabel(entity) {
  if ("filename" in entity) {
    return entity.filename;
  }
  if ("company" in entity) {
    return `${entity.company} / ${entity.job_title}`;
  }
  return `score ${entity.total_score}`;
}

function visibleCard(entity) {
  const text = JSON.stringify(entity);
  return text
    .replaceAll(resume.raw_text, "[hidden]")
    .replaceAll(jd.raw_text, "[hidden]")
    .replaceAll("0400 000 000", "[hidden]");
}

test("resume, JD and match workflow uses selectors instead of hand-filled IDs", () => {
  assert.equal(selectorLabel(resume), "candidate-redacted.pdf");
  assert.equal(selectorLabel(jd), "Synthetic Company / AI Application Engineer");
  const runPayload = {
    jd_id: jd.jd_id,
    resume_version_id: resume.version.resume_version_id,
  };
  assert.deepEqual(runPayload, {
    jd_id: "jd_0001",
    resume_version_id: "resume_0001_version_0001",
  });
  assert.equal(visibleCard(match).includes(resume.raw_text), false);
});

test("match compare ranks versions without exposing raw resume or JD text", () => {
  const compare = [
    { rank: 1, total_score: 88, resume_version_id: "resume_0001_version_0002" },
    { rank: 2, total_score: 82, resume_version_id: "resume_0001_version_0001" },
  ];
  assert.deepEqual(compare.map((item) => item.rank), [1, 2]);
  assert.equal(visibleCard(compare).includes("Private"), false);
});

test("agent need_more_info and resume payload stay ref-based", () => {
  const payload = {
    workflow_name: "job_application_preparation",
    resume_version_id: resume.version.resume_version_id,
    jd_id: jd.jd_id,
    raw_text: resume.raw_text,
  };
  const privacySafePayload = visibleCard(payload);
  assert.equal(privacySafePayload.includes(resume.raw_text), false);
  assert.match(privacySafePayload, /resume_0001_version_0001/);
  assert.match(privacySafePayload, /jd_0001/);
});

test("application board summarizes linked refs", () => {
  const application = {
    company: jd.company,
    role_title: jd.job_title,
    status: "ready_to_apply",
    priority: "high",
    jd_id: jd.jd_id,
    resume_version_id: resume.version.resume_version_id,
    match_report_id: match.match_report_id,
    agent_run_id: "agent_run_0001",
  };
  const refs = ["JD", "Resume", "Match", "Agent"].filter((label) =>
    application[`${label.toLowerCase()}_id`] || label === "Resume",
  );
  assert.equal(refs.includes("Resume"), true);
  assert.equal(visibleCard(application).includes("Private"), false);
});

test("knowledge answer shows citations and hides raw source text", () => {
  const answer = {
    answer: "Use FastAPI projects as evidence.",
    citations: [{ label: "Synthetic note", snippet: "FastAPI projects..." }],
    source_raw_text: "Private chunk text that must not render",
  };
  const display = visibleCard({
    answer: answer.answer,
    citations: answer.citations,
  });
  assert.match(display, /Synthetic note/);
  assert.equal(display.includes(answer.source_raw_text), false);
});
