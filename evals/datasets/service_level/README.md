# Service-Level Evaluation Dataset

Phase 2.1/2.2 service-level fixtures are de-identified, self-contained examples. They are written in realistic JD/resume/RAG styles but do not contain real applicants, real employers, real contact details, real job links, or secrets.

The runner calls current CareerAgent services against a temporary SQLite database:

- `jd_parser_cases.json` -> `job_service.create_job`
- `resume_parser_cases.json` -> `resume_service.create_resume`, `parse_resume`, `check_resume_risk`
- `match_cases.json` -> `resume_service`, `job_service`, `match_service.run_match_report`
- `rag_retrieval_cases.json` -> `rag_service.create_document`, `index_document`, `answer_question`
- `agent_workflow_cases.json` -> `agent.runner.run_workflow`

RAG cases cover `lexical`, `vector`, `hybrid`, and no-evidence refusal behavior. Vector/hybrid cases expect persisted chunk vectors from indexing, not query-time chunk re-embedding.

These cases are a real evaluation foundation, not a production-quality benchmark. They intentionally evaluate the current deterministic/mock services as they exist today.
