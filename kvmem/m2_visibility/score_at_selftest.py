# -*- coding: utf-8 -*-
"""kvshim_score_at self-test: acceptance items 2 (determinism), 3 (pieces), 4 (cap bounds).

Runs in one engine against the project block placed in slot 1 ([4078,4096), question at
4096, gap 0). Every measurement wipes LIVE and re-shares the blocks first.

Run: python -X utf8 kvmem/m2_visibility/score_at_selftest.py
"""
import ctypes
import hashlib
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import score_lib as S                     # noqa: E402
import m2_visibility_probe as P           # noqa: E402

OUT = os.path.join(P.WORK_DIR, "evidence", "score_at")
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ROOTTOOLS = os.path.join(os.path.dirname(HERE), "..", "tools")
ANSWER = "3 月 14 日上线"


def bits(values):
    return [struct.pack("<f", v).hex() for v in values]


def main():
    os.makedirs(OUT, exist_ok=True)
    man = S.manifest()
    lay = S.layout([(1, "project", "project", "m2")], man=man)
    prompt = P.K.turn(P.FULL["project"]["q"])
    pos = P.CHAT
    res = {"schema": "score_at_selftest_v1", "answer": ANSWER, "prompt": prompt,
           "geometry": S.segments_text(lay), "checks": {}}

    eng = P.open_engine()
    try:
        P.reset_all(eng)
        placed = S.place(eng, lay)
        res["placed"] = placed
        print("geometry (top-aligned, question at %d):" % pos)
        S.show(lay)
        print("  delta applied: %s" % [(p["id"], p["base"], p["delta"]) for p in placed])

        # ---- acceptance 2 + 3: one call, then the identical call again -------------
        r1 = S.score(eng, lay, placed, prompt, ANSWER, pos)
        r2 = S.score(eng, lay, placed, prompt, ANSWER, pos)
        res["run1"] = r1
        res["run2"] = r2
        print()
        print("[2/3] n=%d rc=%d sum=%.10f mean=%.10f last=%.10f"
              % (r1["n"], r1["rc"], r1["sum"], r1["mean"], r1["last"]))
        print("      %-7s %-8s %-22s %-6s %s" % ("idx", "token", "piece", "rank", "logprob"))
        for i, tok in enumerate(r1["tokens"]):
            print("      %-7d %-8d %-22r %-6d %.10f"
                  % (i, tok, r1["piece_list"][i], r1["ranks"][i],
                     r1["logprobs"][i]))
        print("      pieces joined = %r" % r1["pieces"])

        same = {
            "tokens": r1["tokens"] == r2["tokens"],
            "logprob_bits": bits(r1["logprobs"]) == bits(r2["logprobs"]),
            "ranks": r1["ranks"] == r2["ranks"],
            "sum": r1["sum"] == r2["sum"],
            "mean": r1["mean"] == r2["mean"],
            "last": r1["last"] == r2["last"],
            "pieces": r1["pieces"] == r2["pieces"],
            "rc": r1["rc"] == r2["rc"] and r1["n"] == r2["n"],
        }
        ok2 = all(same.values())
        res["checks"]["determinism"] = {"ok": ok2, "detail": same,
                                        "logprob_bits": bits(r1["logprobs"])}
        print("      determinism (bitwise): %s  %s" % (ok2, same))

        ok3 = (len(r1["piece_list"]) == r1["n"] and all(r1["piece_list"])
               and "".join(r1["piece_list"]) == r1["pieces"])
        res["checks"]["pieces"] = {"ok": ok3, "pieces": r1["pieces"],
                                   "per_token": [{"token": t, "piece": r1["piece_list"][i]}
                                                 for i, t in enumerate(r1["tokens"])]}
        print("      every token has a piece: %s" % ok3)

        # ---- acceptance 4: cap bounds ---------------------------------------------
        rc3 = S.score(eng, lay, placed, prompt, ANSWER, pos, cap=3)
        head = r1["logprobs"][:3]
        trunc_ok = (rc3["rc"] == -3 and rc3["n"] == 3 and rc3["tokens"] == r1["tokens"][:3]
                    and rc3["logprobs"] == head
                    and abs(rc3["sum"] - sum(head)) <= 1e-6)
        print()
        print("[4] cap=3 -> rc=%d n=%d tokens=%s sum=%.10f (full sum=%.10f, first3=%.10f)"
              % (rc3["rc"], rc3["n"], rc3["tokens"], rc3["sum"], r1["sum"], sum(head)))
        res["checks"]["cap_truncation"] = {"ok": bool(trunc_ok), "rc": rc3["rc"], "n": rc3["n"],
                                           "sum": rc3["sum"], "head_logprobs": head}

        # raw-call guards: cap=0, null out pointers, null strings, seq out of range,
        # and a position that would run past the pool.
        f = eng.lib.kvshim_score_at
        vp, ci, cp = ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p
        DP = ctypes.POINTER(ctypes.c_double)
        IP, FP = ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_float)
        f.argtypes = [vp, ci, cp, cp, ci, DP, DP, DP, IP, FP, IP, ci, IP]
        f.restype = ci
        h = ctypes.c_void_p(eng.h)
        d = ctypes.c_double(0.0)
        i4 = ctypes.c_int(0)
        p = prompt.encode("utf-8")
        a = ANSWER.encode("utf-8")
        guards = {}
        guards["cap0"] = f(h, P.LIVE, p, a, pos, ctypes.byref(d), ctypes.byref(d),
                           ctypes.byref(d), None, None, None, 0, ctypes.byref(i4))
        guards["cap_negative"] = f(h, P.LIVE, p, a, pos, ctypes.byref(d), ctypes.byref(d),
                                   ctypes.byref(d), None, None, None, -5, ctypes.byref(i4))
        guards["null_prompt"] = f(h, P.LIVE, None, a, pos, ctypes.byref(d), ctypes.byref(d),
                                  ctypes.byref(d), None, None, None, 8, ctypes.byref(i4))
        guards["null_answer"] = f(h, P.LIVE, p, None, pos, ctypes.byref(d), ctypes.byref(d),
                                  ctypes.byref(d), None, None, None, 8, ctypes.byref(i4))
        guards["seq_out_of_range"] = f(h, 99, p, a, pos, ctypes.byref(d), ctypes.byref(d),
                                       ctypes.byref(d), None, None, None, 8, ctypes.byref(i4))
        guards["past_pool"] = f(h, P.LIVE, p, a, 8190, ctypes.byref(d), ctypes.byref(d),
                                ctypes.byref(d), None, None, None, 8, ctypes.byref(i4))
        # LIVE still holds the cap=3 run at [4096, ...); re-decoding the same positions in
        # the same sequence is refused by the engine, and -1 is the honest answer.
        guards["positions_busy" ] = f(h, P.LIVE, p, a, pos, ctypes.byref(d), ctypes.byref(d),
                                ctypes.byref(d), None, None, None, 8, ctypes.byref(i4))
        # all out pointers null + free positions must still succeed (nothing written, rc 0)
        eng.reset(P.LIVE)
        P.share_layout(eng, lay, placed)
        guards["null_outs_ok"] = f(h, P.LIVE, p, a, pos, None, None, None, None, None, None,
                                   8, None)
        want = {"cap0": -1, "cap_negative": -1, "null_prompt": -1, "null_answer": -1,
                "seq_out_of_range": -1, "past_pool": -1, "positions_busy": -1,
                "null_outs_ok": 0}
        ok4 = guards == want
        res["checks"]["guards"] = {"ok": ok4, "got": guards, "want": want}
        print("      guards got=%s  want=%s  -> %s" % (guards, want, ok4))

        # ---- build echo ------------------------------------------------------------
        dll = os.path.join(ROOTTOOLS, "kvshim_vk.dll")
        res["build"] = {"dll": dll, "dll_sha256": hashlib.sha256(open(dll, "rb").read()).hexdigest(),
                        "libllama_a_mtime": os.path.getmtime(
                            os.path.join(ROOT, "build-vulkan", "src", "libllama.a")),
                        "exports": [n for n in ("kvshim_score_at", "kvshim_piece",
                                                "kvshim_ask_at", "kvshim_ask_at_topk")
                                    if hasattr(eng.lib, n)]}
        print()
        print("[5] dll sha256=%s  libllama.a mtime=%s  exports=%s"
              % (res["build"]["dll_sha256"], res["build"]["libllama_a_mtime"],
                 res["build"]["exports"]))
    finally:
        eng.close()

    all_ok = all(c["ok"] for c in res["checks"].values())
    res["all_ok"] = all_ok
    path = os.path.join(OUT, "selftest.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=2)
    print()
    print("selftest %s -> %s" % ("PASS" if all_ok else "FAIL", path))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
