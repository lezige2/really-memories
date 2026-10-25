# -*- coding: utf-8 -*-
"""S1-b 真机臂驱动（v6 口径 ae2d88ad5ecc25d3）。

两条路径共用 chat.two_session_run 的同一调度：
  * 真引擎 = KVEngine(14B, n_ctx=8192, n_seq=8, gpu=99, kv=q8_0)
  * 透明代理 = RecordingCountingEngine(chat.CountingEngine)：只数 share/drop/reset，
    再额外记每轮问答（判据仍由 two_session_run 自己产出，驱动不改判）

用法（仓库根目录）：
  PY -X utf8 kvmem/m2_visibility/chat_lease/_run_s1_real.py \
      --rounds 10 --sample 1 --out kvmem/m2_visibility/m2_planner/out/S1-real.json

只读仓库 chat.db；所有臂用 temp DB 副本（--db 默认 chat_lease/tmp_db/chat@237d8e1f.db）。
"""
import argparse
import hashlib
import json
import os
import sys
import time
import traceback
from datetime import datetime

ROOT = r"D:\llama-mem"
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import chat  # noqa: E402

SPEC = os.path.join(ROOT, "docs", "_work", "M2-FULL-S1-SPEC-lead.md")
DEFAULT_DB = os.path.join(ROOT, "kvmem", "m2_visibility", "chat_lease", "tmp_db",
                          "chat@237d8e1f.db")
FROZEN_THREE = [os.path.join(TOOLS, n) for n in ("analysis.py", "retrieval.py", "evidence.py")]
BLOCK_FILES = [os.path.join(ROOT, "kvmem", "m2_v1_14b", n + ".kvmem")
               for n in ("home", "project")]
HABIT_FILE = os.path.join(ROOT, "kvmem", "m2_v1_14b", "habit.kvmem")
SESSION_SEQ_TO_ID = {int(chat.TWO_SEQ_A): "A", int(chat.TWO_SEQ_B): "B"}


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def sha_map(paths):
    return {p: sha16(p) for p in paths if os.path.exists(p)}


def norm(text):
    return "".join(str(text or "").split())


class RecordingCountingEngine(chat.CountingEngine):
    """计数代理 + 只读旁路记录（不改调度/不改判据）。"""

    def __init__(self, eng):
        super().__init__(eng)
        self.per_round = []

    def chat_round(self, session_seq, question, first, chat_start):
        before = int(self._eng.n_tokens(int(session_seq)))
        ans = self._eng.ask(int(session_seq), question, n_predict=48,
                            pos=(int(chat_start) if first else None))
        after = int(self._eng.n_tokens(int(session_seq)))
        sid = SESSION_SEQ_TO_ID.get(int(session_seq), str(session_seq))
        self.per_round.append({"session": sid, "seq": int(session_seq),
                               "round": sum(1 for r in self.per_round if r["session"] == sid) + 1,
                               "n_tokens_before": before, "n_tokens_after": after,
                               "delta": after - before, "answer": ans,
                               "answer_norm": norm(ans)})
        return ans


def make_provider(before, db_path):
    """⑤：真机臂的唯一 sha_stable 判据（跑前快照在闭包里，跑后现算对比）。"""
    watched = FROZEN_THREE + BLOCK_FILES + [os.path.join(TOOLS, "chat.py"), SPEC]

    def provider(pool=None):
        after = sha_map(watched)
        db_after = sha16(db_path) if os.path.exists(db_path) else None
        checked = []
        for p in watched:
            b, a = before["files"].get(p), after.get(p)
            checked.append({"path": p, "sha16_before": b, "sha16_after": a,
                            "unchanged": bool(b is not None and b == a)})
        return {"status": "done",
                "unchanged": bool(all(c["unchanged"] for c in checked)),
                "checked": checked,
                "checked_blocks": ["home", "project"],
                "not_checked": [{"name": "habit", "why": "只登记未挂、不检"}],
                "db": {"path": db_path, "sha16_before": before["db"],
                       "sha16_after": db_after,
                       "unchanged": bool(before["db"] == db_after),
                       "note": "chat.db 是派生库（可重建），坐标见 G3"},
                "at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}

    return provider


def fact_layer(res, per_round):
    """①/②b 的逐轮旁证（判据本身在 two_session_run 的 checks 里，驱动只并排展示）。"""
    facts = {s["id"]: s["fact"] for s in res["sessions"]}
    out = {}
    for sid, fact in facts.items():
        others = [f for k, f in facts.items() if k != sid]
        rows = [r for r in per_round if r["session"] == sid]
        own_literal = fact in res["answers"].get(sid, "")
        own_norm = norm(fact) in norm(res["answers"].get(sid, ""))
        other_any = [f for f in others
                     if any(norm(f) in r["answer_norm"] for r in rows)]
        out[sid] = {"fact": fact,
                    "own_hit_last_literal": bool(own_literal),
                    "own_hit_last_norm": bool(own_norm),
                    "own_hit_rounds": sum(1 for r in rows if norm(fact) in r["answer_norm"]),
                    "rounds": len(rows),
                    "other_fact_in_any_round": other_any}
    return out


def main():
    ap = argparse.ArgumentParser(description="S1-b real arm driver (v6)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--rounds", type=int,
                    default=int(os.environ.get("S1_ROUNDS", chat.TWO_N_ROUNDS)))
    ap.add_argument("--sample", type=int, default=1)
    ap.add_argument("--db", default=DEFAULT_DB)
    args = ap.parse_args()

    before = {"files": sha_map(FROZEN_THREE + BLOCK_FILES
                              + [os.path.join(TOOLS, "chat.py"), SPEC]),
              "db": sha16(args.db)}
    chat.DB = args.db                      # 仓库 chat.db 只读；本进程只用 temp 副本
    t0 = time.time()
    product = {"schema": "s1_real_arm_driver_v1",
               "spec": "docs/_work/M2-FULL-S1-SPEC-lead.md@" + sha16(SPEC),
               "chat_py_sha16": sha16(os.path.join(TOOLS, "chat.py")),
               "script_sha16": sha16(os.path.abspath(__file__)),
               "db_copy": {"path": args.db, "sha16_before": before["db"]},
               "rounds_requested": int(args.rounds),
               "sample": int(args.sample),
               "started_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}
    eng = None
    try:
        t_load = time.time()
        eng = RecordingCountingEngine(
            chat.KVEngine(chat.MODEL, n_ctx=chat.N_CTX, n_seq=chat.N_SEQ,
                          gpu=99, kv="q8_0"))
        product["engine_load_s"] = round(time.time() - t_load, 1)
        product["engine"] = {"model": chat.MODEL, "model_bytes": os.path.getsize(chat.MODEL),
                             "n_ctx": int(chat.N_CTX), "n_seq": int(chat.N_SEQ),
                             "kv": "q8_0", "gpu_layers": 99,
                             "bytes_per_token": int(eng.bytes_per_token())}
        provider = make_provider(before, args.db)
        t_run = time.time()
        res = chat.two_session_run(eng, n_rounds=int(args.rounds),
                                   sha_stable_provider=provider)
        product["run_s"] = round(time.time() - t_run, 1)
        product["run"] = res
        product["per_round"] = eng.per_round
        product["fact_layer"] = fact_layer(res, eng.per_round)
        product["counter_calls"] = {"share": int(eng.share_calls),
                                    "drop": int(eng.drop_calls),
                                    "reset": int(eng.reset_calls)}
        product["exit"] = int(res["exit"])
    except BaseException as exc:            # 停手：不吞异常，原样落盘再抛出
        product["exception"] = {"type": type(exc).__name__, "msg": str(exc),
                                "traceback_tail": traceback.format_exc()[-2000:]}
        product["exit"] = 3
    finally:
        if eng is not None:
            try:
                eng.close()
            except BaseException:
                pass
        product["finished_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        product["elapsed_s"] = round(time.time() - t0, 1)
        out_dir = os.path.dirname(os.path.abspath(args.out))
        os.makedirs(out_dir, exist_ok=True)
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(product, fh, ensure_ascii=False, indent=1)
        print("product: %s (%d B, sha16=%s, exit=%s)"
              % (args.out, os.path.getsize(args.out), sha16(args.out), product["exit"]))

    res = product.get("run")
    if res is None:
        print("EXCEPTION: %s" % json.dumps(product.get("exception"), ensure_ascii=False)[:1200])
        return product["exit"]
    print("sessions: %s" % json.dumps(
        [{k: s[k] for k in ("id", "seq", "rounds", "chat_start", "chat_cells", "n_tokens",
                            "pos_max", "pos_max_expect", "reading_ok", "plan")}
         for s in res["sessions"]], ensure_ascii=False))
    print("checks: %s" % json.dumps(res["checks"], ensure_ascii=False))
    print("fail_ids: %s verdict: %s" % (res["fail_ids"], res["verdict"]))
    print("answers: %s" % json.dumps(res["answers"], ensure_ascii=False)[:400])
    print("fact_layer: %s" % json.dumps(product["fact_layer"], ensure_ascii=False))
    print("counters: %s" % json.dumps(res["counters"], ensure_ascii=False))
    print("accounting: %s" % json.dumps(res["cells_accounting"], ensure_ascii=False))
    print("sha_stable: status=%s unchanged=%s"
          % (res["sha_stable"].get("status"), res["sha_stable"].get("unchanged")))
    return product["exit"]


if __name__ == "__main__":
    sys.exit(main())