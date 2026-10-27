# M5C2 证据链复现审计：已提交的代码，能不能复现已提交的证据数字？

- 审计任务：共享任务板 `task-8`（执行者 `chain-repro`）
- 审计对象：`main@96eeefc`（本地、未推送；`origin/main=8008064`）里**已提交**的 M5C2 CPU 生成脚本与 `kvmem/m2_visibility/m5/out/*.json` 证据
- 机器可读明细：`kvmem/m2_visibility/m5/out/M5C2-EVIDENCE-CHAIN-REPRO.json`
- 干净副本（仓库外）：`D:\m5c2-chain-repro-20261026-210154\`（`_src` 原始件、`runs\E*` 每次运行、`logs\E*.log` 原始 stdout/stderr、`_harness\results.json`）
- 纪律：**零 GPU / 零模型 / 零联网**；**从未在 `D:\llama-mem` 内执行任何生成脚本**（只在副本运行，产物不回写）；未改动/未提交仓库既有文件；只写本文件与上述 JSON。

---

## 0. 结论摘要（先看这一段）

| 分类 | 数量 | 具体项 |
|---|---:|---|
| **byte 级可复现（原样，仅替换 ROOT 常量）** | 3 | `make_m5c2_rev6_design_readout.py`、`make_m5b2_rates.py`、`make_m5b3_v24_rates.py` |
| **byte 级可复现（仅更新过期金标常量后）** | 2 | `make_m5b4_rates.py`、`make_m5b4_ab.py` —— 产物除**唯一金标 sha 留痕字段**外**逐字节全同** |
| **数据级可复现（byte 差异仅内嵌绝对路径）** | 2 | `make_m5b2_judge.py`、`make_m5b_judge.py` |
| **失败** | 0 | 未发现“逻辑对不上”的失败项 |
| **未做：需 GPU/模型（import 链触碰 `_e3gpu_run`/engine）** | 7 组 | `run_m5c2_rev5_offline.py`、`run_m5c2_rev5_1_offline.py`、`run_m5c2_rev7_offline.py` + 4 组 GPU 生成器 |
| **真·数值与代码不自洽** | **0** | 本任务未发现 |
| **常量过期造成的“假不一致”** | 4 处 | 2 个产物字段 + 2 个脚本常量（金标 sha/长度） |
| **其他证据链缺陷** | 3 | 首版金标不可恢复；文档与 JSON 分居两个分支；judge 产物内嵌绝对路径 |

一句话：**已提交的代码能复现已提交的核心读数**（4/41=9.76%、7/46=15.22%、14/35、10/71、rev6 design 读数等），
但 “b4 金标件” 在**脚本常量、产物留痕、文档抬头三处仍写着被替换掉的首版 sha**，导致按原样运行会 **exit 1**；
把该常量更新为当前真值后，数值**逐字段一致、逐 sid 标签一致**——**是留痕过期，不是数字造假，也不是逻辑对不上**。

---

## 1. 装置与方法（保证“干净”）

1. **干净副本**：`D:\m5c2-chain-repro-20261026-210154\_src\`，逐文件用 `git cat-file -p 96eeefc:<path>` 取**已提交 blob**写入并校验 sha256（共 32 个文件；清单与 sha16 见 JSON `clean_copy.files`）。
2. **两处例外**：`docs/_work/PREREG-M5-B2.md`、`PREREG-M5-B3-v2.4.md` 在 `main` **未入库**，取自磁盘，并与 `full@5574253` 的 blob **逐字节相同**（sha16 `482a94820917d16e`、`37e3742c0e4056ef`）。
3. **最小改动**：CPU 脚本里硬编码 `ROOT = Path(r"D:\llama-mem")`，副本内**只**替换该行为副本根（diff 见 JSON `patch_diff`）；数值实验**只**改过期金标常量（sha16 + 字节数），不动任何逻辑。
4. **运行**：`python -X utf8 <副本脚本>`，`cwd=副本根`；捕获 exit code / stdout / stderr；产物与 `_src` 中已提交件比 sha256，不同则做 JSON 字段级 diff。
5. **产物写入副本**，仓库中证据文件零改动（审计结束时 `git status` 无任何 tracked 修改）。

---

## 2. 逐脚本结果

| # | 脚本（已提交） | CPU-only | 已提交常量 vs 当前输入 | 运行结果 | 产物 sha16（期望 → 实际） | 结论 |
|---|---|---|---|---|---|---|
| E1/E2 | `make_m5b4_rates.py` | ✅ 纯 stdlib | ❌ `GOLD_SHA16=9054…`/`len=10208` 过期（当前 `9273…`/`13195`） | E1 **exit 1**；E2（仅改常量）exit 0 | `783d423a39db02e3` → **`dea992869cebd7a2`**（121993 B 同长，**1 字段差**） | **可复现**（除 `gold_sha16` 留痕字段） |
| E3/E4 | `make_m5b4_ab.py` | ✅（`m5_ground_v2_3` 为纯规则 sqlite/stdlib） | ❌ 同一过期金标常量 | E3 **exit 1**；E4（仅改常量）exit 0 | `0ff84d2617ab8b99` → **`4a875b92728842d4`**（68603 B 同长，**1 字段差**） | **可复现**（除 `same_gold` 留痕字段） |
| E5 | `make_m5c2_rev6_design_readout.py` | ✅ 纯 stdlib | ✅（设计上不校验金标 sha，改为逐 sid 比值） | exit 0 | `5c7812ce27fb0090` → **`5c7812ce27fb0090`** | **byte 级可复现** |
| E6 | `make_m5b3_v24_rates.py` | ✅ 纯 stdlib | ✅ 5 项 EXPECT 全匹配 | exit 0 | `3d5f5907e1e4e869` → **`3d5f5907e1e4e869`** | **byte 级可复现** |
| E7 | `make_m5b2_rates.py` | ✅ 纯 stdlib | ✅ 5 项 EXPECT 全匹配 | exit 0 | `9ac66b6dfaf8f804` → **`9ac66b6dfaf8f804`** | **byte 级可复现** |
| E8 | `make_m5b2_judge.py`（附加） | ✅（冻结规则 `m5_ground_v2_3.py`） | ✅ `cc03…`/44209 | exit 0 | `5deead7180dbb6a8`(229930 B) → `b5ebe7db43c9a047`(230018 B) | **数据级可复现**（仅 2 个内嵌绝对路径字段差 88 B） |
| E9 | `make_m5b_judge.py`（附加） | ✅ 同上 | ✅ | exit 0 | `7acb93fd5373479f`(80628 B) → `4133adbd0d9ca405`(80714 B) | **数据级可复现**（仅 2 个内嵌路径字段差 86 B） |

### 2.1 E1：已提交代码按原样运行 → 拒绝

```
$ python -X utf8 ...\runs\E1...\kvmem\m2_visibility\m5\make_m5b4_rates.py
exit=1   stderr: M5B4-LEAD-RULING changed
```
（`make_m5b4_rates.py:75-76`：`sha16(gb) != GOLD_SHA16 or len(gb) != 10208` 同时触发；E3 报 `GOLD changed`，`make_m5b4_ab.py:170`。）

### 2.2 E2：**仅**更新金标常量 → 数值全同

补丁仅两行（副本内，diff 留存）：
```diff
-GOLD_SHA16 = "9054479b32b79eb1"
+GOLD_SHA16 = "9273ebc97aa1413a"
-    if sha16(gb) != GOLD_SHA16 or len(gb) != 10208:
+    if sha16(gb) != GOLD_SHA16 or len(gb) != 13195:
```
结果：`exit=0`，产物 121993 B（与已提交同长），字段级 diff **仅 1 项**：
```
.gold_sha16: expected "9054479b32b79eb1"  actual "9273ebc97aa1413a"
```
其余 260 条 rows、rates、question_level、abstain、sensitivity、coverage、b4_s2、thresholds **全部相同**。

### 2.3 E4：AB 产物同理（旧 v2.3 臂在 CPU 上逐句重算也一致）

仅 `GOLD_SHA/len` 两处补丁；`exit=0`，68603 B 同长，字段级 diff **仅 1 项**：
```
.same_gold: expected "9054479b32b79eb1"  actual "9273ebc97aa1413a"
```
即 `rates_b4_same_definition`（v2.3 3/41、rev5.1 4/41；v2.3 11/46、rev5.1 7/46）、legacy 口径、题级、deltas、McNemar/配对 bootstrap 全部复现。

### 2.4 E5/E6/E7：**byte 级**全同

- E5 `M5C2-REV6-B4DESIGN-READOUT.json` `5c7812ce27fb0090` / 19866 B —— 全同。该脚本有**抗 stale 设计**：不校验金标 sha，而是把当前 gold 与 `M5B4-RATES.json` 的逐 sid gold 快照比较（`gold_values_unchanged_vs_M5B4-RATES=true`），因此过期常量不影响它。
- E6 `M5B3-v24-RATES.json` `3d5f5907e1e4e869` / 12830 B —— 全同（14/35、10/71、undecidable 重标等全部一致）。
- E7 `M5B2-RATES.json` `9ac66b6dfaf8f804` / 11407 B —— 全同（14/35=40.00%、10/71=14.08%）。

### 2.5 E8/E9：数据全同，byte 差仅“产物内嵌绝对路径”

字段级 diff 只有两项：`.gen.path`、`.judge.path`（已提交件写死 `D:\llama-mem\…`）。所有 verdict/句子/计数/哈希字段一致 ⇒ 判据产物**内容可复现**，但**离开原路径就不可能 byte 级复现**（见 §10 建议）。

---

## 3. 专项：b4 的 4/41、7/46 在当前金标下是否成立？逐 sid 证明

### 3.1 事实链

| 项 | 值 |
|---|---|
| 脚本常量 `GOLD_SHA16` | `9054479b32b79eb1`（首版） |
| 产物 `M5B4-RATES.json.gold_sha16` | `9054479b32b79eb1`（首版） |
| 产物 `M5B4-AB-OLD-VS-NEW.json.same_gold` | `9054479b32b79eb1`（首版） |
| **当前已提交金标** `out/M5B4-LEAD-RULING.json` | **`9273ebc97aa1413a` / 13195 B** |
| 首版金标是否还能找到 | **否**（见 3.3） |
| 当前金标 `audit_fix` | `gold_changed=false`（修版只补 11/19→19/19 条 `ruled` 留痕，值未变） |

### 3.2 独立重算（不依赖任何脚本产物里的旧标签）

用**已提交 `M5B4-JUDGE.json` + 当前 `M5B4-LEAD-RULING.json`** 直接重算：

| 指标 | 重算值 | 产物记录 | 一致 |
|---|---|---|---|
| 漏判 leak（fabricated ∧ ∈{supported,undecidable}） | **4 / 41 = 0.097561** | 4/41 | ✅ |
| 误判 false（support_present ∧ unsupported） | **7 / 46 = 0.152174** | 7/46 | ✅ |
| strict_leak（fabricated ∧ supported） | 4/41 | 4/41 | ✅ |
| any_non_supported_false | 13/46 | 13/46 | ✅ |
| parse_fail | 1/261 | 1/261 | ✅ |
| gold_counts | `{support_present:46, fabricated:41, no_fact:164, undecidable:10}` | 同 | ✅ |
| 题级 leak / false | 2/10、4/24 | 同 | ✅ |
| abstain 路由 | 15 句 | 15 | ✅ |

**逐 sid 金标标签一致性**（证明不是“数字碰巧相等”）：
- 把 `M5B4-RATES.json.rows[].gold`（该产物生成于**首版金标**时代）与**当前** `M5B4-LEAD-RULING.json.gold` 做逐 sid 比较：
  **261 个 sid，差异 0 个**（`per_sid_gold_diff_n = 0`）。
- 漏判分子 sid 集合：重算 = `["b4-s2-q2-s01","b4-s3-q4-s03","b4-s3-q4-s11","b4-s3-q4-s12"]` = 产物 rows，逐项相同。
- 误判分子 sid 集合：重算 7 项 = 产物 rows，逐项相同。
⇒ 首版与当前金标在 **gold 值层面完全相同**，因此 4/41、7/46 在**当前金标**下成立，而不仅是“在脚本假设下成立”。

### 3.3 但：首版金标文件本身不可复核（真实证据链缺口）

命令（在 `D:\llama-mem` 内只读）：
```bash
git cat-file --batch-all-objects --batch-check   # 2963 objects / 1491 blobs
# 按要求 size==10208 过滤 → 0 个 blob
# 全 blob sha256 前缀 9054479b 扫描 → 0 命中
git log --all --format=%H -- kvmem/m2_visibility/m5/out/M5B4-LEAD-RULING.json
# → 唯一提交 01dc0cc4，内容 sha16=9273ebc97aa1413a / 13195 B
```
结论：**首版金标 `9054479b32b79eb1/10,208 B` 已不在 git、也不在磁盘**（`docs/_work/ARTIFACTS-KEY.md` 亦自认“已被本版替换、磁盘不再单独存在”）。
所以“**两版 gold 完全相同**”这句结论**无法用旧文件逐字节证明**；只能像本审计这样，用 `RATES.rows` 逐 sid 标签 + 当前金标比对（261/261 一致）间接证明。
**数值不受影响；但“可回溯复核”不成立。**

---

## 4. 产物内部 `prereg/judge/gold/prompt/code` sha16 与当前文件对照

> 当前值 = 工作树文件（并已确认 `main` 已提交 blob 与磁盘一致；`docs/*` 以 `full@5574253` 为准）。

| 产物 | 字段 | 记录值 | 当前对应文件值 | 结论 |
|---|---|---|---|---|
| `M5B4-RATES.json` | `prereg_sha16` | `f30d89e30262b148` | `PREREG-M5-C2-B4.md` = 同 | ✅ |
| | `judge_sha16` | `6a3001b6ca23ef7d` | `M5B4-JUDGE.json` = 同 | ✅ |
| | `gold_sha16` | `9054479b32b79eb1` | `M5B4-LEAD-RULING.json` = `9273ebc97aa1413a` | ❌ **过期（首版）** |
| `M5B4-AB-OLD-VS-NEW.json` | `same_gold` | `9054479b32b79eb1` | 同上 | ❌ **过期（首版）** |
| | `old_judge.sha16` | `cc03e48c360ae0ee` / 44209 | `m5_ground_v2_3.py` = 同 | ✅ |
| | `new_judge.judge_sha16` | `6a3001b6ca23ef7d` | `M5B4-JUDGE.json` = 同 | ✅ |
| | `new_judge.prompt_sha16` | `a6bc4f268f7711de` | `REV4_TEMPLATE`（AST 提取）= 同 | ✅ |
| `M5B4-JUDGE.json` | `prereg_sha16` / `sentences_sha16` / `prompt_sha16` / `actual_prompt_sha16` | `f30d89…` / `c349ca…` / `a6bc4f…` / `a6bc4f…` | 全部 = 同 | ✅ |
| `M5B4-LEAD-RULING.json` | `prereg_sha16` | `f30d89e30262b148` | 同 | ✅ |
| `M5B2-RATES.json` | `inputs.*`（5 项） | `65a2…/6529…/b085…/1dfb…/5dee…` | 全部 = 同 | ✅ |
| | `prereg.sha16` | `482a94820917d16e` | `PREREG-M5-B2.md` = 同 | ✅ |
| `M5B3-v24-RATES.json` | `inputs.*`（5 项） | `65a2…/6529…/b085…/5dee…/9ac6…` | 全部 = 同 | ✅ |
| | `prereg.sha16` / `v24_impl.sha16` / `v24_selftest.sha16` | `37e3742c0e4056ef` / `1387b851450bde44` / `08e6e92c715fec58` | 全部 = 同 | ✅ |
| `M5C2-REV6-B4DESIGN-READOUT.json` | `b4_judge_sha16` / `gold_sha16_current` | `6a30…` / `9273…` | = 同（当前金标） | ✅ |
| | `gold_sha16_original` | `9054479b32b79eb1` | 历史留痕（文件已不存在） | ⚠️ 说明性字段 |
| | `rev6_prompt_sha16` | `162f680de2f5812e` | `REV6_TEMPLATE`（AST 提取）= 同 | ✅ |
| `M5C2-REV5-OFFLINE.json` | `prereg.sha16` / `b2_input.sha16` / `prompt_sha16` | `81a5…` / `553a…` / `a6bc…` | 全部 = 同 | ✅（脚本未复跑） |
| `M5C2-REV5-1-OFFLINE.json` | `b2_input` / `rev5_input` / `prompt_sha16` | `553a…` / `f304…` / `a6bc…` | 全部 = 同 | ✅（脚本未复跑） |
| `M5C2-REV7-OFFLINE.json` | `prereg_sha16` / `items_source_sha16` / `gold_sha16_current` / `prompt_sha16` / `code_sha16` | `32ea…` / `6a30…` / `9273…` / `a6bc…` / `65ed60125528d5d6` | 全部 = 同（`code_sha16` = 当前 `run_m5c2_rev7_offline.py`） | ✅（脚本未复跑） |
| `M5B2-JUDGE.json` / `M5B-JUDGE.json` | `judge.sha16` / `gen.sha16` | `cc03…` / `d8fd814958699336`、`e74ee1951aa41c31` | 全部 = 同 | ✅ |
| `M5B4-GEN.json` | `prereg.sha16` / `frozen_dll_sha16` / `prompt_template_sha16` | `f30d89…` / `9edbafa150700614` / `96ab1c08d6b1b21f` | `PREREG-M5-C2-B4.md` / `tools/kvshim_vk.dll`（50,007,552 B）/ `TURN_TEMPLATE` 全部 = 同 | ✅ |

**不符项合计 2 个字段**（`M5B4-RATES.gold_sha16`、`M5B4-AB-OLD-VS-NEW.same_gold`），根因同一：首版金标被替换而留痕未回填。
（`M5C2-REV6-B4DESIGN-READOUT.gold_sha16_original` 是**有意的历史字段**，不算不符。）

---

## 5. 未做项（需 GPU/模型，按纪律绝不运行）

| 脚本 | 试图产物 | 阻断点（import 链） |
|---|---|---|
| `run_m5c2_rev5_offline.py` | `M5C2-REV5-OFFLINE.json` | `:21 import run_m5c2_rev4_1` → `run_m5c2_rev4_1.py:31 import _e3gpu_run as E`，`:28` 追加 `engine/`；`_e3gpu_run.py` 顶部持 14B gguf（8.99 GB）与 `kvshim_vk.dll` |
| `run_m5c2_rev5_1_offline.py` | `M5C2-REV5-1-OFFLINE.json` | `:22 import run_m5c2_rev5_offline` → 同一链路 |
| `run_m5c2_rev7_offline.py` | `M5C2-REV7-OFFLINE.json` | `:53-54 import run_m5c2_rev5_offline / rev5_1_offline` → 同一链路（rev7 复现由 rev7-impl / rev7-auditor / cleanroom-auditor 任务承担） |
| `run_m5c2_b4_gen.py`、`run_m5c2_b4_judge.py` | `M5B4-GEN.json`、`M5B4-SENTENCES.json`、`M5B4-JUDGE.json` | 直连 `_e3gpu_run`/engine + llama DLL |
| `run_m5c2_b2eval.py` | `M5C2-B2EVAL.json` | `:27 import _e3gpu_run as E` |
| `run_m5c2_rev4.py / rev4_1 / rev2_order / floor* / r2 / rev6_b4design / run_m5_b_v2 / run_m5_b2_v2 / run_m5_c_v2` | REV4/ORDER/FLOOR/REV6 等 | 均 import `_e3gpu_run` 或 engine/llama DLL、加载模型 |
| 所有 GEN 级数字（模型实际输出） | — | 物理上需 GPU+14B 模型；离线只能核对冻结依赖（本审计已核：DLL `9edbafa150700614`、prompt `a6bc…`/`162f…`/`96ab…`、prereg 均匹配） |

> 注意：`rev5/rev5.1/rev7 offline` **脚本自身逻辑是纯 CPU**，只是复用了 GPU 运行器模块里的正则/常量；若要彻底解决，应把共享常量抽到无 GPU 依赖的 `*_common.py` 再复跑（建议项，非本次改动）。

---

## 6. 文档数字 → 代码支撑对照

| 文档（及其数字） | 代码路径 | 支撑结论 |
|---|---|---|
| `out/M5B4-RATES.md` + `PROGRESS-AND-ROADMAP.md §13.32`：(b4) 留 4/41=**9.76%**（CI 3.86–22.55）、误 7/46=**15.22%**（CI 7.57–28.22）、题级 2/10、4/24、parse_fail 1/261、`pass=false` | `M5B4-JUDGE`+当前金标 → `make_m5b4_rates.py`（E2） | ✅ **有代码支撑**（更新过期常量后逐字段同）；⚠️ 文档抬头引用的金标 sha 是首版 |
| `out/M5B4-AB-OLD-VS-NEW.md`：v2.3 **3/41**→rev5.1 **4/41**（+2.44pp）、**11/46**→**7/46**（−8.70pp）、CI 重叠、Δ 不显著、McNemar | `make_m5b4_ab.py` + 冻结 `m5_ground_v2_3.py`（E4） | ✅ **有代码支撑**（除 `same_gold` 全同；旧臂逐句重算一致） |
| `out/M5B2-RATES.md`、`PROGRESS §13.30`：(b2) 14/35=**40.00%**、10/71=**14.08%**、`four_state=未通过` | `make_m5b2_rates.py`（E7） | ✅ **byte 级可复现** |
| `out/M5B3-v24-RATES.md`、`PROGRESS §13.31`：v2.4 仍 14/35、10/71；只把 `no_a_component` 重标 undecidable；未通过 | `make_m5b3_v24_rates.py`（E6） | ✅ **byte 级可复现** |
| `out/M5C2-REV6-B4DESIGN.md` / `-READOUT.json`：parse_fail **3/261**、false **4/46**、leak **6/41**、r4_fab **0**、verbatim **−7.57pp**、gate 三阈值过（design_set 非验收） | `make_m5c2_rev6_design_readout.py`（E5） | ✅ **byte 级可复现** |
| `M5B2-JUDGE.json` / `M5B-JUDGE.json`（判据读数上游） | `make_m5b2_judge.py`（E8）/ `make_m5b_judge.py`（E9） | ✅ 数据级可复现（byte 差仅内嵌绝对路径） |
| `M5C2-REV5-OFFLINE` / `REV5-1-OFFLINE` 及文档数字 | `run_m5c2_*_offline.py` | ⚠️ **本次未复现**（import 链触碰 GPU 运行器）；静态溯源 prereg/B2EVAL/prompt 全匹配 |
| `PROGRESS` C32 / rev7 段：误判 **2/46**、漏判 **4/41**、parse_fail **1/261**、新增漏判 **0** | `run_m5c2_rev7_offline.py` | ⚠️ **本任务未复现**（同一 import 链）；但其常量**已全部指向当前金标/当前代码**（`9273…`/`65ed6012…`/`32eaf82c…`），无 stale 问题；复现由 rev7 任务负责 |
| 所有 GEN 级数字（模型实际输出） | 需 GPU/模型 | ❌ **无离线代码支撑**（物理限制；冻结依赖已核对一致） |

---

## 7. 最关键的 3 个“文档数字对不上代码”的证据（带命令与 sha）

### 证据 1：b4 读数的**金标留痕**对不上当前金标（脚本会 exit 1）

```bash
sha256 前缀（16 位）:
  make_m5b4_rates.py:16   GOLD_SHA16 = "9054479b32b79eb1"   len 断言 10208
  out/M5B4-RATES.json     gold_sha16 = "9054479b32b79eb1"
  out/M5B4-LEAD-RULING.json 实际 = "9273ebc97aa1413a" / 13195 B
# 干净副本按原样运行：
$ python -X utf8 ...\make_m5b4_rates.py
exit=1  stderr: M5B4-LEAD-RULING changed
```
→ **文档/产物写的 sha 与当前金标文件不是同一个**；但更新该常量后读数逐字段全同（E2），故属**留痕过期**。

### 证据 2：首版金标**不可从 git 恢复**，但逐 sid 标签确实相同

```bash
git cat-file --batch-all-objects --batch-check   # 2963 objects
# size==10208 的 blob：0 个；sha256 前缀 9054479b：0 命中
git log --all --format=%H -- kvmem/m2_visibility/m5/out/M5B4-LEAD-RULING.json
# → 仅 01dc0cc4，blob sha16=9273ebc97aa1413a / 13195
# 逐 sid 比对（本审计结果）：RATES.rows[].gold（首版时代记录） vs 当前 gold →
#   261 sid，diff = 0
```
→ “两版 gold 完全相同”这句话**无法用旧文件验证**（旧文件不存在），只能由逐 sid 标签一致性间接证明；其数值结论成立。

### 证据 3：**文档与 JSON 证据不在同一分支/提交**

```bash
git ls-tree -r --name-only 96eeefc | grep -c '^docs/'      # → 0
git ls-tree -r --name-only 96eeefc | grep -c '\.md$'       # → 1（只有 README.md）
git ls-tree -r --name-only 5574253 | grep -c '\.md$'       # → 195（full 分支的文档）
git ls-tree -r --name-only 5574253 kvmem/m2_visibility/m5/out/ | grep -c '\.json$'  # → 0
```
→ `main@96eeefc`：代码 + m5/out 下 100 个 JSON、**0 份 docs**；`full@5574253`：195 份 md、**0 个 m5 JSON**。
**任何单一提交都无法同时检阅“文档结论 + 实证 JSON”**；`PREREG` 等预登记只存在于本地 `full` 分支（origin 上没有）。

---

## 8. 复跑方式（可复核）

```bash
# 审计副本（仓库外，含原始件/每次运行/原始日志）
D:\m5c2-chain-repro-20261026-210154\
  _src\          # 32 个已提交 blob（逐文件 sha256 校验）+ _harness/manifest.json
  runs\E1..E9\   # 每个实验的独立副本（只替换 ROOT / 过期常量，diff 见 results.json）
  logs\E*.log    # 每个实验的原始 stdout/stderr/exit
  _harness\results.json  # 机器可读结果（含 field_diffs、patch_diff）
# 重跑：
python -X utf8 "D:\m5c2-chain-repro-20261026-210154\_harness\run_all.py"
python -X utf8 "D:\m5c2-chain-repro-20261026-210154\_harness\build_deliverables.py"
```
（审计完成后 `git status` 无 tracked 修改；仓库内新增的只有本文件与 `out/M5C2-EVIDENCE-CHAIN-REPRO.json`。）

---

## 9. 残留风险与建议（不改本次结论）

1. **回填留痕**：把 `make_m5b4_rates.py/.make_m5b4_ab.py` 的 `GOLD_SHA16/长度` 与两个产物里的 `gold_sha16/same_gold` 更新为 `9273ebc97aa1413a/13195`，并注明“首版 9054…/10208 已被 audit_fix 版替换、gold 值逐 sid 未变”。否则任何人照 README/文档复跑都会先撞 exit 1。
2. **把首版金标入库存档**（若有备份）：或至少在 `ARTIFACTS-KEY` 里明确“该 sha 仅为历史留痕、文件不可得”，避免“可复核”错觉。当前文档已部分承认，但脚本/产物未同步。
3. **合并/同步 `full` 与 `main`**：文档与证据分居两分支，导致“结论 + 证据”无法在单一 commit 互校；预登记（PREREG）不在 origin。
4. **产物不要内嵌绝对路径**（`make_m5b*_judge.py`）：改用相对路径或只留 sha，否则离开 `D:\llama-mem` 永远无法 byte 级复现。
5. **离线复算脚本剥离 GPU import**：`run_m5c2_rev5_offline/rev5_1/rev7` 仅需 `_e3gpu_run` 里的正则/常量，建议抽 `*_common.py`，让“零 GPU 复算”名副其实、可被任何人在干净环境重跑。
6. **入库规则要当心**：`.gitignore` 第 62 行 `*.json`、第 180 行 `*.md`，现有 192 个 JSON 与 `full` 分支 195 个 md 都是 `git add -f` 强加跟踪；新增证据（含本审计 JSON）默认被忽略，容易漏提交。