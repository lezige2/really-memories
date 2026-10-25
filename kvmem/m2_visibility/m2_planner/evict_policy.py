# -*- coding: utf-8 -*-
"""淘汰策略 —— **独立模块，默认 `off`，不接进 `plan()` 主路径**。

为什么默认 off（三条，都必须一起读）：

1. 签字版把淘汰列为**非目标**：`RESULTS-RED.md:150`（§7 未做/明确不做）与 `M2-PLAN.md` §4。
2. 签字版 S2↔S6 的**结构耦合**论证以「无淘汰」为前提：`RESULTS-RED.md:94` / `:170` ——
   「在『无淘汰』前提下，预算越界必然伴随拒绝义务 ⇒ S2 的红必然伴随 S6 的红」。
   **一旦主路径开始踢块，这条论证的前提就不成立**，S2/S6 的读数要重新解释。
3. 挂载块上限（≈4000）这一档**已删除**（`RESULTS-RED.md:143`：「已删除（无确切值/无出处）」），
   所以本模块**不发明任何阈值**；要不要踢、踢到多少，由**调用方给数**。

启用契约（显式，不许默认开）：`evict_order(blocks, policy="lru")`。
返回**被踢块的顺序**（先踢第一个）；调用方对它做 `seq_rm`（文件不动 —— 退役只摘引用）。
`policy="off"` 永远返回 `[]`，即「一个都不踢」，此时超预算的正确行为仍是**拒绝**（不降级）。

排序规则（policy="lru"）：
  ① `last_used` 小的先踢（LRU；缺省 `last_used=0` ⇒ 视为最旧）；
  ② 平手时 `key` **大**的先踢（`distance_key` 越大越不相关 = 离对话越远）；
  ③ 再平手 `seq` 大的先踢（只为了让顺序确定，不代表语义）。
"""

DEFAULT_POLICY = "off"
POLICIES = ("off", "lru")


def _sort_key(b):
    return (int(b.get("last_used", 0)), -int(b.get("key", 0)), -int(b["seq"]))


def evict_order(blocks, policy=None):
    """返回**按淘汰先后**排好的 seq 列表；`off` ⇒ `[]`。纯函数。"""
    pol = policy or DEFAULT_POLICY
    if pol not in POLICIES:
        raise ValueError("unknown eviction policy: %r（可选 %r）" % (pol, list(POLICIES)))
    if pol == "off":
        return []
    return [int(b["seq"]) for b in sorted(blocks, key=_sort_key)]


def pinned_from_leases(leases, n_seq):
    """从**租约表**取 pin 集合：`{s for s in range(1, n_seq) if leases.leased(s)}`。

    契约（写死，别外推）：**pin 的对象是「被引用」，不是「重要」**。本 helper 只回答
    「谁还被引用着」（租约表的语义），不回答「谁该留」；重要性排序/阈值判定都不在这里，
    也不许本模块自己去看引擎或 `chat.py` 推断 —— 那样就把「谁被引用」和「谁重要」混成一个词了。

    入参是 **duck-typed** 的：只要对象有可调用的 `.leased(seq)`（`m3_lease.BlockLeases.leased`
    就是这个语义，`GuardedLeases` 继承）。**不 import 引擎、零 GPU**。对象没有 `.leased()`
    时**显式 `TypeError`** —— 不许静默返回空集冒充「没有 pinned」（那会把「未接上」伪装成绿）。
    """
    getter = getattr(leases, "leased", None)
    if not callable(getter):
        raise TypeError(
            "pinned_from_leases() 需要带 .leased(seq) 的租约对象（duck-typed），收到 %r；"
            "拿不到租约表时正确读数是「未接上」，不是空 pinned。"
            % (type(leases).__name__,))
    return {int(s) for s in range(1, int(n_seq)) if getter(int(s))}


def select_to_evict(blocks, chat_len, n_ctx, policy=None, mount_cap=None, pinned=()):
    """按预算踢到装得下；**不发明阈值**：`mount_cap=None` 表示不启用这一档。

    `pinned` = 调用方**显式注入**的不可踢 seq 集合（来源见 `pinned_from_leases`，契约同：
    pin = 被引用，不是重要）。缺省空集 ⇒ 输出与 P1 之前**逐字段相同**（连键都不多）。

    返回 `{"policy", "kept", "evicted", "over_budget_before", "over_budget_after"}`；
    `pinned` 非空时另加 `pinned` / `refused_reason` / `pinned_skipped` 三个键：
    - 过滤只在**本函数**里做（`evict_order` 保持纯排序语义，不接 pinned）；
    - 混合集：pinned 一个都不许踢，先踢普通块；
    - **全 pinned + 超预算**：`evicted == []`、`over_budget_after == True`、
      `refused_reason == "all_pinned"` ⇒ 调用方必须 `PlanRefused`，**不许静默降级继续**。
    - `policy="off"` 时 `evicted=[]`；若 `over_budget_after` 仍为 True，正确动作仍是拒绝。
    """
    pol = policy or DEFAULT_POLICY
    pin = {int(s) for s in (pinned or ())}
    cap = None if mount_cap is None else int(mount_cap)
    order = evict_order(blocks, pol)
    if pin:                                        # 过滤只做在这里；evict_order 不动
        pinned_skipped = [s for s in order if s in pin]
        order = [s for s in order if s not in pin]
    else:
        pinned_skipped = []

    def _over(bs):
        cells = sum(int(b["cells"]) for b in bs)
        over_ctx = cells + int(chat_len) > int(n_ctx)
        over_cap = (cap is not None) and (cells > cap)
        return bool(over_ctx or over_cap)

    kept = list(blocks)
    evicted = []
    over_before = _over(kept)
    for seq in order:
        if not _over(kept):
            break
        kept = [b for b in kept if int(b["seq"]) != seq]
        evicted.append(seq)
    over_after = _over(kept)
    base = {"policy": pol, "kept": kept, "evicted": evicted,
            "over_budget_before": over_before, "over_budget_after": over_after,
            "mount_cap_used": cap,
            "note": "evicted 里的块只做 seq_rm（摘引用），磁盘文件不动；"
                    "over_budget_before/after 两读数都必须报，不许只报一个。"}
    if not pin:
        return base
    blocked_all = bool(kept) and over_after and all(int(b["seq"]) in pin for b in kept)
    return dict(base, pinned=sorted(pin),
                refused_reason="all_pinned" if blocked_all else None,
                pinned_skipped=pinned_skipped,
                pinned_note="pinned = 调用方注入的「被引用」集合；不许本模块自己推断")