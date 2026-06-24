# CareerAgent API Reference

所有 API 默认返回统一结构：

```json
{
  "data": {},
  "request_id": "..."
}
```

错误返回：

```json
{
  "error": {
    "code": "error_code",
    "message": "Human readable message.",
    "details": {}
  },
  "request_id": "..."
}
```

## Health / DB

| Method | Path | 说明 |
| --- | --- | --- |
| GET | `/health` | API health check |
| GET | `/api/db/health` | DB reachability、database type、core table check |

## Profile APIs

| Method | Path | 说明 |
| --- | --- | --- |
| POST | `/api/profiles` | 创建用户求职画像 |
| GET | `/api/profiles` | 查询 profile 列表 |
| GET | `/api/profiles/{profile_id}` | 查询 profile detail |
| PATCH | `/api/profiles/{profile_id}` | 更新 profile |
| GET | `/api/profiles/{profile_id}/summary` | 查询 completeness / readiness summary |

关键字段：

- `id`
- `target_roles`
- `target_industries`
- `target_locations`
- `skill_map`
- `preferences`
- `source_resume_version_id`
- `readiness_level`
- `completeness_score`

隐私边界：Profile API 只保存目标、技能结构、偏好和可选 resume version ref，不返回 Resume raw text。

## Resume APIs

| Method | Path | 说明 |
| --- | --- | --- |
| POST | `/api/resumes/upload` | 上传 `.pdf` / `.docx` / `.md` / `.markdown` / `.txt` 并提取文本 |
| POST | `/api/resumes/{resume_id}/parse` | deterministic parse，返回结构化简历候选结果 |
| POST | `/api/resumes/{resume_id}/risk-check` | deterministic risk-check，不修改数据库 |
| POST | `/api/resumes/{resume_id}/versions` | 保存用户确认后的 structured resume version |
| GET | `/api/resumes` | 查询 resume 列表 |
| GET | `/api/resumes/{resume_id}` | 查询 resume detail |
| GET | `/api/resumes/{resume_id}/versions` | 查询 resume versions |

关键字段：

- `resume_id`
- `filename`
- `raw_text_preview`
- `structured_resume`
- `risk_flags`
- `risk_report`

## Resume Version APIs

| Method | Path | 说明 |
| --- | --- | --- |
| GET | `/api/resume-versions/{version_id}` | 查询 version detail |
| POST | `/api/resume-versions/{version_id}/clone` | clone version |
| PATCH | `/api/resume-versions/{version_id}/archive` | soft archive |

关键字段：

- `resume_version_id`
- `version_name`
- `version_number`
- `target_role`
- `status`
- `is_archived`

## JD APIs

| Method | Path | 说明 |
| --- | --- | --- |
| POST | `/api/jobs` | 创建 JD 和 deterministic job profile |
| GET | `/api/jobs` | 查询 JD 列表 |
| GET | `/api/jobs/{jd_id}` | 查询 JD detail |

关键字段：

- `jd_id`
- `company`
- `job_title`
- `job_profile.required_skills`
- `job_profile.role_category`

## Match APIs

| Method | Path | 说明 |
| --- | --- | --- |
| POST | `/api/matches/run` | 针对 resume version 和 JD 运行 deterministic match |
| GET | `/api/matches` | 查询 match reports |
| GET | `/api/matches?jd_id={jd_id}` | 按 JD 筛选 |
| GET | `/api/matches?resume_version_id={resume_version_id}` | 按 resume version 筛选 |
| GET | `/api/matches/{match_report_id}` | 查询 match detail |

关键字段：

- `match_report_id`
- `total_score`
- `dimension_scores`
- `strengths`
- `gaps`
- `evidence`

## RAG APIs

| Method | Path | 说明 |
| --- | --- | --- |
| POST | `/api/rag/documents` | 创建 RAG document |
| GET | `/api/rag/documents` | 查询 documents |
| GET | `/api/rag/documents/{doc_id}` | 查询 document detail |
| POST | `/api/rag/documents/{doc_id}/index` | deterministic chunk/index |
| GET | `/api/rag/chunks` | 查询 chunks，可按 `doc_id` 筛选 |
| POST | `/api/rag/search` | lexical search |
| POST | `/api/rag/answer` | deterministic answer with citations |

关键字段：

- `doc_id`
- `raw_text_preview`
- `chunk_count`
- `sources`
- `snippet`
- `uncertainty`

## Agent APIs

| Method | Path | 说明 |
| --- | --- | --- |
| POST | `/api/agents/runs` | 创建 deterministic workflow run |
| GET | `/api/agents/runs` | 查询 runs，可按 workflow/status 筛选 |
| GET | `/api/agents/runs/{run_id}` | 查询 run detail |
| GET | `/api/agents/runs/{run_id}/steps` | 查询 step timeline |

当前 workflow：

- `job_application_preparation`

关键字段：

- `run.id`
- `status`
- `input_refs`
- `output_refs`
- `missing_slots`
- `steps`

## Application APIs

| Method | Path | 说明 |
| --- | --- | --- |
| POST | `/api/applications` | 创建手动投递 tracking record |
| GET | `/api/applications` | 查询投递列表 |
| GET | `/api/applications?status={status}` | 按 status 筛选 |
| GET | `/api/applications?company={company}` | 按 company 筛选 |
| GET | `/api/applications?role_category={role_category}` | 按 role category 筛选 |
| GET | `/api/applications?resume_version_id={resume_version_id}` | 按 resume version 筛选 |
| GET | `/api/applications?jd_id={jd_id}` | 按 JD 筛选 |
| GET | `/api/applications/{application_id}` | 查询 detail |
| PATCH | `/api/applications/{application_id}` | 更新状态或摘要字段 |
| GET | `/api/applications/stats` | 查询投递统计 |

关键字段：

- `application_id`
- `company`
- `role_title`
- `status`
- `jd_id`
- `resume_version_id`
- `match_report_id`
- `interview_notes`
- `reflection`

## Bad Case APIs

| Method | Path | 说明 |
| --- | --- | --- |
| POST | `/api/evaluations/bad-cases` | 创建人工 bad case |
| GET | `/api/evaluations/bad-cases` | 查询 bad cases |
| GET | `/api/evaluations/bad-cases/{bad_case_id}` | 查询 detail |
| PATCH | `/api/evaluations/bad-cases/{bad_case_id}` | 更新 status/severity/摘要字段 |

关键字段：

- `source_type`
- `source_id`
- `category`
- `severity`
- `status`
- `description`

## Evaluation APIs

| Method | Path | 说明 |
| --- | --- | --- |
| POST | `/api/evaluations/runs` | 创建并执行 deterministic evaluation run |
| GET | `/api/evaluations/runs` | 查询 runs |
| GET | `/api/evaluations/runs/{run_id}` | 查询 run summary |
| GET | `/api/evaluations/runs/{run_id}/results` | 查询 run results |
| GET | `/api/evaluations/cases` | 查询 evaluation cases |
| POST | `/api/evaluations/cases` | 创建 manual evaluation case |
| POST | `/api/evaluations/cases/from-bad-case/{case_id}` | 从 Bad Case 创建 evaluation case |
| GET | `/api/evaluations/stats` | 查询 evaluation stats |

关键字段：

- `evaluation_runs.metrics.pass_rate`
- `evaluation_cases.bad_case_id`
- `evaluation_results.passed`
- `evaluation_results.score`

当前只支持 deterministic smoke / regression tracking，不做 LLM judge。
