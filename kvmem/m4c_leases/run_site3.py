# -*- coding: utf-8 -*-
"""站点 3：一个引擎、两个不同选择（尾部收缩）。

判据读自 M4C_ASSERT_LOG_PATH 指向的文件（A site3.unmount.flow: sites 调用流 == dropped；
B site3.turn_orphan: 回合末 orphan == 0）。判定与退出码在 m4c_harness.verdict()。
"""
import json, io, os, sys, time, uuid, contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:\llama-mem"
sys.path.insert(0, os.path.join(ROOT, "tools")); sys.path.insert(0, HERE)
import m4c_harness as H
import m4c_verdict as V

SRC = os.path.join(ROOT, "tools", "chat.py")
NEEDLE = 'leases.reset(seq, site="m1.unmount.after_detach")'
WANT_SEQ = [[], ["profile", "project"], ["profile"]]


def variant():
    lines = open(SRC, encoding="utf-8").read().split("\n")
    hits = [i for i, t in enumerate(lines) if NEEDLE in t]
    if len(hits) != 1:
        raise SystemExit("STOP: site 3 命中 %d 行" % len(hits))
    i = hits[0]; removed = lines[i];
    src_lines = list(lines)
    lines[i] = removed.split("leases.reset")[0] + "pass  # M4C-DELETED-SITE-3"
    d = os.path.join(HERE, "tmp", "variants"); os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "chat_site3_deleted.py.snap")
    assert len(lines) == len(src_lines), "变体行数必须等于原文行数：行号身份（deleted_line_no / def_fp）以它为前提"
    open(p, "w", encoding="utf-8", newline="").write("\n".join(lines))
    return p, removed, i + 1, len(src_lines), len(lines)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "green"
    mode_unknown = mode not in ("green", "red", "unmount-dropnonempty")   # 拼错的 mode 不许默认成绿
    tag = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("M4C_BATCH_ID", "nobatch")
    batch = os.environ.get("M4C_BATCH_ID", "nobatch")
    if mode == "red":
        path, removed, lineno, src_n, var_n = variant()
    else:
        path, removed, lineno, src_n, var_n = SRC, None, None, None, None
    if H.verify_landed(os.environ.get("M4C_BATCH_ID", "nobatch")) != 0:
        sys.exit(3)
    run_id = uuid.uuid4().hex[:8]
    logp = os.path.join(HERE, "out", "asserts-%s.json" % run_id)
    os.environ["M4C_ASSERT_LOG_PATH"] = logp
    rec = {"schema": "m4c_site3_v5", "site": 3, "mode": mode,
           "expected_red": mode == "red", "run_id": run_id, "batch_id": batch,
           "assert_log_path": logp, "deleted_line": removed, "deleted_line_no": lineno,
           "src_line_count": src_n, "variant_line_count": var_n,
           "variant_sha16": H.sha16(path), "chat_py_sha16": H.sha16(SRC), "mode_unknown": mode_unknown,
           "want_sequence": WANT_SEQ, "selection_per_turn": [],
           "seqs_left_empty_per_turn": [], "covers_declared": ["site3"],
           "exit": None, "die_message": None,
           "sampled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    def drive(rec, logp):
        chat = H.load(path, "chat_s3_%s_%s" % (mode, tag))
        st = {"i": -1}

        def fixed_selection(con, q, k=2):
            st["i"] += 1
            want = list(WANT_SEQ) + ([[]] if mode == "unmount-dropnonempty" else [])
            names = want[st["i"]] if st["i"] < len(want) else []
            rec["selection_per_turn"].append({"turn": st["i"] + 1, "q": q[:18], "want": names})
            return [{"name": n, "score": 1.0, "signals": {"fixture": True}} for n in names]

        orig_cells = chat.GuardedLeases.cells_of

        def traced_cells(self, seq):
            v = orig_cells(self, seq)
            rec.setdefault("cells_readings_all", []).append({"seq": int(seq), "cells": v})
            return v

        chat.GuardedLeases.cells_of = traced_cells   # 只观测，不改判定
        chat._selection = fixed_selection
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                chat.cmd_m1()
            rec["exit"] = 0
        except SystemExit as exc:
            rec["exit"] = exc.code
            rec["die_message"] = buf.getvalue().strip().split("\n")[-1][:400]
        except Exception as exc:
            rec["exit"] = -1
            rec["die_message"] = "%s: %s" % (type(exc).__name__, exc)
        per = rec["selection_per_turn"]
        def seqs_of(w): return {i + 1 for i, _n in enumerate(w)}
        for a, b in zip(per, per[1:]):
            rec["seqs_left_empty_per_turn"].append({"turn": b["turn"],
                "seqs_prev": sorted(seqs_of(a["want"])), "seqs_written": sorted(seqs_of(b["want"])),
                "seqs_left_empty": sorted(seqs_of(a["want"]) - seqs_of(b["want"]))})
        _l = rec.get("assert_log_path")
        if _l and os.path.exists(_l):
            _log = json.load(open(_l, encoding="utf-8"))
            rec["dropped_count"] = sum(a.get("count", 0) for a in _log if a.get("id") == "site3.dropped")
            _seqs = [x for a in _log if a.get("id") == "site3.dropped.seqs" for x in a.get("seqs", [])]
            _rd = [r for r in rec.get("cells_readings_all", []) if r["seq"] in _seqs]
            rec["sites_readers"] = ["m1.unmount.after_detach -> A 判据 chat.py L563", "m1.mount.before_load -> 站点 4"]
            rec["control_tag"] = "m1.cells_control"
            rec["control_seq_in_use"] = bool(_seqs and _rd)
            try:
                if _rd:
                    rec["cells_control_empty_seq"] = {"seq": _rd[-1]["seq"], "cells": _rd[-1]["cells"],
                        "why_empty": "本臂该 seq 刚 reset、其后无 attach（reset 契约给的空）"}
            except Exception as exc:
                rec["control_failed"] = "%s: %s" % (type(exc).__name__, exc)

    out = os.path.join(HERE, "out", "M4C-SITE3-%s-%s-%s.json" % (mode, tag, run_id))
    rc = H.run_main(rec, out, logp, drive,
                    os.environ.get("M4C_FIXTURE_FILE") or os.path.abspath(__file__))
    print("assertions:", H.json.dumps(rec.get("assertions") or [], ensure_ascii=False)[:400])
    sys.exit(rc)


if __name__ == "__main__":
    main()
