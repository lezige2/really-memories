# L2 独立复核（inspector）

> **复核对象**：M2 完整 L2「`detach` 未命中记账一致性」补正后批次（task-27 四项补正；executor 自报通过）。
> **性质**：只读独立复核；**未改仓库任何代码/产物/库**，全部运行产物只落系统临时目录（`C:/Users/lezige/AppData/Local/Temp/m3l2/`）。
> **依据**：预登记 `docs/_work/M2-FULL-PREREG-draft.md` `c2afd97aad278ade` §2.2；task-26/27 派单 + L1 复核（`INSPECTOR-L1-REVIEW.md 66cf3aa5`）的 roll-forward 条件。
> **结论一句话**：**L2 零 GPU 判据层 = 通过（可签）**；链条 `pre 红 → after 绿 → variant_b 回红（H1 绿/U 红）`闭合；`drop_delta_on_unbooked` 把「先 drop 再 raise」在每个未命中的例上都堵死；`chat_lease.py`/`_test_lease.py` 未动；L1 11/11 不破；`freeze_check` FROZEN。**真机/产品路径重跑 = 未做**；另记 1 条事件留痕缺口（§6 Note）与 1 条解释性注记（rollback 变体）。
> **时间锚**：读数取 2026-10-25 **20:24–20:40**；sha16 全部二进制现算。

---

## §1 坐标（我现算，不引 lead 值当证据）

| 对象 | sha16 / bytes | 说明 |
|---|---|---|
| `m3_lease.py` | **`33ae679a50d58c93`** / 9,047 | L2 最终态（20:28:41） |
| `_before/m3_lease.py@675f983f8d02f1df` | `675f983f` / 7,526 | L2 真改前（20:24:16 落，**早于改码**） |
| `_before/m3_lease.py@37a0a6f4b8ea1154` | `37a0a6f4` / 8,701 | L2 主改动后 / docstring 补正前（20:28:36） |
| `_test_lease_detach.py` | **`4fc62f1b757bfc50`** / 12,775 | L2 构造床（主床 4 例 + 扩展 U4） |
| `_test_lease_overlap.py` | **`85279a5b6edc861d`** / 9,626 | L1 床（默认输出已改临时目录） |
| `_test_lease.py` | `d2ddc6b69249dab6` / 4,128 | 既有套件，未动 |
| `tools/chat_lease.py` | `619a043215035de7` / 19,274 | **未动**（含 `STRICT:47`/`:232-236`、reset 拒 `:320-326`） |
| `LANDED-l2.json` | **`467e0b3f31cd3ff2`** / 11,260 | 补正后台账（`supersedes.ledger_self_sha16=550faba2`，`addendum.original` 保留原读数） |
| `land_l2.py` / `land_l1.py` | `b4e0d0fbec427d7f` / 16,134；`52c2c6690384c38b` / 10,855 | 均已在台账 `tooling` |
| 产物 | `M3-L2-pre-v2 428f4cfe`、`after-v2 e68df9a4`、`variant-b b20a03d8`、`variant-rollback-v2 b5e73ae2`、`M3-L1-recheck-after-L2-v2 383516da` | 主批次首次产物（`5d2f864b`/`2294b3ad`/`0658aa48`/`1e31f28a`）保留在台账 `addendum.original` |

**改动范围（我 diff `675f983f→33ae679a`）**：仅 2 处 —— ① 类 docstring 加一段（`strict` 只降级 raise、不关记账）；② `__init__` 增 `strict=True` 与 `unbooked_count = 0`；③ `detach` 改为 `ranges.get` + 未命中分支（计数 + `unbooked_detach` 事件 + strict 抛/不 drop；非 strict 照 drop）+ 命中路径原操作。`attach`（L1 部分）**未动**；`reset`/`safe_reset_all` 未动。
**v2 补正仅 docstring**：`diff _before@37a0a6f4 → 33ae679a` = 只有 docstring 一段，**行为零变化**（我逐行确认）⇒ 台账 `change.v2_delta` 自述属实。

---

## §2 两套分母并列（**不合并**）+ 链条

### 2.1 executor 主床（`_test_lease_detach.py`，4 例：H1 + U1/U2/U3；U4 进扩展床）

| 阶段 | 产物 | detach 调用 / 命中 / 未命中 | observed unbooked | 主床 drop_total | exit / fail |
|---|---|---|---|---|---|
| pre（`675f983f`） | `428f4cfe` | **4 / 1 / 3** | **0** | **5** | 2 / `[H1,U1,U2,U3]`（U4 亦红） |
| after（`33ae679a`） | `e68df9a4` | **4 / 1 / 3** | **3** | **2** | 0 / `[]` |
| `variant_b`（`4694db4c`） | `b20a03d8` | 4 / 1 / 3 | 0 | 5 | 2 / `[U1,U2,U3,U4]`（**H1 绿**） |

### 2.2 executor 扩展床（5 例：+`U4_non_strict_miss`，与主床并列、不与 pre 混算）

| 阶段 | detach / 命中 / 未命中 | observed unbooked | 扩展床 drop_total |
|---|---|---|---|
| pre | **5 / 1 / 4** | 0 | **6** |
| after | **5 / 1 / 4** | **4** | **3** |
| `variant_rollback`（模块 = `675f983f`） | 5 / 1 / 4 | 0 | 6 |

### 2.3 我的独立床（inspector `l2_constructs.py`，11 例：H1–H3 命中 + U1–U5 未命中 + N1/N2 非 strict + C1 基线）

| 阶段 | 产物 sha16 | 读数 |
|---|---|---|
| pre（我 20:24:15 快照 `675f983f`） | `768565e2`（v3；v1 `4a8b9438` 已交 lead） | 0 raised / U 的 on-unbooked 全 = 1 / `unbooked_count`=ABSENT / drop 9 |
| after（`33ae679a`） | `…/L2-inspector-after.json`（见 §11） | **6 raised**（U1–U5+C1）/ U 的 on-unbooked 全 = 0 / count 1 / drop 3 |
| `variant_b`（`4694db4c`） | `…/L2-inspector-variant-b.json` | **H1–H3 绿、U1–U5 红**（no raise、drop 1）/ 与 executor 的 H1 绿/U 红完全一致 |

**链条结论**：`pre 红 → after 绿 → variant_b 回红` **闭合**；`variant_rollback`（整体回退到 L1 版）**H1 也红是因为该模块没有 `unbooked_count` 属性**（`None ≠ 0`），**不是命中路径坏**——只能当整体回退证据，**不得用于「命中路径」判定**（命中路径的绿由 `variant_b` + after + 我的 H1–H3 三处独立支撑）。

---

## §3 主 KPI：`drop_delta_on_unbooked`（只测**被拒绝那次调用**的 `eng.drop` 增量）

| 例 | pre | after | variant_b | 期望 |
|---|---|---|---|---|
| `H1_hit` | 1 | **1** | 1 | 1 |
| `U1_never_attached` | 1 | **0** | 1 | 0 |
| `U2_table_drift_pop` | 1 | **0** | 1 | 0 |
| `U3_second_detach` | 1 | **0**（例内总 drop=1 来自前一次**合法** detach） | 1 | 0 |
| `U4_non_strict_miss` | 1 | **1**（非 strict 照 drop） | 1 | 1 |

**我独立复跑 executor 床**（landed 默认路径 + `--lease` 指向 pre 副本）得到**同表**：after `fail=[] exit 0`、pre `fail=[H1,U1,U2,U3,U4] exit 2`、主床 drop_total 5→2、扩展 6→3。我自己的 11 例床给出**同向读数**（U 的 on-unbooked pre 全 1 → after 全 0；N1/N2 非 strict = 1）。⇒ 「先 drop 再 raise」在**每一个**未命中例上都会被抓，不靠 U3 总量侧证。

---

## §4 `strict=False` 语义边界（不是「关判据开关」）

我独立构造（`N1` 从未挂载 + `N2` 已挂载表上未命中）：

| 读法 | N1 | N2 | 判定 |
|---|---|---|---|
| `raised` | False | False | 非 strict 不抛 ✓ |
| `unbooked_count` delta | **+1** | **+1** | 记账**照记** ✓ |
| 事件 | `unbooked_detach` | `unbooked_detach` | 留痕**照留** ✓ |
| `eng.drop` | 1 | 1 | 旧行为保留 ✓ |
| 默认构造 | `BlockLeases(eng).strict is True`；`unbooked_count == 0`（**不是 None**） | | ✓ |

结论：`strict` **只降级 raise**，不关记账/事件 ⇒ 符合 lead 裁定（若它连记账也关，才会被删）。我另核 docstring 自述「两种模式记账都不关」与实际代码一致。

---

## §5 `variant_b` 隔离（承重的是「未命中分支」本身）

- `diff variant_b(4694db4c) vs landed(33ae679a)`：**只删** `detach` 里的未命中检测 + 抛错分支，**保留** `strict` 形参、`unbooked_count` 初始化、docstring 其余内容 ⇒ 干净隔离，没有「删别的东西」。
- 读数：**H1 绿**（不抛、drop 1、count 0），**U1/U2/U3（及我的 U4/U5）红**（不抛、drop 1、count 0）⇒ 绿灯来自未命中分支，红也指回它。
- `variant_rollback`（`675f983f`）按 lead 裁定保留并标注 `caveat`（H1 红 = 缺属性），`out/M3-L2-variant.json 0658aa48` 亦保留。

---

## §6 `chat_lease.py` invariants + 新 raise 的边界

1. **sha 未动** = `619a0432`；我的文本快照（`sites:329` append / `report():359` / `STRICT:47`+`:232-236` / `range_mismatch:342-346` / reset 拒 `:320-326` / session_state 桥）**diff 为空**。
2. **独立 GuardedLeases 测试**（日志只落 temp）：
   - 命中 detach 经 guard：`returned=1`、`detached+1`、`drop+1`、事件 `attach/detach/released` —— **与 L2 前一致**；
   - 未命中 detach 经 guard：**`LeaseError` 照抛、不被吞**；`detached` delta 0、`drop` delta 0、`counts` 未被污染；`unbooked_detach` 事件落在 `BlockLeases.events`；
   - 既有 **reset 拒绝**语义不变：`refused+1`、raise 不吞、`drop` 0；`report()` 键仍为 `{counts, sites, refusals_logged, all_sites_asserted_empty}`。
3. **Note（留痕缺口，非本刀要求）**：未命中 detach 走 `GuardedLeases` 时，① 包装层不再写旧的 `detach`（`block_seq=None`）事件（因为 `super().detach` 先抛）；② `unbooked_detach` 只在 `BlockLeases.events`，**不进 `chat_lease` 的 `EVENT_LOG`/`sites`**。M4-C site3（`chat.py:562`）走**命中**路径，故不受影响；若将来要求产品级事件流也留痕，需在包装层补一条——**记为范围外 note，不判 L2 缺口**。

---

## §7 回归与未动清单

- **L1 不破**：executor `M3-L1-recheck-after-L2-v2 383516da` = **11/11、fail=[]、exit 0、拒绝 4/真命中 4**；我**独立重跑** `_test_lease_overlap.py`（默认输出）同样 **11/11 fail=[] exit 0**。
- **既有套件**：`_test_lease.py` 仍 `d2ddc6b6`，我现跑 **0 failed**。
- **`freeze_check`**：我现跑 `FROZEN (3 files, 3 thresholds, INDEX_VERSION 5 / ANALYSIS_VERSION 4)`，**exit 0**。
- **未动**（我逐份现算）：`chat.py cb70be52`、`kvmem/chat.db 237d8e1f`、`m2_planner` 三件（`01507f6b`/`74da0732`/`aa7cbf3f`）、`tools/chat_lease.py 619a0432`、`tools/freeze_check.py 6016085a`、`_test_lease.py d2ddc6b6`。

---

## §8 台账可信性

- **20 份逐文件复算 = 0 漂移**（8 份相对 `m3/` + `tools/*`、`kvmem/chat.db` 相对仓库根 + `out/*`）；`recompute.files_recomputed=20 / mismatched=[]` 与我的复算一致。
- **`_before@675f983f` = 我 20:24:15 快照逐字节相等**（7,526 B，`675f983f`）——用我**先于施工**的快照做基准，不采台账自述。
- **G1（先改后补副本）本轮已闭环**：`_before@675f983f` mtime **20:24:16**（早于 L2 主改动）；`_before@37a0a6f4` mtime **20:28:36**（早于 docstring 补正 20:28:41）⇒ **先副本再改**，L1 判决 §5 的规程已执行。
- `supersedes`（旧台账 `550faba2` / 6,928 B）+ `addendum.original` 全文保留、不抹旧读数；`tooling` 含 `land_l2.py b4e0d0fb` / `land_l1.py 52c2c669`；`self_registration` 明示不登记自身 sha；两采样 31 s `identical=true`（其列出的 20 个 sha 与我现算一致）。

---

## §9 工具卫生（L1 第 ④ 条不可签项的修复）

- 两份测试床默认输出均改为 **`tempfile.gettempdir()/m3_lease_products/`**（`_test_lease_overlap.py:213`、`_test_lease_detach.py:243`）；只有显式 `--out` 才写仓库 `out/`。
- **实证**：我跑 landed 默认路径 + pre `--lease` 各一次，`kvmem/m2_visibility/m3/out/` 目录列表**前后 diff 为空**（无新增文件）；产物落在 temp `…\m3_lease_products\M3-L2-203451.json`。⇒ L1 复核第 ④ 条不可签项**已修**。

---

## §10 四态 + 可签 / 不可签

**四态**：L2 零 GPU 判据层 = **通过**；L2 真机/产品路径重跑 = **未做**（产品 detach 两处 `chat.py:561/:593` 均命中路径，按码结构行为不变，但未实测）；产品级事件留痕 = **范围外 note**（§6 Note）。

**可签句**：
> L2 `detach` 未命中记账一致性已落地：改前主床 4 例红（H1 为缺 `unbooked_count` 属性的红 + U1–U3 静默 drop）→ 落地主床 **4/1/3、observed unbooked 3、drop_total 5→2**、扩展床 **5/1/4、drop 6→3**；`drop_delta_on_unbooked` **H1=1、U1–U3=0、U4=1**；`variant_b` **H1 绿 + U1–U4 红**；抛错路径 `unbooked_count` 从 **0** 起、事件落、`eng.drop` 不增；非 strict 只降级 raise（记账/事件/照 drop 均保留）；`chat_lease.py 619a0432` 未动、既有 reset 拒绝计数不变；L1 **11/11**、`_test_lease d2ddc6b6` **0 failed**、`freeze_check` **FROZEN**。

**可签（补充，限定范围）**：① 链条 pre→after→variant_b 闭合，两套分母并列不合并（§2）；② 我独立 11 例床同向读数（pre on-unbooked 全 1 → after 全 0；H1–H3 不变；N1/N2 边界符合）；③ 台账 20 文件 0 漂移 + `_before` 与我施工前快照字节相等 + G1 规程已执行；④ 工具默认输出已改、仓库不再被污染。

**不可签（逐条理由）**：
1. **「真机/产品路径读数不变」** —— 未重跑 `chat.py` 两条 detach 路径；`attach`/`detach` 命中路径按码结构不变，但**只有结构推断**。
2. **「产品级事件流含 unbooked 留痕」** —— `unbooked_detach` 只在 `BlockLeases.events`，不在 `chat_lease` 的 `EVENT_LOG`/`sites`；且未命中 detach 经包装时旧的 `detach(block_seq=None)` 事件不再写（§6 Note）。当前 M4-C 不依赖，但不能签「产品事件流已覆盖未命中」。
3. **「`variant_rollback` 的 H1 红说明命中路径坏」** —— 不可这样读：其原因是缺属性；命中路径证据只能用 `variant_b`/after/我的 H1–H3（已做）。
4. **`strict=False` 的产品调用面** —— 当前产品不用它；它只是兼容旧调用序列的降级路径，若将来被用于绕过判据须 lead 裁定（docstring 已声明只降级 raise）。

---

## §11 我的产物锚（temp，仅证据）

- 我组三阶段：`L2-inspector-after.json`（landed 11 例）、`L2-inspector-variant-b.json`（variant_b 11 例）、`L2-inspector-pre-v3.json` `768565e2`（pre，11 例）；`guard-l2.json`（GuardedLeases 边界，仅 temp 日志）。
- 复核中用到的字节快照：`pre-m3_lease.py@675f983f`（20:24:15，早于 executor 改码 20:24:2x）、`pre-chat_lease.py@619a0432`+invariants、`pre-overlap@7a92480b`、`post-*`（20:32 批次）、`varb/`（executor 的 variant_b 模块副本，`4694db4c`）。
- 自伤披露：本轮**未向仓库写任何文件**（运行产物全部落 temp，已用 `out/` 目录 diff 证明）；`__pycache__` 的 `.pyc` 由运行产生、未清理（避免再动仓库）。

---

## §12 数值锚（摘要）

`m3_lease.py 675f983f(7,526) → 37a0a6f4(8,701, 主改) → 33ae679a(9,047, docstring 补正)`；`_before` 三份（`7a838d0a`/`675f983f`/`37a0a6f4`）；床 `_test_lease_detach 4fc62f1b`、`_test_lease_overlap 85279a5b`（默认输出已改 temp，我实证仓库 `out/` 无新增）、`_test_lease d2ddc6b6`；台账 `467e0b3f`（supersedes `550faba2`）；产物 `pre-v2 428f4cfe` / `after-v2 e68df9a4` / `variant-b b20a03d8` / `rollback-v2 b5e73ae2` / `L1-recheck 383516da`；脚本 `land_l2 b4e0d0fb` / `land_l1 52c2c669`；未动 `chat_lease 619a0432`、`chat.py cb70be52`、`chat.db 237d8e1f`、`freeze_check 6016085a`（FROZEN/exit 0）、m2_planner 三件。