"""S1–S6 断言。每条都返回 (ok, detail)；ok=False 即"红"。"""
from kvsim import Sim


def S1_geometry(sim, plan, spec=None):
    """结构不变量：越界 / 重叠 / cells 数。manifest 比对是 S1m，只对真实产物做（模拟器没有 manifest）。"""
    errs = []
    seen = []
    for seq, target_pos in plan:
        b = sim.blocks[seq]
        pos_hi = target_pos
        pos_lo = pos_hi - b["cells"] + 1
        if pos_lo < 0:
            errs.append("seq%d pos_lo<0" % seq)
        if pos_hi >= sim.n_ctx:
            errs.append("seq%d pos_hi>=n_ctx" % seq)
        if pos_hi - pos_lo + 1 != b["cells"]:
            errs.append("seq%d cells mismatch" % seq)
        for s2, lo2, hi2 in seen:
            if not (pos_hi < lo2 or pos_lo > hi2):
                errs.append("seq%d 与 seq%d 区间重叠" % (seq, s2))
        seen.append((seq, pos_lo, pos_hi))
    return (not errs, errs or "ok")


def S2_budget(sim, plan, chat_len, pool_bytes=None):
    """**只有一档**：cell 数 + 对话长度 <= n_ctx。

    bytes 档（sum(cells)*bytes_per_token <= pool_bytes）已删除：池就是整个 KV cache，
    pool_bytes / bytes_per_token = 855638016 / 104448 = 8192 = n_ctx **恰好相等**
    => 「上下文够」与「池够」是同一个约束的两种货币写法（恒真档 => 让预算看起来两档、实际一档）。
    """
    cells = sum(sim.blocks[s]["cells"] for s, _ in plan)
    ok = cells + chat_len <= sim.n_ctx
    det = {"cells": cells, "chat_len": chat_len, "cell_ok": ok,
           "bytes_tier": "已删除（恒真：pool_bytes = n_ctx * bytes_per_token）",
           "mount_cap_tier": "已删除（无确切值）",
           "identity": "%d / %d = %d = n_ctx" % (sim.pool_bytes, sim.bytes_per_token,
                                                 sim.pool_bytes // sim.bytes_per_token)}
    return (ok, det)


def S6_refuse(refused_reason, expect_reason):
    """拒绝义务：**必须抛**，且 **reason 必须对**（否则「拒了但理由错」会被判绿）。"""
    return (refused_reason == expect_reason,
            {"refused": refused_reason, "expected_reason": expect_reason})


def _distance(sim, seq, plan):
    target = dict(plan)[seq]
    return sim.chat_start() - target


def S3a_anchor(sim, plan, keys):
    most = min(keys, key=lambda s: (keys[s], s))
    got = dict(plan)[most]
    want = sim.chat_start() - 1
    return (got == want, {"most_relevant": most, "got_pos_hi": got, "want": want})


def S3b_order(sim, plan, keys):
    most = min(keys, key=lambda s: (keys[s], s))
    rest = [(s, t) for s, t in plan if s != most]
    order = sorted(rest, key=lambda st: (keys[st[0]], st[0]))          # tie-break: (distance_key, seq)
    d = [sim.chat_start() - t for _, t in order]
    mono = all(d[i] <= d[i + 1] for i in range(len(d) - 1))
    return (mono, {"order": [(s, keys[s], dd) for (s, _), dd in zip(order, d)], "monotone": mono})


def S4_no_drag(before, after, involved):
    bad = [s for s in before if s not in involved and before[s] != after[s]]
    return (not bad, {"dragged": bad, "before": before, "after": after})


def S5_bytes(hashA, hashB, involved):
    bad = [s for s in hashA if s not in involved and hashA[s] != hashB.get(s)]
    return (not bad, {"changed": bad, "A": hashA, "B": hashB})
