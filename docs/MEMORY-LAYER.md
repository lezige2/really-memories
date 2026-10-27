# MEMORY-LAYER（C 版记忆数据层设计说明）

> 范围：`tools/memory_service.py`（数据/规则层）与 `tools/chat_daily.py`（薄适配）的分层。
> 目标：把散在 chat_daily 里的记忆启发式收拢成**可单测、可解释、可替换**的一层；
> 不改研究件、不改冻结口径、外部行为不变。

## 1 分层

```
┌──────────────────────────────────────────────────────────────┐
│ tools（CLI / HTTP / QQ / 验收）  chat_daily REPL · chat_service│
│                                 run_c_acceptance · qq_bridge  │
├──────────────────────────────────────────────────────────────┤
│ chat app（薄适配，chat_daily.DailyApp）                       │
│   DB/KV 写入、块挂载与 M3 守卫、会话 save/load、个体日志、     │
│   对话窗 rollover、拒答/寒暄/联网的**调用编排**                │
├──────────────────────────────────────────────────────────────┤
│ memory_service（本层，纯 CPU 规则；零 GPU/零网络/无副作用）    │
│   extract_facts / plan_upsert / retrieve / needs_* / introspect│
├──────────────────────────────────────────────────────────────┤
│ engine / storage：kvshim(VK KV) · sqlite(memory_source/block) │
│   tools/kvslots.py · tools/memory_source.py · session_state   │
└──────────────────────────────────────────────────────────────┘
```

依赖方向单向：`tools → chat app → memory_service → engine`；memory_service **不 import**
chat_daily / kvslots，可独立单测（`tools/test_memory_service_cpu.py`）。

## 2 memory_service API（v1.0）

| API | 语义 |
|---|---|
| `tokens(text)` | 中文按字符 bigram、英文/数字按词、单字退化单字 |
| `retrieve(query, rows, topk, cfg, meta_fn)` | bigram + 标签加权 → 现行门槛 → topk；返回 `{id,score,coverage,text,hits,tag_hits}` |
| `extract_facts(text)` | 规则抽取：车牌/手机号/身份证/型号/金额/时间/地点/机构/偏好/陈述兜底；每条带 `status="未核实"` |
| `plan_upsert(facts, memories)` | 按「主体+谓词」去重：同值 `noop`；不同值 `update`（保留新值 + `supersedes=旧 id`）；新事实 `insert` |
| `needs_auto_remember(text)` | 是否静默写入（陈述“我的事实”且非问题/命令） |
| `is_fact_question(text)` | 无记忆命中时是否应拒答（个人事实问句） |
| `needs_lookup(text, control)` | 是否该走联网检索（时间敏感/需查证，记忆召回不联网） |
| `introspect(rows, meta_fn)` | 记忆清单：id/首行/长度/来源/标签/关联/时间/tokens |
| `score_row(row, toks, meta_fn)` | 单行相关分（供 1 跳关联扩展排序复用） |

`RetrievalConfig` 可调门槛：top1 命中 ≥2、覆盖率 ≥0.30；短查询（token ≤2）例外
（≥1 命中且覆盖 ≥0.5）；标签权重默认 +2/标签。chat_daily 仍用默认值，故行为不变。

## 3 哪些已结构化、哪些仍是启发式

**已结构化（数据层，可单测）**
- 事实抽取：`kind/subject/predicate/value/time/status(未核实)`；
- 去重/冲突：`subject+predicate` 键、`noop/update/insert`、`supersedes` + 时间戳；
- 检索打分与门槛：可配参数，不再散落在 UI/对话逻辑里；
- 内省：来源（manual/auto_summary/auto_archive）、标签、关联、token 数。

**仍是启发式（规则版，明确不承诺语义理解）**
- 抽取只覆盖常见句式；抽不到时退化为 `statement`（整句）；
- 实体/金额等用正则，允许误抽/漏抽，故一律标 `未核实`；
- 检索是字符重合度，不做同义/embedding；相似句靠“全挂 + 标签/时间区分”而非语义消歧；
- `needs_auto_remember` / `is_fact_question` / `needs_lookup` 是正则+长度阈值；
- rollover 摘要仍是模型生成（失败退化前 1500 字），摘要只作索引，原文归档块保留。

## 4 与 chat_daily 的边界（薄适配）

- chat_daily 仍负责：sqlite/KV 写入与回滚、`daily_memory_meta` 标签/关联、块挂载（M3
  守卫顺序）、`save_session`/rollover、个体日志事件、拒答文本与寒暄回复的编排。
- chat_daily 只调用 memory_service：`_retrieval_select` 的基础打分/门槛/topk
  （1 跳扩展留在 chat_daily，用 `score_row` 排序）、`_auto_remember_candidate`、
  `_should_search`、`_product_fact_question`、`memories()/introspect()`、`remember()`
  的 facts 记录与 `supersedes` 关联。
- **append-only 不变**：冲突更新不删除旧记忆；新记忆写入后把旧 id 记进
  `daily_memory_meta.related_ids` 并打 `supersedes` 标签，检索可通过 1 跳扩展同时看到新旧。

## 5 测试与行为保证

- `tools/test_memory_service_cpu.py`：28 checks（token/检索门槛/topk/标签/抽取/
  upsert 三态/判据/内省）。
- 回归：`test_chat_daily_cpu` 93/0、`test_retrieval_cpu` 36/0、`test_refusal_cpu` 31/0、
  `test_rollover_cpu` 33/0（另 `test_memory_graph_cpu`/`test_logging_cpu`/
  `test_openai_compat_cpu`/`test_chat_service_cpu` 复跑仍 0 failed）。
- 行为差异：**静默记忆/拒答/检索门槛口径不变**；唯一可见变化是“同一主体+谓词的重复陈述”
  不再重复建块（同值 noop），冲突值仍追加并在元数据记 `supersedes`。