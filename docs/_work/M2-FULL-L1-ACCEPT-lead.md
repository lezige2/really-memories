# M2 完整 · L1 定稿（lead · 2026-10-25 20:30 本地）

> 预登记 `docs/_work/M2-FULL-PREREG-draft.md` `4978c94474ba050c` §2.1（判据原文）· 独立复核 `docs/_work/INSPECTOR-L1-REVIEW.md` `66cf3aa5025be42c`
> 交付：`kvmem/m2_visibility/m3/m3_lease.py` `7a838d0a956e44aa → 675f983f8d02f1df`（6,211 → 7,526 B，**1 处改动**）

---

## 0 一句话

**L1（位置租约重叠校验）= 通过**：改前 4 例红（红形态 = **静默双 `share`**，同一 `dst_seq` 上后挂的块覆盖前者 cells）、落地后两组各自全绿、变体裁掉检查即回红；**检查确实在 `eng.share` 之前**（拒绝路径 `holders`/`ranges`/`share` 三者不动）；`chat_lease.py` 与既有测试**一字未动**。**真机臂未做**（本刀零 GPU 不要求），不可签项见 §5。

## 1 改了什么（diff 全文可读：1 个 hunk）

`attach(block_seq,dst_seq,lo,hi)` 在 `eng.share` 之前新增：
1. `lo,hi = int(lo),int(hi)` 归一（原值已是 int，非重叠路径无行为差）；
2. **同块同区间重放** ⇒ 记 `attach_replay`、`return`（幂等，不重复 share）；
3. **同 `dst_seq` 半开相交** `klo < hi and lo < khi` ⇒ `LeaseError`，消息含 `dst_seq`、两段 `[lo,hi)`、两个块名；**抛错前不 share、不改表**。
不同 `dst_seq` 重叠**保持合法**（同一块挂多 seq 正是 M2 并发形态）。

## 2 读数（两组分母并列，**不合并**）

| 组 | 改前（红） | 落地后（绿） | 变体（删检查） |
|---|---|---|---|
| **executor 组**（4 重叠 + 4 边界 + 2 跨 dst + 1 重放 = 11） | `out/M3-L1-pre.json` `dc31efac9ecf82e5`：11 / 拒绝 **0** / 真命中 **0**，fail O1–O4，exit 2 | `out/M3-L1-after.json` `6954b190ebd71d18`：11 / **4** / **4**，fail=[]，exit 0 | `out/M3-L1-variant.json` `77db39ddd69f34c3`：回到 11/0/0、4 红、exit 2 |
| **inspector 组**（4 重叠 + 4 边界 + 2 跨 dst + 1 重放 + 2 既有拒 + 1 三态专例 = 11 但**用例不同**） | `L1-inspector-pre.json` `175ab618fdf551f9`：11 / **2** / 0，**4 红 C1/C2/C3/C11** | `after` `8fdec7b6`：11 / **6** / **4**，6 raised = C1/C2/C3/C9/C10/C11，C4–C8 不抛，**0 红** | `variant1`（只删重叠循环、留 replay+归一）`5939c981` 与 `variant2`（整体回退，= pre **逐字节相同**）**均回红** |

**链条闭合**，且 `variant1` 证明承重的是**重叠循环本身**（保留 replay/归一仍回红）—— 排除了"绿灯来自别的改动"。

## 3 抛错路径三态（本刀最易假绿处，独立复核过）

4 个重叠拒绝例：`raised=true`、`share_calls_after=1`（仅 setup 那次）、`no_share_on_raise` / `ranges_unchanged` / `holders_unchanged` 全 true、消息含两段区间。
⇒ **实现是 check-before-share，不是 share-then-check**。若为后者，异常照抛但 cells 已被覆盖 —— 这条是独立于执行方自报的判据。

## 4 未动项 / 回归

| 项 | 值 |
|---|---|
| `tools/chat_lease.py` | **`619a043215035de7`**，文本 invariants 快照 diff **为空**（`sites:329` / `report():359` / `STRICT:47`+`:232-236` / `range_mismatch:342-346` / session_state 桥） |
| `m3/_test_lease.py` | **`d2ddc6b69249dab6`**（施工前后同值），现跑 **0 failed** |
| `GuardedLeases` 组合测试 | 经包装层重叠 ⇒ `LeaseError`、表不变、`share_delta=0`、`report()` 键不变；`from_manifest` 声明不符 ⇒ `range_mismatch` **照记不抛** |
| `freeze_check` | **FROZEN / exit 0** |
| `tools/chat.py` / `kvmem/chat.db` / `m2_planner/` | `cb70be52` / `237d8e1f` / 未动 |
| 台账 `m3/LANDED-l1.json` | `db2893ee4fc75802`，11 文件逐份复算 **0 漂移**，两采样间隔 31 s `identical=true`；`_before/m3_lease.py@7a838d0a` 与复核方 20:11:01 独立快照**逐字节相等**、且 `git show HEAD:` = `7a838d0a` |

## 5 四态 + 不可签

| 项 | 判 |
|---|---|
| L1 零 GPU 判据层（重叠拒绝 + 三态 + 变体红证 + 回归） | **通过（本判决签署）** |
| L1 真机臂（14B 上跑一遍看读数不变） | **未做**（本刀零 GPU 不要求；但因此不可签"实测未改真机读数"） |
| 引擎侧外力（绕过租约表直接 `eng.share`） | **范围外（记录）**：L1 的保证域 = 「经 `BlockLeases` 的挂载不重叠」 |
| 施工流程 | **缺口 G1（记录、不追责）**：executor **先改码后补 `_before`**；副本经 `git HEAD` + 复核方独立快照双证可信，但流程应"先副本再改" |

**不可签**：①「实测不改 14B 真机读数」（未跑）②「replay 在表-引擎不同步下也安全」（无测试）③「L1 能保护引擎侧外力」④「测试床默认不写仓库」（`_test_lease_overlap.py` 默认把产物写进 `out/`，复核方一跑就留残留 `M3-L1-201838.json`，已删）⑤「无流程缺口」（G1）。

## 6 记入下游的两条前提（**S1 必须写进预登记**）

1. **L1 的保证域是"全部走租约表"**：S1 的多会话 `share/drop` 必须全经 `BlockLeases`，否则要加「**直接 `eng.share` 计数 = 0**」的断言，不然 L1 对多会话失效。
2. **replay 分支依赖「表-引擎严格同步」**：引擎侧被清而表未动时会**静默不挂载**。S1 若复用 replay，必须补一致性判据，或**禁 replay**。

## 7 归因说明（不是缺口，是价值）

产品三处 attach 的 `dst_seq` 都是 0，区间两两互斥：`:310` 连续打包 `[4010,4060)`/`[4060,4096)`；`:397`/`:604` 走 `SLOT=64` 网格 `[4046,4096)`/`[3996,4032)`。互斥**依赖每块 n ≤ SLOT=64** —— n>64 时旧代码会静默覆盖前块 cells，**现在会抛错显形**。这就是这一刀的意义：把"静默覆盖"变成"响"。

## 8 签署

| 项 | 内容 |
|---|---|
| 签署人 | lead |
| 签署 | **L1 位置租约重叠校验：通过**（2026-10-25）—— 改前 4 例红（静默双 share）→ 落地两组各自全绿 → 变体删检查即回红；抛错路径三态不动；`chat_lease.py`/`_test_lease.py` 未动；`freeze_check` FROZEN |
| 可复算 | 产物 ⇐ `dc31efac9ecf82e5` / `6954b190ebd71d18` / `77db39ddd69f34c3` / `175ab618fdf551f9` / `8fdec7b6` / `5939c981`；台账 ⇐ `db2893ee4fc75802`；复核 ⇐ `66cf3aa5025be42c`；预登记 ⇐ `4978c94474ba050c` |
| 下一步 | **L2**（`detach` 未命中记账不一致；改前红已取：`out/M3-L2-pre.json` `5d2f864b301af8ec`，4 detach / 命中 1 / 未命中 3、`drop_calls_total=5`、fail U1/U2/U3）→ 再 P1 → 再 S1 |