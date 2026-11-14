# P1b 官方 C2 独立回放（23 条 held-out）

- 数据：`out/P1B-HELDOUT.jsonl` sha `f98419176ad311b10d0d1dff5e08fbd70899eb27349c65ada1417b160dbff0a4`（未改标签）
- 方法：仅调用公开接口 `p1b_subject.extract/decide/Sidecar`，按 setup 顺序重放；末句为受测语句；**未改实现、未起服务、未写现网**
- 标签映射：supersede→supersede；ask→ask；ask(ambiguous_subject/no_cue/negative_cue)→ambiguous；write/same_value→ignore

## 总分

| 组 | 匹配 |
|---|---|
| chain | 5/12 |
| answer_regression | 5/5 |
| negation | 1/6 |
| **合计** | **11/23 = 0.478** |

## 逐条

| id | 组 | 期望 | 实测 | 原始动作/原因 | 失败模式 | 判定 |
|---|---|---|---|---|---|---|
| P1B-C01 | chain | supersede | **supersede** | supersede / cue | decided | ✅ |
| P1B-C02 | chain | ask | **supersede** | supersede / anchor | decided | ❌ |
| P1B-C03 | chain | supersede | **ignore** | write / - | no_prior | ❌ |
| P1B-C04 | chain | supersede | **supersede** | supersede / cue | decided | ✅ |
| P1B-C05 | chain | ambiguous | **ignore** | write / - | no_prior | ❌ |
| P1B-C06 | chain | ignore | **ignore** | write / - | no_prior | ✅ |
| P1B-C07 | chain | supersede | **ignore** | write / - | extract_miss | ❌ |
| P1B-C08 | chain | supersede | **supersede** | supersede / anchor | decided | ✅ |
| P1B-C09 | chain | supersede | **ignore** | write / - | extract_miss | ❌ |
| P1B-C10 | chain | supersede | **ignore** | write / - | extract_miss | ❌ |
| P1B-C11 | chain | supersede | **ignore** | write / - | no_prior | ❌ |
| P1B-C12 | chain | supersede | **supersede** | supersede / anchor | decided | ✅ |
| P1B-R01 | answer_regression | ignore | **ignore** | write / no_setup | no_setup | ✅ |
| P1B-R02 | answer_regression | ignore | **ignore** | write / no_setup | no_setup | ✅ |
| P1B-R03 | answer_regression | ignore | **ignore** | write / no_setup | no_setup | ✅ |
| P1B-R04 | answer_regression | ignore | **ignore** | write / no_setup | no_setup | ✅ |
| P1B-R05 | answer_regression | ignore | **ignore** | write / no_setup | no_setup | ✅ |
| P1B-N01 | negation | ambiguous | **ignore** | write / - | no_prior | ❌ |
| P1B-N02 | negation | supersede | **ignore** | write / - | extract_miss | ❌ |
| P1B-N03 | negation | supersede | **ignore** | write / - | extract_miss | ❌ |
| P1B-N04 | negation | supersede | **ignore** | write / - | extract_miss | ❌ |
| P1B-N05 | negation | ignore | **ignore** | write / - | no_prior | ✅ |
| P1B-N06 | negation | supersede | **ignore** | write / - | extract_miss | ❌ |

## 错误分类

- **误覆盖（false supersede）**：`P1B-C02` —— C02『我又买了一辆车，车牌是沪C·22222』被判为 anchor supersede，**覆盖了车#1 的车牌**（正是要防的 cue 撞车原型）。
- **漏覆盖（missed supersede）**：P1B-C03、P1B-C07、P1B-C09、P1B-C10、P1B-C11、P1B-N02、P1B-N03、P1B-N04、P1B-N06。
- 其中 **7 条根因是抽取未命中**（extract_miss，未识别出 value/predicate）：P1B-C07、P1B-C09、P1B-C10、P1B-N02、P1B-N03、P1B-N04、P1B-N06 ⇒ 决策层根本没看到事实，退化为普通 write。
- ask/ambiguous 误判：无（无 / 无）。

## answer_regression

- 决策/写路径 5/5 均为 ignore（未写任何事实）；**但“是否仍拒答”属答案层，本回放未起服务，未覆盖**。

## 结论

**FAIL（11/23）**：不达通过线。三条硬缺陷：① C02 误覆盖（新主体被当成换牌）；② 否定/离开句（N02 离职、N03 搬走、N04 送猫、N06 退会员）与 C07/C09/C10 均**抽取未命中 → 漏覆盖**；③ C05 主体缺失未能 ask（因 prior 车牌未被解析）。
按令停在此处：不改实现、不调标签；C03『工作号』属不同槽位，写新事实其实合理，该条我标 supersede **可能过严**，交 B 裁定。