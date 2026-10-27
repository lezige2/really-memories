# DOC-HASH-LEDGER-M5C2 —— 文档哈希引用 / 关键数字对账账本

> **性质**：只读审计。**未改动任何被审计文件**，未 git 提交，零 GPU / 零模型 / 零联网，未读 (b5) 运行数据。
> **生成时间**：2026-10-26T21:18:35+08:00 ｜ **工作区**：`D:\llama-mem` ｜ **HEAD**：`96eeefc`（main）、`5574253`（full）
> **机读账本**：`kvmem/m2_visibility/m5/out/M5C2-DOC-HASH-LEDGER.json`（citations[] / numbers[] / summary / corrections[]）
> **口径**：锚 = 工作区原始字节 `sha256[:16]`（与项目 ANCHORS-CURRENT 约定一致，不做换行/编码归一）。8-hex 引用按前缀匹配。

## 0 一句话结论

**核心读数全部对得上代码/数据；真正的问题集中在“冻结时引用已过期（stale-at-freeze）/ 声明时间不实 / 归因表细节”。**
哈希引用 151 条：match **144**、stale_reconstructible **1**、stale_unresolved **4**、unverifiable **2**；
数字主张 47 条：match **39**、对不上 **6**、不可复算 **1**、历史快照 **1**、待冻结/待满足 **0**。

两条**必须马上改**的 stale 引用：

1. `PREREG-M5-C2-REV7.md:7` 引用 `(b5) e306ce994d306a84` —— 该值只等于**去掉 §9 后**的 B5 早期版本（截断 + rstrip = 11,388 B）；现行 B5 是 `d6c7bdac73ef7326` / 14,597 B，且 **§9 在 B5 冻结前就已写入**（mtime 19:54:15 < frozen_at 19:55；`full@5574253` 的 blob 同为含 §9 的 `d6c7bdac`，commit 19:59:10）。**REV7 20:15 冻结时引用已过期（stale-at-freeze），不是“冻结后追加”。**
2. `PREREG-M5-C2-B5.md:6` 引用 `PREREG-M5-C2-B4.md e9a88fda` —— 当前 B4 是 `f30d89e30262b148` / 10,910 B；REV6 对同一文件引的正是 `f30d89e3`。`e9a88fda` 在**全树 + 全部 git blob + 所有截断/换行变体**中都不存在 ⇒ 无法重构，只能当笔误/未入树中间态。

## 0.5 审计期内文件变动（moving target，必须知道）

审计期间（约 21:04–21:12）`docs/_work/` 有两份文件在被 LEAD 实时修订，本账本**先一次性快照再核验**，因此结论对应“下表最后一行”的字节状态；若之后又改，需重跑。

| 文件 | 观察到的版本 | 变化 |
|---|---|---|
| `PREREG-M5-C2-REV7.1.md` | `370b6fcf` / 15,193 B @20:58:50 → `09d6f1b1` / 16,313 B @21:07:03（本账本快照 `09d6f1b163ea0b84` / 16,313 B） | 20:58 版还是草稿、§0 仍写 N1=4；21:06:55 被 LEAD 冻结，改为 N1=3、去掉“与上重叠”、并补了 redline 表 |
| `PREREG-M5-C2-B6.md` | 21:07 出现（16,637 B）→ 15,434 B @21:10:32 → 本账本快照 `ac27d47d3a3efff9` / 17,374 B | (b6) 题面新出；21:07 版自钉 `920333f2` 按自身口径不可复算、4-gram 报 1/1；21:10 版起自钉可复算、4-gram 改 0/0/0；仍在编辑 |

> 这正是“文档可靠性”最难核的一类情况：**文件在被审计的同时还在被改**。账本对这类文件的判定都以快照 sha16 为准，不含“未来版本”。

## 1 范围与方法

**被审来源**（21 件）：`docs/_work/PREREG-M5-C2-*.md`（16 件，含审计期内出现并已冻结的 B6，及同期冻结的 REV7.1 更正件）、`docs/_work/PREREG-M5-B2.md`、`docs/_work/INSPECTOR-M5C2-REV7.md`、`out/M5B4-RATES.md`、`out/M5B4-AB-OLD-VS-NEW.md`、根 `README.md`。

**解析链**：① 同行/前两行的文件名 → 用哈希命中选目标；② 全树内容哈希唯一命中；③ `(b2)/(b4)/(b5)/rev6/rev7` 别名；④ 最近左侧文件名（给 stale 用）。
**重构手段**：当前文件在任意行边界截断 × {raw, rstrip, rstrip+`\n`, CRLF}；`git rev-list --all --objects` 的 **1,491 个 blob** 全部重算；归档草稿；全树二进制内容哈希。

**范围缺口（如实记录）**：`docs/_work/INSPECTOR-M5C2-REV7.1.md` 不存在（审计期结束前始终未出现）；`docs/_work/PREREG-M5-C2-B6.md` 在审计期内（21:07）才出现，已纳入本账本快照。

## 2 哈希引用账本

### 2.1 match（144 条）—— 可直接信任

| # | 来源（行） | 引用值 | 目标 | 实际 sha16 / 字节 |
|---|---|---|---|---|
| 1 | `docs/_work/PREREG-M5-B2.md:6` | `cc03e48c360ae0ee` | `kvmem/m2_visibility/m5/m5_ground_v2_3.py` | `cc03e48c360ae0ee` / 44,209 B |
| 2 | `docs/_work/PREREG-M5-B2.md:10` | `8102950d9de660be` | `docs/_work/PREREG-M5-B.md` | `8102950d9de660be` / 12,053 B |
| 3 | `docs/_work/PREREG-M5-B2.md:92` | `cc03e48c360ae0ee` | `kvmem/m2_visibility/m5/m5_ground_v2_3.py` | `cc03e48c360ae0ee` / 44,209 B |
| 4 | `docs/_work/PREREG-M5-B2.md:127` | `5e11e1ac06f022c7` | `kvmem/m2_visibility/m5/m5_ground_v2.py` | `5e11e1ac06f022c7` / 66,413 B |
| 5 | `docs/_work/PREREG-M5-B2.md:128` | `5a3f12f2a742a864` | `docs/_work/PREREG-M5-JUDGE-v2.3.md` | `5a3f12f2a742a864` / 10,394 B |
| 6 | `docs/_work/PREREG-M5-B2.md:129` | `cc03e48c360ae0ee` | `kvmem/m2_visibility/m5/m5_ground_v2_3.py` | `cc03e48c360ae0ee` / 44,209 B |
| 7 | `docs/_work/PREREG-M5-B2.md:130` | `8102950d9de660be` | `docs/_work/PREREG-M5-B.md` | `8102950d9de660be` / 12,053 B |
| 8 | `docs/_work/PREREG-M5-B2.md:131` | `0d882f20987fea70` | `kvmem/m2_visibility/m5/out/M5C-36-adj.json` | `0d882f20987fea70` / 60,432 B |
| 9 | `docs/_work/PREREG-M5-B2.md:132` | `60fedd7d4bbf0556` | `docs/_work/LEAD-M5-C-ADJUDICATION.md` | `60fedd7d4bbf0556` / 10,023 B |
| 10 | `docs/_work/PREREG-M5-C2-B2EVAL.md:4` | `69c8d48ea026c50a` | `docs/_work/PREREG-M5-C2-REV4-1.md` | `69c8d48ea026c50a` / 6,201 B |
| 11 | `docs/_work/PREREG-M5-C2-B2EVAL.md:4` | `5ad46f8efb762c6d` | `docs/_work/JUDGE-ROBUSTNESS-SPEC.md` | `5ad46f8efb762c6d` / 8,555 B |
| 12 | `docs/_work/PREREG-M5-C2-B2EVAL.md:25` | `5ad46f8efb762c6d` | `docs/_work/JUDGE-ROBUSTNESS-SPEC.md` | `5ad46f8efb762c6d` / 8,555 B |
| 13 | `docs/_work/PREREG-M5-C2-B2EVAL.md:26` | `be618108a82c2f42` | `docs/_work/PREREG-M5-C2-REV4.md` | `be618108a82c2f42` / 6,996 B |
| 14 | `docs/_work/PREREG-M5-C2-B2EVAL.md:26` | `a6bc4f268f7711de` | `kvmem/m2_visibility/m5/run_m5c2_rev4.py#REV4_TEMPLATE` | `a6bc4f268f7711de` |
| 15 | `docs/_work/PREREG-M5-C2-B2EVAL.md:28` | `9edbafa150700614` | `tools/kvshim_vk.dll` | `9edbafa150700614` / 50,007,552 B |
| 16 | `docs/_work/PREREG-M5-C2-B2EVAL.md:32` | `6529e151568dc593` | `kvmem/m2_visibility/m5/out/M5B2-SENTENCES.json` | `6529e151568dc593` / 78,825 B |
| 17 | `docs/_work/PREREG-M5-C2-B2EVAL.md:32` | `65a2124b73f17d53` | `kvmem/m2_visibility/m5/out/M5B2-LEAD-RULING.json` | `65a2124b73f17d53` / 4,192 B |
| 18 | `docs/_work/PREREG-M5-C2-B4.md:6` | `482a9482` | `docs/_work/PREREG-M5-B2.md` | `482a94820917d16e` / 12,695 B |
| 19 | `docs/_work/PREREG-M5-C2-B4.md:6` | `65a2124b` | `kvmem/m2_visibility/m5/out/M5B2-LEAD-RULING.json` | `65a2124b73f17d53` / 4,192 B |
| 20 | `docs/_work/PREREG-M5-C2-B4.md:91` | `9edbafa150700614` | `tools/kvshim_vk.dll` | `9edbafa150700614` / 50,007,552 B |
| 21 | `docs/_work/PREREG-M5-C2-B4.md:104` | `65a2124b` | `kvmem/m2_visibility/m5/out/M5B2-LEAD-RULING.json` | `65a2124b73f17d53` / 4,192 B |
| 22 | `docs/_work/PREREG-M5-C2-B4.md:132` | `6f41f3d6ee318587` | `docs/_work/_archive/PREREG-M5-C2-B4.draft-2026-10-26-before-analyst.md` | `6f41f3d6ee318587` / 7,823 B |
| 23 | `docs/_work/PREREG-M5-C2-B5.md:6` | `482a9482` | `docs/_work/PREREG-M5-B2.md` | `482a94820917d16e` / 12,695 B |
| 24 | `docs/_work/PREREG-M5-C2-B5.md:6` | `65a2124b` | `kvmem/m2_visibility/m5/out/M5B2-LEAD-RULING.json` | `65a2124b73f17d53` / 4,192 B |
| 25 | `docs/_work/PREREG-M5-C2-B5.md:91` | `9edbafa150700614` | `tools/kvshim_vk.dll` | `9edbafa150700614` / 50,007,552 B |
| 26 | `docs/_work/PREREG-M5-C2-B5.md:104` | `65a2124b` | `kvmem/m2_visibility/m5/out/M5B2-LEAD-RULING.json` | `65a2124b73f17d53` / 4,192 B |
| 27 | `docs/_work/PREREG-M5-C2-B5.md:146` | `a6bc4f268f7711de` | `kvmem/m2_visibility/m5/run_m5c2_rev4.py#REV4_TEMPLATE` | `a6bc4f268f7711de` |
| 28 | `docs/_work/PREREG-M5-C2-B5.md:147` | `32eaf82ca56600c4` | `docs/_work/PREREG-M5-C2-REV7.md` | `32eaf82ca56600c4` / 5,835 B |
| 29 | `docs/_work/PREREG-M5-C2-B5.md:148` | `faaf2605116bb594` | `docs/_work/PREREG-M5-C2-REV6.md` | `faaf2605116bb594` / 5,773 B |
| 30 | `docs/_work/PREREG-M5-C2-B6.md:6` | `482a94820917d16e` | `docs/_work/PREREG-M5-B2.md` | `482a94820917d16e` / 12,695 B |
| 31 | `docs/_work/PREREG-M5-C2-B6.md:6` | `f30d89e30262b148` | `docs/_work/PREREG-M5-C2-B4.md` | `f30d89e30262b148` / 10,910 B |
| 32 | `docs/_work/PREREG-M5-C2-B6.md:6` | `d6c7bdac73ef7326` | `docs/_work/PREREG-M5-C2-B5.md` | `d6c7bdac73ef7326` / 14,597 B |
| 33 | `docs/_work/PREREG-M5-C2-B6.md:89` | `9edbafa150700614` | `tools/kvshim_vk.dll` | `9edbafa150700614` / 50,007,552 B |
| 34 | `docs/_work/PREREG-M5-C2-B6.md:101` | `a6bc4f268f7711de` | `kvmem/m2_visibility/m5/run_m5c2_rev4.py#REV4_TEMPLATE` | `a6bc4f268f7711de` |
| 35 | `docs/_work/PREREG-M5-C2-B6.md:101` | `09d6f1b163ea0b84` | `docs/_work/PREREG-M5-C2-REV7.1.md` | `09d6f1b163ea0b84` / 16,313 B |
| 36 | `docs/_work/PREREG-M5-C2-B6.md:101` | `32eaf82ca56600c4` | `docs/_work/PREREG-M5-C2-REV7.md` | `32eaf82ca56600c4` / 5,835 B |
| 37 | `docs/_work/PREREG-M5-C2-B6.md:102` | `faaf2605116bb594` | `docs/_work/PREREG-M5-C2-REV6.md` | `faaf2605116bb594` / 5,773 B |
| 38 | `docs/_work/PREREG-M5-C2-B6.md:110` | `65a2124b` | `kvmem/m2_visibility/m5/out/M5B2-LEAD-RULING.json` | `65a2124b73f17d53` / 4,192 B |
| 39 | `docs/_work/PREREG-M5-C2-FLOOR-REV2.md:4` | `dfc36bece621f871` | `docs/_work/PREREG-M5-C2-FLOOR.md` | `dfc36bece621f871` / 7,242 B |
| 40 | `docs/_work/PREREG-M5-C2-FLOOR-REV2.md:10` | `a8e33701520a8d07` | `kvmem/m2_visibility/m5/out/M5C2-FLOOR-ARTIFACT.json` | `a8e33701520a8d07` / 29,679 B |
| 41 | `docs/_work/PREREG-M5-C2-FLOOR-REV2.md:11` | `04fa29e14c2e7788` | `kvmem/m2_visibility/m5/out/M5C2-FLOOR-ARTIFACT-AMEND.json` | `04fa29e14c2e7788` / 1,506 B |
| 42 | `docs/_work/PREREG-M5-C2-FLOOR-REV2.md:12` | `24003605732b3e36` | `kvmem/m2_visibility/m5/out/M5C2-T384.json` | `24003605732b3e36` / 23,385 B |
| 43 | `docs/_work/PREREG-M5-C2-FLOOR-REV2.md:39` | `9edbafa150700614` | `tools/kvshim_vk.dll` | `9edbafa150700614` / 50,007,552 B |
| 44 | `docs/_work/PREREG-M5-C2-FLOOR-REV2.md:92` | `dfc36bece621f871` | `docs/_work/PREREG-M5-C2-FLOOR.md` | `dfc36bece621f871` / 7,242 B |
| 45 | `docs/_work/PREREG-M5-C2-FLOOR.md:4` | `d4ab619b59bfe6fb` | `docs/_work/PREREG-M5-C2-R2.md` | `d4ab619b59bfe6fb` / 5,830 B |
| 46 | `docs/_work/PREREG-M5-C2-ORDER.md:5` | `54faca9edb3a8daf` | `docs/_work/PREREG-M5-C2-FLOOR-REV2.md` | `54faca9edb3a8daf` / 6,173 B |
| 47 | `docs/_work/PREREG-M5-C2-ORDER.md:9` | `04fa29e14c2e7788` | `kvmem/m2_visibility/m5/out/M5C2-FLOOR-ARTIFACT-AMEND.json` | `04fa29e14c2e7788` / 1,506 B |
| 48 | `docs/_work/PREREG-M5-C2-ORDER.md:49` | `9edbafa150700614` | `tools/kvshim_vk.dll` | `9edbafa150700614` / 50,007,552 B |
| 49 | `docs/_work/PREREG-M5-C2-R2.md:10` | `df1ae09cc9ecc0d2` | `docs/_work/LEAD-M5-B-ADJUDICATION.md` | `df1ae09cc9ecc0d2` / 5,627 B |
| 50 | `docs/_work/PREREG-M5-C2-R2.md:10` | `9ac66b6dfaf8f804` | `kvmem/m2_visibility/m5/out/M5B2-RATES.json` | `9ac66b6dfaf8f804` / 11,407 B |
| 51 | `docs/_work/PREREG-M5-C2-R2.md:11` | `4fc889483d4f49b3` | `docs/_work/PREREG-M5-C2-SEMANTIC.md` | `4fc889483d4f49b3` / 7,115 B |
| 52 | `docs/_work/PREREG-M5-C2-R2.md:48` | `0d882f20987fea70` | `kvmem/m2_visibility/m5/out/M5C-36-adj.json` | `0d882f20987fea70` / 60,432 B |
| 53 | `docs/_work/PREREG-M5-C2-R2.md:48` | `aaed082264712c59` | `kvmem/m2_visibility/m5/out/M5C-36-alignment.json` | `aaed082264712c59` / 245,640 B |
| 54 | `docs/_work/PREREG-M5-C2-R2.md:63` | `6529e151568dc593` | `kvmem/m2_visibility/m5/out/M5B2-SENTENCES.json` | `6529e151568dc593` / 78,825 B |
| 55 | `docs/_work/PREREG-M5-C2-R2.md:64` | `65a2124b73f17d53` | `kvmem/m2_visibility/m5/out/M5B2-LEAD-RULING.json` | `65a2124b73f17d53` / 4,192 B |
| 56 | `docs/_work/PREREG-M5-C2-R2.md:89` | `4fc889483d4f49b3` | `docs/_work/PREREG-M5-C2-SEMANTIC.md` | `4fc889483d4f49b3` / 7,115 B |
| 57 | `docs/_work/PREREG-M5-C2-R2.md:90` | `df1ae09cc9ecc0d2` | `docs/_work/LEAD-M5-B-ADJUDICATION.md` | `df1ae09cc9ecc0d2` / 5,627 B |
| 58 | `docs/_work/PREREG-M5-C2-R2.md:91` | `9ac66b6dfaf8f804` | `kvmem/m2_visibility/m5/out/M5B2-RATES.json` | `9ac66b6dfaf8f804` / 11,407 B |
| 59 | `docs/_work/PREREG-M5-C2-R2.md:92` | `6529e151568dc593` | `kvmem/m2_visibility/m5/out/M5B2-SENTENCES.json` | `6529e151568dc593` / 78,825 B |
| 60 | `docs/_work/PREREG-M5-C2-R2.md:93` | `65a2124b73f17d53` | `kvmem/m2_visibility/m5/out/M5B2-LEAD-RULING.json` | `65a2124b73f17d53` / 4,192 B |
| 61 | `docs/_work/PREREG-M5-C2-R2.md:94` | `0d882f20987fea70` | `kvmem/m2_visibility/m5/out/M5C-36-adj.json` | `0d882f20987fea70` / 60,432 B |
| 62 | `docs/_work/PREREG-M5-C2-R2.md:95` | `aaed082264712c59` | `kvmem/m2_visibility/m5/out/M5C-36-alignment.json` | `aaed082264712c59` / 245,640 B |
| 63 | `docs/_work/PREREG-M5-C2-REV4-1.md:4` | `be618108a82c2f42` | `docs/_work/PREREG-M5-C2-REV4.md` | `be618108a82c2f42` / 6,996 B |
| 64 | `docs/_work/PREREG-M5-C2-REV4-1.md:5` | `5ad46f8efb762c6d` | `docs/_work/JUDGE-ROBUSTNESS-SPEC.md` | `5ad46f8efb762c6d` / 8,555 B |
| 65 | `docs/_work/PREREG-M5-C2-REV4-1.md:9` | `8d36dbcd9605d68c` | `kvmem/m2_visibility/m5/out/M5C2-REV4.json` | `8d36dbcd9605d68c` / 73,938 B |
| 66 | `docs/_work/PREREG-M5-C2-REV4.md:5` | `fb0da1b792004fa2` | `docs/_work/PREREG-M5-C2-ORDER.md` | `fb0da1b792004fa2` / 5,453 B |
| 67 | `docs/_work/PREREG-M5-C2-REV4.md:11` | `a8e33701520a8d07` | `kvmem/m2_visibility/m5/out/M5C2-FLOOR-ARTIFACT.json` | `a8e33701520a8d07` / 29,679 B |
| 68 | `docs/_work/PREREG-M5-C2-REV4.md:11` | `04fa29e14c2e7788` | `kvmem/m2_visibility/m5/out/M5C2-FLOOR-ARTIFACT-AMEND.json` | `04fa29e14c2e7788` / 1,506 B |
| 69 | `docs/_work/PREREG-M5-C2-REV4.md:14` | `521170d38c12206c` | `kvmem/m2_visibility/m5/out/M5C2-FLOOR-REV2.json` | `521170d38c12206c` / 97,760 B |
| 70 | `docs/_work/PREREG-M5-C2-REV4.md:67` | `9edbafa150700614` | `tools/kvshim_vk.dll` | `9edbafa150700614` / 50,007,552 B |
| 71 | `docs/_work/PREREG-M5-C2-REV5.md:4` | `6b0d750abbd06b1b` | `docs/_work/PREREG-M5-C2-B2EVAL.md` | `6b0d750abbd06b1b` / 4,113 B |
| 72 | `docs/_work/PREREG-M5-C2-REV5.md:4` | `553a96fc481fcf9c` | `kvmem/m2_visibility/m5/out/M5C2-B2EVAL.json` | `553a96fc481fcf9c` / 153,626 B |
| 73 | `docs/_work/PREREG-M5-C2-REV5.md:36` | `553a96fc481fcf9c` | `kvmem/m2_visibility/m5/out/M5C2-B2EVAL.json` | `553a96fc481fcf9c` / 153,626 B |
| 74 | `docs/_work/PREREG-M5-C2-REV5.md:38` | `a6bc4f268f7711de` | `kvmem/m2_visibility/m5/run_m5c2_rev4.py#REV4_TEMPLATE` | `a6bc4f268f7711de` |
| 75 | `docs/_work/PREREG-M5-C2-REV6-1.md:4` | `faaf2605116bb594` | `docs/_work/PREREG-M5-C2-REV6.md` | `faaf2605116bb594` / 5,773 B |
| 76 | `docs/_work/PREREG-M5-C2-REV6-1.md:4` | `5ad46f8efb762c6d` | `docs/_work/JUDGE-ROBUSTNESS-SPEC.md` | `5ad46f8efb762c6d` / 8,555 B |
| 77 | `docs/_work/PREREG-M5-C2-REV6.md:4` | `5ad46f8efb762c6d` | `docs/_work/JUDGE-ROBUSTNESS-SPEC.md` | `5ad46f8efb762c6d` / 8,555 B |
| 78 | `docs/_work/PREREG-M5-C2-REV6.md:4` | `f30d89e30262b148` | `docs/_work/PREREG-M5-C2-B4.md` | `f30d89e30262b148` / 10,910 B |
| 79 | `docs/_work/PREREG-M5-C2-REV6.md:9` | `783d423a39db02e3` | `kvmem/m2_visibility/m5/out/M5B4-RATES.json` | `783d423a39db02e3` / 121,993 B |
| 80 | `docs/_work/PREREG-M5-C2-REV6.md:50` | `c349ca5a93192aac` | `kvmem/m2_visibility/m5/out/M5B4-SENTENCES.json` | `c349ca5a93192aac` / 99,636 B |
| 81 | `docs/_work/PREREG-M5-C2-REV7.1.md:4` | `32eaf82ca56600c4` | `docs/_work/PREREG-M5-C2-REV7.md` | `32eaf82ca56600c4` / 5,835 B |
| 82 | `docs/_work/PREREG-M5-C2-REV7.1.md:5` | `1f8f44b921e575fe` | `kvmem/m2_visibility/m5/out/M5C2-REV7-OFFLINE.json` | `1f8f44b921e575fe` / 507,657 B |
| 83 | `docs/_work/PREREG-M5-C2-REV7.1.md:5` | `6695a4b4de403870` | `kvmem/m2_visibility/m5/out/_rev7_audit.py` | `6695a4b4de403870` / 57,234 B |
| 84 | `docs/_work/PREREG-M5-C2-REV7.1.md:6` | `9273ebc97aa1413a` | `kvmem/m2_visibility/m5/out/M5B4-LEAD-RULING.json` | `9273ebc97aa1413a` / 13,195 B |
| 85 | `docs/_work/PREREG-M5-C2-REV7.1.md:6` | `6a3001b6ca23ef7d` | `kvmem/m2_visibility/m5/out/M5B4-JUDGE.json` | `6a3001b6ca23ef7d` / 452,456 B |
| 86 | `docs/_work/PREREG-M5-C2-REV7.1.md:7` | `65ed60125528d5d6` | `kvmem/m2_visibility/m5/run_m5c2_rev7_offline.py` | `65ed60125528d5d6` / 44,761 B |
| 87 | `docs/_work/PREREG-M5-C2-REV7.1.md:38` | `32eaf82ca56600c4` | `docs/_work/PREREG-M5-C2-REV7.md` | `32eaf82ca56600c4` / 5,835 B |
| 88 | `docs/_work/PREREG-M5-C2-REV7.1.md:74` | `32eaf82ca56600c4` | `docs/_work/PREREG-M5-C2-REV7.md` | `32eaf82ca56600c4` / 5,835 B |
| 89 | `docs/_work/PREREG-M5-C2-REV7.1.md:74` | `32eaf82ca56600c4` | `docs/_work/PREREG-M5-C2-REV7.md` | `32eaf82ca56600c4` / 5,835 B |
| 90 | `docs/_work/PREREG-M5-C2-REV7.1.md:74` | `a6bc4f268f7711de` | `kvmem/m2_visibility/m5/run_m5c2_rev4.py#REV4_TEMPLATE` | `a6bc4f268f7711de` |
| 91 | `docs/_work/PREREG-M5-C2-REV7.1.md:81` | `6a3001b6ca23ef7d` | `kvmem/m2_visibility/m5/out/M5B4-JUDGE.json` | `6a3001b6ca23ef7d` / 452,456 B |
| 92 | `docs/_work/PREREG-M5-C2-REV7.1.md:81` | `9273ebc97aa1413a` | `kvmem/m2_visibility/m5/out/M5B4-LEAD-RULING.json` | `9273ebc97aa1413a` / 13,195 B |
| 93 | `docs/_work/PREREG-M5-C2-REV7.1.md:82` | `32eaf82ca56600c4` | `docs/_work/PREREG-M5-C2-REV7.md` | `32eaf82ca56600c4` / 5,835 B |
| 94 | `docs/_work/PREREG-M5-C2-REV7.1.md:140` | `65ed60125528d5d6` | `kvmem/m2_visibility/m5/run_m5c2_rev7_offline.py` | `65ed60125528d5d6` / 44,761 B |
| 95 | `docs/_work/PREREG-M5-C2-REV7.1.md:152` | `1f8f44b921e575fe` | `kvmem/m2_visibility/m5/out/M5C2-REV7-OFFLINE.json` | `1f8f44b921e575fe` / 507,657 B |
| 96 | `docs/_work/PREREG-M5-C2-REV7.1.md:156` | `32eaf82ca56600c4` | `docs/_work/PREREG-M5-C2-REV7.md` | `32eaf82ca56600c4` / 5,835 B |
| 97 | `docs/_work/PREREG-M5-C2-REV7.1.md:156` | `6a3001b6ca23ef7d` | `kvmem/m2_visibility/m5/out/M5B4-JUDGE.json` | `6a3001b6ca23ef7d` / 452,456 B |
| 98 | `docs/_work/PREREG-M5-C2-REV7.1.md:156` | `9273ebc97aa1413a` | `kvmem/m2_visibility/m5/out/M5B4-LEAD-RULING.json` | `9273ebc97aa1413a` / 13,195 B |
| 99 | `docs/_work/PREREG-M5-C2-REV7.1.md:156` | `c349ca5a93192aac` | `kvmem/m2_visibility/m5/out/M5B4-SENTENCES.json` | `c349ca5a93192aac` / 99,636 B |
| 100 | `docs/_work/PREREG-M5-C2-REV7.md:4` | `6a3001b6ca23ef7d` | `kvmem/m2_visibility/m5/out/M5B4-JUDGE.json` | `6a3001b6ca23ef7d` / 452,456 B |
| 101 | `docs/_work/PREREG-M5-C2-REV7.md:4` | `9273ebc97aa1413a` | `kvmem/m2_visibility/m5/out/M5B4-LEAD-RULING.json` | `9273ebc97aa1413a` / 13,195 B |
| 102 | `docs/_work/PREREG-M5-C2-REV7.md:5` | `faaf2605116bb594` | `docs/_work/PREREG-M5-C2-REV6.md` | `faaf2605116bb594` / 5,773 B |
| 103 | `docs/_work/PREREG-M5-C2-REV7.md:30` | `a6bc4f268f7711de` | `kvmem/m2_visibility/m5/run_m5c2_rev4.py#REV4_TEMPLATE` | `a6bc4f268f7711de` |
| 104 | `docs/_work/PREREG-M5-C2-REV7.md:71` | `6a3001b6ca23ef7d` | `kvmem/m2_visibility/m5/out/M5B4-JUDGE.json` | `6a3001b6ca23ef7d` / 452,456 B |
| 105 | `docs/_work/PREREG-M5-C2-REV7.md:71` | `9273ebc97aa1413a` | `kvmem/m2_visibility/m5/out/M5B4-LEAD-RULING.json` | `9273ebc97aa1413a` / 13,195 B |
| 106 | `docs/_work/PREREG-M5-C2-SEMANTIC.md:11` | `df1ae09cc9ecc0d2` | `docs/_work/LEAD-M5-B-ADJUDICATION.md` | `df1ae09cc9ecc0d2` / 5,627 B |
| 107 | `docs/_work/PREREG-M5-C2-SEMANTIC.md:11` | `9ac66b6dfaf8f804` | `kvmem/m2_visibility/m5/out/M5B2-RATES.json` | `9ac66b6dfaf8f804` / 11,407 B |
| 108 | `docs/_work/PREREG-M5-C2-SEMANTIC.md:11` | `482a94820917d16e` | `docs/_work/PREREG-M5-B2.md` | `482a94820917d16e` / 12,695 B |
| 109 | `docs/_work/PREREG-M5-C2-SEMANTIC.md:66` | `482a94820917d16e` | `docs/_work/PREREG-M5-B2.md` | `482a94820917d16e` / 12,695 B |
| 110 | `docs/_work/PREREG-M5-C2-SEMANTIC.md:67` | `cc03e48c360ae0ee` | `kvmem/m2_visibility/m5/m5_ground_v2_3.py` | `cc03e48c360ae0ee` / 44,209 B |
| 111 | `docs/_work/PREREG-M5-C2-SEMANTIC.md:68` | `9ac66b6dfaf8f804` | `kvmem/m2_visibility/m5/out/M5B2-RATES.json` | `9ac66b6dfaf8f804` / 11,407 B |
| 112 | `docs/_work/PREREG-M5-C2-SEMANTIC.md:69` | `df1ae09cc9ecc0d2` | `docs/_work/LEAD-M5-B-ADJUDICATION.md` | `df1ae09cc9ecc0d2` / 5,627 B |
| 113 | `docs/_work/PREREG-M5-C2-SEMANTIC.md:70` | `0d882f20987fea70` | `kvmem/m2_visibility/m5/out/M5C-36-adj.json` | `0d882f20987fea70` / 60,432 B |
| 114 | `docs/_work/PREREG-M5-C2-SEMANTIC.md:71` | `5a3f12f2a742a864` | `docs/_work/PREREG-M5-JUDGE-v2.3.md` | `5a3f12f2a742a864` / 10,394 B |
| 115 | `docs/_work/INSPECTOR-M5C2-REV7.md:5` | `32eaf82ca56600c4` | `docs/_work/PREREG-M5-C2-REV7.md` | `32eaf82ca56600c4` / 5,835 B |
| 116 | `docs/_work/INSPECTOR-M5C2-REV7.md:24` | `6695a4b4de403870` | `kvmem/m2_visibility/m5/out/_rev7_audit.py` | `6695a4b4de403870` / 57,234 B |
| 117 | `docs/_work/INSPECTOR-M5C2-REV7.md:25` | `6a3001b6ca23ef7d` | `kvmem/m2_visibility/m5/out/M5B4-JUDGE.json` | `6a3001b6ca23ef7d` / 452,456 B |
| 118 | `docs/_work/INSPECTOR-M5C2-REV7.md:25` | `9273ebc97aa1413a` | `kvmem/m2_visibility/m5/out/M5B4-LEAD-RULING.json` | `9273ebc97aa1413a` / 13,195 B |
| 119 | `docs/_work/INSPECTOR-M5C2-REV7.md:39` | `32eaf82ca56600c4` | `docs/_work/PREREG-M5-C2-REV7.md` | `32eaf82ca56600c4` / 5,835 B |
| 120 | `docs/_work/INSPECTOR-M5C2-REV7.md:40` | `6a3001b6ca23ef7d` | `kvmem/m2_visibility/m5/out/M5B4-JUDGE.json` | `6a3001b6ca23ef7d` / 452,456 B |
| 121 | `docs/_work/INSPECTOR-M5C2-REV7.md:41` | `9273ebc97aa1413a` | `kvmem/m2_visibility/m5/out/M5B4-LEAD-RULING.json` | `9273ebc97aa1413a` / 13,195 B |
| 122 | `docs/_work/INSPECTOR-M5C2-REV7.md:143` | `1f8f44b921e575fe` | `kvmem/m2_visibility/m5/out/M5C2-REV7-OFFLINE.json` | `1f8f44b921e575fe` / 507,657 B |
| 123 | `docs/_work/INSPECTOR-M5C2-REV7.md:158` | `65ed60125528d5d6` | `kvmem/m2_visibility/m5/run_m5c2_rev7_offline.py` | `65ed60125528d5d6` / 44,761 B |
| 124 | `docs/_work/INSPECTOR-M5C2-REV7.md:174` | `c349ca5a93192aac` | `kvmem/m2_visibility/m5/out/M5B4-SENTENCES.json` | `c349ca5a93192aac` / 99,636 B |
| 125 | `docs/_work/INSPECTOR-M5C2-REV7.md:202` | `1f8f44b921e575fe` | `kvmem/m2_visibility/m5/out/M5C2-REV7-OFFLINE.json` | `1f8f44b921e575fe` / 507,657 B |
| 126 | `docs/_work/INSPECTOR-M5C2-REV7.md:203` | `1f8f44b921e575fe` | `kvmem/m2_visibility/m5/out/M5C2-REV7-OFFLINE.json` | `1f8f44b921e575fe` / 507,657 B |
| 127 | `docs/_work/INSPECTOR-M5C2-REV7.md:204` | `1f8f44b921e575fe` | `kvmem/m2_visibility/m5/out/M5C2-REV7-OFFLINE.json` | `1f8f44b921e575fe` / 507,657 B |
| 128 | `docs/_work/INSPECTOR-M5C2-REV7.md:206` | `de80cd38a7147f0f` | `kvmem/m2_visibility/m5/out/M5C2-REV7-AUDIT.json` | `de80cd38a7147f0f` / 55,523 B |
| 129 | `docs/_work/INSPECTOR-M5C2-REV7.md:223` | `6695a4b4de403870` | `kvmem/m2_visibility/m5/out/_rev7_audit.py` | `6695a4b4de403870` / 57,234 B |
| 130 | `docs/_work/INSPECTOR-M5C2-REV7.md:224` | `de80cd38a7147f0f` | `kvmem/m2_visibility/m5/out/M5C2-REV7-AUDIT.json` | `de80cd38a7147f0f` / 55,523 B |
| 131 | `docs/_work/INSPECTOR-M5C2-REV7.md:227` | `65ed60125528d5d6` | `kvmem/m2_visibility/m5/run_m5c2_rev7_offline.py` | `65ed60125528d5d6` / 44,761 B |
| 132 | `docs/_work/INSPECTOR-M5C2-REV7.md:227` | `1f8f44b921e575fe` | `kvmem/m2_visibility/m5/out/M5C2-REV7-OFFLINE.json` | `1f8f44b921e575fe` / 507,657 B |
| 133 | `kvmem/m2_visibility/m5/out/M5B4-RATES.md:3` | `6a3001b6ca23ef7d` | `kvmem/m2_visibility/m5/out/M5B4-JUDGE.json` | `6a3001b6ca23ef7d` / 452,456 B |
| 134 | `kvmem/m2_visibility/m5/out/M5B4-RATES.md:5` | `783d423a39db02e3` | `kvmem/m2_visibility/m5/out/M5B4-RATES.json` | `783d423a39db02e3` / 121,993 B |
| 135 | `kvmem/m2_visibility/m5/out/M5B4-RATES.md:6` | `f30d89e30262b148` | `docs/_work/PREREG-M5-C2-B4.md` | `f30d89e30262b148` / 10,910 B |
| 136 | `kvmem/m2_visibility/m5/out/M5B4-AB-OLD-VS-NEW.md:6` | `c349ca5a93192aac` | `kvmem/m2_visibility/m5/out/M5B4-SENTENCES.json` | `c349ca5a93192aac` / 99,636 B |
| 137 | `kvmem/m2_visibility/m5/out/M5B4-AB-OLD-VS-NEW.md:7` | `6a3001b6ca23ef7d` | `kvmem/m2_visibility/m5/out/M5B4-JUDGE.json` | `6a3001b6ca23ef7d` / 452,456 B |
| 138 | `kvmem/m2_visibility/m5/out/M5B4-AB-OLD-VS-NEW.md:8` | `0ff84d2617ab8b99` | `kvmem/m2_visibility/m5/out/M5B4-AB-OLD-VS-NEW.json` | `0ff84d2617ab8b99` / 68,603 B |
| 139 | `kvmem/m2_visibility/m5/out/M5B4-AB-OLD-VS-NEW.md:13` | `cc03e48c360ae0ee` | `kvmem/m2_visibility/m5/m5_ground_v2_3.py` | `cc03e48c360ae0ee` / 44,209 B |
| 140 | `README.md:19` | `db32faae83bec9fc` | `patches/persistent-memory.patch` | `db32faae83bec9fc` / 32,337 B |
| 141 | `README.md:70` | `21ec668df2171350` | `docs/_work/M2-ACCEPT-lead.md` | `21ec668df2171350` / 10,479 B |
| 142 | `README.md:70` | `84ec4e3f9b493cf7` | `docs/_work/M2-FULL-FINAL-lead.md` | `84ec4e3f9b493cf7` / 8,368 B |
| 143 | `README.md:158` | `c7c8b264f960daea` | `verify.sh` | `c7c8b264f960daea` / 6,566 B |
| 144 | `README.md:220` | `cb11df4453756882` | `kvmem/m2_visibility/ISOLATION-REPORT.md` | `cb11df4453756882` / 19,043 B |

> 其中 `a6bc4f268f7711de` 不是文件哈希，而是**抽取 prompt 模板**的 sha16 —— 已从 `run_m5c2_rev4.py` 的 `REV4_TEMPLATE` 字面量**重算命中**（266 字符）；`9edbafa150700614` 是 GPU shim DLL 的 sha256 前缀 —— `tools/kvshim_vk.dll` 现字节即此值（50,007,552 B）。这两条此前容易被当成“不可验证”，实际都可复算。

### 2.2 stale_reconstructible（1 条）—— 过期但能精确复原

- `docs/_work/PREREG-M5-C2-REV7.md:7` 引用 `e306ce994d306a84`（目标 `docs/_work/PREREG-M5-C2-B5.md`）
  - 复算：`truncate_at("## 9 LEAD 追加") then rstrip()` ⇒ **e306ce994d306a84 / 11,388 B**（`verified=True`）
  - 现行文件：`d6c7bdac73ef7326 / 14,597 B`；raw 截断体（未 rstrip，11,390 B）哈希 `9c09ceaf99d37a23` ≠ 引用值
  - 含义：**§9 并非冻结后追加**——B5 于 19:54:15 写入 §9、19:55 冻结、`full@5574253`（19:59:10）的 blob 也含 §9；REV7 19:53 起草时 B5 尚无 §9，20:15 声明冻结时未重钉 ⇒ **stale-at-freeze**。另：B5 §9 标题自称 `2026-10-26T20:20+08:00`，与 mtime 19:54:15 / frozen_at 19:55 矛盾（声明时间不实）。

### 2.3 stale_unresolved（4 条）—— 过期且无法复原

- `docs/_work/PREREG-M5-C2-B5.md:6` 引用 `e9a88fda` → 目标 `docs/_work/PREREG-M5-C2-B4.md`（当前 `f30d89e30262b148` / 10,910 B）
  - 已试尽：当前 B4 的**所有行边界截断**（raw/rstrip/rstrip+LF/CRLF）、归档草稿 `6f41f3d6`(7,823 B)、git 全部 1,491 个 blob、全树内容哈希 —— **均无 e9a88fda**。
  - 对照：`PREREG-M5-C2-REV6.md:4` 对同一文件引 `f30d89e30262b148`（=现值）⇒ B5 的 `e9a88fda` 是孤例，最可能是笔误或某次未入树的中间态。
  - 说明：B5 引用的 B4 哈希：当前 B4、归档草稿、全部 git blob、各种截断/换行变体均不等于此值；REV6 同一 B4 引的是当前值 f30d89e3
- `docs/_work/PREREG-M5-C2-B6.md:6` 引用 `e9a88fda` → 目标 `docs/_work/PREREG-M5-C2-B4.md`（当前 `f30d89e30262b148` / 10,910 B）
  - 已试尽：当前 B4 的**所有行边界截断**（raw/rstrip/rstrip+LF/CRLF）、归档草稿 `6f41f3d6`(7,823 B)、git 全部 1,491 个 blob、全树内容哈希 —— **均无 e9a88fda**。
  - 对照：`PREREG-M5-C2-REV6.md:4` 对同一文件引 `f30d89e30262b148`（=现值）⇒ B5 的 `e9a88fda` 是孤例，最可能是笔误或某次未入树的中间态。
  - 说明：B5 引用的 B4 哈希：当前 B4、归档草稿、全部 git blob、各种截断/换行变体均不等于此值；REV6 同一 B4 引的是当前值 f30d89e3
- `kvmem/m2_visibility/m5/out/M5B4-RATES.md:4` 引用 `9054479b32b79eb1` → 目标 `kvmem/m2_visibility/m5/out/M5B4-LEAD-RULING.json`（当前 `9273ebc97aa1413a` / 13,195 B）
  - 已试尽：现行 `9273ebc9 / 13,195 B` 的全部截断变体、git 全部 blob、全树 —— 旧版 `10,208 B` 字节**未保留**。
  - **但数值等价可证**：RATES / AB 里 261 条 `gold` 与现文件**逐 sid 相同（0 差异）**，`gold_changed=false`，故 4/41、7/46 等读数不受影响。
  - 说明：RATES/AB 记录的“金标”历史坐标（10,208 B，19:00 audit_fix 前）；现文件为 9273ebc9（13,195 B）；旧版本字节未保留，但 gold 逐 sid 值未变（可证数值等价）
- `kvmem/m2_visibility/m5/out/M5B4-AB-OLD-VS-NEW.md:5` 引用 `9054479b32b79eb1` → 目标 `kvmem/m2_visibility/m5/out/M5B4-LEAD-RULING.json`（当前 `9273ebc97aa1413a` / 13,195 B）
  - 已试尽：现行 `9273ebc9 / 13,195 B` 的全部截断变体、git 全部 blob、全树 —— 旧版 `10,208 B` 字节**未保留**。
  - **但数值等价可证**：RATES / AB 里 261 条 `gold` 与现文件**逐 sid 相同（0 差异）**，`gold_changed=false`，故 4/41、7/46 等读数不受影响。
  - 说明：RATES/AB 记录的“金标”历史坐标（10,208 B，19:00 audit_fix 前）；现文件为 9273ebc9（13,195 B）；旧版本字节未保留，但 gold 逐 sid 值未变（可证数值等价）

### 2.4 unverifiable（2 条）—— 无法复算

- `20261026`（1 处，例：`docs/_work/PREREG-M5-C2-R2.md:52`）：R2 §… 的 neg_control_seed=20261026 是随机种子，不是哈希；被 8-hex 正则误捕
- `6f26bce0`（1 处，例：`README.md:70`）：M2-ACCEPT-lead.md 的“已签”历史坐标；签署版字节不在工作树/全部 git blob 中，不可复算；README/INDEX 已把它与现行 21ec668d 并列

> `6f26bce0` 是 M2-ACCEPT-lead.md 的“已签”历史坐标，签署版字节不在树/不在 git，**不可复算**；README/INDEX 已把它与现行 `21ec668d` 并列，属澄清写法，不是“把旧值当现值”。
> `20261026` 其实是 `neg_control_seed`（随机种子），被 8-hex 正则误捕，**不是哈希引用**。

## 3 数字主张 vs 真实数据

| # | 主张 | 出处 | 声称 | 复算 | 判定 |
|---|---|---|---|---|---|
| N01 | 样本 261 句 | `kvmem/m2_visibility/m5/out/M5B4-RATES.md:7`；`docs/_work/PREREG-M5-C2-REV7.md:70` | 261 | 261 | **match** |
| N02 | 金标四态 46 / 41 / 164 / 10 | `kvmem/m2_visibility/m5/out/M5B4-LEAD-RULING.json:27` | support 46 / fabricated 41 / no_fact 164 / undecidable 10 | {'support_present': 46, 'no_fact': 164, 'undecidable': 10, 'fabricated': 41} | **match** |
| N03 | rev5.1 误判 7/46 = 15.22% | `kvmem/m2_visibility/m5/out/M5B4-RATES.md:101` | 7/46 = 15.22% | recomputed 7/46 = 15.22% | **match** |
| N04 | rev5.1 漏判 4/41 = 9.76% | `kvmem/m2_visibility/m5/out/M5B4-RATES.md:101` | 4/41 = 9.76% | recomputed 4/41 = 9.76% | **match** |
| N05 | parse_fail 1/261 | `kvmem/m2_visibility/m5/out/M5B4-RATES.md:49` | 1/261 | recomputed 1/261 | **match** |
| N06 | rev7 误判 2/46 | `docs/_work/PREREG-M5-C2-REV7.md:60`；`kvmem/m2_visibility/m5/out/M5C2-REV7-OFFLINE.json:96` | 2/46 | 2/46 | **match** |
| N07 | rev7 漏判 4/41 | `kvmem/m2_visibility/m5/out/M5C2-REV7-OFFLINE.json:443` | 4/41 | 4/41 | **match** |
| N08 | rev7 parse_fail 1/261 | `kvmem/m2_visibility/m5/out/M5C2-REV7-OFFLINE.json:52` | 1/261 | 1/261 | **match** |
| N09 | rev7 新增漏判 = 0 | `kvmem/m2_visibility/m5/out/M5C2-REV7-OFFLINE.json:455` | 0/35 | 0/35 | **match** |
| N10 | rev7 N3 作废条目 124/777 | `kvmem/m2_visibility/m5/out/M5C2-REV7-OFFLINE.json:495` | 124/777 | 124/777 | **match** |
| N11 | rev6 前逐字率 98.45% = 318/323 | `docs/_work/PREREG-M5-C2-REV7.md:25` | 98.45% (318/323) | {"quote_bearing_items": 323, "verbatim_hits": 318, "evidence_verbatim_rate": 0.98452, "all_items": 777, "all_items_verbatim_hits": 318, "all_items_verbatim_rate": 0.409266, "sentences_with_quote_items": 98, "sentences_all_verbatim": 95, "sentence_all_verbatim_rate": 0.969388, "definition": "quote-bearing = evidence non-empty and no explicit 未提及/未找到/找不到; exact substring in source_text"} | **match** |
| N12 | rev6 后逐字率 90.88% = 289/318 | `docs/_work/PREREG-M5-C2-REV7.md:25` | 90.88% (289/318) | {"quote_bearing_items": 318, "verbatim_hits": 289, "evidence_verbatim_rate": 0.908805, "all_items": 513, "all_items_verbatim_hits": 289, "all_items_verbatim_rate": 0.563353, "sentences_with_quote_items": 105, "sentences_all_verbatim": 89, "sentence_all_verbatim_rate": 0.847619, "definition": "quote-bearing = evidence non-empty and no explicit 未提及/未找到/找不到; exact substring in source_text"} | **match** |
| N13 | rev6 读数：漏判 6/41、误判 4/46、parse_fail 3 | `docs/_work/PREREG-M5-C2-REV7.md:26` | 6/41 ; 4/46 ; 3 | leak {"n": 6, "denominator": 41, "rate": 0.146341, "sids": ["b4-s2-q1-s05", "b4-s2-q2-s01", "b4-s2-q3-s07", "b4-s3-q4-s11", "b4-s3-q5-s06", "b4-s3-q5-s08"]} ; false_unsupported {"n": 4, "denominator": 46, "rate": 0.086957, "wilson95": {"n": 46, "k": 4, "rate": 0.086957, "lo": 0.034335, "hi": 0.203249}, "sids": ["b4-s1-q2-s01", "b4-s1-q ; parse_fail {"n": 3, "rate": 0.011494, "sids": ["b4-s1-q1-s02", "b4-s1-q1-s05", "b4-s1-q3-s04"]} | **match** |
| N14 | v2.3 在 b4 上 3/41=7.32% 与 11/46=23.91% | `kvmem/m2_visibility/m5/out/M5B4-AB-OLD-VS-NEW.md:22` | 3/41 = 7.32% ; 11/46 = 23.91% | 3/41 = 7.32% ; 11/46 = 23.91% | **match** |
| N15 | b2 时代口径：旧 29/41=70.73%、新 6/41=14.63% | `kvmem/m2_visibility/m5/out/M5B4-AB-OLD-VS-NEW.md:60` | 29/41 = 70.73% ; 6/41 = 14.63% | 29/41 = 70.73% ; 6/41 = 14.63% | **match** |
| N16 | FLOOR-REV2 39 例 + 臂6 8/8、臂2 6/6、臂3 6/6、臂5 7/7 | `docs/_work/PREREG-M5-C2-REV4.md:14`；`docs/_work/PREREG-M5-C2-B5.md:168` | 39 例；8/8, 6/6, 6/6, 7/7 | n=39；{"arm2": "6/6", "arm3": "6/6", "arm5": "7/7", "arm6": "8/8"} | **match** |
| N17 | floor 31/31 全 A（含空源文 6/6 判 A） | `docs/_work/PREREG-M5-C2-REV4.md:11` | 31/31 全 A | 31/31 全 A（arm1 空源文 A=6/6） | **match_numeric_provenance_loose** |
| N18 | B2EVAL 106 句 | `kvmem/m2_visibility/m5/out/M5B4-RATES.md:7` | 106 句 | 106 | **match** |
| N19 | (b2) 510 句 + 金标 71/35/385/19 | `docs/_work/PREREG-M5-C2-B2EVAL.md:32` | 510 句；71/35/385/19 | 510 句；{"support_present": 71, "fabricated": 35, "no_fact": 385, "undecidable": 19} | **match** |
| N20 | 补丁 6 文件 / 600 insertions / 0 deletions（32,337 B, db32faae） | `README.md:19` | 6 文件 / 600 / 0 / 32,337 B | 6 文件 / 600 / 0 / 32337 B / db32faae83bec9fc | **match** |
| N21 | verify.sh 124 行 / 12 项关系断言（c7c8b264） | `README.md:158` | 124 行 / 12 项 / c7c8b264f960daea | 124 行 / 12 项（4 补丁关系+2 边车+6 expect）/ c7c8b264f960daea | **match** |
| N22 | ISOLATION-REPORT.md = cb11df44 / 19,043 B | `README.md:220` | cb11df4453756882 / 19,043 B | cb11df4453756882 / 19043 B | **match** |
| N23 | B5 §8.1 LEAD 复测：4-gram 与 (b2) 共享 2 个（80元，/00元，） | `docs/_work/PREREG-M5-C2-B5.md:128` | 2 个：80元， 00元， | 2 个：00元， / 80元， | **match** |
| N24 | B5 §8.1 LEAD 复测：4-gram 与 (b4) 共享 8 个 | `docs/_work/PREREG-M5-C2-B5.md:129` | 8 个：期多长？/90天，/发票吗？/80元，/是什么？/费多少？/00元，/是多少？ | 8 个：00元， / 80元， / 90天， / 发票吗？ / 是什么？ / 是多少？ / 期多长？ / 费多少？ | **match** |
| N25 | B5 §8.1「16 个已占领域名出现次数 = 全 0」 | `docs/_work/PREREG-M5-C2-B5.md:130` | 全 0 | 全文计数：{"租车": 1, "物业": 1}；§1 题面内计数：{} | **mismatch_literal_ok_within_section1** |
| N26 | B5 §8.1「关键专有名词 全 0」 | `docs/_work/PREREG-M5-C2-B5.md:119` | 全 0 | 全文计数：{"仁和口腔": 1, "迅达租车": 1, "华庭物业": 1, "北方联通": 1, "力量方舟": 1}；§1 题面内计数：{"仁和口腔": 0, "迅达租车": 0, "华庭物业": 0, "北方联通": 0, "力量方舟": 0} | **mismatch_literal_ok_within_section1** |
| N27 | B5 40 题 / 8 场景 / 3 detail + 2 lure / 源文字数 | `docs/_work/PREREG-M5-C2-B5.md:1` | 8 场景、40 题、24 detail + 16 lure、字数 59/59/52/53/52/55/52/50 | 场景 8、题 40（detail 24 / lure 16）、字数 59/59/52/53/52/55/52/50 | **match** |
| N28 | B4 40 题 / 8 场景 / 源文字数 / 归档草稿 7,823 B | `docs/_work/PREREG-M5-C2-B4.md:1` | 8 场景、40 题、字数 69/68/60/57/55/59/51/59、草稿 6f41f3d6 / 7,823 B | 场景 8、题 40、字数 69/68/60/57/55/59/51/59、草稿 6f41f3d6ee318587 / 7823 B | **match** |
| N29 | REV7 §0 归因表：N1=4、N2=2、N3=2（与上重叠 1 例） | `docs/_work/PREREG-M5-C2-REV7.md:15` | N1 4 / N2 2 / N3 2（重叠 1） | N1 3 / N2 2 / N3 2（重叠 0，7 例互不重复）：[["b4-s1-q2-s01", "N1"], ["b4-s1-q2-s07", "N3"], ["b4-s1-q2-s09", "N3"], ["b4-s1-q2-s15", "N1"], ["b4-s1-q3-s03", "N1"], ["b4-s2-q1-s01", "N2"], ["b4-s8-q2-s02", "N2"]] | **mismatch** |
| N30 | REV7 §0：7 例误判中 R4+ fabricated_evidence 命中 = 0 | `docs/_work/PREREG-M5-C2-REV7.md:11` | 0 | 7 例 FP 的 rev5.1 rule_hits 中 R4+ 数 = 0 | **match** |
| N31 | REV7 §0 覆盖率 0.75 / 0.333 / 0.5 | `docs/_work/PREREG-M5-C2-REV7.md:15` | 0.75；0.333；0.5 | 0.750；0.333；0.500（N1 修复后 8600元 = 1.0） | **match** |
| N32 | INSPECTOR「M5B4-JUDGE.json / 452456 B / 261 行」 | `docs/_work/INSPECTOR-M5C2-REV7.md:40` | 452,456 B / 261 行 | 452,456 B / 17040 行（JSON pretty-print） | **mismatch** |
| N33 | REV7 §2 N3 自检断言：患者 必须 valid=false | `docs/_work/PREREG-M5-C2-REV7.md:49` | valid=false | {"A2_pass": false, "A3_pass": false, "A2_valid": true, "A3_n_occurrences": 13} | **mismatch_unsatisfiable** |
| N34 | REV7.1 附录 B：14 个判定函数与 rev7 逐字节相同 | `docs/_work/PREREG-M5-C2-REV7.1.md:140` | 14 个函数逐字节相同；仅 verify_inputs/main 不同 + 新增 2 个断言函数 | identical=14 ['sha16', 'write_json_atomic', 'normalize7', 'value_tokens', 'token_kind_of_span', 'matcher', 'r1_r2_r3_rev7', 'r4_plus_rev7', 'verdict_v51', 'baseline_reproduce', 'judge_row_rev7', 'pick_attribution', 'rev7_causes', 'char_evidence'] ; differ=['verify_inputs', 'main'] ; only_rev7.1=['item_assertion', 'verdict_assertion'] | **match** |
| N35 | REV7.1：rev7.1 在 b4 上实测四门槛 2/46、4/41、1/261、new_miss 0/35 | `docs/_work/PREREG-M5-C2-REV7.1.md:72` | 2/46、4/41、1/261、0/35 | 产物 55191eaf2426f736 / 510,508 B，gate = 2/46、4/41、1/261、0/35；与 rev7 产物差异键 = ['assertions', 'code_bytes', 'code_file', 'code_sha16', 'inputs', 'prereg_sha16', 'schema'] | **match** |
| N36 | REV7.1：7 句变化 = 5 fixed / 0 broken / 2 neutral | `docs/_work/PREREG-M5-C2-REV7.1.md:73` | 7 = 5 fixed + 0 broken + 2 neutral | n_changed=7, fixed=5, broken=0, neutral=2 | **match** |
| N37 | B5 §9.5：要求 (b6) 在 (b5) 开跑前出题并冻结 | `docs/_work/PREREG-M5-C2-B5.md:173` | 存在已冻结的 (b6) 题面 | B6 已出题：ac27d47d3a3efff9 / 17,374 B（8 场景、40 题）；头注 frozen=true | **match** |
| N38 | INSPECTOR：两次重跑与既有产物完全同字节（1f8f44b9 / 507,657 B） | `docs/_work/INSPECTOR-M5C2-REV7.md:27` | 同字节；1f8f44b9 / 507657 B | 产物现值 1f8f44b921e575fe / 507657 B（与 git 已提交 blob 同字节）；“两次重跑一致”本次未复跑，无法验证 | **unverifiable** |
| N39 | M5B4-RATES.md / AB：金标 = 9054479b32b79eb1 / 10,208 B | `kvmem/m2_visibility/m5/out/M5B4-RATES.md:4`；`kvmem/m2_visibility/m5/out/M5B4-AB-OLD-VS-NEW.md:5` | 9054479b32b79eb1 / 10,208 B | 现文件 9273ebc97aa1413a / 13195 B | **stale_historical_snapshot_values_equivalent** |
| N40 | B6：8 场景 × 5 题 = 40（24 detail + 16 lure） | `docs/_work/PREREG-M5-C2-B6.md:1` | 8 场景 / 40 题 / 24 detail + 16 lure | md：8 场景 / 40 题（detail 24 / lure 16）；json：8 场景 / 40 题 / detail 24 / lure 16 | **match** |
| N41 | B6 附录 A：与 (b2)/(b4)/(b5) 的共享 4-gram = 0 / 0 / 0 | `docs/_work/PREREG-M5-C2-B6.md:197` | 0 / 0 / 0 | 0 / 0 / 0 | **match** |
| N42 | B6：json.prereg_sha16 = 本件 md 全文件 sha16（零自指口径） | `kvmem/m2_visibility/m5/out/M5C2-B6-SENTENCES.json:4` | json.prereg_sha16 = md sha256[:16] | md ac27d47d3a3efff9 / 17,374 B；json.prereg_sha16 = ac27d47d3a3efff9；json 本身 23588ec099ca9255 / 9,482 B | **match** |
| N43 | B6：md 内不含自身哈希、也不含 json 哈希（零自指） | `docs/_work/PREREG-M5-C2-B6.md:7` | md 不含自身/json 哈希 | md 含自身哈希=False；含 json 哈希=False | **match** |
| N44 | B6：8 领域与已占 16 域交集 = ∅；自造专名在 b2/b4/b5 出现 0 次 | `docs/_work/PREREG-M5-C2-B6.md:135` | 交集 ∅；专名各 0 次 | 交集 []；已占域 16 个（b2 8 + b4 8 + b5 8 = 24）；专名命中 {"洁雅干洗店": 0, "遇见花店": 0, "美然理发店": 0, "恒信修表店": 0, "康宁体检中心": 0, "城东体育馆": 0, "市图书馆": 0, "社区药店": 0} | **match** |
| N45 | B6 附录 A：md↔json 逐字一致 48/48（8 源文 + 40 问） | `docs/_work/PREREG-M5-C2-B6.md:176` | 48/48 | md 侧 48 条 / json 侧 48 条；json 字符串在 md 中找到 48，md 字符串在 json 中找到 48 | **match** |
| N46 | REV7.1 附录 B：14 个判定函数与 rev7 逐字节相同；脚本 50,618 B / 88256d27 | `docs/_work/PREREG-M5-C2-REV7.1.md:140` | 14 个函数相同；code_sha16=88256d274c9993cc / 50,618 B | 相同函数 14 个；脚本 88256d274c9993cc / 50,618 B | **match** |
| N47 | REV7.1 §6 状态行 executed=false，但重跑产物已存在 | `docs/_work/PREREG-M5-C2-REV7.1.md:160` | executed=false | 产物 55191eaf2426f736 / 510,508 B（mtime 2026-10-26T21:07:27+08:00）存在；头注 frozen=true@21:06:55；即“已执行但状态未更新” | **mismatch** |

### 3.1 对不上的项（逐条说明）

**N25 — B5 §8.1「16 个已占领域名出现次数 = 全 0」**（出处 `docs/_work/PREREG-M5-C2-B5.md:130`）

- 声称：`全 0`
- 复算：`全文计数：{"租车": 1, "物业": 1}；§1 题面内计数：{}`
- 方法：substring count in whole file vs §1
- 说明：字面写「本文件/全 0」为假：租车、物业各 1 次（均出现在 §8.1 本行名单里）；若按「§1 题面」口径则为 0

**N26 — B5 §8.1「关键专有名词 全 0」**（出处 `docs/_work/PREREG-M5-C2-B5.md:119`）

- 声称：`全 0`
- 复算：`全文计数：{"仁和口腔": 1, "迅达租车": 1, "华庭物业": 1, "北方联通": 1, "力量方舟": 1}；§1 题面内计数：{"仁和口腔": 0, "迅达租车": 0, "华庭物业": 0, "北方联通": 0, "力量方舟": 0}`
- 方法：substring count in whole file vs §1
- 说明：同一行行名即含 5 个专名 ⇒ 字面计数各 1；题面内 0

**N29 — REV7 §0 归因表：N1=4、N2=2、N3=2（与上重叠 1 例）**（出处 `docs/_work/PREREG-M5-C2-REV7.md:15`）

- 声称：`N1 4 / N2 2 / N3 2（重叠 1）`
- 复算：`N1 3 / N2 2 / N3 2（重叠 0，7 例互不重复）：[["b4-s1-q2-s01", "N1"], ["b4-s1-q2-s07", "N3"], ["b4-s1-q2-s09", "N3"], ["b4-s1-q2-s15", "N1"], ["b4-s1-q3-s03", "N1"], ["b4-s2-q1-s01", "N2"], ["b4-s8-q2-s02", "N2"]]`
- 方法：recompute from REV7 产物 false_by_reason.attribution + JUDGE rule_hits
- 说明：总数 7 正确，但分解不可复算：N1 实为 3（且该行只列 3 个 sid 却写 4）；N3 两例与 N2 无重叠；JUDGE 中 R1 value_mismatch 共 5 次 = 3 次标点型（8600元）+ 2 次实体贪心型

**N32 — INSPECTOR「M5B4-JUDGE.json / 452456 B / 261 行」**（出处 `docs/_work/INSPECTOR-M5C2-REV7.md:40`）

- 声称：`452,456 B / 261 行`
- 复算：`452,456 B / 17040 行（JSON pretty-print）`
- 方法：line count
- 说明：字节与 sha 均对；“261 行”与文件实际行数不符（261 应是句数，单位写错）

**N33 — REV7 §2 N3 自检断言：患者 必须 valid=false**（出处 `docs/_work/PREREG-M5-C2-REV7.md:49`）

- 声称：`valid=false`
- 复算：`{"A2_pass": false, "A3_pass": false, "A2_valid": true, "A3_n_occurrences": 13}`
- 方法：run product assertions A2/A3
- 说明：按字面 N3（子串命中⇒valid=true），患者在句首「患者：」中逐字存在 ⇒ 断言不可满足；产物 A2/A3 pass=false。REV7.1 已撤回该断言

**N47 — REV7.1 §6 状态行 executed=false，但重跑产物已存在**（出处 `docs/_work/PREREG-M5-C2-REV7.1.md:160`）

- 声称：`executed=false`
- 复算：`产物 55191eaf2426f736 / 510,508 B（mtime 2026-10-26T21:07:27+08:00）存在；头注 frozen=true@21:06:55；即“已执行但状态未更新”`
- 方法：compare status line vs artifact existence
- 说明：不影响数值/判定，只是状态字段过期；建议把 executed 改为 true 并重钉产物 sha16

### 3.2 不可复算 / 历史快照

- **N38 — INSPECTOR：两次重跑与既有产物完全同字节（1f8f44b9 / 507,657 B）**：产物现值 1f8f44b921e575fe / 507657 B（与 git 已提交 blob 同字节）；“两次重跑一致”本次未复跑，无法验证（方法：no rerun performed (discipline: read-only, zero execution of GPU/model runners)）；按纪律不执行执行者脚本；仅能确认落盘产物与提交 blob 一致
- **N39 — M5B4-RATES.md / AB：金标 = 9054479b32b79eb1 / 10,208 B**：现文件 9273ebc97aa1413a / 13195 B（方法：hash/size compare + gold values compare）；旧版字节未保留（全树/全部 git blob 均无 9054479b）；但 RATES/AB 中 261 条 gold 与现文件逐 sid 相同（0 差异）⇒ 4/41、7/46 等数值不受影响

## 4 建议更正清单（只建议，未改被审文件）

> **2026-10-26 复核更正（X04/X05）**：初版把 B5 §9 描述为“19:55 冻结后 20:20 追加”，该前提已被独立复核推翻 —— B5 mtime=**19:54:15**（早于 frozen_at 19:55），`git cat-file -p full:docs/_work/PREREG-M5-C2-B5.md` = `d6c7bdac73ef7326` / 14,597 B 且含 §9（full commit 19:59:10）。真实缺陷是“REV7 19:53 起草时 B5 尚无 §9，20:15 冻结时未重钉 ⇒ stale-at-freeze”，以及“B5 §9 标题自称 20:20 与 mtime/frozen_at 矛盾（声明时间不实）”。下方 X04/X05 已按此改写；四类计数与数据层未变。

| # | 严重度 | 位置 | 问题 | 建议 |
|---|---|---|---|---|
| X01 | high | `docs/_work/PREREG-M5-C2-REV7.md:15` | §0 归因表 N1 写 4 例，但只列 3 个 sid；冻结产物 false_by_reason 的 N1 归类是 3 例。总数 7 对，分解错。 | 把「4」改为「3」；若想保留“4 处”请明确口径为“R1 命中数 5（含 N2 2 处）/ N1 句 3 例”。（REV7.1 已于 21:06:55 冻结版改为 3；本更只需改 REV7 或在 REV7 头注加 supersede→REV7.1。） |
| X02 | high | `docs/_work/PREREG-M5-C2-REV7.md:17` | §0 写 N3「2（与上重叠 1 例）」，实际两例（s07/s09）与 N2 无重叠、且各自均为独立句。 | 删去「与上重叠 1 例」，改为「2（与 N1/N2 无重叠）」。（REV7.1 冻结版已改为「N3 未修好，仍为 FP」。） |
| X03 | high | `docs/_work/PREREG-M5-C2-B5.md:6` | B5 引用 (b4) 原题面为 e9a88fda，当前 B4 = f30d89e30262b148（10,910 B）；REV6 对同一文件引的是 f30d89e3。e9a88fda 在全树/git 全部 blob/截断变体中均无匹配。 | 改为 `PREREG-M5-C2-B4.md f30d89e30262b148`（或 `f30d89e3`）。 |
| X04 | high | `docs/_work/PREREG-M5-C2-REV7.md:7` | REV7 把 (b5) 钉成 e306ce994d306a84，但该值只等于「B5 去掉 §9 并 rstrip」的 11,388 B 早期版本；B5 于 19:54:15 写入 §9、19:55 冻结，冻结版 = d6c7bdac73ef7326 / 14,597 B（含 §9）。REV7 20:15 冻结时引用已过期（stale-at-freeze）。 | 把 REV7 的 (b5) 重钉为冻结版 d6c7bdac73ef7326 / 14,597 B；或明确注释“引的是 19:53 早期草稿、已被 19:55 冻结版取代”。冻结前须重跑 pin 校验。 |
| X05 | high | `docs/_work/PREREG-M5-C2-B5.md:143` | §9 标题自称 `2026-10-26T20:20+08:00`，但 B5 mtime=19:54:15、frozen_at=19:55、`full@5574253` 的 blob 含 §9（commit 19:59:10）⇒ **§9 在冻结前已写入**，标题时间不实；REV7 因起草早（19:53）而引用了无 §9 的 e306ce，属 stale-at-freeze。 | 把 §9 标题时间改真（写入 19:54:15，与 frozen_at 一致）或删掉该时间戳；在头注同时列出“冻结版 d6c7bdac / 14,597 B（含 §9）”与“REV7 引用的早期版本 e306ce / 11,388 B”；不要把 §9 写成“冻结后追加”。 |
| X06 | high | `docs/_work/PREREG-M5-C2-REV7.md:49` | REV7 §2（冻结）要求 `患者` 必判 valid=false，但按同件 N3 字面定义（子串命中 ⇒ valid=true）不可满足：患者在句首「患者：」逐字存在。产物 A2/A3 已 pass=false。 | REV7 头注加一行「A2/A3 断言不可满足，已由 PREREG-M5-C2-REV7.1 撤回并真值化」；或直接以 REV7.1 取代 REV7 的 §2 断言段。 |
| X07 | medium | `docs/_work/PREREG-M5-C2-REV7.1.md:160` | REV7.1 已 frozen=true@21:06:55、重跑产物 M5C2-REV7-1-OFFLINE.json 也已落盘（55191eaf / 510,508 B），但 §6 状态行仍写 executed=false ⇒ 状态字段与事实不符。 | 把 executed 改为 true，并把产物 sha16（55191eaf2426f736）写进 REV7.1 的钉哈希行；这是账本里唯一“状态字段落后于产物”的点。 |
| X08 | medium | `kvmem/m2_visibility/m5/out/M5B4-RATES.md:4` | RATES.md 与 AB.md 把金标钉成 9054479b / 10,208 B，但现文件是 9273ebc9 / 13,195 B（19:00 audit_fix 后）。旧版字节未保留，全树与 git 全部 blob 均无。 | 改成双坐标：`分析时点金标 = 9054479b / 10,208 B（历史，字节未留）`；`现行金标 = 9273ebc9 / 13,195 B`，并注明 gold 值未变、读数不受影响。 |
| X09 | medium | `docs/_work/INSPECTOR-M5C2-REV7.md:40` | 把 M5B4-JUDGE.json 写成「452456 B / 261 行」，实际 261 是句数，文件是 17,040 行（pretty-print JSON）。 | 改为「452,456 B / 261 句（JSON 17,040 行）」。 |
| X10 | medium | `docs/_work/PREREG-M5-C2-REV4.md:11` | 「31/31 全 A」的数值可复算，但出处引的是 M5C2-FLOOR-ARTIFACT.json（15 例的另一件）+ AMEND（否定该 31/31）；真正的 31 例在 M5C2-FLOOR-GBNF-EXPLORATORY.json，且该文件从未被标 sha16。 | 补一行出处：`M5C2-FLOOR-GBNF-EXPLORATORY.json <sha16> / 31 例`，并把 ARTIFACT+AMEND 标为“否定该 31/31 的更正链”。 |
| X11 | medium | `docs/_work/PREREG-M5-C2-B5.md:130` | §8.1 两行「全 0」按字面（本文件计数）为假：租车/物业各 1 次、5 个专名各 1 次，均因本行名单本身；按 §1 题面口径才是 0。 | 把口径写死为「§1 题面内出现次数 = 0（本表行名提及不计）」，避免字面自破。 |
| X12 | medium | `docs/_work/PREREG-M5-C2-B6.md:0` | B5 §9.5 要求 (b6) 在 (b5) 开跑前“出题并冻结”。B6 在本账本审计期内先以草稿出现（21:07，期间自钉口径不可复算），21:16:37 由 LEAD 冻结（frozen=true）并改为零自指可复算设计 ⇒ 该条现已满足；仅作为“审计期内变动”留痕。 | 已按要求冻结（21:16:37）；建议把冻结版 md sha16（ac27d47d3a3efff9）与 json sha16（23588ec099ca9255）写进冻结记录/回报，并在 §8 固定“冻结后不再编辑”。 |
| X13 | low | `docs/_work/PREREG-M5-C2-R2.md:48` | 引用的文件名 M5C-36-r1-adj.json / M5C-36-r1-alignment.json 不存在；哈希与字节（60,432 / 245,640）实际对应 M5C-36-adj.json / M5C-36-alignment.json。 | 把两处文件名去掉 `-r1`。 |
| X14 | low | `README.md:70` | `6f26bce0`（M2-ACCEPT-lead.md 已签坐标）在全树与全部 git blob 中均无对应字节，无法复算；README/INDEX 已与“现场 21ec668d”并列，属澄清写法但易被当成现行锚。 | 标注「历史签署坐标，字节未保留（unverifiable），按 ANCHORS-CURRENT #5 处置」。 |
| X15 | medium | `docs/_work/PREREG-M5-C2-REV7.1.md:160` | REV7.1 §6 状态行 executed=false 与已落盘的重跑产物冲突（同 X07，此处单列以便跟踪）。 | 状态行改 executed=true + 钉产物 sha16。 |
| X16 | medium | `docs/_work/PREREG-M5-C2-B6.md:4` | B6 是审计期内新建的活文件（21:07 草稿 → 21:16:37 冻结，期间至少 5 个版本）。md 自钉值 920333f2→9c256c16→037a57a6 一路变化，21:07 版按它自己的“剔除互引行”口径根本不可复算；最终采用零自指设计（json.prereg_sha16 = md 全文件哈希）后已可复算。教训：冻结前多版本迭代必须每次重钉，冻结时留痕 md sha16。 | 冻结时：① 一次性定稿；② json.prereg_sha16 重算并写入；③ 把 md sha16（ac27d47d3a3efff9）、json sha16（23588ec099ca9255）、字节、mtime 四元组写进 §8 与任务回报；④ 冻结后不得再编辑。 |

### 4.1 证据补充（供改稿直接引用）

- **X01**：M5C2-REV7-OFFLINE.false_by_reason: N1=3（b4-s1-q2-s01/s15、b4-s1-q3-s03）、N2=2、N3=2，7 例互不重叠；JUDGE 中 R1 value_mismatch=5（3 标点型 + 2 实体贪心型）
- **X02**：false_by_reason attribution: b4-s1-q2-s07=N3、b4-s1-q2-s09=N3，与 N2 的 b4-s2-q1-s01 / b4-s8-q2-s02 无交集
- **X03**：sha256(B4)=f30d89e30262b148；归档草稿=6f41f3d6（7,823 B，也不是 e9a88fda）；git rev-list --all --objects 仅 1 个 B4 blob=1982d167→f30d89e3
- **X04**：sha256(B5[:idx("## 9 LEAD 追加")].rstrip())=e306ce994d306a84 / 11,388 B；raw 截断 11,390 B 的哈希是 9c09ceaf；sha256(B5 全文)=d6c7bdac73ef7326；`git cat-file -p full:…-B5.md` 同为 d6c7bdac / 14,597 B 且含 §9（full commit 19:59:10）
- **X05**：B5 mtime=2026-10-26T19:54:15（早于 frozen_at 19:55）；`git cat-file -p full:docs/_work/PREREG-M5-C2-B5.md`=d6c7bdac / 14,597 B 且含 §9，full commit 19:59:10 ⇒ **§9 早于冻结**；§9 标题自写 20:20 与 mtime/frozen_at 矛盾（声明时间不实）；REV7 19:53 起草、20:15 冻结仍引 e306ce（无 §9）= stale-at-freeze
- **X06**：M5C2-REV7-OFFLINE.assertions.A2.pass=false / A3.pass=false；A2 occurrence: item_in_sentence=true, matcher_hit=substring, valid=true, coverage=1.0
- **X07**：产物 21:07:27 落盘，gate 与 rev7 逐项相同（2/46、4/41、1/261、0/35）；产物 diff 仅 provenance/schema/inputs/assertions
- **X08**：sha256(M5B4-LEAD-RULING.json)=9273ebc97aa1413a / 13,195 B；RATES/AB 的 261 条 gold 与现文件逐 sid 相同（0 差异）⇒ 数值等价
- **X09**：wc -l = 17,040；bytes=452,456 与 sha 6a3001b6 均对
- **X10**：EXPLORATORY: n=31, arm_rate arm1..5 A=6/6,6/6,6/6,6/6,7/7 → 31/31；FLOOR-ARTIFACT: n=15, position_bias=false；AMEND: position_bias=true, prior_gbnf_all_A_invalidated=true
- **X11**：全文 count: 仁和口腔=1/迅达租车=1/华庭物业=1/北方联通=1/力量方舟=1；租车=1/物业=1；§1 段内全部=0
- **X12**：21:07 版自钉 920333f2 按自身口径不可复算（实得 31804f44）；21:16:37 冻结版：md ac27d47d3a3efff9 / 17,374 B，json.prereg_sha16=ac27d47d3a3efff9（一致，可复算）
- **X13**：磁盘只有 M5C-36-adj.json (0d882f20/60,432) 与 M5C-36-alignment.json (aaed0822/245,640)
- **X14**：全 1491 个 git blob 扫描无 6f26bce0；现文件 21ec668d/10,479 B
- **X15**：M5C2-REV7-1-OFFLINE.json 55191eaf / 510,508 B / 2026-10-26T21:07:27+08:00
- **X16**：本账本快照：md ac27d47d3a3efff9 / 17,374 B；json.prereg_sha16=ac27d47d3a3efff9；json 23588ec099ca9255（一致，见 N42）

## 5 哪些引用可信 / 哪些过期 / 哪些无法验证

**可信（可直接引）**：全部核心读数引用的产物哈希 —— `M5B4-JUDGE.json 6a3001b6`、`M5B4-LEAD-RULING.json 9273ebc9`、`M5B4-RATES.json 783d423a`、`M5B4-SENTENCES.json c349ca5a`、`M5C2-REV7-OFFLINE.json 1f8f44b9`、`run_m5c2_rev7_offline.py 65ed6012`、`_rev7_audit.py 6695a4b4`、`M5C2-REV7-AUDIT.json de80cd38`、`PREREG-M5-C2-REV7.md 32eaf82c`、`PREREG-M5-C2-REV6.md faaf2605`、`PREREG-M5-B2.md 482a9482`、`PREREG-M5-C2-B4.md f30d89e3`、`JUDGE-ROBUSTNESS-SPEC.md 5ad46f8e`、`M5B2-LEAD-RULING.json 65a2124b`、`m5_ground_v2_3.py cc03e48c`、`tools/kvshim_vk.dll 9edbafa1`、prompt `a6bc4f26`。

**过期（需改）**：`REV7:7 → e306ce`（应双坐标）；`B5:6 / B6:6 → e9a88fda`（应 f30d89e3，无对应可复原）；`RATES.md:4 / AB.md:5 → 9054479b`（历史坐标，需标时点、值等价）。**名字错但哈希能唯一定位**：`R2:48,93` 的 `M5C-36-r1-*.json`（真实文件名无 `-r1-`，按哈希匹配到 `M5C-36-*.json`，判 match 并注 filename_mismatch）。

**无法验证（如实标注，不是“错”）**：`6f26bce0`（M2 已签历史坐标，字节未留）；INSPECTOR 的“两次重跑同字节”（本次未复跑，按纪律不执行执行者脚本）。**注**：`REV7.1` 的“实测四门槛”与 B5 §9.5 的 (b6) 在审计期内已落地（产物 `55191eaf`；B6 `ac27d47d` frozen=true@21:16:37），不再是缺口，见 N35/N37。

## 6 复算命令（任何人可重跑）

```bash
# 单文件锚（项目约定：工作区原始字节，不归一换行）
python -X utf8 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest()[:16])" <path>

# REV7 的 (b5) 引用为何是 e306ce：去掉 §9 再 rstrip
python -X utf8 -c "import hashlib;b=open('docs/_work/PREREG-M5-C2-B5.md','rb').read();i=b.find('## 9 LEAD 追加'.encode());v=b[:i].rstrip();print(hashlib.sha256(v).hexdigest()[:16], len(v))"   # e306ce994d306a84 11388

# 金标四态 + 基线两率（从产物复算，不看文档转述）
python -X utf8 -c "import json,collections;g=json.load(open('kvmem/m2_visibility/m5/out/M5B4-LEAD-RULING.json',encoding='utf-8'))['gold'];print(collections.Counter(g.values()))"

# 全部 git blob 的 sha16 扫描（用于证明 e9a88fda / 9054479b / 6f26bce0 从没被提交过）
git cat-file --batch-all-objects --batch-check | awk '$2=="blob"{print $1}' | while read o; do git cat-file -p $o | python -X utf8 -c "import sys,hashlib;print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest()[:16],sys.argv[1])" $o; done | grep -E "e9a88fda|9054479b|6f26bce0"
```

## 7 审计纪律声明

- 只读：未修改/未删除任何被审文件；只写了本文件与 `M5C2-DOC-HASH-LEDGER.json` 两份交付物。
- 未 git 提交；未跑任何 GPU/模型/网络；未读 (b5) 运行数据（(b5) 尚未跑）。
- 审计期内两份文件在被实时修订，本账本记录的是**一次性快照**：`PREREG-M5-C2-REV7.1.md` = `09d6f1b163ea0b84` / 16,313 B @2026-10-26T21:07:03+08:00（已 frozen=true@21:06:55）；`PREREG-M5-C2-B6.md` = `ac27d47d3a3efff9` / 17,374 B @2026-10-26T21:16:37+08:00（已 frozen=true@21:16:37）。build 完成后已复核无漂移；若之后任一文件再变，需重跑本脚本。
