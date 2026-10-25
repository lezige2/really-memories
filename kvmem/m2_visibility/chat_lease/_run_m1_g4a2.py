# -*- coding: utf-8 -*-
"""G4a-2/G4a-3 验证驱动：`m1` 真机臂（14B），正/变体两跑。

* 正跑：现盘 `tools/chat.py`（G4a-2：decide 入参 = 可挂载 selection）→ `out/M4C-m1-rerun-v2.json`
* 变体：`_before/chat.py@bb083a1b71165e97`（decide 入参 = 未过滤 sel）→ `out/G4a2-red-variant.json`
  ⇒ 同一构造必须回到 `memory_hit` 且控制问句被生成（ask=1）。

计数证：RecEngine 记录每次 `load`/`ask`；`decides` 记录每次 `E.decide(q, selection, ...)` 的
入参条数与结果；控制问句的 `ask` 次数直接由「ask 文本 == CONTROL_Q」现算。
全程一次性 temp DB 副本；仓库 DB / 冻结文件只读；`sha_stable` 前后复算。
"""
import argparse
import contextlib
import difflib
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
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

import chat as chat_new            # noqa: E402
from kvslots import KVEngine       # noqa: E402
import memory_source as ms         # noqa: E402

OUT = os.path.join(HERE, "out")
TMP = os.path.join(HERE, "tmp_db")
REPO_DB = os.path.join(ROOT, "kvmem", "chat.db")
SPEC = os.path.join(ROOT, "docs", "_work", "M2-FULL-S1-SPEC-lead.md")
BLOCKS = {k: os.path.join(ROOT, "kvmem", "m2_v1_14b", k + ".kvmem")
          for k in ("home", "project", "habit")}
FROZEN = {
    "analysis.py": os.path.join(TOOLS, "analysis.py"),
    "retrieval.py": os.path.join(TOOLS, "retrieval.py"),
    "evidence.py": os.path.join(TOOLS, "evidence.py"),
    "chat.py": os.path.join(TOOLS, "chat.py"),
    "spec": SPEC,
    "repo_chat.db": REPO_DB,
    **{"block_" + k: v for k, v in BLOCKS.items()},
}
LOADS, ASKS, FINAL, DECIDES = [], [], {}, []


def sha16(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


def snap():
    return {k: sha16(v) for k, v in FROZEN.items()}


class CountingEngine(KVEngine):
    """记录 load/ask；close 前抓终态 cells/pos。计数即判据：控制问句 ask 必须为 0。"""

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
            for s in range(8):
                FINAL[str(s)] = {"n_tokens": int(self.n_tokens(s)),
                                 "pos_max": int(self.pos_max(s))}
        finally:
            super().close()


def load_module(path, name):
    spec = importlib.util.spec_from_loader(name, SourceFileLoader(name, path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def run_one(mod, db_copy, assert_log):
    global LOADS, ASKS, FINAL, DECIDES
    LOADS, ASKS, FINAL, DECIDES = [], [], {}, []
    if os.path.exists(assert_log):
        os.remove(assert_log)
    os.environ["M4C_ASSERT_LOG_PATH"] = assert_log
    orig_decide = mod.E.decide

    def rec_decide(query, selection, transcript=""):
        d = orig_decide(query, selection, transcript)
        DECIDES.append({"q": query, "n_selection": len(selection),
                        "selection_names": [s["name"] for s in selection],
                        "state": d["state"], "refuse": bool(d["refuse"]),
                        "reason": d["reason"], "reply": d["reply"]})
        return d

    mod.E.decide = rec_decide
    mod.KVEngine = CountingEngine
    mod.DB = db_copy
    buf, err = io.StringIO(), io.StringIO()
    t0 = time.time()
    code, tb = 0, None
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
            mod.cmd_m1(explain=False, control=False)
    except SystemExit as e:
        code = int(e.code or 0)
    except BaseException:
        code, tb = 1, traceback.format_exc()
    run_s = round(time.time() - t0, 1)
    log = []
    if os.path.exists(assert_log):
        with open(assert_log, encoding="utf-8") as fh:
            log = json.load(fh)
    events = [e for e in log if e.get("role") == "event"]
    return {"exit": code, "run_s": run_s, "stdout": buf.getvalue(),
            "stderr": err.getvalue(), "traceback": tb,
            "loads": list(LOADS), "asks": list(ASKS), "final_cells": dict(FINAL),
            "decides": list(DECIDES),
            "events": events,
            "attach_events": [e for e in events if e.get("id") == "chat.attach"],
            "skip_events": [e for e in events if e.get("id") == "site3.skipped_no_block"],
            "die_events": [e for e in events if e.get("id") == "die"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chat", default=os.path.join(TOOLS, "chat.py"))
    ap.add_argument("--out", default=os.path.join(OUT, "M4C-m1-rerun-v2.json"))
    ap.add_argument("--tag", default="v2")
    ap.add_argument("--kind", default="")
    ap.add_argument("--base", default="")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)

    chat_path = os.path.abspath(args.chat)
    if chat_path == os.path.abspath(os.path.join(TOOLS, "chat.py")):
        mod = chat_new
    else:
        mod = load_module(chat_path, "chat_variant_%s" % args.tag)
    copy = os.path.join(TMP, "chat@g4a2-%s.db" % args.tag)
    if os.path.exists(copy):
        os.remove(copy)
    shutil.copy2(REPO_DB, copy)
    copy_before = sha16(copy)
    before = snap()
    assert_log = os.path.join(OUT, "M4C-m1-rerun-%s.asserts.json" % args.tag)

    rec = run_one(mod, os.path.abspath(copy), assert_log)
    after = snap()
    copy_after = sha16(copy)

    control_q = mod.CONTROL_Q
    ask_by_q = {}
    for a in rec["asks"]:
        ask_by_q[a["q"]] = ask_by_q.get(a["q"], 0) + 1
    control_asks = [a for a in rec["asks"] if a["q"] == control_q]
    control_decide = [d for d in rec["decides"] if d["q"] == control_q]
    d0 = control_decide[0] if control_decide else {}
    product = {
        "schema": "m4c_m1_g4a2_v1",
        "task": "task-35 G4a-2/G4a-3",
        "tag": args.tag,
        "at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "chat_py": {"path": os.path.relpath(chat_path, ROOT).replace("\\", "/"),
                    "sha16": sha16(chat_path), "bytes": os.path.getsize(chat_path)},
        "db": {"repo": sha16(REPO_DB),
               "copy": os.path.relpath(copy, ROOT).replace("\\", "/"),
               "copy_sha16_before": copy_before, "copy_sha16_after": copy_after},
        "exit": rec["exit"], "run_s": rec["run_s"],
        "stdout": rec["stdout"], "stderr": rec["stderr"], "traceback": rec["traceback"],
        "asserts": {
            "log": os.path.relpath(assert_log, ROOT).replace("\\", "/"),
            "attach_events": rec["attach_events"],
            "attaches_done": len(rec["attach_events"]),
            "skip_events": rec["skip_events"],
            "die_events": rec["die_events"],
        },
        "loads": rec["loads"],
        "final_cells": rec["final_cells"],
        "decides": rec["decides"],
        "asks": rec["asks"],
        "ask_by_question": ask_by_q,
        "control_q": {
            "q": control_q,
            "decide": d0,
            "ask_count": len(control_asks),
            "answers": [a["answer"] for a in control_asks],
        },
        "sha_stable": {"before": before, "after": after,
                       "unchanged": before == after,
                       "changed": [k for k in before if before[k] != after[k]]},
    }
    if args.tag == "v2":
        product["g4a2_checks"] = {
            "control_state_no_evidence": d0.get("state") == "no_evidence",
            "control_refuse_true": d0.get("refuse") is True,
            "control_ask_zero": len(control_asks) == 0,
            "control_reply_refusal": bool(d0.get("reply"))
                                    and d0.get("reply") == mod.E.REFUSAL,
            "mounts_profile_project": sorted(l["path"] for l in rec["loads"])
                                       == ["profile.kvmem", "project.kvmem"],
        }
        product["four_state"] = ("通过" if all(product["g4a2_checks"].values())
                                 else "未通过")
    else:
        product["variant_of"] = "kvmem/m2_visibility/chat_lease/_before/chat.py@bb083a1b71165e97"
        product["variant_kind"] = args.kind or "single-point(want->sel)"
        if args.base:
            bsrc = open(args.base, encoding="utf-8", newline="").read().split("\n")
            vsrc = open(chat_path, encoding="utf-8", newline="").read().split("\n")
            dl = list(difflib.unified_diff(bsrc, vsrc, "base", "variant", lineterm=""))
            product["single_point_diff"] = {
                "base": os.path.relpath(args.base, ROOT).replace("\\", "/"),
                "base_sha16": sha16(args.base),
                "hunks": sum(1 for ln in dl if ln.startswith("@@")),
                "changed_lines": [ln for ln in dl
                                  if ln.startswith(("-", "+")) and not ln.startswith(("---", "+++"))],
            }
        product["red_points"] = {
            "control_state_memory_hit": d0.get("state") == "memory_hit",
            "control_refuse_false": d0.get("refuse") is False,
            "control_ask_nonzero": len(control_asks) > 0,
            "generated_answer_nonempty": any((a or "").strip() for a in
                                             [x["answer"] for x in control_asks]),
        }
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(product, fh, ensure_ascii=False, indent=1)
    print("product: %s (%d B, sha16=%s)" % (args.out, os.path.getsize(args.out),
                                            sha16(args.out)))
    print("tag=%s exit=%s control_state=%r refuse=%r control_ask=%d attaches=%d die=%s"
          % (args.tag, rec["exit"], d0.get("state"), d0.get("refuse"),
             len(control_asks), len(rec["attach_events"]),
             [e.get("id") for e in rec["die_events"]]))
    return 0


if __name__ == "__main__":
    sys.exit(main())