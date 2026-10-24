# -*- coding: utf-8 -*-
"""Trace assertions (driver-side gate, hard fail)."""
import argparse, json, re, sys
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--run-json", required=True)
    a = ap.parse_args()
    d = json.load(open(a.run_json, encoding="utf-8"))
    cells = {s["id"]: s["cells"] for s in d["layout"]["segments"]}
    rows = {}
    cur = None
    bad = []
    gate = []
    classes = {"SUM": 0, "SUM2": 0, "blk": 0, "OK": 0}
    for line in open(a.log, encoding="utf-8", errors="replace"):
        if "[MASKDBG-SUM]" in line:
            m = re.search(r"p1=(\d+)", line)
            cur = int(m.group(1)) if m else None
            rows.setdefault(cur, {})
            g = re.search(r"row_allowed=(\d+)", line)
            u = re.search(r"n_ub=(\d+)", line)
            if g and u:
                gate.append((cur, int(g.group(1)), int(u.group(1))))
        elif "[MASKDBG] " in line:
            m = re.search(r"blk=(\S+) .*cells=(\d+) allowed=(\d+) masked=(\d+)", line)
            if not m or cur is None:
                continue
            blk, c, ok, mk = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
            rows[cur][blk] = (c, ok, mk)
            if blk not in cells:
                bad.append("unknown block %s" % blk)
            elif c != cells[blk]:
                bad.append("%s cells=%d but layout says %d" % (blk, c, cells[blk]))
            elif ok + mk != c:
                bad.append("%s allowed+masked=%d != cells=%d" % (blk, ok + mk, c))
    expect = int(d.get("decode_batches_expected", -1))
    if expect < 0:
        bad.append("run json missing decode_batches_expected")
    elif len(rows) != expect:
        bad.append("expected %d traced p1 rows (1 prompt + n_predict), got %d" % (expect, len(rows)))
    if not rows:
        bad.append("no [MASKDBG-SUM] line -- trace empty")
    for p1, blks in rows.items():
        missing = set(cells) - set(blks)
        if missing:
            bad.append("p1=%s missing block lines %s" % (p1, sorted(missing)))
    # total gate: the row must allow exactly the real cells (memory cells + chat tokens)
    # three-source reconciliation:
    #   row_allowed        <- whole-row scan inside the engine
    #   cell_count         <- probe kvshim_seq_cell_scan, measured before the ask
    #   chat tokens (p1)   <- positions 4096..p1, i.e. p1 - CHAT + 1
    #   total_masked       <- per-block window loop (position filtered)
    # n_ub is the ubatch size (1 during decode), NOT the number of prompt tokens in the row.
    CHAT = 4096
    cell_count = int((d.get("cell_layer") or {}).get("cell_count") or -1)
    for p1, row_allowed, n_ub in gate:
        blks = rows.get(p1, {})
        total_masked = sum(v[2] for v in blks.values())
        chat = p1 - CHAT + 1
        want = cell_count + chat - total_masked
        if row_allowed != want:
            bad.append("reconciliation p1=%s: row_allowed=%s != cell_count(%s) + chat(%s) - masked(%s) = %s"
                       % (p1, row_allowed, cell_count, chat, total_masked, want))
    if not gate:
        bad.append("no SUM row_allowed/n_ub captured -- total gate not evaluated")
    print("p1 rows:", len(rows), " blocks per row:", len(next(iter(rows.values()))) if rows else 0,
          " total-gate rows:", len(gate))
    with open(a.log, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if "[MASKDBG-SUM] " in line:
                classes["SUM"] += 1
            elif "[MASKDBG-SUM2] " in line:
                classes["SUM2"] += 1
            elif "[MASKDBG-OK]" in line:
                classes["OK"] += 1
            elif "[MASKDBG] " in line:
                classes["blk"] += 1
    d["trace_classes"] = classes
    d["_gate_rows"] = gate          # name and shape unchanged: 25 rows of [p1, row_allowed, n_ub]
    with open(a.run_json, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False, indent=1)
    print("trace_classes:", classes)
    if bad:
        print("ASSERT FAILED:")
        for b in bad[:10]:
            print("  -", b)
        return 5
    print("ASSERT OK: allowed+masked == cells for every block row; every p1 row has all blocks")
    return 0
if __name__ == "__main__":
    sys.exit(main())