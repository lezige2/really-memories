# ERRATA-M5C2 —— 冻结构文档↔代码/产物错述集中勘误

> **性质**：只读汇集；**未改动任何冻结字节**（不带 rev7.1/B5/B6/REV7 原件），未跑 GPU，未联网，未 git 提交。
> **生成**：2026-10-26T22:01:06+0800 ｜ 机读件：`kvmem/m2_visibility/m5/out/ERRATA-M5C2.json` ｜ 条目 **13** 条（high 1 / medium 5 / low 7）。
> **冻结**：`frozen=true` · `frozen_rev=1` · `frozen_at=2026-10-26T22:15:00+08:00` · `frozen_by=LEAD`（b5 生成开跑前冻结）。
> **不自钉**：本件**不写自身 sha16/sha256**（避免 FD-8 自指不可复算问题）；**外钉由 LEAD 在 RULING/账本记录**。

## 0 结论

- 全部为**文档措辞/字段名/时间戳/枚举**级错述；**没有一条改变可用读数或 b5 准入**。
- 冻结件自身不能改 → 一律进 ERRATA（集中记录），**b5 前不重钉**（重钉会动 b5 前置条件，反而违规）。
- “必须重钉”清单 = **空**；条件重钉见 §5。
- **CLAIM-MAP 子集**：claim-map 5 条 fail 单独成节（§7，`affects_result` 全部 = **no**），另收 REV7 原件 N1=4/重叠 1 例、N3“与上重叠”、A2/A3 不可满足（陈述性）。
- **规则段未变证明**：rev7.1（`88256d27…`）与 rev7（`65ed6012…`）的 15 个判定函数（含内联 `gate_item`）**逐字节相等**、规则段 diff=0，见 §8；故 **B5.1 重钉 = 0 条**（§9）。

## 1 输入（只读，哈希自核）

| 输入件 | sha16 | 字节 |
|---|---|---|
| `kvmem/m2_visibility/m5/out/M5C2-REV7-1-CLAIM-MAP.json` | `2923b0abf896eac7` | 101305 |
| `kvmem/m2_visibility/m5/out/M5C2-REV7-1-AUDIT.json` | `64ad2b4e27c7812d` | 44528 |
| `kvmem/m2_visibility/m5/out/M5C2-FREEZE-DISCIPLINE.json` | `0e9398edf6402db7` | 41355 |
| `kvmem/m2_visibility/m5/out/M5C2-DOC-HASH-LEDGER.json` | `b8efdb09b215f0c5` | 152796 |

### 1.1 与任务清单的对应（10/10 覆盖 + 3 条同类附加）

| 任务项 | 要求 | ERRATA |
|---|---|---|
| 1 | `rev7_1_unusable` 字段名不存在（产物 gate 字段是 `rev7_unusable`；语义 false 一致） | E01 |
| 2 | rev7.1 §6 `executed=false` 但产物已落盘（21:07/21:28） | E02 |
| 3 | B5 §8.2（rev6+rev6.1）vs §9.1（rev5.1+rev7，永久排除 rev6）内部冲突，仅 R4 消解 | E03 |
| 4 | B5 §9 标题 20:20 vs mtime 19:54:15/frozen_at 19:55；REV7 frozen_at 20:15 vs 入库 19:59:10 → 时间戳不可作时序证据 | E04, E05 |
| 5 | B6 frozen_at 21:16:03 vs mtime 21:16:37（+34 s） | E05 |
| 6 | REV7 N1=4 / “重叠 1 例”（rev7.1 §A.6 supersede，需指向 `09d6f1b1…`） | E06 |
| 7 | rev7.1 产物自钉 code_sha16/code_bytes ⇒ 仓库外 byte 级不可达（FD-8） | E07 |
| 8 | `M5B4-RATES.md:4` / `M5B4-AB-OLD-VS-NEW.md:5` 旧 gold `9054479b`/10,208 B 不可得（261 条 gold 逐 sid 等价） | E08 |
| 9 | `A2p_r1_home.json d0b360ec→a793c7bd`、`M2-ACCEPT-lead.md 6f26bce0→21ec668d`（历史值保留+现值并列） | E09 |
| 10 | 冻结记录普遍不自钉（0/20 PREREG；独立扫描 0/26）— 结构性建议，非错误 | E10 |
| 额外 | claim-map 另外 3 条 fail（B1 函数数 14→15 / 头注 no GPU runner / §4 枚举 N4）同属冻结构错述，一并入册 | E11, E12, E13 |

## 2 总表

| # | 严重度 | 文档:行 | 一句话 | 影响读数 | 影响复算 | 影响 b5 准入 |
|---|---|---|---|---|---|---|
| E01 | medium | `docs/_work/PREREG-M5-C2-REV7.1.md:72` | rev7.1 §3 门槛写 `rev7_1_unusable=false` ⇒ (b5) 准入（同句/§3.4/§5 共 3 处：L72、L | 无 | 数值级可复算（字段名 solecism） | 无（准入结论不变） |
| E02 | low | `docs/_work/PREREG-M5-C2-REV7.1.md:160` | §6 状态行：`executed=false`（写于冻结时 21:06:55）。 | 无 | 数值级可复算（状态位滞后，数值不变） | 无 |
| E03 | medium | `docs/_work/PREREG-M5-C2-B5.md:140` | §8.2 冻结决定（L140）：判据侧须为 **rev6（抽取 prompt 逐字复制）+ rev6.1（融合核验器）**。 | 无 | 数值级可复算（判据组成需读 R4） | 无（需登记 R4 为前置） |
| E04 | medium | `docs/_work/PREREG-M5-C2-B5.md:143` | B5 §9 标题声明 `2026-10-26T20:20+08:00`；REV7 头注声明 `frozen_at=2026-10-26T20 | 无 | 文档级（时间戳声明不可作证据） | 无 |
| E05 | low | `docs/_work/PREREG-M5-C2-B6.md:146` | B6 §8 冻结记录：`frozen_at=2026-10-26T21:16:03+08:00`。 | 无 | 文档级（声明时刻差 34 s） | 无 |
| E06 | high | `docs/_work/PREREG-M5-C2-REV7.md:15` | REV7 §0 归因表：N1 = **4** 例（列 3 个 sid）、N3 行 `2（与上重叠 1 例）`（L17）。 | 无 | 数值级可复算（rev7.1 §A.6 已更正 3/2/2） | 无 |
| E07 | medium | `kvmem/m2_visibility/m5/out/M5C2-REV7-1-OFFLINE.json（code_sha16/code_bytes 字段）` | 产物自钉 `code_sha16=88256d274c9993cc` / `code_bytes=50618`，可据此断言“由该脚本产生”。 | 无 | 数值级可复算（字节级不可达） | 无 |
| E08 | low | `kvmem/m2_visibility/m5/out/M5B4-RATES.md:4` | RATES.md:4 与 M5B4-AB-OLD-VS-NEW.md:5 引旧金标 `M5B4-LEAD-RULING.json 90544 | 无 | 数值级可复算（旧字节不可得、gold 逐 sid 等价） | 无 |
| E09 | low | `PROGRESS-AND-ROADMAP.md:1930（旧值）/3625（现值并列）；README.md:70` | 历史锚：`A2p_r1_home.json` 旧值 `d0b360ec444ebc3f`（PROGRESS-AND-ROADMAP.md:1 | 无 | 文档级（旧字节不可得；现值可核） | 无 |
| E10 | medium | `docs/_work/PREREG-*.md（结构性：20/20 冻结 PREREG 不自钉）` | 冻结件以 `frozen=true/frozen_at` 声明身份，但**不自钉自身 sha16**（FD-2：0/20 冻结 PREREG | 无 | 文档级（结构性：不自钉） | 无 |
| E11 | low | `docs/_work/PREREG-M5-C2-REV7.1.md:140` | 附录 B：其余 **14** 个函数逐字节相同（排除 verify_inputs/main/item_assertion/verdict_a | 无 | 数值级可复算（实测 15 而非 14） | 无 |
| E12 | low | `docs/_work/PREREG-M5-C2-REV7.1.md:7` | §0 引用脚本头注：“no engine / no GPU runner”。 | 无 | 数值级可复算（import 可达 / 0 调用） | 无 |
| E13 | low | `docs/_work/PREREG-M5-C2-REV7.1.md:83` | §4：`false_by_reason` schema 同 REV7 §4 —— 枚举 `N1/N2/N3/N4/R4+/declared/ | 无 | 数值级可复算（N4 未实现） | 无 |

## 3 逐条

### E01 ｜ medium ｜ `docs/_work/PREREG-M5-C2-REV7.1.md:72`

- **声称**：rev7.1 §3 门槛写 `rev7_1_unusable=false` ⇒ (b5) 准入（同句/§3.4/§5 共 3 处：L72、L75、L96）。
- **实际**：产物 gate 无 `rev7_1_unusable` 字段；实际字段为 `rev7_unusable`（值 false）。脚本 `run_m5c2_rev7_1_offline.py:829` 写 `gate["rev7_unusable"]`。
- **证据**：gate.keys=['false_positive', 'leak_missed', 'parse_fail', 'new_miss', 'false_positive_sids', 'leak_missed_sids', 'parse_fail_sids', 'new_miss_sids', 'any_fail', 'rev7_unusable', 'rev7_unusable_basis']；rev7_1_unusable in gate=False；gate.rev7_unusable=False；脚本 L829 = gate["rev7_unusable"] = bool(gate["any_fail"])。
- **影响**：读数：无；可复算：数值级可复算（字段名 solecism）；b5 准入：无（准入结论不变）
- **处置**：ERRATA 记录；若出 rev7.2，统一字段名为 `rev7_unusable`（或文档改述旧名）。b5 前不改冻结件。
- **依据**：claim_map:C3-UNUSABLE-FIELD, artifact gate, script L829

### E02 ｜ low ｜ `docs/_work/PREREG-M5-C2-REV7.1.md:160`

- **声称**：§6 状态行：`executed=false`（写于冻结时 21:06:55）。
- **实际**：重跑产物已落盘：55191eaf2426f736 / 510508 B，mtime 2026-10-26T21:28:52（首次生成 21:07:27，二次重跑 21:28:52，字节相同 55191eaf…）；晚于冻结时刻。
- **证据**：产物 sha16=55191eaf2426f736 与 claim-map/audit 输入一致；audit 64ad2b4e 独立复算 gate 一致；冻结件不可改故状态位必然滞后。
- **影响**：读数：无；可复算：数值级可复算（状态位滞后，数值不变）；b5 准入：无
- **处置**：ERRATA；在产物/账本侧补记 `executed_at=2026-10-26T21:07:27+08:00`（首次）/21:28:52（二次），不改冻结件。
- **依据**：claim_map:C6-EXECUTED, freeze_discipline:FD-3, ledger:N47

### E03 ｜ medium ｜ `docs/_work/PREREG-M5-C2-B5.md:140`

- **声称**：§8.2 冻结决定（L140）：判据侧须为 **rev6（抽取 prompt 逐字复制）+ rev6.1（融合核验器）**。
- **实际**：同一冻结件 §9.1（L146–L149）：抽取层 = rev5.1 prompt（a6bc4f26…），判定层 = rev7（32eaf82c…），并**永久排除 rev6**（`faaf2605` not_adopted）。两种判据组成互斥。
- **证据**：B5=d6c7bdac73ef7326/14597 B；§8.2 L140 vs §9.1 L146–L149 逐字对读；消解仅见 `RULING-M5C2-B5-FREEZE.md` R4（非 B5 本体）。
- **影响**：读数：无；可复算：数值级可复算（判据组成需读 R4）；b5 准入：无（需登记 R4 为前置）
- **处置**：ERRATA + 指向 RULING R4；若出 B5.1，合并 §8.2 与 §9.1（但 b5 前不得改判据区）。
- **依据**：freeze_discipline:FD-1 ④, RULING-M5C2-B5-FREEZE R4

### E04 ｜ medium ｜ `docs/_work/PREREG-M5-C2-B5.md:143`

- **声称**：B5 §9 标题声明 `2026-10-26T20:20+08:00`；REV7 头注声明 `frozen_at=2026-10-26T20:15:00+08:00`。
- **实际**：B5 mtime=2026-10-26T19:54:15（< frozen_at 19:55）；`full@5574253`（2026-10-26 **19:59:10** +0800）内的 B5 blob 已含 §9（`d6c7bdac73ef7326`/14,597 B）；REV7 声明 `frozen_at=20:15` **晚于**其首次入库 commit `5574253`（19:59:10）⇒ 声明时刻晚于字节入库时刻，声明时间不可作时序证据。注：同一批 blob 在我方 C32 归档提交 `4d3d822`（21:44:14）被原样重提交，**不代表** 21:44 才写入。
- **证据**：`git cat-file -p full:docs/_work/PREREG-M5-C2-B5.md`=d6c7bdac73ef7326/14,597 B 且含 `## 9 LEAD 追加`；full commit 时间 19:59:10；B5 mtime=19:54:15；REV7 §3 frozen_at=20:15。
- **影响**：读数：无；可复算：文档级（时间戳声明不可作证据）；b5 准入：无
- **处置**：ERRATA（R7 纪律：声明时间 + mtime + git commit 三坐标）；b5 前不改。
- **依据**：freeze_discipline:FD-1 ⑤/FD-5, git full 5574253

### E05 ｜ low ｜ `docs/_work/PREREG-M5-C2-B6.md:146`

- **声称**：B6 §8 冻结记录：`frozen_at=2026-10-26T21:16:03+08:00`。
- **实际**：B6 mtime=2026-10-26T21:16:37（比声明晚 34 s）。
- **证据**：B6 md=ac27d47d3a3efff9/17374 B；json.prereg_sha16=ac27d47d3a3efff9（md==json 互证，内容自洽）；仅冻结声明的时刻与最后一次落盘差 34 s。
- **影响**：读数：无；可复算：文档级（声明时刻差 34 s）；b5 准入：无
- **处置**：ERRATA；B6.1 或下次冻结记录同时写 mtime；b5 前不改。
- **依据**：freeze_discipline:FD-4, claim_map

### E06 ｜ high ｜ `docs/_work/PREREG-M5-C2-REV7.md:15`

- **声称**：REV7 §0 归因表：N1 = **4** 例（列 3 个 sid）、N3 行 `2（与上重叠 1 例）`（L17）。
- **实际**：实测 N1=**3**（b4-s1-q2-s01 / -s15、b4-s1-q3-s03）；N1/N2/N3 互不重叠（7 = 3+2+2）；REV7.1 §A.6（L129–L134）已更正并在产物中复算 3/2/2。
- **证据**：REV7 原件 L15/L17 逐字对读；rev7.1 A.6 L132「new：N1 3 例 / N2 2 例 / R3 2 例（互不重叠）」；rev7.1 产物 false_by_reason 归因计数 3/2/2。
- **影响**：读数：无；可复算：数值级可复算（rev7.1 §A.6 已更正 3/2/2）；b5 准入：无
- **处置**：ERRATA 指向 REV7.1 §A.6（09d6f1b1…）；若 REV7 仍需被独立引用，出 rev7.2 修正表；b5 前不改。
- **依据**：claim_map, ledger:X01/X02, REV7.1 A.6

### E07 ｜ medium ｜ `kvmem/m2_visibility/m5/out/M5C2-REV7-1-OFFLINE.json（code_sha16/code_bytes 字段）`

- **声称**：产物自钉 `code_sha16=88256d274c9993cc` / `code_bytes=50618`，可据此断言“由该脚本产生”。
- **实际**：仓库外重跑同一逻辑得到 7cf178a4f4814c7a / 510,508 B：58/60 顶层键相同，差异仅 provenance 与自指字段（code_sha16/code_bytes，因 ROOT 路径长度变化 +25 B）。
- **证据**：FREEZE-DISCIPLINE FD-8（重跑 exit=0、两次重跑 byte 一致、diff_keys=['schema', 'prereg_sha16', 'code_sha16', 'code_file', 'code_bytes', 'inputs', 'assertions']）。
- **影响**：读数：无；可复算：数值级可复算（字节级不可达）；b5 准入：无
- **处置**：ERRATA 记录口径（数值级复算合格、字节级不可达）；未来产物提供“期望 code_sha16 对照”或改不含自哈希的判定层脚本。
- **依据**：freeze_discipline:FD-8, ledger

### E08 ｜ low ｜ `kvmem/m2_visibility/m5/out/M5B4-RATES.md:4`

- **声称**：RATES.md:4 与 M5B4-AB-OLD-VS-NEW.md:5 引旧金标 `M5B4-LEAD-RULING.json 9054479b32b79eb1 / 10,208 B`。
- **实际**：现行金标 = 9273ebc97aa1413a / 13,195 B；旧版字节未入树/未入 git（不可重构），但 261 条 gold 逐 sid 相同（0 差异）⇒ 4/41、7/46 等读数等价。
- **证据**：现文件 sha256 前缀 9273ebc9；ledger 复算 261 sid 全等；旧值在 1,491 个 git blob 与全树均无命中。
- **影响**：读数：无；可复算：数值级可复算（旧字节不可得、gold 逐 sid 等价）；b5 准入：无
- **处置**：ERRATA 双坐标并列（旧值保留 + 现值 + 等价说明）；不改 RATES/AB 冻结读数。
- **依据**：ledger:stale_unresolved, RATES:4, AB:5

### E09 ｜ low ｜ `PROGRESS-AND-ROADMAP.md:1930（旧值）/3625（现值并列）；README.md:70`

- **声称**：历史锚：`A2p_r1_home.json` 旧值 `d0b360ec444ebc3f`（PROGRESS-AND-ROADMAP.md:1930）、`M2-ACCEPT-lead.md` 已签 `6f26bce0`（README.md:70）。
- **实际**：现值：`kvmem/m2_visibility/m14b_e10_probe/out/A2p_r1_home.json` = a793c7bd0fbba4f2 / 9,512 B；`docs/_work/M2-ACCEPT-lead.md` = 21ec668df2171350 / 10,479 B。旧值 d0b360ec / 6f26bce0 在全树与全部 git blob 中无对应字节（不可复算）。
- **证据**：两文件现 sha16 实测；`grep d0b360ec/6f26bce0` 命中处均标 stale/不可复算（ROADMAP-CONSISTENCY REF-01/S14/R7；ledger X14）。
- **影响**：读数：无；可复算：文档级（旧字节不可得；现值可核）；b5 准入：无
- **处置**：ERRATA：保留历史值 + 并列现值 + 标“旧字节不可得”（README/INDEX 已是此写法，建议统一到 errata 索引）。
- **依据**：ledger, ROADMAP-CONSISTENCY REF-01/S14

### E10 ｜ medium ｜ `docs/_work/PREREG-*.md（结构性：20/20 冻结 PREREG 不自钉）`

- **声称**：冻结件以 `frozen=true/frozen_at` 声明身份，但**不自钉自身 sha16**（FD-2：0/20 冻结 PREREG 自钉）。
- **实际**：我独立扫描：docs/_work 下 PREREG*.md 共 26 个，含自身当前 sha16 的 0 个；FD inventory：31 个冻结文档 / 20 个冻结 PREREG / 自钉 0。
- **证据**：逐文件 sha256[:16] 是否出现在自身文本（0/26 命中）；B6 已改用“零自指 + json.prereg_sha16=md 哈希”闭环（例外）。
- **影响**：读数：无；可复算：文档级（结构性：不自钉）；b5 准入：无
- **处置**：结构性建议（非错误）：后续冻结件二选一——①自钉 + 变更表，或 ②零自指 + 机读件钉 md 哈希（B6 模式）；现有冻结件不改。
- **依据**：freeze_discipline:FD-2, 我的独立扫描

### E11 ｜ low ｜ `docs/_work/PREREG-M5-C2-REV7.1.md:140`

- **声称**：附录 B：其余 **14** 个函数逐字节相同（排除 verify_inputs/main/item_assertion/verdict_assertion）。
- **实际**：实测逐字节相同 = **15**（我独立比对：common=17，same=15，含嵌套 `gate_item`；差异仅 verify_inputs/main 与新增 2 个断言函数），文档漏列 `gate_item`。
- **证据**：逐函数块（含嵌套 def，按缩进边界截块后 sha256）比对：same=15；gate_item_in_identical=True。
- **影响**：读数：无；可复算：数值级可复算（实测 15 而非 14）；b5 准入：无
- **处置**：ERRATA（或 rev7.2 改 15）；不改冻结件。
- **依据**：claim_map:B1-COUNT, 我的独立复算

### E12 ｜ low ｜ `docs/_work/PREREG-M5-C2-REV7.1.md:7`

- **声称**：§0 引用脚本头注：“no engine / no GPU runner”。
- **实际**：脚本经 R5_1→R5→R4_1 传递 import `_e3gpu_run`（可达），但 **0 次前向调用**；产物 `no_gpu/no_model_call/no_network/no_forward` 均为 true。
- **证据**：run_m5c2_rev4_1.py 的 import 列表含 `_e3gpu_run`；脚本 forward( 计数=0；产物 flags 全 true。
- **影响**：读数：无；可复算：数值级可复算（import 可达 / 0 调用）；b5 准入：无
- **处置**：ERRATA：措辞改“import 可达但未调用/未前向”；不改冻结件。
- **依据**：claim_map:H-IMPORT-CLAIM, import chain

### E13 ｜ low ｜ `docs/_work/PREREG-M5-C2-REV7.1.md:83`

- **声称**：§4：`false_by_reason` schema 同 REV7 §4 —— 枚举 `N1/N2/N3/N4/R4+/declared/other`。
- **实际**：实现 `pick_attribution`（L533–L548）无 N4 分支（N4 仅在 docstring 出现）；产物 `false_by_reason` 归因集合 = ['N1', 'N2', 'N3']。
- **证据**：pick_attribution 返回值仅 N1/N2/N3/R4+/declared/other；产物 attributions 集合=['N1', 'N2', 'N3']；独立审计亦标为 documentation/audit-label only。
- **影响**：读数：无；可复算：数值级可复算（N4 未实现）；b5 准入：无
- **处置**：ERRATA（文档枚举改“N1/N2/N3/R4+/declared/other（N4 未实现）”）；不改冻结件。
- **依据**：claim_map:C4-N4-ENUM, 我的独立抽查

## 4 影响面矩阵（读数 / 证据可复算 / b5 准入）

| # | 影响读数？ | 影响证据可复算？ | 影响 b5 准入？ |
|---|---|---|---|
| E01 | 无 | 数值级可复算（字段名 solecism） | 无（准入结论不变） |
| E02 | 无 | 数值级可复算（状态位滞后，数值不变） | 无 |
| E03 | 无 | 数值级可复算（判据组成需读 R4） | 无（需登记 R4 为前置） |
| E04 | 无 | 文档级（时间戳声明不可作证据） | 无 |
| E05 | 无 | 文档级（声明时刻差 34 s） | 无 |
| E06 | 无 | 数值级可复算（rev7.1 §A.6 已更正 3/2/2） | 无 |
| E07 | 无 | 数值级可复算（字节级不可达） | 无 |
| E08 | 无 | 数值级可复算（旧字节不可得、gold 逐 sid 等价） | 无 |
| E09 | 无 | 文档级（旧字节不可得；现值可核） | 无 |
| E10 | 无 | 文档级（结构性：不自钉） | 无 |
| E11 | 无 | 数值级可复算（实测 15 而非 14） | 无 |
| E12 | 无 | 数值级可复算（import 可达 / 0 调用） | 无 |
| E13 | 无 | 数值级可复算（N4 未实现） | 无 |

**汇总**：读数影响 = **0 条**；证据可复算：数值级仍可复算 **9** 条、仅文档/声明级 **4** 条（E07 另注“字节级不可达”）；b5 准入影响 = **0 条**（E03 仅需把 R4 登记为前置）。

## 5 处置建议：ERRATA 集中记录 vs 重钉

**默认：ERRATA（集中记录，b5 前不重钉）。**

- 理由：13/13 条不影响读数（其中 9 条数值级仍可复算、4 条仅文档/声明级）；b5 准入影响为 0。重钉会改冻结字节，反而破坏“冻结后不改”纪律，且 b5 前置条件（题面/源文/判据）在 b5 前不得动。
- **必须在 b5 前重钉的条目：无**（`must_repin_before_b5=[]`）。

**条件重钉（不建议在 b5 前做）**

- 若外部专家要求冻结件“文本自洽” ⇒ 涉及 E01, E03, E06, E11, E12, E13；做法：出 rev7.2 / B5.1 / B6.1（新哈希、保留旧件），**在 b5 之后**；b5 题面/源文/判据区不得改
- 若外部专家要求字节级 clean-room 复现 ⇒ 涉及 E07；做法：改产物生成侧（记录期望 code_sha16 供外部比对，或判定层脚本去自哈希）；不改冻结件
- 若要求冻结时间可核 ⇒ 涉及 E04, E05；做法：下次冻结记录同时写 mtime 与 git commit；REV7 声明时间不可改（已入库）

**登记约束**：ERRATA 不能写入冻结字节；建议 LEAD 在 RULING/账本维护“errata 索引”，每条指向本文件 E0x。

## 6 关键复算命令（任何人可重跑）

```bash
# B5 §9 是否早于冻结（mtime / git 双证）
stat -c '%y' docs/_work/PREREG-M5-C2-B5.md
git cat-file -p full:docs/_work/PREREG-M5-C2-B5.md | sha256sum | cut -c1-16   # d6c7bdac73ef7326
git show -s --format='%h %ci' full      # 5574253 2026-10-26 19:59:10

# 字段名错述（E01）
python -X utf8 -c "import json;g=json.load(open('kvmem/m2_visibility/m5/out/M5C2-REV7-1-OFFLINE.json'))['gate'];print(list(g));print(g.get('rev7_unusable'), 'rev7_1_unusable' in g)"

# 函数逐字节相同数（E11，含嵌套 gate_item）：见 out/m5c2_rev7_1_claim_map.py 的 static_ref 检查（本次独立复算 same=15，diff 仅 main/verify_inputs）
```

## 7 CLAIM-MAP-ERRATA（`M5C2-REV7-1-CLAIM-MAP.json` 5 条 fail 子集）

> 来源：claim-map `2923b0abf896eac7`（84 claims / 76 pass / **5 fail** / 3 unverifiable）。每条标 **`affects_result`**（顾问硬要求）。另有 2 条陈述性（CM06/CM07）。

| # | claim_id | 严重度 | 位置 | 一句话 | affects_result |
|---|---|---|---|---|---|
| CM01 | `C3-UNUSABLE-FIELD` | medium | `docs/_work/PREREG-M5-C2-REV7.1.md:72` | §3 写 `rev7_1_unusable=false` ⇒ (b5) 准入。 | **no** |
| CM02 | `C4-N4-ENUM` | low | `docs/_work/PREREG-M5-C2-REV7.1.md:83` | §4 声明 false_by_reason 枚举含 N4。 | **no** |
| CM03 | `C6-EXECUTED` | low | `docs/_work/PREREG-M5-C2-REV7.1.md:160` | §6 状态行 `executed=false`。 | **no** |
| CM04 | `H-IMPORT-CLAIM` | low | `docs/_work/PREREG-M5-C2-REV7.1.md:7` | §0 引脚本头注“no engine / no GPU runner”。 | **no** |
| CM05 | `B1-COUNT` | low | `docs/_work/PREREG-M5-C2-REV7.1.md:140` | 附录 B.1：其余 14 个函数逐字节相同。 | **no** |
| CM06 | `REV7-S0-ATTR（陈述性）` | high | `docs/_work/PREREG-M5-C2-REV7.md:15,17` | REV7 原件 §0：N1 = 4 例（列 3 sid）；N3 行“2（与上重叠 1 例）”。 | **no** |
| CM07 | `REV7-A2A3（陈述性）` | medium | `docs/_work/PREREG-M5-C2-REV7.md:36-40` | REV7 §2 断言 A2/A3：`患者` 必判 valid=false。 | **no** |

### CM01 ｜ `C3-UNUSABLE-FIELD` ｜ medium ｜ affects_result=**no**

- **声称**：§3 写 `rev7_1_unusable=false` ⇒ (b5) 准入。
- **实际**：产物 gate 字段实为 `rev7_unusable`（false）；无 `rev7_1_unusable`；脚本 L829 写旧名。
- **证据**：claim-map C3 fail；gate.keys 含 rev7_unusable、rev7_unusable_basis；四门槛 2/46、4/41、1/261、0/35 全过。
- **影响**：读数：无；可复算：数值级可复算；b5 准入：无
- **处置**：ERRATA（E01）；字段名统一留待 rev7.2。

### CM02 ｜ `C4-N4-ENUM` ｜ low ｜ affects_result=**no**

- **声称**：§4 声明 false_by_reason 枚举含 N4。
- **实际**：实现 pick_attribution 无 N4 分支（N4 仅在 docstring）；产物归因集合 {N1,N2,N3}。
- **证据**：claim-map C4 fail；pick_attribution L533–548；产物 false_by_reason attributions=[N1,N2,N3]。
- **影响**：读数：无；可复算：数值级可复算；b5 准入：无
- **处置**：ERRATA（E13）；文档枚举改“N4 未实现”。

### CM03 ｜ `C6-EXECUTED` ｜ low ｜ affects_result=**no**

- **声称**：§6 状态行 `executed=false`。
- **实际**：产物 55191eaf2426f736/510508 B 已落盘（mtime 2026-10-26T21:28:52），晚于 frozen_at 21:06:55；状态位滞后。
- **证据**：claim-map C6 fail；FD-3；audit 独立复算 gate 一致。
- **影响**：读数：无；可复算：数值级可复算（状态位滞后，数值不变）；b5 准入：无
- **处置**：ERRATA（E02）；账本侧补 executed_at。

### CM04 ｜ `H-IMPORT-CLAIM` ｜ low ｜ affects_result=**no**

- **声称**：§0 引脚本头注“no engine / no GPU runner”。
- **实际**：R5_1→R5→R4_1 传递 import `_e3gpu_run`（可达），但 0 次前向调用；产物 no_gpu/no_model_call/no_network/no_forward 全 true。
- **证据**：claim-map H-IMPORT fail；run_m5c2_rev4_1.py import 列表含 _e3gpu_run；forward( 计数=0。
- **影响**：读数：无；可复算：数值级可复算（import 可达 / 0 调用）；b5 准入：无
- **处置**：ERRATA（E12）；措辞改“import 可达但未调用”。

### CM05 ｜ `B1-COUNT` ｜ low ｜ affects_result=**no**

- **声称**：附录 B.1：其余 14 个函数逐字节相同。
- **实际**：实测 15（含嵌套 gate_item）；我独立复算 same=15，diff 仅 main/verify_inputs，新增 item_assertion/verdict_assertion。
- **证据**：claim-map B1 fail；本次逐函数原文切片 sha256 复算；audit code_audit.n_identical=15。
- **影响**：读数：无；可复算：数值级可复算（15>14，规则零改动结论不变）；b5 准入：无
- **处置**：ERRATA（E11）；rev7.2 改 15。

### CM06 ｜ `REV7-S0-ATTR（陈述性）` ｜ high ｜ affects_result=**no**

- **声称**：REV7 原件 §0：N1 = 4 例（列 3 sid）；N3 行“2（与上重叠 1 例）”。
- **实际**：N1=3（3 个 sid 自洽）；N3 两例与 N2 无重叠、各自独立句；7 = 3+2+2。REV7.1 §A.6 已更正（09d6f1b1…）。
- **证据**：ledger X01/X02；REV7.1 A.6 L129–L134 明确“old 4 / new 3”；rev7.1 产物 false_by_reason 逐 sid 3/2/2。
- **影响**：读数：无（总数 7 正确）；可复算：数值级可复算（rev7.1 A.6）；b5 准入：无
- **处置**：ERRATA（E06）；REV7 不再被直接引用为判定件，指向 REV7.1 A.6。

### CM07 ｜ `REV7-A2A3（陈述性）` ｜ medium ｜ affects_result=**no**

- **声称**：REV7 §2 断言 A2/A3：`患者` 必判 valid=false。
- **实际**：按同件 N3 字面定义不可满足（句首“患者：”逐字存在）⇒ 产物 A2/A3 pass=false；REV7.1 以真断言替代（允许类别③），A2/A3 观测口径不变。
- **证据**：ledger X06（high）；rev7.1 ASSERT_A2/A3 改真值断言；rev7.1 产物 assertions 全 pass。
- **影响**：读数：无；可复算：数值级可复算（rev7.1 真断言）；b5 准入：无
- **处置**：ERRATA（陈述性）；不重钉 REV7，指向 REV7.1 断言段。

## 8 「规则段未变」证明（顾问硬条件）

**主张**：run_m5c2_rev7_1_offline.py `88256d274c9993cc` 中 N1–N4 判定函数与 rev7 `65ed60125528d5d6` 对应函数逐字节相等（含 gate_item 内联函数）；规则段 diff 为空。

| 校验项 | 值 |
|---|---|
| rev7.1 脚本 | `kvmem/m2_visibility/m5/run_m5c2_rev7_1_offline.py` / `88256d274c9993cc` / 50618 B |
| rev7 脚本 | `kvmem/m2_visibility/m5/run_m5c2_rev7_offline.py` / `65ed60125528d5d6` / 44761 B |
| 函数总数（rev7 / rev7.1） | 17 / 19 |
| 逐字节相同 | **15** 个（含内联 `gate_item`：✓ / nested_gate_item_identical=True） |
| 允许差异 | `main`, `verify_inputs`（+ 新增 `item_assertion`, `verdict_assertion`） |
| **规则段 diff** | **0 行差异（空）** |
| 产物旗标 | `rule_code_unchanged=True` |
| 独立审计交叉 | `_rev7_1_audit.py`/audit JSON：n_identical=15、nested_gate_item_identical=True、imports_identical=True、PURE_PATTERNS/ENTITY_PATTERN identical={'PURE_PATTERNS': True, 'ENTITY_PATTERN': True} |

**逐函数原文切片 sha256（两侧相等）**

| 函数 | sha16 | 字节 | 相等 |
|---|---|---|---|
| `baseline_reproduce` | `db8e36b8fe0f4941` | 4199 | ✓ |
| `char_evidence` | `cc6934d3bba078cf` | 1074 | ✓ |
| `gate_item` | `5b234501f97b1bf4` | 292 | ✓ |
| `judge_row_rev7` | `525503e0d0f85502` | 2756 | ✓ |
| `matcher` | `ab08de325e4f7f14` | 294 | ✓ |
| `normalize7` | `d7a4593b013983f2` | 234 | ✓ |
| `pick_attribution` | `efe0294e175d7e8f` | 506 | ✓ |
| `r1_r2_r3_rev7` | `7ad2a016dfc395ea` | 2802 | ✓ |
| `r4_plus_rev7` | `37a14385f4658d12` | 918 | ✓ |
| `rev7_causes` | `061c875d375f5117` | 1072 | ✓ |
| `sha16` | `e35507310833a7e1` | 59 | ✓ |
| `token_kind_of_span` | `39298a409009c521` | 289 | ✓ |
| `value_tokens` | `5a1922e4094e6fb1` | 763 | ✓ |
| `verdict_v51` | `fcb192e873c3170f` | 510 | ✓ |
| `write_json_atomic` | `305f7a01ccf57257` | 228 | ✓ |

**结论**：规则段 diff 为空 / 判定函数字节不变；N1–N4 的定义、阈值（0.8/0.9）、词表（PURE_PATTERNS/ENTITY_PATTERN）、金标、输入均未改。

**复算命令**（在仓库根执行；只读）

```bash
python -X utf8 - <<'PY'
import re, hashlib, difflib
A_F = "kvmem/m2_visibility/m5/run_m5c2_rev7_1_offline.py"
B_F = "kvmem/m2_visibility/m5/run_m5c2_rev7_offline.py"
def blocks(p):
    ls = open(p, encoding="utf-8").read().split(chr(10)); out = {}
    for i, l in enumerate(ls):
        m = re.match(r"^(\s*)def\s+(\w+)\s*\(", l)
        if not m: continue
        base = len(m.group(1)); blk = [l]
        for n in ls[i+1:]:
            if not n.strip(): blk.append(n); continue
            if len(n) - len(n.lstrip()) <= base: break
            blk.append(n)
        while blk and not blk[-1].strip(): blk.pop()
        out[m.group(2)] = chr(10).join(blk)
    return out
a, b = blocks(A_F), blocks(B_F)
same = sorted(k for k in set(a) & set(b) if a[k] == b[k])
diff = sorted(k for k in set(a) & set(b) if a[k] != b[k])
print("identical:", len(same), same)
print("differing:", diff)
for k in same: print(k, hashlib.sha256(a[k].encode()).hexdigest()[:16], len(a[k].encode()))
sa = chr(10).join(a[k] for k in same); sb = chr(10).join(b[k] for k in same)
dl = [x for x in difflib.unified_diff(sb.split(chr(10)), sa.split(chr(10)), lineterm="") if x.startswith(("+", "-")) and not x.startswith(("+++", "---"))]
print("rule_segment_diff_lines:", len(dl))  # 期望 0
PY
```

## 9 B5.1 重钉判定（是否触及 N1–N4 定义/阈值/词表/金标/输入）

**必须开 B5.1 的条目：无（`required=[]`）。**

- 理由：没有任何一条 errata 触及 N1–N4 的定义/阈值/词表/金标/输入（规则段 diff 为空、判定函数字节不变）；全部为文档措辞/字段名/时间戳/历史坐标级 ⇒ 无需开 B5.1。若将来要修 B5 §8.2↔§9.1 判据组成冲突（E03），属 b5 前置条件，只能在 b5 之后另立 B5.1，且不得在 b5 前动。

**附：ERRATA 与 B5.1 的边界**

- 不改题面/源文/问题/判据区（b5 前置条件）⇒ 一律 ERRATA。
- 若专家坚持冻结件文本自洽：只允许在 **b5 之后**另立 rev7.2/B5.1/B6.1（新哈希、旧件保留），且 B5.1 只能改说明区，判据组成冲突（E03）由 RULING R4 维持解释。

---

*本文件由 `doc-ledger` 于 2026-10-26T22:01:06+0800 只读生成；未改动任何冻结件、未 git 提交。本件自身不自钉哈希（外钉由 LEAD 记录）。*
