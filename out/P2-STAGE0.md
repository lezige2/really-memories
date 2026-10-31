# P2 Stage 0：池是否捞到（只读，n200 副本）

- 源 `kvmem/scale40k/n200/chat.db` sha `2d84aefda3c76ece`；K2 off/time off；现有 top20=`memory_service.retrieve(topk=20)`；未写码、未写库、未 commit。
- 有 target 38 条：**pool@20 = 32/38 = 0.8421**（<0.95，判停）

| 未进池 | target | 池内 rank | 全排序 rank | gate |
|---|---|---|---|---|
| q048 | 53 | 空 | 3 | below_threshold |
| q052 | 70 | 空 | 4 | below_threshold |
| q060 | 25 | 空 | 1 | below_threshold |
| q062 | 130 | 空 | 22 | pass |
| q063 | 144 | 空 | 26 | pass |
| q070 | 187 | 空 | 10 | below_threshold |

## 与 S2 五条对比

- S2：q048(全排3)/q052(4)/q060(1)/q062(22)/q063(26)
- 本次：q048(3)、q052(4)、q060(1)、q062(22)、q063(26)、q070(10)
- **不完全一致**：新增 q070（empty；全排序 rank10，cov 0.167<0.30）；pool 33→32。

## 代码漂移（关键）

- `tools/memory_service.py` mtime **2026-10-30T20:17:51**，晚于 `P2-POOL-REPORT`(16:28) 与 `S2-GATE-DIAG`(20:10)；
- 阈值常量仍是 2.0/0.30，但实现已变；q070 现在被 top1 门槛清空。
- 旧 P2/S2 数字不能直接与新跑对比，**需先重定基线**；本轮不据此改任何逻辑。

## 判定

- **STOP：pool@20=32/38=0.842 <0.95 → 池没捞到，精排无意义；不写 rerank、不进 Stage 1。另：未进池集合非 S2 原 5 条，新增 q070（empty，全排序 rank10），pool 33→32；memory_service.py 于 2026-10-30 20:17 变更，晚于 P2/S2 报告，需先重定基线。**

- 5→6 条未进池中，3 条被门槛清空（全排序 1/3/4），q070 新增清空（10），q062/q063 排 22/26；
- 瓶颈仍在“进池”（闸/排序），不在池内精排；不写 rerank、不进 Stage 1。
