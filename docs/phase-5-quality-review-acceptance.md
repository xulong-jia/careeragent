# CareerAgent 阶段五 Quality Review / Bad Case 验收报告

## 1. 阶段五目标回顾

阶段五目标是建立质量复查和 bad case 闭环，让 CareerAgent 能够对 Match Report、RAG Answer、Agent Run 等结果进行人工质量记录，并把问题、风险和改进建议沉淀为可追踪记录。

本阶段目标包括：

- 建立质量复查和 bad case 闭环。
- 对 Match Report、RAG Answer、Agent Run 等结果进行人工质量记录。
- 支持人工标注 bad case。
- 支持记录问题类型、严重程度、状态、改进建议。
- 支持通过 bad case 反向改进 Match / RAG / Agent Workflow。
- 当前阶段优先做人工 review record，不做自动评估。
- 当前阶段不接真实 LLM reviewer。
- 当前阶段不做自动投递。
- 当前阶段不做正式 Evaluation Center。

## 2. 已完成功能清单

- Quality Review / Bad Case 设计文档。
- `bad_cases` DB table。
- BadCase ORM model。
- Alembic migration 0005。
- BadCase schema skeleton。
- Bad Case repository。
- Bad Case service。
- Bad Case API。
- create bad case。
- list bad cases。
- filter bad cases。
- get bad case detail。
- patch bad case。
- allowed values validation。
- extra sensitive fields rejected。
- QualityReviewPage 最小 UI。
- Dashboard / navigation Quality Review 入口。
- MarkBadCasePanel 可复用组件。
- Match 页面 Mark as bad case 入口。
- KnowledgeBasePage Mark as bad case 入口。
- AgentRunsPage Mark as bad case 入口。
- 不保存 raw_text / JD raw_text / RAG chunk text。
- 未接 LLM / OpenAI / DeepSeek / Qwen。
- 未做自动评估 / 自动投递。

## 3. 当前不包含的能力

当前阶段五不包含：

- 自动评估。
- 真实 LLM reviewer。
- OpenAI / DeepSeek / Qwen API。
- `evaluation_runs` / `evaluation_items`。
- 复杂 Evaluation Center。
- 批量 benchmark。
- 复杂评分 dashboard。
- 自动投递。
- 投递管理。
- 自动申请职位。
- 未经约束的 prompt / tool execution。

## 4. Bad Case 数据模型验收

`bad_cases` 用于记录人工质量复查问题。`source_type` / `source_id` 只保存来源类型和来源 ID，`category` / `severity` / `status` 均为 string。`description` / `expected_behavior` / `actual_behavior` / `suggested_fix` 只保存问题摘要。

隐私边界：

- 不保存 resume raw_text。
- 不保存 JD raw_text。
- 不保存 RAG chunk full text。
- 不保存投递记录或面试复盘原文。

BadCase 核心字段：

- `id`
- `user_id`
- `source_type`
- `source_id`
- `category`
- `severity`
- `title`
- `description`
- `expected_behavior`
- `actual_behavior`
- `suggested_fix`
- `status`
- `created_at`
- `resolved_at`

索引：

- `source_type`
- `source_id`
- `status`
- `severity`
- `category`
- `source_type + source_id`

## 5. Bad Case API 验收

Bad Case API：

- `POST /api/evaluations/bad-cases`
- `GET /api/evaluations/bad-cases`
- `GET /api/evaluations/bad-cases/{bad_case_id}`
- `PATCH /api/evaluations/bad-cases/{bad_case_id}`

验收点：

- 支持 create / list / filter / detail / patch。
- list 支持 `source_type` / `source_id` / `category` / `severity` / `status` filters。
- `status=fixed` / `status=wont_fix` 自动设置 `resolved_at`。
- `status=open` / `status=reviewing` 会清空 `resolved_at`。
- invalid `source_type` / `category` / `severity` / `status` 返回 400 `bad_case_invalid_field`。
- missing bad case 返回 404 `bad_case_not_found`。
- request schema 使用 `extra="forbid"` 拒绝额外敏感字段。
- API response 不返回源对象全文。

## 6. QualityReviewPage 验收

前端能力：

- Sidebar 增加 Quality Review。
- Dashboard 增加 Quality Review 卡片和 bad case 数量。
- QualityReviewPage 支持创建 bad case。
- 支持 bad case list。
- 支持 filters。
- 支持 bad case detail。
- 支持 patch status / severity / suggested_fix / title / description / category 等安全字段。
- 支持 loading / empty / error / success 状态。
- 页面提示用户只记录问题摘要，不粘贴完整原文。
- 页面不展示 raw_text / JD raw_text / RAG chunk text / API Key。

## 7. Mark as bad case 入口验收

Mark as bad case 入口能力：

- 新增 MarkBadCasePanel 可复用组件。
- Match 页面可从 Match Report 创建 bad case。
- KnowledgeBasePage 可从 selected document / answer result 创建 bad case。
- AgentRunsPage 可从 Agent Run 创建 bad case。
- MarkBadCasePanel 自动填 `source_type` / `source_id`。
- `description` 默认空。
- `expected_behavior` / `actual_behavior` / `suggested_fix` 由用户手写摘要。
- 不自动复制 Resume / JD / RAG chunk / Agent refs 原文。
- 创建成功后提示可在 Quality Review 页面查看。

## 8. 手动验收路径

1. 启动后端。
2. 执行 Alembic upgrade。
3. 检查 `/api/db/health`。
4. 启动前端。
5. 打开 Quality Review 页面。
6. 创建 bad case。
7. 查看 bad case list。
8. 使用 `source_type` / `category` / `severity` / `status` filters。
9. 查看 bad case detail。
10. patch status / severity / suggested_fix。
11. 确认 `fixed` / `wont_fix` 设置 `resolved_at`。
12. 确认 `open` / `reviewing` 清空 `resolved_at`。
13. 在 Match 页面使用 Mark as bad case。
14. 在 Knowledge Base 页面使用 Mark as bad case。
15. 在 Agent Runs 页面使用 Mark as bad case。
16. 确认入口不自动复制原文。
17. 回到 Quality Review 页面确认新 bad case 可见。
18. 重启服务后确认 `bad_cases` 仍在。

## 9. 自动化检查命令

后端测试：

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests
```

前端 build：

```bash
cd frontend && npm run build
cd ..
```

Docker Compose config：

```bash
docker compose config
```

Alembic upgrade：

```bash
PYTHONPATH=backend backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
```

DB health：

```bash
PYTHONPATH=backend backend/.venv/bin/python - <<'PY'
from fastapi.testclient import TestClient
from app.main import app

with TestClient(app) as client:
    response = client.get("/api/db/health")
    print(response.status_code)
    print(response.json())
PY
```

Git 检查：

```bash
git diff --check
git status --short --branch
```

安全扫描：

```bash
git ls-files | rg '(^|/)(\.env|local_data|node_modules|dist|\.venv|__pycache__|uploads|vector_index|exports|logs|cache)(/|$)|\.(db|sqlite|sqlite3)$|CareerAgent_最终版项目开发执行手册\.md' || true
```

```bash
rg -n --hidden --glob '!.git/**' --glob '!local_data/**' --glob '!backend/local_data/**' --glob '!**/__pycache__/**' --glob '!backend/.venv/**' --glob '!frontend/node_modules/**' --glob '!frontend/dist/**' '(sk-[A-Za-z0-9_-]{20,}|OPENAI_API_KEY\s*=\s*[^\s#]+|DEEPSEEK_API_KEY\s*=\s*[^\s#]+|QWEN_API_KEY\s*=\s*[^\s#]+)' . || true
```

## 10. 安全与隐私检查

阶段五验收必须确认：

- `.env` 未提交。
- `local_data/` 未提交。
- `*.db` / `*.sqlite` / `*.sqlite3` 未提交。
- `vector_index/` 未提交。
- `node_modules` 未提交。
- `frontend/dist` 未提交。
- `backend/.venv` 未提交。
- `__pycache__` 未提交。
- uploads / exports / logs / cache 未提交。
- 真实简历未提交。
- 真实 JD 未提交。
- 真实文档未提交。
- API Key 未提交。
- 投递记录未提交。
- 面试复盘未提交。
- `CareerAgent_最终版项目开发执行手册.md` 未提交。
- 未发现 `sk-`、填值 `OPENAI_API_KEY`、DeepSeek/Qwen key。
- `bad_cases` 表不包含 `raw_text` / `jd_raw_text` / `chunk_text` / `full_text` / `resume_text` / `job_text`。
- Bad Case API response 不返回源对象全文。
- QualityReviewPage 不提示用户粘贴原文。
- MarkBadCasePanel 不自动复制原文。
- 不接 LLM。
- 不做自动评估。
- 不做自动投递。

## 11. 阶段五验收标准

通过标准：

- backend pytest 通过。
- frontend build 通过。
- docker compose config 通过。
- Alembic upgrade 通过。
- DB health 通过。
- git diff --check 通过。
- 安全扫描通过。
- `bad_cases` 可持久化。
- Bad Case API 可创建、查询、筛选、详情、更新。
- invalid allowed values 可被拒绝。
- extra sensitive fields 可被拒绝。
- QualityReviewPage 可操作。
- Mark as bad case 入口可操作。
- 不保存或展示隐私原文。
- 无 LLM / 无自动评估 / 无自动投递。

## 12. 阶段五结论

阶段五可以视为通过。当前项目已从 deterministic Agent Workflow workbench 升级为带 Quality Review / Bad Case 闭环的求职工作台。

当前 Quality Review 是人工 review record，不是真实自动评估系统。

下一步建议先做阶段五总验收确认。验收通过后，再单独新增 release notes。后续可打 tag：`v0.5.0-quality-review`。不要直接进入下一阶段开发。
