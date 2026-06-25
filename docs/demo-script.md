# CareerAgent Demo Script

本文档给出从零演示 CareerAgent 当前本地原型的流程。所有示例数据必须是 synthetic data，不使用真实简历、真实 JD、真实公司隐私、真实联系方式或真实面试复盘。

## 1. 启动后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

检查：

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/db/health
```

## 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

打开：

```text
http://localhost:5173
```

## 3. 可选：使用 Docker Compose

```bash
docker compose build
docker compose up
```

Compose 后端会在容器启动时执行 `alembic upgrade head`。SQLite 数据保存在 `backend/local_data/careeragent.db`，该目录不进入 Git。

## 4. 可选：生成 synthetic demo data

后端启动后，在仓库根目录运行：

```bash
python3 scripts/seed_demo_data.py
```

如果后端不是默认地址：

```bash
CAREERAGENT_API_BASE_URL=http://localhost:8000 python3 scripts/seed_demo_data.py
```

脚本会通过公开 HTTP API 创建：

- synthetic resume
- synthetic JD
- match report
- RAG document + chunks
- Agent run
- application record
- bad case
- evaluation case
- evaluation run

## 5. 手动演示流程

### Resume Center

1. 上传 `.pdf`、`.docx`、`.md` 或 `.txt` synthetic resume。
2. 查看 `raw_text_preview`。
3. 选择 resume version，点击 Parse。
4. 查看 parser method、warnings、raw text preview 和 structured resume JSON。
5. 编辑 structured resume JSON，确认 JSON valid。
6. 点击 Risk Check，查看 risk flags 和 risk report。
7. 填写 version name、target role，保存 confirmed version。
8. 查看 resume versions，确认新增 version 不覆盖旧版本。
9. 可继续 clone 或 archive 一个版本。

PDF / DOCX 当前只做文本层提取，不做 OCR；risk-check 只展示规则检测结果，不自动修改简历。

### Profile Center

1. 创建 synthetic profile。
2. 填写 target roles、target locations、target industries、skill map 和 preferences。
3. 可选绑定刚保存的 confirmed resume version。
4. 查看 completeness score、missing fields 和 readiness level。

当前无认证系统，`user_id` 使用默认 `default`，不演示多用户权限。

### Dashboard

回到 Dashboard，确认展示 profile readiness、resume parse status、risk flags count、project count、active project count、latest project status，以及 Resume、JD、Match、Knowledge、Agent、Applications、Quality、Evaluation 统计。若刚运行 seed 脚本，应看到多个模块已有数据。

### JD Center

1. 创建 synthetic JD。
2. 查看 deterministic job profile。
3. 确认 required skills、role category、interview focus。

### Match Report

1. 选择 resume version 和 JD。
2. 点击 Run Match。
3. 查看 total score、dimension scores、strengths、gaps 和 evidence。

### Project Optimization

1. 先在 JD Center 创建或选择一个 synthetic JD，并复制 JD ID。
2. 创建 synthetic project facts。
3. 填写 name、role、period、background、tech stack、responsibilities、results 和 evidence JSON。
4. 选择 project，查看 detail 和 evidence。
5. 输入 JD ID，可选输入 resume version、match report 或 profile refs。
6. 点击 Run rewrite。
7. 查看 matched points、missing points、evidence required、rewritten bullets、forbidden changes 和 risk flags。

当前 Project Rewrite 是 deterministic suggestions，不接真实 LLM，不自动写回 Resume Version，不新增不存在的项目经历、指标、公司、技术栈、上线成果或业务规模。

### Interview Center

1. 准备一个 synthetic JD ID 和一个 synthetic Resume Version ID。
2. 打开 Interview Center。
3. 在 Generate Questions 中输入 `jd_id` 和 `resume_version_id`，可选输入 `project_id`、`project_rewrite_id`、question types 和 max questions。
4. 点击 Generate Questions，查看 warnings、need more info、question type、difficulty、expected points 和 source refs。
5. 选择一个 question，在 textarea 中输入 synthetic answer。
6. 点击 Submit Answer，确认保存后页面只展示 `answer_text_preview`。
7. 选择 answer 并点击 Score Answer，查看 structure、technical depth、business understanding、evidence、clarity、risk control、overall average、feedback 和 weakness tags。
8. 使用 question filters 或 answer refresh 确认历史 question / answer 可从 DB-backed API 读取。

当前 Interview Center 只接 deterministic question generation、answer submit/list 和 scoring API；不接真实 LLM，不做 LLM judge，不写入 Study Plan，不展示 Resume/JD full raw_text。请勿输入真实面试复盘或隐私答案。

### Knowledge Base

1. 创建 synthetic RAG document。
2. 点击 index。
3. 搜索关键词，例如 `FastAPI interview preparation`。
4. 运行 deterministic answer。
5. 查看 sources 和 snippets。

### Agent Runs

1. 创建 `job_application_preparation` workflow。
2. 选择 resume version 和 JD。
3. 可选启用 RAG query。
4. 查看 run detail 和 step timeline。

### Applications

1. 创建手动 application record。
2. 绑定 `jd_id`、`resume_version_id`、`match_report_id`。
3. 修改 status。
4. 使用 status / company / jd_id / resume_version_id 筛选。
5. 查看 stats。

### Quality Review

1. 创建 bad case。
2. 选择 source type 和 source id。
3. 只写问题摘要，不粘贴完整 raw_text。
4. 更新 status。

### Evaluation

1. 打开 Evaluation 页面。
2. 选择 `all`。
3. 点击 Run smoke set。
4. 查看 latest metrics。
5. 查看 results 和 cases。

## 6. 截图清单

当前仓库不包含真实截图，不伪造截图。运行本地 demo 后可人工补充以下截图到 `docs/screenshots/`：

- Dashboard
- Resume Center
- Resume Center parse / risk-check / confirmed version workflow
- Project Optimization
- Interview Center
- Match Report
- Knowledge Base
- Agent Runs
- Application Tracker
- Quality Review
- Evaluation Page

截图提交前必须确认没有真实个人信息、真实 JD、真实公司隐私、API key 或本地路径敏感信息。
