# M1.8 终审报告（inspector）：四处已按判据落地、A1–A17 17/17、真实库不变差

- **作者**：inspector（只读检测员，task-17）
- **判法**：四态闭集（通过/未通过/未接上/未做）；真红=断言在坏实现上变红；`no_worse` 以真实库 8 探针为准
- **性质**：本文件只写复核结论；**未改代码/产物/台账**。独立复跑全部在系统临时目录（零 GPU）
- **上游**：M1.8 判据与施工单见 `docs/_work/M1.8-CONFLICTS-inspector.md`（`fb50943e25bbd847` / 28,930 B，§4.6 已追加 P1 缺口）；M18-3 重出版规格见 `docs/_work/INSPECTOR-M18-3-RESPEC.md`（`e479483ca6bbd43b` / 18,825 B）；M2 加固复核见 `docs/_work/INSPECTOR-M2-ACCEPT.md` §7

## 0 输入锚（全部现算，复核时点 2026-10-25 19:54）

| 对象 | sha16 | 大小 |
|---|---|---|
| `tools/retrieval.py` | **`43f660196ab90a14`** | 18,197 B（M18-3-B 已落） |
| `tools/analysis.py` | **`49e91c7bd3dd32ef`** | 18,382 B（自 M18-2 起未再变） |
| `tools/test_retrieval_judges.py` | **`be3d93bfca7bc39d`** | 15,108 B（A1–A17） |
| `kvmem/chat.db` | `237d8e1f5de9a382` | 110,592 B |
| `out/M18-A-after-m18-3v2.json` | `9a9483861eb146bd` | 5,592 B（17/17） |
| `out/M18-A-pre-M18-3v2.json` | `79456d7762d3c300` | 5,660 B（14/17，红 A8/A12/A15） |
| `out/M18-PROBES-after-m18-3v2.json` | `5f7c74adc17f407e` | 7,092 B |
| `out/M18-CMP-m18-3v2-vs-prev.json` | `f2c6ea12c8be536a` | 5,112 B（0/8/0） |
| `out/M18-CMP-m18-3v2-vs-before.json` | `69572f127b720bc2` | 4,134 B（3/5/0） |
| `m1/LANDED-m18-3v2.json` | `766f44d645ce504a` | 7,868 B（11 文件、`spec=e479483c`、`invalidates=2bb61058`） |
| `evidence/M18-3-INVALIDATES.md` | `2bb610586b0c9b42` | 2,154 B（旧两条改法判作废） |

五处改动同属一批：M18-2（analysis 收紧）、M18-1（`s>0 or prop`）、M18-4（`keep=out[:1]`）、M18-3-B（`prop_gated`）。**四阈值 `1.30/0.35/0.55/1.10`、`INDEX_VERSION=5`、`ANALYSIS_VERSION=4` 全程未动。**

## 1 复核方法（不读 executor 的结论当证据）

1. **我自己跑断言**：`python tools/test_retrieval_judges.py --out <temp>`，改后盘面跑一遍；再把 `retrieval.py` 换成 `_before/retrieval.py@b89fb2004f7aa69a`、`analysis.py` 换成 `_before/analysis.py@49e91c7bd3dd32ef`（即 M18-3 落盘前）**用同一份新测试文件再跑一遍**，验证"断言在旧代码上确实红"。
2. **diff 范围**：`diff -u _before/retrieval.py@b89fb2004f7aa69a tools/retrieval.py`；`cmp` 比 `analysis.py` 字节；grep 四阈值/版本/cov 分母。
3. **真实库探针**：`probe_m18_8.py --tag verify --out <temp>` 自己跑一遍（`chat.db` 只读拷贝、`build_index` 在拷贝上），再用 `P8.judge` 对 `M18-PROBES-after-M18-4.json` 判 `same/better/worse`，与 `f2c6ea12c8be536a` 逐条对照。
4. **r2 字段复核**：直接读 `out/M2-ACCEPT-r2.json` + `planner.py` / `accept_m2_real.py` 代码路径（见 §5 与 `INSPECTOR-M2-ACCEPT.md` §7）。

**只读自证 + 一处自伤披露**：除本文件外未在工作区写任何文件。**披露**：我用 `probe_m18_8.py --compare` 复核时，该脚本把对照结果按默认路径写进了 `kvmem/m2_visibility/m1/out/M18-PROBES-cmp.json`（19:53:31，5,154 B）；我发现后**立即删除**，未改任何既有产物、未登记；其读数即 §4 的 0/8/0。此后所有独立复跑产物都只落系统临时目录。

## 2 A1–A17 独立复跑（我自己跑的，不是读 executor 产物）

| 盘面 | n_pass | fail | 与 executor 产物 |
|---|---|---|---|
| **改后**（`retrieval.py 43f66019`） | **17/17** | `[]` | 与 `9a9483861eb146bd` 一致（我另存的 temp 产物 `n_pass=17`） |
| **改前**（`retrieval.py b89fb200` + 新测试文件） | **14/17** | **`A8, A12, A15`** | 与 `79456d7762d3c300` 一致 |

⇒ **断言承重成立**：同一套 A1–A17，在落地前的代码上**确实红 A8/A12/A15**（不是事后补绿、也不是只读产物）。
- A8：`公积金` 搜索 `[1]`（答成奖金）→ 改后 `[]`；
- A12（同构正例）：`[1]` → `[]`；
- A15（张冠李戴两向）：`(a)` 奖金块问住址 `[1]`、`(b)` 奖金+住址块问公积金 `[1]` → 改后都是 `[]`。
- A13/A14 改前改后都绿 —— 它们是"不许杀"的**护栏**（A13=P2 合成版、A14=同义异锚），不是区分器；我在规格 §4.3 就写明这一点，这里不夸大。
- 产物 `thresholds` 字段实测 `1.30 / 0.35 / 0.55 / 1.10` 未变（A11 亦绿）。

**测试文件改动范围**（`407835e279bb1aed → be3d93bfca7bc39d`，−2/+66 行）：只改模块 docstring 首行与产物 `schema` 串（`m18_judges_test_v1 → v2`），**A1–A11 的函数体一字未动**，新增 A12–A17 及 `CASES` 条目。阈值断言（A11）本身未改。

## 3 落地范围（diff / 字节 / 版本）

- `tools/retrieval.py` vs `_before/retrieval.py@b89fb2004f7aa69a`：**恰好 1 个 hunk，+6/−5**，位置在回退处决块（hunk 覆盖 L292–302）。文件里**两个** `if used_fallback:`：**L293（处决块）改了，L303（信号标记块）未动**（在 hunk 之外）。
- 改动语义：`need = 1 if (allowed≤2) else 2` + `if hits < need` → `prop_gated = bool(want_prop) and allowed is not None and sid in allowed` + `if not prop_gated and (hits < 2 or cov < COV_MIN)`。**只换例外的对象**，未新增表、未读正文。
- `tools/analysis.py` 与 `_before/analysis.py@49e91c7bd3dd32ef` **`cmp` 字节一致**，sha16 仍 `49e91c7bd3dd32ef`。
- 四阈值、`INDEX_VERSION=5`、`ANALYSIS_VERSION=4` 均未变；`cov_den = sum(idf_map.values()) + len(absent) * idf_absent` 未变（**没有把 bigram 塞回分母**，旧变体 A 没有复活）。
- 索引身份：`kvmem/chat.db` 的 `index_meta = {docs:2, version:5, analysis:4}` ⇒ `is_stale()` 返回 False。**不需要重建索引**：M18-2 只改查询侧 `PROPERTIES`/锚定判定；建索引的表（`term`/`facet`/`value_kind`）语义未变；`attr` 表全仓**只写不读**（`retrieval.py` 仅 DDL/DELETE/INSERT，`chat.py` 无读点），其行即使陈旧也不参与检索。`docs=2` 是遗留键（`M1.8-CONFLICTS-inspector.md` §4.3 已记）。

## 4 真实库 8 条（我自己跑 `--compare`）

我以 `M18-PROBES-after-M18-4.json` 为 before、我自己现跑的 `verify-probes.json` 为 after（`db 237d8e1f5de9a382`、`retrieval 43f66019`、`analysis 49e91c7b`）：

| id | 查询 | before | after | judge |
|---|---|---|---|---|
| P1 | 我的地址是什么 | 块3 | 块3 | same |
| P2 | 我的住址是什么 | **块5** | **块5** | same |
| P3 | 我生日是哪天 | 块3 | 块3 | same |
| P4 | 我车牌颜色是什么 | ABSTAIN | ABSTAIN | same |
| P5 | 我住在哪 | 块5 | 块5 | same |
| P6 | 我女儿什么时候生日 | 块10 | 块10 | same |
| P7 | 我女儿生日是哪天 | 块10 | 块10 | same |
| P8 | 我身高多少 | ABSTAIN | ABSTAIN | same |

- **我跑出的计数：better 0 / same 8 / worse 0 ⇒ `no_worse` 成立**，与 executor 的 `f2c6ea12c8be536a` 逐条一致（P2=5、P6/P7=10、P4/P8=ABSTAIN）。
- 对 M1.8 起点（`before` = `M18-PROBES-before.json`，`analysis 9b936852` / `retrieval c8e9e332`）：**3 better（P2/P6/P7 由 ABSTAIN 变块）/ 5 same / 0 worse**（`69572f127b720bc2`）——这 3 条改善来自 M18-1+M18-2+M18-4 的合力；**M18-3-B 本身相对上一步 0 变化**（回退路径没有被它放宽或收紧的实例）。
- P1 的"块3 而非块5"是同分排序缺口（`P1-gap.md 25af6ef3f5e1d548`），判 `same`，不判 worse；已记 §4.6。

## 5 r2 字段复核（lead 指定的 D1/D2/D3/selection_layer，详见 `INSPECTOR-M2-ACCEPT.md` §7）

| 项 | 结论 | 关键证据 |
|---|---|---|
| **D1 字面量按实参** | **已修** | r1 的 `naming` 写死 `delta=12 / cells_moved=45`；r2 为 `delta=19 / cells_moved=666`，`planner.py:132-135` 用 `% (new_cells, moved)` 生成 |
| **D2 三读数独立** | **已修** | `pre_eq`=pre↔pre2、`post_eq`=post↔post2、`unchanged`=pre↔post（sha+bytes）；四份读数分别来自 `engine.save()` 落临时文件（`accept_m2_real.py:152-155, 315, 361`） |
| **D3 真打 `order_assert`** | **已修** | `order_red_probe` 打本臂真正执行的 `order_assert`（同函数正序 true / 反序 false、`red_proof_ok=true`），不再引本臂从不调用的 `planner.check_ops` |
| **selection_layer 前后出现** | **已修** | `selection_layer={analysis_py 49e91c7b, retrieval_py b89fb200}`，`sha_stable.before/after` 都含两键；我现算两文件 sha 与产物一致 ⇒ 归属由产物自证，不靠 mtime（r2 `sampled_at=19:41:51` 晚于两文件 mtime，时序也成立） |
| 其余自洽 | **通过** | 三块 bytes/sha 前后一致、`cells_accounting 736=736`、`coverage_*all_exact`、`geometry.match`、`r1_comparison.all_match`、`invariant_failures=[]`、`verdict=通过`、`exit=0`、99.5 s |
| 仍开 | D5/D6/D7/D8 | D5 `op_ms` stub 无注记（差 28.1 ms 无账）；D6 car 未入 `coverage_after_insert`；D7 `mounted_still_answers`/`fact_ok.ask` 仍复读历史（`exclusion.pass=false` 记而不用）⇒ 非承重；D8 跨布局 `no_car` 臂缺（r2 已注明"不在本臂"） |

## 6 M1.8 四态与签署建议

**逐条四态（按各自判据）**

| 冲突 | 判据 | 状态 | 依据 |
|---|---|---|---|
| M18-2 值模式两向 | A4/A5/A6/A7（两向） | **通过** | 17/17 中四条全绿；真实库 P4/P8 仍 ABSTAIN |
| M18-1 属性 vs 词法 | A1（放行）+ A2/A3（不得杀/不得放错块） | **通过** | 全绿；真实库 P1/P2/P5 选到块（P1=3 为排序缺口非判据） |
| M18-4 闸门一致性 | A10 | **通过** | 绿；A10 在"回退 M18-4"的副本上红（我 §6 解耦试验证过） |
| M18-3 回退过宽（重出版） | A8 + A12/A13/A14/A15 + P2 + 8 探针 | **通过** | 17/17；改前 14/17 承重；真实库 0 worse |

**可签（我建议 lead 签这句）**：
> **M1.8 已定位（4 处真冲突）；四处已按判据落地（M18-2 收紧 → M18-1 放松 → M18-4 放松 → M18-3-B 改对象为 `prop_gated`）；A1–A17 17/17（相同断言在落地前代码上 14/17、红 A8/A12/A15，承重成立）；真实库 8 条 vs M1.8 起点 3 better / 5 same / 0 worse，vs 上一步 0 better / 8 same / 0 worse。**

**不可签（任何一句都不要签）**：
1. **「四处都达到 legacy 权威口径」** —— `docs/legacy-2026-10-24/README.md` 仍只在备份树（工作区为空），判据出处这一环无工作区锚（§4.1）。
2. **「M1.8 无新缺口」** —— 至少 §7 的 11 条在册（P1 排序、A14 类单例覆盖、相对时间、`index_meta.docs`、FEATURES M1 锚漂、freeze_check 未 re-freeze 等）。
3. **「freeze_check 已转绿」** —— 现在必红（见 §8），re-freeze 尚未做。
4. **「M18-3 备选 Bw 也落地」** —— 只落 B；Bw 仅留档在规格附录 A，未实施。

## 7 缺口清单（全列，含归属与建议）

1. **P1 同分排序**（M18-1 暴露）：`prop` 路径进来的候选 bm25 同为 0 ⇒ `sort` 退化为 `source_id` 序 ⇒ 聚合块 3 先于目标块 5；判 `same`，**修法属排序议题**（同分按块长度/专指度），不属本批判据，未改。已在 `M1.8-CONFLICTS-inspector.md` §4.6 与 `evidence/P1-gap.md` 记录。
2. **A14 类"同义异锚"只有单例覆盖**：目前只有 address 的「家 vs 住址」一条；phone/limit/plate 的同义锚等价性没有断言。建议后续把"A14 类"提升为一条**属性无关**的断言模板（每属性至少一个异锚例），否则 B 的"属性闸门定案"原则在别的属性上只靠 A4–A7 间接覆盖。**这是判据覆盖面缺口，不是当前红。**
3. **Bw（锚窗口版）未落**：作为 lead 明确说"不要 Bw"的备选留档在规格附录 A（实测同样 11/11 + 10/10 + 0 worse），不实施；若将来 A14 类扩展需要"词法证据"形状，它是最小候选。
4. **相对时间不可检索**（跨模块）：写入侧有 `anchored_time`，检索只索引原文 ⇒ `我女儿生日是哪天` 类只能选到写"下周三"的块；属 M4↔M1 边界，不靠放宽 birthday 模式蒙混。
5. **`index_meta.docs=2` 遗留键**：`build_index` 只写 `version`/`analysis`，`is_stale` 不看行数 ⇒ 源表行数变化不触发重建；低危（`chat.py` 重建路径会兜住）。
6. **FEATURES M1 行锚漂**：`FEATURES.md:128-129` 的 `chat.py:385/426` 与实际 `:485/:526` 不符，`chat.py` sha 也未回填（M4-C 后未回填）。
7. **legacy README 仅在备份树**：M1.8 "判据出处"在可交付物里无工作区锚（按 FEATURES §6-⑦ 只能记 A，不能记 R）。
8. **非属性单字回退被收紧且无真实库实例**：B 把值闸路径的单字回退改成必须 2 个罕见字（A8 即此类，方向宁红不绿）；真实库 8 条无实例。若未来出现合法单字值闸查询，应另立断言（对象=该 `value_kind` 的名词表）。
9. **`attr` 表只写不读**（遗留表）：语义陈旧无影响，但属索引身份不自洽的一部分（与 §7.5 同源）。
10. **治理：executor 报告曾引不存在的 sha**（`e0a4b0e9d0c9b7c5` vs 盘上 `05cc5a2b2af444af`）；本批我引的每个 sha 均现算。建议后续产物由脚本生成 `files` 段而非手写。
11. **freeze_check 仍红**（2 条：analysis、retrieval；`evidence.py dccf7f010eaf9c7e` 未变）——属"已知可解释红"，见 §8。

## 8 治理问题表态：M1.8 收口后是否 re-freeze？

**我的意见：赞成在 M1.8 判决签署之后做一次 re-freeze，但必须是"同一次改动里连 A11 锚一起改"的记账动作，不能只改 `freeze_check.py`。**

理由与精确清单：

1. `tools/freeze_check.py` 的 `FROZEN` 现在写的是旧基线：`analysis.py 9b9368524422f352`、`retrieval.py c8e9e332ef8fd367`（`evidence.py dccf7f010eaf9c7e` 未变，不用动）。re-freeze 后应改为 `49e91c7bd3dd32ef` / `43f660196ab90a14`。
2. **自指警告**：A11 把 `freeze_check.py` 自身的 sha16 当封存锚（`8decec8a4715bc8b`）。一旦改 `freeze_check.py`，A11 必红 ⇒ **re-freeze 必须同时更新 A11 的 `anchors` 字典**（`freeze_check.py` 旧→新；`eval_heldout.py 597fd0ca` 不动），并把这次"A11 期望值随 re-freeze 更新"写进台账。否则"17/17"就是靠改断言换来的假绿。
3. 记账要求（建议落成一个独立小批，与 M1.8 判决分开）：
   - 留 `_before/freeze_check.py@8decec8a4715bc8b` 字节副本 + `_before/test_retrieval_judges.py@be3d93bfca7bc39d`；
   - 台账写 **old→new**：`freeze_check.py 8decec8a→<new>`、`test_retrieval_judges.py be3d93bf→<new>`，理由写"**M18-1..M18-4 经 inspector 复核（A1–A17 17/17 + 真实库 no_worse）后按判据更新选择层基线；阈值/版本未变，无索引重建**"；
   - 重跑 `python tools/test_retrieval_judges.py` ⇒ 期望仍 **17/17**（产物另存，如 `out/M18-A-after-refreeze.json`）；
   - 跑 `python tools/freeze_check.py` ⇒ 期望 **`SELECTION LAYER: FROZEN`、exit 0**；
   - 阈值/版本仍不动（`GATE/COV_MIN/REL_CUT/ABS_CUT = 1.30/0.35/0.55/1.10`、`INDEX_VERSION=5`、`ANALYSIS_VERSION=4`），**不要借 re-freeze bump 版本**（本批只改查询侧语义，建索引表语义未变；bump 会强制重建，收益为零、风险是引入不必要的索引差异）。
4. **不建议现在立刻做**：M1.8 判决未签、若签后还有 r3/其它 M2 收尾改动，会二次 re-freeze；建议顺序 = **lead 签 M1.8 → executor 单独小批 re-freeze → 我复核 freeze_check 转绿 + A 仍 17/17**。若 lead 选择"再等等"，我接受，但要求之后每份产物继续显式标注"freeze_check 已知可解释红"（`LANDED-m18-3v2.json` 已标）。

## 9 数值锚（复核用）

`tools/retrieval.py 43f660196ab90a14 / 18,197 B` ｜ `tools/analysis.py 49e91c7bd3dd32ef / 18,382 B` ｜ `tools/test_retrieval_judges.py be3d93bfca7bc39d / 15,108 B` ｜
`chat.db 237d8e1f5de9a382 / 110,592 B` ｜ `index_meta {docs:2, version:5, analysis:4}` ｜ `freeze_check.py 8decec8a4715bc8b / 3,053 B`（红 2 条）｜ `eval_heldout.py 597fd0ca671e898e / 12,294 B`（未变）｜
`out/M18-A-after-m18-3v2.json 9a9483861eb146bd`（17/17）｜ `out/M18-A-pre-M18-3v2.json 79456d7762d3c300`（14/17，A8/A12/A15）｜
`out/M18-PROBES-after-m18-3v2.json 5f7c74adc17f407e` ｜ `M18-CMP-m18-3v2-vs-prev.json f2c6ea12c8be536a`（0/8/0）｜ `M18-CMP-m18-3v2-vs-before.json 69572f127b720bc2`（3/5/0）｜
`m1/LANDED-m18-3v2.json 766f44d645ce504a / 7,868 B` ｜ `evidence/M18-3-INVALIDATES.md 2bb610586b0c9b42` ｜
r2：`M2-ACCEPT-r2.json c95e0b7c2b7cc163 / 23,767 B` ｜ r1 `76e2783343c3e196`（未动）｜ `planner.py 01507f6bbf816c11` ｜ `accept_m2_real.py fe625c3776f86bd8` ｜ `LANDED-m2accept-r2.json 1d7d0c392291d6fe`。

---

## §10 缺口状态更新（2026-10-25 20:35 追加，§7 编号不变）

> 本文件 §0–§9 是 19:54 的终审快照；之后发生三件收尾，按 lead 要求在此销号/更新。§7 其余各条**保持原判**。

| §7 编号 | 原状 | 现状（我现算复核） |
|---|---|---|
| **#6** FEATURES M1 行锚漂 | `chat.py:385/:426` + `4c8d73e9` | **销号**。`FEATURES.md` 现 = **`79f2d9c4730f6815`**（15,218 B，20:02:58）；`chat.py` = `cb70be52eef253fa`，`_selection` 在 **485**、调用在 **526**（我在盘上核过 `FEATURES.md:13/127-129`）。注：`M1.8-VERDICT-lead.md` §9 记的 `FEATURES.md f790e8f5` 与现盘不符（已报文 lead，不作数） |
| **#7** legacy README 仅在备份树 | 判据出处无工作区锚 | **销号**。80 份 md 已按字节回填（分母 85、`still_missing=[]`；`m1/LANDED-restore.json` `fe1f2ff914a80196`）。我抽 8 份独立比对：7 份与备份树逐字节相等（含 `PROJECT-STATE.md 3d40d558`、`docs/legacy-2026-10-24/README.md `a7a63a2080f38e14`、`mine/inspector/M3-ACCEPT.md 9a57a203`、`mine/lead/DISCIPLINES.md 17b69bf0`、`mine/inspector/M5-CRITERIA.md 2d31dfef`、`docs/README-PHASE1-ENGINE.md 500557aa`、`kvmem/m2_7b/MOVE-MAP.md 3791ffa6`），第 8 份 `mine/inspector/M4-ACCEPT.md` DIFF 属**保护件**预期；三份保护件（`FEATURES.md`/`README.md`/`mine/inspector/M4-ACCEPT.md`）确认**未被覆盖**。**引用规则**：回填件按**史料**读、旧签字不作数、`PROGRESS` 仍是唯一权威（`PROGRESS §0.1`） |
| **#11** freeze_check 未 re-freeze | 红 2 条 | **销号（M1.8 收尾完成）**。我独立复核：`tools/freeze_check.py` 现 = **`6016085a05890581`** 并打印 `SELECTION LAYER: FROZEN (3 files, 3 thresholds, versions {'INDEX_VERSION': 5, 'ANALYSIS_VERSION': 4})`，**exit 0**；我自己重跑 A = **17/17**（`fail=[]`）；A11 承重自证产物 `out/M18-A11-redproof.json` = **`1997e32a2187e56f`**（16/17，`fail_ids=['A11']`，exit 2）；`out/M18-A-after-refreeze.json` = `673a2c9334d2f4a7`；台账 `m1/LANDED-refreeze.json` = `5075fc4bc23b816f`；`tools/analysis.py 49e91c7b` / `tools/retrieval.py 43f66019` / `tools/evidence.py dccf7f01` / `tools/eval_heldout.py 597fd0ca` / 四阈值 / 两版本号**全未动** |

**保持原判的缺口**：§7.1 P1 同分排序 ｜ §7.2 A14 类同义异锚单例覆盖 ｜ §7.3 Bw 未落 ｜ §7.4 相对时间不可检索 ｜ §7.5 `index_meta.docs=2` ｜ §7.8 非属性单字回退无真实库实例 ｜ §7.9 `attr` 只写不读 ｜ §7.10 引 sha 方法纪律（本条已三次被现实印证：executor 两起、verdict §9 的 `f790e8f5`）。

> **2026-10-25 20:45 追加**：lead 已按同一纪律立规 —— **互为引用的两份文件，任何一方都不钉死对方的 sha，一律「现算为准」**；`M1.8-VERDICT-lead.md` 现 = **`7d3b74416a503235`**（12,352 B，新增 §10 自伤披露），`PROGRESS` = `761052001274bfdd`、`FEATURES.md` = `8c1a7568e71123d9` 已同步（三个数我现算复核）。**本 §10 表内 20:35 快照的 sha 一律以现算为准**，不再追改。