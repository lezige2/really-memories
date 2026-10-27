# INSPECTOR 复核：G4d 回归链 + G4 收口读数（独立复算）

> **as-of**：`2026-10-25T22:46+08:00`；**锚坐标 22:55 追补**（task-34 追补后 `ANCHORS-CURRENT` 再更新）。只读复核；未改代码/台账/DB/产品，只更新 `ANCHORS-CURRENT.md` 的现行坐标（见 §6）。
> **锚入口**：`docs/_work/ANCHORS-CURRENT.md` = **`41a5b29b50849fdb` / 15,759 B**（22:55 现版；中间快照 `d2e0f181` 15,821 B、`9e110717` 14,312 B、`a54c8109` 10,928 B 只对更早状态有效）。
> **被核判决**：`docs/_work/G4-CLOSURE-lead.md` = `234db8cff54e514e` / 6,302 B（草签）；其 §8 已按 22:48 版更新，22:55 F1 补注后仍待 lead 再改。

## 0 结论（先给 lead 要的“是否成立”）

**G4d 回归链本身：成立。** 现盘 `tools/chat.py = 22081c411c64fbe7 / 75,310 B`；三条 needle 各 1 命中（site1 `:270`、site3 `:594`、site4 `:630`）；夹具 base/green/red 与签署 `12950f6a` / `f3f6ce7f` / `dd46774c` 的**读数逐字段同**（die 文案逐字同），只有调度/血缘元数据变化；单点变体 `want→sel` 实算 1 个 hunk；site4 的 `coverage_not_met` 是夹具结构性，不属本单引入。

**但按你四条字面，有两处不能直接签“全绿”：**

1. **第 3 条（红臂 orphan 36→86 / green 0）在 G4d 里没有落点。** G4d 的 site3 红臂/绿臂 `orphans` 都是 **0/0/0**；`LANDED-g4d.gaps.orphan_expectation` 自己写明「36→86 属 CLOSURE §site3 的 M4-C-4 测量臂，不在 DELETE 产品读数里」。36→86 只在 **`m4c4/M4C4-deleted-b10... 4ada6cec`**（green 对应 `08a197d2`）；我复算了这两份历史产物，读数与 §4.3 一致，但 **G4d 没有重跑它**。所以：若销号依据是「G4d 重跑」，该条未做；若依据是「b10 历史读数未变」，该条成立（我已核）。**请裁口径，不能把 b10 当成 G4d 重跑。**
2. **第 4 条（原文保全）有一处不成立。** `LANDED-s1-real 05a99bf3` 的 `addendum.original_readings_intact=true`、产品 sha 全等于现盘、`_land_s1.py b63b22d0` 已标 `unverifiable`、`_write_s1_corrections.py bff31b15` 已显式排除——这些都成立。**但 `addendum.F1_db_label.actual_sha16 = 30d224c474f42628`，而补正产品 `S1-real-default-regression-correction.json db472434` 仍写 `sha16_after = 2d3bae59168b6ed1`**：同一 F1 证据出现两个坐标，台账没有双坐标/新旧说明，不能算“只补标签、原读数未改”。见 §4.1。

**G4-CLOSURE §2-C2 的自我更正：我核过，改得对。** `M4C-CLOSURE-lead.md §4.3` 原文：**36→86 是 site3 `m1.unmount.after_detach`（`chat.py:562`，G4 后为 `:594`）**；site4 `m1.mount.before_load` 紧随 `load_into`（`kvshim.cpp:573` 自清）⇒“删掉必须红”**签署时即判据作废**，且被 site3 掩码；两行与你的撤回一致（§5）。

---

## 1 needle 唯一性（现盘实测，不抄 executor）

`tools/chat.py 22081c411c64fbe7 / 75,310 B`，逐行 `in` 实测：

| site | needle | 命中行 | 命中数 |
|---|---|---|---:|
| 1 | `leases.reset(i, site="chat.place.fresh")` | **270** | 1 |
| 3 | `leases.reset(seq, site="m1.unmount.after_detach")` | **594** | 1 |
| 4 | `leases.reset(seq, site="m1.mount.before_load")` | **630** | 1 |

另：`chat.py` 全部 `leases.reset(` 行 = `:270 / :386 / :594 / :630 / :962`；三条 needle 不交叉。**通过。**
（G4b 后 `site4` 从签署的 `:595` 漂到 `:618`（task-33），再到现在的 `:630`；行号可变，needle 唯一，G4d 断言应保持 `len(hits)==1`，不要硬编码。）

## 2 夹具臂读数同一性（G4d 承重点）

`out/M4C-fixture-rerun.json b997191a` 的 arm → 产品 sha 与签署产品逐字段比较；下表“元数据差”是**我复算的差异字段数**（不是 `diff_fields` 字段，后者只列被判定为读数的字段）：

| 臂 | 签署产品 | G4d 产品 | 读数结论 | 元数据差（全为调度/血缘） |
|---|---|---|---|---|
| site1 base | `12950f6a` / 3,806 | `87f060bd` / 3,806 | `loads` 逐字段同（profile 50/50/49、project 36/36/35）；`attaches_done=2`、`attach_events_ok=true`、`hits=null`、`assertions_status=checked`；**同** | 12：`run_id/sampled_at/assert_log_path/batch_id/chat_py_sha16/variant_sha16` + `harness_sha16(m4c_harness.py b48f037f→12d3f37c)` + `def_fp` 4 处行号 +1 |
| site3 green | `f3f6ce7f` / 7,781 | `960af172` / 7,781 | `orphans` 0/0/0（chat_n 0/63/108）、`hits=null`、covers site3；**同** | 12（同上类） |
| site3 red | `dd46774c` / 5,750 | `f05e1de9` / 5,752 | `is_red=true`、`expected_red=true`、`assertions_status=assertion_failed`、`die_message` **逐字同**：`error: M4-C 范围断言红 @m1.unmount: 调用流 hits=[]（0 条） != dropped=[2]（1 条）`；**同** | 15：上述 12 + `deleted_line_no 562→594` + `src/variant_line_count 700→1428` + `variant_sha16 0c149c11→22b978ce` |

**对“仅行号/`chat_py_sha16` 变”的纠正**：实际还变了 `harness_sha16`（`m4c_harness.py` 本身有改动：`b48f037f`→`12d3f37c`）、`def_fp` 行号、`variant_sha16`、`src/variant_line_count`；`land.py` 台账是正确地把这些归入“调度/血缘”后 `diff_fields={}`。**没有“读数变了”的差异**，但判决书若写“仅行号/chat sha 变”是不精确的。
- site1 **deleted** 臂 G4d 未重跑（无 `g4d` 产品）；G4d 只承诺 base/green/red，故不算缺口，但“base 与 deleted 同”这一条 G4d **没有新证据**，只能引 b09 签署。
- site3 red 的 orphan 读数只有 **0**（`after_mount_loop` 单点），不是 36/86；再次说明 §0 第 1 条。

## 3 site4 两臂（结构性既有？）

G4d `site4_base e697accd` / `site4_deleted b91108ce`：两臂 `exit=0`（**产物字段**）、`is_red=false`、`die_kind=null`、`hits=null`、`coverage_ok=false`、`covers_declared=["site4"]`、`covers_observed=["site3"]`；`loads` 逐字段相同、`orphans` 0/0/0、`assertions_status=checked`；`site4_no_effect` 四项 true。**`rc 5` 不是产物 `exit` 字段**（产物写 0），应是外层 `m4c_verdict`/runner 的 `coverage_not_met` 判定码；引用时须区分“产物 exit / 进程 rc / verdict 码”三义。

**历史臂**（`kvmem/m4c_leases/out/M4C-DELETE-SITE4-*.json`，共 17 份）：
- `base-attempt10` / `deleted-attempt10`：`coverage_ok=false`、`covers_observed=[3]`（旧字段形态）——**同样“只观测到 site3”**，可证明覆盖缺口在本单之前已存在。
- 其余 13 份是 `exit -1/1`、`crash`、旧 schema 或 `coverage` 字段缺失（attempt1/2/4/6/7/8/9 等），**不能**单独证明“结构性既有”；只能证明该夹具历史上不稳。
⇒ **结论：结构性既有成立，但证据应引 attempt10 这一对，不要把 13 份 crash 臂当论据**；`coverage_not_met` 不阻塞 G4d（与 `G4-CLOSURE §3` 的“未接上”一致）。

## 4 重生成台账的原文保全

### 4.1 `LANDED-s1-real 05a99bf3` / 35,003 B

| 检查 | 结果 |
|---|---|
| `addendum.original_readings_intact` | **true**（嵌套在 `addendum`，不是顶层；我按路径核到） |
| 产品 sha 与现盘 | 全部相等（real_s1 `3df8d70b`、real_s2 `39b7f9de`、smoke `a067294a`、default_regression `39aa2505`、dry* `f2ae36b3/007015df`、cases `c9211e5d`、pre `8bb70d6b`、default_unchanged `12cebec6`、corrections `db472434`）；`two_samples.s1/s2` 同；`four_state` 原值保留（含 `default_path_m1_explain: 654 B / 3e8aae60`） |
| `_land_s1.py b63b22d0` | `module_shas_note.land_coordinate.status="unverifiable"`，写明无 `_before`、git 未跟踪、现盘 `9bd414c3/25,853`；**合格** |
| `_write_s1_corrections.py bff31b15` | `module_shas_note.excluded` 显式列出并给理由（一次性补正写入器、输出由 `db472434` 锁定）；**合格** |
| **F1 证据坐标** | **不一致**：`addendum.F1_db_label.actual_sha16=30d224c474f42628`；`S1-real-default-regression-correction.json` 的 `F1_db_copy_correction.corrected.sha16_after=2d3bae59168b6ed1`（correction sha `db472434` 未变）。同一 F1 证据两个 actual 坐标，且无“task-32 的 2d3bae59 / 本轮副本 30d224c4”双坐标注。`temp_db/chat@237d8e1f.db` 现字节确为 `30d224c4`；correction 是旧副本的锁。 |
| 其他 | `scripts.land` / `module_shas.land` 均为新 `9bd414c3`；`scripts` 仍含 writer；`F3.added` 仍 4 件（writer 的排除在 `module_shas_note`，不在 F3，可接受但引用时别漏看） |

**判**：产品/读数层保全成立；**F1 元数据不成立**，需要补双坐标或把 `actual_sha16` 改回/注明“旧副本 2d3bae59”的不可现算。不能以 `original_readings_intact=true` 覆盖它。

### 4.2 其他三份

- **`LANDED-g4a2 ae44a406` / 11,005**：`products.v2=6c3e3f55`、`prefix_regression=18127962` 且 `variant_kind="prefix-regression"`、`single_point_variant=9653e1d9` 且 `variant_kind="single-point(want→sel)"`/`hunks=1`、`driver=9129e8a4`、`containment=b07a4608`、`explain_addendum=2f4917d6`；判 `g4a2` 与 `g4a3` 均通过；**合格**。
- **`LANDED-g4-addendum d5fe3e3e` / 2,184**：`supersedes=7a9d6cea`；`original.untouched=true` 且磁盘 `LANDED-g4.json` 仍 `7a9d6cea`；`fix.judge_unchanged` 改为“consume `sel_mountable`”，`effective_chat_py_sha16=1790f3a9`、`current=22081c41`；**合格**。
- **`S1-default-unchanged-explain-v2-addendum 2f4917d6` / 1,973**：原产物 `S1-default-unchanged 12cebec6`、`S1-real-default-regression 39aa2505` **未动**；v1 坐标 `3e8aae60` 标“已作废”；当前 `c4cbad83784e647f / 1,126 B`（LF；原始 CRLF 1,146）、去首行 `explain_version: 2` + 标注后 **872 B / `3e8aae60`**，可逆；**合格**。

### 4.3 单点变体

`out/G4a2-variant-want2sel.json 9653e1d9`：`single_point_diff.base=_before/chat.py@1790f3a9...`（sha 实算 `1790f3a9`），变体 `tmp_db/variants/chat_want2sel.py` `0be03070`；我用 `difflib.SequenceMatcher` 实算 **仅 1 个 replace hunk（行 552）**：`E.decide(q, sel_mountable, …)` → `E.decide(q, sel, …)`，无其他改动；控制问句 `memory_hit`、`refuse=false`、`ask_count=1`、答案非空，`red_points` 4/4。**“严格单点变体”成立。**
`18127962` 台账标 `prefix-regression`，产品本身无 `variant_kind` 字段（靠台账）；引用时须写“台账标签”，不要写成产物自述。

## 5 G4-CLOSURE 自我更正

`M4C-CLOSURE-lead.md §4.3` 总表原文（我逐行核）：
- site3 `m1.unmount.after_detach`：紧随动作为**无**；实测 orphan **0→36→86**、`engine_after seq1:[50,4095]/seq2:[36,4031]`、green 全 0；判“承重（池不泄漏）”。
- site4 `m1.mount.before_load`：紧随 `:598 ms.load_into`（前一步 detach）；**未单独跑**；结构同 site1；DESIGN §2“结构性不可掩 + 被 site3 掩码”；判“判据作废，ledger 已判”。

⇒ 你 §2-C2 的更正**正确**：36→86 归 site3；site4 的“删掉必须红”是签署时即作废，不是 G4d 的回归失败。`G4-CLOSURE §2-C2` 与 §4.3 一致，无异议。

## 6 锚更新（我改的唯一文件）

`chat.py` 已从 `1790f3a9` 到 `22081c41`（+`explain_version: 2`，75,310 B），我原 `ANCHORS-CURRENT a54c8109` 的 row1/row23 已过期。已更新：

- `ANCHORS-CURRENT.md` = **`d2e0f181e4e4581a` / 15,821 B**（35 行；row1 现 `22081c41`，row8 MANIFEST `ff532d39`，row9–11 README/PROJECT/HANDOFF，row23 现 `c4cbad83 / 1,126 B`，并补充 G4d/G4a-2/S1 台账行 24–32 与 task-34 行 33–35）。
- **影响**：`G4-CLOSURE §5` / task-34 banner 目前挂的 `a54c8109` 只对旧快照有效，须改挂 **`d2e0f181`**；否则 §5 的“锚 a54c8109”本身成为 stale 引文。`a54c8109`、`9e110717` 不删，作为 22:26 / 22:40 历史坐标。

## 7 建议的判决口径（供 lead 裁）

- **G4d 回归链**：签“通过”（§2 读数同一 + §1 needle + §3 site4 结构性 + §4.3 更正）。
- **G4 全绿**：先补两件再签更稳：① §0-1 的 orphan 口径（接受 b10 缓存未重跑，或补 `M4C4` 重跑）；② §4.1 F1 双坐标。
- 若你要求“四条字面全成立才销号”，则当前状态应为 **G4d 通过、G4 判决挂起（待 F1 与 orphan 口径）**；我不建议把 b10 历史读数说成 G4d 重跑，也不建议让 `original_readings_intact=true` 掩盖 F1 坐标变化。