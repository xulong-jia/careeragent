# Benchmark Foundation Dataset

This directory contains v3.2 synthetic benchmark foundation fixtures.

The 100 benchmark cases cover:

- 30 JD parser cases
- 20 resume parser cases
- 20 RAG retrieval cases
- 10 RAG grounded answer cases
- 10 match calibration cases
- 5 project rewrite guard cases
- 5 agent workflow cases

`human_review_sample.jsonl` adds synthetic reviewer labels for calibration and
human-agreement metrics. The benchmark does not include real resumes, real JDs,
private application materials, provider traces, API keys, or production logs.

These fixtures are a large-sample evaluation foundation only. They do not certify
production AI quality without real anonymized datasets, provider runs, reviewer
protocols, and regression trend review.
