# CareerAgent Evaluation Fixtures

This directory stores deterministic, privacy-safe evaluation fixtures.

## Layout

```text
evals/datasets/smoke/   Synthetic smoke inputs by module
evals/datasets/service_level/  De-identified service-level cases
evals/expected/smoke/   Expected contract outputs by module
evals/results/          Local generated run outputs, ignored except .gitkeep
```

## Run

```bash
python scripts/run_evals.py --dataset smoke
python scripts/run_evals.py --dataset synthetic
python scripts/run_evals.py --dataset service_level
python scripts/run_evals.py --dataset smoke --module rag
python scripts/run_evals.py --dataset regression
```

The runner writes `summary.md`, `metrics.json`, `failed_cases.json`, `actual_outputs.json`, and `run_config.json`.

`metrics.json` includes a non-secret `run_config` with prompt/schema/retrieval/model/code/evaluation version metadata. This is for deterministic regression traceability only; it is not model comparison or LLM judging.

`service_level` uses a temporary SQLite database and calls current CareerAgent services. It is a real evaluation foundation, but it still evaluates foundation service behavior and is not a production-quality benchmark.

Phase 2.3 parser cases cover 12 JD parser cases and 8 resume parser cases. Parser metrics include role/category hits, section/skill/project/education hits, risk flag hit rate, evidence coverage, confidence presence, warning expectations, and case pass.

Phase 2.4 match cases cover 9 Match service-level cases, including strong/weak matches, missing project evidence, business context gaps, unsupported metric risk, education fit, and same-JD multi-resume comparison. Match metrics include dimension score presence, evidence dimension coverage, strength/gap keyword hits, expected score range, risk flag hit rate, rewrite priority hit rate, scoring method presence, confidence presence, and case pass.

Phase 2.4 project rewrite cases cover 6 Project Rewrite service-level cases, including missing required skills, unsupported metrics, learning-to-business overclaim, empty original bullets, and no fabricated technologies. Project Rewrite metrics include before/after presence, evidence required presence, forbidden changes presence, risk level presence, matched/missing point hit rates, risk flag hit rate, fabrication guard pass, and case pass.

Phase 2.5 agent workflow cases cover 8 Agent service-level cases, including success, need_more_info, resume, failed-step Bad Case payload, retry, cancel, interview preparation, and study gap planning. Agent metrics include status match, step coverage, missing slot match, resume/retry/cancel success, bad case payload presence, run config presence, privacy-safe payload presence, and case pass.

Phase 2.2 RAG cases cover `lexical`, `vector`, `hybrid`, and no-evidence behavior. RAG metrics include recall/citation/source type plus `retrieval_mode_match`, `average_top_score`, `vector_index_used`, and uncertainty matching.

The current RAG path uses a local bag-of-words vectorizer with DB-persisted chunk vectors. It is a production foundation, not a final semantic embedding benchmark. Run the smoke dataset before enabling any real LLM or external embedding provider, and keep real-provider experiments out of committed `evals/results/` artifacts unless they are sanitized and explicitly reviewed.

The current parser path uses local deterministic parser foundation by default. Optional LLM parser runs must use runtime secrets only and must not commit raw private outputs or provider traces.

The current Match and Project Rewrite paths use deterministic trustworthy foundation logic by default. Do not treat service-level pass rates as production job-search judgment quality or as permission to use rewritten bullets without human confirmation.

The current Agent Workflow path uses deterministic local services and a synchronous runner. Do not treat service-level pass rates as proof of durable production workflow execution or real LLM agent behavior.

Phase 2.6 security/privacy/deployment checks add readiness, redaction and deletion-proof regression coverage, but they do not make evaluation outputs production compliance artifacts. Keep generated eval outputs in ignored `evals/results/` or `/tmp`, and do not commit real provider traces, raw private text, credentials or production logs.

## Boundaries

Smoke fixtures use synthetic refs, summaries, and short signals only. Service-level fixtures may include de-identified JD/resume/RAG text so the current services can run; do not add real names, real employers, real contact details, credentials, private application materials, or committed eval run outputs.
