# L1 独立复核（inspector）

> **复核对象**：M2 完整 L1「位置租约重叠校验」落地（task-24，executor 自报通过；**本复核只读、未改仓库任何文件**）。
> **复核依据**：预登记 `docs/_work/M2-FULL-PREREG-draft.md` `4978c94474ba050c` §2.1；task-25 派单六步 + lead 补两条判。
> **结论一句话**：**L1 判据层 = 通过（可签）**；链条 `改前红 → 落地绿 → 变体回红` 闭合，抛错路径三态不动，`chat_lease.py`/`_test_lease.py` 未动，`freeze_check` FROZEN。**真机臂 = 未做**（未签「实测不改读数」）；另记 2 条范围/流程缺口、1 条测试工具缺陷（见 §7–§8）。
> **时间锚**：全部读数取 2026-10-25 **20:18–20:30**；所有 sha16 = 二进制读现算。我的全部产物在 `C:/Users/lezige/AppData/Local/Temp/m3l1/`。

---

## §1 坐标与快照（现算，不引 lead 值当证据）

**被测改动**：`kvmem/m2_visibility/m3/m3_lease.py` **`7a838d0a956e44aa`（6,211 B）→ `675f983f8d02f1df`（7,526 B）**；与我 20:11:01 的改动前字节快照 diff = **1 个 hunk，只在 `BlockLeases.attach`**：

| 新增 | 内容 | 位置 |
|---|---|---|
| +1 | `lo, hi = int(lo), int(hi)` 归一 | `attach` 开头 |
| +11 | 同块同区间重放分支：`ranges.get((dst,lo,hi)) == block_seq` ⇒ `_note("attach_replay")` 后 `return`（**跳过 `eng.share`**） | `eng.share` 之前 |
| +9 | 重叠检查：遍历 `ranges`，同 `dst_seq` 且半开相交（`klo < hi and lo < khi`）⇒ `LeaseError`（消息含两段区间 + 两个块名/seq） | **`eng.share` 之前** |

**证据坐标（我现算）**：改动后模块 `675f983f`；测试 `_test_lease_overlap.py` `7a92480b621eb408`（9,571 B）；台账 `m3/LANDED-l1.json` `db2893ee4fc75802`（6,739 B）；executor 产物 `out/M3-L1-pre.json` `dc31efac9ecf82e5`（7,454）/ `after` `6954b190ebd71d18`（8,132）/ `variant` `77db39ddd69f34c3`（7,496）/ `regression` `b1ac5823d4f7d238`（890）；`_before/m3_lease.py@7a838d0a956e44aa` = `7a838d0a` / 6,211 B。
**mtime 序（证明 pre 产物先于改码）**：pre 20:11:29 < `m3_lease.py` 20:11:59 < after 20:12:27 < variant 20:12:34 < regression 20:14:06 < 台账 20:16:26（`_before` 副本 20:12，见 §5）。
**未动清单（我逐份现算）**：`tools/chat_lease.py 619a043215035de7`、`m3/_test_lease.py d2ddc6b69249dab6`、`tools/chat.py cb70be52eef253fa`、`kvmem/chat.db 237d8e1f5de9a382`、`tools/freeze_check.py 6016085a05890581`、`analysis 49e91c7b` / `retrieval 43f66019` / `evidence dccf7f01` / `eval_heldout 597fd0ca`、`m2_planner` 三件 `planner 01507f6b` / `plan 74da0732` / `evict aa7cbf3f`。

---

## §2 链条：两组分母**并列、不合并**

### 2.1 我的组（inspector 独立构造床 `l1_constructs.py`，11 例：4 重叠 + 4 边界/相邻 + 2 跨 dst + 1 重放 + 2 既有拒 + 1 三态专例）

| 阶段 | 产物 sha16 / B | 构造 | 拒绝（总） | 其中 L1 真命中 | 未达标（红） |
|---|---|---|---|---|---|
| **pre**（20:11:01，**我先于落地独立锚定**） | `175ab618fdf551f9` / 7,754 | 11 | 2（C9 未注册 + C10 空块） | **0** | **C1/C2/C3/C11（4 例）** |
| **after**（现盘 `675f983f`） | `8fdec7b6d4826370` / 8,454 | 11 | **6** | **4** | 无（11/11） |
| **variant1**（只删重叠循环，保留 replay + 归一） | `5939c981d8f5d69e` / 7,753 | 11 | 2 | 0 | C1/C2/C3/C11 |
| **variant2**（删两处新增分支 = 改前语义） | `175ab618fdf551f9`（与 pre **逐字节相同**） | 11 | 2 | 0 | C1/C2/C3/C11 |

- pre 的红形态 = **静默双 share**：`share_calls_after = 2`（C1/C2/C3/C11），`ranges` 后被第二块覆盖。**这正是 L1 要堵的形态**，比「读不到异常」硬。
- 落地后：**6 raised = C1/C2/C3/C9/C10/C11**，C4–C8 全不抛 ⇒ 与预期**完全一致**。
- variant1 证明**承重的是重叠循环本身**（保留 replay/归一仍回红）；variant2 与 pre 产物逐字节相同，是链条自洽的强证据。

### 2.2 executor 组（`_test_lease_overlap.py` 自带 11 例：4 重叠 O1–O4 / 4 边界 / 2 跨 dst / 1 重放）

| 阶段 | 产物 | 构造/拒绝/真命中 | exit | fail_cases |
|---|---|---|---|---|
| pre（module sha `7a838d0a`，证明是改前跑） | `dc31efac` | **11 / 0 / 0** | 2 | O1–O4 |
| after（module `675f983f`） | `6954b190` | **11 / 4 / 4** | 0 | [] |
| variant（module sha `7a838d0a` = 改前字节） | `77db39dd` | **11 / 0 / 0** | 2 | O1–O4 |

**结论**：两组各自闭合；不做任何跨组分母合并。我组多出的 2 例（C9 未注册 / C10 空块）是**既有拒回归**，**不计入 L1 真命中**。另：我重跑 executor 测试一次，产物除 `pid/at` 元数据外与其 after **逐字段相同**（见 §8 自伤披露）。

---

## §3 抛错路径三态（本刀最易被做成假绿处）

现盘 4 个重叠拒绝例（C1 部分重叠 / C2 包含 / C3 完全相同 / C11 三态专例）逐例读数：

| 例 | raised | `share_calls_after` | 无新增 share | `ranges` 不变 | `holders` 不变 | 消息含 |
|---|---|---|---|---|---|---|
| C1 | ✅ LeaseError | **1**（仅 setup 那一次） | ✅ | ✅ | ✅ | `[4045,4095)` 与 `[4060,4100)` + 两块名 |
| C2 | ✅ | 1 | ✅ | ✅ | ✅ | 两段区间 |
| C3 | ✅ | 1 | ✅ | ✅ | ✅ | 两段区间（同区间不同块） |
| C11 | ✅ | 1 | ✅ | ✅ | ✅ | 同 C1 |

**判定**：实现是 **check-before-share**（先检查、后 `eng.share`/写表），**不是** share-then-check ⇒ 拒绝路径 `holders`/`ranges`/`eng.share` **三者都不动**。若把检查挪到 `share` 之后，C11 会立刻红（`share_calls_after=2` 且表已变），属**实现错**。

---

## §4 invariants / 回归 / 未动

1. **`chat_lease.py` 未动**：sha 仍 `619a043215035de7`；我的文本快照（`GuardedLeases:282`、`sites:289`+`:329` append 形状、`reset:316`（拒绝计数+raise 不吞、`:331-336` cells≠0 抛）、`attach:339`、`detach:351`、`report():359`、`STRICT:47`+`:232-236`、`from_manifest:296`+`range_mismatch:342-346`、session_state 桥 `share:208`/`reset:218`）**diff 为空**。
2. **独立组合测试**（`guard-check.json` `8c8384f3efcc7138`，零 GPU、日志只落 temp）：经 `GuardedLeases` 的重叠 ⇒ `LeaseError`、消息含两段、`tables_unchanged=true`、`share_delta=0`、`counts.attached=1`、`report()` 键 = `{counts, sites, refusals_logged, all_sites_asserted_empty}`；`from_manifest` 声明 `[4045,4095)` 实挂 `[4040,4090)` ⇒ **`range_mismatch` 事件照记、不抛** ⇒ 语义未变。
3. **既有套件**：`_test_lease.py` sha 仍 `d2ddc6b69249dab6`；我现跑 **0 failed**。
4. **`freeze_check`**：我现跑 = `SELECTION LAYER: FROZEN (3 files, 3 thresholds, versions {'INDEX_VERSION': 5, 'ANALYSIS_VERSION': 4})`，**exit 0**。
5. `tools/`、`kvmem/chat.db`、`m2_planner/` 三件未动（sha 见 §1）。

---

## §5 台账可信性

- **11 文件逐份复算 = 0 漂移**：8 份相对 `m3/`（`m3_lease.py 675f983f`、`_test_lease_overlap.py 7a92480b`、`_test_lease.py d2ddc6b6`、`out/M3-L1-pre dc31efac`、`after 6954b190`、`variant 77db39dd`、`regression b1ac5823`、`_before/m3_lease.py@7a838d0a 7a838d0a`）+ 3 份相对仓库根（`tools/freeze_check.py 6016085a`、`chat_lease.py 619a0432`、`chat.py cb70be52`），台账记的 `sha16/bytes` 与现盘**全部相等**；`recompute.mismatched=[]` 与我的复算一致。
- **`_before` 副本可信（双重交叉验证）**：① 与我的 20:11:01 独立快照**逐字节相等**（6,211 B，`7a838d0a`）；② `git show HEAD:kvmem/m2_visibility/m3/m3_lease.py` = **`7a838d0a` / 6,211 B** ⇒ 副本确为改前态，**不是改后伪造**。
- 两采样 31 s `identical=true`，我核对其列出的 11 个 sha 与现算一致。台账自身不登记自己的 sha（`self_registration` 明示「自指恒假」）✓。
- **流程缺口 G1（记录、不追责、可接受）**：副本 mtime 20:12 晚于改码 20:11:59 ⇒ **先改码、后从 `git show HEAD:` 补取**，非施工前落盘。本次因上述双重交叉验证成立而**可接受**；但流程不合规（若 git 对象被改写/未跟踪则无法自证）。建议 land 脚本强制「先落 `_before` 再改码」，后续票据沿用。

---

## §6 两处语义变更的风险判

### (a) 重放分支跳过 `eng.share`（语义确实变了）

- 事实：同一块同一区间二次 attach，pre 会再 share（`share_calls_after=2`），现盘跳过（`=1`）并记 `attach_replay`。
- **现产品路径不会命中**（结构判断，我独立按代码 + `chat.db` 块大小 50/36 复算）：
  - `chat.py:310`（`_place`）：`cursor=CHAT_START` 逐块向前连续打包 ⇒ 块 1 `[4010,4060)`（50 cells）、块 2 `[4060,4096)`（36），一次运行内每块只 attach 一次；
  - `chat.py:397`（`_place_slots`）：`end=CHAT_START-(i-1)*SLOT`、`lo=end-n` ⇒ 块 1 `[4046,4096)`、块 2 `[3996,4032)`（中间 14 cells 空档）；
  - `chat.py:604`（`cmd_m1` mount）：`end=CHAT_START-i*SLOT`、`lo=end-n` ⇒ 同 `_place_slots` 的两段；且 `:593` 先 detach、`:595` reset、`:598` load ⇒ **旧键已删，重放不命中**。
  - 三处 `dst_seq` 都是 0，现区间**两两互斥**（`n_i=50/36 ≤ SLOT=64`）⇒ L1 在现产品路径**不抛错、不改行为**；`int` 归一在原值已是 int 时无差异。
- 对 **M4-C 14B 绿臂/未来真机**：按上，产品 attach 逐调用行为相同 ⇒ **结构上不应改读数**；但**我未重跑 14B 绿臂**，故只能签「不应改」，**不签「实测未改」**。
- **残余风险**：replay 跳 share 依赖「租约表与引擎状态严格同步」。若将来出现「引擎侧被清/改而表未动」的路径（S1 多会话复用挂载、或有人跨过租约表），重放会**静默不挂载**。建议 S1 若复用 replay，先补「表-引擎一致性」判据，或 S1 禁 replay。

### (b) L1 只查 `ranges`：**范围外（设计边界）+ 一条 S1 集成前提**，不算 L1 缺口

- 定性：L1 的保证域 = **「经 `BlockLeases` 的挂载不重叠」**。引擎侧外力（直接 `eng.share`、`planner.py:66/82` 的 `share_new`/`repos_local`、`m2_v1` 工具、真机臂里的直接 share）**不在域内**，L1 查不出。
- 理由：租约表职责是记账；要发现「绕过自己的写」需引擎侧 hook 或对账，属另一装置 —— 且 `PROGRESS:761/:771-776` 已实测「引擎不拒绝 reset」，引擎不会替我们报警。把这件事写成 L1 的缺口会**误导**（它做的是它承诺的那一层）。
- **S1 集成前提（必须写进 S1 预登记）**：多会话的 share/drop **必须全部走租约表**（或加一条「直接 `eng.share` 计数 = 0」的断言），否则 L1 对多会话失效。

---

## §7 四态 + 可签 / 不可签

**四态**：L1 零 GPU 判据层 = **通过**；L1 真机臂 = **未做**；引擎侧外力 = **范围外（记录）**；台账流程 = **G1 缺口（记录、不追责）**。

**可签（lead 句式，数值为我现算）**：
> L1 位置租约重叠校验已落地：改前 4 例红（静默双 share，`share_calls` 2）→ 落地 11/11 → 变体删检查回红；抛错路径三态不动；`chat_lease.py` `619a0432` / `_test_lease.py` `d2ddc6b6` 未动；`freeze_check` FROZEN。

**可签（补充，限定范围）**：
1. **链条闭合**：我组 `pre 175ab618 → after 8fdec7b6 → variant1 5939c981 / variant2 175ab618(=pre)`；executor 组 `dc31efac → 6954b190 → 77db39dd`，两组各自三级分母并列（§2）。
2. **抛错三态**：4 个重叠拒绝例 `holders`/`ranges`/`eng.share` 三者不动（§3），实现是 check-before-share。
3. **产品不触发**：`chat.py` 三处 attach 区间两两互斥（我按 `:250-256`/`:397`/`:599-604` 公式 + `chat.db` 块 50/36 独立复算），`dst_seq` 均为 0；replay 分支在现产品路径不命中。
4. **未动清单**：`chat_lease.py`、`_test_lease.py`、`chat.py`、`chat.db`、`m2_planner`、冻结三件/阈值/两版本号。
5. **台账**：11 文件 0 漂移；`_before` 与我的独立改前快照字节相等 + git HEAD 对象相等。

**不可签（逐条给理由）**：
1. **「实测不改真机读数」** —— 未重跑 M4-C 14B 绿臂，只有结构推断（§6a）。
2. **「replay 分支安全」** —— 只在表-引擎同步前提下成立，该前提**无测试**；S1 若复用需另立判据。
3. **「L1 保护引擎侧外力」** —— 范围外；只保护经租约表的挂载（§6b）。
4. **`_test_lease_overlap.py` 工具卫生** —— 默认把产物写进仓库 `out/M3-L1-<HHMMSS>.json`（无 `--out` 时），我运行即产生残留（已删，见 §8）；**不影响 L1 判据**，但应改默认到 temp 或强制 `--out`。
5. **G1 流程** —— `_before` 后补（可接受但记缺口，§5）。

---

## §8 自伤披露 + 边界

- **我的一处仓库写入**：复核时运行 executor 的 `_test_lease_overlap.py`，其**默认输出路径**写了 `kvmem/m2_visibility/m3/out/M3-L1-201838.json`（`ae64767e962126e5` / 8,132 B；与 after 仅差 `pid/at` 元数据）。**已立即删除**，副本留在 temp（`inspector-run-M3-L1-201838.json`）；仓库 `out/` 现只剩 executor 的 4 份 + `M3-L2-pre.json`（见下）。这是我第二次踩「工具默认写仓库」的坑，已在 §7 不可签第 4 条记录其工具缺陷。
- 我的运行还在 `kvmem/m2_visibility/m3/__pycache__/` 写 `.pyc`（无害、未清理，避免再动仓库）。
- **并行施工边界**：复核期间（20:18）executor 已开始 L2 —— `_test_lease_detach.py`（9,234 B）与 `out/M3-L2-pre.json` 出现；**不属本次复核**，我不对其作任何判断；L1 的 7 个坐标文件 sha 在复核前后一致（§1）。
- 本次复核**未**改任何代码/产物/数据库/他人文档；唯一新增文件 = 本文件。

---

## §9 数值锚（摘要）

- 改动：`m3_lease.py 7a838d0a(6,211) → 675f983f(7,526)`，1 hunk @ `attach`；`_before` 副本 `7a838d0a`；新测试 `7a92480b`；台账 `db2893ee`。
- 我组：pre `175ab618`（11/2/0，4 红）→ after `8fdec7b6`（11/6/4，0 红）→ variant1 `5939c981` / variant2 `175ab618`（各 11/2/0，4 红）；`guard-check.json 8c8384f3`。
- executor 组：`dc31efac`（11/0/0 exit2）→ `6954b190`（11/4/4 exit0）→ `77db39dd`（11/0/0 exit2）；`b1ac5823`（回归）。
- 未动：`chat_lease 619a0432`、`_test_lease d2ddc6b6`、`chat.py cb70be52`、`chat.db 237d8e1f`、`freeze_check 6016085a`（FROZEN/exit 0）、`analysis 49e91c7b` / `retrieval 43f66019` / `evidence dccf7f01` / `eval_heldout 597fd0ca`、`planner 01507f6b` / `plan 74da0732` / `evict aa7cbf3f`。
- 产品实测几何（我独立复算）：块 50/36 cells；`:310` `[4010,4060)`/`[4060,4096)`；`:397` 与 `:604` `[4046,4096)`/`[3996,4032)`；互斥条件 `n_i ≤ 64`。