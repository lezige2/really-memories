# -*- coding: utf-8 -*-
"""Run TIME-30 cases through temporal_timeline.retrieve offline (no service)."""
import json
import sys
from datetime import datetime

sys.path.insert(0, "tools")
import temporal_timeline as TT  # noqa: E402

CASES = [json.loads(l) for l in open("out/TIME-30-CASES.jsonl", encoding="utf-8") if l.strip()]

rows = []
for c in CASES:
    rows.append({"id": 1, "text": c["block"], "created_at": c["created_at"]})

rows_of = {c["id"]: [{"id": 1, "text": c["block"], "created_at": c["created_at"]}] for c in CASES}

out = []
for c in CASES:
    now = datetime.fromisoformat(c["anchor"])
    r = TT.retrieve(c["query"], now, rows_of[c["id"]], topk=4)
    exp = c["expected"]
    kind = exp.get("kind")
    if kind == "value":
        hit = bool(r["kept"]) and ("value" in exp)       # 值命中需看模型答案，离线只能判“是否给出块”
        status = "kept" if r["kept"] else ("abstain" if r["abstain"] else "empty")
        ok = bool(r["kept"]) and not r["abstain"]
    elif kind in ("abstain", "refusal"):
        status = "abstain" if r["abstain"] else ("kept" if r["kept"] else "empty")
        ok = r["abstain"]
    else:  # fallback
        status = "fallback" if r["ambiguous"] else ("abstain" if r["abstain"] else "kept")
        ok = r["ambiguous"]
    out.append({"id": c["id"], "kind": kind, "query": c["query"], "expected": exp,
                "anchor": r["anchor"], "query_intervals": r["query_intervals"],
                "kept": [k["id"] for k in r["kept"]],
                "kept_detail": [{"id": k["id"], "intervals": k.get("intervals"),
                                 "anchor": k.get("anchor"), "phrase": k.get("phrase"),
                                 "score": k.get("score")} for k in r["kept"]],
                "abstain": r["abstain"], "ambiguous": r["ambiguous"], "lazy": r["lazy"],
                "reason": r["reason"], "status": status, "ok": ok})

passed = sum(1 for r in out if r["ok"])
abst = [r for r in out if r["kind"] in ("abstain", "refusal")]
amb = [r for r in out if r["kind"] == "fallback"]
future = [r for r in out if r["id"].startswith("F")]
rest = [r for r in out if not r["id"].startswith("F")]
gate = passed >= 27 and all(r["ok"] for r in abst) and all(r["ok"] for r in amb)

rep = {"schema": "timeline_30_result_v1", "n": len(out), "passed": passed,
       "gate": ">=27/30 + abstain100 + fallback100", "gate_pass": gate,
       "abstain_n": len(abst), "abstain_ok": sum(1 for r in abst if r["ok"]),
       "fallback_n": len(amb), "fallback_ok": sum(1 for r in amb if r["ok"]),
       "future": {"n": len(future), "passed": sum(1 for r in future if r["ok"])},
       "rest": {"n": len(rest), "passed": sum(1 for r in rest if r["ok"])},
       "rows": out}
json.dump(rep, open("out/TIMELINE-30-RESULT.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

md = ["# 时间轴检索 · 30 题离线", "",
      "| id | 类型 | query | intervals | kept | abstain | amb | 判定 |", "|---|---|---|---|---|---|---|---|"]
for r in out:
    ivs = ",".join("%s..%s" % (i.get("start"), i.get("end")) for i in r["query_intervals"]) or "—"
    md.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
        r["id"], r["kind"], r["query"][:16], ivs, r["kept"], r["abstain"],
        r["ambiguous"], "✅" if r["ok"] else "❌"))
md += ["", "## 汇总", "",
       "- 总通过 **%d/%d**（门 27）：**%s**" % (passed, len(out), "过" if passed >= 27 else "不过"),
       "- 无答案 %d 条 abstain **%d/%d**" % (len(abst), rep["abstain_ok"], len(abst)),
       "- 歧义 %d 条 fallback **%d/%d**" % (len(amb), rep["fallback_ok"], len(amb)),
       "- **未来组 F01–F10：%d/%d**；其余 T01–T20：%d/%d" % (
           rep["future"]["passed"], rep["future"]["n"], rep["rest"]["passed"], rep["rest"]["n"]),
       "", "## 说明",
       "- 值命中在离线层只能判断“是否给出块”，具体值正确性需服务/模型层；本表不混算。",
       "- 每条已导出 `query_intervals / anchor / kept[].intervals / phrase`，可用于区分归一错与检索错。"]
open("out/TIMELINE-30-RESULT.md", "w", encoding="utf-8").write("\n".join(md))
print("passed %d/%d | abstain %d/%d | fallback %d/%d | F %d/%d | T %d/%d | gate %s" % (
    passed, len(out), rep["abstain_ok"], len(abst), rep["fallback_ok"], len(amb),
    rep["future"]["passed"], rep["future"]["n"], rep["rest"]["passed"], rep["rest"]["n"], gate))
for r in out:
    if not r["ok"]:
        print("FAIL", r["id"], r["kind"], "status", r["status"], "| reason", r["reason"])