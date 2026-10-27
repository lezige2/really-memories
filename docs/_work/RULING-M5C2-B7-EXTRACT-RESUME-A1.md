# RULING-M5C2-B7-EXTRACT-RESUME-A1（resume 脚本唯一一次小修授权 · 冻结 v1）

> 性质：对 `run_m5c2_b7_extract_resume.py d29e1019533310fe` 的**唯一一次**解冻授权；不改变原裁定的合并规则/限额/gate 纪律。
> 触发：首次执行在 `verify_pins` 处 exit 1（**未载模型、未写任何文件**；GPU 未占用；partial 封存目录未动）。根因：(1) CLI 缺 `--expect-gen-bytes/--expect-sents-bytes`；(2) 调 `EX.verify_pins()` 时未传入 CLI 期望值，落到 b7 动态常量 None 上崩溃。

## R1 允许的改动（仅此）

1) 增加两个**纯校验**参数 `--expect-gen-bytes`、`--expect-sents-bytes`；
2) 调用改为 `EX.verify_pins(expect_gen_sha16, expect_gen_bytes, expect_sents_sha16, expect_sents_bytes)`；
3) 其余一律不动：`RESUME_LIMIT_S=4200`、strict gate（无 opt-in）、shard2=按 sid 集合补集、合并强校验（唯一/623/顺序）、INCOMPLETE 语义、不写 completed。

## R2 验收

- dry-run 重跑（含 623/623、duplicate、missing）；
- 真实模式需先通过 **pins preflight**（不载引擎、不写盘）再进入 GPU；
- 新 sha 报 LEAD 后重钉 `M5C2-B7-EXTRACT-RESUME-SCRIPT-FREEZE.json` v2 并恢复只读。

## R3 边界

- 本次为**唯一一次**解冻；若再失败 ⇒ 记 `未接上`，不得第三次；不得用 wrapper 绕过冻结实现（B 方案不采用）；
- 合并产物必须写 `resume_provenance`，partial 封存目录 `_aborted_20261027T130048/` 不动。
