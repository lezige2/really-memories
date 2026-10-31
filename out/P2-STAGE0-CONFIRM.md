# P2 Stage 0 确认跑（HEAD 082b6de，只读）

- HEAD `082b6dea9edc3f4afb9f59957bdb730f64f5629d`（short 082b6de，matches 082b6de=True）
- DB `kvmem/scale40k/n200/chat.db` sha `2d84aefda3c76ece`；queries sha `653f877b46665737`；memory_service.py sha `0062679a426a7975`
- K2 off/time off，top20 现有检索；未写码、未写库、未 commit。

- **pool@20 = 32/38 = 0.8421**

| 未进池 | target | 池内 | raw top50 有 target | raw rank | 分类 |
|---|---|---|---|---|---|
| q048 | 53 | 空 | True | 3 | gate_cleared_top1 |
| q052 | 70 | 空 | True | 4 | gate_cleared_top1 |
| q060 | 25 | 空 | True | 1 | gate_cleared_top1 |
| q062 | 130 | 非空(20) | True | 22 | out_of_top20 |
| q063 | 144 | 非空(20) | True | 26 | out_of_top20 |
| q070 | 187 | 空 | True | 10 | gate_cleared_top1 |

## q070 单列

- raw retrieval：全库有 10 个候选，target 在 raw top50 的 rank=10（**非 raw 空**）；
- 但 `retrieve(topk=20)` 返回 **空**（gate=below_threshold）→ **被 top1 门槛清空**，不是“没捞到”。

## 其余 5 条同口径

- q048/q052/q060：raw top50 有 target（rank 3/4/1），retrieve 空 → **gate_cleared_top1**；
- q062/q063：retrieve 非空、target 在 raw top50（22/26）但 >20 → **out_of_top20**。

## 封存与教训

- 仍 **32/38=0.842** → **封存 P2**：粗排池不足，rerank 无从谈起；不写 rerank、不进 Stage 1。
- 旧 **33/38 作废/不可引用**。
- 教训（单列）：**pool/recall 数字必须绑 HEAD sha**；`memory_service` 10-30 20:17 变更使旧基线失效，禁止跨 HEAD 引用。
