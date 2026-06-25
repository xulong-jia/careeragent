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
- [ ] Interview Center 后续开发继续使用 preview / refs，不把完整 raw_text 作为默认 payload 透传给前端。
- [ ] RAG 文档只使用 synthetic notes。
- [ ] RAG response 默认展示 preview / snippet，不展示完整 chunk text。

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

## Demo

- [ ] 运行 `scripts/seed_demo_data.py` 前确认连接的是本地后端。
- [ ] 截图前确认页面没有真实个人数据。
- [ ] 截图存放到 `docs/screenshots/` 前人工复核内容。
