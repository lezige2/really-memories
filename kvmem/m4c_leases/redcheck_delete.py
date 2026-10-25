# -*- coding: utf-8 -*-
"""站点 1 / 4 的删行实测：删掉该站点的 leases.reset 后读数是否与不删一致。

期望不红（这两站是冗余站点）。判定与退出码在 m4c_harness.verdict()。
"""
import io, json, os, sys, time, uuid, contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:\llama-mem"
sys.path.insert(0, os.path.join(ROOT, "tools")); sys.path.insert(0, HERE)
import m4c_harness as H
import m4c_verdict as V

SRC = os.path.join(ROOT, "tools", "chat.py")
NEEDLES = {1: 'leases.reset(i, site="chat.place.fresh")',
           4: 'leases.reset(seq, site="m1.mount.before_load")'}
WANT_SEQ = [[], ["profile", "project"], ["profile"]]


def variant(site):
    lines = open(SRC, encoding="utf-8").read().split("\n")
    hits = [i for i, t in enumerate(lines) if NEEDLES[site] in t]
    if len(hits) != 1:
        raise SystemExit("STOP: site %d 命中 %d 行" % (site, len(hits)))
    i = hits[0]; removed = lines[i];
    src_lines = list(lines)
    lines[i] = removed.split("leases.reset")[0] + "pass  # M4C-DELETED-SITE-%d" % site
    d = os.path.join(HERE, "tmp", "variants"); os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "chat_site%d_deleted.py.snap" % site)
    assert len(lines) == len(src_lines), "变体行数必须等于原文行数：行号身份（deleted_line_no / def_fp）以它为前提"
    open(p, "w", encoding="utf-8", newline="").write("\n".join(lines))
    return p, removed, i + 1, len(src_lines), len(lines)


def attach_readings(logp):
    """配置读数（§6.22 第四样）：attach 执行过的次数 + 条目形状。

    attaches_done 数的是「日志里 id 恰为 chat.attach 的条目数」—— 名字描述它数的东西（§6.19）。
    attach_events_ok 只在有对象时判形状（role/site 由 _event 写死）；空集记 None：
    「没有对象」由 attaches_done 的期望承担，不让 False 同时表示「没有」与「形状错」两义（§6.2/§6.3）。
    空集/形状三态的判定在 m4c_verdict.instrument_hits（字段 + 消费者同批，§6.15）。
    日志文件不存在 ⇒ 两个字段都 None（「没有日志」不是「0 次附着」）；空日志才是 0。
    None 不等于通过：instrument_hits 仍按期望命中，只是产物里两种情形可分（§6.3）。
    """
    if not os.path.exists(logp):
        return {"attaches_done": None, "attach_events_ok": None}
    log = json.load(open(logp, encoding="utf-8"))
    a = [x for x in log if isinstance(x, dict) and x.get("id") == "chat.attach"]
    return {"attaches_done": len(a),
            "attach_events_ok": (all(x.get("role") == "event" and x.get("site") is None for x in a)
                                 if a else None)}


def main():
    site = int(sys.argv[1])
    mode = sys.argv[2] if len(sys.argv) > 2 else "base"
    tag = sys.argv[3] if len(sys.argv) > 3 else "attempt"
    mode_unknown = mode not in ("base", "deleted")   # 拼错的 mode 不许默认成 base
    if mode == "deleted":
        path, removed, lineno, src_n, var_n = variant(site)
    else:
        path, removed, lineno, src_n, var_n = SRC, None, None, None, None
    if H.verify_landed(os.environ.get("M4C_BATCH_ID", "nobatch")) != 0:
        sys.exit(3)
    run_id = uuid.uuid4().hex[:8]
    logp = os.path.join(HERE, "out", "asserts-%s.json" % run_id)
    os.environ["M4C_ASSERT_LOG_PATH"] = logp
    rec = {"schema": "m4c_delete_v4", "site": site, "mode": mode,
           "expected_red": False,   # 站点 1/4 期望"删了也不红"（冗余）
           "run_id": run_id, "batch_id": os.environ.get("M4C_BATCH_ID", "nobatch"),
           "assert_log_path": logp, "deleted_line": removed, "deleted_line_no": lineno,
           "src_line_count": src_n, "variant_line_count": var_n,
           "variant_sha16": H.sha16(path), "chat_py_sha16": H.sha16(SRC), "loads": [],
           "mode_unknown": mode_unknown,
           # 配置读数（§6.22 第四样）：期望写进产物，判据由 m4c_verdict.instrument_hits 比
           "attaches_expected_min": 1, "attaches_done": None, "attach_events_ok": None,
           "covers_declared": ["site%d" % site], "exit": None, "note": None,
           "selection_per_turn": [],
           "sampled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    def drive(rec, logp):
        chat = H.load(path, "chat_del_%d_%s_%s" % (site, mode, tag))
        orig = chat.ms.load_into
        def traced(eng, row, seq, *a, **kw):
            n = orig(eng, row, seq, *a, **kw)
            rec["loads"].append({"seq": int(seq), "name": row[1], "n_returned": int(n),
                                 "n_tokens_after": int(eng.n_tokens(int(seq))),
                                 "pos_max_after": int(eng.pos_max(int(seq)))})
            return n
        chat.ms.load_into = traced
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                if site == 1:
                    chat.QUESTIONS = []
                    chat.cmd_chat(control=False)   # 走 attach 真的发生过的路径："冗余"与"无人使用"读数相同、结论不同
                else:
                    st = {"i": -1}
                    def fixed_selection(con, q, k=2):
                        st["i"] += 1
                        names = WANT_SEQ[st["i"]] if st["i"] < len(WANT_SEQ) else []
                        return [{"name": n, "score": 1.0, "signals": {"fixture": True}} for n in names]
                    chat._selection = fixed_selection
                    chat.cmd_m1()
            rec["exit"] = 0
        except SystemExit as exc:
            rec["exit"] = exc.code
            rec["note"] = buf.getvalue().strip().split("\n")[-1][:300]
        except Exception as exc:
            rec["exit"] = -1
            rec["note"] = "%s: %s" % (type(exc).__name__, exc)
        rec.update(attach_readings(logp))   # 空集/形状的三态语义见函数 docstring

    lp = os.path.join(HERE, "out", "asserts-%s.json" % run_id)
    out = os.path.join(HERE, "out", "M4C-DELETE-SITE%d-%s-%s-%s.json" % (site, mode, tag, run_id))
    rc = H.run_main(rec, out, logp, drive,
                    os.environ.get("M4C_FIXTURE_FILE") or os.path.abspath(__file__))   # 冗余站点：期望不红
    print("loads:", H.json.dumps(rec["loads"], ensure_ascii=False))
    sys.exit(rc)


if __name__ == "__main__":
    main()
