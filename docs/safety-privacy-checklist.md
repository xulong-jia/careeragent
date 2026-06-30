# Safety and Privacy Checklist

本清单用于本地开发、演示和提交前自查。CareerAgent 当前是本地 prototype，不适合直接处理真实敏感求职材料。

## Git 与文件

- [ ] 不提交 `.env`。
- [ ] 不提交真实 API key。
- [ ] 不提交 `local_data/`。
- [ ] 不提交 SQLite 数据库文件：`*.db`、`*.sqlite`、`*.sqlite3`。
- [ ] 不提交 `frontend/dist/`。
- [ ] 不提交 `node_modules/`。
- [ ] 不提交 `.venv/`。
- [ ] 不提交 uploads、vector index、exports、logs、cache。
- [ ] 不提交执行手册原文或私有项目材料。

推荐检查：

```bash
git status --short --branch
git ls-files | rg '(^|/)(\.env|local_data|node_modules|dist|\.venv|__pycache__|uploads|vector_index|exports|logs|cache)(/|$)|\.(db|sqlite|sqlite3)$'
```

## API Key

- [ ] `.env.example` 只保留空 placeholder。
- [ ] `OPENAI_API_KEY` 当前不需要填写。
- [ ] 当前 deterministic MVP 不依赖任何真实 LLM provider。

## Resume / JD / RAG

- [ ] Demo resume 使用 synthetic text。
- [ ] Demo JD 使用 synthetic text。
- [ ] 不上传真实简历、真实 JD、真实邮件、手机号、地址、证件号或薪资记录。
- [ ] 不把完整 `raw_text` 输出到日志。
- [ ] Resume / JD 默认 API response 不返回完整 raw_text，只返回 `raw_text_preview`。
- [ ] `raw_text_preview` / `text_preview` 使用短 preview，并经过 email、phone、secret masking。
- [ ] 如需日志输出 payload，先使用 `app.core.privacy.redact_mapping`。
- [ ] Interview Center 后续开发继续使用 preview / refs，不把完整 raw_text 作为默认 payload 透传给前端。
- [ ] RAG 文档只使用 synthetic notes。
- [ ] RAG response 默认展示 preview / snippet，不展示完整 chunk text。
- [ ] RAG document 删除后，document/chunks 不再出现在默认 list/search；历史 answer runs 只保留 safe refs/citations。

## Agent

- [ ] Agent 当前是 deterministic state machine。
- [ ] Agent step payload 只保存 IDs、refs 和 short metadata。
- [ ] 不把完整 resume raw_text、JD raw_text 或 RAG chunk text 写入 agent refs。
- [ ] Agent 不自动投递。

## Application Tracking

- [ ] Application 只做手动 tracking。
- [ ] 不接招聘网站。
- [ ] 不自动提交职位申请。
- [ ] 不保存完整投递材料、邮件正文或面试 transcript。
- [ ] `interview_notes` 和 `reflection` 只写摘要。
- [ ] DELETE Application 只做 `archived`，并记录 status history；默认 list/stats 不展示 archived。

## Delete / Archive Governance

- [ ] `DELETE /api/resumes/{resume_id}` 软删除 resume，并归档其 versions。
- [ ] `DELETE /api/jobs/{jd_id}` 归档 JD；历史引用不能导致 Application/Match 500。
- [ ] `DELETE /api/applications/{application_id}` 归档投递记录，不物理删除运营历史。
- [ ] `DELETE /api/rag/documents/{doc_id}` 删除 document/chunks，answer history 只保留 safe refs。
- [ ] 缺失记录返回明确 404 error code，不吞错、不伪造成功。

## Bad Case

- [ ] Bad Case 只保存 `source_type` / `source_id` 和问题摘要。
- [ ] 不在 description / expected / actual / suggested fix 中粘贴完整简历、JD、RAG chunk 或面试原文。
- [ ] Bad Case API schema 不接受 `raw_text` 等额外敏感字段。

## Evaluation

- [ ] Evaluation 当前是 deterministic smoke / regression tracking。
- [ ] 不做 LLM judge。
- [ ] 不做多模型对比。
- [ ] Evaluation Case 不复制 `raw_text`。
- [ ] 从 Bad Case 创建 evaluation case 时只保存 refs 和短摘要。
- [ ] Evaluation `run_config` 只记录 prompt/schema/retrieval/model/code/evaluation version，不记录 secret。
- [ ] `scripts/run_evals.py` 输出的 `metrics.json` / `failed_cases.json` 不包含 raw private text keys。

## Version Tracking

- [ ] 版本常量集中在 `app.core.versioning`。
- [ ] RAG retrieval debug 包含 retrieval/schema/model version。
- [ ] Agent final summary 包含 safe version metadata。
- [ ] Evaluation API 和 fileized eval runner 包含 evaluation version。

## Demo

- [ ] 运行 `scripts/seed_demo_data.py` 前确认连接的是本地后端。
- [ ] 截图前确认页面没有真实个人数据。
- [ ] 截图存放到 `docs/screenshots/` 前人工复核内容。

## 提交前扫描

```bash
git status --short
git ls-files | grep -E '(^|/)(\.env|local_data|node_modules|dist|__pycache__|\.pytest_cache|.*\.db|.*\.sqlite|.*\.pyc)$' || true
grep -R "OPENAI_API_KEY\|sk-" . --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=dist --exclude-dir=.venv || true
grep -R "raw_text\|answer_text\|chunk.text\|interview_notes\|reflection" backend/app/api backend/app/schemas backend/app/services backend/app/agents scripts evals -n || true
```

grep 命中需要人工判断：schema/model/request 字段、测试 fixture 和文档说明可以存在；日志、默认响应、eval payload 和 committed artifacts 不应包含真实 secret 或大段原文。
