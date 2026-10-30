# P1b 官方 R2 判定（一次）

- R2 数据 `out/P1B-HELDOUT-R2.jsonl` sha `20ea3bc07a3640965fdf8ba6b886c5b2afaa5256e7ef3dab65d477faa2c049c7`（18 条）
- v1 回归 `out/P1B-HELDOUT-v1.jsonl` sha `f98419176ad311b10d0d1dff5e08fbd70899eb27349c65ada1417b160dbff0a4`（23 条，原标签）
- v1 重标版 `out/P1B-HELDOUT.jsonl` sha `ca06289ac25c6f5324dbdccbf67b8f3e3bd52bc09fee43eb200e939ac6392e4e`（C03→ignore）
- 方法：仅公开接口 `extract/decide/Sidecar`；setup 顺序重放、末句受测；**未改实现/未起服务/不写库**

## 结果

| 集合 | 匹配 | 误覆盖 | 漏覆盖 | ask 错判 | ambiguous 错判 | extract_miss |
|---|---|---|---|---|---|---|
| R2 (18) | **5/18** | 0 | 11 | 0 | 4 | 9 |
| v1 (23) | **13/23** | 0 | 8 | 0 | 6 | 0 |
| v1 重标 (23) | **14/23** | 0 | 7 | 0 | 6 | 0 |

R2 分组：chain 4/12；negation 1/6

## 通过门（B 的定义）

| 条件 | 结果 |
|---|---|
| 误覆盖 = 0 | **✅ 通过**（R2 无 false supersede；v1 的 C02 亦不再覆盖） |
| 否定/ambiguous 100% 询问或弃权 | **❌**（R2-N01/N02/N03/N05 仍 write/same_value） |
| 单主体链覆盖（supersede 全中） | **❌**（11 条漏覆盖） |
| 多主体互不影响 | **✅** |
| **总判定** | **FAIL —— 封存 P1b** |

## R2 逐条

| id | kind | 期望 | 实测 | 原始动作/原因 | 失败模式 | 判定 |
|---|---|---|---|---|---|---|
| R2-C01 | 换牌（同主体） | supersede | **ambiguous** | ask/ambiguous_subject | decided | ❌ |
| R2-C02 | 新买一辆（新主体） | ask | **ambiguous** | ask/ambiguous_subject | decided | ❌ |
| R2-C03 | 两号并行（手机/座机） | ignore | **ignore** | write/- | extract_miss | ✅ |
| R2-C04 | 两卡并行（工资卡/社保卡） | supersede | **ignore** | write/- | extract_miss | ❌ |
| R2-C05 | 两工位并行（上海/北京） | supersede | **ignore** | write/- | extract_miss | ❌ |
| R2-C06 | 主体缺失句 | ambiguous | **ambiguous** | ask/ambiguous_subject | decided | ✅ |
| R2-C07 | 旧值回写陷阱 | ignore | **ignore** | write/- | extract_miss | ✅ |
| R2-C08 | 同名两人（跨主体） | ignore | **ignore** | write/- | no_prior | ✅ |
| R2-C09 | 两猫并行·只改一只 | supersede | **ambiguous** | ask/ambiguous_subject | decided | ❌ |
| R2-C10 | 两会议槽（周一/周四） | supersede | **ignore** | write/- | extract_miss | ❌ |
| R2-C11 | 两出差槽（下周北京/下月上海） | supersede | **ignore** | write/- | extract_miss | ❌ |
| R2-C12 | 银行卡换行（同卡） | supersede | **ignore** | write/- | extract_miss | ❌ |
| R2-N01 | 否定·不是 | ambiguous | **ignore** | write/- | no_prior | ❌ |
| R2-N02 | 离开·已离职 | supersede | **ignore** | same_value/- | decided | ❌ |
| R2-N03 | 离开·已搬走 | supersede | **ignore** | write/- | extract_miss | ❌ |
| R2-N04 | 离开·已退卡 | supersede | **ambiguous** | ask/negative_cue | decided | ❌ |
| R2-N05 | 离开·停用号码 | supersede | **ignore** | write/- | extract_miss | ❌ |
| R2-N06 | 否定·不是该公司 | ignore | **ignore** | write/- | no_prior | ✅ |

## 要点

- **C02 撞车对已修**：R2-C02『又提了一辆车』不再覆盖车#1（false supersede = 0），但落到 `ambiguous` 而非 `ask`；C01『车牌换到…』因新句无显式主体也判 `ambiguous` 而非 `supersede`。两者都**安全**，但动作标签与期望不符。
- **extract 仍未通用**：R2 有 9 条 extract_miss（社保卡/工位/会议/出差/银行卡/座机/备用号/搬走/停用），说明 C4 的槽位修复未覆盖这些说法。
- **否定句仍漏**：N01 否定后仍 write、N02 判 same_value、N03/N05 extract_miss → 否定/离开未形成 supersede。
- answer_regression 5 条本回放只验证决策路径 ignore；**“仍拒答”需活服务，未覆盖**。

## 结论

**FAIL（R2 5/18、v1 13/23）**：误覆盖已清零，但漏覆盖 11 条、否定/ambiguous 门未过 ⇒ 按 B 规则**封存 P1b**，只跑这一次，不再重跑。