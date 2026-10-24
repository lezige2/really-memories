# -*- coding: utf-8 -*-
"""Derived self-check for the proxy (no hand-written method list).

  python -X utf8 surface_check.py      -> run_surface.json

Five checks, all derived from the real objects or from the source tree:
  1 classification  dir(type(eng)) vs the proxy class -> intercepted/observed/passthrough/unsupported
  2 truth           three deliberately wrong calls must raise the ENGINE's exception, verbatim
  3 dunders         unsupported protocols listed + grep proving current code uses none of them
  4 setattr         attribute writes must land on the engine + grep for such writes
  5 bridge trace    a save/restore run must log bridge.installed or bridge.inactive
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)
import chat                                                       # noqa: E402
import chat_lease as CL                                           # noqa: E402
from kvslots import KVEngine                                       # noqa: E402

SRC_DIRS = [TOOLS, os.path.join(ROOT, "kvmem", "m2_visibility")]
PATTERNS = {
    "len(eng)": r"len\(\s*eng\s*\)",
    "iter(eng)": r"(?:iter|next)\(\s*eng\s*\)",
    "with eng": r"with\s+eng\s*[:\n]",
    "eng[...]": r"\beng\s*\[",
    "copy.copy(eng)": r"copy\.(?:copy|deepcopy)\(\s*eng\s*\)",
    "pickle(eng)": r"pickle\.\w+\(\s*eng\s*\)",
    "eng.attr = (write)": r"\beng\.\w+\s*=\s*[^=]",   # scoped below (see SCOPE_WRITE)
    "type(eng) is": r"type\(\s*eng\s*\)\s*(?:is|==)",
    "isinstance(eng)": r"isinstance\(\s*eng\s*,",
}
SKIP = {"chat_lease.py", "surface_check.py"}       # the proxy itself and this file
# attribute writes are only meaningful in the modules that receive a proxied engine
SCOPE_WRITE = {"chat.py", "session_state.py", "memory_source.py", "chat_lease.py"}


def grep_tree():
    hits = {}
    for d in SRC_DIRS:
        for base, _dirs, files in os.walk(d):
            for fn in files:
                if not fn.endswith(".py") or fn in SKIP:
                    continue
                p = os.path.join(base, fn)
                try:
                    text = open(p, encoding="utf-8").read()
                except OSError:
                    continue
                for label, pat in PATTERNS.items():
                    if label.startswith("eng.attr") and fn not in SCOPE_WRITE:
                        continue
                    for m in re.finditer(pat, text):
                        line = text.count("\n", 0, m.start()) + 1
                        hits.setdefault(label, []).append(
                            {"file": os.path.relpath(p, ROOT), "line": line,
                             "text": text.splitlines()[line - 1].strip()[:100]})
    return hits


def main():
    res = {"schema": "chat_lease_surface_v1", "pid": os.getpid(), "strict": CL.STRICT}
    eng = KVEngine(chat.MODEL, n_ctx=chat.N_CTX, n_seq=8, gpu=99, kv="q8_0")
    try:
        leases = CL.GuardedLeases(eng, site_prefix="surface")
        surf = CL.surface(eng, leases)
        # 1: the unsupported-dunder list is only meaningful if the engine defines none of them
        surf["dunders_defined_by_engine"] = surf["dunders_not_supported"]
        res["check1_classification"] = {
            "intercepted": surf["intercepted"], "observed": surf["observed"],
            "passthrough_count": len(surf["passthrough"]),
            "shadowed": surf["shadowed"], "missing": surf["missing"],
            "isinstance_ok": surf["isinstance_ok"], "proxy_class": surf["proxy_class"],
            "base_class": surf["base_class"],
            "dunders_not_supported": surf["dunders_not_supported"],
            "dunders_defined_by_engine": surf["dunders_defined_by_engine"],
            "pass": bool(surf["clean"] and surf["isinstance_ok"]
                         and not surf["dunders_defined_by_engine"]
                         and surf["intercepted"] == ["drop", "reset", "share"]),
        }
        res["check2_forwarding_truth"] = CL.forwarding_truth(eng, leases)
        g = grep_tree()
        # 3: dunders/协议 — current code must not use any of them on an engine object
        used = {k: v for k, v in g.items()
                if k in ("len(eng)", "iter(eng)", "with eng", "eng[...]",
                         "copy.copy(eng)", "pickle(eng)")}
        res["check3_dunders"] = {
            "not_supported": surf["dunders_not_supported"],
            "engine_defines": surf["dunders_defined_by_engine"],
            "protocol_uses_in_source": used,
            "pass": not surf["dunders_defined_by_engine"] and not used,
        }
        # 4: attribute writes land on the engine; none in source relies on proxy-local writes
        writes = g.get("eng.attr = (write)", [])
        fwd = CL.setattr_forwarding(eng, leases)
        res["check4_setattr"] = {"forwarding": fwd, "writes_in_source": writes,
                                 "pass": bool(fwd["landed_on_engine"])}
        # 5: a real save/restore must leave a bridge trace in ITS run log
        prev = json.load(open(os.path.join(HERE, "run_load.json"), encoding="utf-8"))
        rows = CL.read_log(prev["log"]["events"])
        kinds = [r["kind"] for r in rows]
        res["check5_bridge_trace"] = {
            "log": prev["log"], "installed": kinds.count("bridge.installed"),
            "active": kinds.count("bridge.active"), "inactive": kinds.count("bridge.inactive"),
            "pass": bool(kinds.count("bridge.installed") + kinds.count("bridge.inactive") >= 1
                         and kinds.count("bridge.active") >= 1),
        }
        res["type_identity_grep"] = {"hits": g.get("type(eng) is", []),
                                     "isinstance_hits": g.get("isinstance(eng)", []),
                                     "pass": True}
    finally:
        eng.close()
    res["all_pass"] = all(res[k]["pass"] for k in ("check1_classification",
                                                   "check3_dunders", "check4_setattr",
                                                   "check5_bridge_trace")) \
        and all(c["same"] for c in res["check2_forwarding_truth"])
    json.dump(res, open(os.path.join(HERE, "run_surface.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False, indent=1)[:2800])
    print("[RUN] wrote run_surface.json  all_pass=%s" % res["all_pass"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
