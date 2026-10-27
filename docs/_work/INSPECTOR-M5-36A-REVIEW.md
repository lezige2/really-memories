# M5 36A (a) 试跑：两臂结果、三方对齐与人判可用性（只读/未改产物代码/零 GPU 新调用）

**日期**：2026-10-26  **角色**：inspector（ADJ + JUDGE 执行 + 本报告）  **结论层级**：试跑可用性；**不是 M5 最终判决**。

## 1 输入与冻结坐标

- pairs `M5-36A-pairs.json = f0767d84 / 7,503`
- intent `M5-36A-intent-sealed.json = 9f140979 / 2,184`
- ADJ `M5-36A-adj.json = 1f5d7a54 / 10,653`
- JUDGE `M5-36A-judge.json = bff8a34b / 27,935`
- REVIEW `docs/_work/REVIEW-M5-36A-blind.json = 39d1d248 / 9,143`
- `m5_ground.py = 86b7c501 / 18,496`（**冻结，未修改**）
- 模型臂：pairs `aa9e6106 / 7,851`；intent `6e4656d3 / 1,373`；pilot `b6f086bc / 22,809`
- 对齐件：`M5-36A-alignment.json = b38c17f7 / 38,475`；pilot 更新后 `f86ecbfd / 7,868`

## 2 规则臂

30 对中 **12 对 `orig == rewrite`（基线）**、**18 对真改写**。主口径只算 18 对；以独立盲标 REVIEW 为真值。

| 块 | ADJ/REVIEW | JUDGE/REVIEW | leak | false |
|---|---|---|---|---|
| **rewrite18（主）** | **18/18** | **18/18** | **0/5**（事件 `[]`） | **0/13**（事件 `[]`） |
| baseline12 | **12/12** | **10/12 = 83.33%** | 不设分母 | 不设分母 |
| all30（仅存档） | **30/30** | **28/30** | 旧口径 2/15（P13/P25） | 0/15 |

- `excluded[] = []`；不报单一准确率。
- baseline 不一致恰为 **P13/P25**；all30 的 2/15 只作旧口径并列留档，**不是真灵敏度**。

## 3 三方对齐与 JUDGE 缺陷

**ADJ vs REVIEW：0 mismatch（30/30）。JUDGE vs REVIEW：2 mismatch，恰为 P13/P25。**

| pair | 文本 | ADJ | JUDGE | REVIEW | JUDGE facts |
|---|---|---|---|---|---|
| P13 | 我住在杭州西湖边。 | unsupported | **supported** | unsupported | `[]` |
| P25 | 我只喝龙井茶，不加糖。 | unsupported | **supported** | unsupported | `[]` |

**LEAD 裁决（已落盘 `M5-36A-alignment.json.lead_ruling`）**：
1. P13/P25 上 ADJ 与 REVIEW 正确、JUDGE 错误；**不修改冻结的 `m5_ground.py 86b7c501`**，记 **`judge_defect: no_fact_to_supported`（2 例）**。
2. **判据本身不作废**；判据定义正确、缺陷在判定器实现 ⇒ **“判据可用、判定器有缺陷”**，定级 **阻塞（阻断全量）**。
3. 两率主口径维持 **rewrite18：leak 0/5、false 0/13**；all30 与 baseline12 只并列留档。
4. 模型臂 accepted 16（leak 0/5、false 0/11、ADJ/JUDGE/intent 三方 0 mismatch）+ **14/30 verbatim_copy**；分母 5 <10，只作装置可用性。

## 4 模型臂

- **30 次调用 → accepted 16 / CAND 剔除 14**；剔除理由全为 **`verbatim_copy`**（模型原样复读；CAND 冻结、未补生成、未按 JUDGE 挑选）。
- accepted：intent unsupported 5 / supported 11；ADJ、JUDGE 均 **5/11**；**三方 0 mismatch**。
- **leak 0/5、false 0/11、excluded[] = []**；leak 分母 5 <10，**样本量不足以给区间，只作装置可用性**。
- **装置/模型行为发现**：模型面对“含虚构事实且不得增删事实”的句子倾向原样复读（14/30）；这是装置行为，**不是判定器结论**，未据此改分母或补生成。
- 装置自证：36 层读回 + `offloaded 36/49` + `vulkan_imported=true`，峰值 **7.3924 GiB**，`model_calls=30`。

## 5 可用性清单（逐条）

| 项 | 状态 | 说明 |
|---|---|---|
| 装置自证 | **通过** | 36 层读回、36/49 offload、Vulkan 导入、峰值 7.3924 GiB |
| 规则臂 ADJ/JUDGE | **完成** | 30 对全部盲标；ADJ 先封存，后才读 intent/JUDGE |
| 模型臂 ADJ/JUDGE | **完成** | accepted 16；14 条 verbatim_copy 在生成端剔除 |
| 三方对齐 | **完成** | ADJ/REVIEW 30/30；JUDGE/REVIEW 28/30；P13/P25 |
| **判定器可用性** | **未全绿** | **阻塞项 = JUDGE `no_fact_to_supported`（P13/P25，2 例）** |
| pilot 可用性 | **未通过** | 不写“试跑可用性通过”；不写最终判决 |

## 6 下一步建议

1. **另立 M5 judge v2 预登记**，把 **J1–J6 修订**中的 no-fact 分支写死：`facts=[]` 不得直接 `supported`，应走 `no_fact`/`unknown` 或要求显式“源文无该硬事实”的独立判据；P13/P25 作为回归钉。
2. v2 预登记同时固定本次三条口径：**基线/改写分块**、**accepted 分母 + verbatim_copy 生成端剔除**、**ADJ/JUDGE/REVIEW 三方盲标**；样本量目标 ≥10/臂，否则只报装置可用性。
3. 规则臂 v2 的 rewrite18 主口径（leak 0/5、false 0/13）可引用；**all30 的 2/15 不得单独引用为改写漏判率**。
4. 模型臂仅作装置发现；**不得**把 14/30 verbatim_copy 解释为“模型不会改写/判定器通过”。