# M2 完整 · P1 定稿（lead · 2026-10-25 21:10 本地）

> 预登记 `docs/_work/M2-FULL-PREREG-draft.md` `c2afd97aad278ade` §2.3 · 独立复核 `docs/_work/INSPECTOR-P1-REVIEW.md` `607fcd7c7d09d660`
> 交付：`kvmem/m2_visibility/m2_planner/evict_policy.py` `aa7cbf3f86df30f8（3,468 B）→ c2a8d8cbb5b0d4e3（6,030 B）`

---

## 0 一句话

**P1（pinned 驱逐）= 通过**：`select_to_evict(..., pinned=())` 新增**关键字**、缺省空集 ⇒ 既有行为逐字段不变；混合集**只踢普通块、pinned 一个不动**；**全 pinned 且超预算 ⇒ 必须响**（`evicted=[]`、`over_budget_after=True`、`refused_reason="all_pinned"`），调用方 `PlanRefused`，**不许静默降级**。`pin` 的来源按裁定 (ii) = **调用方显式注入**（`pinned_from_leases`，duck-typed，不看引擎）。

## 1 读数（三级分母 `13 / 6 / 1`）

| 产物 | 分母 | 结果 |
|---|---|---|
| `out/P1-pre.json` `9d5df8c3acd2c355` | `13/6/0` | 红 4 例（H1 helper 不存在 / H2 契约 / M1 / A1，现盘无 `pinned` 形参 ⇒ `TypeError`），exit 2 |
| `out/P1-after.json` `495a54de8fabb607` | `13/6/1` | **5/5 绿**、`fail=[]`、exit 0 |
| `out/P1-variant-no-filter.json` `22d96d19c6cee471` | `13/6/2` | 红 **M1+A1**：M1 `evicted=[7]` ⇒ `evicted∩pinned=[7]`（pinned 被踢） |
| `out/P1-variant-allpinned-silent.json` `b70cef0e9826b797` | `13/6/1` | 红 **只 A1**：`over_after=False`、`refused_reason=None`、`caller_action="proceed"`；M1 仍绿 ⇒ 红点精确 |
| `out/P1-regression.json` `02b1e9bc9bfa87a4` | — | 三份回归三层对照 |

**两例完整输出**：M1（3 pinned + 3 普通、超预算）`{kept:[1,3,2,5,7], evicted:[4], evicted∩pinned:[], over_after:False, refused_reason:null}`；A1（全 pinned）`{kept:[2,5,7], evicted:[], over_before:True, over_after:True, refused_reason:"all_pinned", caller_action:"PlanRefused"}`。

## 2 判据 ③ 的口径变更（必须留痕）

预登记原句要求"输出与现盘**逐字段相同**"。**该要求已作废**：三份签名回归产物（`RED-SUITE`/`GREEN-SUITE` mtime 19:06:41、`PLAN-SELFTEST` 19:11:22）早于其背书对象 —— `planner.py 01507f6b` 是 19:40:56 的 r2 D1 修复，**"逐字节相同"在物理上不可能成立**。
⇒ 判据 ③ 改为**同代对照**：**旧 `evict_policy aa7cbf3f` vs 新 `c2a8d8cb`，跑在同一个现 `planner.py 01507f6b` 上**，输出必须逐字段相同。复核方自建 `reg_old/`+`reg_new/` 两镜像独立跑过：`RED` old=new=签名 `13771a2d`；`GREEN` old=new=`52fc03d4` 且**旧模块同样差**那句 `naming`；`PLAN-SELFTEST` old vs new 仅差 `/modules/evict_policy.py`；三层残留 `[]`。⇒ **P1 未污染默认路径**，且"既有漂移"被独立复现（非 P1 造成）。

**证据代差已补**（另见 `M2-ACCEPT-lead.md §8`）：重生成 `RED-SUITE-regen 13771a2d`（**与原产物逐字节相同**）/ `GREEN-SUITE-regen 52fc03d4` / `PLAN-SELFTEST-regen 0003eb0b`，台账 `LANDED-m2planner-regen.json 5a3ea953`（`supersedes: null`，原产物未动）；现码读数 **9/9 按设计红 + 18 断言/4 契约全绿 + 12/12 与 3 必红**，**真行为差异 = 0**。**缺口 G2**：旧 GREEN 产物 `naming` 写死 `(=45)` 而同条 `cells_moving=50`（与 D1 同类），不可回改。

## 3 契约（裁定 (ii) 落地）

- `pinned_from_leases(leases, n_seq) = {s ∈ range(1,n_seq) | leases.leased(s)}`；**duck-typed**：只认 `.leased()`；无该属性 ⇒ **显式 `TypeError`**；属性存在但不可调用（`leased=5`）⇒ 也 `TypeError`；空集合法（`n_seq=1`）。
- docstring 写死：**pin 的对象是「被引用」，不是「重要」**；规划器/策略不得看引擎推断。
- `plan(blocks, chat_start, budget)` 3 参 / `evict_order` 纯排序不接 pinned / `DEFAULT_POLICY="off"` / 主路径不 import（唯一 import 仍 `selftest_plan.py:22`）/ 无新阈值（`mount_cap=None` 不启用）—— 逐项复核未动。

## 4 四态 + 不可签

| 项 | 判 |
|---|---|
| P1 零 GPU 判据层（混合集过滤 + 全 pinned 必响 + 两条变体 + 同代对照 + duck-typed 契约） | **通过（本判决签署）** |
| P1 接主路径 / 真实对话里生效 | **未做**（预登记明确"淘汰默认 off、不接主路径"是**非目标**，不是缺口） |
| 台账 | `LANDED-p1.json 73522bc3cb69967b`：18 文件 0 漂移、两采样 31 s 一致、`land_p1.py e39636c2` 入 `tooling`、`_before@aa7cbf3f` mtime 20:41:17 **早于**新模块 20:42:11 ⇒ **先副本再改成立（G1 规程第二次闭环）** |
| 不可签 | ①「P1 在真实对话里生效」（非目标）②「`_before` 有第三方字节交叉」（该文件不在 `git HEAD`，只有 mtime 顺序 + 台账；后续 pre 副本另存 temp ≈ 复核方做法）③「台账记了变体模块 sha」（只记产物，复核方现算 `d8821fd7`/`163de6a4` 建议补入）④「`PLAN-SELFTEST` regen sha 恒定」（含 `at`，每次跑不同：executor `83ec7645` vs 复核方 `6097f6f5`，只差 `at`） |

## 5 签署

| 项 | 内容 |
|---|---|
| 签署人 | lead |
| 签署 | **P1 pinned 驱逐：通过**（2026-10-25）—— 改前 4 例红 → 落地 5/5、分母 `13/6/1`；混合集只踢普通块、全 pinned 超预算 `refused_reason="all_pinned"` + `PlanRefused`；两条变体红点精确；同代对照三层残留 `[]`（判据 ③ 口径变更已留痕）；duck-typed 契约不空集冒充；`plan()`/`evict_order`/`DEFAULT_POLICY`/主路径 import 均未动；跨批守门（L1 11/11、L2 5/5、`freeze_check` FROZEN）全绿 |
| 可复算 | 产物 ⇐ `9d5df8c3acd2c355` / `495a54de8fabb607` / `22d96d19c6cee471` / `b70cef0e9826b797` / `02b1e9bc9bfa87a4`；台账 ⇐ `73522bc3cb69967b`；复核 ⇐ `607fcd7c7d09d660`；预登记 ⇐ `c2afd97aad278ade`；证据代差 ⇐ `LANDED-m2planner-regen.json 5a3ea9533d2c5fc0` |
| 下一步 | **S1 多序列**（唯一必须 14B 的一件；前置 P-1/P-2 已入预登记 §2.4/§3，预算裁定 B、N≤20 需在跑前冻结） |