# CareerAgent 阶段四 Agent Workflow 验收报告

## 1. 阶段四目标回顾

阶段四目标是建立可审计、可追踪、可恢复的 Agent Workflow 基础设施。

- 建立可审计、可追踪、可恢复的 Agent Workflow 基础设施。
- 通过 deterministic state machine 串联 Resume / JD / Match / RAG。
- 持久化 `agent_runs` / `agent_steps`。
- 记录 step timeline、status、duration、error、input_refs、output_refs。
- 支持 `need_more_info` 缺槽追问。
- 提供 Agent Runs API。
- 提供 AgentRunsPage 最小 UI。
- 当前阶段不接真实 LLM Agent。
- 当前阶段不做自动投递。
- 当前阶段不是自由聊天 Agent。

## 2. 已完成功能清单

- Agent Workflow 设计文档。
- `agent_runs` / `agent_steps` tables。
- AgentRun / AgentStep ORM models。
- Alembic migration。
- Agent schema skeleton。
- deterministic workflow runner。
- fixed workflow: `job_application_preparation`。
- `validate_inputs` step。
- `load_resume_version` step。
- `load_job_profile` step。
- `run_match_report` step。
- `rag_search` skipped/completed behavior。
- `build_final_summary` step。
- `need_more_info` behavior。
- failed behavior。
- step timeline DB persistence。
- Agent repository。
- Agent service。
- Agent Runs API。
- run list/detail/steps endpoints。
- AgentRunsPage 最小 UI。
- safe JSON render helper。
- 前端不展示 raw_text / JD raw_text / chunk text。
- 未接 LLM / OpenAI / DeepSeek / Qwen。
- 未做自动投递。

阶段四当前是 deterministic workflow，不是真实 LLM Agent。

## 3. 当前不包含的能力

- 真实 LLM Agent。
- OpenAI / DeepSeek / Qwen API。
- 自由聊天 Agent。
- true tool-calling Agent。
- 自动投递。
- 投递管理。
- Bad Case 页面。
- Evaluation Center。
- 复杂异步任务队列。
- run resume endpoint。
- 复杂 Agent memory。
- 多 workflow 编排。
- 自动申请职位。
- 未经约束的 prompt/tool execution。

## 4. Agent 数据模型验收

`agent_runs` 用于记录一次 workflow run。`agent_steps` 用于记录一次 run 下的 step timeline。`agent_steps.run_id` 外键指向 `agent_runs.id`，并通过 `run_id + step_order` unique constraint 避免同一 run 下 step 顺序冲突。

`input_refs` / `output_refs` 只保存 IDs / refs / short metadata，不保存 resume raw_text、JD raw_text 或 RAG chunk full text。`error_message` 不保存隐私原文。

AgentRun 核心字段：

- `id`
- `user_id`
- `workflow_name`
- `status`
- `input_refs`
- `output_refs`
- `missing_slots`
- `questions`
- `error_code`
- `error_message`
- `created_at`
- `started_at`
- `finished_at`
- `duration_ms`

AgentStep 核心字段：

- `id`
- `run_id`
- `step_name`
- `step_order`
- `status`
- `input_refs`
- `output_refs`
- `error_code`
- `error_message`
- `created_at`
- `started_at`
- `finished_at`
- `duration_ms`

## 5. Deterministic Workflow Runner 验收

当前最小 workflow：

```text
job_application_preparation
```

步骤：

1. `validate_inputs`
2. `load_resume_version`
3. `load_job_profile`
4. `run_match_report`
5. `rag_search`
6. `build_final_summary`

验收行为：

- `use_rag=false` 时 `rag_search` step 创建并标记 `skipped`。
- `use_rag=true` 且 `rag_query` 缺失时 run/step 返回 `need_more_info`。
- `need_more_info` 时只创建 `validate_inputs` step，后续 steps 不创建。
- `failed` 时当前 step `failed`，run `failed`，后续 steps 不继续。
- success 时 run `completed`。
- `final_summary` 是 deterministic 短文本，不调用 LLM、不编造经历。

## 6. Agent Runs API 验收

Agent Runs API：

- `POST /api/agents/runs`
- `GET /api/agents/runs`
- `GET /api/agents/runs/{run_id}`
- `GET /api/agents/runs/{run_id}/steps`

验收行为：

- `POST /api/agents/runs` 同步执行 deterministic workflow。
- `completed` / `need_more_info` / `failed` 均作为 run 业务状态返回。
- unsupported workflow 返回 `400 agent_workflow_not_supported`。
- missing run 返回 `404 agent_run_not_found`。
- `GET /api/agents/runs` 支持 `workflow_name` / `status` / `limit` filters。
- `GET /api/agents/runs/{run_id}/steps` 按 `step_order asc` 返回 timeline。
- API response 不返回 raw_text / JD raw_text / RAG chunk full text / full snippet。

## 7. AgentRunsPage 验收

前端能力：

- Sidebar 增加 Agent Runs。
- Dashboard 增加 Agent Runs 卡片。
- AgentRunsPage 支持创建 deterministic workflow run。
- `workflow_name` 固定默认 `job_application_preparation`。
- 支持输入 `resume_id` / `resume_version_id` / `jd_id` / `use_rag` / `rag_query`。
- 支持 runs list。
- 支持 run detail。
- 支持 steps timeline。
- 展示 `completed` / `need_more_info` / `failed` / `skipped` / `pending` / `running`。
- 支持 loading / error / empty state。
- safe JSON render helper 隐藏敏感字段。

safe JSON 会隐藏或替换以下 key：

- `raw_text`
- `jd_raw_text`
- `chunk_text`
- `full_text`
- `snippet`
- `api_key`
- `secret`
- `token`

## 8. 手动验收路径

1. 启动后端。
2. 执行 Alembic upgrade。
3. 检查 `/api/db/health`。
4. 启动前端。
5. 打开 Agent Runs 页面。
6. 创建缺少 resume/JD 的 run。
7. 确认 `need_more_info`。
8. 创建 synthetic Resume / JD 前置数据。
9. 创建成功的 `job_application_preparation` run。
10. 查看 run list。
11. 查看 run detail。
12. 查看 steps timeline。
13. 确认 `use_rag=false` 时 `rag_search` 为 `skipped`。
14. 创建 `use_rag=true` 且缺少 `rag_query` 的 run。
15. 确认 `need_more_info`。
16. 如已有 synthetic RAG document，验证 `use_rag=true` 路径。
17. 确认页面没有展示 raw_text / JD raw_text / chunk text。
18. 重启服务后确认 `agent_runs` / `agent_steps` 仍在。

## 9. 自动化检查命令

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests

cd frontend && npm run build
cd ..

docker compose config

PYTHONPATH=backend backend/.venv/bin/alembic -c backend/alembic.ini upgrade head

PYTHONPATH=backend backend/.venv/bin/python - <<'PY'
from fastapi.testclient import TestClient
from app.main import app

with TestClient(app) as client:
    response = client.get("/api/db/health")
    print(response.status_code)
    print(response.json())
PY

git diff --check

git status --short --branch
```

安全扫描命令：

```bash
git ls-files | rg '(^|/)(\.env|local_data|node_modules|dist|\.venv|__pycache__|uploads|vector_index|exports|logs|cache)(/|$)|\.(db|sqlite|sqlite3)$|CareerAgent_最终版项目开发执行手册\.md' || true

rg -n --hidden --glob '!.git/**' --glob '!local_data/**' --glob '!backend/local_data/**' --glob '!**/__pycache__/**' --glob '!backend/.venv/**' --glob '!frontend/node_modules/**' --glob '!frontend/dist/**' '(sk-[A-Za-z0-9_-]{20,}|OPENAI_API_KEY\s*=\s*[^\s#]+|DEEPSEEK_API_KEY\s*=\s*[^\s#]+|QWEN_API_KEY\s*=\s*[^\s#]+)' . || true
```

## 10. 安全与隐私检查

- `.env` 未提交。
- `local_data/` 未提交。
- `*.db` / `*.sqlite` / `*.sqlite3` 未提交。
- `vector_index/` 未提交。
- `node_modules` 未提交。
- `frontend/dist` 未提交。
- `backend/.venv` 未提交。
- `__pycache__` 未提交。
- `uploads` / `exports` / `logs` / `cache` 未提交。
- 真实简历未提交。
- 真实 JD 未提交。
- 真实文档未提交。
- API Key 未提交。
- 投递记录未提交。
- 面试复盘未提交。
- `CareerAgent_最终版项目开发执行手册.md` 未提交。
- 未发现 `sk-`、填值 `OPENAI_API_KEY`、DeepSeek/Qwen key。
- Agent step payload 不保存 raw_text / JD raw_text / chunk text。
- Agent API response 不返回 raw_text / JD raw_text / chunk text。
- AgentRunsPage safe JSON helper 过滤敏感字段。
- Agent Workflow 不调用 LLM。
- Agent Workflow 不自动投递。

## 11. 阶段四验收标准

- backend pytest 通过。
- frontend build 通过。
- docker compose config 通过。
- Alembic upgrade 通过。
- DB health 通过。
- `git diff --check` 通过。
- 安全扫描通过。
- `agent_runs` / `agent_steps` 可持久化。
- deterministic runner 可生成 step timeline。
- `need_more_info` 可用。
- failed behavior 可追踪。
- Agent Runs API 可用。
- AgentRunsPage 可操作。
- 前端和 API 不展示隐私原文。
- 无 LLM / 无自动投递。

## 12. 阶段四结论

阶段四可以视为通过。

当前项目已从 RAG knowledge base 升级为 deterministic Agent Workflow workbench。当前 Agent 是 deterministic workflow，不是真实 LLM Agent。

下一步建议先做阶段四总验收确认。验收通过后，再单独新增 release notes。后续可打 tag：`v0.4.0-agent-workflow`。

不要直接进入下一阶段开发。
