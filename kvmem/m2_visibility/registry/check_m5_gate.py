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
    print("PASS" if res["pass"] else "FAIL")
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
