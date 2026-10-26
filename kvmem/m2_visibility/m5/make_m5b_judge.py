#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Turn M5B-GEN.json answers into M5B-JUDGE.json using frozen judge v2.3.

No GPU, no model, no rates.  The only judging call is
`m5_ground_v2_3.analyze_answer(answer, [scenario.source_text], question)`.
This file does not read ADJ/REVIEW material and does not compute leak/false rates.
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(HERE))
import m5_ground_v2_3 as J  # noqa: E402

JUDGE_SHA16 = "cc03e48c360ae0ee"
JUDGE_BYTES = 44209
GEN = HERE / "out" / "M5B-GEN.json"
OUT = HERE / "out" / "M5B-JUDGE.json"


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def coord(p):
    b = Path(p).read_bytes()
    return {"path": str(p), "sha16": sha16(b), "bytes": len(b)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", default=str(GEN))
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    jb = Path(J.JUDGE_PATH).read_bytes() if hasattr(J, "JUDGE_PATH") else (HERE / "m5_ground_v2_3.py").read_bytes()
    if sha16(jb) != JUDGE_SHA16 or len(jb) != JUDGE_BYTES:
        raise SystemExit("frozen judge changed: %s / %d" % (sha16(jb), len(jb)))
    gen_b = Path(a.gen).read_bytes()
    gen = json.loads(gen_b.decode("utf-8"))
    qas = []
    for sc in gen.get("scenarios", []):
        source = sc.get("source_text", "")
        for q in sc.get("questions", []):
            rep = J.analyze_answer(q.get("answer", ""), [source], q.get("text", ""))
            sents = []
            for s in rep.get("sentences", []):
                sents.append({
                    "idx": s.get("idx"), "text": s.get("raw", s.get("text")),
                    "text_norm": s.get("text_norm"),
                    "verdict": s.get("verdict"), "reason": s.get("reason"),
                    "components": [c.get("text") for c in s.get("components", [])],
                    "covered": [c.get("text") for c in s.get("covered", [])],
                    "uncovered": [c.get("text") for c in s.get("uncovered", [])],
                    "partial": s.get("verdict") == "unsupported" and s.get("n_covered", 0) > 0,
                })
            qas.append({
                "scenario": sc.get("id"), "qid": q.get("qid"), "question": q.get("text"),
                "kind": q.get("kind"), "expected": q.get("expected"),
                "answer": q.get("answer"), "answer_sha16": q.get("answer_sha16"),
                "verdict": rep.get("verdict"), "branch": rep.get("branch"),
                "reason": rep.get("reason"), "sentence_counts": rep.get("sentence_counts"),
                "sentences": sents,
                "partial_hit_sentences": rep.get("partial_hit_sentences", []),
                "polarity_conflicts": rep.get("polarity_conflicts", []),
                "extraction_fp": rep.get("extraction_fp", []),
            })
    jb2 = Path(J.JUDGE_PATH).read_bytes() if hasattr(J, "JUDGE_PATH") else (HERE / "m5_ground_v2_3.py").read_bytes()
    if sha16(jb2) != JUDGE_SHA16 or jb2 != jb:
        raise SystemExit("frozen judge changed during judging")
    out = {
        "schema": "m5_b_judge_v1",
        "prereg": gen.get("prereg"),
        "gen": {"path": str(Path(a.gen)), "sha16": sha16(gen_b), "bytes": len(gen_b)},
        "judge": {"path": str(Path(J.JUDGE_PATH) if hasattr(J, "JUDGE_PATH") else HERE / "m5_ground_v2_3.py"),
                  "sha16": sha16(jb2), "bytes": len(jb2), "version": getattr(J, "JUDGE_VERSION", "v2.3")},
        "judge_sha_before": sha16(jb), "judge_sha_after": sha16(jb2),
        "qa": qas,
        "no_single_accuracy": True, "no_final_verdict": True,
        "no_rates_computed": True,
        "note": "per-question judge output only; blind labels and rates are owned by LEAD/ADJ/REVIEW",
    }
    tmp = str(a.out) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, a.out)
    print(json.dumps({"out": coord(a.out), "n_qa": len(qas),
                      "judge_sha16": sha16(jb2), "gen": coord(a.gen)},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())