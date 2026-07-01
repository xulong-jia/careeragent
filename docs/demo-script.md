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

回到 Dashboard，确认展示 profile readiness、resume parse status、risk flags count、project count、active project count、latest project status，以及 Resume、JD、Match、Knowledge、Agent、Applications total/active/upcoming/overdue/conversion、Quality、Evaluation 统计。若刚运行 seed 脚本，应看到多个模块已有数据。

### JD Center

1. 创建 synthetic JD。
2. 查看 parser foundation job profile。
3. 确认 required / preferred skills、role category、evidence、confidence、warnings 和 interview focus。

### Match Report

1. 选择 resume version 和 JD。
2. 点击 Run Match。
3. 查看 total score、dimension scores、strengths、gaps 和 evidence。

### Project Optimization

1. 先在 JD Center 创建或选择一个 synthetic JD。
2. 创建 synthetic project facts。
3. 填写 name、role、period、background、tech stack、responsibilities、results 和 evidence JSON。
4. 选择 project，查看 detail 和 evidence。
5. 使用 JD selector 选择岗位，可选通过 selectors 绑定 resume version、match report 或 profile refs。
6. 点击 Run rewrite。
7. 查看 matched points、missing points、evidence required、rewritten bullets、forbidden changes 和 risk flags。

当前 Project Rewrite 是 deterministic suggestions，不接真实 LLM，不自动写回 Resume Version，不新增不存在的项目经历、指标、公司、技术栈、上线成果或业务规模。

### Interview Center

1. 先完成 JD Center、Resume Center 和 Project Optimization 的 synthetic 数据准备。
2. 打开 Interview Center。
3. 在 Generate Questions 中使用 JD、Resume Version、Project 和 RAG Answer selectors；Project Rewrite ref 属于高级可选项。
4. 点击 Generate Questions，查看 warnings、need more info、question type、difficulty、expected points 和 source refs。
5. 选择一个 question，在 textarea 中输入 synthetic answer。
6. 点击 Submit Answer，确认保存后页面只展示 `answer_text_preview`。
7. 选择 answer 并点击 Score Answer，查看 structure、technical depth、business understanding、evidence、clarity、risk control、overall average、feedback 和 weakness tags。
8. 使用 question filters 或 answer refresh 确认历史 question / answer 可从 DB-backed API 读取。
9. 可选：从 RAG Answer selector 选择一个 grounded answer run 重新生成 questions，确认 grounded refs 只以 source refs preview 出现；ungrounded run 只显示 warning。
10. 回到 Dashboard，查看 Interview Training 的 question count、answer count、scored answer count、latest average score 和 latest weakness tags。

当前 Interview Center 只接 deterministic question generation、answer submit/list、scoring API、Dashboard training stats 和 v1.2 12D optional grounded RAG answer run refs；不接真实 LLM，不做 LLM judge，不写入 Study Plan，不展示 Resume/JD full raw_text、RAG full chunk text 或完整已保存 answer_text。请勿输入真实面试复盘或隐私答案。

### Study Plan Center

1. 先完成 Profile、Match、Project Optimization 或 Interview Center 的 synthetic 数据准备，至少准备 target role。
2. 打开 Study Plan。
3. 在 Generate Study Plan 中输入 target role，或通过 Profile selector 让后端从 profile target_roles 推断。
4. 可选通过 Match Report、Interview Answer、RAG Answer selectors 绑定 refs；Project Rewrite ref 是高级可选项；填写 weakness tags、available hours per week 和 horizon weeks。
5. 点击 Generate Study Plan，查看 phases、tasks、resources、deliverables、acceptance criteria 和 source refs preview。
6. 使用 Plan Filters 按 status、target role、Profile selector 或 Match Report selector 刷新列表。
7. 选择 plan，查看 detail 中的 task_id、priority、status、source_gap、description、acceptance criteria、evidence required 和 source refs preview。
8. 修改 task status 为 todo、in progress、done、blocked 或 skipped，确认 detail 中 updated_at 刷新。
9. 可选：用 RAG Answer selector 选择 grounded answer run 重新生成 study plan，确认只新增学习/证据复核类 refs；ungrounded run 只记录 uncertainty ref，不作为强来源。
10. 回到 Dashboard，查看 Study Plans、Active Study Plans、Pending Tasks、Blocked Tasks、Done Tasks、Latest Study Target 和 In Progress Tasks 摘要。

当前 Study Plan Center 只接 deterministic generate/list/detail/task status/stats API、前端 StudyPlanPage、Dashboard study stats 和 v1.2 12D optional grounded RAG answer run refs；完整演示路径为 generate -> 查看 phases/tasks -> 更新 task status -> Dashboard stats。v1.3 Agent Workflow 可调用 Study Plan generation，但 Study Plan 页面本身不接真实 LLM，不接外部学习平台或日历提醒，不展示 Resume/JD full raw_text、RAG full chunk text 或完整 answer_text。

### Knowledge Base

1. 创建 synthetic RAG document。
2. 点击 index。
3. 搜索关键词，例如 `FastAPI interview preparation`。
4. 运行 deterministic answer，确认 Answer Run ID、grounded、uncertainty、evidence summary、citations、source refs preview 和折叠 retrieval debug。
5. 在 Answer History 中使用 grounded、uncertainty 和 retrieval mode filters 刷新历史。
6. 选择一个 answer run，查看 detail 中的 question、answer、citations、source_refs preview、retrieval_debug 和 created_at。
7. 回到 Dashboard，查看 RAG Documents、Indexed Documents、RAG Chunks、Grounded Answers、Ungrounded Answers、Latest RAG Answer 和 Latest RAG Uncertainty。
8. 在 Interview Center、Study Plan 或 Agent Runs 中通过 RAG Answer selector 选择 grounded answer run。

当前 Knowledge Base 默认使用 lexical retrieval；阶段 2.2 可通过 API/env 测试 DB-persisted local vector/hybrid retrieval，但默认不接真实 LLM、外部 embedding 或 production vector DB。v1.2 final handoff 确认可完整演示 create/index document -> search -> grounded answer -> answer history -> Dashboard RAG stats -> Interview / Study Plan optional RAG Answer refs。页面只展示 preview、snippet、source_refs preview、safe retrieval debug 和 stats 聚合，不展示 document full raw_text、chunk full text、embedding vector、Resume/JD full raw_text 或完整 interview answer_text，也不自动写入 Interview、Study Plan、Resume、Project 或 Application。

### Agent Runs

1. 先准备 Resume Version、JD，建议同时准备一个绑定该 resume version 的 active project。
2. 打开 Agent Runs，创建 `job_application_preparation` workflow。
3. 使用 Resume Version、JD、Project、Existing Application 和 RAG Answer selectors；可选填写 RAG Query。
4. 保持 `Create or link application` 开启时，workflow 会创建 saved draft application；通过 Existing Application selector 可绑定已有记录。
5. 点击 Create run。
6. 查看 run detail、step timeline、`final_summary.total_score`、top strengths/gaps、next actions 和 created record IDs。
7. 确认 step order 包含 Match、Project Rewrite、Interview Question generation、Study Plan generation、Application create/link 和 Final Summary。

当前 Agent Runs 是 deterministic workflow baseline，不接真实 LLM，不做自由聊天 Agent，不自动投递，不自动修改简历、项目、面试答案、学习计划任务状态或投递状态。

### Applications

1. 创建手动 application record，必须绑定 `jd_id` 和 `resume_version_id`；可选绑定 `match_report_id` 和 `agent_run_id`。
2. 填写 company、role title、role category、status、priority、apply date、next step date、source URL、location、notes、interview notes、reflection、interview question IDs 和 tags。
3. 如果刚运行 Agent workflow，可在 Application Board、列表或详情中查看 Agent 创建/绑定的 draft application。
4. 修改 status，并填写 status reason / note；确认 detail 中 status history 新增一条记录。
5. 更新 notes、priority、dates、reflection 等非状态字段，确认 status history 不重复新增。
6. 使用 status / company / role category / priority / jd_id / resume_version_id / match_report_id / agent_run_id 筛选。
7. 在 reflection 表单填写 interview feedback、failure reason、preparation gaps、next actions 和 weakness tags；确认只更新 Application，不自动写 Bad Case 或 Study Plan。
8. 回到 Dashboard，查看 application total、active、interview、offer、rejected、upcoming、overdue、conversion 和 latest application。

当前 Applications 只做手动运营 tracking，不自动投递，不接招聘网站，不自动状态流转，不保存完整投递材料、简历原文、JD 原文或完整面试复盘。

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
- Study Plan Center
- Match Report
- Knowledge Base
- Agent Runs
- Application Tracker
- Quality Review
- Evaluation Page

截图提交前必须确认没有真实个人信息、真实 JD、真实公司隐私、API key 或本地路径敏感信息。
