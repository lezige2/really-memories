# -*- coding: utf-8 -*-
"""m2_probe_segments.py -- segment-wise questions, the one experiment that bisects
"only one segment is attended" vs "4 segments degrade decode".

Each question gets a clean chat sequence: reset(LIVE) then re-share the same segments, so no
generated token from the previous probe can contaminate the next.

Recorded per segment: id, add_order, position range, answer.
Also: add order reversed (to separate "lowest position" from "added last"), and two cell-count
variants (4x5 cells vs 3x30 cells) to separate "segment count" from "total cell count".
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import kvslots as K                                          # noqa: E402

MODEL = os.path.join(r"D:\models", "DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf")
CHAT, SLOT, LIVE = 4096, 64, 0

SEG = [
    ("home", "我住在广陵路 12 号 2 单元 602。", "我住在哪？", "广陵路"),
    ("project", "项目代号蓝鲸，计划 3 月 14 日上线。", "项目什么时候上线？", "3月14"),
    ("habit", "我的咖啡只喝美式，不加糖。", "我喝咖啡有什么习惯？", "美式"),
    ("car", "我的车牌是 浙B-3F19K，深灰色速腾。", "我的车牌号是多少？", "浙B-3F19K"),
]


def main():
    eng = K.KVEngine(MODEL, n_ctx=8192, n_seq=8, gpu=99, kv="q8_0")

    def build(order, texts=None):
        """Mount segments in `order` (indexes into SEG) at B-right slot targets."""
        for s in range(8):
            eng.reset(s)
        laid = []
        for slot, idx in enumerate(order, start=1):
            bid, text, _q, _f = SEG[idx]
            eng.reset(slot)
            eng.write(slot, (texts or {}).get(bid, text), add_bos=True)
            n = eng.pos_max(slot) + 1
            tgt = CHAT - (slot - 1) * SLOT - n
            eng.repos_local(slot, tgt - (eng.pos_max(slot) - n + 1))
            laid.append((bid, slot, tgt, tgt + n))
        return laid

    def ask_clean(laid, q, n_predict=16):
        eng.reset(LIVE)
        for _bid, slot, lo, hi in laid:
            eng.share(slot, LIVE, lo, hi)
        return eng.ask(LIVE, q, n_predict=n_predict, pos=CHAT).strip()

    try:
        order = [0, 1, 2, 3]
        laid = build(order)
        print("forward order (segment, add_order, [lo,hi), answer):")
        for bid, slot, lo, hi in laid:
            idx = [i for i, s in enumerate(SEG) if s[0] == bid][0]
            _b, _t, q, fact = SEG[idx]
            ans = ask_clean(laid, q)
            print("  %-8s add=%-2d [%d,%d) %s %r"
                  % (bid, slot, lo, hi, "OK" if fact in ans else "MISS", ans[:30]))

        rev = [3, 2, 1, 0]
        laid_r = build(rev)
        print("reversed add order (home added LAST, still highest position):")
        for bid, slot, lo, hi in laid_r:
            idx = [i for i, s in enumerate(SEG) if s[0] == bid][0]
            _b, _t, q, fact = SEG[idx]
            ans = ask_clean(laid_r, q)
            print("  %-8s add=%-2d [%d,%d) %s %r"
                  % (bid, slot, lo, hi, "OK" if fact in ans else "MISS", ans[:30]))

        # ---- cell-count variants: 4 x ~5 cells vs 3 x ~30 cells
        tiny = {"project": "蓝鲸。", "habit": "美式。", "car": "浙B。"}
        laid_t = build(order, texts=tiny)
        ans = ask_clean(laid_t, "我住在哪？")
        tot = sum(hi - lo for _b, _s, lo, hi in laid_t)
        print("4 segments, tiny others (total %d cells): %s %r"
              % (tot, "OK" if "广陵路" in ans else "MISS", ans[:30]))

        filler = "项目代号蓝鲸，计划 3 月 14 日上线，目前处于联调阶段，每周同步一次进度。"
        laid_b = build([0, 1], texts={"project": filler})
        eng.reset(3)
        eng.write(3, filler, add_bos=True)
        n = eng.pos_max(3) + 1
        tgt = CHAT - 2 * SLOT - n
        eng.repos_local(3, tgt - (eng.pos_max(3) - n + 1))
        laid_b.append(("habit", 3, tgt, tgt + n))
        tot = sum(hi - lo for _b, _s, lo, hi in laid_b)
        ans = ask_clean(laid_b, "我住在哪？")
        print("3 segments, %d cells total: %s %r"
              % (tot, "OK" if "广陵路" in ans else "MISS", ans[:30]))

        # ---- text control at the same four positions
        for s in range(8):
            eng.reset(s)
        pos = []
        for bid, slot, lo, hi in laid:
            pass
        eng.reset(LIVE)
        for bid, slot, lo, hi in laid:
            text = [t for b, t, _q, _f in SEG if b == bid][0]
            eng.write_at(LIVE, text, lo, add_bos=(lo == 0))
        ans = eng.ask(LIVE, "我住在哪？", n_predict=16, pos=CHAT).strip()
        print("text control at the same [lo,hi) positions: %s %r"
              % ("OK" if "广陵路" in ans else "MISS", ans[:30]))
        return 0
    finally:
        eng.close()


if __name__ == "__main__":
    sys.exit(main())