# -*- coding: utf-8 -*-
"""test_retrieval_service_cpu.py -- P0 regression: natural mode MUST mount memory.

Fixture: 3 real memories in a temporary sqlite DB (one contains 京A88888).
Question "我的车牌号是多少？" must (a) be selected by _retrieval_select and
(b) actually mount a block in the natural-mode answer path (block_ids non-empty).

No GPU/model: StubEngine + real memory_service/chat_daily code.
Run: python -X utf8 tools/test_retrieval_service_cpu.py ; exit 0 = pass.
"""
import os
import sys
import tempfile
import time

os.environ["LLAMA_MEM_MODE"] = "natural"
os.environ["LLAMA_MEM_VERIFY"] = "0"      # verify is orthogonal to this regression

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import chat_daily as D  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print("ok   %s" % name)
    else:
        FAILS.append(name)
        print("FAIL %s %s" % (name, detail))


def make_app(tmp):
    return D.DailyApp(
        D.StubEngine(),
        db_path=os.path.join(tmp, "daily.db"),
        blocks_dir=os.path.join(tmp, "blocks"),
        sessions_dir=os.path.join(tmp, "sessions"),
        model_path=os.path.join(tmp, "model.stub"),
        restore=False,
        retrieval_mode="topk",
        topk=4,
        logger=False,
    )


FACTS = [
    "我的车牌号是京A88888。",
    "我的工位在 6 楼 B 区，分机号 8042。",
    "我每周三晚上 7 点有组会。",
]


def main():
    tmp = tempfile.mkdtemp(prefix="retr_p0_")
    D.install_fake_model(os.path.join(tmp, "model.stub"))
    app = make_app(tmp)
    ids = {}
    for f in FACTS:
        app.remember(f)
    for r in app._rows():
        ids[str(r[3])] = int(r[0])
    check("fixture_3_memories", len(app._rows()) == 3, len(app._rows()))
    check("fixture_has_plate_fact",
          any("京A88888" in str(r[3]) for r in app._rows()))

    q = "我的车牌号是多少？"
    sel = app._retrieval_select(q)
    check("retrieval_select_hits_plate",
          bool(sel) and any("京A88888" in str(app._row_by_id(s["source_id"])[3])
                            for s in sel), sel)
    check("retrieval_candidates_nonzero",
          int(getattr(app, "_last_candidate_count", 0)) > 0,
          getattr(app, "_last_candidate_count", None))

    # stub engine returns a canned answer; the counted block_ids come from mounting
    app.eng.ask = lambda seq, text, n_predict=32, pos=None: "你的车牌号是京A88888。"
    res = app._ask_natural(q, time.perf_counter())
    plate_id = ids["我的车牌号是京A88888。"]
    check("natural_mode_answered", bool(res and res.get("answer")))
    check("natural_mode_block_ids_nonempty", bool(res.get("block_ids")), res.get("block_ids"))
    check("natural_mode_mounted_plate_block", plate_id in (res.get("block_ids") or []),
          res.get("block_ids"))
    check("natural_mode_state", res.get("state") == "natural", res.get("state"))

    # a non-matching question must not mount the plate block
    app.eng.ask = lambda seq, text, n_predict=32, pos=None: "不知道"
    res2 = app._ask_natural("今天天气怎么样？", time.perf_counter())
    check("unrelated_no_plate_mount", plate_id not in (res2.get("block_ids") or []),
          res2.get("block_ids"))

    print("\n%d/%d passed" % (len(FAILS) + 0, 0) if False else
          "\n%s" % ("ALL PASS" if not FAILS else "FAILURES: %r" % (FAILS,)))
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())