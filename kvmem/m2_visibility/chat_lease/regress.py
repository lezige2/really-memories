# -*- coding: utf-8 -*-
"""Regression harness for the chat.py lease wiring (M3's last open item).

  python -X utf8 regress.py --label before --out run_before.json
  python -X utf8 regress.py --label after  --out run_after.json

Three runs per label:
  chat      python -X utf8 tools/chat.py            (2 blocks, 86 cells, 3 questions + control)
  m1        python -X utf8 tools/chat.py m1         (per-question mount/unmount -> 4 resets)
  m2driver  kvmem/m2_visibility/m2/_driver_m2.py    (frozen M2 baseline: 51 cells, 3 questions)

Answers are hashed with chat.clean() -- the SAME function the product prints through, so the
sha is over what a user would read, not over raw generation.
"""
import hashlib, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)
import chat                                                       # noqa: E402

PY = sys.executable
QA = re.compile(r"^问：(.*)$")
A = re.compile(r"^答：(.*)$")


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _pairs(stdout):
    """问/答 pairs in order, cleaned exactly like the product does."""
    out, q = [], None
    for line in stdout.splitlines():
        m = QA.match(line)
        if m:
            q = m.group(1).split("   [")[0].strip()
            continue
        m = A.match(line)
        if m and q is not None:
            ans = chat.clean(m.group(1))
            out.append({"q": q, "answer": ans, "sha16": sha(ans)[:16], "chars": len(ans)})
            q = None
    return out


def run(cmd, cwd=ROOT, timeout=1800):
    t0 = time.time()
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    return {"cmd": " ".join(cmd), "rc": p.returncode, "seconds": round(time.time() - t0, 1),
            "stdout_tail": (p.stdout or "")[-3000:], "stderr_tail": (p.stderr or "")[-1500:],
            "stdout_sha16": sha(p.stdout or "")[:16], "pairs": _pairs(p.stdout or "")}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--skip-m2", action="store_true")
    a = ap.parse_args()

    res = {"schema": "chat_lease_regress_v1", "label": a.label, "pid": os.getpid(),
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "chat_py_sha16": sha(open(os.path.join(TOOLS, "chat.py"), encoding="utf-8").read())[:16],
           "lease_module_present": os.path.exists(os.path.join(TOOLS, "chat_lease.py"))}
    res["chat"] = run([PY, "-X", "utf8", os.path.join(TOOLS, "chat.py")])
    res["m1"] = run([PY, "-X", "utf8", os.path.join(TOOLS, "chat.py"), "m1"])
    # the 4th site: _place_slots() is only reached through "save"
    res["save"] = run([PY, "-X", "utf8", os.path.join(TOOLS, "chat.py"), "save"])
    sess = os.path.join(ROOT, "kvmem", "sessions", "live.json")
    if os.path.exists(sess):
        blob = open(sess, encoding="utf-8").read()
        import shutil
        shutil.copyfile(sess, os.path.join(HERE, "_session_%s.json" % a.label))
        res["save"]["session_sha16"] = sha(blob)[:16]
    if not a.skip_m2:
        mp = os.path.join(HERE, "_m2_%s.json" % a.label)
        r = run([PY, "-X", "utf8",
                 os.path.join(ROOT, "kvmem", "m2_visibility", "m2", "_driver_m2.py"),
                 "--run-json", mp])
        res["m2driver"] = r
        if os.path.exists(mp):
            d = json.load(open(mp, encoding="utf-8"))
            res["m2driver"]["asks"] = [{"q": k.get("question"), "answer": k.get("answer"),
                                        "ok": k.get("ok"),
                                        "sha16": sha(chat.clean(k.get("answer") or ""))[:16]}
                                       for k in d.get("asks", [])]
            res["m2driver"]["all_hits"] = d.get("all_hits")
            res["m2driver"]["cells"] = d.get("layout", {}).get("cells") or d.get("cells")
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    json.dump(res, open(os.path.join(HERE, a.out), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    for k in ("chat", "m1", "save", "m2driver"):
        if k in res:
            print("%-8s rc=%s %.0fs pairs=%d" % (k, res[k]["rc"], res[k]["seconds"],
                                                 len(res[k]["pairs"])))
            for pr in res[k]["pairs"]:
                print("   %-28s %s %s" % (pr["q"][:26], pr["sha16"], pr["answer"][:40]))
    print("[RUN] wrote", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
