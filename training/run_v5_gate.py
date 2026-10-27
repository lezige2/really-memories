# -*- coding: utf-8 -*-
"""v5 评测闸门（待命/复核用；不改被测代码，只读写 training/ 与 out/）。

用途（LEAD 发信号后）：
  1) 跑主命令（不重启服务、不清 eval2 会话）：
     python -X utf8 training/run_training_eval.py --endpoint http://127.0.0.1:8765 \
         --out out/TRAINING-EVAL-v5.json --next out/TRAINING-NEXT-v5.json --no-cleanup
  2) 本脚本后处理：
     python -X utf8 training/run_v5_gate.py --post
     在 EVAL/NEXT 里补：六硬用例逐条 pass/fail、infra 标记（HTTP 500 / 复读政策 / 连接失败）、
     排除 infra 后的通过率、真实失败分组（记忆检索/verify/web/身份自称）。
"""
import argparse
import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "out" / "TRAINING-EVAL-v5.json"
NEXT = ROOT / "out" / "TRAINING-NEXT-v5.json"

# 六硬用例：车牌（查询/复读/重复陈述）、组会（地点/时间）、时间（写后查）
SIX_HARD = ["h02", "h03", "m02", "m03", "s03", "u05"]
HARD_LABEL = {"h02": "下周三去哪开会→广州", "h03": "下周五去哪开会→成都",
              "m02": "我叫什么名字→阿泽", "m03": "组会在哪开→B座302",
              "s03": "养的猫叫什么→豆豆", "u05": "明天去哪出差→不得编造城市"}
EXTRA_HARD = [("h01", "帮我加个好友→诚实说做不了")]

LEAK_RE = re.compile(r"检索资料；说话自然|不要源标|说话自然、简短、口语化")
REP_RE = re.compile(r"(.)\1{14,}")
HTTP_RE = re.compile(r"HTTP ?50\d|500 Internal|Internal Server Error", re.I)
CONN_RE = re.compile(r"URLError|ConnectionRefused|ConnectionReset|timed out|10061|10054")
IDENT_RE = re.compile(r"DeepSeek|深度求索|Qwen|通义|千问|GPT|R1[- ]?Lite|Lite[- ]?Preview")


def classify_infra(rows):
    http500, conn, repeat = [], [], []
    for r in rows:
        a = r.get("actual") or {}
        ans = str(a.get("answer") or "")
        err = str(a.get("error") or "")
        if HTTP_RE.search(err):
            http500.append(r["id"])
        elif CONN_RE.search(err):
            conn.append(r["id"])
        elif LEAK_RE.search(ans) or REP_RE.search(ans):
            repeat.append(r["id"])
    return {"http_500": http500, "connection_failed": conn,
            "policy_repeat": repeat,
            "n_infra": len(http500) + len(conn) + len(repeat)}


def real_groups(results):
    groups = {"memory_retrieval": [], "verify": [], "web": [], "identity_claim": [],
              "generation_degenerate": [], "other": []}
    for r in results:
        if r.get("pass"):
            continue
        cid = r["id"]
        a = r.get("actual") or {}
        ans = str(a.get("answer") or "")
        st = a.get("state")
        if LEAK_RE.search(ans) or REP_RE.search(ans):
            groups["generation_degenerate"].append(cid)
        elif st == "verify_fallback" or "这条我没法从记忆里核对" in ans:
            groups["verify"].append(cid)
        elif r.get("category") == "networking" or st == "web":
            groups["web"].append(cid)
        elif IDENT_RE.search(ans):
            groups["identity_claim"].append(cid)
        elif r.get("category") == "identity":
            groups["identity_claim"].append(cid)
        elif r.get("category") in ("memory_qa", "mixed"):
            groups["memory_retrieval"].append(cid)
        else:
            groups["other"].append(cid)
    return groups


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", default=str(EVAL))
    ap.add_argument("--next", default=str(NEXT))
    ap.add_argument("--post", action="store_true", help="后处理已有 v5 EVAL/NEXT")
    ap.add_argument("--extra-hard", default=",".join(x[0] for x in EXTRA_HARD),
                    help="额外硬用例 id（默认 h01 加好友）")
    ap.add_argument("--six-hard", default=",".join(SIX_HARD),
                    help="六硬用例 id，逗号分隔（默认：%s）" % ",".join(SIX_HARD))
    args = ap.parse_args()
    ev_path, nx_path = Path(args.eval), Path(args.next)
    if not ev_path.exists():
        print("缺少 %s；先跑主命令：python -X utf8 training/run_training_eval.py "
              "--endpoint http://127.0.0.1:8765 --out out/TRAINING-EVAL-v5.json "
              "--next out/TRAINING-NEXT-v5.json --no-cleanup" % ev_path)
        return 2
    six_hard = [x.strip() for x in args.six_hard.split(",") if x.strip()]
    ev = json.loads(ev_path.read_text(encoding="utf-8"))
    rows = ev.get("results") or []
    infra = classify_infra(rows)
    infra_ids = set(infra["http_500"] + infra["connection_failed"] + infra["policy_repeat"])
    valid = [r for r in rows if r["id"] not in infra_ids]
    valid_pass = sum(1 for r in valid if r.get("pass"))
    by_id = {r["id"]: r for r in rows}
    six = {}
    for cid in six_hard:
        r = by_id.get(cid)
        six[cid] = {"label": HARD_LABEL.get(cid, ""), "present": r is not None,
                    "pass": bool(r and r.get("pass")),
                    "failure_class": (r or {}).get("failure_class"),
                    "answer": str(((r or {}).get("actual") or {}).get("answer") or "")[:160]}
    extra_ids = [x.strip() for x in args.extra_hard.split(",") if x.strip()]
    extra = {}
    for cid in extra_ids:
        label = dict(EXTRA_HARD).get(cid, "")
        rr = by_id.get(cid)
        extra[cid] = {"label": label, "present": rr is not None,
                      "pass": bool(rr and rr.get("pass")),
                      "failure_class": (rr or {}).get("failure_class"),
                      "answer": str(((rr or {}).get("actual") or {}).get("answer") or "")[:160]}
    groups = real_groups([r for r in valid if not r.get("pass")])
    ev["v5_gate"] = {
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
        "six_hard": six,
        "six_hard_all_pass": all(v["present"] and v["pass"] for v in six.values()),
        "extra_hard": extra,
        "extra_hard_all_pass": all(v["present"] and v["pass"] for v in extra.values()),
        "infra": infra,
        "pass_rate_raw": ev.get("summary", {}).get("pass_rate"),
        "pass_rate_excl_infra": round(valid_pass / len(valid), 6) if valid else None,
        "n_valid_excl_infra": len(valid),
        "real_failures": {k: {"n": len(v), "ids": v} for k, v in groups.items()},
        "verdict": ("pass" if all(v["present"] and v["pass"] for v in six.values())
                    and not infra["n_infra"] else
                    ("infra_present" if infra["n_infra"] else "hard_fail")),
    }
    ev_path.write_text(json.dumps(ev, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    nx = json.loads(nx_path.read_text(encoding="utf-8")) if nx_path.exists() else {}
    nx["six_hard"] = six
    nx["six_hard_all_pass"] = ev["v5_gate"]["six_hard_all_pass"]
    nx["extra_hard"] = ev["v5_gate"]["extra_hard"]
    nx["extra_hard_all_pass"] = ev["v5_gate"]["extra_hard_all_pass"]
    nx["infra"] = infra
    nx["pass_rate_excl_infra"] = ev["v5_gate"]["pass_rate_excl_infra"]
    nx["real_failures"] = ev["v5_gate"]["real_failures"]
    nx["top3_real"] = sorted(
        ((k, len(v)) for k, v in groups.items() if v), key=lambda kv: (-kv[1], kv[0]))[:3]
    nx_path.write_text(json.dumps(nx, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print("extra_hard:", json.dumps({k: v["pass"] for k, v in extra.items()}, ensure_ascii=False))
    print("six_hard_all_pass:", ev["v5_gate"]["six_hard_all_pass"],
          json.dumps({k: v["pass"] for k, v in six.items()}, ensure_ascii=False))
    print("infra:", json.dumps(infra, ensure_ascii=False))
    print("pass_rate_raw:", ev["v5_gate"]["pass_rate_raw"],
          "excl_infra:", ev["v5_gate"]["pass_rate_excl_infra"],
          "valid:", len(valid))
    print("top3_real:", nx["top3_real"])
    print("wrote:", ev_path, nx_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())