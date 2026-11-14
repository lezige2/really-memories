# P1 · audit 服务级验证（副本）

## ask：符合预期

- 服务 `--audit`，问「我的猫叫什么？」→ 返回「你的猫叫豆豆」、`block_ids=[14]`。
- `out/audit` 新增 **2 条**，**同一 trace_id `1174ebd66697…`**：
  - `retrieve`：decision=selected、reason=off、block_ids=[14]、latency 5.78ms
  - `answer`：decision=natural、block_ids=[14]、latency 2911ms、query_sha16/answer_sha16 均有
- **无原文**（`猫叫豆豆` 未出现在 JSONL 中）。
- 小缺口：`retrieve` 事件的 `query_sha16` 为 `None`，只有 `answer` 带 query 哈希。

## archive / reheat

- archive：**1 条**（archived/auto_archive）✅
- **reheat：2 条**（`restore/no_newer` + `restore/reheat_execute`）❌
- 即 C4 声称的“reheat 只 1 条合并事件”**未实现**，plan 与 execute 各写一条。

## 结论

ask 审计合格；reheat 去重未做，需合并 plan/execute 两条（或只在 execute 落一条）。