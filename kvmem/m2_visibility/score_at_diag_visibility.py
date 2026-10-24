# -*- coding: utf-8 -*-
"""POST-HOC DIAGNOSTIC: is the block in 3 reaching the logits at all?

  empty   : LIVE holds nothing but the prompt (no memory anywhere)
  project : the project block mounted at the geometry's usual place

If Delta(project - empty) is large in BOTH case1 and case3, then the block is read in both
and the pre-registered metric's failure is a property of the metric, not of the geometry.

Run: python -X utf8 kvmem/m2_visibility/score_at_diag_visibility.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import score_lib as S                     # noqa: E402
import m2_visibility_probe as P           # noqa: E402

OUT = os.path.join(P.WORK_DIR, "evidence", "score_at")
ANSWER = "3 月 14 日上线"


def main():
    man = S.manifest()
    prompt = P.K.turn(P.FULL["project"]["q"])
    res = {"schema": "score_at_diag_visibility_v1", "answer": ANSWER, "cases": {}}
    eng = P.open_engine()
    try:
        for name, top in (("case1", P.CHAT), ("case3", P.CHAT - 1)):
            P.reset_all(eng)
            lay = S.layout([(1, "b", "project", "m2")], top=top, man=man)
            placed = S.place(eng, lay)
            with_mem = S.score(eng, lay, placed, prompt, ANSWER, top)
            eng.reset(P.LIVE)                       # nothing below the question at all
            empty = eng.score_at(P.LIVE, prompt, ANSWER, top)
            empty["piece_list"] = [eng.piece(t) for t in empty["tokens"]]
            d = {k: with_mem[k] - empty[k] for k in ("sum", "mean", "last")}
            res["cases"][name] = {"top": top, "with_memory": with_mem, "empty": empty,
                                  "delta_vs_empty": d}
            print("== %s (block [%d,%d), question at %d)" % (name, top - 18, top - 1, top))
            print("   empty  sum=%9.4f mean=%8.4f" % (empty["sum"], empty["mean"]))
            print("   block  sum=%9.4f mean=%8.4f" % (with_mem["sum"], with_mem["mean"]))
            print("   delta  sum=%+9.4f mean=%+8.4f last=%+8.4f"
                  % (d["sum"], d["mean"], d["last"]))
    finally:
        eng.close()
    path = os.path.join(OUT, "diag_visibility.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print()
    print("-> %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
