# M5C2-B7-READINGS 变更记录

## v1 -> v2（授权解冻，唯一一次）

- 时间：2026-10-27T11:45:00+08:00
- 原因：RULING-M5C2-B7-A4.md（sha16 8b7a7d47d6b30000 / 2,460 B）修订 A3 R2/R3：
  A/B 两读并列，结论取较差档（severity: 未通过 > 擦边 > 未接上 > 达标），
  headline 必须用较差读；并新增必写披露（A 漏报 1 例 b5-s4-q1-s01；
  B 多检 2 句含 1 真漏判）。
- 解冻操作：清除脚本与 FREEZE 两件的只读位（IsReadOnly=false / chmod 666）。
- 旧 v1：`run_m5c2_b7_readings.py 5fae02247f8103b2 / 22,157 B`；
  FREEZE `M5C2-B7-READINGS-FREEZE.json 1aa290e4c7b3af4a / 1,412 B`。
- 新 v2：见同目录 freeze v2 回执（sha16/字节由 LEAD 重钉）。
- 其余 b7 脚本与 rev7.2 未改动。

## v2 -> v3（授权解冻，唯一一次；A5 判定映射修正）

- 时间：2026-10-27T12:30:00+08:00
- 原因：RULING-M5C2-B7-A5.md（ab06e8be828897c5 / 2,281 B）：
  达标 = 两率 Wilson 上界 ≤15%/≤20% 且分母≥20（点估计仅用于判未通过）；
  A2 的 8.67% 仅为 n_fp=150 示例，不得硬编码；按 n_fp=148 导出 FP≤13/148=8.78%。
- 解冻操作：清除脚本与 FREEZE 只读位。
- 旧 v2：`run_m5c2_b7_readings.py 8a8174aa08a850fb / 24,707 B`。

## v3 -> v4（授权解冻，唯一一次；C2 layer0 单列）

- 时间：2026-10-27T13:45:00+08:00
- 原因：RULING-M5C2-B7-EXTRACT-RESUME-A2-A1.md（ecbebaa82448e0fb / 636 B）：
  layer0 abstain_check 实际 42 = shard1 19 + shard2 23（不是 19），n_forward=581；
  readings 须接受 DECIDE 的 abstain_ok 判定、四档外单列，且不混入两率池。
- 解冻操作：清除脚本与 FREEZE 只读位。
- 旧 v3：`run_m5c2_b7_readings.py 852a04eacd8be1bd / 26,733 B`。
