# INCIDENT-M5C2-REV7.2-FREEZE（冻结后写盘事故 · 登记件）

> 性质：**事故登记**（非裁定）；关联 `M5C2-REV7-2-FREEZE.json v1.2`、`M5C2-REV7-2-P4-DIFF.json`、`M5C2-REV7-2-C5-ABLATION-FP.json`、`M5C2-REV7-2-CLEANBLIND.json`（待出）。
> 记录人：LEAD · 发现时间：2026-10-27T10:46+08:00 · 处置完成：2026-10-27T11:00+08:00

## 1 事件

rev7.2 首次冻结（`d94630da3270a05a`，10:43:37）之后，执行方 rev7-impl 仍在写盘：

| 件 | 冻结时 | 冻结后被观察到 |
|---|---|---|
| `run_m5c2_rev7_2_offline.py` | `7f97ea6c47b9fa5f` / 38,119 B | **`17c8e32a16b75947` / 38,200 B**（+81 B），mtime 10:44:59 |
| `M5C2-REV7-2-DEV.json` | `a1137c5cd47a8aaf` / 870,903 B | 曾在 10:43:55 出现 `9f0c51bf6252a05b` / 906,952 B；最终回到 `a1137c5c`/870,903 B，mtime 10:45:56 |

**事故窗口**：约 10:42:36（独立审计产物落盘）至 10:45:56（DEV 最后一次写盘）。

## 2 发现与处置

1. **发现**：LEAD 巡检发现 DEV mtime 晚于 FREEZE；rev7-auditor 复核时亦报告"外钉瞬时不匹配"。
2. **处置**：LEAD 立即 `interrupt_agent(rev7-impl)` 停止写盘；随后用**当前脚本**在盘重跑：DEV **逐字节复现 `a1137c5cd47a8aaf`**，verdict map `5afa1f3e02cf4b21` 不变、A1 7/7、FP 2、leak 0/29、`all_pass=true`。
3. **独立复核**：rev7-auditor 对冻结版 DEV 逐 sid 复核 326/326 **diff=0**；LEAD 另出 `M5C2-REV7-2-P4-DIFF.json`（记录两输入 sha、命令、时间戳、结果）。
4. **重钉**：FREEZE v1.1（`36d9d3e1`）→ v1.2（`bac1285dec4eb866`），承重 pin 明确为 **verdict map `5afa1f3e02cf4b21`**；文件级 sha 仅作证据索引，重算一致即闭合。

## 3 影响面

| 结论 | 是否重开 | 说明 |
|---|---|---|
| rev7.2 机制语义（M1/M2/M3′） | 否 | 脚本改动前后重跑 verdict 逐字节一致 |
| dev 断言 A1/A2′/A3/A4/T1–T4 | 否 | 在钉定 DEV 上复算通过 |
| 独立实现 diff=0 | **是（按顾问 C1/C2 重做）** | 见 P4-DIFF 与 CLEANBLIND（清盲审计，进行中） |
| b5 的「擦边」/b6 的「未接上」 | 否 | 与本事故无关 |

## 4 根因与整改

- **根因**：冻结件的"冻结"只是登记，不是访问控制；执行方在同一目录继续写盘，无互斥。
- **整改（已生效）**：对 rev7.2 的脚本、DEV/AUDIT、FREEZE、b7 题面与题面 pin **设置 `IsReadOnly`**（见 §5）；后续任何修改必须显式解冻（先清只读、改完重钉）。
- **流程**：冻结后执行方不得再写该目录；LEAD 巡检以 `mtime + sha + declared` 三记核对。

## 5 只读清单（2026-10-27T11:00 设置）

- `kvmem/m2_visibility/m5/run_m5c2_rev7_2_offline.py`
- `kvmem/m2_visibility/m5/run_m5c2_rev7_2_offline_audit.py`
- `kvmem/m2_visibility/m5/out/M5C2-REV7-2-DEV.json`
- `kvmem/m2_visibility/m5/out/M5C2-REV7-2-DEV-AUDIT.json`
- `kvmem/m2_visibility/m5/out/M5C2-REV7-2-FREEZE.json`
- `kvmem/m2_visibility/m5/out/M5C2-B7-QUESTIONS.json`
- `kvmem/m2_visibility/m5/out/M5C2-B7-QUESTIONS-FREEZE.json`
- `docs/_work/RULING-M5C2-B7.md` / `RULING-M5C2-B7-A1.md`

## 6 证明链（冻结态 = 验证态）

1. `M5C2-REV7-2-P4-DIFF.json`：在**最终** DEV `a1137c5c` × AUDIT `977eff68` 上重算 diff=0（含命令/时间戳）；
2. `M5C2-REV7-2-CLEANBLIND.json`：清盲实现者在不看 A2′ 的条件下自行选择读法，并报两种读法 diff（顾问 C2）；
3. 上述两件 + 独立只读复核，共同支撑"冻结的记录 = 实际被验证的状态"。