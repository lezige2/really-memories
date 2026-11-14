# answer_alignment v2 · C2 独立复核

## 两栏（不藏）

| 口径 | 结果 |
|---|---|
| **原始正过** | **3/10**（pass: H06、H09、H10） |
| **原答案支持者的误拒** | **0/2**（支持者仅 H06、H10） |
| 20 负例被拒 | **20/20**；**fail_open 0** |

## 10 正例逐条（是否支持 target）

| id | 答案支持 target | decide | reason |
|---|---|---|---|
| P2-H01 | 否 | reject | no_aligned_block |
| P2-H02 | 否 | reject | no_aligned_block |
| P2-H03 | 否 | reject | no_aligned_block |
| P2-H04 | 否 | reject | no_aligned_block |
| P2-H05 | 否 | reject | unresolved_subject |
| P2-H06 | 是 | pass | aligned_block |
| P2-H07 | 否 | reject | no_value_for_asked_slot |
| P2-H08 | 否 | reject | no_value_for_asked_slot |
| P2-H09 | 否 | pass | aligned_block |
| P2-H10 | 是 | pass | aligned_block |

**注意 H09**：答案「阿泰」不支持 target（阿平），却判 `pass/aligned_block` ⇒ 属于“无支持也放行”，与误拒是另一类问题。

## 多事实检查（补 2 条）

| 场景 | 结果 |
|---|---|
| 车牌+电话，问电话 | **pass / aligned_block** ✅ 不误杀 |
| 车牌+电话，问车牌 | **reject / no_aligned_block** ❌ 误杀 |

## 根因（比数字更重要）

- 复现：**单事实**「你的车牌是京N·7K3Q0」+ 块 19（`张伟的车的车牌号是…`）→ 同样 reject。
- 块 19 可识别主体 `name:张伟`，查询主体为 `self`（我的）⇒ 主体不匹配 → `no_aligned_block`。
- 手机样例之所以过，是因为块 22 的主体**不可识别**（`韩峥一开始的手机号…` 不匹配 possessive 词表），恰好绕开该校验。
- ⇒ **0/2 是抽样偶然**：任何“我的X + 块带人名”的正确回答都会被误杀（P2-H04 车牌即此类）。

## 建议

- 正例口径应改为“全 10 条中，答案支持者里误拒数”，并**扩大支持者集合**（当前仅 2 条）后重算。
- 修 `decide`：块具名主体与 `self` 查询应按“句内实体/槽位”对齐，而不是主体字符串直接比对。

- 纯函数复核，未启服务/未写库/未 commit。