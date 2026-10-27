# M2 完整 · L2 定稿（lead · 2026-10-25 20:40 本地）

> 预登记 `docs/_work/M2-FULL-PREREG-draft.md` `c2afd97aad278ade` §2.2 · 独立复核 `docs/_work/INSPECTOR-L2-REVIEW.md` `dbb8cda373406136`
> 交付：`kvmem/m2_visibility/m3/m3_lease.py` `675f983f8d02f1df → 37a0a6f4b8ea1154 → 33ae679a50d58c93`（9,047 B，两处改动：`__init__` 建 `unbooked_count=0`、`detach` 未命中先记账后抛且不 drop；补正只改 docstring）

---

## 0 一句话

**L2（`detach` 未命中记账一致性）= 通过**：改前「未命中仍 `eng.drop`」是**静默丢引用**；落地后未命中**先记账（`unbooked_count` +1、`unbooked_detach` 事件）→ strict 抛 `LeaseError` → 不 drop**，主床 `drop_calls_total` **5 → 2**。**关键的假绿抓手是 `drop_delta_on_unbooked`**（只测被拒那次调用的 drop 增量）：改前 U 例全 **1**、落地后全 **0** —— "先 drop 再 raise"在每个 U 例上都被堵死，不靠例内总量侧证（U3 总量为 1 是因为它前面有一次**合法** detach）。

## 1 读数（两套分母并列，**不合并**）

| 床 | 改前 | 落地后 |
|---|---|---|
| 主床 4 例（H1 + U1/U2/U3） | `out/M3-L2-pre-v2.json` `428f4cfe3f9011da`：分母 `4/1/3`、observed unbooked **0**、`drop_calls_total=5`、红 H1（缺属性）+U1–U3 | `out/M3-L2-after-v2.json` `e68df9a404c5fadc`：`4/1/3`、observed **3**、`drop_calls_total=2`、`fail=[]`、exit 0 |
| 扩展床 5 例（+ U4 非 strict 未命中） | 同上 + U4 | `5/1/4`、`drop_calls_total=3` |
| **`drop_delta_on_unbooked`** | U 例全 **1** | **H1=1、U1=U2=U3=0、U4=1** |

**变体隔离（两套，各司其职）**：
- `variant_b`（模块 `4694db4c1011056c`，产物 `b20a03d8246fdd23`）= **落地版只删未命中检测+抛错分支、保留 `strict` 形参与 `unbooked_count` 初始化** ⇒ **H1 绿 + U1–U4 红**。这才是"承重的是未命中分支本身"。
- `variant_rollback`（模块 `675f983f`，产物 `b5e73ae256b07008`）= 整体回退到 L1 版 ⇒ 5/5 红，**其中 H1 红是"缺 `unbooked_count` 属性"，不作命中路径证据**（命中路径由 `variant_b` + after + 复核方独立 H1–H3 三处支撑）。原 `out/M3-L2-variant.json` `0658aa48` 保留未删。

## 2 非 strict 分支（我裁"保留 + 补测"）

`strict=False` = **记账与事件不关、只关 raise**（写进类 docstring）。专例 N1/N2 核过：未命中 ⇒ `unbooked_count` +1、`unbooked_detach` 事件落、**`eng.drop` 照旧 1 次**、不抛；默认构造仍 `strict=True`、`unbooked_count==0`。⇒ **不是"关判据开关"**（判据的可观测面仍在，只有 throw 降级），符合 §2.2「strict 模式（默认 strict）抛」的字面。

## 3 未动项 / 回归

| 项 | 值 |
|---|---|
| `tools/chat_lease.py` | **`619a043215035de7`**，文本 invariants 快照 diff 空；独立 GuardedLeases 测试：命中路径不变、未命中经 guard **LeaseError 照抛不被吞**、既有 **reset 拒绝语义不变**（refused +1、drop 0） |
| L1 回归 | `out/M3-L1-recheck-after-L2-v2.json` `383516da95ecf92f`：**11/11**、拒绝 4、真命中 4 |
| `m3/_test_lease.py` | `d2ddc6b69249dab6`（未改）、现跑 **0 failed** |
| `freeze_check` | **FROZEN / exit 0** |
| `tools/chat.py` / `chat.db` / `m2_planner/` / 冻结三件 | `cb70be52` / `237d8e1f` / 未动 |
| 台账 | `m3/LANDED-l2.json` `467e0b3f31cd3ff2`（12 文件 0 漂移、两采样 31 s 一致；`addendum.original` 保留首批读数 `550faba2…`）；`land_l2.py` `b4e0d0fbec427d7f` 入账；`_before@675f983f` 与复核方 **20:24:15 先于施工**的快照**逐字节相等** |
| **G1 闭环** | 本次 `_before@37a0a6f4` mtime 20:28:36**早于**终版 20:28:41 ⇒ **先副本再改做到了** |

## 4 四态 + 不可签

| 项 | 判 |
|---|---|
| L2 零 GPU 判据层（未命中记账 + strict 不 drop + 变体隔离 + 非 strict 边界 + L1 不破） | **通过（本判决签署）** |
| 真机 / 产品路径重跑 | **未做**（本刀零 GPU；不可签"产品读数不变"） |
| `unbooked_detach` 只在 `BlockLeases.events`、不进 `chat_lease` 的 `EVENT_LOG/sites` | **范围外 note**：M4-C 断言不依赖它；但**行为确有变化** —— 经包装层的未命中 detach 由"静默 drop + 旧 `detach(block_seq=None)` 事件"变成"抛 `LeaseError`" |
| 工具默认输出写仓库 | **已修**（两床默认落系统临时目录，写 `out/` 须显式 `--out`；复核方实证仓库前后无新增） |
| 不可签 | ①「产品路径/真机读数不变」（未重跑）②「`unbooked_detach` 进了产品事件流」（没有，范围外）③「rollback 的 H1 红可作命中证据」（不可）④「`strict=False` 产品调用面已审计」（产品不用它） |

## 5 记入下游的产品风险 note（**P1/S1 与将来重跑 14B 必读**）

L2 把"未命中 detach"从**静默**改成**抛错**。产品路径 `chat.py:561/:593` 都是已知状态下的 detach，理论上不命中；但**若租约表出现记账漂移**，`chat` 现在会**抛 `LeaseError`** 而不是静默降级。这条必须是"响"（否则 L1/L2 都白做），但要写进预案：**任何 14B/M4-C 绿臂重跑，若出现新的 `LeaseError`，第一件事查 `unbooked_count`**，不许用修断言或吞异常的方式"恢复绿"。

## 6 签署

| 项 | 内容 |
|---|---|
| 签署人 | lead |
| 签署 | **L2 `detach` 未命中记账一致性：通过**（2026-10-25）—— 改前 U 例静默 drop（`drop_delta_on_unbooked` 全 1）→ 落地后全 0、`drop_calls_total` 5→2、`variant_b` H1 绿 + U1–U4 红、非 strict 只降级 raise、`chat_lease.py` 未动且 reset 拒绝语义不变、L1 11/11、`freeze_check` FROZEN |
| 可复算 | 产物 ⇐ `428f4cfe3f9011da` / `e68df9a404c5fadc` / `b20a03d8246fdd23` / `b5e73ae256b07008` / `383516da95ecf92f`；台账 ⇐ `467e0b3f31cd3ff2`；复核 ⇐ `dbb8cda373406136`；预登记 ⇐ `c2afd97aad278ade` |
| 下一步 | **P1 pinned 驱逐**（零 GPU；`evict_policy.select_to_evict(..., pinned=())`，全 pinned 超预算必须 `PlanRefused` 不许静默降级）→ 然后 **S1**（前置 P-1/P-2 已写进预登记 §2.4/§3） |