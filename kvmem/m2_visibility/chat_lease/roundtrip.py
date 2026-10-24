# -*- coding: utf-8 -*-
"""Session save -> load round trip: answers must be byte-identical before/after the bridge.

  python -X utf8 roundtrip.py --label before
  CHAT_LEASE_BRIDGE=0 python -X utf8 roundtrip.py --label bridge_off

Two real processes (`chat.py save` then `chat.py load`), same as a user would run.
"""
import hashlib, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)
import chat                                                       # noqa: E402

PY = sys.executable
QA, A = re.compile(r"^问：(.*)$"), re.compile(r"^答：(.*)$")


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def pairs(out):
    res, q = [], None
    for line in out.splitlines():
        m = QA.match(line)
        if m:
            q = m.group(1).split("   [")[0].strip()
            continue
        m = A.match(line)
        if m and q is not None:
            ans = chat.clean(m.group(1))
            res.append({"q": q, "answer": ans, "sha16": sha(ans)[:16]})
            q = None
    return res


def run(args):
    p = subprocess.run([PY, "-X", "utf8"] + args, cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return {"rc": p.returncode, "pairs": pairs(p.stdout or ""),
            "tail": (p.stdout or "")[-1200:], "err": (p.stderr or "")[-600:]}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    a = ap.parse_args()
    res = {"schema": "chat_lease_roundtrip_v1", "label": a.label,
           "bridge_env": os.environ.get("CHAT_LEASE_BRIDGE", "1"),
           "save": run([os.path.join(TOOLS, "chat.py"), "save"]),
           "load": run([os.path.join(TOOLS, "chat.py"), "load"])}
    man = os.path.join(ROOT, "kvmem", "sessions", "live.json")
    if os.path.exists(man):
        blob = open(man, encoding="utf-8").read()
        m = json.loads(blob)
        res["manifest_sha16"] = sha(blob)[:16]
        res["manifest_placement"] = [{"block": b["block"], "slot": b["slot_id"],
                                      "start": b["start"], "end": b["end"],
                                      "n_tokens": b["n_tokens"]}
                                     for b in m["placement"]["blocks"]]
        res["manifest_chat"] = m["chat"]
        import shutil
        shutil.copyfile(man, os.path.join(HERE, "_rt_session_%s.json" % a.label))
    res["sha16"] = {k: [p["sha16"] for p in res[k]["pairs"]] for k in ("save", "load")}
    json.dump(res, open(os.path.join(HERE, "run_rt_%s.json" % a.label), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("label %-10s bridge=%s" % (a.label, res["bridge_env"]))
    for k in ("save", "load"):
        print(" %-4s rc=%s" % (k, res[k]["rc"]))
        for p in res[k]["pairs"]:
            print("   %-28s %s %s" % (p["q"][:26], p["sha16"], p["answer"][:34]))
    print("[RUN] wrote run_rt_%s.json" % a.label)
    return 0


if __name__ == "__main__":
    sys.exit(main())
