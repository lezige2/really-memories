# M5 judge v2.1 只读审计（零 GPU、零模型、未改任何产物）

**as-of**：2026-10-26T10:21+0800（磁盘态：PREREG 10:04:50 / `m5_ground_v2.py` 10:11:17 / regression 10:12:08 / LANDED 10:12:50）
**角色**：inspector（非实现者、非 v2 ADJ/REVIEW，§G）；结论层级 = 判定器缺陷修复可用性，**不是 M5 最终判决**
**方法**：自己复算 sha16/字节；`run_regression(write=False)` 内存重跑（输出只落 `%TEMP%`）；v1/v2 分支逐段规范 diff；不写仓库、不碰 git、零模型

> ⚠ **坐标更正（2026-10-26T11:16 追加，详见文末「附」）**：本审计**最初坐标** = `m5_ground_v2.py 34afeef1ee02ba82 / 55,401`、regression `bb7eb3aef4c98e03 / 175,707`、LANDED `9e81ff740b8422ee / 6,718`（正文表第 1/5 行与「引用句」按此写）；**执行/现盘坐标** = `5e11e1ac06f022c7 / 66,413`、`205a61dc51b3cb4a / 193,316`、`8bb5e4dec15c59c1 / 11,068`（audit R1–R6 整改后）。**引用本件结论时必须用现盘坐标**（替换方法见「附」§⑤）；其余结论与限定不变。

## 结论

**可签（限定）。** 作为「M5 判定器 `judge_defect` 双层缺陷（层 a 漏抽实体 + 层 b 空事实默认 supported）修复的**装置可用性**」可签：§D1–§D5 五项验收我逐条独立复现成立，v1 冻结件零改动，92 个 side 上不存在 `v1 unsupported|undecidable → v2 supported` 路径，θ/STOP/FRAME 为源码常量不可被 env/CLI 覆盖。
**不可据此签**：θ 已校准；46 对上的「0 漏判 / 0 误判」可外推；M5 可进全量；(c) 已验证。以上均超出 46 对 in-sample 证据（两率分母 5/13 < 10，且误指控类被 §C5 结构性地排除在两率之外）。附 6 条非阻塞整改，其中 R1（坐标错标）建议在 PROGRESS 引用前修正或加注。

## 逐项核对

| # | 必查项 | 结论 | 证据（file:line / json 路径） |
|---|---|---|---|
| 1 | sha 真实性 & v1 未改 | **全部相符**。三件盘上 sha16/字节与任务书逐字节相等；`m5_ground.py` = `86b7c501ab9904aa`/18,496（mtime 03:51，早于 v2）；预登记 §0.1 十二件**我自己复算 12/12 全等**（pairs `f0767d84`/7,503、intent `9f140979`/2,184、adj `1f5d7a54`/10,653、judge `bff8a34b`/27,935、REVIEW `39d1d248`/9,143、model pairs `aa9e6106`/7,851、model intent `6e4656d3`/1,373、model-adj `1b52862f`/6,035、model-judge `8bc7af8e`/17,928、alignment `b38c17f7`/38,475、INSPECTOR `21c704ba`/4,670） | `m5_ground_v2.py` 34afeef1ee02ba82/55,401；`out/M5-JUDGE-v2-regression.json` bb7eb3aef4c98e03/175,707；`LANDED-m5-judge-v2.json` 9e81ff740b8422ee/6,718；`PREREG` 6c77b56f406432aa/35,739；regression `/judge_sha16`、`/supersedes_untouched=true` |
| 2 | 分支顺序 / fail-closed / θ 可否覆盖 | **成立（可签）**。分支 1–4 **语义等价**于 v1，仅 3 处形式改写（`pseg` 提升、`_v1.TRAD` 别名、if/elif 链拆分）；`unhit → unsupported` 在覆盖检查**之前**；结构上无「v1 unsupported → v2 supported」路径（实测 92 side 中 0 例，`v1 undecidable→v2 supported` 亦 0）；θ 为源码常量且 `ground()` 恒传 `THETA` | v2 `:231-233` vs v1 `:345-346`；分支 2 在 `:263-266`，覆盖检查在 `:277-290`；`THETA=0.20` `:49`；`:278` 传常量；`:115` 的 θ 形参只服务回归台，无 env/CLI（`:941-946` 无 theta 参数）。**注**：docstring `:14` 称「byte-for-byte v1」措辞过强，实为语义等价 |
| 3 | 可复现性（冻结集合 / 零模型复跑） | **成立**。STOP 38 字 = `a4406d0bd1de47c7`、FRAME 34 项 = `f7df16d8ba96e68f`，以常量存在并**在 import 时自校验**（不符即 RuntimeError，含排序/去重检查）；我按 §B1 定义从 v1 `FUNC∪INTERROG∪{问,答}`、`BLACKLIST∪7字` 独立重建，两哈希逐字符相同；`run_regression(write=False)` 零模型复跑与盘上件**仅差 `created_at` 1 处**，其余全等 | v2 `:69`（STOP）、`:73-76`（FRAME）、`:78-79`（哈希）、`:82-87`（断言）；复跑输出 `%TEMP%/m5v2_reg_fresh.json`，结构化 diff = 1 项（`/created_at` 10:12:07 vs 10:15:41） |
| 4 | 回归数与 diff | **全部相符**。`diff_vs_v1` 只有 P13/P25 两行（各含 orig+rewrite 共 4 个 side，全 `supported→unsupported`）；`unexpected=0`；rewrite18 `leak 0/5`、`false 0/13`（我按 pairs+ADJ∩REVIEW 独立重算）；baseline12 `12/12`（v1 `10/12`）；`no_fact=0`；u 谱 `{0.000, 0.666667, 0.800}` = §C1 `{0.000,0.667,0.800}`；12 个 branch-5 side 的 gram_n（P13 5/5、P16rw 1、P22 3/3、P24 3/2、P25 3/3、P26o 3、P28 3/3）与 §C1 逐行相符；**五档 θ 读数真的完全相同**（实测 distinct=1，非漏报）：0.10/0.15/0.20/0.25/0.30 的 `sides_92`=52/40/0、missed=0、false=0、rw18 0/5+0/13 全一致 | regression `/diff_vs_v1`(2)、`/counts/unexpected_rows=0`、`/rates/rewrite18_main`、`/rates/baseline12`、`/u_spectrum`、`/threshold_table`、`/threshold_table_note`（"实测五档读数只有 1 种"）；92 side 分支分布 44/36/8/4 |
| 5 | in-sample 声明 / 越界措辞 | **部分满足**。回归件明写 in-sample（五处 note + `fitting_disclosure`），并写「θ 未被校准 / 不代表 M5 可进全量」；无「已验证 / 已校准 / 通过率」越界措辞（仅 `summary="5/5 通过"` 指 5 条验收）；**但未明写** (c)/全量须 out-of-sample；**台账 LANDED 完全无** in-sample / 未校准 / out-of-sample / 分母<10 注记（grep 0 命中），单看台账只剩 `v2_signable:true` 与 0/5、0/13 | regression `/threshold_table[i]/note`、`/fitting_disclosure/detail`、`/verdict/scope`、`/rates/rewrite18_main/sample_size_note`；`LANDED-m5-judge-v2.json` 全文无上述限定 |
| 6 | `|G|=0 → undecidable` 是否死代码 | **非死代码**。回归命中 0（与 §C1/F6 预测一致），由 selftest 三条合成句覆盖；我抽 3 条核对：C4「嗯，可能吧。」、C5「好像是吧。」、`no_fact`「也就是说。」均 `gram_n=0 → undecidable`（pass）；我另用 `ground()` 端到端复跑同三句，均 `branch=5c_no_fact`、`reason=no_fact_unverifiable` | v2 `:363`（NO_FACT_SYNTHETIC）、`:382-387`（循环断言 `verdict==undecidable and gram_n==0`）、`:350-361`（10 条 CONTROLS）；selftest 共 15 条全 pass；**但 regression 与 selftest 都没覆盖 `ground()` 层 5c**（见 R3） |
| 7 | 预登记坐标不符 | **observed 字段如实，但留痕不齐**。盘上 PREREG = `6c77b56f`/35,739（与任务书一致）；regression `/prereg/sha16` 仍是已取代稿 `8330fa716ef32a28`，同时如实记录 `observed_sha16=6c77b56f406432aa`、`observed_bytes=35739` 并加 note 说明「交给实现的坐标 vs 落盘所见」；**但未记录实现方报告的 `135d020f`/35,716/411 行**（仅 `LANDED:222-226` 有）；语义上：θ=0.20（§C2）、分支序（§B0）、验收 5 条（§D1–5）我逐条对 6c77b56f 正文核过，与实现一致；mtime 序 prereg(10:04:50) < v2(10:11:17) < reg(10:12:07) ⇒ 落盘版早于任何 v2 结果，不可能被结果拟合；但 `135d020f→6c77b56f` 的 +23B 差异在不碰 git 的前提下**无法 diff**，「三项从未被改动」只能保守表述为「落盘版本三项与实现一致，且早于结果」 | v2 `:5`、`:48`；regression `/prereg/*`、`/corrections[7]`（留痕条目）；`LANDED:216-232`；`PROGRESS-AND-ROADMAP.md:2912`、`ARTIFACTS-KEY.md:158` 均只记 6c77b56f |
| 8 | 方向反转披露 / 是否承诺超证据 | **预登记如实披露，两份落盘件未承接**。§H1（`:373`）整段写明 ② 是「主动指控」、方向由「宁漏」偏向「宁错」、非 fail-open 放宽而是「误判倾向的引入」，并配 §C5 事先声明 T6–T10 五例已知误伤；但 regression 与 LANDED 均**零命中**「方向/指控/漏判优先/宁漏」（仅保留 known_fp 清单与 0/0 计数），台账读者看不到该方向反转。越界判断：未承诺「v2 通过/已校准」（合规），但「46 对 0 漏判/0 误判」是 in-sample 且两率分母 5/13<10，**误指控这一新错误模式被 §C5 放在两率分母之外** ⇒ 0/0 不能被读成「低误指控率」 | 预登记 `:373`、`:271-286`；regression `/known_fp_controls`（10 条，5 条 known_fp）、`/rates/rewrite18_main/{leak,false}`；LANDED `:90-95`、`:140-145` |

## 缺口 / 风险清单

**阻塞：无。** 未发现 sha 不符、v1 被改、差异 >2 行、`unexpected>0`、θ 可覆盖、验收不成立、① 死代码或超证据承诺中任一项。

- **R1（非阻塞，须修）坐标错标**：`m5_ground_v2.py:5,:48` 与 regression `/prereg/sha16` 把**已取代稿** `8330fa716ef32a28` 标为 `prereg`，而实现实际遵循 `6c77b56f`。建议改名 `prereg_coordinate_given` 或直接改指 6c77b56f，并在回归件补记 `135d020f`/35,716/411 行（现仅 LANDED 有），使「首读→落盘」链条单件可读。
- **R2（非阻塞）CLI 复跑会改产物**：`--regression` 走 `run_regression()` 默认 `write=True`（`:951-952`、`:925-929`），任何复跑都重写 `out/M5-JUDGE-v2-regression.json`（`created_at` 变 ⇒ sha 变 ⇒ 台账 `bb7eb3ae` 失效）。本次审计只能用 `write=False`。建议加 `--no-write/--dry-run`。
- **R3（非阻塞）5c 接线无自动测试 + 结构性断言偏弱**：selftest 只测 `ngram_check`（`:373-387`），回归 `no_fact=0`，`ground()` 的 5c 出口无任何自动覆盖（我已手工端到端验通）；且 `_assert_invariants()` 的 `:341-343` 是恒真断言（比较对象就是同一对字面量），分支被重排时不会失败——真正的保障是 elif 链本身（已读码确认正确）。
- **R4（非阻塞）recheck 语义已变但未留痕**：v2 的 recheck 用 v2 嵌套判（`:316-318`），P13/P25 上 `recheck_verdict=unsupported`（v1 不触发、为 null），四条布尔仍全 true；regression 完全不记 recheck（grep 0 命中）⇒ §B3「recheck 一行不动」名义上被破，建议在结果件记一句。
- **R5（非阻塞）台账限定缺失**：LANDED 缺 in-sample / 未校准 / out-of-sample / 分母<10 注记，rates 只写 `0/5`、`0/13`。建议把 regression `/verdict/scope` 与 `sample_size_note` 抄进台账。
- **R6（非阻塞）自述措辞**：docstring `:14` 称分支 1–4「byte-for-byte v1」，实为 3 处形式改写后的语义等价；`summary="5/5 通过"` 在脱离上下文时可被引成「v2 通过」（§H7.4 禁止）。建议改为「5/5 acceptance checks pass」。

## 引用句（可整段进 PROGRESS）

> **M5 judge v2.1 只读审计（2026-10-26，零 GPU / 零模型 / 未改产物）**：**可签，限定为「judge_defect 双层缺陷修复的装置可用性」**。五件坐标逐一复算相符：`m5_ground_v2.py 34afeef1ee02ba82 / 55,401`、`out/M5-JUDGE-v2-regression.json bb7eb3aef4c98e03 / 175,707`、`LANDED-m5-judge-v2.json 9e81ff740b8422ee / 6,718`、`PREREG-M5-JUDGE-v2.md 6c77b56f406432aa / 35,739`；v1 `m5_ground.py 86b7c501ab9904aa / 18,496` 与预登记 §0.1 的十二件冻结产物 **12/12 未变**（自算，未信台账）。`run_regression(write=False)` 复跑与盘上件仅差 `created_at` 一处 ⇒ 零模型可复现。`diff_vs_v1` 只 P13/P25 两行（4 side，`u=0.800 / 0.667`，`miss=杭州/州西/西湖/湖边`、`龙井/井茶`），`unexpected=0`，rewrite18 `leak 0/5`、`false 0/13`，baseline12 `12/12`（v1 `10/12`），`no_fact=0`，u 谱 `{0.000, 0.667, 0.800}`，**五档 θ 读数实测只有 1 种**（回归集对 θ 无标定能力）；`|G|=0 → undecidable` 由 selftest 三条合成句 + 我的 `ground()` 端到端复核确认非死代码。θ/STOP/FRAME 为源码常量（`a4406d0bd1de47c7` / `f7df16d8ba96e68f`，与我按 §B1 定义重建逐字符相符），无 env/CLI 覆盖，92 side 上无 `v1 unsupported|undecidable → v2 supported` 路径。**不构成**：θ 已校准、46 对 0 漏判/0 误判可外推（in-sample，两率分母 5/13<10，误指控类被 §C5 排除在两率之外）、M5 可进全量、(c) 已验证——(c)/全量必须 out-of-sample 重新检验。待修（非阻塞）：①源码与回归件仍把 `prereg` 标为已取代稿 `8330fa71`（落盘实为 `6c77b56f`，`observed_*` 已如实记录，但 `135d020f/35,716` 只在台账）；②`--regression` 默认写盘会改产物；③`ground()` 的 5c 接线无自动测试、`_assert_invariants` 为恒真断言；④方向反转仅在预登记 §H1 披露，两份落盘件未承接。

## 附：整改增量复核（audit R1–R6 → 现盘 `5e11e1ac`）

**追加 as-of**：`2026-10-26T11:16+08:00`。零 GPU / 零模型 / 未改产物：`--regression` 以 `write=False` 跑（`written=false`），盘上 regression sha 仍 `205a61dc`、mtime 未变（10:35:26）。本节回答 lead 裁定的问题：审计原坐标被整改件取代后，「可签（限定）」能否顺延。

### ① 增量是否只落 R1–R6 + 机械性改写（可核部分）

- **旧件不在盘**：全仓无 `34afeef1` 副本（`_before/` 只有 10-25 的 (c) 旧件），本会话不碰 git ⇒ **逐字节 diff 不可得**。只能给三条独立可核证据：
  1. 源码内整改台账 `corrections[]`（`m5_ground_v2.py:991-1043`）逐条列 R1–R6 的 kind / item / authority；`LANDED.audit_remediation.items` 同文（R1 坐标改指、R2 默认不写盘、R3 selftest+真断言、R4 recheck 回退、R5 台账限定、R6 措辞）。
  2. 源码 docstring 自述三处**纯机械改写**（`:19-20`）：`pseg` 提出分支体、`_v1.TRAD` 别名、if/elif 链拆成带标签分支；读码确认在位（`pseg` `:257-266`、`_v1.TRAD` `:279`、`B_*` 标签 `:110-116`，分支序 `:233/288/293/297/301`）。
  3. **行为不变**（见 ②：92 side 复算、46 对 0 diff）。
- **θ/STOP/FRAME 未变且不可覆盖**：`THETA=0.20`（`:61`）；`STOP_SHA16==a4406d0bd1de47c7`、`FRAME_SHA16==f7df16d8ba96e68f`（`:94-97`，import 时 raise）；`STRICT_GT=True`（`:63`）；判定用 `u > theta`（`:197`）；全文件无 `os.environ`/`getenv`，CLI（`:1078-1096`）无 theta 参数，regression `gate.theta_not_runtime_overridable=true`。
- **`--regression` 默认不写盘**：`run_regression(write=False)`（`:522`）+ 独立 `--write` 开关（`:1085-1086`）；本会话 dry-run 得 `write_note="默认不落盘（audit R2）"`、`written=false`。
- **归因结论**：R1–R6 六项在现盘**逐条在位**；「`34afeef1→5e11e1ac` 的差异只落在 R1–R6 + 机械改写」是**源码自述 + 行为不变**的**推论**，**不是逐字节证明**（证据缺口见 ④）。

### ② 46 对 verdict 是否 0 diff

本会话对现盘 `5e11e1ac` 跑 `--regression`（dry-run）：
- `written=false`、`disk_sha16_before=205a61dc51b3cb4a`、`matches_disk_ignoring_created_at=true` ⇒ 现盘判据与盘上回归件**除 `created_at` 外逐字段自洽**（复跑可复现）。
- 验收 `checks 5/5 true`、`abort=false`；`diff_vs_v1 = [P13 supported→unsupported, P25 supported→unsupported]`（4 side，`u=0.800/0.667`，branch `5a_2gram_negative`）⇒ 除设计内 P13/P25 外 **46 对 0 diff**（其余 28 对两 side 与 v1 标签一致）。
- `counts`：`pairs=46 / sides=92`（R1 30 + R2 16）、`unexpected_rows=0`、`no_fact_undecidable=0`、`near_threshold=0`、u 谱 `{0.000,0.667,0.800}`；`rewrite18 leak 0/5`、`false 0/13`；side 分布 v1 `56/36/0` → v2 `52/40/0`。
- selftest **18/18 pass**（含 `ground()` 端到端 5c 三条、C4/C5 合成句、C1–C10 对照）。
- **允许项单列**：P13/P25 四 side 的 `recheck_verdict` 由 `unsupported` 回退为 `supported`（R4，v1 语义；`recheck_semantics=v1_unchanged`；**仅报告字段，不改任何 side/pair verdict**；`LANDED.corrections[1]` 已记）。⇒ 「46 对 0 diff」成立；但只读 `recheck_verdict` 会误以为行为变化，引用须带本节。

### ③ 整改后 LANDED 的限定是否补齐

**已补齐（R5 要求满足）**：`in_sample=true`；`theta_calibrated=false`；`out_of_sample_required_for=["(c) 长生成","全量"]`；`denominator_note="两率分母 5/13 <10，仅装置可用性"`；`known_fp_excluded_from_rates="5 例（T6–T10）"`；`scope_note`（只表示修复可用性，不代表全量 / θ 已校准 / (c) 已验证）；`discipline{gpu_used:false, model_calls:0, git_operations:0, theta_retuned:false}`；另有 `prereg_coordinate_mismatch` 三稿坐标链与 `update` 说明。

### ④ 顺延结论

**「可签（限定）」可顺延到 `5e11e1ac06f022c7 / 66,413`，限定不变** = 「`judge_defect` 双层缺陷修复的**装置可用性**」；**不含**：θ 已校准、46 对 0 漏判/0 误判可外推、M5 可进全量、(c) 已验证（(c)/全量仍须 out-of-sample 检验）。
证据强度分层：
- **强（本会话独立复算）**：92 side verdict、dry-run 与盘件等（除 `created_at`）、验收 5/5、常量锁定与不可覆盖、默认不写盘、selftest 18/18、v1 件零改动（`86b7c501ab9904aa / 18,496` 现盘复算）。
- **弱（不可验）**：旧件 `34afeef1` 缺失且不碰 git ⇒ **逐字节增量不可证**；「差异只落 R1–R6」只能由「源码/台账自述 + 46 对行为不变」支撑。
- **若该强度不被接受** ⇒ 唯一缺口 = 一次带旧件副本或 git 的二进制 diff（超本会话纪律/权限）；**该缺口不改变顺延的适用范围**：顺延仅覆盖「46 对 + 判据结构不变量」，未见输入（含 (c)）仍须独立检验。

### ⑤ 引用纪律（替换旧坐标）

正文「引用句」可继续引用，但须替换坐标：`34afeef1/55,401`→`5e11e1ac/66,413`、`bb7eb3ae/175,707`→`205a61dc/193,316`、`9e81ff74/6,718`→`8bb5e4de/11,068`；并把「待修 R1–R6」读作**整改前快照**——现盘 R1–R6 **已全部落地**（R1 坐标 `:5/:57`+regression `/prereg/sha16=6c77b56f`；R2 默认 `write=False`；R3 selftest+真断言 `:363-411`；R4 `_v1.ground` `:346`+`recheck_semantics=v1_unchanged`；R5 LANDED 限定；R6 docstring `:21` 与 summary 措辞）。
