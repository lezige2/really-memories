# -*- coding: utf-8 -*-
"""M4-C-4 池泄漏观测臂：删 site 3 的 reset 之后，被丢 seq 的 cell 是否仍被持有（orphan>0）。

两臂都是**观测臂**，不是验收臂：
  · chat.die 被换成"照原样打印 + 记录 + 返回"（不抛、不 exit），finally 里恢复；
  · 产物写死 observation_arm / die_bypassed，die_events 只作 exhibit（role="exhibit"），
    **不进判据**——die 已被 bypass，用 die 判红就是桩自证。
判据只有一条、且只认引擎侧读数（cmd_m1 自己打的 [exhibit] 行）：
    is_red      := max_orphan > 0
    expected_red := (mode == "deleted")
engine_after 在 eng.close() 之前真读引擎实例（n_tokens/pos_max），不由 orphan 反推。

不调 H.run_main/finalize：finalize 的三条常驻守卫要求"红必须伴随 exit==1（die 路径）"，
观测臂把 die 换成返回值 ⇒ 该前提不成立。self-evidence 三件套与身份核仍用 H 的写法。
产物落 out/m4c4/：快闸 step5 的 glob 是 out/M4C-*.json（验收产物谱系），观测臂不得冒充它。
"""
import ast, contextlib, hashlib, io, json, os, re, sys, time, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:\llama-mem"
sys.path.insert(0, os.path.join(ROOT, "tools")); sys.path.insert(0, HERE)
import m4c_harness as H

SRC = os.path.join(ROOT, "tools", "chat.py")
NEEDLE = 'leases.reset(seq, site="m1.unmount.after_detach")'
WANT_SEQ = [[], ["profile", "project"], ["profile"], []]
OUT_DIR = os.path.join(HERE, "out", "m4c4")
ORPHAN_RE = re.compile(r"\[exhibit\] orphan=(-?\d+) chat_n=(-?\d+) "
                       r"mounted_seqs=\[([^\]]*)\] orphan_cells=\[([^\]]*)\]")


def variant():
    """同 run_site3.variant()：同一 NEEDLE、行数不变、只把那一行换成 pass。"""
    lines = open(SRC, encoding="utf-8").read().split("\n")
    hits = [i for i, t in enumerate(lines) if NEEDLE in t]
    if len(hits) != 1:
        raise SystemExit("STOP: site 3 命中 %d 行" % len(hits))
    i = hits[0]
    removed = lines[i]
    src_lines = list(lines)
    lines[i] = removed.split("leases.reset")[0] + "pass  # M4C-DELETED-SITE-3"
    d = os.path.join(HERE, "tmp", "variants")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "chat_site3_deleted.py.snap")
    assert len(lines) == len(src_lines), "变体行数必须等于原文行数：行号身份以它为前提"
    open(p, "w", encoding="utf-8", newline="").write("\n".join(lines))
    return p, removed, i + 1, len(src_lines), len(lines)


def parse_exhibits(text, turns):
    """把 [exhibit] orphan=… 行按出现顺序对到"该打印的轮"（want != 上一轮 want 的轮）。

    逐轮两条硬自洽：sum(orphan_cells) == orphan；mounted_seqs == 该轮 want 推出的 seq 集。
    """
    rows, problems = [], []
    for m in ORPHAN_RE.finditer(text):
        rows.append({"orphan": int(m.group(1)), "chat_n": int(m.group(2)),
                     "mounted_seqs": [int(x) for x in ast.literal_eval("[" + m.group(3) + "]")],
                     "orphan_cells": [[int(s), int(c)] for s, c in
                                      ast.literal_eval("[" + m.group(4) + "]")]})
    if len(rows) != len(turns):
        problems.append("exhibit 行数 %d != 应打印轮数 %d（打印点被动了？）"
                        % (len(rows), len(turns)))
    for r, t in zip(rows, turns):
        r["turn"] = t["turn"]
        r["want"] = list(t["want"])
        r["sum_matches"] = sum(c for _s, c in r["orphan_cells"]) == r["orphan"]
        r["mounted_matches_want"] = (sorted(r["mounted_seqs"]) ==
                                     sorted(i + 1 for i in range(len(t["want"]))))
        if not r["sum_matches"]:
            problems.append("turn %d: sum(orphan_cells) != orphan" % t["turn"])
        if not r["mounted_matches_want"]:
            problems.append("turn %d: mounted_seqs %s != want %s"
                            % (t["turn"], r["mounted_seqs"], t["want"]))
    return rows, problems


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "green"
    tag = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("M4C_BATCH_ID", "nobatch")
    batch = os.environ.get("M4C_BATCH_ID", "nobatch")
    if mode not in ("green", "deleted"):
        print("usage: run_m4c4.py <green|deleted> <tag>")
        sys.exit(2)
    if mode == "deleted":
        path, removed, lineno, src_n, var_n = variant()
    else:
        path, removed, lineno, src_n, var_n = SRC, None, None, None, None
    if H.verify_landed(batch) != 0:
        sys.exit(3)
    run_id = uuid.uuid4().hex[:8]
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "M4C4-%s-%s-%s.json" % (mode, tag, run_id))
    me = os.path.abspath(__file__)
    rec = {"schema": "m4c4_observation_v1", "site": 3, "mode": mode,
           "observation_arm": True, "die_bypassed": True,
           "expected_red": mode == "deleted", "is_red": None,
           "run_id": run_id, "batch_id": batch, "tag": tag,
           "variant_sha16": H.sha16(path), "chat_py_sha16": H.sha16(SRC),
           "deleted_line": removed, "deleted_line_no": lineno,
           "src_line_count": src_n, "variant_line_count": var_n,
           "want_sequence": WANT_SEQ, "selection_per_turn": [],
           "covers_declared": ["site3.m4c4"], "covers_observed": [],
           "coverage_ok": False,
           "fixture_file_used": me,
           "fixture_from_env": bool(os.environ.get("M4C_FIXTURE_FILE")),
           "sampled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "harness_sha16_now": H.harness_id(me),
           "orphan_turn": [], "chat_n_sequence": [], "die_events": [],
           "engine_after": None, "max_orphan": None, "orphan_leak": None,
           "stdout_sha16": None, "stdout_exhibit_lines": 0,
           "instrument": None, "instrument_hits": [], "error": None,
           "evidence_problems": [], "exit": None}
    rec["harness_sha16"] = rec["harness_sha16_now"]

    def drive(rec, _logp):
        mod = H.load(path, "chat_m4c4_%s_%s" % (mode, tag))
        st = {"i": -1}

        def fixed_selection(con, q, k=2):
            st["i"] += 1
            want = WANT_SEQ[st["i"]] if st["i"] < len(WANT_SEQ) else []
            rec["selection_per_turn"].append({"turn": st["i"] + 1, "q": q[:18],
                                              "want": list(want)})
            return [{"name": n, "score": 1.0, "signals": {"fixture": True}} for n in want]

        orig_die = mod.die

        def bypass_die(msg):
            rec["die_events"].append({"role": "exhibit", "turn": st["i"] + 1,
                                      "site": None, "message": msg})
            print("  [bypass-die] turn=%d %s" % (st["i"] + 1, msg))
            return None

        inst = {}
        orig_eng = mod.KVEngine

        class _Eng(orig_eng):
            def __init__(self, *a, **kw):
                orig_eng.__init__(self, *a, **kw)
                inst["eng"] = self

            def close(self):
                if rec.get("engine_after") is None:
                    rec["engine_after"] = {str(s): [int(self.n_tokens(s)), int(self.pos_max(s))]
                                           for s in range(mod.N_SEQ)}
                return orig_eng.close(self)

        mod._selection = fixed_selection
        mod.die = bypass_die
        mod.KVEngine = _Eng
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                mod.cmd_m1()
            rec["exit"] = 0
        except SystemExit as exc:
            rec["exit"] = exc.code
        except Exception as exc:
            rec["error"] = "%s: %s" % (type(exc).__name__, exc)
            rec["exit"] = -1
        finally:
            mod.die = orig_die
            mod.KVEngine = orig_eng
        text = buf.getvalue()
        rec["stdout_sha16"] = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        prev, turns = [], []
        for t in rec["selection_per_turn"]:
            if t["want"] != prev:
                turns.append(t)
            prev = t["want"]
        rows, problems = parse_exhibits(text, turns)
        rec["orphan_turn"] = rows
        rec["chat_n_sequence"] = [r["chat_n"] for r in rows]
        rec["stdout_exhibit_lines"] = sum(1 for ln in text.splitlines()
                                          if "[exhibit] orphan=" in ln)
        rec["evidence_problems"] = problems[:]
        if rows:
            rec["max_orphan"] = max(r["orphan"] for r in rows)
            rec["is_red"] = bool(rec["max_orphan"] > 0)
            rec["orphan_leak"] = rec["is_red"]
        if rec["engine_after"] is None:
            rec["evidence_problems"].append("engine_after 缺失（未取到引擎实例读数）")
        rec["covers_observed"] = ["site3.m4c4"] if rows else []
        rec["coverage_ok"] = rec["covers_observed"] == rec["covers_declared"]
        if not rec["coverage_ok"]:
            rec["evidence_problems"].append("coverage: 判据 site3.m4c4 未被观测到")
        if rec["is_red"] is None and not rec["error"]:
            rec["evidence_problems"].append("is_red 无法从 orphan 推出")

    drive(rec, None)
    rec["selfevidence"] = H.selfevidence(rec)
    rec["identity_cross_check"] = H.identity_cross_check(rec)
    if rec["evidence_problems"]:
        code = 5
    elif rec["error"]:
        code = 1
    elif rec["is_red"] is not rec["expected_red"]:
        code = 1
    else:
        code = 0
    rec["exit"] = code
    rec["verdict_rule"] = ("0 观测完成且形态与预登记一致；1 引擎报错或形态不符；"
                           "5 证据缺/形状违反（仪器坏）；2 用法；3 台账不符")
    json.dump(rec, open(out, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2, default=str)
    print("wrote", out)
    print(json.dumps({k: rec.get(k) for k in (
        "mode", "observation_arm", "die_bypassed", "is_red", "expected_red",
        "orphan_leak", "max_orphan", "chat_n_sequence", "coverage_ok",
        "harness_sha16", "selfevidence", "identity_cross_check",
        "error", "evidence_problems", "exit")}, ensure_ascii=False))
    sys.exit(code)


if __name__ == "__main__":
    main()