# P0E 端到端结论（2026-10-30，research pass）

> 判定：**P0E 20+200 双过，research pass**；`--event-date` 仍默认 off，现网未迁移；启用需用户点头 + 备份 + dry-run + 回滚 + 迁移后重跑。
> 代码：`b1b0cd4`（v2.2）；chat_daily `8f21f101…`、k2_family `9b5082d1…`、answer_verifier `29b2cb6c…`、event_time `6d146575…`、memory_source `8d580bd1…`、chat_service `6c93febe…`。

## 1 20 档（S1-20B，副本，event on，v2.2，K2 auto）

| 项 | 结果 | 判据 |
|---|---|---|
| 81 | **81/81** | =81/81 ✅ |
| extra | **20/20** | ≥19 ✅ |
| MT20 | **18/20** | ≥18 ✅ |

- DB sha：跑前 `2f13183b…630d` → 跑后 `fab6d827…41ad`（评测写块，预期）；PID 11688，三 suite 同进程。
- MT20 仅 V9MT17/18“爱吃”旧值，无族键边界，不归 verifier/event_date。

## 2 200 档（S1-200，n200 副本，event on，v2.2，K2 auto）

| 指标 | 值 |
|---|---|
| recall@38 | **27/38 = 0.7105**（门槛 0.70，余量 0.0105） |
| recall@40 | **27/40 = 0.6750**（并列报，不达标） |
| pass | 0.325（13/40） |
| 旧值泄漏 / 拒答 | 0.15 / 0.2（负例拒答 100%） |
| P50 / P95 | 11.8s / 20.8s |
| 5xx / lock / dropped / truncated | 0 / 0 / 0 / 0 |
| K2 gate | 40/40 `count`，non_count=[] |

- **K2 在 200 档贡献为 0**（count 全关），只能写“不劣化”，不能写“有效”；
- 200 档 R@38 与 K2-off 0.711 基本相等，属 no-op。

## 3 写侧探针

- `明天下午三点开会` → event_date 次日、time 15:00、confidence high、basis_ts 非空；
- `每周三开会` → event_date NULL、periodic。

## 4 仍不做

- flag 默认 off；现网 `daily` 未迁移（uv=0、无 event 列）；
- 迁移需：用户点头 → 备份 → 副本 dry-run + 内容哈希比对 → 迁移 → 迁移后重跑 81/extra/MT20（v2.2 标签）→ 旧库备份留 1 周；
- 不把 200 的 0.7105 写成“K2 有效”；不因双过就默认开启。

## 5 下一步

- 等用户决定是否迁移/启用 event_date；
- 若启用，按上面流程；不启用则保持 off，P0 结论只作 research。