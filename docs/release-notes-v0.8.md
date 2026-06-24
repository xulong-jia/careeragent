# CareerAgent v0.8.0 Release Notes

Release theme: `v0.8.0-resume-profile-foundation`

本版本目标是打牢 CareerAgent 的数据入口，让后续 Match、Project Optimization、Interview、Study Plan 和 Agent 能基于可信的 Profile 与 Structured Resume 工作。v0.8 仍是 deterministic MVP / engineering handoff，不是执行手册完整版。

## 1. Resume parser foundation

相关提交：

- `e375e99c43da42f1ed3f5f384b39245d4e5fea7d`：`feat: add resume parsing and risk check APIs`
- `847170b53d453f92ceac39afb93ddd1786143ddf`：`feat: wire resume parsing workflow into frontend`

已完成：

- TXT / Markdown UTF-8 文本读取。
- PDF 文本层提取，使用 PyMuPDF。
- DOCX 文本层提取，使用 python-docx。
- deterministic resume parser。
- deterministic resume risk-check service。
- `resumes.parse_status` migration。
- `resume_versions.risk_report` migration。
- 后端 resume parser / risk / version tests。

边界：

- 不做 OCR。
- 不接真实 LLM parser。
- risk-check 是确定性规则检测，不是事实审计。
- risk-check 不自动修改简历。

## 2. Resume parse / risk / version APIs

新增或增强 API：

- `POST /api/resumes/{resume_id}/parse`
- `POST /api/resumes/{resume_id}/risk-check`
- `POST /api/resumes/{resume_id}/versions`
- 保留 upload / list / detail / version list / version detail / clone / archive。

保存 confirmed version 时，前端提交用户确认后的：

- `version_name`
- `target_role`
- `structured_resume`
- `risk_report`
- `source_version_id`

## 3. ResumeCenter frontend workflow

ResumeCenterPage 已接入：

- 上传 PDF / DOCX / Markdown / txt synthetic resume。
- 查看 raw text preview。
- 运行 Parse。
- 查看 extraction method / warnings。
- 编辑 structured resume JSON。
- JSON parse validation。
- 运行 Risk Check。
- 查看 risk flags 和 risk report。
- 保存 confirmed structured resume version。

隐私边界：

- 前端只展示 raw text preview。
- Dashboard 不展示 raw text。
- error message 不包含完整 raw text。
- 保存版本时只提交必要字段。

## 4. Profile Center MVP

相关提交：

- `7b7ee0bc982933f182c5f40eb63abe05cfef535b`：`feat: add profile center MVP`

已完成：

- `profiles` 表和 migration。
- Profile model / schema / repository / service / API。
- Profile APIs：
  - `POST /api/profiles`
  - `GET /api/profiles`
  - `GET /api/profiles/{profile_id}`
  - `PATCH /api/profiles/{profile_id}`
  - `GET /api/profiles/{profile_id}/summary`
- ProfilePage。
- completeness / readiness summary。
- Dashboard profile readiness。

边界：

- 当前无认证系统，`user_id` 默认 `default`。
- 不做多用户权限隔离。
- 不从简历自动生成 profile。
- Profile 不保存身份证、详细住址、政治、健康等敏感身份信息。

## 5. Dashboard readiness

Dashboard 当前展示：

- latest profile readiness level。
- profile completeness score。
- latest resume parse status。
- resume risk flags count。
- 原有 Resume、JD、Match、RAG、Agent、Application、Bad Case、Evaluation 统计。

## 6. 本版本不做内容

- 不接真实 LLM。
- 不做 OCR。
- 不接 embedding / vector DB。
- 不重写 match scoring。
- 不做 Project Optimization。
- 不做 Interview Center。
- 不做 Study Plan。
- 不做认证系统。
- 不做多用户权限。
- 不做自动投递。
- 不接招聘网站。
- 不做生产部署。

## 7. 测试结果

2026-06-24 在 `main` 执行：

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests
```

结果：165 passed, 6 warnings。

```bash
cd frontend && npm run build
```

结果：通过。

```bash
docker compose config
```

结果：通过。

```bash
python3 -m py_compile scripts/seed_demo_data.py
```

结果：通过。

```bash
git diff --check
```

结果：通过。

```bash
docker compose build
```

结果：未完成。当前机器 Docker daemon/socket 不可用：

```text
failed to connect to the docker API at unix:///Users/jiaxulong/.docker/run/docker.sock
```

该项需要在 Docker daemon 可用环境重新验证。

## 8. 安全与隐私

- 不提交真实简历。
- 不提交 raw `local_data`。
- 不提交 SQLite DB。
- 不提交 API key。
- 不提交 `dist`、`node_modules`、缓存或上传文件。
- PDF / DOCX 解析仅做文本层提取。
- Resume raw text 仍属于本地 prototype 数据，后续生产化需要继续收敛 raw_text 返回、日志和导出策略。
- Profile 只保存求职目标、技能结构、偏好和可选 resume version ref。
- risk-check 不自动修改简历。
