# -*- coding: utf-8 -*-
import hashlib, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
def sha(x): return hashlib.sha256((x or "").encode("utf-8")).hexdigest()
def load(p): return json.load(open(p, encoding="utf-8"))

r1 = load(os.path.join(HERE, "run_m2_r1.json"))
r2 = load(os.path.join(HERE, "run_m2_r2.json"))
qs = ["home", "project", "habit"]
cmp_ = []
for i, q in enumerate(qs):
    a1, a2 = r1["asks"][i], r2["asks"][i]
    cmp_.append({"segment": q, "question": a1["question"],
                 "identical": a1["answer"] == a2["answer"],
                 "sha256_r1": sha(a1["answer"]), "sha256_r2": sha(a2["answer"]),
                 "answer_r1": a1["answer"], "answer_r2": a2["answer"],
                 "hit_r1": a1["hit"], "hit_r2": a2["hit"],
                 "hit_string": a1["hit_string"],
                 "ok_r1": a1["ok"], "ok_r2": a2["ok"],
                 "pos_asked": a1["pos_asked"],
                 "n_tokens_before": a1["n_tokens_before"],
                 "n_tokens_after": a1["n_tokens_after"]})
# the 14B fixture manifest does not carry the model hash; measure it from the file itself
if not r1["engine"].get("model_sha256"):
    h = hashlib.sha256()
    with open(r1["engine"]["model"], "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    r1["engine"]["model_sha256"] = h.hexdigest()
    print("model sha256 measured:", r1["engine"]["model_sha256"])

ev = {
 "schema": "m2_evidence_v1",
 "definition": ("M2 = three long-term memories (home/project/habit) held as KV cells inside "
                "attention, never written into the prompt, and answered correctly one after "
                "another in a single session."),
 "engine": r1["engine"],
 "geometry": r1["geometry"],
 "blocks": r1["blocks"],
 "placed": r1["placed"],
 "control_gate": r1["control_gate"],
 "questions": cmp_,
 "two_runs": {"both_pass": bool(r2.get("m2_pass") and r1.get("m2_pass")),
              "all_three_byte_identical": all(c["identical"] for c in cmp_),
              "all_hits_r1": r1["all_hits"], "all_hits_r2": r2["all_hits"],
              "elapsed_s": [r1.get("elapsed_s"), r2.get("elapsed_s")]},
 "commands": ["python -X utf8 kvmem/m2_visibility/m2/_driver_m2.py --run-json "
              "kvmem/m2_visibility/m2/run_m2_r1.json"],
 "unverified": [
  "no control gate in this driver (recorded as absent, with substitute evidence in control_gate)",
  "only n_predict=64 was tried; longer budgets untested",
  "the three questions are fixed strings; other phrasings untested",
  "no attention/numeric evidence that the blocks are read -- only behavioural",
  "long-duration VRAM stability not stress-tested (free VRAM 9426 MiB before every run)",
  "single model/quant (14B Q4_K_M, q8_0 KV); nothing else was swept"],
}
NEG1 = os.path.join(HERE, "run_m2_negctl_r1.json")
NEG2 = os.path.join(HERE, "run_m2_negctl_r2.json")
if os.path.exists(NEG1) and os.path.exists(NEG2):
    n1, n2 = load(NEG1), load(NEG2)
    q4a, q4b = n1["asks"][3], n2["asks"][3]
    ev["negctl"] = {
        "question": n1["negative_control_question"],
        "why": n1["why"],
        "premise": n1["negctl_premise"],
        "verdict_r1": q4a["verdict"], "verdict_r2": q4b["verdict"],
        "fabricated_token_r1": q4a.get("verdict_token"),
        "fabricated_token_r2": q4b.get("verdict_token"),
        "answer_r1": q4a["answer"], "answer_r2": q4b["answer"],
        "answer_sha256_r1": q4a["answer_sha256"],
        "two_runs_identical": q4a["answer"] == q4b["answer"],
        "regression_q1_q3_identical_to_run_m2_r1": {
            "r1": n1["regression"]["all_identical"],
            "r2": n2["regression"]["all_identical"]},
        "negctl_interpreted": [n1.get("negctl_interpreted"), n2.get("negctl_interpreted")],
        "real_plate_in_apparatus": "浙B-3F19K (exists only in control_texts_14b.json)",
        "real_plate_not_reproduced": q4a.get("verdict_token") != "浙B-3F19K",
    }

json.dump(ev, open(os.path.join(HERE, "evidence_m2.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2, default=str)
print("both_pass:", ev["two_runs"]["both_pass"])
print("all three byte-identical:", ev["two_runs"]["all_three_byte_identical"])
for c in cmp_:
    print("  %-8s identical=%-5s hit=%-6s sha16=%s" % (c["segment"], c["identical"],
          c["hit_string"], c["sha256_r1"][:16]))
print("dll measured:", r1["engine"]["loaded_dll_sha256"])
print("geometry:", json.dumps(r1["geometry"], ensure_ascii=False))
