# -*- coding: utf-8 -*-
"""C4-k: the M5 source gate must have real call sites, and no way around it.

Two machine checks, no prose promises:

  1. call sites -- every call of assert_m5_source_allowed across the tree, as file:line;
  2. no bypass  -- every file that reads a registry source on the M5 path must either call
     the gate or carry an explicit TODO(stage3) marker. A file that reads a source with
     neither is a bypass and fails this check.

  python -u -X utf8 check_m5_gate.py
"""
import io, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
GATE = "assert_m5_source_allowed"
TODO = "TODO(stage3)"
# files that could ever read a registry source on the way into M5
SURFACES = ["kvmem/m2_visibility/m5", "kvmem/m2_visibility/m4", "tools"]
SOURCE_PAT = re.compile(r"chat\.db|memory_source|registry_source_id|probe_text|get_source")


def pyfiles(rel):
    base = os.path.join(ROOT, rel)
    if os.path.isfile(base):
        return [base]
    out = []
    for d, _, fs in os.walk(base):
        if "_before" in d or "_test" in d or "_ablate" in d or "_m5db" in d:
            continue
        out += [os.path.join(d, f) for f in fs if f.endswith(".py")]
    return out


def grep_gate():
    hits = []
    for rel in SURFACES:
        for f in pyfiles(rel):
            for i, line in enumerate(io.open(f, encoding="utf-8", errors="replace"), 1):
                st = line.strip()
                if st.startswith("#") or st.startswith("def "):
                    continue
                # a call, not a mention inside a sentence or a docstring path
                if re.search(r"(?:=|\(|,|\*\*)\s*" + GATE + r"\(", line):
                    hits.append({"file": os.path.relpath(f, ROOT).replace("\\", "/"),
                                 "line": i, "text": st[:120]})
    return hits




def stage3_strict():
    """Stage 3 strict mode: three layers, each machine-checked.

    Layer 1 BINDS THE RETURN POINT, not a function name: the gate must be called inside the
    body of the function that returns the admitted source list. Renaming the function or
    moving the loop cannot satisfy this; a refactor that leaves a return without a gate is
    exactly what it looks for.
    Layer 2 proves reachability from the public entry point.
    Layer 3 is AUTHORITATIVE: make the registry unavailable and the process must refuse.
    """
    import ast
    res = {"schema": "m5_gate_stage3_v1"}
    bridge = os.path.join(ROOT, "kvmem/m2_visibility/m4/m5_bridge.py")
    src = io.open(bridge, encoding="utf-8").read()
    tree = ast.parse(src)

    def returns_source_dict(fn):
        for n in ast.walk(fn):
            if isinstance(n, ast.Return) and isinstance(n.value, ast.Dict):
                keys = [k.value for k in n.value.keys if isinstance(k, ast.Constant)]
                if "text" in keys:
                    return True
        return False

    rp = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or not returns_source_dict(node):
            continue
        gates = sorted(n.lineno for n in ast.walk(node)
                       if isinstance(n, ast.Call)
                       and getattr(n.func, "attr", "") == GATE)
        rp.append({"function": node.name, "def_line": node.lineno,
                   "gate_lines": gates,
                   "file_line": "m5_bridge.py:%d" % (gates[0] if gates else node.lineno)})
    res["source_returning_functions"] = rp
    res["layer1_ast"] = {
        "ok": bool(rp) and all(f["gate_lines"] for f in rp),
        "rule": "every function that returns an admitted source list must call the gate",
        "ungated": [f["function"] for f in rp if not f["gate_lines"]]}

    entry = [n for n in ast.walk(tree)
             if isinstance(n, ast.FunctionDef) and n.name == "ensure_db"]
    names = sorted(f["function"] for f in rp)
    reach = []
    for fn in entry:
        for n in ast.walk(fn):
            if isinstance(n, ast.Call) and getattr(n.func, "id", "") in names:
                reach.append({"call": n.func.id, "line": n.lineno,
                              "file_line": "m5_bridge.py:%d" % n.lineno})
    res["reachability"] = {"entry": "ensure_db", "calls": reach, "ok": bool(reach),
                           "note": "ensure_db keeps its own REG_DB existence check; that check is now only a REACHABILITY witness -- layer 3 is the authority"}

    sys.path.insert(0, os.path.join(ROOT, "kvmem", "m2_visibility", "m4"))
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    sys.path.insert(0, os.path.join(ROOT, "kvmem", "m2_visibility", "m5"))
    import tempfile
    import m5_bridge as BR
    saved = BR.REG_DB
    verdict = {}
    try:
        BR.REG_DB = os.path.join(tempfile.gettempdir(), "_stage3_no_registry.db")
        try:
            BR.ensure_db(os.path.join(tempfile.gettempdir(), "_stage3_probe.db"))
            verdict = {"raised": None}
        except Exception as e:                                    # noqa: BLE001
            verdict = {"raised": type(e).__name__, "message": str(e)[:200]}
    finally:
        BR.REG_DB = saved
    res["runtime_refusal"] = {
        "how": "REG_DB pointed at a missing path, then ensure_db()",
        "result": verdict,
        "ok": verdict.get("raised") in ("OriginError", "AssertionError"),
        "authority": "layer 3 -- no static argument can prove the absence of a bypass return"}

    res["todo_stage3_count"] = src.count(TODO)
    res["no_todo_stage3"] = res["todo_stage3_count"] == 0
    res["pass"] = all([res["layer1_ast"]["ok"], res["reachability"]["ok"],
                       res["runtime_refusal"]["ok"], res["no_todo_stage3"]])
    return res


def main():
    res = {"schema": "m5_gate_check_v1", "gate": GATE}
    res["call_sites"] = grep_gate()
    res["call_site_count"] = len(res["call_sites"])
    # in scope = it can put text in front of M5 as a grounding source. Decided by machine
    # evidence (it touches the M5 text copy or imports the M5 engine), not by filename.
    def in_scope(relp, src):
        """A source path is code that MATERIALIZES M5 source text, or the engine itself.

        Merely reading the text copy for a verification probe is not a source path, and the
        machine decides that: no register_block / INSERT INTO blocks means it creates no
        source rows.
        """
        writes_the_m5_copy = ("m5_m4_blocks" in src
                              and ("INSERT" in src or "register_block(" in src))
        return relp.startswith("kvmem/m2_visibility/m5/") or writes_the_m5_copy

    reads, bypass, out_of_scope = [], [], []
    for rel in SURFACES:
        for f in pyfiles(rel):
            src = io.open(f, encoding="utf-8", errors="replace").read()
            lines = src.split("\n")
            hit = [i for i, l in enumerate(lines, 1)
                   if SOURCE_PAT.search(l) and not l.strip().startswith("#")]
            if not hit:
                continue
            relp = os.path.relpath(f, ROOT).replace("\\", "/")
            if not in_scope(relp, src):
                out_of_scope.append({"file": relp, "read_lines": hit[:4],
                                     "why": ("creates no M5 source rows (no register_block / "
                                             "INSERT INTO blocks): it reads the copy for a "
                                             "probe or works on the chat side")})
                continue
            rec = {"file": relp, "read_lines": hit[:8], "reads_registry_source": True,
                   "calls_gate": GATE in src, "has_todo_stage3": TODO in src}
            if relp.endswith("tools/memory_source.py"):
                rec["role"] = "definition of the registry API, not an M5 source path"
                rec["calls_gate"] = True
            rec["ok"] = rec["calls_gate"] or rec["has_todo_stage3"]
            reads.append(rec)
            if not rec["ok"]:
                bypass.append(rec)
    res["out_of_scope"] = out_of_scope
    res["registry_readers"] = reads
    res["bypass_count"] = len(bypass)
    res["m5_has_registry_read"] = any(r["file"].startswith("kvmem/m2_visibility/m5")
                                      for r in reads)
    res["m5_files_scanned"] = [os.path.relpath(f, ROOT).replace("\\", "/")
                               for f in pyfiles("kvmem/m2_visibility/m5")]
    res["verdict"] = {
        "gate_defined": os.path.exists(os.path.join(ROOT, "tools", "memory_source.py")),
        "has_call_site": res["call_site_count"] > 0,
        "no_bypass": not bypass,
        "m5_source_path_exists": res["m5_has_registry_read"],
        "note": ("M5 does not read the registry yet, so there is no source-selection branch "
                 "to gate: Stage 3 must add the call inside M5 source selection and mark it "
                 "TODO(stage3) until then. The gate is therefore enforced by this scan, not "
                 "by hope."),
    }
    res["pass"] = (res["verdict"]["has_call_site"] and res["verdict"]["no_bypass"])
    stage3 = "--stage3" in sys.argv
    if stage3:
        res["stage3"] = stage3_strict()
        res["pass"] = res["pass"] and res["stage3"]["pass"]
    out = os.path.join(HERE, "run_check_m5_gate.json")
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("call sites of %s: %d" % (GATE, res["call_site_count"]))
    for h in res["call_sites"]:
        print("  %s:%d  %s" % (h["file"], h["line"], h["text"]))
    print("registry readers on the M5 surface: %d (bypass: %d)"
          % (len(reads), len(bypass)))
    for r in reads:
        print("  %-46s gate=%s todo=%s -> %s"
              % (r["file"], r["calls_gate"], r["has_todo_stage3"],
                 "OK" if r["ok"] else "BYPASS"))
    print("out of scope (not an M5 source path): %d" % len(res["out_of_scope"]))
    print("m5 dir scanned:", ", ".join(os.path.basename(p) for p in res["m5_files_scanned"]))
    if stage3:
        st = res["stage3"]
        print("stage3 layer1 (AST, bound to the return point): %s"
              % ("OK" if st["layer1_ast"]["ok"] else "FAIL"))
        for f in st["source_returning_functions"]:
            print("  %s returns a source list; gate at %s" % (f["function"], f["file_line"]))
        print("stage3 layer2 (reachability from ensure_db): %s %s"
              % ("OK" if st["reachability"]["ok"] else "FAIL",
                 [c["file_line"] for c in st["reachability"]["calls"]]))
        print("stage3 layer3 (runtime refusal, authoritative): %s -> %s"
              % ("OK" if st["runtime_refusal"]["ok"] else "FAIL",
                 st["runtime_refusal"]["result"].get("raised")))
        print("stage3 no_todo_stage3: %s (count=%d)"
              % (st["no_todo_stage3"], st["todo_stage3_count"]))
    print("PASS" if res["pass"] else "FAIL")
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
