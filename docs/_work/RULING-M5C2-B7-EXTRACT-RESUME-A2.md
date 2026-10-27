# RULING-M5C2-B7-EXTRACT-RESUME-A2（等价性与披露要求 · 冻结 v1）

> 性质：resume/merge 的**等价性门禁与披露**；不改合并规则/限额/判据。依据：顾问 2026-10-27 对 resume 复核意见。
> 适用：shard1(407 句, 其中 388 前向 + 19 layer0) + shard2(216 句) → 合并 623/623。

## C1 会话不变性（合并前必须做，唯一会让整批作废的检查）

1) **pins 十项逐项断言**：model / dll / prompt / n_ctx / n_batch / temp / seed / n_gpu_layers / harness / judge_layer；
2) **负例**：篡改任一 pin ⇒ 校验必须 **exit≠0**（已实测：错误 GEN sha ⇒ rc=1，报 “does not match the frozen pin”）；
3) **20 句重跑抽检**：从 shard1 已完成的 388 前向句中随机抽 20 句，在**新会话**里按同一 prompt 重跑，与 shard1 的 `raw_out` **逐字节比对**；
   - 全同 ⇒ 会话不变性成立，可合并；
   - **任一不同 ⇒ 记「未接上」，不得合并**（不许"差异很小就算了"）。

## C2 layer0 异质性（19 句）

- 事实：19 句走 `abstain_check` 短路（items=[]、verdict=abstain_ok、无前向），与 forward 路径不同构；
- 处置：合并保留 `layer0` 标记；`readings` 必须**单独报一组**（b7 19/623；b6 对照 28/233），不得混入同口径池；本轮不额外重跑。

## C3 timeout 关闭方式

- 退出码 3、`abort_class=timeout_mid`、`signals_sent=false`、boot_id before=after、无 WATCHDOG/Minidump ⇒ **graceful timeout**，非外部 kill；此结论必须写进合并 EXTRACT/台账。

## D 归因与纪律

- `root_cause: timeout_limit_underestimated`（限值低于期望运行时间，计划错误；非装置故障）；
- 纪律：今后 `LIMIT_S = 实测吞吐(s/句) × 句数 × 1.5`；
- resume 限值 4200 s 对 216 句（实测约 1,944 s）足够；**若发生重试，重试计入同一限值**（不叠加）。

## E 合并后核验

- `verify_b7_extract_merge.py` 的 38 项必须包含：C1 抽检结果、C2 分层标记、C3 关闭方式证据；否则只验了"数量对"。
- 盲标隔离：resume 会再写 `out/`，盲标者全程不得读 judge 侧产物（doc-ledger/chain-repro 已声明）。
