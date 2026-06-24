# CareerAgent Final Acceptance Report

本报告记录 v0.9.0 `project-optimization` final handoff 后的当前项目状态。结论基于当前仓库真实代码、测试和文档，不代表生产就绪系统。

## 1. 验收结论

v0.9.0 `project-optimization` 已完成 deterministic Project Optimization MVP，并与 v0.8 的 Resume/Profile Foundation 集成到同一个本地工作台中。

已完成范围：

- 9A Project facts backend：新增 `projects` 表、Project model / schema / repository / service / API，支持 create / list / detail / patch，可按 `profile_id`、`resume_version_id`、`status` 筛选。
- 9B Project rewrite backend：新增 `project_rewrites` 表、Project Rewrite schema / service / API，支持 `POST /api/projects/{project_id}/rewrite` 和 `GET /api/project-rewrites/{rewrite_id}`。
- 9B deterministic rewrite：生成 `matched_points`、`missing_points`、`evidence_required`、`rewritten_bullets`、`forbidden_changes`、`risk_flags` 和 `rewrite_strategy`。
- 9C ProjectOptimizationPage：前端接入 Project CRUD 和 Project Rewrite API，支持创建 / 更新 project facts、选择 project、输入 JD ID、运行 rewrite、展示结果。
- 9D Dashboard / docs / tests 收口：Dashboard 展示 project count、active project count、latest project name/status；README、API、DB schema、架构和 demo flow 已更新。
- 9E final handoff：补齐 v0.9 final acceptance、release notes、安全边界和后续不做范围。

## 2. 当前模块状态

| 模块 | 当前状态 |
| --- | --- |
| Resume Center | 已完成 v0.8 foundation MVP：文本层提取、deterministic parser、risk-check、confirmed version 保存和前端 workflow |
| Profile Center | 已完成 v0.8 MVP：profiles 表、Profile API、ProfilePage、summary/completeness 和 Dashboard readiness |
| Project Optimization | 已完成 v0.9 deterministic MVP：projects / project_rewrites、Project CRUD、rewrite API、ProjectOptimizationPage 和 Dashboard project summary |
| JD Center | 已完成 deterministic MVP |
| Match Report | 已完成 deterministic MVP |
| RAG Knowledge Base | 已完成 lexical deterministic prototype |
| Agent Runs | 已完成 deterministic state machine prototype |
| Application Tracking | 已完成手动 tracking MVP |
| Quality Review / Bad Case | 已完成人工复盘 MVP |
| Evaluation | 已完成 deterministic smoke evaluation MVP |
| Docker / Compose | 已完成本地开发配置；build 需在 Docker daemon 可用环境验证 |
| Docs / Demo | 已完成 v0.9 handoff 文档、demo script 和 release notes |

## 3. v0.9 Project Optimization 能力

Project Facts：

- `projects` 表保存用户手动确认的项目事实。
- Project API 支持 create / list / detail / patch。
- `profile_id` / `resume_version_id` 是可选关联；传入时后端会校验对象存在。
- `status` 支持 `active` / `archived`，列表支持状态筛选。
- 已有 Project API 和 DB infrastructure 测试。

Project Rewrite：

- `project_rewrites` 表保存 rewrite 结果。
- `POST /api/projects/{project_id}/rewrite` 针对 JD profile 运行 deterministic rewrite。
- `GET /api/project-rewrites/{rewrite_id}` 查询持久化 rewrite 结果。
- 输出包含 `matched_points`、`missing_points`、`evidence_required`、`rewritten_bullets`、`forbidden_changes`、`risk_flags` 和 `rewrite_strategy`。
- 已有 Project Rewrite API、规则和 DB infrastructure 测试。

Frontend / Dashboard：

- ProjectOptimizationPage 支持 project list、create / update project facts、project detail、rewrite form 和 rewrite result display。
- 前端展示 matched / missing / evidence required / rewritten bullets / forbidden changes / risk flags。
- Dashboard 展示 project count、active project count、latest project name/status，并保留 Profile/Resume/Application/Evaluation 等现有统计。

## 4. 明确边界

v0.9 明确不做：

- 不接真实 LLM。
- 不自动写回 Resume Version。
- 不编造项目经历、数字、公司、技术栈、上线状态、业务规模、用户量、收益或准确率。
- 不做 Interview Center。
- 不做 Study Plan。
- 不重写 Match Scoring。
- 不接 embedding / vector DB。
- 不做自动投递。
- 不做认证、多用户权限。
- 不把 deterministic evaluation 当作模型能力最终评分。

## 5. 测试与检查结果

2026-06-24 在 `main` 执行：

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests
```

结果：193 passed, 6 warnings。

```bash
cd frontend && npm run build
```

结果：通过，TypeScript 和 Vite production build 成功。

```bash
docker compose config
```

结果：通过，Compose 配置可解析。

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

结果：未验证。当前环境 Docker daemon/socket 不可用：

```text
failed to connect to the docker API at unix:///Users/jiaxulong/.docker/run/docker.sock
```

该结果记录为环境限制，不视为代码失败。Docker build 需要在 Docker daemon 可用环境重新验证。

## 6. 安全与隐私

- `.env`、真实 API key、local DB、`local_data/`、uploads、vector index、exports、logs、cache、`dist/` 和 `node_modules/` 不进入 Git。
- Demo 和测试只使用 synthetic data。
- 不提交真实简历、真实 JD、投递记录、面试复盘、真实公司隐私或敏感商业数据。
- PDF / DOCX 解析只做文本层提取，不做 OCR。
- Resume `raw_text` 仍属于本地 prototype 数据；前端只展示 preview，后续生产化前需要继续收敛 raw_text 返回和日志策略。
- Profile 只保存目标岗位、地点、行业、技能结构、偏好和可选 resume version ref，不保存身份证、详细住址、政治、健康等敏感身份信息。
- Project facts 只应保存用户确认的 synthetic 或可公开复述事实，不应保存真实公司私密信息或内部不可公开材料。
- Project Rewrite 不自动修改简历版本；`risk_flags` / `forbidden_changes` 用于提醒用户不要过度包装。
- Bad Case 和 Evaluation Case 不应保存大段隐私原文。

## 7. Tag 建议

当前 v0.9 handoff 文档完成后，建议提交：

```bash
git commit -m "docs: finalize v0.9 project optimization handoff"
```

提交并完成最终只读验收后，可考虑创建 annotated tag：

```bash
git tag -a v0.9.0-project-optimization -m "CareerAgent v0.9.0 project optimization"
```

打 tag 前建议确认：

- `git status --short --branch` clean 且 `main` 与 `origin/main` 同步。
- 全量 backend tests、frontend build、`docker compose config`、`py_compile` 和 `git diff --check` 通过。
- Docker daemon 可用时补跑 `docker compose build`；如果不可用，在 release notes 中保留环境限制说明。
