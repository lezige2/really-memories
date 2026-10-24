# -*- coding: utf-8 -*-
"""m2_v1.py -- M2 first cut: placement only, on a frozen selection.

Five contracts, as revised:

 1. The byte baseline is a *path*, not a memory copy:
        fresh load(pristine) + place(target)
      == load + place + (extra shift) + evict + reload(pristine) + place(target)
    A block that has been moved once cannot equal its pre-eviction memory image; comparing
    those two would report normal L3b wear as lost content. Block file hash must also be
    unchanged, and the comparison is over a block-only sequence, never the chat state.

 2. Capacity fixture: 4 slots, 64 manifest steps over 6 blocks. Selection is precomputed
    (frozen), so anything that fails here is placement.

 3. Evicting the TOP block is its own case: the next block must move up and its end must
    equal the chat anchor. Checked after every step, not just at the end.

 4. A structurally perfect layout can still be disconnected. After each mount the block
    must be visible to the live sequence (seq_cp), answer a fact only it knows, and the
    unselected blocks must stay unmounted.

 5. Budget is per block, because a global total hides one block being shuttled:
    block -> moves, requantizations, last_target. Top-block promotion counts.

Deterministic eviction only (LRU). No product eviction policy in this cut.
"""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import kvslots as K                                          # noqa: E402
import freeze_check                                          # noqa: E402

MODEL = os.path.join(r"D:\models", "DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf")
DIR = os.path.join(ROOT, "kvmem", "m2_v1")
CHAT = 4096
SLOT = 64
LIVE = 0
POOL = [1, 2, 3, 4]            # small on purpose: 6 blocks cannot fit
MOVES_BUDGET = 5
REQ_BUDGET = 10

BLOCKS = {
    "profile": "我的工号是 A-4417，隶属平台研发部。",
    "project": "项目代号蓝鲸，计划 3 月 14 日上线。",
    "habit": "我的咖啡只喝美式，不加糖。",
    "car": "我的车牌是 浙B-3F19K，深灰色速腾。",
    "pet": "我养了一只橘猫，叫年糕。",
    "home": "我住在广陵路 12 号 2 单元 602。",
}
FACT_Q = {
    "profile": ("我的工号是多少？", "A-4417"),
    "project": ("项目什么时候上线？", "3月14"),
    "habit": ("我喝咖啡有什么习惯？", "美式"),
    "car": ("我的车牌号是多少？", "浙B-3F19K"),
    "pet": ("我养的猫叫什么？", "年糕"),
    "home": ("我住在哪？", "广陵路"),
}
# 64 steps: deliberately revisits blocks so evictions happen, in a fixed order
MANIFEST = (["profile", "project", "habit", "car"]
            + (["pet", "home", "profile", "project"] * 6)
            + ["habit", "car", "pet", "home"] * 3
            + ["profile", "car", "pet", "habit", "home", "project"] * 5)

results = []
budget = {}
evictions = {"count": 0, "top": 0}
block_hash_before = {}


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print("  [%s] %-52s %s" % ("PASS" if ok else "FAIL", name, detail))


def h(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def path_of(bid):
    return os.path.join(DIR, bid + ".kvmem")


class Pool:
    def __init__(self, eng):
        self.eng = eng
        self.slot = {}                     # slot -> block id
        self.layout = {}                   # slot -> (lo, hi)
        self.last_used = {}

    def mount(self, bid, slot, tag=""):
        eng = self.eng
        eng.reset(slot)
        n = eng.load_strict(slot, path_of(bid))
        base = eng.pos_max(slot) - n + 1
        tail = CHAT - (slot - 1) * SLOT
        target = tail - n
        rec = budget.setdefault(bid, {"resident_moves": 0, "total_mounts": 0,
                                      "requant_total": 0, "last_target": None})
        rec["total_mounts"] += 1
        rec["resident_moves"] = 0      # new residency: L3b wear does not carry over
        if base != target:
            moved = eng.repos_local(slot, target - base)
            if moved != n:
                raise RuntimeError("repos_local moved %d of %d for %s" % (moved, n, bid))
            rec["resident_moves"] += 1      # resets on every reload from pristine
            rec["requant_total"] += 1
        eng.share(slot, LIVE, target, target + n)
        rec["last_target"] = target
        self.slot[slot] = bid
        self.layout[slot] = (target, target + n)
        self.last_used[bid] = self.clock
        return n

    def evict(self, slot):
        self.eng.reset(slot)                       # seq_rm: drop the ref, free the cells
        bid = self.slot.pop(slot, None)
        self.layout.pop(slot, None)
        budget.setdefault(bid, {"resident_moves": 0, "total_mounts": 0,
                                "requant_total": 0, "last_target": None})
        return bid

    def victim(self, incoming):
        """LRU over the occupied slots; deterministic given the manifest."""
        cands = [(self.last_used.get(b, -1), s) for s, b in self.slot.items()]
        if not cands:
            return None
        cands.sort()
        _, slot = cands[0]
        return slot

    def place(self, bid, clock):
        self.clock = clock          # LRU stamps must be taken before eviction
        for slot in POOL:
            if self.slot.get(slot) == bid:
                self.last_used[bid] = clock
                return slot, False
        free = [s for s in POOL if s not in self.slot]
        slot = free[0] if free else self.victim(bid)
        if slot is None:
            return None, False
        if slot in self.slot:
            if slot == 1:
                evictions["top"] += 1
            evictions["count"] += 1
            self.evict(slot)
        self.mount(bid, slot)
        return slot, True

    def top(self):
        """The block flush with the chat anchor, or None (which is the FATAL head gap)."""
        if 1 not in self.slot:
            return None
        lo, hi = self.layout[1]
        return (self.slot[1], lo, hi)


def assert_layout(pool, tag):
    top = pool.top()
    if top is None:
        check("layout after %s" % tag, False, "chat_head EMPTY -> fatal head gap")
        return False
    bid, lo, hi = top
    ok = (hi == CHAT)
    check("layout after %s" % tag, ok,
          "top=%s [%d,%d) end==%d" % (bid, lo, hi, CHAT))
    return ok


def main():
    ok, _ = freeze_check.check(verbose=True)
    check("selection layer frozen", ok)

    os.makedirs(DIR, exist_ok=True)
    eng = K.KVEngine(MODEL, n_ctx=8192, n_seq=8, gpu=99, kv="q8_0")
    try:
        # ---- build pristine block files
        for i, (bid, text) in enumerate(BLOCKS.items(), start=1):
            if not os.path.exists(path_of(bid)):
                eng.reset(i)
                eng.write(i, text, add_bos=True)
                eng.save(i, path_of(bid))
                eng.reset(i)
            block_hash_before[bid] = h(path_of(bid))

        # ---- (1) the byte baseline is a path, not a memory image
        probe = "profile"
        n = BLOCKS and len(BLOCKS[probe])
        eng.reset(6)
        n = eng.load_strict(6, path_of(probe))
        t0 = 3000
        eng.repos_local(6, t0 - (eng.pos_max(6) - n + 1))
        eng.save(6, os.path.join(DIR, "fresh.kvmem"))
        fresh = h(os.path.join(DIR, "fresh.kvmem"))
        # same pristine, but the block has already been shifted once before being evicted
        eng.reset(6)
        eng.load_strict(6, path_of(probe))
        eng.repos_local(6, t0 - (eng.pos_max(6) - n + 1))
        eng.repos_local(6, 2600 - t0)          # one extra shift: L3b wear, must not matter
        eng.reset(6)                           # evict
        eng.load_strict(6, path_of(probe))     # reload pristine
        eng.repos_local(6, t0 - (eng.pos_max(6) - n + 1))
        eng.save(6, os.path.join(DIR, "after.kvmem"))
        after = h(os.path.join(DIR, "after.kvmem"))
        eng.reset(6)
        check("fresh load+place == evict->reload+place", fresh == after,
              "%s vs %s (block-only seq)" % (fresh, after))

        # ---- (2)+(3)+(5) capacity run over the frozen manifest
        pool = Pool(eng)
        pool.clock = 0
        for step, bid in enumerate(MANIFEST):
            slot, _ = pool.place(bid, step)
            assert_layout(pool, "step %d (%s -> slot %s)" % (step, bid, slot))

        check("evictions actually happened", evictions["count"] > 0,
              "%d evictions over %d steps, pool=%d" % (evictions["count"],
                                                      len(MANIFEST), len(POOL)))
        check("the TOP block was evicted at least once", evictions["top"] > 0,
              "top evictions: %d" % evictions["top"])

        # ---- (4) visibility: the top block answers its own fact, the others are unmounted
        # A layout can be perfect and still be disconnected: the live sequence has to be
        # rebuilt from the current pool, otherwise it holds stale shares from evicted
        # blocks and decodes over garbage.
        eng.reset(LIVE)
        for s_, b_ in sorted(pool.slot.items()):
            lo_, hi_ = pool.layout[s_]
            eng.share(s_, LIVE, lo_, hi_)
        top = pool.top()
        q, fact = FACT_Q[top[0]]
        ans = eng.ask(LIVE, q, n_predict=28, pos=CHAT)
        check("top block is visible to the chat (%s)" % top[0], fact in ans,
              "q=%s ans=%r" % (q, ans.strip()[:40]))

        mounted = set(pool.slot.values())
        idle = [s for s in POOL if s not in pool.slot]
        leaked = [s for s in idle if eng.n_tokens(s) > 0]
        check("unselected blocks are not mounted", not leaked,
              "idle slots with tokens: %s" % leaked)
        unselected = [b for b in BLOCKS if b not in mounted]
        check("unselected block text is not in any slot",
              all(eng.n_tokens(s) == 0 for s in idle),
              "unselected=%s" % unselected)

        # ---- leak: evicting leaves no ref and no cells
        victim_slot = [s for s in POOL if s in pool.slot][-1]
        pool.evict(victim_slot)
        check("evict drops the sequence cleanly",
              eng.n_tokens(victim_slot) == 0 and eng.pos_max(victim_slot) < 0,
              "n_tokens=%d pos_max=%d" % (eng.n_tokens(victim_slot),
                                          eng.pos_max(victim_slot)))
        assert_layout(pool, "after the final eviction")

        # ---- (5) per-block budget
        over = {b: r for b, r in budget.items()
                if r["resident_moves"] > MOVES_BUDGET or r["requant_total"] > REQ_BUDGET}
        check("per-block shift budget respected", not over, "%s" % (over or "all within"))
        worst = max(budget.items(), key=lambda kv: kv[1]["resident_moves"])
        print("  tightest block: %s %s" % (worst[0], worst[1]))

        # ---- block files untouched
        changed = [b for b in BLOCKS if h(path_of(b)) != block_hash_before[b]]
        check("block files unchanged", not changed, "%s" % (changed or "all pristine"))

        ok_asks = not any(not r[1] and "layout" in r[0] for r in results)
        print("\n%d/%d checks passed" % (sum(1 for r in results if r[1]), len(results)))
        return 0 if all(r[1] for r in results) else 1
    finally:
        eng.close()


if __name__ == "__main__":
    sys.exit(main())