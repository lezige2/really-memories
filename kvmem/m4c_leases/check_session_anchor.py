# -*- coding: utf-8 -*-
"""回归锚：把 session 剔除 saved_at 之后算 sha16。三态，MISSING 判 FAIL。

口径（写死，不再靠记忆或反推）：
  1) 读 JSON；2) 递归剔除键 `saved_at`；3) `json.dumps(..., sort_keys=True, ensure_ascii=False)`
     （**不带 separators**）; 4) UTF-8 -> sha256 前 16 位。
此口径由 /tmp/find_anchor_rule.py 在 10 种候选里唯一命中文档值（strip_canon_default / strip_canon_ascii 等价命中）。

三态：EQUAL / DIFF / MISSING，**MISSING 判 FAIL** —— 失败会销毁自己的证据，所以「没看到」不能判通过。

定位：**回归锁，不是正确性证据**。它守的是「存档不变式 + 见证者别在存档路径上误触发」，
不是「存档没被污染」—— cmd_save 会走 _place_slots，那里有站点 2 的见证者，
失败方式是 die 在写盘之前 ⇒ 盘上没有产物。
"""
import hashlib, json, os, sys

SESSIONS = r"D:\llama-mem\kvmem\sessions"
BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "SESSION-ANCHOR-BASELINE.json")

def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if k != "saved_at"}
    if isinstance(o, list):
        return [strip(v) for v in o]
    return o

def anchor_of(path):
    doc = json.load(open(path, encoding="utf-8"))
    canon = json.dumps(strip(doc), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]

def main():
    record = len(sys.argv) > 1 and sys.argv[1] == "--record"
    files = {}
    for name in sorted(os.listdir(SESSIONS)):
        if name.endswith(".json"):
            p = os.path.join(SESSIONS, name)
            files[name] = {"anchor": anchor_of(p), "bytes": os.path.getsize(p)}
    out = {"schema": "session_anchor_v2", "rule": "strip saved_at -> json.dumps(sort_keys=True, ensure_ascii=False) -> sha256[:16]",
           "three_state": ["EQUAL", "DIFF", "MISSING"],
           "rule_for_missing": "MISSING 判 FAIL（失败会销毁它自己的证据）",
           "files": files,
           "script_sha16": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()[:16],
           "sampled_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime())}
    if record:
        json.dump({"live_anchor": files["live.json"]["anchor"], "recorded_at": out["sampled_at"],
                   "note": "M4-C 改动前录下的基线；sl 为回归锁的上界"},
                  open(BASELINE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    base = json.load(open(BASELINE, encoding="utf-8")) if os.path.exists(BASELINE) else None
    out["anchor_before"] = base["live_anchor"] if base else None
    out["anchor_after"] = files.get("live.json", {}).get("anchor")
    if out["anchor_after"] is None:
        out["outcome"] = "MISSING"
    elif out["anchor_before"] is None:
        out["outcome"] = "MISSING(baseline)"
    else:
        out["outcome"] = "EQUAL" if out["anchor_before"] == out["anchor_after"] else "DIFF"
    out["verdict"] = "FAIL" if out["outcome"].startswith("MISSING") or out["outcome"] == "DIFF" else "PASS"
    out["documented_value"] = "fa94b1bc58c0e421"
    out["reproduces_documented"] = out["anchor_after"] == out["documented_value"]
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "SESSION-ANCHOR.json")
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps({k: out[k] for k in ("anchor_before", "anchor_after", "outcome", "verdict",
                                          "reproduces_documented", "script_sha16", "sampled_at")}, ensure_ascii=False))

if __name__ == "__main__":
    main()
