# M5-C2 doc-ledger 账本独立抽查（20 条）

> 抽查人：`rev7-impl`（task-13） · 生成时刻：`2026-10-26T21:32:49+08:00` · 只读抽查，未改任何被审文件 · 零 GPU/模型/联网 · 未 git 提交
> 被审账本：`kvmem/m2_visibility/m5/out/M5C2-DOC-HASH-LEDGER.json`（`02f43fdde85953c9` / 149960 B）、`docs/_work/DOC-HASH-LEDGER-M5C2.md`（`df270b1c2c9fc6b7` / 56701 B）
> 本抽查件：`kvmem/m2_visibility/m5/out/M5C2-DOC-LEDGER-SPOTCHECK.json`（机器可读，逐条 evidence 全在里面） + 本文件

## 0 一句话结论

**20 条抽查：19 条与账本一致，仅 1 条分歧（S20）——不是数据错，是账本 JSON 里对 REV7.1 状态的“两处自述”停留在草稿阶段（`scope.rev7_1_snapshot.frozen=false`、`key_findings[3]` 称“仍未冻结草稿/产物未落盘”），且这两处与账本自己的 `moving_target`/`X07`/`N47`/`X15` 直接矛盾。哈希采集层没有系统性问题（22 条 `file_state` 记录 22/22 与磁盘字节一致）。**

| 桶 | 条数 | 一致 | 分歧 |
|---|---:|---:|---:|
| ① 哈希引用（stale/match 判定） | 8 | 8 | 0 |
| ② 数字不一致（numbers_mismatch 类） | 6 | 6 | 0 |
| ③ 边界条目（unverifiable / 非文件哈希 / 出处错位 / 重跑声明 / 账本自述） | 6 | 5 | 1 |
| **合计** | **20** | **19** | **1** |

## 1 方法与纪律

- **hash**：sha256(bytes)[:16]，工作区原始字节
- **whole_tree**：os.walk 全树，跳过 .git/__pycache__/node_modules；14,835 个 ≤50MB 文件全哈希，42 个 >50MB 二进制跳过并记录清单
- **git_blobs**：git cat-file --batch-all-objects --batch 逐一重算：1,491 blob / 75.0 MB；另对可达对象 1,469 blob 交叉验证
- **truncation**：B4 当前件逐行边界截断 × {raw, rstrip, rstrip+NL, CRLF, CRLF+rstrip} + 逐行 rstrip + BOM = 669 变体；归档草稿 749 变体
- **numbers**：一律从产物 JSON / 原文重算，不采信账本转述；gold 等价用 RATES.rows/rows_full/AB.rows 三张 261 行表 vs RULING.gold
- **non_file_hashes**：prompt 模板从 run_m5c2_rev4.py 的 REV4_TEMPLATE 字面量重算；DLL 直接哈希二进制
- **rerun**：N38：复制 C32 脚本到 Temp 并仅重定向 ART 路径，连跑两次；仓库文件未写
- **discipline**：只读；未改任何被审文件；零 GPU/零模型/零联网；未读 (b5) 运行数据；未 git 提交；本抽查仅新增 2 个交付文件

账本自带口径我全部照用（sha256 前 16 位、`[0-9a-f]{16}`/`{8}` 提取、逐 sid 复算），但**结论一律来自我自己跑的命令**，不采信账本转述。

## 2 逐条明细（账本判定 / 我的复算 / 一致或分歧）

| # | 桶 | 条目 | 账本判定 | 我的复算 | 结论 |
|---|---|---|---|---|---|
| S01 | ①引用 | B5:6 引 (b4) 原题面 e9a88fda；账本判 stale_unresolved（不可重构） | stale_unresolved | stale_unresolved（确证不可重构） | 一致 |
| S02 | ①引用 | REV7:7 引 (b5) e306ce994d306a84；账本判 stale_reconstructible，重构体=11,388 B | stale_reconstructible (reconstruction.verified=true) | 重构成立：truncate@“## 9 LEAD 追加” + rstrip = e306ce994d306a84 / 11,388 B | 一致 |
| S03 | ①引用 | RATES/AB 引金标 9054479b32b79eb1 / 10,208 B；账本判 stale_unresolved，并称 261 条 gold 逐 sid 等价 | stale_unresolved；N39=stale_historical_snapshot_values_equivalent | 旧字节确不可得；261 条 gold 逐 sid 等价成立（3 份 261 行表 0 差异） | 一致 |
| S04 | ①引用 | B6 冻结哈希 ac27d47d（md）+ json.prereg_sha16 一致（零自指口径） | match（md ac27d47d3a3efff9 / 17,374 B；json 23588ec099ca9255） | md ac27d47d3a3efff9 / 17,374 B；json.prereg_sha16=ac27d47d3a3efff9；frozen=true | 一致 |
| S05 | ①引用 | REV7.1 冻结哈希 09d6f1b1（B6 引、账本 file_state 记 16,313 B） | match | 09d6f1b163ea0b84 / 16,313 B / 160 行 / frozen=true | 一致 |
| S06 | ①引用 | M5B4-JUDGE.json 6a3001b6ca23ef7d（多文档共同引用） | match（452,456 B） | 6a3001b6ca23ef7d / 452,456 B | 一致 |
| S07 | ①引用 | M5B4-LEAD-RULING.json 9273ebc97aa1413a（金标现行坐标） | match（13,195 B） | 9273ebc97aa1413a / 13,195 B | 一致 |
| S08 | ①引用 | 现行 B5 = d6c7bdac73ef7326 / 14,597 B（REV7:7 的对照坐标） | match | d6c7bdac73ef7326 / 14,597 B | 一致 |
| S09 | ②数字 | REV7 §0 归因表：N1 写 4（实 3）；N3 写「与上重叠 1 例」（实 0 重叠） | mismatch（N1 4→3；重叠 1→0；总数 7 正确） | N1=3 / N2=2 / N3=2，7 例互不重叠；REV7 L15 写 “**4**”、L17 写 “（与上重叠 1 例）” | 一致 |
| S10 | ②数字 | INSPECTOR 把 M5B4-JUDGE.json 写成「452456 B / 261 行」 | mismatch（实际 17,040 行；261 是句数） | 452,456 B / 17,040 行（261 句） | 一致 |
| S11 | ②数字 | REV7 §2 要求 患者 必判 valid=false，但 N3 字面定义下不可满足；产物 A2/A3 pass=false | mismatch_unsatisfiable（产物 assertions pass=false） | 不可满足成立：患者 在句首「患者：」内逐字存在 ⇒ item_in_sentence=true、matcher_hit=substring、valid=true、coverage=1.0 ⇒ 断言必假 | 一致 |
| S12 | ②数字 | B5 §8.1 两行「全 0」按字面（本文件计数）为假 | mismatch_literal_ok_within_section1（字面假、§1 题面口径为真） | 字面假成立：专名 5 个各 1 次、租车/物业 各 1 次；§1 题面段内全 0 | 一致 |
| S13 | ②数字 | REV7.1 §6 状态行 executed=false，但重跑产物已落盘 | mismatch（状态字段过期） | mismatch 成立：L160 executed=false；产物 55191eaf2426f736 / 510,508 B 存在 | 一致 |
| S14 | ②数字 | R2 引用的 M5C-36-r1-adj.json / M5C-36-r1-alignment.json 不存在 | 更正清单 X13（low）：应去掉 -r1 | 两个 -r1 文件确实不存在；哈希/字节对应无 -r1 的两个文件 | 一致 |
| S15 | ③边界 | 8-hex 正则误捕随机种子 neg_control_seed=20261026 | unverifiable / not_a_hash | 确为随机种子，非哈希：无任何文件或 blob 的 sha16 以 20261026 开头 | 一致 |
| S16 | ③边界 | README 引 M2-ACCEPT-lead.md「已签 6f26bce0」——不可复算 | unverifiable（历史签署坐标，字节未保留） | 不可复算成立：全树 + 全部 git blob 无 6f26bce0；现文件 21ec668df2171350 / 10,479 B | 一致 |
| S17 | ③边界 | 非文件哈希：prompt 模板 a6bc4f268f7711de、DLL 9edbafa150700614 | match（由字面量/二进制重算解析） | 两个值均可复算：REV4_TEMPLATE(266 chars) → a6bc4f26…；kvshim_vk.dll → 9edbafa150700614 / 50,007,552 B | 一致 |
| S18 | ③边界 | 31/31 数值对，但出处引错文件（ARTIFACT 15 例 + AMEND 否定链），真正的 31 例在 EXPLORATORY | match_numeric_provenance_loose | 数值 31/31 成立（EXPLORATORY n_done=31，arm1..5 = 6/6/6/6/7 全 A）；provenance 确实错位 | 一致 |
| S19 | ③边界 | INSPECTOR 称「两次重跑与既有产物完全同字节 1f8f44b9 / 507,657 B」；账本判不可复算（按纪律不复跑） | numbers_unverifiable（no rerun performed） | 抽查复跑后：声明成立 ⇒ 可升级为 verified（账本保守但不错） | 一致（账本判定保守；抽查升级为已验证） |
| S20 | ③边界 | 账本对 REV7.1 状态的两处自述（1) 快照 frozen=false；2) key_findings 称“仍是未冻结草稿且所引实测产物未落盘”） | scope.rev7_1_snapshot={"sha16":"09d6f1b163ea0b84","bytes":16313,"mtime":"21:07:03","frozen":false}；key_findings[3]=“…REV7.1 撤回但仍是未冻结草稿且所引‘实测产物’未落盘” | 两处均与事实不符：文件是 frozen=true（21:06:55），产物 55191eaf2426f736 / 510,508 B 已于 21:07:27 落盘 | **分歧（账本内部不一致 + 与事实不符）** |

## 3 逐条复算证据（每条的独立命令结果）

### S01 — B5:6 引 (b4) 原题面 e9a88fda；账本判 stale_unresolved（不可重构）

- 账本引用位置：`C024 + C034 (B5:6 / B6:6)`
- 账本判定：`stale_unresolved`
- 我的复算：stale_unresolved（确证不可重构）
- 结论：**一致**
  - 当前 B4 = f30d89e30262b148 / 10,910 B（不是 e9a88fda）
  - 全树扫描 14,835 个 ≤50MB 文件（另 42 个 >50MB 二进制跳过：exe/pdb/lib/kvmem，均不可能是 11KB 级 markdown）→ 无 sha16=e9a88fda
  - git 全部对象 1,491 个 blob（--batch-all-objects，75.0 MB）+ 可达 1,469 个 → 无命中
  - B4 逐行截断变体 669 个（raw/rstrip/rstrip+NL/CRLF/CRLF+rstrip，含逐行 rstrip 与 BOM）→ 无命中；归档草稿 6f41f3d6 / 7,823 B 另 749 变体 → 无命中
  - git 中 B4 路径仅 1 个 blob：1982d167 → f30d89e30262b148（10,910 B）—— 与账本 X03 说法一致
- 备注：B6:6 是“明知旧值”的引用（原文写「B5 文内自引的 b4 值 e9a88fda 为更早版本，以本件实测为准」），账本仍标 stale_unresolved：口径可辩但不影响结论。

### S02 — REV7:7 引 (b5) e306ce994d306a84；账本判 stale_reconstructible，重构体=11,388 B

- 账本引用位置：`C106 (REV7:7)`
- 账本判定：`stale_reconstructible (reconstruction.verified=true)`
- 我的复算：重构成立：truncate@“## 9 LEAD 追加” + rstrip = e306ce994d306a84 / 11,388 B
- 结论：**一致**
  - marker “## 9 LEAD 追加” 首字节偏移 = 11,390
  - raw 截断 11,390 B → sha16 9c09ceaf99d37a23（≠ 引用值）
  - 截断后 rstrip 11,388 B → sha16 e306ce994d306a84（= 引用值）✅
  - 其余变体不符：rstrip+NL 11,389 B → 13ab742f12ca1536；CRLF 11,390 B → e95316e61bce012b
  - 现行 B5 全文 = d6c7bdac73ef7326 / 14,597 B（S08 条另证）
- 备注：账本 method/note 与 reconstruction 字段的 3 个数字（11,388 / 11,390 / 9c09ceaf）全部逐位复现。

### S03 — RATES/AB 引金标 9054479b32b79eb1 / 10,208 B；账本判 stale_unresolved，并称 261 条 gold 逐 sid 等价

- 账本引用位置：`C138 + C141 + N39 (RATES:4 / AB:5)`
- 账本判定：`stale_unresolved；N39=stale_historical_snapshot_values_equivalent`
- 我的复算：旧字节确不可得；261 条 gold 逐 sid 等价成立（3 份 261 行表 0 差异）
- 结论：**一致**
  - 当前金标 = 9273ebc97aa1413a / 13,195 B；全树 14,835 文件 + 1,491 git blob 均无 sha16=9054479b
  - gold 等价独立复算：RATES.rows(261) vs RULING.gold → 0 差异；RATES.rows_full(261) → 0；AB.rows(261) → 0
  - gold_counts 46/164/10/41 与 RULING 一致；RATES.gold_sha16 与 AB.same_gold 均记 9054479b（生成时点坐标）
  - RATES/AB 是 9054479b 时点产物且内嵌逐 sid gold ⇒ 该快照可直接证明旧金标值域未变
- 备注：旧版 10,208 B 的字节本身不可再验；等价性论证依赖 RATES/AB 内嵌 rows 的时点可信，这点账本未明说，我补记。

### S04 — B6 冻结哈希 ac27d47d（md）+ json.prereg_sha16 一致（零自指口径）

- 账本引用位置：`N42 + N43 + X12/X16（B6 自钉）`
- 账本判定：`match（md ac27d47d3a3efff9 / 17,374 B；json 23588ec099ca9255）`
- 我的复算：md ac27d47d3a3efff9 / 17,374 B；json.prereg_sha16=ac27d47d3a3efff9；frozen=true
- 结论：**一致**
  - sha256(PREREG-M5-C2-B6.md)=ac27d47d3a3efff9，bytes=17,374
  - M5C2-B6-SENTENCES.json sha16=23588ec099ca9255 / 9,482 B
  - json.prereg_sha16 == md 全文件 sha16（可复算，零自指成立）
  - B6 内 pinned 坐标行：B2 482a94820917d16e、B4 f30d89e30262b148、B5 d6c7bdac73ef7326 均与现值一致
- 备注：B6 是审计期内 21:16:37 才冻结的活文件；账本快照取到的是冻结版，moving_target 留痕完整。

### S05 — REV7.1 冻结哈希 09d6f1b1（B6 引、账本 file_state 记 16,313 B）

- 账本引用位置：`C037 (B6:101)`
- 账本判定：`match`
- 我的复算：09d6f1b163ea0b84 / 16,313 B / 160 行 / frozen=true
- 结论：**一致**
  - sha256=09d6f1b163ea0b84，bytes=16,313；frozen=true ×3、frozen=false ×0
  - 内容含 N1=3 更正、“N3 未修好，仍为 FP”、A.6 例数更正、executed=false
- 备注：本件即我上一轮冻结件；账本快照时点 21:07:03 与落盘一致。

### S06 — M5B4-JUDGE.json 6a3001b6ca23ef7d（多文档共同引用）

- 账本引用位置：`C088/C091/C094/C100/C103/C108/C121/C124/C137/C143`
- 账本判定：`match（452,456 B）`
- 我的复算：6a3001b6ca23ef7d / 452,456 B
- 结论：**一致**
  - sha256=6a3001b6ca23ef7d，bytes=452,456
  - 10 处引用全部指向同一目标，指向正确
- 备注：同一文件的“261 行”写法错误另见 S10（N32）。

### S07 — M5B4-LEAD-RULING.json 9273ebc97aa1413a（金标现行坐标）

- 账本引用位置：`C087/C095/C101/C104/C109/C122/C125`
- 账本判定：`match（13,195 B）`
- 我的复算：9273ebc97aa1413a / 13,195 B
- 结论：**一致**
  - sha256=9273ebc97aa1413a，bytes=13,195
  - n=261、gold_counts 46/164/10/41 与账本 N02 一致
- 备注：与历史坐标 9054479b 的区分见 S03。

### S08 — 现行 B5 = d6c7bdac73ef7326 / 14,597 B（REV7:7 的对照坐标）

- 账本引用位置：`C033 (B5 自身)`
- 账本判定：`match`
- 我的复算：d6c7bdac73ef7326 / 14,597 B
- 结论：**一致**
  - sha256=d6c7bdac73ef7326，bytes=14,597
  - 与 S02 的组合证明：§9 于冻结后追加且未重钉

### S09 — REV7 §0 归因表：N1 写 4（实 3）；N3 写「与上重叠 1 例」（实 0 重叠）

- 账本引用位置：`N29 + X01/X02 (REV7:15/17)`
- 账本判定：`mismatch（N1 4→3；重叠 1→0；总数 7 正确）`
- 我的复算：N1=3 / N2=2 / N3=2，7 例互不重叠；REV7 L15 写 “**4**”、L17 写 “（与上重叠 1 例）”
- 结论：**一致**
  - REV7 产物 false_by_reason 逐条：s01→N1、s15→N1、s1-q3-s03→N1、s07→N3、s09→N3、s2-q1-s01→N2、s8-q2-s02→N2 ⇒ N1 3 / N2 2 / N3 2
  - 三组 sid 集合两两无交集 ⇒ 重叠 0
  - REV7 原文 L15 “**R1 数值归一化缺失** | **4**” 只列 3 个 sid；L17 “**2**（与上重叠 1 例）”
  - 我另做的消融边际（去 N1→FP 5、去 N2→4、去 N3→2）与 3/2/0 修复数一致
- 备注：REV7.1 冻结版已改为 3 / “N3 未修好，仍为 FP” + A.6 例数更正（我上一轮交付）。

### S10 — INSPECTOR 把 M5B4-JUDGE.json 写成「452456 B / 261 行」

- 账本引用位置：`N32 + X09 (INSPECTOR:40)`
- 账本判定：`mismatch（实际 17,040 行；261 是句数）`
- 我的复算：452,456 B / 17,040 行（261 句）
- 结论：**一致**
  - wc -l = 17,040（换行 17,040 个，文件无缺尾换行）
  - bytes=452,456、sha16=6a3001b6ca23ef7d 均对
  - INSPECTOR 原文 L40 确实写 “452456 B / 261 行”
- 备注：单位错误（行 vs 句），字节/sha 不受影响。

### S11 — REV7 §2 要求 患者 必判 valid=false，但 N3 字面定义下不可满足；产物 A2/A3 pass=false

- 账本引用位置：`N33 + X06 (REV7:49)`
- 账本判定：`mismatch_unsatisfiable（产物 assertions pass=false）`
- 我的复算：不可满足成立：患者 在句首「患者：」内逐字存在 ⇒ item_in_sentence=true、matcher_hit=substring、valid=true、coverage=1.0 ⇒ 断言必假
- 结论：**一致**
  - REV7 产物 assertions.A2.pass=False、A3.pass=False
  - A2 occurrence: 患者 item_in_sentence=True / valid=True / coverage=1.0；A3 同（13 次出现全 pos 0）
  - 按 N3 规则 valid = (item in sentence) or coverage>=0.90 ⇒ 两条路径都为真，断言 valid=false 不可能成立
- 备注：这正是 REV7.1 要撤回的断言；rev7.1 产物对应 A2/A3 已 pass=true（真值化）。

### S12 — B5 §8.1 两行「全 0」按字面（本文件计数）为假

- 账本引用位置：`N25 + N26 + X11 (B5:119/130)`
- 账本判定：`mismatch_literal_ok_within_section1（字面假、§1 题面口径为真）`
- 我的复算：字面假成立：专名 5 个各 1 次、租车/物业 各 1 次；§1 题面段内全 0
- 结论：**一致**
  - 全文 count：仁和口腔=1、迅达租车=1、华庭物业=1、北方联通=1、力量方舟=1、租车=1、物业=1
  - §1 段（“## 1”→“## 2”，2,217 B）内：上述 7 个串全部 0 次
  - B5 L119 写“逐字检索本文件出现 0 次”、L130 写“全 0”，而名单本身就在同段表格里
- 备注：账本的口径二分（字面 vs 题面）判断正确；我只抽查了这 7 个破坏字面性的串，未逐个数满 16 领域名。

### S13 — REV7.1 §6 状态行 executed=false，但重跑产物已落盘

- 账本引用位置：`N47 + X07/X15 (REV7.1:160)`
- 账本判定：`mismatch（状态字段过期）`
- 我的复算：mismatch 成立：L160 executed=false；产物 55191eaf2426f736 / 510,508 B 存在
- 结论：**一致**
  - REV7.1 L160 原文含 `executed=false`（同文件 frozen=true / next=b5_acceptance）
  - 产物 sha16=55191eaf2426f736、510,508 B、gate 2/46·4/41·1/261·0/35 与 rev7 逐项同
  - 注：该产物 mtime 现已为 21:24:11（他人复跑，字节不变）；账本快照记的 21:07:27 在 21:18:35 时点为真
- 备注：纯状态字段问题，不影响数值/判定；改写 executed=true 需 LEAD 决定（冻结件不得擅改）。

### S14 — R2 引用的 M5C-36-r1-adj.json / M5C-36-r1-alignment.json 不存在

- 账本引用位置：`X13 (REV4-1/R2 文件名)`
- 账本判定：`更正清单 X13（low）：应去掉 -r1`
- 我的复算：两个 -r1 文件确实不存在；哈希/字节对应无 -r1 的两个文件
- 结论：**一致**
  - M5C-36-r1-adj.json / M5C-36-r1-alignment.json：exists=False
  - M5C-36-adj.json = 0d882f20987fea70 / 60,432 B（= 引用哈希/字节）
  - M5C-36-alignment.json = aaed082264712c59 / 245,640 B（= 引用哈希/字节）
- 备注：账本证据里的“aaed0822/245,640”我复算为 aaed082264712c59，前缀一致。

### S15 — 8-hex 正则误捕随机种子 neg_control_seed=20261026

- 账本引用位置：`C056 (R2:52)`
- 账本判定：`unverifiable / not_a_hash`
- 我的复算：确为随机种子，非哈希：无任何文件或 blob 的 sha16 以 20261026 开头
- 结论：**一致**
  - R2 L52 原文：固定 `neg_control_seed=20261026`，配对表落盘
  - 14,835 文件 + 1,491 blob 扫描：无 sha16=20261026 前缀命中
  - 该值在 RATES 的 bootstrap 记录里作 seed 出现（reps/seed 语义）
- 备注：边界处理正确（账本显式标注“正则误捕”，没有硬凑 match）。

### S16 — README 引 M2-ACCEPT-lead.md「已签 6f26bce0」——不可复算

- 账本引用位置：`C147 + X14 (README:70)`
- 账本判定：`unverifiable（历史签署坐标，字节未保留）`
- 我的复算：不可复算成立：全树 + 全部 git blob 无 6f26bce0；现文件 21ec668df2171350 / 10,479 B
- 结论：**一致**
  - 14,835 文件 + 1,491 blob（--batch-all-objects）扫描：无 sha16=6f26bce0
  - docs/_work/M2-ACCEPT-lead.md = 21ec668df2171350 / 10,479 B（README 已并列写“现场 21ec668d”）
- 备注：账本给的处置（ANCHORS-CURRENT #5）合理；属“历史坐标 vs 现行锚”区分问题。

### S17 — 非文件哈希：prompt 模板 a6bc4f268f7711de、DLL 9edbafa150700614

- 账本引用位置：`C014/C015/C090 (prompt + DLL)`
- 账本判定：`match（由字面量/二进制重算解析）`
- 我的复算：两个值均可复算：REV4_TEMPLATE(266 chars) → a6bc4f26…；kvshim_vk.dll → 9edbafa150700614 / 50,007,552 B
- 结论：**一致**
  - ast 提取 run_m5c2_rev4.py 的 REV4_TEMPLATE 常量（len=266），sha256 utf8 → a6bc4f268f7711de（strip 不变）
  - sha256(tools/kvshim_vk.dll) → 9edbafa150700614 / 50,007,552 B
- 备注：这类“内容坐标”引用账本用重算而非找文件，方法正确。

### S18 — 31/31 数值对，但出处引错文件（ARTIFACT 15 例 + AMEND 否定链），真正的 31 例在 EXPLORATORY

- 账本引用位置：`N17 + X10 (REV4:11「31/31 全 A」)`
- 账本判定：`match_numeric_provenance_loose`
- 我的复算：数值 31/31 成立（EXPLORATORY n_done=31，arm1..5 = 6/6/6/6/7 全 A）；provenance 确实错位
- 结论：**一致**
  - M5C2-FLOOR-GBNF-EXPLORATORY.json：n_done=31 / n_planned=31；arm_rate={1:6A,2:6A,3:6A,4:6A,5:7A} ⇒ 31/31
  - M5C2-FLOOR-ARTIFACT.json：n_done=15、position_bias=false、conclusion 已写 “prior GBNF all-A invalid”
  - M5C2-FLOOR-ARTIFACT-AMEND.json（账本简写 “AMEND”）：position_bias=true、prior_gbnf_all_A_invalidated=true
- 备注：账本把 AMEND 简写为“AMEND”，实际文件名含 -ARTIFACT-；仅为行文简写，不是事实错。

### S19 — INSPECTOR 称「两次重跑与既有产物完全同字节 1f8f44b9 / 507,657 B」；账本判不可复算（按纪律不复跑）

- 账本引用位置：`N38 (INSPECTOR 重跑声明)`
- 账本判定：`numbers_unverifiable（no rerun performed）`
- 我的复算：抽查复跑后：声明成立 ⇒ 可升级为 verified（账本保守但不错）
- 结论：**一致（账本判定保守；抽查升级为已验证）**
  - 临时目录重跑 C32 脚本两次（仅把 ART 重定向到 Temp，不改仓库文件）：两次产物 byte 一致 = d9c4de2657b24759 / 507,657 B
  - 与既有产物差异仅 2 个自指字段（code_sha16、code_bytes，因副本脚本字节不同）；把这两个字段回填为 live 脚本值（65ed60125528d5d6 / 44,761）后，重建字节 sha16 = 1f8f44b921e575fe ✅
  - 既有产物 = worktree = git HEAD blob，三者 byte 相同（1f8f44b9 / 507,657 B）
  - live 脚本 sha16 = 65ed60125528d5d6 = 产物 code_sha16 字段
- 备注：唯一的不可判定点是“当时是否真的跑过两次”；我证明的是“今天跑两次必然得到同一字节”，即可复现性成立。

### S20 — 账本对 REV7.1 状态的两处自述（1) 快照 frozen=false；2) key_findings 称“仍是未冻结草稿且所引实测产物未落盘”）

- 账本引用位置：`scope.rev7_1_snapshot.frozen + key_findings[3]`
- 账本判定：`scope.rev7_1_snapshot={"sha16":"09d6f1b163ea0b84","bytes":16313,"mtime":"21:07:03","frozen":false}；key_findings[3]=“…REV7.1 撤回但仍是未冻结草稿且所引‘实测产物’未落盘”`
- 我的复算：两处均与事实不符：文件是 frozen=true（21:06:55），产物 55191eaf2426f736 / 510,508 B 已于 21:07:27 落盘
- 结论：****分歧（账本内部不一致 + 与事实不符）****
  - live REV7.1：sha256=09d6f1b163ea0b84 / 16,313 B（与快照 sha/bytes 一致）；frozen=true 出现 3 次、frozen=false 0 次
  - 账本自己的 moving_target 对同一文件写 “21:07:03 状态=frozen=true@21:06:55（LEAD 复核通过）”；X07 写“已 frozen=true@21:06:55、产物也已落盘”；N47 以“产物存在”立论 ⇒ 与 frozen=false/key_findings[3] 直接冲突
  - 账本 MD 版（df270b1c）无“未冻结/产物未落盘”字样，且 file-state 表写“21:06:55 被 LEAD 冻结” ⇒ 该错误仅存在于 JSON 的两个字段，疑似旧草稿阶段文本未随 21:07 冻结快照更新
  - 产物存在性：mtime 21:07:27（账本 N47 记），现 mtime 21:24:11（他人复跑，字节不变 55191eaf2426f736）
- 备注：分歧定位：JSON 的 key_findings 文本与 scope.rev7_1_snapshot.frozen 标记停留在 20:58 草稿阶段、未随 21:07 冻结快照刷新；账本的 citations/numbers/moving_target/file_state 四处均正确。修复建议：frozen 改 true、删 key_findings[3] 后半句。

## 4 分歧（仅 S20，2 处同源）

### D1（S20，severity=medium）

- 位置：`M5C2-DOC-HASH-LEDGER.json → scope.rev7_1_snapshot.frozen`
- 账本说：false
- 事实：true（文件内 frozen=true ×3、frozen=false ×0；frozen_at=2026-10-26T21:06:55+08:00；write_state=frozen）
- 推测原因：快照字段来源混用：sha16/bytes 取自 21:07:03 冻结体，frozen 标记沿用 20:58 草稿记录（与账本自身 moving_target 冲突）
- 修复建议：把 frozen 改为 true（或改为读字节后按 frozen_at 判定）

### D2（S20，severity=medium）

- 位置：`M5C2-DOC-HASH-LEDGER.json → key_findings[3]`
- 账本说：“REV7.1 撤回但仍是未冻结草稿且所引‘实测产物’未落盘”
- 事实：REV7.1 已于 21:06:55 冻结，产物 M5C2-REV7-1-OFFLINE.json（55191eaf2426f736 / 510,508 B）已于 21:07:27 落盘；账本 X07/N47/X15 与 moving_target 均按此事实书写
- 推测原因：key_findings 文本写于 20:58 草稿阶段，未随 21:07 冻结快照刷新（MD 版无此句）
- 修复建议：删去“仍是未冻结草稿且所引实测产物未落盘”，改为“已冻结（21:06:55）且产物已落盘（55191eaf），仅 executed=false 状态字段过期”

## 5 全局交叉检查（超出 20 条之外的一致性证据）

- **file_state_22_entries**：22/22 与 live 字节一致（含 B6 json、INSPECTOR、README）
- **git_blob_count**：all-objects blob=1,491 → 与账本 X14 的“1491 个 git blob”一致；可达对象为 1,469
- **B4_git_blob**：B4 路径仅 1 个 blob（1982d167 → f30d89e3），与 X03 一致
- **ledger_hashes**：json 02f43fdde85953c9 / 149,960 B、md df270b1c2c9fc6b7 / 56,701 B —— 与任务给定值一致
- **citations_spot**：8 条引用抽查：8/8 与账本一致（其中 3 条 stale 类我独立复核了“不可重构/可重构/旧值等价”）

## 6 关键发现

- 20 条抽查：19 条与账本一致，仅 1 条（S20）为账本自身对 REV7.1 状态的两处自述错误（frozen=false、key_findings[3]），且与账本自己的 moving_target/X07/N47 矛盾。
- 三处硬核结论我全部独立复现：REV7→(b5) e306ce = 截断+rstrip 11,388 B（raw 11,390 B 是 9c09ceaf）；B5→(b4) e9a88fda 在 14,835 文件 + 1,491 blob + 1,418 个截断变体里都不存在；金标 9054479b 旧字节确不可得但 261 条 gold 逐 sid 等价（0 差异）。
- 6 条数字不一致全部复现（N1 4→3、重叠 1→0、261 行→17,040、A2/A3 不可满足、§8.1 字面全 0、executed=false；另 X13 文件名 -r1 错）。
- 我额外把账本标 unverifiable 的 N38 升级为 verified：重跑两次 byte 一致，回填自指字段后精确重建 1f8f44b921e575fe。
- 账本 22 条 file_state 记录与 live 字节 22/22 一致，说明其哈希采集层没有系统性问题；两个分歧都在“叙述层”而非“数据层”。

## 7 抽查边界（如实声明）

- 未逐条复算全部 151 条引用 / 47 条数字，只抽 20 条；已抽部分无漏判、无误判。
- 全树扫描跳过 42 个 >50 MB 二进制（`build-vulkan/bin/*.exe`、`vulkan-sdk/*.pdb|lib`、`downloads/*.exe`、`out/M5B2-probe.kvmem`）；这些不可能是 10 KB 级 markdown/JSON 的载体，且账本自身也用“全树+全 blob”口径。
- `M5B4-RATES.json` / `M5B4-AB-OLD-VS-NEW.json` 的“时点可信”依赖其自身生成时 gold 坐标（9054479b）；我复算的是“其内嵌 261 条 gold 与现行金标逐 sid 相同”，这是该等价论断可得的最强证据。
- REV7.1 产物的 mtime 在我抽查期间从 21:07:27 变为 21:24:11（他人复跑，字节仍为 55191eaf2426f736）；账本快照的 mtime 在其时点为真。

