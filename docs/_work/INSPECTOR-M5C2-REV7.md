# INSPECTOR-M5C2-REV7 —— rev7 判定层离线复算的独立审计

> 审计人：`rev7-auditor`（独立于实现方 `rev7-impl`） · 日期：2026-10-26
> 工作目录：`D:\llama-mem` · 任务板：`task-2`
> 冻结件：`docs/_work/PREREG-M5-C2-REV7.md` sha16=`32eaf82ca56600c4` / 5835 B / 88 行 / `frozen=true`
> 审计脚本（自写，不 import 执行者）：`kvmem/m2_visibility/m5/out/_rev7_audit.py`

## 0. 四态结论（先给答案）

**装置不合格。**

| 判据 | 结果 |
|---|---|
| §3 四道数值门槛 | **4/4 通过**（FP 2/46、漏判 4/41、parse_fail 1/261、new_miss 0）→ 按 §3 字面 `rev7_unusable=false` |
| §2 三条必须断言 | **A1 pass；A2/A3 FAIL，且我独立证明其可满足性 = 0** |
| 执行者产物保真度 | 我独立复算与其产物在 261 句 / 777 条 / 四门槛明细 / 逐句改动 / 作废清单上 **零结果差异** |
| 不合格根因 | **冻结件内部矛盾**：§2 N3 的定位定义与 §2 的 A2/A3 断言互斥；§0 对两例 FP 的「句内根本不存在」证据陈述与数据不符。**不是**执行者不忠实，**不是**数值不达标 |

据此不能写「通过」：若为了让 A2/A3 成立而自行加一条未冻结规则（例如剥离句首「患者：」标签、或把「患者」判为非值实体），那就是在执行中改写冻结 PREREG；执行者没有这样做（如实打印 FAIL），我也没有要求它这样做。是否接受「只按 §3 判数值达标、把 §2 断言记为 PREREG 缺陷并重冻结」属于 LEAD 裁决，我只给可满足性证明与证据。

## 1. 我做了什么 / 没做什么（独立性声明）

**做了**
1. 自写 `_rev7_audit.py`（57234 B，sha16 `6695a4b4de403870`）：从 PREREG §2 逐字实现 N1–N4（含 `normalize`、`value_tokens`、N3 定位门、N4 作用域、R1/R2/R3/R4+/derived、逐句聚合），**不 import、不复制、不执行**执行者脚本；在独立实现与交叉比对完成前没有读过 `run_m5c2_rev7_offline.py`。
2. 用冻结输入 `M5B4-JUDGE.json`（`6a3001b6ca23ef7d`）+ `M5B4-LEAD-RULING.json`（`9273ebc97aa1413a`）独立复算 rev5.1 基线（261 句 verdict + 777 条 per-item `absent`/`rule_hits`）与 rev7 字面结果。
3. 完成自己的复算后才阅读执行者脚本（1026 行）做作弊面审计；对执行者产物 `M5C2-REV7-OFFLINE.json` 做只读逐项比对。
4. 为核验「两次运行是否 byte 级一致」，**重跑了执行者脚本两次**（唯一副作用：其产物 mtime 变化；两次输出与既有产物完全同字节，见 §8）。这是本报告中我唯一触碰执行者产物的动作。

**没做 / 不能做**
- 未跑 GPU、未调模型、未联网；(b5) 一次未读（纪律要求）。
- 未从零重跑抽取层：`items[]` 取自冻结的 M5B4-JUDGE（本阶段定义如此）。
- 未对执行者脚本做形式化静态证明，只做全文模式扫描 + 关键段落阅读（导入面、判定函数、门槛、聚合、输出装配、常量区）。
- 未判定「PREREG 文本缺陷是否应触发重冻结/改版」——属 LEAD 决策；我未改 PREREG、金标、输入、执行者脚本与产物内容。

## 2. 冻结输入与基线复现（全部我自己算）

| 输入 | 期望 | 实测 | 结论 |
|---|---|---|---|
| `PREREG-M5-C2-REV7.md` | `32eaf82ca56600c4` / 5835 B / 88 行 / 无尾换行 / frozen=true | 全部符合 | ✓ |
| `M5B4-JUDGE.json` | `6a3001b6ca23ef7d` / 452456 B / 261 行 | 符合 | ✓ |
| `M5B4-LEAD-RULING.json` | `9273ebc97aa1413a` / 13195 B / `gold_counts` 46/41/164/10 | 符合，gold 计数逐项相等 | ✓ |

rev5.1 基线（用冻结 items[] 重算，零 GPU）：

| 指标 | 我的复算 | 与简报 |
|---|---|---|
| 逐句 verdict vs 已存 `verdict` | **261/261** 一致 | ✓ |
| 逐条 `absent` + `rule_hits`（777 条） | **777/777** 一致 | ✓ |
| derived 标记（246 条模型行重算） | 246/246 一致（13 例 True） | ✓ |
| 误判 FP | **7/46**：`b4-s1-q2-s01, b4-s1-q2-s07, b4-s1-q2-s09, b4-s1-q2-s15, b4-s1-q3-s03, b4-s2-q1-s01, b4-s8-q2-s02` | ✓ 逐 sid 相同 |
| 漏判 leak | **4/41**：`b4-s2-q2-s01, b4-s3-q4-s03, b4-s3-q4-s11, b4-s3-q4-s12` | ✓ 逐 sid 相同 |
| parse_fail | 1/261：`b4-s2-q2-s05` | ✓ |
| 已存 rule_hits 分布 | R3 454 / R1 24 / R4+ 3 / **R2 0** / R_derived 13 | ✓（R2 全量为 0，R2 的锚点选择在本数据上不可观测） |

结论：基线没有漂移；rev7 的 7→2 不是基线差异造成的。

## 3. rev7 独立复算（PREREG §2 字面 N1–N4）

| 门槛 | 阈值 | 我的复算 | 判定 |
|---|---|---|---|
| 误判 | ≤ 4/46 | **2/46**（`b4-s1-q2-s07`、`b4-s1-q2-s09`） | pass |
| 漏判 | ≤ 5/41 | **4/41**（不变，同基线 4 例） | pass |
| parse_fail | ≤ 2/261 | **1/261** | pass |
| 新增漏判（gold=fabricated 且 rev5.1 unsupported → rev7 supported） | = 0 | **0**（分母 35） | pass |

逐句变化共 **7 句**（其余 254 句 verdict 不变）：

| sid | gold | rev5.1 → rev7 | 我的成因 |
|---|---|---|---|
| `b4-s1-q2-s01` | support_present | unsupported → supported | N1（`8600元` vs `8,600 元`，旧二元覆盖 0.75） |
| `b4-s1-q2-s15` | support_present | unsupported → supported | N1（`手术费是8600元`） |
| `b4-s1-q3-s03` | support_present | unsupported → supported | N1（`手术费8600元`） |
| `b4-s2-q1-s01` | support_present | unsupported → supported | N2（旧 greedy 抽 `租车公司` 不在源文 → R1 门槛掉，不再 value_mismatch） |
| `b4-s8-q2-s02` | support_present | unsupported → supported | N2（旧 `地点是宠安医院` → 新捕获组 `宠安医院` 在源文 → 参与 R1，fuzzy 覆盖达标） |
| `b4-s1-q1-s02` | no_fact | unsupported → supported | N3/N4（12 条全作废 → 无 absent 可用） |
| `b4-s5-q1-s01` | no_fact | unsupported → supported | N3/N4（7 条全作废） |

- **作废条目：124/777 = 15.96%**，分布在 26 句（235 句无作废；单句最多 12 条）。
- `n_valid` 合计 653（present 214 / absent 439 / unverified 0），`n_unverified` 全数据为 0。
- 未修的 2 例 FP：`b4-s1-q2-s07`、`b4-s1-q2-s09`——`患者`（和 s07 的 `做的`）逐字存在于句中，N3 判 `valid=true`，R3 的 `未提及` 仍计入聚合。
- 归因汇总：7 例基线 FP 中 **N1 修 3（s01/s15/s03）、N2 修 2（s2-q1-s01、s8-q2-s02）、N3 修 0、R4+ 0、declared 0**；N3/N4 额外造成 2 例 `no_fact` 由 unsupported→supported（不影响任何门槛，方向上是更宽松）。

**我的数值 vs 执行者数值（关键项）**

| 项 | 我 | 执行者 | 一致 |
|---|---|---|---|
| FP | 2/46，sids=`s07,s09` | 2/46，同 sids | ✓ |
| 漏判 | 4/41，同 sids | 4/41，同 sids | ✓ |
| parse_fail | 1/261，`b4-s2-q2-s05` | 同 | ✓ |
| new_miss | 0/35 | 0/35 | ✓ |
| 逐句变化 | 7（5 修好 + 2 中性 + 0 改坏） | 7（同集合） | ✓ |
| 作废条目 | 124（16.0%） | 124（16.0%） | ✓ |
| rev7 binding rule hits | R3 435 / R1 8 / R4+ 3 | 435 / 8 / 3 | ✓ |
| rev5.1 rule hits | R3 454 / R1 24 / R4+ 3 / derived 13 | 同 | ✓ |

**敏感性（我自己做的消融，用于定位机制贡献）**

| 配置 | FP | 漏判 | parse_fail | new_miss |
|---|---|---|---|---|
| 字面 N1+N2+N3(+N4) | 2 | 4 | 1 | 0 |
| 去掉 N1 | 5 | 4 | 1 | 0 |
| 去掉 N2 | 4 | 4 | 1 | 0 |
| 去掉 N3 | 2 | 4 | 1 | 0 |
| N2 门改到 evidence 上 | 2 | 4 | 1 | 0 |
| 全作废句聚合改判 undecidable | 2 | 4 | 1 | 0 |

结论：**7→2 全部来自 N1（3 例）+ N2（2 例）；N3 对四门槛的净贡献为 0**（只改变 2 句 `no_fact`，sids `b4-s1-q1-s02`、`b4-s5-q1-s01`），N3 也没能修掉它本来要修的 s07/s09。

## 4. 断言独立判定（A1 / A2 / A3）

**A1 —— pass。** `normalize('手术费 8,600 元') = '手术费8600元'`；`coverage('8600元', '手术费8600元') = 1.0`（换一种覆盖顺序仍为 1.0，结论不依赖实现顺序）。

**A2 —— 在 §2 字面定义下不可满足。** 字符级证据：

| 字段 | 值 |
|---|---|
| sid | `b4-s1-q2-s07` |
| sentence（原文） | `患者：是在仁和口腔做的。` |
| sentence（normalize 后） | `患者:是在仁和口腔做的。`（NFKC 把全角冒号变半角） |
| item（normalize 后） | `患者` |
| 子串命中位置 | **0**（即句首第 0–1 字符） |
| window_coverage | **1.0** |
| N3 字面判定 | `valid = (子串命中) or (覆盖 ≥ 0.90)` ⇒ **true** |
| 断言要求 | `valid = false` |
| 可满足性 | **0**（要让它 false，必须改动 N3 定义或额外加未冻结条件） |

**A3 —— 不可满足。** `b4-s1-q2-s09` 句 `患者：右下第一磨牙。`（normalize 后 `患者:右下第一磨牙。`），`患者` 同样是位置 **0** 的子串；该句 13 个 `患者` 条目全部 `valid=true`，coverage=1.0。断言要求全部 `valid=false`，同样无法在字面 N3 下成立。

**§0 事实核对（独立于执行者）**

| sid | 条目 | 句内是否逐字存在 | 位置（normalize 后） | §0 的说法 |
|---|---|---|---|---|
| `b4-s1-q2-s07` | `患者` | **是** | 0 | 「句内根本不存在」✗ |
| `b4-s1-q2-s07` | `做的` | **是** | 9–10 | 「句内根本不存在」✗ |
| `b4-s1-q2-s09` | `患者` | **是** | 0（重复 13 次） | 「不存在或重复」：重复 ✓、不存在 ✗ |

即：**§0 的方向（R3 缺席词越界：非值实体条目的 `未提及` 被当作答案缺席计入聚合）成立，但它给出的证据陈述「句内根本不存在」与数据不符**；正因如此，N3（以「能否在句中定位」为唯一作废标准）对这两例必然放行，设计上就无法修复它们。要修必须换成「条目是否承载值/答案槽」的判据（例如排除句首「患者：」角色标签、排除虚词），而这在冻结 PREREG 里没有定义。

**N4 的冗余**：N3 已规定作废条目「不参与聚合、不产生 absent、不计入 unverified」，N4 第二条「作废条目的缺席词不进入聚合」是其子集；N4 首条「缺席词仅在 valid=true 条目上生效」在结果层面与「命中了但被聚合排除」等价（作废条目不进入任何聚合输入）。故 **N3 一旦成立，N4 对四门槛与所有 verdict 均无增量作用**——我的消融证实了这一点。

## 5. 与执行者产物逐项比对（`M5C2-REV7-OFFLINE.json`）

产物：sha16 `1f8f44b921e575fe` / 507657 B / schema `m5c2_rev7_offline_v1` / 261 句 / 777 条。
比对方式：我自己的复算结果 vs 产物 JSON，按键值逐条对比（不是看它的自报汇总）。

| 比对项 | 规模 | 差异 |
|---|---|---|
| 逐句字段 `verdict_rev7` | 261 | **0**（`verdict_rev7_diff` 为空） |
| 逐句字段 `gold/route/n_items/n_valid/n_invalid/n_absent/n_unverified` | 261×7 | **0**（`sentence_field_diff` 为空） |
| 逐条 `item` 文本 / `valid` / `item_verdict` | 777×3 | **0**（`item_diff` 为空；映射 present↔supported、absent↔unsupported、invalid↔invalid 后逐条相等） |
| 四门槛计数与 FP/leak/parse_fail/new_miss sid 明细 | 4 组 | 完全一致（4 组 sid 列表逐项相等） |
| `sentence_diff`（fixed/broken/neutral/unchanged_*） | 7 句 | 集合与每句 from→to 一致（5 fixed、0 broken、2 neutral） |
| `invalid_items` 清单 | 124 条 | (sid,item) 集合完全一致 |
| `derived_applicable` | 13 | sid 集合一致 |
| `baseline_reproduction` 块 | 261/261、777/777、246/246 | 与我的复算一致 |
| `false_by_reason` | 7 例 | fixed 标记 7/7 一致；attribution 命名（N1/N2/N3）一致 |
| provenance | prereg/items/gold sha16、`n_forward=0`、`n_sentences=261`、`rev7_ver=1`、`design_set/not_acceptance=true` | 全部一致 |
| 代码溯源 | 产物 `code_sha16=65ed60125528d5d6` / `code_bytes=44761` | 与实际脚本哈希/字节**一致** |
| 断言块 | A1 pass(value 1.0)；A2/A3 pass=false | 与我的判定一致；执行者未把 FAIL 包装成 pass |

**结论：结果层面零差异。** 我找不到任何「自报数字与实际不符」的地方；执行者产物在结果字段上是可信的。

## 6. 作弊 / 偏离审计（执行者脚本 `run_m5c2_rev7_offline.py`，1026 行）

| 检查点 | 结果 |
|---|---|
| sid 特判 | **无**。`if sid ==` / `sid in ...` 出现 0 次；`b4-…` 字面共 8 处，全部在 `EXPECT_FP`/`EXPECT_LEAK`（基线验证常量）、`ASSERT_A2/A3`、注释与自述字典中，判定函数从不读取 sid 定值 |
| 阈值 | 只有 0.80（R1、R4+ 长、R4+ 短 Jaccard）与 0.90（N3 窗口门），与冻结一致；无 0.85/0.95/0.75 等改阈值痕迹 |
| 词表 | 直接引用参考实现 `R5.NEG_WORDS` / `R5.ABSENT_MARKERS`、`R5.derived_plus`，未重定义、未增删 |
| 金标 | 只读 + 哈希强校验（漂移即 `SystemExit`）；无写金标代码 |
| (b5) | **未读取**；源码只在设计集说明字符串里出现 `b5`，无 b5 数据路径 |
| GPU / forward | import 仅 stdlib + `run_m5c2_rev5_offline` / `run_m5c2_rev5_1_offline`（纯离线判定模块）；无任何模型/网络调用；实测两次运行各约 0.27–0.29 s |
| 隐藏/额外分支 | 有一处 **`route == "empty_source" → unsupported`**（脚本 305/447 行）。该 route 在 261 行中不存在（只用 `model_extract` 246 + `abstain_check` 15），未触发，数值零影响。但它确实是 **PREREG §2 未冻结的额外聚合规则**，属「良性偏离」，须记录 |
| 额外输入 | 额外只读校验 `M5B4-SENTENCES.json`（`c349ca5a93192aac`，与 judge 内 `sentences_sha16` 一致）仅用于取句子原文；非 (b5)、不参与判定 |
| 前置硬门 | 先要求基线 261/261 + 777/777 + derived 246/246 + FP/leak 明细与简报一致，否则 `Exit(3)`——基线漂移时不会继续算 rev7 |
| 两次运行 | **byte 级一致**（见 §8） |

**判定：未发现任何「靠 sid 特判、改阈值/词表、改金标、读 b5、隐藏结果」的作弊。** 两处需记录的偏离：①`empty_source` 死分支（冻结外额外规则，零影响）；②作废条目的诊断 `rule` 标签按 N4 字面把 R3 抑制后落到 R4+（见 §7 差异清单；不影响任何结果字段）。

## 7. Schema 完整性与差异清单

**§4 完整性**：顶层 7 个必需字段齐（`rev7_ver/n_sentences/n_forward/design_set/not_acceptance/prereg_sha16/items_source_sha16/gold_sha16_current`，其中 `n_forward=0`）；逐条字段齐（`sid,item,evidence,valid,matcher_hit,coverage,numeric_ok,item_verdict`——用 `coverage` 满足 `dice/coverage`）；逐句字段齐（9 个）；读数齐（FP/leak 数与明细、`false_by_reason` 7 例归类、作废条目 124 及占比 0.1596、逐句对照全列含 0 例 broken、§2 三条断言逐条 pass/fail）；另有 `implementation_checks`（N2 门两类、N4 作用域共 5 项，全 pass）等附加字段，不损害 schema。

**差异清单（全部列出，含非结果差异）**

| # | 性质 | 内容 | 对 §3/§4 结果的影响 |
|---|---|---|---|
| 1 | 结果 | **无差异**（261 句 / 777 条 / 门槛 / 明细 / invalid / derived / baseline 全等） | 0 |
| 2 | 诊断字段 | 作废条目的 `rule`/`rule_hits` 标签：执行者按 N4 字面把 R3 限制在 valid 条目，16 个作废条目首命中记为 `R4+`；我保留 R3 命中但整条排出聚合。§4 未要求该字段 | 无（`valid`/`item_verdict`/verdict 全等） |
| 3 | 解释/实现 | R2 锚点集合：执行者把被 N2 门排除的实体 token 仍作为 R2 anchor；我在 token 层直接剔除。本数据 **R2 命中总数 0**，不可观测 | 无 |
| 4 | 额外规则 | `empty_source → unsupported` 聚合分支（冻结外），本数据不可达 | 无 |
| 5 | 额外输入 | 只读校验 `M5B4-SENTENCES.json` 取句文本 | 无 |
| 6 | 归因粒度 | 执行者 `rev7_causes` 用「只要有作废条目就加 N3」的粗归因，故 s1-q2-s01/s2-q1-s01 的 cause 含 N3；我的精确归因只标 N1/N2（那两句作废条目本来就没命中） | 无（诊断字段） |
| 7 | 断言 | A2/A3 均为 FAIL；我的可满足性证明与其 FAIL 一致 | 这正是「装置不合格」的判据 |

## 8. 两次运行 byte 级一致（我对执行者产物的实测）

在备份产物后直接重跑执行者脚本两次（`python -X utf8 run_m5c2_rev7_offline.py`，返回码 0）：

| 运行 | 产物 sha16 | 字节 | 耗时 |
|---|---|---|---|
| 改前已有产物 | `1f8f44b921e575fe` | 507657 | — |
| 第 1 次重跑 | `1f8f44b921e575fe` | 507657 | 0.27 s |
| 第 2 次重跑 | `1f8f44b921e575fe` | 507657 | 0.29 s |

两次输出与既有产物 **完全同字节**（不是「长得像」）。唯一副作用是产物 mtime 更新，内容零变化。我的审计脚本自身也连跑两次，输出 JSON sha16 均为 `de80cd38a7147f0f`（byte 级一致）。

## 9. 边界例

| 边界 | 数量 | 观察 |
|---|---|---|
| `route=abstain_check` | 15 | 全部保持 layer0（`abstain_ok`），items 均为空；N1–N4 不触碰 |
| `parse_ok=False` | 1（`b4-s2-q2-s05`，`item_without_evidence`） | 判 `parse_fail`，0 条目 |
| `derived=True` | 13 | 全部 → `undecidable`；gold 构成 no_fact 7 / support_present 6。注意其中 `b4-s5-q4-s02` 等「最」关键词句由于 `derived_plus` 的缺失集为空也被判 undecidable——这是 rev5.1 继承行为、非 rev7 改动，但它让 6 个 support_present 句免于计入 FP（须知晓的既有口径） |
| `items=[]` | 16 | 15 abstain + 1 parse_fail |
| 全部条目作废的句子 | 6 | 全部 gold=`no_fact`；2 句 unsupported→supported（`b4-s1-q1-s02`、`b4-s5-q1-s01`），4 句原本已 supported；无 support_present/fabricated 句受影响 → 四门槛零影响。这是 N3 的已知副作用方向（对 no_fact 更宽松），冻结件未规定「全作废应判 undecidable」 |
| 无作废条目的句子 | 235 | N3 不介入 |

## 10. 交付物与哈希

| 文件 | sha16 | 字节 | 说明 |
|---|---|---|---|
| `kvmem/m2_visibility/m5/out/_rev7_audit.py` | `6695a4b4de403870` | 57234 | 我的独立实现 + 审计脚本（自包含，不 import 执行者） |
| `kvmem/m2_visibility/m5/out/M5C2-REV7-AUDIT.json` | `de80cd38a7147f0f` | 55523 | 审计产物（输入/基线/rev7/敏感性/断言/边界/执行者比对/结论） |
| `docs/_work/INSPECTOR-M5C2-REV7.md` | 本文件 | — | 人读报告 |

被审计对象（未改动内容）：执行者脚本 `run_m5c2_rev7_offline.py` sha16 `65ed60125528d5d6` / 44761 B；产物 `M5C2-REV7-OFFLINE.json` sha16 `1f8f44b921e575fe` / 507657 B。

## 11. 最大的保留意见（给 LEAD）

四道 §3 门槛全过，执行者产物在结果层完全可信；但**冻结 PREREG 自身不成立**——§2 的 A2/A3 在其字面 N3 定义下可满足性为 0，§0 用来支撑 N3 设计的「句内根本不存在」与数据相反。若把「装置合格」定义为只满足 §3，则等于默认允许日后用一条未冻结规则去「凑」§2 断言；若坚持 §2 必须全过，则任何忠实实现都必然 FAIL。**建议 LEAD 明确：①本阶段按 §3 记「数值达标」；②PREREG §2 断言与 §0 归因需重冻结/更正，N3 不能作为修 s07/s09 的机制；③(b5) 的准入条件以哪个口径为准，须在文档里写死。** 这两句不写清，下一阶段会把「PREREG 缺陷」误当成「实现缺陷」或反之。