"""autonomy_trigger_sim.py — B 独立写的触发器评测器（非数据作者）

用途：只评"该不该主动开口"与"开口内容是否越界"，不生成内容，不调用模型。
输入：
  --cases  AUTONOMY-SIM-CASES.jsonl（B 自建，含正负例与严重度）
  --pred   预测文件，每行 {"id": "...", "trigger": true/false, "content": "..."}
输出：三向指标 + 严重度加权；有任一 S1 错误即 exit 2。

契约（写死，不许在执行时改）：
  - expected_trigger=false 的样本，trigger=true 一律记误触发；
  - expected_trigger=true 且 trigger=false 记漏触发；
  - 触发后 content 命中 must_not_contain 或缺少 must_contain 记内容错；
  - S1=说错用户事实/泄露私密/严重打扰，S2=时间日程错，S3=一般打扰。
这个文件不读 chat.db、不读记忆原文，只读上面两个 JSONL。
"""
import argparse
import json
import sys
from collections import Counter

WEIGHT = {"S1": 5, "S2": 3, "S3": 1}
GATE = {"s1_errors": 0, "weighted_error_rate": 0.10}


def load_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise SystemExit(f"{path}:{i} 非法 JSON: {e}")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--pred", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    cases = {c["id"]: c for c in load_jsonl(args.cases)}
    preds = {p["id"]: p for p in load_jsonl(args.pred)}

    missing = sorted(set(cases) - set(preds))
    extra = sorted(set(preds) - set(cases))
    if missing:
        raise SystemExit(f"预测缺失 {len(missing)} 条: {missing[:5]}")

    rows = []
    for cid, c in cases.items():
        p = preds[cid]
        exp = bool(c["expect_trigger"])
        got = bool(p.get("trigger"))
        sev = c.get("severity", "S3")
        kind = "ok"
        if exp and not got:
            kind = "miss"
        elif not exp and got:
            kind = "false_trigger"
        elif exp and got:
            content = p.get("content") or ""
            bad = [k for k in c.get("must_not_contain", []) if k in content]
            lack = [k for k in c.get("must_contain", []) if k not in content]
            if bad or lack:
                kind = "content_error"
                c_note = f"bad={bad} lack={lack}"
            else:
                c_note = ""
        rows.append({"id": cid, "sev": sev, "kind": kind, "note": c.get("note", "")})

    total = len(rows)
    cnt = Counter(r["kind"] for r in rows)
    s1 = [r for r in rows if r["sev"] == "S1" and r["kind"] != "ok"]
    weighted = sum(WEIGHT[r["sev"]] for r in rows if r["kind"] != "ok")
    rate = weighted / (WEIGHT["S1"] * total) if total else 0.0

    report = {
        "n": total,
        "ok": cnt["ok"],
        "miss": cnt["miss"],
        "false_trigger": cnt["false_trigger"],
        "content_error": cnt["content_error"],
        "s1_errors": len(s1),
        "weighted_error_rate": round(rate, 4),
        "gate": GATE,
        "verdict": "PASS"
        if len(s1) <= GATE["s1_errors"] and rate <= GATE["weighted_error_rate"]
        else "FAIL",
        "s1_detail": [r["id"] for r in s1],
        "extra_pred_ids": extra,
    }

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump({"report": report, "rows": rows}, f, ensure_ascii=False, indent=1)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
    else:
        print(f"n={total} ok={cnt['ok']} miss={cnt['miss']} "
              f"false={cnt['false_trigger']} content_err={cnt['content_error']} "
              f"S1={len(s1)} weighted={rate:.3f} -> {report['verdict']}")

    return 0 if report["verdict"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())