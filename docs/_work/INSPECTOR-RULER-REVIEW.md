# INSPECTOR 复核：task-34 尺子统一（含两处口径更正）

> **as-of**：`2026-10-25T22:52+08:00`；**22:55 追补 §9**（banner 去硬 sha + F1 双坐标 + G4d orphan 字段）。只读核验；仅改了我自己的 `ANCHORS-CURRENT.md`（见 §5）。
> **锚入口**：`docs/_work/ANCHORS-CURRENT.md` = **`41a5b29b50849fdb` / 15,759 B**（22:55 现版；中间快照 `d2e0f181` 15,821 B / `9e110717` 14,312 B / `a54c8109` 10,928 B 均只对更早状态有效）。
> **G4d 详核**：另见 `docs/_work/INSPECTOR-G4D-REVIEW.md`（本文 §6 只给结论，不重复四表）。

## 0 结论

**task-34 五条：四条通过、一条带条件通过。**

| # | 检查 | 判 | 依据（我实测） |
|---:|---|---|---|
| 1 | `verify.sh` 关系断言 | **通过** | `bash verify.sh` → **rc=0 / ALL PASS (12 项)**；补丁 600/0、快照 600/0、归档 500/0、归档≠实时，四条关系全过；不再写死 500/600 |
| 2 | MANIFEST 600 + archive 500 | **通过** | MANIFEST `ff532d39 / 9,095 B`；补丁 `db32faae / 32,337 / 600`，归档 `f41cbfbd / 26,577 / 500`；hunk **12 / 6 文件**（默认/patch 口径；`-U0` 会是 13，见 §2） |
| 3 | `.gitignore` 放行 `docs/_work` | **通过** | 当前 `4bddcfdd / 4,901 B`；`git check-ignore -v docs/_work/ANCHORS-CURRENT.md` → `.gitignore:51:!docs/_work/**`；`git ls-files --others --exclude-standard docs/_work` 能列出文件 ⇒ 可跟踪；其余 `_*` 仍忽略 |
| 4 | `check_ablate_run.py` 读声明 + 三态 | **通过** | 当前 `bf3687a1 / 4,705 B`；跑 a7 → `PASS (0 failed, 1 unverified) / rc=0`；`n_predict` 声明 64、引擎无属性 ⇒ UNVERIFIED，不伪造 PASS；四臂 cells/pos/controls 全 OK |
| 5 | README/PROJECT-STATE/HANDOFF as-of banner + 指向锚 | **通过（带条件）** | 三份文件头部均有 as-of banner，路径都指向 `docs/_work/ANCHORS-CURRENT.md`；**但 banner 里钉的入口值仍是 `a54c8109`，而锚文件已更新到 `d2e0f181`** ⇒ 锚指针过期（见 §5） |

**两处口径更正：**
1. **`.gitignore` 尾空格说法是错的**。我独立在 temp repo 实测：`_*/   `（三个尾空格）与 `_*/` 的 ignore 行为**完全相同**，git 会剥掉行尾未转义空格；真正吞掉 `docs/_work` 的是 **`_*/` 通配本身**（它匹配任意层级的 `_` 开头目录），生效的是 `!docs/_work/` + `!docs/_work/**` 例外。这是**第三次“转述即断言”**（G4c、site 标错、本次）。
2. **MANIFEST hunk 数不是 5，是 12/6**；`llama-kv-cache.cpp` 是 **4 hunk**。但“hunk 数”依赖 diff context：默认 `-U3` / patch 文本 = **12**，`git diff --unified=0` = **13**（kv-cache 5，因为 `:1720` 与 `:1722` 两处相邻改动在 0 context 下拆开）。MANIFEST 的 12/6 与默认/patch 口径一致；拿 `-U0` 去对它会得到“不一致”的假象。

---

## 1 `verify.sh`（关系断言，不是字面量）

实测命令与关键输出：

```text
$ bash verify.sh
引擎补丁 = 600/0（关系：实时 == MANIFEST 声明 600/0） PASS
补丁快照 = 600/0（关系：快照 == 工作区 diff） PASS
归档基线 = 500/0（关系：归档 == MANIFEST 归档声明；仅历史基线） PASS
归档基线 != 实时（500 != 600；500 版确实不是现行补丁） PASS
...
ALL PASS (12 项)          # rc=0
```

独立复算值（不靠脚本打印）：
- `git -C llama.cpp diff --numstat | awk` → `600 / 0`；
- `awk` 数 `patches/persistent-memory.patch` 的 `+`/`-`（排除 `+++`/`---`）→ `600 / 0`；
- 同样数 archive → `500 / 0`；
- MANIFEST 的 `insertions: 600 deletions: 0` / `archive-insertions: 500` 与上述一致；
- `verify.sh` 自身 **`c7c8b264f960daea` / 6,566 B**（与 lead 报的值一致）。
- 12 项计数 = 4 补丁关系 + 2 报告边车 + 6 门禁/可证伪（A1/A2/B/C/D/E），与输出一致。

**判**：通过；且“实时==MANIFEST / 快照==实时 / 归档==MANIFEST archive / 归档≠实时”四条**关系**都成立，不是把 600/500 写死。

## 2 MANIFEST 600 / archive 500 / hunk 数

- 当前 MANIFEST：**`ff532d394c17ae38 / 9,095 B`**；正文写 `file: patches/persistent-memory.patch`、`sha256 db32faae...`、`bytes 32337`、`insertions: 600 deletions: 0`、archive `f41cbfbd / 26,577 B / 500`。
- 磁盘实算：patch `db32faae83bec9fc / 32,337 / 12 hunk`，archive `f41cbfbd285af61f / 26,577 / 500`；`git -C llama.cpp diff --stat` = 6 文件 / 600 ins；**全对上**。
- **hunk 数**（独立计数）：
  - patch 文件头 `@@` = **12**；按文件 1/2/**4**/2/1/2；`llama-kv-cache.cpp` **4**（与 MANIFEST 行 38 一致）；
  - `git -C llama.cpp diff`（默认 `-U3`）= **12**，按文件同 1/2/4/2/1/2；
  - `git -C llama.cpp diff --unified=0` = **13**（kv-cache 5）：`:1720,0 +2048,157` 与 `:1722,0 +2207,7` 在 0 context 下拆成两个 hunk；patch 用默认 context 合并为 `@@ -1718,8 +2045,172 @@`。所以“5 hunk / 12 hunk”不是同一口径，**executor 的 12/6 在默认/patch 口径下正确，lead 原写 5 错**；`-U0` 的 13 不能作为反证。
- MANIFEST 的 **DLL 段仍有旧基线** `49,952,768 / 849e7281`（`target:` / `shipped baseline`），现盘 DLL 是 `/50,007,552 / 9edbafa1`；该段只能标 `unverifiable`，**不能因 MANIFEST patch 部分已修就把 DLL 旧值当现值**。

**判**：通过（patch/archive 身份与 hunk 库存）；DLL 旧基线另列 unverifiable。

## 3 `.gitignore` 放行面（独立 temp-repo 实验）

当前：`.gitignore = 4bddcfddcbe98ea3 / 4,901 B`，关键行：

```text
44: **/runs_*/_*/
45: _*/
...
50: !docs/_work/
51: !docs/_work/**
```

实测：

```text
$ git check-ignore -v docs/_work/ANCHORS-CURRENT.md
.gitignore:51:!docs/_work/**    docs/_work/ANCHORS-CURRENT.md     # rc=0
$ git ls-files --others --exclude-standard docs/_work
docs/_work/ANCHORS-CURRENT.md
...（可列出 ⇒ 未被忽略）
$ git check-ignore -v kvmem/chat.db tools/kvshim_vk.dll
.gitignore:91:*.db      kvmem/chat.db
.gitignore:20:*.dll     tools/kvshim_vk.dll
```

**尾空格的独立判定**（temp git repo，三组）：
- `.gitignore` 写 `_*/   `（尾空格）与写 `_*/`：对 `docs/_work/x.md`、`_foo/y.md`、`a/_bar/z.md` 的 `git check-ignore -v` **输出与命中行完全相同**（都命中 `_*/`）⇒ **git 确实剥尾空格**。
- 真正吞掉的原因是 `_*/` **本身**：即使没有尾空格，它仍匹配 `docs/_work`（任意层级 `_` 目录）；例外 `!docs/_work/` / `!docs/_work/**` 才放行。
- 结论：audit 说的“尾空格吞掉 docs/_work”**不成立**；lead 的转述错了，executor 的“git 本来就剥尾空格”对，且“真正吞掉的是通配”也对。

**判**：通过；但 `docs/_work/**` 的放行**依赖**例外行，删除例外会重新被 `_*/` 吞掉——这是后续 `.gitignore` 维护的约束。

## 4 `check_ablate_run.py`（读声明 + 三态）

- 当前 **`bf3687a17cbd230e / 4,705 B`**；源码 `n_predict` 分支不再写 `24`：先读 `d["n_predict"]`，再回退 `engine.n_predict`；缺失/引擎无属性 → `None`（UNVERIFIED），只有声明值存在且全部一致才 True；硬失败才 rc 1。
- 实跑 a7：`PASS (0 failed, 1 unverified) / rc=0`；`n_predict` 显示 `declared 64; engine exposes no n_predict attribute = UNVERIFIED`；`cells_span` 四臂 True、`raw_pos_max=4095`、`controls_answer_plate` 四臂 `T/T/F/F`（两个 control 通过，消融/等长失败）；产物 `run_m4_ablate_plate_a7.json 77e11a04` **未动**（我只读打开）。
- **判**：通过；`unverified` 没有被算成 PASS，符合三态。

## 5 README / PROJECT-STATE / HANDOFF 的 as-of banner

| 文件 | 当前 sha / 字节 | banner | 问题 |
|---|---|---|---|
| `README.md` | **`75585cbcbb4d3a50` / 22,259** | 有，2026-10-25 快照，指向 `PROGRESS-AND-ROADMAP §0.1` + `ANCHORS-CURRENT` | 入口锚钉 `a54c8109`，**已过期** |
| `PROJECT-STATE.md` | **`49245552ecfca426` / 52,052** | 有，2026-10-24 快照；明确“现盘类读数已过期、冻结哈希只按史料引” | 同上；旧 `ins=500 / DLL 849e7281` 仍在正文，但 banner 已降级 |
| `HANDOFF.md` | **`8ffff98d26aca85f` / 10,030** | 有，2026-10-25 快照；指向 `ANCHORS-CURRENT` | 同上 |

**判**：banner 形式与“不重写长文、只加 banner + 指向锚”的要求**通过**；**锚指针值未同步**（三处都还是 `a54c8109`，当前应为 `d2e0f181`）。这不是 task-34 代码问题，而是锚维护动作：**banner 写“以文件本身为准”能兜底，但钉死的旧 sha 仍会腐烂**。建议 executor/lead 把三处 `a54c8109` 换成 `d2e0f181`（或去掉硬 sha、只写路径），再重挂 task-34 banner。

## 6 G4-CLOSURE §5：读数与签署逐字段同（独立复核）

**结论：通过（§5 的 base/green/red 三条同一性成立）。**

- `base 12950f6a` → `87f060bd`：`loads` profile 50/50/49、project 36/36/35 逐字段同；`attaches_done=2`、`attach_events_ok=true`、`hits=null`、`assertions_status=checked`；同。
- `site3-green f3f6ce7f` → `960af172`：`orphans` 0/0/0（chat_n 0/63/108）、`hits=null`、covers site3；同。
- `site3-red dd46774c` → `f05e1de9`：`is_red=true`、`expected_red=true`、`assertions_status=assertion_failed`、`die_message` **逐字同**；`deleted_line_no` 562→594、行数 700→1428 属代码变长的行号/血缘，不是读数差。
- 但判决书若写“仅行号/`chat_py_sha16` 变”不精确：还变了 `harness_sha16`（`m4c_harness.py` `b48f037f→12d3f37c`）、`def_fp` 行号、`variant_sha16`、`src/variant_line_count`；这些被 `diff_fields={}` 归入调度/血缘。**G4d 回归链本身成立**。
- **两个不能混入 §5 的事**：① 36→86 是 **M4C4 b10** 的池读数（`4ada6cec`），G4d 的 DELETE red 只有 0，**没有重跑 36→86**；② `LANDED-s1-real 05a99bf3` 的 F1 `actual_sha16=30d224c4` 与 correction product `2d3bae59` 并存，需双坐标（详见 `INSPECTOR-G4D-REVIEW.md §4.1`）。这两条不推翻 §5 的三条同一性，但推翻“G4 全绿无保留”。

## 7 仍依赖 selection 顺序/分数的已签产物清单

G4c 撤回后，**保留 m1 CLI 臂相关，剔除 M4-C 夹具臂**。我判这份清单应缩为：

**保留（需按现行 selection 口径重跑/重述）**
1. `kvmem/m2_visibility/m2_planner/out/S1-real-default-regression.json`（**m1 真机臂**；`four_state.default_path_m1_real=未通过 KeyError` 即此臂）。
2. `kvmem/m2_visibility/m2_planner/out/S1-default-unchanged.json`（**m1 --explain**；v1 `3e8aae60` 已由 task-34/35 坐标演进，产物本身未改，引用须用 v2 addendum）。
3. `out/M4C-m1-rerun.json` / `out/M4C-m1-rerun-v2.json`（**m1 CLI 臂**，task-33/35 诊断/绿臂；不是 M4-C 签名臂）。
4. `out/G4a2-variant-want2sel.json` / `out/G4a2-red-variant.json`（m1 CLI 诊断变体；非签署读数，只作红证）。

**剔除（夹具固定 selection，不读 retrieval 顺序/分数）**
- `M4C-DELETE-SITE1-*`、`M4C-SITE3-*`、`M4C-DELETE-SITE4-*`、`m4c4/*`：`redcheck_delete.py` 的 `WANT_SEQ` + `fixed_selection` 写死 seq 分配；
- `M4C-VERDICT` 的 base/green/red `loads` 顺序：夹具口径，不是检索顺序；
- `M4-B run_m4_ablate_plate_a7`：固定块消融，不依赖检索排序；
- `S1-real` / `S1-real-2` / dryrun / cases：chat/双会话/固定案例，不依赖 m1 的 selection 排序。

**结论**：清单要留，但只留第 1–2 项（签署读数）+ 第 3–4 项（当前诊断）；M4-C 夹具臂全部剔除。若只问“已签”，严格是 **1、2**；3–4 是 task-33/35 未签诊断，不应混称已签。

## 8 交付物

- 本文件 = `INSPECTOR-RULER-REVIEW.md`。
- 锚更新：`ANCHORS-CURRENT.md` = **`41a5b29b50849fdb` / 15,759 B**（task-34 首轮 **d2e0f181** / 15,821 B；22:55 banner/F1 追补后见 §9）；本身 sha 不入文件。
- 未改任何产品/台账/DB/`.gitignore`/README/PROJECT/HANDOFF。

## 9 22:55 追补（banner + F1 + G4d orphan）

**banner 三份：通过。**
- `README.md` = **`5466f139846a3b0a` / 22,222 B**；`PROJECT-STATE.md` = **`fafa049fa9e1ebf4` / 52,015 B**；`HANDOFF.md` = **`9bb387c278da34e3` / 9,993 B**。
- 三份头部：as-of 在、路径在、**不再钉任何硬 sha**（全文 grep `a54c8109`/`d2e0f181` 均无）；文案为“坐标以 `ANCHORS-CURRENT` 内容为准”。`ANCHORS` row9–11 已同步。

**F1 双坐标：通过。**
- `LANDED-s1-real.json` = **`797a845029f3f374` / 36,120 B**；`addendum.original_readings_intact=true`。
- `F1_db_label.actual_dual_coordinates`：`task32_copy_sha16=2d3bae59` / `this_round_copy_sha16=30d224c4`，并给 `task32_source` / `this_round_source` / `why_two_actuals` / `authority`；correction 产物 `db472434` **未回改**（`no_product_modified=true`）。
- 独立复算：当前 temp 副本 `30d224c4`；correction `db472434` 仍写 `2d3bae59`；18 个产品/两采样路径 sha **全部等于现盘**；`four_state.default_path_m1_explain` 仍保留 v1 `3e8aae60`/654 B 原读数。
- 行级：`chat.db` 与 temp 副本 10 表中 **8 张逐行相同**（doc/facet/index_meta/memories/memory_block/memory_source/memory_source_excerpt/term，数量 10/17/3/2/2/10/7/346），只有派生 `attr`/`value_kind` 不同（value_kind 同集合）⇒ “同内容不同重建批次”成立。

**G4d `orphan_expectation`：实质已写，字段未写。**
- `LANDED-g4d.json` = **`35f9150128e3f4f1` / 13,973 B**；`four_state["36→86（M4-C-4 测量臂）"] = "未做（沿用 b10 历史读数，未重跑；见 stop_item.orphan_36_86_scope）"`，`stop_item.orphan_36_86_scope.rerun_this_round=false`，`verdict="未做（沿用 b10 历史读数，未重跑）"`。
- **但 `gaps.orphan_expectation` 仍是原句**：“…不在 DELETE 产品读数里；本单如实报 observed=0/0/0”，**没有“未重跑”三字**。若你按字段名验收，这条算 **未通过/需补一行**；按语义则 `stop_item`/`four_state` 已如实。
- `G4-CLOSURE §8.1` 写“`gaps.orphan_expectation` 已写明 … 本轮未重跑”**归因不准**：该字段没写，写的是 `stop_item.orphan_36_86_scope` / `four_state`；§8.2 仍引旧 `05a99bf3` 且说“无新旧双坐标”，**F1 现已补，§8.2 应更新为已补**（否则 §8 本身腐烂）。