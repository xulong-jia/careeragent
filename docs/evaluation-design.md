# CareerAgent 阶段六：Deterministic Evaluation / 评测体系设计

状态说明：阶段六 MVP 已完成。当前实现是 deterministic evaluation，用于回归检查和质量追踪，不是 LLM judge，不是多模型评测平台，也不是对模型能力的最终评分。

## 1. 当前目标

- 持久化 evaluation runs / cases / results。
- 提供内置 `synthetic_smoke_v1`，覆盖 Match、RAG、Agent、Application 和 Bad Case。
- 支持手动创建 evaluation case。
- 支持从 Bad Case 创建 evaluation case，并保留 `bad_case_id` 关联。
- 提供 Evaluation API 和 EvaluationPage。
- 让后续 Bad Case regression set 有稳定数据结构可扩展。

## 2. 明确不做

- 不接真实 LLM。
- 不做 LLM judge。
- 不接 embedding、vector database 或 reranker。
- 不做多模型对比。
- 不做大型人工标注系统。
- 不做复杂 evaluation dashboard。
- 不把 smoke result 当作模型能力最终评分。

## 3. 数据表

### evaluation_runs

用途：记录一次 evaluation run 的配置、状态和聚合指标。

| 字段 | 说明 |
| --- | --- |
| id | `eval_run_<uuid hex>` |
| name | run 名称 |
| module | `all`、`match`、`rag`、`agent`、`application`、`bad_case` |
| dataset_name | 默认 `synthetic_smoke_v1` |
| status | `pending`、`running`、`completed`、`failed` |
| metrics | JSON，包含 `total_count`、`passed_count`、`failed_count`、`pass_rate`、`by_module` |
| run_config | JSON，记录 deterministic、llm_judge=false、model_comparison=false |
| started_at / finished_at / created_at | 时间戳 |

### evaluation_cases

用途：记录 synthetic、manual 或 bad_case 来源的评测 case。

| 字段 | 说明 |
| --- | --- |
| id | `eval_case_<uuid hex>` |
| module | `match`、`rag`、`agent`、`application`、`bad_case` |
| dataset_name | 数据集名称 |
| case_name | case 名称 |
| input_payload | JSON，只保存 synthetic payload、结构化 refs 或摘要 |
| expected_output | JSON，只保存期望结构或摘要 |
| tags | JSON list |
| source_type | `synthetic`、`bad_case`、`manual` |
| bad_case_id | 可选 FK，指向 `bad_cases.id` |
| created_at / updated_at | 时间戳 |

### evaluation_results

用途：记录一次 run 中每个 case 的实际输出、得分和通过状态。

| 字段 | 说明 |
| --- | --- |
| id | `eval_result_<uuid hex>` |
| run_id | FK，指向 `evaluation_runs.id` |
| case_id | FK，指向 `evaluation_cases.id` |
| module | case 所属模块 |
| status | `passed`、`failed`、`error` |
| actual_output | JSON，deterministic evaluator 输出 |
| expected_output | JSON，case 的期望结构 |
| passed | boolean |
| score | float，当前 MVP 为 0 或 1 |
| error | 可选错误摘要 |
| created_at | 时间戳 |

## 4. API

```text
POST /api/evaluations/runs
GET /api/evaluations/runs
GET /api/evaluations/runs/{run_id}
GET /api/evaluations/runs/{run_id}/results
GET /api/evaluations/cases
POST /api/evaluations/cases
POST /api/evaluations/cases/from-bad-case/{case_id}
GET /api/evaluations/stats
```

Bad Case API 继续保持：

```text
POST /api/evaluations/bad-cases
GET /api/evaluations/bad-cases
GET /api/evaluations/bad-cases/{bad_case_id}
PATCH /api/evaluations/bad-cases/{bad_case_id}
```

## 5. Synthetic Smoke Set

`synthetic_smoke_v1` 当前覆盖：

- Match：检查 `total_score`、`dimension_scores`、`strengths`、`gaps`、`evidence` 结构和 score 范围。
- RAG：检查 query、sources、snippets、uncertainty 结构，允许 no evidence 的可解释返回。
- Agent：检查 workflow status 是否为 `completed` 或 `need_more_info`，steps 是否有顺序。
- Application：检查 status 枚举、筛选命中和 stats 字段结构。
- Bad Case：检查 source refs、category、status 和 privacy-safe contract。

## 6. Bad Case 关联

`POST /api/evaluations/cases/from-bad-case/{case_id}` 会读取已有 Bad Case，并创建一条 `source_type=bad_case` 的 evaluation case。

保存策略：

- 保存 `source_type`、`source_id`、`category`、`severity`、`status`。
- 保存 description / expected / actual / suggested fix 的短摘要。
- 保存 `bad_case_id` 以支持追踪。
- 不复制 Resume raw_text、JD raw_text、RAG chunk text、Agent full refs 或其他隐私原文。

## 7. 前端

EvaluationPage 当前支持：

- 查看 evaluation stats。
- 运行 `synthetic_smoke_v1`。
- 查看 evaluation run 列表。
- 查看最近一次 run 的 metrics。
- 查看 results 列表。
- 查看 cases 列表。

Dashboard 已增加 Evaluation stats 入口。

## 8. 后续扩展

- 将 Bad Case 回归集独立成 regression dataset。
- 为 Match / RAG / Agent 增加更细粒度 deterministic rule。
- 增加失败样例 diff 和趋势统计。
- 在接入真实 LLM judge 前，先补隐私审计、采样策略和人工确认流程。
