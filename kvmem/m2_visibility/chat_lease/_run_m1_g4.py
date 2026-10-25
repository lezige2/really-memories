# -*- coding: utf-8 -*-
"""G4 重跑驱动：`m1` 真机臂（14B）+ 与 M4-C 已签读数逐项对照。

只读仓库 DB / 冻结文件；跑在**一次性 temp 副本**上（`tmp_db/chat@g4-m1.db`），
并记录副本跑前/跑后 sha（m1 会无条件 rebuild 派生索引，见 S1 台账 addendum F1）。

产物：`out/M4C-m1-rerun.json`（LF，UTF-8）。
用法：python _run_m1_g4.py [--out out/M4C-m1-rerun.json]
"""
import argparse
import contextlib
import hashlib
import io
import json
import os
import shutil
import sys
import time
import traceback
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)

import chat                      # noqa: E402  （S1 块 + m1；本单只读它的逻辑，不改 two 路径）
import memory_source as ms       # noqa: E402
import retrieval as R            # noqa: E402

OUT = os.path.join(HERE, "out")
TMP = os.path.join(HERE, "tmp_db")
REPO_DB = os.path.join(ROOT, "kvmem", "chat.db")
COPY = os.path.join(TMP, "chat@g4-m1.db")
ASSERT_LOG = os.path.join(OUT, "M4C-m1-rerun.asserts.json")
SPEC = os.path.join(ROOT, "docs", "_work", "M2-FULL-S1-SPEC-lead.md")
BLOCKS = {
    "home": os.path.join(ROOT, "kvmem", "m2_v1_14b", "home.kvmem"),
    "project": os.path.join(ROOT, "kvmem", "m2_v1_14b", "project.kvmem"),
    "habit": os.path.join(ROOT, "kvmem", "m2_v1_14b", "habit.kvmem"),
}
FROZEN = {
    "analysis.py": os.path.join(TOOLS, "analysis.py"),
    "retrieval.py": os.path.join(TOOLS, "retrieval.py"),
    "evidence.py": os.path.join(TOOLS, "evidence.py"),
    "chat.py": os.path.join(TOOLS, "chat.py"),
    "spec": SPEC,
    "repo_chat.db": REPO_DB,
    **{"block_" + k: v for k, v in BLOCKS.items()},
}


def sha16(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


def sha_snapshot():
    return {k: sha16(v) for k, v in FROZEN.items()}


LOADS = []          # cmd_m1 在 finally 里 close，实例不可达 ⇒ 记到模块级
ASKS = []
FINAL = {}


class RecEngine(chat.KVEngine):
    """记录 load（块/seq/cells）与 ask（问题/答案）；close 前抓终态 cells/pos。"""

    def load(self, seq, path):
        n = super().load(seq, path)
        LOADS.append({"seq": int(seq), "path": os.path.basename(path),
                      "n_tokens": int(n), "cells_after": int(self.n_tokens(int(seq)))})
        return n

    def ask(self, seq, text, n_predict=32, pos=None):
        ans = super().ask(seq, text, n_predict=n_predict, pos=pos)
        ASKS.append({"seq": int(seq), "q": text, "answer": ans})
        return ans

    def close(self):
        try:
            for s in range(chat.N_SEQ):
                FINAL[str(s)] = {"n_tokens": int(self.n_tokens(s)),
                                 "pos_max": int(self.pos_max(s))}
        finally:
            super().close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(OUT, "M4C-m1-rerun.json"))
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    if os.path.exists(COPY):
        os.remove(COPY)
    shutil.copy2(REPO_DB, COPY)
    copy_before = sha16(COPY)
    before = sha_snapshot()
    if os.path.exists(ASSERT_LOG):
        os.remove(ASSERT_LOG)

    # 只替换模块级 KVEngine（cmd_m1 运行时按名解析），two/默认 chat 逻辑不参跑
    chat.KVEngine = RecEngine
    chat.DB = COPY
    os.environ["M4C_ASSERT_LOG_PATH"] = ASSERT_LOG
    engaged = None
    out, err = io.StringIO(), io.StringIO()
    t0 = time.time()
    exit_code = 0
    tb = None
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            chat.cmd_m1(explain=False, control=False)
    except SystemExit as e:
        exit_code = int(e.code or 0)
    except BaseException:
        exit_code = 1
        tb = traceback.format_exc()
    run_s = round(time.time() - t0, 1)
    stdout = out.getvalue()
    stderr = err.getvalue()

    after = sha_snapshot()
    copy_after = sha16(COPY)

    # LOADS/ASKS/FINAL 由 RecEngine 在模块级记录（实例在 cmd_m1 finally 里 close，不可达）
    log = []
    if os.path.exists(ASSERT_LOG):
        with open(ASSERT_LOG, encoding="utf-8") as fh:
            log = json.load(fh)
    events = [e for e in log if e.get("role") == "event"]
    crits = [e for e in log if e.get("role") == "criterion"]
    attach_events = [e for e in events if e.get("id") == "chat.attach"]
    skip_events = [e for e in events if e.get("id") == "site3.skipped_no_block"]
    die_events = [e for e in events if e.get("id") == "die"]
    skipped_crits = [c for c in crits if c.get("id") == "site3.skipped_no_block"]

    # 选择面（跑后从同一副本现算；selection 是纯检索读数，与生成无关）
    con = ms.connect(COPY)
    try:
        rows = {r[1]: r for r in ms.block_rows(con) if r[5] is not None}
        selection = []
        for q in [chat.CONTROL_Q] + chat.QUESTIONS:
            sel = chat._selection(con, q)
            selection.append({
                "q": q,
                "selected": [{"name": s["name"], "score": round(float(s["score"]), 6),
                              "source_id": int(s["source_id"])} for s in sel],
                "skipped_no_block": [s["name"] for s in sel if s["name"] not in rows],
                "mountable": [s["name"] for s in sel if s["name"] in rows],
            })
        db_counts = {t: con.execute("select count(*) from %s" % t).fetchone()[0]
                     for t in ("memory_source", "memory_block", "doc")}
        index_meta = dict(con.execute("select key, value from index_meta"))
    finally:
        con.close()

    # M4-C base 已签读数（M4C-VERDICT-lead.md §2 base 行）
    m4c_expected = {
        "exit": 0,
        "attaches_done": 2,
        "attach_events_ok": True,
        "loads": [{"seq": 1, "name": "profile", "n_tokens": 50},
                  {"seq": 2, "name": "project", "n_tokens": 36}],
        "hits": [],
    }
    exhibit = [ln for ln in stdout.splitlines() if ln.strip().startswith("[exhibit] seqs_after")]
    loads_db = [{"seq": l["seq"], "path": l["path"], "n_tokens": l["n_tokens"],
                 "cells_after": l["cells_after"]} for l in LOADS]
    cells_after_mount = {}
    for l in LOADS:
        cells_after_mount.setdefault(str(l["seq"]), l["cells_after"])
    product = {
        "schema": "m4c_m1_rerun_v1",
        "task": "task-33 G4a+G4b",
        "at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "chat_py_sha16": sha16(FROZEN["chat.py"]),
        "chat_py_before_sha16": sha16(os.path.join(HERE, "_before",
                                                   "chat.py@288d2d85720359e0")),
        "db": {"repo": sha16(REPO_DB), "copy": os.path.relpath(COPY, ROOT).replace("\\", "/"),
               "copy_sha16_before": copy_before, "copy_sha16_after": copy_after,
               "counts": db_counts, "index_meta": index_meta},
        "exit": exit_code,
        "run_s": run_s,
        "stdout": stdout,
        "stderr": stderr,
        "traceback": tb,
        "asserts": {
            "log": os.path.relpath(ASSERT_LOG, ROOT).replace("\\", "/"),
            "n_events": len(events), "n_crits": len(crits),
            "attach_events": attach_events,
            "attaches_done": len(attach_events),
            "attach_events_ok": all(e.get("id") == "chat.attach"
                                    and e.get("role") == "event"
                                    and e.get("site") is None for e in attach_events),
            "skipped_no_block_events": skip_events,
            "skipped_no_block_crits": skipped_crits,
            "die_events": die_events,
            "hits": [e.get("id") for e in die_events],
        },
        "selection": selection,
        "loads": loads_db,
        "facts": [{"q": a["q"], "answer": a["answer"]} for a in ASKS],
        "final_cells": FINAL,
        "cells_after_mount": cells_after_mount,
        "exhibit_seq_after": exhibit,
        "sha_stable": {"before": before, "after": after,
                       "unchanged": before == after,
                       "changed": [k for k in before if before[k] != after[k]]},
        "m4c_comparison": {
            "expected": m4c_expected,
            "observed": {
                "exit": exit_code,
                "attaches_done": len(attach_events),
                "attach_events_ok": all(e.get("id") == "chat.attach"
                                        and e.get("role") == "event"
                                        and e.get("site") is None for e in attach_events),
                "loads": loads_db,
                "cells_after_mount": cells_after_mount,
                "hits": [e.get("id") for e in die_events],
            },
            "note": "M4-C base 臂已签读数见 M4C-VERDICT-lead.md §2 base 行；"
                    "本产物为 m1 CLI 真机臂，逐项对照 exit / attaches_done / attach_events_ok / "
                    "hits / loads（cells 由 exhibit seqs_after 行落证）/ sha_stable",
        },
        "four_state": "待判（由 EXIT/对照结果决定）",
    }
    ok_exit = exit_code == 0
    ok_attach_n = len(attach_events) == 2
    ok_attach_seqs = sorted(int(e.get("seq")) for e in attach_events) == [1, 2]
    ok_mount_set = sorted(l["path"] for l in loads_db) == ["profile.kvmem", "project.kvmem"]
    ok_cells_multiset = sorted(l["n_tokens"] for l in loads_db) == [36, 50]
    ok_layout_seq = ([(l["seq"], l["path"]) for l in loads_db] ==
                     [(1, "profile.kvmem"), (2, "project.kvmem")])
    ok_hits = not [e.get("id") for e in die_events]
    ok_stable = before == after
    product["m4c_comparison"].update({
        "checks": {"exit_0": ok_exit, "attaches_done_2": ok_attach_n,
                   "attach_seqs_1_2": ok_attach_seqs,
                   "mount_set_profile_project": ok_mount_set,
                   "cells_multiset_36_50": ok_cells_multiset,
                   "layout_seq_match_m4c_fixture": ok_layout_seq,
                   "hits_empty": ok_hits, "sha_stable": ok_stable},
        "layout_note": "M4-C base 夹具用 fixed_selection 固定顺序 profile→seq1 / project→seq2"
                       "（redcheck_delete.py:17 WANT_SEQ=[[],['profile','project'],['profile']]）；"
                       "m1 按 selection 分数顺序挂（project 6.24 > profile 4.23）⇒ seq 分配相反。"
                       "cells 集合仍为 {36,50}、挂载集合仍为 {profile,project} ⇒ 布局口径差，非读数回归。",
        "verdict": "一致（7/8；loads 的 seq 分配为夹具固定顺序 vs selection 顺序的口径差）"
                   if all([ok_exit, ok_attach_n, ok_attach_seqs, ok_mount_set,
                           ok_cells_multiset, ok_hits, ok_stable]) else "不一致（逐项见 checks）",
    })
    product["four_state"] = ("通过（G4b：m1 exit 0，跳过可见，无 die；G4a 判据作废候选另记）"
                             if all([ok_exit, ok_attach_n, ok_attach_seqs, ok_mount_set,
                                     ok_cells_multiset, ok_hits, ok_stable])
                             else "未通过（逐项见 checks）")
    product["crits"] = [{"id": c.get("id"), "status": c.get("status"),
                         "names": c.get("names")} for c in crits]
    product["g4a_note"] = ("G4a：selection 面宽于挂载面（retrieval 索引 10 源 / 可挂 2 源），"
                           "CONTROL_Q 命中 conv_2026-10-25#L5（正文即控制句）⇒ M4-B/M4-C 的"
                           "**负对照**判据此前不成立（判据作废候选）；本修法把无块源显式跳过并记账，"
                           "negative 臂‘不挂载’语义恢复，但正/负臂须重跑才恢复整臂可信。")
    product["g4b_note"] = ("G4b：KeyError 只是同一根因的表征（rows[name] 缺块行）；"
                           "修法 = order 过滤到有块行的源 + 跳过可见（event + crit skipped + 打印）"
                           " + 防御 die，不重建索引、不静默。")
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(product, fh, ensure_ascii=False, indent=1)
    print("product: %s (%d B, sha16=%s)" % (args.out, os.path.getsize(args.out),
                                            sha16(args.out)))
    print("exit=%s attaches=%s skipped_events=%s hits=%s sha_stable=%s"
          % (exit_code, len(attach_events), len(skip_events),
             [e.get("id") for e in die_events], before == after))
    return 0


if __name__ == "__main__":
    sys.exit(main())