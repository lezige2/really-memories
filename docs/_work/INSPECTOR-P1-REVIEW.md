# P1 独立复核（inspector）

> **对象**：M2 完整 P1「pinned 驱逐」零 GPU 层（预登记 `docs/_work/M2-FULL-PREREG-draft.md` §2.3，`4978c94474ba050c`）。
> **性质**：只读独立复核；**仓库只写本文件**，全部运行/对照产物落系统临时目录（`C:/Users/lezige/AppData/Local/Temp/p1/`）。
> **结论一句话**：**P1 零 GPU 判据层 = 通过（可签）**；改前 4 红 → 5/5 绿；两条变体红点精确；`pinned_from_leases` 的 duck-typed 契约（无 `.leased()` ⇒ 显式 `TypeError`）成立；判据 ③ 的**同代对照**成立（旧/新模块在同一现 `planner.py` 上，除 `modules/evict_policy.py`/`at` 外逐字段相同，残留 `[]`），且 `GREEN naming` 漂移**由旧模块同样复现** ⇒ 属既有漂移（r2 D1），非 P1。跨批守门全绿。
> **时间锚**：2026-10-25 20:50–21:00；sha16 全部二进制现算。

---

## §0 方法与边界

- 五份产物**不采信台账自述**：我用 `_test_evict_pinned.py`（`94b3ce56`）在 temp 里对 after/pre/两条变体重跑，逐 case 比对 `got/checks/ok/fail/分母`。
- 判据 ③ **不采信 executor 的分层结论**：我自己搭两个镜像目录（`reg_old/`、`reg_new/`，同一现 `planner.py 01507f6b`），只换 `evict_policy.py`，跑 `red_suite.py` / `test_planner.py` / `selftest_plan.py`，JSON 摊平后做三层对照。
- 只引现算 sha；台账 sha 引用前复算。

---

## §1 坐标（我现算）

| 对象 | sha16 / bytes | 时间/说明 |
|---|---|---|
| `evict_policy.py` | **`c2a8d8cbb5b0d4e3`** / 6,030 | 20:42:11（落地） |
| `_before/evict_policy.py@aa7cbf3f86df30f8` | `aa7cbf3f` / 3,468 | **20:41:17 —— 早于改码，先副本再改成立** |
| `_test_evict_pinned.py` | `94b3ce567cd809be` / 11,554 | 5 例：H1/H2/M1/A1/O1 |
| `land_p1.py` | `e39636c2b246c044` / 22,408 | 已在台账 `tooling` |
| `LANDED-p1.json` | `73522bc3cb69967b` / 11,134 | 18 文件、两采样 31 s `identical`、我复算 **0 漂移** |
| 产物 | `P1-pre 9d5df8c3` / `P1-after 495a54de` / `variant-no-filter 22d96d19` / `variant-allpinned-silent b70cef0e` / `regression 02b1e9bc` | 均 20:44:54 |
| `planner.py` | `01507f6b` / 9,093 | 19:40:56（r2 D1 后） |
| `plan.py` | `74da0732` / 4,290 | **未动** |
| 签名回归产物 | `RED-SUITE 13771a2d`（19:06:41）· `GREEN-SUITE d3485eb2`（19:06:41）· `PLAN-SELFTEST a0c0782b`（19:11:22） | 均早于 `planner.py` 改时 19:40:56 ⇒ **与现模块漂移，成立** |

**改动范围（我 diff `aa7cbf3f→c2a8d8cb`）**：只加两样 —— ① 新函数 `pinned_from_leases(leases, n_seq)`（duck-typed `.leased()`，无则显式 `TypeError`）；② `select_to_evict` 新增 `pinned=()`：`pin` 非空时在**本函数**过滤，另加 `pinned/refused_reason/pinned_skipped/pinned_note` 四键，全 pinned+超预算 ⇒ `evicted=[]`、`over_budget_after=True`、`refused_reason="all_pinned"`；`pin` 空 ⇒ **返回旧 dict（键与值都不变）**。`evict_order` / `DEFAULT_POLICY` / `plan()` 未动。

---

## §2 ① 五份产物：我独立重跑，读数逐项一致

重跑方式：`_test_evict_pinned.py --policy <模块> --out <我的产物>`（`pre` 用 `_before` 字节副本、变体用各自模块；**均不写仓库**）。

| 产物 | 我重跑 exit / fail | 分母（总块/pinned/被踢） | 与 executor 产物读数 |
|---|---|---|---|
| pre | 2 / `[H1,H2,M1,A1]`（O1 绿） | **13 / 6 / 0** | 逐 case `got/checks` **相同** |
| after | 0 / `[]` | **13 / 6 / 1** | 相同 |
| variant-no-filter | 2 / `[M1,A1]` | 13 / 6 / **2** | 相同 |
| variant-allpinned-silent | 2 / `[A1]` | 13 / 6 / 1 | 相同 |

> 产物**字节**不同（路径/`at` 不同），但**读数逐字段相同** —— 这正是「复核=重算读数，不是比对文件字节」的正确口径。

关键读数（我复算）：M1 混合集 `evicted=[4]`、`kept_seqs=[1,3,2,5,7]`、`evicted_meets_pinned=[]`、`over_before=True/after=False`、`refused_reason=null`；A1 全 pinned `evicted=[]`、`kept=[2,5,7]`、`over_before=True/after=True`、`refused_reason="all_pinned"`、`caller_action="PlanRefused"`；O1 `policy=off` 键集恰为 `OLD_KEYS` 七键。

---

## §3 ② 判据 ③：同代对照 + 既有漂移控制（**我自己重算，未采信 executor**）

做法：temp 下建两个镜像 `reg_old/`（旧模块 `aa7cbf3f`）与 `reg_new/`（新模块 `c2a8d8cb`），**其余文件全部拷自现仓库**（`planner.py 01507f6b`、`plan.py 74da0732`、`kvsim/assertions/fake_planner/red_suite/test_planner/selftest_plan` 同代），各自跑三份套件，JSON 摊平逐字段比。

| 产物 | 旧模块 vs 新模块（同代） | 旧模块 vs 签名产物（既有漂移） | 残留（新−签名 减去 漂移 减去 P1 字段） |
|---|---|---|---|
| `RED-SUITE` | **`[]`**（且 old=new=signed=`13771a2d`） | **`[]`** | **`[]`** |
| `GREEN-SUITE` | **`[]`**（old=new=`52fc03d4`） | `/assertions/E1_effect_verified/1/log/3/naming`：**old=`cells_moved(=50)`** vs signed `(=45)` | **`[]`** |
| `PLAN-SELFTEST` | 仅 `/modules/evict_policy.py`（`aa7cbf3f→c2a8d8cb`） | `/modules/planner.py`（**signed=`4162661c`** vs old/new=`01507f6b`）、`/at` | **`[]`** |

**结论**：
1. **判据 ③（同代对照）成立**：同一现模块环境下，旧/新 `evict_policy` 的套件输出除 `modules.evict_policy.py`（与可允许的 `at`）外**逐字段相同**；`p1_isolation_unexpected=[]`。
2. **「旧模块跑出来也差 GREEN naming」= 真**：旧模块产出同样是 `cells_moved(=50)`，与签名产物的 `(=45)` 不同 ⇒ **该漂移不是 P1 引入的**，是 r2 D1 的既有结果。
3. **归因有独立证据**：`LANDED-m2accept-r2.json` 记 `planner.py 4162661c→01507f6b`、scope「D1/D2/D3 修完后重跑」；现 `planner.py:132-134` 的 naming 由实参 `%d` 生成（旧版硬编码 45）⇒ 签名产物 `GREEN-SUITE` 是在 `planner.py=4162661c` 时代产生的。
4. **「逐字节相同」判据作废是对的**：签名产物 mtime 19:06/19:11，早于 `planner.py` 19:40:56 ⇒ 字节相同在事实上不可能；按同代对照判是唯一可判口径，且已判过。
5. 我复跑的 `PLAN-SELFTEST` 新模块 sha 与 executor 记录的 `83ec7645` 不同（我 `6097f6f5`），差异**只在 `/at` 时间戳** —— 引用其产物 sha 时须注意这是「运行时刻量」，不是常量。

---

## §4 ③ 两条变体：红点精确

- `variant-no-filter`（diff = 只删 `if pin:` 过滤块，其余同落地版）：**fail {M1,A1}**；M1 `evicted=[7]` ⇒ `evicted∩pinned=[7]`（**正是「pinned 被踢」**）；A1 同样 `evicted=[7]`；被踢数 2（M1+A1）。⇒ 红在「pinned 没被保护」，不是别的。
- `variant-allpinned-silent`（diff = 全 pinned 分支改成 `evicted=[]、over_after=False、refused_reason=None` 的静默降级）：**只 fail {A1}**；M1 仍 `evicted=[4]` 绿；A1 `over_after=False`、`refused_reason=null`、`caller_action="proceed"` ⇒ 红在「静默降级」，不是把别的东西弄坏。
- 两变体模块 sha 我现算：`no_filter d8821fd775a51f88` / `allpinned_silent 163de6a477d166c1`（台账只记产物 sha，未记变体模块 sha —— 见 §8 不可签 ④）。

---

## §5 ④ `pinned_from_leases` duck-typed 契约

| 被调对象 | 我实测 |
|---|---|
| 无 `.leased` 属性的普通对象 | **`TypeError`**（消息含「需要带 .leased(seq) 的租约对象」「正确读数是『未接上』」） |
| 有 `.leased` 但**不可调用**（`leased = 5`） | **`TypeError`**（额外边界，H2 未覆盖，我补测） |
| 正常 stub（leased 于 {2,5,7}，`n_seq=8`） | 返回 `{2,5,7}`，探测 seq **1..7**（不含对话 seq 0） |
| `n_seq=1` | 返回空集（`range(1,1)`，合法空集；不是「未接上」冒充） |

⇒ 契约成立：**拿不到租约表时是「未接上」，绝不会静默返回空 pinned 冒充绿**。测试床 `H2` 用显式 `expect_raise` 判（不吞异常），`H1` 判 pin 来源与探测序列。

---

## §6 ⑤ 冻结面/语义面未动（我逐项验）

1. `plan.py` **`74da0732`** 未动；`plan(blocks, chat_start, budget)` 签名不变。
2. `evict_order` **未动**（diff 无该函数）；行为等价比对 5 组输入（空/单块/LRU/三块平手/无 key）**全等**；它仍**不接 pinned**（纯排序）。
3. `DEFAULT_POLICY="off"`：新旧模块均 `off`；真机/产品路径不 import 它 —— `grep` 全仓：**`selftest_plan.py:22`** 是唯一 import（测试/自检），`planner.py`/`plan.py`/`tools/chat.py` **0 命中**；`select_to_evict` 的调用者只有 `selftest_plan.py` 与测试床（主路径不接）。
4. `pinned=()` 缺省 ⇒ `select_to_evict` 输出与旧模块**逐字段相同**（我对 7 组输入/两种 policy 做 `dict==` 全等；O1 另判键集恰为 7 键、不许多）。
5. 不发明阈值：`mount_cap=None` 缺省即不启用，本单未加任何常数阈值（`N_CTX` 是测试参数）。

---

## §7 ⑥ 跨批守门（我现跑）

| 项 | 结果 |
|---|---|
| `m3_lease.py` | `33ae679a50d58c93` / 9,047 ✓ |
| L1 重叠床 | **11/11、fail=[]、exit 0**（我现跑） |
| L2 detach 床 | **5/5、fail=[]、exit 0**；`drop_delta_on_unbooked={H1:1,U1:0,U2:0,U3:0,U4:1}`（我现跑） |
| `tools/chat_lease.py` | `619a043215035de7` / 19,274 ✓ |
| `kvmem/chat.db` | `237d8e1f5de9a382` / 110,592 ✓ |
| `tools/freeze_check.py` | **FROZEN / exit 0**（我现跑） |
| 仓库 `out/` | 我的运行**未新增任何文件**（默认输出 temp 已验证；`*-regen.json` 是 task-29 的，不属 P1） |

---

## §8 ⑦ 四态 + 可签 / 不可签

**四态**：P1 零 GPU 判据层 = **通过**；「pinned 驱逐接到产品主路径/真机」= **未做**（预登记 §2.3 本单只做模块层与判据，不接 `plan()` 主路径；这**不是缺口**，是范围）；产品路径 import = **未接上（按设计，默认 off）**。

**可签句**：
> P1 pinned 驱逐模块层已落地：改前 4 红（H1/H2 无 helper、M1/A1 无 `pinned` 形参）→ 落地 5/5 绿、分母 **13/6/1**（pre `13/6/0`）；M1 `evicted=[4]` 且 `evicted∩pinned=[]`，A1 `evicted=[]`/`over_after=True`/`refused_reason="all_pinned"`/`caller_action="PlanRefused"`；两条变体红点精确（no-filter ⇒ M1 的 `evicted∩pinned=[7]` + A1 红；allpinned-silent ⇒ 只 A1 红、M1 绿）；`pinned_from_leases` 无 `.leased()` ⇒ 显式 `TypeError`（非空 pinned 不冒充绿）；判据 ③ 同代对照成立、残留 `[]`，`GREEN naming` 漂移由旧模块同样复现 ⇒ 属既有 r2 D1 漂移、非 P1；`plan.py 74da0732`/`evict_order`/`DEFAULT_POLICY="off"`/主路径未接 全部未动；跨批 `m3_lease 33ae679a`、`chat_lease 619a0432`、`chat.db 237d8e1f` 未动，L1 11/11、L2 5/5、`freeze_check` FROZEN。

**不可签（逐条）**：
1. **「P1 在真实对话里生效」** —— 未接主路径/未上真机；按范围本单不签这条（要签需另单接线 + 真机臂）。
2. **「`_before` 副本有第三方字节交叉」** —— 仓库该文件不在 git 追踪（`git show HEAD:` 报 `exists on disk, but not in 'HEAD'`），真前态只有：`_before` 字节（`aa7cbf3f`）+ **mtime 20:41:17 早于新模块 20:42:11** + 台账采样。**「先副本再改」由 mtime 顺序成立，但没有独立第三方锚**；建议后续把 pre 副本另存 temp 供复核（本轮我无法回到施工前）。
3. **「变体模块可复现」** —— 台账只记两份变体**产物** sha，未记变体**模块** sha（我现算 `d8821fd7` / `163de6a4` 并核对 diff = 只删对应代码）；建议台账补字段。
4. **「executor 记录的 PLAN-SELFTEST new sha 是常量」** —— `83ec7645` 含运行时刻，我复跑得 `6097f6f5`；二者只差 `/at`，**不影响判定**，但引用产物 sha 时须知其非恒定。

**范围外顺手核（task-29 regen，不并入 P1 判定）**：`RED-SUITE-regen` 与签名**逐字节相同**（`13771a2d`，diff 0）；`GREEN-SUITE-regen` 与签名只差 `naming`（45→50，即 D1 漂移本身被重生成吸收）；`PLAN-SELFTEST-regen` 与签名只差 `modules/planner.py`（`4162661c→01507f6b`）、`modules/evict_policy.py`（P1）、`/at` ⇒ **「真行为差异 = 0」在其口径上成立**（差异全是模块 sha/时间戳/已登记的 D1 字段）。

---

## §9 数值锚

`evict_policy aa7cbf3f(3,468) → c2a8d8cb(6,030)`；`_before` mtime 20:41:17 < 新模块 20:42:11；床 `_test_evict_pinned 94b3ce56`（5 例 / 13 块 / 6 pinned / 1 踢）；产物 `pre 9d5df8c3`·`after 495a54de`·`variant-no-filter 22d96d19`·`variant-allpinned-silent b70cef0e`·`regression 02b1e9bc`；变体模块 `d8821fd7`/`163de6a4`；台账 `73522bc3`（18 文件 0 漂移、31 s×2 identical、`land_p1.py e39636c2`）；同代 `reg_old/reg_new`：`RED 13771a2d`（三同）、`GREEN 52fc03d4`（old=new；vs signed 仅 naming 45/50）、`PLAN-SELFTEST` old/new 仅差 `modules.evict_policy.py`；签名 `d3485eb2`/`a0c0782b` 的 `modules/planner.py=4162661c`；现 `planner.py 01507f6b`（19:40:56）；未动 `plan.py 74da0732`、`m3_lease 33ae679a`、`chat_lease 619a0432`、`chat.db 237d8e1f`、`freeze_check 6016085a`（FROZEN/exit 0）。