# RULING-M5C2-B7-EXTRACT-RESUME（冻结 v1）：b7′ S4 抽取的分片续跑

> 裁定人：LEAD · frozen_rev=1 · frozen_at 2026-10-27T12:10:00+08:00 · 性质：**S4 阶段规则补充**（不改题面/rev7.2/读数件/一次性）
> 触发事实：`run_m5c2_b7_extract.py` 继承 `LIMIT_S=3600`；实测 ~12 s/前向 × 623 句 ⇒ 预计 ~6,600 s，将在约 300/623 处 `timeout_mid` 中止（fail-closed）。

## F1 事实

- extract 属 **S4（判据/抽取）**，不是一次性生成；**一次性已由 GEN `041b51eb7837aa90` 消耗**，与提取重跑无关（ABORT A12/A13）。
- 中止为**自然超时**（非崩溃）；RAW 逐句增量落盘，已完成 sid 可复核。
- 禁止在途 SIGKILL（ABORT A7）：必须让其自然结束/失败返回。

## R1 处置顺序

1. **不 kill**，等 `LIMIT_S` 触发、进程自然退出；
2. 冻结 partial RAW（shard1）与其 sha、sid 集合、完成数；
3. 以**新脚本** `run_m5c2_b7_extract_resume.py` 跑 shard2（剩余 sid），合并为完整 EXTRACT；
4. 冻结的 `run_m5c2_b7_extract.py` **不得修改**（只读）。

## R2 续跑合法性（写死）

- 剩余集合 = `SENTS 的 sid 全集 − shard1 已完成 sid`，**按 sid 集合计算，不得按内容/结果挑选**；
- 两片必须同 pins（GEN `041b51eb7837aa90`/140514、SENTS `c5a49a696b66f0c7`/288805、prompt `a6bc4f268f7711de`、model 8,988,110,240、dll `9edbafa150700614`、n_predict=384、greedy、同 engine 配置）；
- gate 仍 strict、**不带** `--allow-gui-procs`；
- 合并要求：sid 唯一、**623/623 完整**、顺序按 SENTS；任一重复/缺失 ⇒ 判失败，不得写 `completed`；
- 产物必须写 `resume_provenance{shard1{path,sha16,bytes,n_sids}, shard2{...}, sids_completed_in_shard1, sids_in_shard2, overlap:0, missing:0}`。

## R3 台账

记 attempt1 `timeout_mid`（LIMIT_S=3600，完成数、RAW sha）与 attempt2 `shard_resume`（shard2 sha、合并后 EXTRACT sha、完整性检查结果）；不改一次性会计。

## R4 边界

不改题面/rev7.2/READINGS/任何冻结件；不得据此调整判定口径；若续跑仍失败 ⇒ 记 `未接上`，不得反复续跑（≤1 次续跑）。
