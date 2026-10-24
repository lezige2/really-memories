# -*- coding: utf-8 -*-
"""M4 §12 acceptance orchestrator: new-process retrieval/answer, dedupe, multi-value, position 0.

  python -u -X utf8 m4_verify.py
"""
import io, json, os, re, sqlite3, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:/llama-mem"
for p in (os.path.join(ROOT, "tools"), HERE):
    sys.path.insert(0, p)
import m4_extract as X                                            # noqa: E402
import m4_store as S                                              # noqa: E402

DB = os.path.join(HERE, "m4_memory.db")
TS = "2026-10-25T09:00:00"
SAMPLE = [
    {"role": "user", "text": "你好呀！", "ts": TS},
    {"role": "assistant", "text": "你好！有什么可以帮你？", "ts": TS},
    {"role": "user", "text": "我住在广陵路 12 号 2 单元 602。", "ts": TS},
    {"role": "user", "text": "我每天早上七点半出门，别在那个时候给我推消息。", "ts": TS},
    {"role": "user", "text": "我车牌是浙B-3F19K。", "ts": TS},
    {"role": "assistant", "text": "记住了。", "ts": TS},
    {"role": "user", "text": "帮我查下明天天气。", "ts": TS},
    {"role": "user", "text": "谢谢，就这样吧。", "ts": TS},
    {"role": "user", "text": "对了，我女儿小名叫豆豆，下周三她生日，提醒我买蛋糕。", "ts": TS},
]
QUESTIONS = ["我住在哪？", "我车牌号是多少？"]


def child(args):
    t0 = time.time()
    p = subprocess.run([sys.executable, "-u", "-X", "utf8",
                        os.path.join(HERE, "m4_newproc.py") if args[0] != "pos0"
                        else os.path.join(HERE, "m4_pos0_refuse.py")]
                       + (args[1:] if args[0] != "pos0" else []),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    blob = ""
    for line in (p.stdout or "").splitlines():
        if line.startswith("@@JSON@@"):
            blob = line[len("@@JSON@@"):]
    data = json.loads(blob) if blob else None
    return {"argv": args, "returncode": p.returncode, "seconds": round(time.time() - t0, 1),
            "json": data, "stderr_tail": (p.stderr or "")[-400:]}


def scenario_dedup():
    conv = SAMPLE + [{"role": "user", "text": "我住在广陵路 12 号 2 单元 602。", "ts": TS}]
    rows = X.run(conv)
    keeps = [(r, m) for r in rows for m in r["memories"]]
    tmp = os.path.join(tempfile.gettempdir(), "m4_dedup.db")
    if os.path.exists(tmp):
        os.remove(tmp)
    con, _ = S.connect(tmp)
    acts = []
    for r, m in keeps:
        a, mid = S.upsert_memory(con, m, turn=r["turn"], sent_id=r["sent_id"], code=r["code"],
                                 block_id="blk")
        acts.append({"attr": m["attr"], "value": m["value"], "action": a})
    n = con.execute("SELECT COUNT(*) FROM memory").fetchone()[0]
    con.close()
    os.remove(tmp)
    distinct = len({(m["subject"], m["attr"], m["value"]) for _r, m in keeps})
    deduped = [a for a in acts if a["action"] == "deduped"]
    return {"keeps": len(keeps), "distinct_keys": distinct, "rows": n, "actions": acts,
            "deduped": deduped,
            "no_new_row": n == distinct,
            "dedup_hit_the_repeat": bool(deduped)
                                    and deduped[0]["value"] == "广陵路 12 号 2 单元 602",
            "ok": n == distinct and bool(deduped)}


def scenario_multi_value():
    tmp = os.path.join(tempfile.gettempdir(), "m4_mv.db")
    if os.path.exists(tmp):
        os.remove(tmp)
    con, _ = S.connect(tmp)
    conv = [{"role": "user", "text": "我住在广陵路 12 号 2 单元 602。", "ts": "2026-10-20T09:00:00"},
            {"role": "user", "text": "我搬到文昌路 5 号了。", "ts": TS}]
    acts = []
    for r in X.run(conv):
        for m in r["memories"]:
            a, mid = S.upsert_memory(con, m, turn=r["turn"], sent_id=r["sent_id"],
                                     code=r["code"], block_id="blk")
            acts.append({"attr": m["attr"], "value": m["value"], "action": a, "mem_id": mid})
    rows = S.dump_memories(con)
    con.close()
    os.remove(tmp)
    live = [r for r in rows if r["status"] == "live"]
    sup = [r for r in rows if r["status"] == "superseded"]
    return {"actions": acts, "rows": len(rows), "live": len(live), "superseded": len(sup),
            "old_value_kept": len(rows) == 2,
            "ok": len(rows) == 2 and len(live) == 1 and len(sup) == 1}


def main():
    res = {"schema": "m4_verify_v1", "parent_pid": os.getpid(),
           "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "db": DB,
           "questions": QUESTIONS}

    con = sqlite3.connect(DB)
    res["stored"] = [dict(zip(("mem_id", "attr", "value", "status", "anchored_time"), r))
                     for r in con.execute("SELECT mem_id, attr, value, status, anchored_time "
                                          "FROM memory ORDER BY mem_id")]
    res["sources"] = [dict(zip(("id", "name", "label", "text"), r))
                      for r in con.execute("SELECT id, name, label, text FROM memory_source")]
    res["blocks"] = [dict(zip(("block_id", "path", "sha256", "cells", "pos_lo", "pos_hi"),
                              r))
                     for r in con.execute("SELECT block_id, path, sha256, cells, pos_lo, pos_hi "
                                          "FROM block")]
    con.close()

    # --- acceptance 4: a new process retrieves
    res["searches"] = [child(["search", "--mode", "search", "--q", q]) for q in QUESTIONS]
    # --- acceptance 5: a new process answers
    res["answers"] = [child(["answer", "--mode", "answer", "--q", q]) for q in QUESTIONS]
    # --- §12.6 position 0, one pass and one refusal, on a real engine
    res["position0"] = child(["pos0"])

    # --- §12.4 dedupe and §12.5 multi-value
    res["dedupe"] = scenario_dedup()
    res["multi_value"] = scenario_multi_value()

    # --- verbatim check for the answers
    val_home = next(m["value"] for m in res["stored"] if m["attr"] == "住址")
    val_plate = next(m["value"] for m in res["stored"] if m["attr"] == "车牌")
    checks = []
    for q, want, blob in ((QUESTIONS[0], val_home, res["answers"][0]),
                          (QUESTIONS[1], val_plate, res["answers"][1])):
        d = blob.get("json") or {}
        checks.append({"q": q, "want_verbatim": want,
                       "answer": d.get("answer", ""),          # raw evidence: decides hit
                       "hit": want in (d.get("answer") or ""),
                       "answer_display": d.get("answer_display"),
                       "display_has_tag": "<" "/think" ">" in (d.get("answer_display") or ""),
                       "raw_has_tag": "<" "/think" ">" in (d.get("answer") or ""),
                       "raw_kept_unchanged": d.get("answer_exact", "").strip()
                                             == (d.get("answer") or ""),
                       "pid": d.get("pid"), "child_of": os.getpid(),
                       "new_process": bool(d.get("pid")) and d.get("pid") != os.getpid(),
                       "retrieval_routed": bool(d.get("routed_by"))})
    res["answer_checks"] = checks
    res["search_checks"] = [{"q": b["argv"][-1], "hits": ((b.get("json") or {}).get("hits") or []),
                             "pid": (b.get("json") or {}).get("pid"),
                             "new_process": (b.get("json") or {}).get("pid") != os.getpid()}
                            for b in res["searches"]]

    acc = {
        "1_one_block": len(res["blocks"]) == 1,
        "2_memories_with_spans": len(res["stored"]) == 6,
        "3_saved_and_inserted": all(b["sha256"] for b in res["blocks"]),
        "4_new_process_retrieval": all(s["hits"] for s in res["search_checks"])
                                   and all(s["new_process"] for s in res["search_checks"]),
        "5_new_process_answer": all(c["hit"] and c["new_process"] for c in checks),
        "6_multi_value_keeps_old": res["multi_value"]["ok"],
        "7_relative_time_anchored": any(m["anchored_time"] == "2026-10-28"
                                        for m in res["stored"]),
        "8_dedupe_no_new_row": res["dedupe"]["ok"] and bool(res["dedupe"]["deduped"]),
        "position0_pass_and_refuse": bool(
            (res["position0"].get("json") or {}).get("pass", {}).get("ok")
            and (res["position0"].get("json") or {}).get("refuse", {}).get("both_guards_refuse")),
    }
    acc["display_never_decides"] = all(c["hit"] == (c["want_verbatim"] in c["answer"])
                                        for c in checks) and all(not c["display_has_tag"]
                                                                 for c in checks)
    acc["raw_answer_preserved"] = all(c["raw_kept_unchanged"] for c in checks)
    acc["all_pass"] = all(acc.values())
    res["acceptance"] = acc
    res["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out = os.path.join(HERE, "run_m4_verify.json")
    json.dump(res, io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps(acc, ensure_ascii=False, indent=1))
    for c in checks:
        print("  Q=%s -> %r hit=%s pid=%s" % (c["q"], c["answer"][:48].replace("\n", " "),
                                              c["hit"], c["pid"]))
    print("[RUN] wrote", out)
    return 0 if acc["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
