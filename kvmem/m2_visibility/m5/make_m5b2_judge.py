#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Turn M5B2-GEN.json answers into M5B2-JUDGE.json using frozen judge v2.3.

Only non-empty answer segments are emitted (PREREG-M5-B2 §2): blank lines and
pure tag/symbol lines are dropped.  v2.3 is still called once per whole answer;
its per-sentence verdicts are filtered, not recomputed with another judge.
No rates, no blind-label material.
"""
import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import m5_ground_v2_3 as J  # noqa: E402

JUDGE_SHA16 = "cc03e48c360ae0ee"
JUDGE_BYTES = 44209
GEN = HERE / "out" / "M5B2-GEN.json"
OUT = HERE / "out" / "M5B2-JUDGE.json"
TAG_OPEN = chr(60) + "think" + chr(62)
TAG_CLOSE = chr(60) + "/think" + chr(62)
TAG_RE = re.compile(r"^</?think\s*>$")
SENT_RE = re.compile(r"[\u3400-\u9fffA-Za-z0-9]")


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def coord(p):
    b = Path(p).read_bytes()
    return {"path": str(p), "sha16": sha16(b), "bytes": len(b)}


def is_counted_segment(raw):
    s = str(raw or "").strip()
    if not s:
        return False
    if TAG_RE.match(s):
        return False
    if s.startswith(TAG_OPEN) and s.endswith(TAG_CLOSE):
        s = s[7:-8].strip()
    if not s:
        return False
    return bool(SENT_RE.search(s))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", default=str(GEN))
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    jb = (HERE / "m5_ground_v2_3.py").read_bytes()
    if sha16(jb) != JUDGE_SHA16 or len(jb) != JUDGE_BYTES:
        raise SystemExit("frozen judge changed: %s / %d" % (sha16(jb), len(jb)))
    gen_b = Path(a.gen).read_bytes()
    gen = json.loads(gen_b.decode("utf-8"))
    qas = []
    total_kept = 0
    total_raw = 0
    total_empty = 0
    any_empty_no_fact = False
    for sc in gen.get("scenarios", []):
        source = sc.get("source_text", "")
        for q in sc.get("questions", []):
            rep = J.analyze_answer(q.get("answer", ""), [source], q.get("question", ""))
            segs = rep.get("sentences", [])
            kept = [s for s in segs if is_counted_segment(s.get("raw", ""))]
            dropped = [s for s in segs if not is_counted_segment(s.get("raw", ""))]
            empty_no_fact = [s for s in dropped if s.get("verdict") == "no_fact"]
            any_empty_no_fact = any_empty_no_fact or bool(empty_no_fact)
            total_kept += len(kept)
            total_raw += len(segs)
            total_empty += len(dropped)
            sents = []
            for s in kept:
                sents.append({
                    "idx": s.get("idx"), "text": s.get("raw"),
                    "verdict": s.get("verdict"), "reason": s.get("reason"),
                    "components": [c.get("text") for c in s.get("components", [])],
                    "covered": [c.get("text") for c in s.get("covered", [])],
                    "uncovered": [c.get("text") for c in s.get("uncovered", [])],
                })
            qas.append({
                "scenario": sc.get("id"), "qid": q.get("qid"), "question": q.get("question"),
                "kind": q.get("kind"), "expected": q.get("expected"),
                "answer": q.get("answer"), "answer_sha16": q.get("answer_sha16"),
                "verdict": rep.get("verdict"), "branch": rep.get("branch"),
                "reason": rep.get("reason"),
                "sentence_counts_nonempty": dict(Counter(s["verdict"] for s in sents)),
                "sentences_nonempty": sents,
                "n_sentences_nonempty": len(sents),
                "raw_sentence_count": len(segs),
                "empty_segment_count": len(dropped),
                "judge_counts_empty_as_no_fact": bool(empty_no_fact),
                "empty_no_fact_count": len(empty_no_fact),
                "partial_hit_sentences": [x for x in rep.get("partial_hit_sentences", [])
                                          if is_counted_segment(x.get("text", ""))],
                "polarity_conflicts": rep.get("polarity_conflicts", []),
                "extraction_fp": rep.get("extraction_fp", []),
            })
    jb2 = (HERE / "m5_ground_v2_3.py").read_bytes()
    if sha16(jb2) != JUDGE_SHA16 or jb2 != jb:
        raise SystemExit("frozen judge changed during judging")
    out = {
        "schema": "m5_b2_judge_v1",
        "prereg": gen.get("prereg"),
        "gen": {"path": str(Path(a.gen)), "sha16": sha16(gen_b), "bytes": len(gen_b)},
        "judge": {"path": str(HERE / "m5_ground_v2_3.py"),
                  "sha16": sha16(jb2), "bytes": len(jb2), "version": getattr(J, "JUDGE_VERSION", "v2.3")},
        "judge_sha_before": sha16(jb), "judge_sha_after": sha16(jb2),
        "qa": qas,
        "sentences_nonempty": total_kept,
        "raw_sentence_count": total_raw,
        "empty_segment_count": total_empty,
        "sample_size_threshold": 150,
        "sample_size_gate": total_kept >= 150,
        "judge_counts_empty_as_no_fact": any_empty_no_fact,
        "no_single_accuracy": True, "no_final_verdict": True, "no_rates_computed": True,
        "note": "per-question judge output on the pre-registered non-empty sentence set only; blank/tag segments dropped; no rates",
    }
    tmp = str(a.out) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, a.out)
    print(json.dumps({"out": coord(a.out), "n_qa": len(qas),
                      "sentences_nonempty": total_kept, "raw_sentence_count": total_raw,
                      "empty_segment_count": total_empty,
                      "sample_size_gate": total_kept >= 150,
                      "judge_counts_empty_as_no_fact": any_empty_no_fact,
                      "judge_sha16": sha16(jb2), "gen": coord(a.gen)},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())