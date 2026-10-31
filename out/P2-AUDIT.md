# P2 三审计 + 关键消融（HEAD 5372660，只读）

- DB `kvmem/scale40k/n200/chat.db` sha `2d84aefda3c76ece`；脚本 `out/p2_new_coarse.py` sha `7e20c2fdd49a682a`；未写库、未 commit。

## 1 泄漏审计

- seed 只用 **query + 块文本**（`p2_new_coarse.py:104,114`）；**不读 target id / 答案值 / tags / heldout**；target 仅用于结果记录（157+），heldout 仅在排名后做 sanity（193-204）。
- target 在 raw top50：**38/38**；raw top20：**36/38**；查询文本含期望值：**0/38**。
- 实体用“块文本前缀 2/3 字”全库公共集合，非按 target 构造；不读 `memory_meta.tags`。

## 2 关键消融

| 臂 | 定义 | pool@20 |
|---|---|---|
| gate_top20 | 现有 retrieve(top20)+coverage 闸 | **32/38 = 0.842** |
| raw_top20 | raw top50 直接取前 20（无 BM25、无闸） | **36/38 = 0.947** |
| bm25_top20 | raw top50 → BM25+实体/谓词 → top20 | **38/38 = 1.000** |
| raw_top50 | 仅 seed 覆盖（非池） | 38/38 |

- 撤闸/取20 救回：q048、q052、q060、q070（+4）
- BM25 额外补：q062、q063（+2）

## 3 结论（如实）

- **提升主要来自撤闸/取 raw top20（32→36）**，不是 BM25；
- BM25 只把 q062/q063 从 22/26 拉进池（36→38）；raw20 单独 0.947 未过 0.95，故 **BM25 是达标必要条件、但不是主因**。
- 原 spec 的“增益主要来自 BM25”表述据此更正。

## 4 边界

- 单库单次只读；未接产品/未写库/未 commit；seed 必须含 target（本轮 38/38）。

## 5 新 held-out 20 补充（10 target）

- `out/P2-HELDOUT-20.jsonl` sha `f0cf9eaf20b6b348`；target 不复用 Q40/S2。
- raw50 recall **10/10**；raw50→top20 **10/10**；BM25 臂 **10/10**。
- - raw50 10/10：上限不受 seed 限；BM25 相对 raw20 无增量（不记功臣）。
- 10 条负例：**待测**（需服务/模型，未测）；未写库、未 commit。
